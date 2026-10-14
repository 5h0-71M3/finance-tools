"""Local upload page for the Lloyds Risk BDX, launched by `finance-tools lloyds-risk-bdx`."""
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from starlette.datastructures import UploadFile  # what request.form() returns; fastapi's UploadFile is a subclass

from finance_tools.lloyds_risk.build import REGIONS, build_region, deliverable_name, read_frame, write_deliverable

_PAGE = Path(__file__).with_name("page.html")


def find_old_files(old_dir: Path) -> dict[str, Path | None]:
    """newest file in last month's Risk folder for each UMR, like `B174010160SS24 Risk BDX ....xlsx`"""
    found: dict[str, Path | None] = {}
    for spec in REGIONS:
        for umr in spec.umrs:
            # `SS24 ` with the trailing space so B174010161SS24 doesn't pick up an SS24S file
            candidates = [p for p in old_dir.glob(f"{umr} *") if p.suffix.lower() in (".xlsx", ".csv")]
            found[umr] = max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None
    return found


def create_app(old_dir: Path, out_dir: Path) -> FastAPI:
    app = FastAPI(title="Lloyds Risk BDX")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return _PAGE.read_text()

    @app.get("/api/defaults")
    def defaults():
        return {
            "old_dir": str(old_dir),
            "out_dir": str(out_dir),
            "regions": [
                {"name": s.name, "umrs": list(s.umrs), "sheets": [s.sheet_24, s.sheet_25]} for s in REGIONS
            ],
            "old_files": {umr: (p.name if p else None) for umr, p in find_old_files(old_dir).items()},
        }

    @app.post("/api/build")
    async def build(request: Request):
        form = await request.form()
        old_defaults = find_old_files(old_dir)

        def frame(field: str, fallback: Path | None = None):
            upload = form.get(field)
            if isinstance(upload, UploadFile) and upload.filename:
                return read_frame(upload.file, upload.filename), upload.filename
            if fallback is not None:
                return read_frame(fallback), fallback.name
            raise HTTPException(400, f"Missing file for {field}.")

        # build both regions before writing anything, so a bad upload never leaves half a delivery behind
        results, regions = [], []
        try:
            for spec in REGIONS:
                new, new_name = frame(f"new_{spec.name}")
                old_24, old_24_name = frame(f"old_{spec.umr_24}", old_defaults[spec.umr_24])
                old_25, old_25_name = frame(f"old_{spec.umr_25}", old_defaults[spec.umr_25])
                result = build_region(new, old_24, old_25, spec)
                summary = result.summary()
                summary["inputs"] = {"new": new_name, spec.umr_24: old_24_name, spec.umr_25: old_25_name}
                results.append(result)
                regions.append(summary)
        except ValueError as e:
            raise HTTPException(400, str(e))

        stamp = datetime.now().strftime("%Y-%m-%dT%H%M")
        written = []
        for result in results:
            spec = result.spec
            for umr, sheet, df in (
                (spec.umr_24, spec.sheet_24, result.file_24),
                (spec.umr_25, spec.sheet_25, result.file_25),
            ):
                path = write_deliverable(df, out_dir / deliverable_name(umr, stamp), sheet)
                written.append({"name": path.name, "sheet": sheet, "rows": len(df)})
        return {"out_dir": str(out_dir), "regions": regions, "files": written}

    @app.get("/api/files/{name}")
    def download(name: str):
        path = out_dir / name
        if path.parent != out_dir or path.suffix != ".xlsx" or not path.is_file():
            raise HTTPException(404, "File not found.")
        return FileResponse(path, filename=name)

    @app.post("/api/reveal")
    def reveal():
        subprocess.run(["open", str(out_dir)], check=False)
        return {"ok": True}

    return app
