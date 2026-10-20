"""Register the BDX report list in a running pipeui and point its watch folder at Downloads.

Split by job so each piece is testable on its own:
- ``newest_matching_file`` / ``check_primary_key`` — read-only file checks;
- ``plan_registrations`` — pure: which spec gets which file, or why it's skipped;
- ``PipeuiClient`` — the HTTP calls (the app owns the DuckDB file, so nothing here opens it).

File matching reuses pipeui's own ``pattern_matches``, so this command and the watch folder
always agree on which file belongs to which report.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import duckdb
import requests
from pipeui.backend.data.base.schema.constants import SUPPORTED_EXTENSIONS
from pipeui.backend.domain.sources.create import pattern_matches

from finance_tools.bdx_reports.manifest import ReportSpec

REGISTER = "register"
ALREADY_REGISTERED = "already registered"
COVERED = "covered by existing report"
NO_FILE = "no file found"
BAD_KEY = "key check failed"


@dataclass(frozen=True)
class PlannedRegistration:
    spec: ReportSpec
    status: str  # REGISTER | ALREADY_REGISTERED | COVERED | NO_FILE | BAD_KEY
    file: Path | None = None
    detail: str = ""


def newest_matching_file(folder: Path, pattern: str, max_age_days: float | None = None) -> Path | None:
    """The most recently modified supported file in ``folder`` (not recursive) that ``pattern`` claims."""
    oldest = time.time() - max_age_days * 86400 if max_age_days else None
    candidates = [
        p for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() in SUPPORTED_EXTENSIONS
        and not p.name.startswith((".", "~"))
        and pattern_matches(pattern, p.name)
        and (oldest is None or p.stat().st_mtime >= oldest)
    ]
    return max(candidates, key=lambda p: p.stat().st_mtime, default=None)


def check_primary_key(path: Path, key: str) -> str | None:
    """None when ``key`` is a column of ``path`` with unique, non-null values; else the problem."""
    # Types don't matter for a key check; reading xlsx as text avoids DuckDB's
    # type-sniffing failures on mixed columns (e.g. "MPL 0312465-00" in a numeric column).
    source = "read_xlsx(?, all_varchar = true)" if path.suffix.lower() == ".xlsx" else "read_csv_auto(?)"
    conn = duckdb.connect()
    try:
        columns = [r[0] for r in conn.execute(f"DESCRIBE SELECT * FROM {source}", [str(path)]).fetchall()]
        if key not in columns:
            return f"no '{key}' column ({len(columns)} columns)"
        rows, distinct, non_null = conn.execute(
            f'SELECT COUNT(*), COUNT(DISTINCT "{key}"), COUNT("{key}") FROM {source}', [str(path)]
        ).fetchone()
    finally:
        conn.close()
    if non_null < rows:
        return f"'{key}' is blank on {rows - non_null:,} rows"
    if distinct < rows:
        return f"'{key}' repeats ({distinct:,} distinct of {rows:,} rows)"
    return None


def plan_registrations(
    specs: tuple[ReportSpec, ...],
    folder: Path,
    existing: dict[str, str | None],
    max_age_days: float | None = None,
    check_keys: bool = True,
) -> list[PlannedRegistration]:
    """What registering ``specs`` from ``folder`` would do, spec by spec. Reads files; writes nothing.

    ``existing`` is pipeui's current reports, name → filename pattern. A spec whose newest
    export is already claimed by an existing report is left to that report (``COVERED``):
    registering a second report on the same files would make every future download
    ambiguous, and the existing one may already have pipeline steps attached.
    """
    plans = []
    for spec in specs:
        if spec.name in existing:
            plans.append(PlannedRegistration(spec, ALREADY_REGISTERED))
            continue
        file = newest_matching_file(folder, spec.pattern, max_age_days)
        if file is None:
            plans.append(PlannedRegistration(spec, NO_FILE))
            continue
        owner = next(
            (name for name, pattern in existing.items() if pattern and pattern_matches(pattern, file.name)),
            None,
        )
        if owner is not None:
            plans.append(PlannedRegistration(spec, COVERED, file, f"'{owner}' already loads these files"))
            continue
        try:
            problem = check_primary_key(file, spec.primary_key) if check_keys else None
        except duckdb.Error as exc:
            problem = f"couldn't read the file: {exc}"
        if problem:
            plans.append(PlannedRegistration(spec, BAD_KEY, file, problem))
            continue
        plans.append(PlannedRegistration(spec, REGISTER, file))
    return plans


class PipeuiClient:
    """The few pipeui endpoints this setup needs."""

    def __init__(self, base_url: str, timeout: float = 900.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout  # registering ingests the file — a 400 MB PolicyList takes a while

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def existing_reports(self) -> dict[str, str | None]:
        """pipeui's reports as name → filename pattern."""
        resp = requests.get(self._url("/sources"), timeout=30)
        resp.raise_for_status()
        return {s["source_name"]: s.get("pattern") for s in resp.json()}

    def register_from_path(self, spec: ReportSpec, file: Path) -> dict:
        """Register ``spec`` from ``file`` and ingest it. Returns the pipeui response body."""
        resp = requests.post(
            self._url("/sources/from-path"),
            json={
                "file_path": str(file),
                "source_name": spec.name,
                "primary_key": spec.primary_key,
                "ingestion_method": spec.ingestion_method,
                "pattern": spec.pattern,
            },
            timeout=self.timeout,
        )
        body = resp.json()
        if resp.status_code >= 400:
            errors = body.get("errors") or [body.get("detail") or resp.text]
            return {"ok": False, "errors": errors}
        return body

    def sources(self) -> list[dict]:
        """pipeui's reports (``GET /sources``)."""
        resp = requests.get(self._url("/sources"), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def scan_functions(self) -> None:
        """Re-discover functions in the configured functions paths."""
        requests.post(self._url("/functions/scan"), timeout=300).raise_for_status()

    def functions(self) -> list[dict]:
        resp = requests.get(self._url("/functions"), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def function_sets(self) -> list[dict]:
        resp = requests.get(self._url("/function-sets"), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def save_function_set(self, name: str, member_ids: list[str], description: str | None = None) -> str:
        """Create ``name`` with these members in order, or replace an existing set's members. Returns its id."""
        existing = next((s for s in self.function_sets() if s["set_name"] == name), None)
        if existing is None:
            resp = requests.post(self._url("/function-sets"), timeout=30, json={
                "set_name": name, "set_description": description, "members": member_ids,
            })
        else:
            resp = requests.patch(self._url(f"/function-sets/{existing['set_id']}"), timeout=30, json={
                "members": member_ids, "set_description": description,
            })
        body = resp.json()
        if resp.status_code >= 400 or not body.get("ok"):
            raise RuntimeError(f"Couldn't save function set {name!r}: {body}")
        return body["set"]["set_id"]

    def pipeline(self, source_id: str) -> list[dict]:
        """A report's steps, built-in and function, in run order."""
        resp = requests.get(self._url(f"/sources/{source_id}/pipeline"), timeout=30)
        resp.raise_for_status()
        return resp.json()["steps"]

    def attach_step(self, source_id: str, *, function_id: str | None = None, set_id: str | None = None) -> dict:
        """Attach a function or set whose only parameter is the working table (no column bindings)."""
        body = {"function_id": function_id} if function_id else {"set_id": set_id}
        resp = requests.post(self._url(f"/pipelines/{source_id}/steps"), json=body, timeout=60)
        result = resp.json()
        if resp.status_code >= 400 or result.get("ok") is False:
            raise RuntimeError(f"Couldn't attach to {source_id}: {result}")
        return result

    def attach_builtin(self, source_id: str, builtin_type: str, config: dict) -> dict:
        resp = requests.post(self._url(f"/sources/{source_id}/attach-builtin"), timeout=60,
                             json={"builtin_type": builtin_type, "builtin_config": config})
        result = resp.json()
        if resp.status_code >= 400 or not result.get("ok"):
            raise RuntimeError(f"Couldn't attach {builtin_type} to {source_id}: {result}")
        return result

    def detach_step(self, source_id: str, source_function_map_id: str) -> None:
        """Removes a function / set step (``DELETE /pipelines/{id}/steps/{map id}``)."""
        requests.delete(self._url(f"/pipelines/{source_id}/steps/{source_function_map_id}"), timeout=60).raise_for_status()

    def reorder(self, source_id: str, step_ids: list[str]) -> None:
        """Saves a new run order: every step's id (built-ins' ``step_id``, functions' and sets'
        ``source_function_map_id``). pipeui refuses an order that uses a column before it exists."""
        resp = requests.put(self._url(f"/pipelines/{source_id}/order"), json={"step_ids": step_ids}, timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"Couldn't reorder {source_id}: {resp.text}")

    def detach_builtin(self, source_id: str, step_id: str) -> None:
        requests.delete(self._url(f"/sources/{source_id}/attach-builtin/{step_id}"), timeout=60).raise_for_status()

    def patch_builtin(self, source_id: str, step_id: str, config: dict) -> dict:
        resp = requests.patch(self._url(f"/sources/{source_id}/attach-builtin/{step_id}"), timeout=60,
                              json={"builtin_config": config})
        result = resp.json()
        if resp.status_code >= 400 or not result.get("ok"):
            raise RuntimeError(f"Couldn't update {step_id} on {source_id}: {result}")
        return result

    def patch_source(self, source_id: str, fields: dict) -> dict:
        """Change a report's settings (pattern, ingestion_method, sheet_name, …)."""
        resp = requests.patch(self._url(f"/sources/{source_id}"), json=fields, timeout=60)
        body = resp.json()
        if resp.status_code >= 400 or not body.get("ok"):
            raise RuntimeError(f"Couldn't update report {source_id}: {body}")
        return body["source"]

    def outputs(self, source_id: str) -> dict:
        """A report's outputs: ``{outputs, summary, output_dir, default_period}``."""
        resp = requests.get(self._url(f"/sources/{source_id}/outputs"), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def save_outputs(self, source_id: str, outputs: list[dict], summary: dict | None) -> dict:
        """Replace a report's output list and control file."""
        resp = requests.put(self._url(f"/sources/{source_id}/outputs"), timeout=60,
                            json={"outputs": outputs, "summary": summary})
        body = resp.json()
        if resp.status_code >= 400 or not body.get("ok"):
            raise RuntimeError(f"Couldn't save the outputs: {body.get('errors') or body}")
        return body

    def build_outputs(self, source_id: str, period: str) -> dict:
        """Run the report and write its output files into pipeui's output folder (the UI's
        Build output files). Returns ``{period, folder, files: [{name, path, rows, replaced}]}``."""
        resp = requests.post(self._url(f"/pipelines/{source_id}/outputs/build"), params={"period": period},
                             timeout=self.timeout)
        body = resp.json()
        if resp.status_code >= 400 or not body.get("ok"):
            raise RuntimeError(f"The build failed: {'; '.join(body.get('errors') or []) or body}")
        return body

    def add_watch_folder(self, folder: Path) -> list[str]:
        """Add ``folder`` to pipeui's watch folders (no-op if present). Returns the new list."""
        settings = requests.get(self._url("/settings"), timeout=30).json()
        paths = list(settings.get("watch_paths") or [])
        if str(folder) not in paths:
            paths.append(str(folder))
            resp = requests.patch(self._url("/settings"), json={"watch_paths": paths}, timeout=30)
            resp.raise_for_status()
        return paths
