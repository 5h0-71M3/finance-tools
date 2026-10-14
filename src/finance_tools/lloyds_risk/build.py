"""Builds the Lloyds Risk BDX deliverables, replacing `Lloyds Risk BDX - Template (Day 5).xlsx`.

The template keeps every policy on the UMR it was reported under last time, so the
deliverables stay consistent with what Lloyds already has:

    Proposed UMR = UMR in last month's `...SS24` file
                   else UMR in last month's `...SS25` file
                   else UMR on the new Looker download

The UMR column is overwritten with the proposed UMR; rows proposed onto the SS24 code
go to the 24 file and everything else goes to the 25 file (this includes the inherited
`B174010161SS24S` UK rows). Blank cells become 0, which is what the template's
`='UK All (new)'!Z2` style formulas produced in the files we sent.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

import pandas as pd
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell

DATE_COLUMNS = ("Effective Date", "Coverage End Date")
DATE_FORMAT = "mm-dd-yy"

_UK_HEADERS = [
    "Coalition Policy Number", "Effective Date", "Coverage End Date", "Was Policy Cancelled (Yes / No)",
    "Is Renewal (Quote) (Yes / No)", "Total Bound Premium", "Retention", "Binder Agg Limit", "Ratable Revenue",
    "Company Name", "GICS Code", "Industry Name", "N Employees", "Insurance Market (Quote)", "Insurance Program",
    "Network Sublimit", "Regulatory Defense Sublimit", "Media Liability Sublimit", "Pci Sublimit",
    "Crisis Management Sublimit", "Extortion Sublimit", "Business Interruption Sublimit",
    "Asset Restoration Sublimit", "Funds Transfer Sublimit", "Reputation Sublimit", "Bipd Third Party Sublimit",
    "Bipd First Party Sublimit", "Pollution Sublimit", "Computer Replacement Sublimit", "Service Fraud Sublimit",
    "Quote Company State", "Company Full Address", "Quote Company City", "Quote Company ZIP", "Lifecycle State",
    "Quote Currency Code", "Lloyd's UMR Code", "Lloyd's Risk Share",
]
"""UK deliverable headers, as sent. Same as the UK Looker download."""

_CANADA_HEADERS = [
    "Coalition Policy Number", "Coalition Policy Number", "Effective Date", "Coverage End Date",
    "Was Policy Cancelled (Yes / No)", "Is Renewal (Yes / No)", "Total Bound Premium", "Retention",
    "Bound Agg Limit", "Ratable Revenue", "Company Name", "GICS Code", "Industry Name", "N Employees",
    "Insurance Market", "Insurance Program", "Network Sublimit", "Regulatory Defense Sublimit",
    "Media Liability Sublimit", "Pci Sublimit", "Crisis Management Sublimit", "Extortion Sublimit",
    "Business Interruption Sublimit", "Asset Restoration Sublimit", "Funds Transfer Sublimit",
    "Reputation Sublimit", "Bipd Third Party Sublimit", "Bipd First Party Sublimit", "Pollution Sublimit",
    "Computer Replacement Sublimit", "Service Fraud Sublimit", "Quote Company Address Complete",
    "Quote Company City", "Quote Company Zip", "Quote Status", "Quote Original Currency", "Lloyds Umr Code",
    "Lloyds Risk Share", "Quote Company State",
]
"""Canada deliverable headers, as sent, including the leading duplicate policy number column."""

_SAME_FIELD = [
    {"Coalition Policy Number", "Quote Coalition Policy Number"},
    {"Effective Date", "Quote Effective Date Date"},
    {"Coverage End Date", "Policy Coverage End Date Date"},
    {"Is Renewal (Yes / No)", "Is Renewal (Quote) (Yes / No)"},
    {"Total Bound Premium", "Bound Premium Incl Endorsements"},
    {"Retention", "Default Retention"},
    {"Bound Agg Limit", "Binder Agg Limit"},
    {"Ratable Revenue", "Company Ratable Revenue"},
    {"Company Name", "Quote Company Name (Quote)"},
    {"Industry Name", "Industry Display Name"},
    {"N Employees", "Number of Employees"},
    {"Insurance Market", "Insurance Market (Quote)"},
    {"Insurance Program", "Quote Insurance Program"},
    {"Company Full Address", "Quote Company Address Complete"},
    {"Quote Company ZIP", "Quote Company Zip"},
    {"Lifecycle State", "Quote Status"},
    {"Quote Currency Code", "Quote Original Currency"},
    {"Lloyd's UMR Code", "Lloyds Umr Code"},
    {"Lloyd's Risk Share", "Lloyds Risk Share"},
]
"""Header spellings seen for the same field across the Looker looks and the deliverables. Columns are
matched by name, never position: the Sept 2026 UK look came back in a different column order than August's."""


@dataclass(frozen=True)
class RegionSpec:
    name: str
    umr_24: str
    umr_25: str
    sheet_24: str
    sheet_25: str
    output_headers: list[str]
    duplicate_key: bool = False
    """Canada sends the policy number twice, as the first two columns"""

    @property
    def field_headers(self) -> list[str]:
        """deliverable headers without the duplicated key, one per Looker column"""
        return self.output_headers[int(self.duplicate_key):]

    @property
    def umrs(self) -> tuple[str, str]:
        return self.umr_24, self.umr_25


UK = RegionSpec("UK", "B174010161SS24", "B174010161SS25", "UK 24", "UK 25", _UK_HEADERS)
CANADA = RegionSpec(
    "Canada", "B174010160SS24", "B174010160SS25", "Canada 24", "Canada 25", _CANADA_HEADERS, duplicate_key=True
)
REGIONS = (UK, CANADA)


@dataclass
class RegionResult:
    spec: RegionSpec
    file_24: pd.DataFrame
    file_25: pd.DataFrame
    from_old_24: int
    from_old_25: int
    from_looker: int
    umr_changed_by_carry_forward: int
    """rows where Looker's UMR differs from the UMR we carried forward"""
    dropped_from_old: int
    """policies in last month's files that are not in the new download"""
    unexpected_umrs: dict[str, int] = field(default_factory=dict)
    """UMRs other than the region's 24/25 codes; these rows land in the 25 file"""

    def summary(self) -> dict:
        return {
            "region": self.spec.name,
            "files": {self.spec.umr_24: len(self.file_24), self.spec.umr_25: len(self.file_25)},
            "from_old_24": self.from_old_24,
            "from_old_25": self.from_old_25,
            "from_looker": self.from_looker,
            "umr_changed_by_carry_forward": self.umr_changed_by_carry_forward,
            "dropped_from_old": self.dropped_from_old,
            "unexpected_umrs": self.unexpected_umrs,
        }


def read_frame(file: str | Path | BinaryIO, filename: str | None = None) -> pd.DataFrame:
    """reads a Looker download or a previously sent deliverable (xlsx or csv)"""
    name = (filename or str(file)).lower()
    df = pd.read_csv(file) if name.endswith(".csv") else pd.read_excel(file, engine="calamine")
    return _drop_row_numbers(df)


def _drop_row_numbers(df: pd.DataFrame) -> pd.DataFrame:
    """Looker downloads lead with an unnamed 1..N row-number column that the template never pasted"""
    first = df.columns[0] if len(df.columns) else None
    if first is None or not str(first).startswith("Unnamed"):
        return df
    if (df[first] == range(1, len(df) + 1)).all():
        return df.drop(columns=first)
    return df


def _umr_column(df: pd.DataFrame, label: str) -> str:
    matches = [c for c in df.columns if "umr" in str(c).lower()]
    if len(matches) != 1:
        raise ValueError(f"{label}: expected one UMR column, found {matches or 'none'}.")
    return matches[0]


def _check_region(umrs: pd.Series, spec: RegionSpec, label: str) -> None:
    """UK and Canada downloads have the same column count, so a swapped upload is caught by its UMRs instead"""
    prefix = spec.umr_24[:-4]  # `B174010161` (UK) / `B174010160` (Canada)
    values = umrs.dropna().astype(str)
    if len(values) and not values.str.startswith(prefix).mean() > 0.5:
        found = ", ".join(values.value_counts().index[:3])
        raise ValueError(f"{label} doesn't look like a {spec.name} file: expected {prefix}… UMRs, found {found}.")


def _umr_lookup(old: pd.DataFrame, label: str, spec: RegionSpec) -> pd.Series:
    """policy number -> UMR, first hit wins like the template's INDEX/MATCH"""
    key = old.columns[0]
    umrs = old.drop_duplicates(key).set_index(key)[_umr_column(old, label)]
    _check_region(umrs, spec, label)
    return umrs


def _align_columns(new: pd.DataFrame, spec: RegionSpec) -> pd.DataFrame:
    """renames the Looker headers to the deliverable's and puts them in the deliverable's order"""
    def spellings(header: str) -> set[str]:
        return next((group for group in _SAME_FIELD if header in group), {header})

    looker = [str(c) for c in new.columns]
    picked, missing = [], []
    for header in spec.field_headers:
        hits = [c for c in looker if c in spellings(header)]
        (picked if len(hits) == 1 else missing).append(hits[0] if len(hits) == 1 else header)
    extra = [c for c in looker if c not in picked]
    if missing or extra:
        raise ValueError(
            f"{spec.name} Looker download columns don't match the deliverable. "
            f"Missing: {missing or 'none'}. Unrecognised: {extra or 'none'}."
        )
    aligned = new[picked].copy()
    aligned.columns = spec.field_headers
    return aligned


def _clean_gics(values: pd.Series) -> pd.Series:
    """GICS codes are sent as text; a csv download would read them as numbers"""
    return values.map(lambda v: str(int(v)) if isinstance(v, (int, float)) and not pd.isna(v) else v)


def _as_datetime(value):
    """xlsx downloads already hold dates; a csv download holds date strings"""
    if isinstance(value, str):
        try:
            return pd.Timestamp(value)
        except ValueError:
            return value
    return value


def build_region(new: pd.DataFrame, old_24: pd.DataFrame, old_25: pd.DataFrame, spec: RegionSpec) -> RegionResult:
    """applies the template's carry-forward logic to one region's Looker download

    :param new: this month's Looker download for the region (UK All / Canada All)
    :param old_24: last month's `...SS24` deliverable for the region
    :param old_25: last month's `...SS25` deliverable for the region
    :param spec: `UK` or `CANADA`
    """
    new = _align_columns(new, spec).reset_index(drop=True)
    key = new[new.columns[0]]
    looker_umr = new[_umr_column(new, f"{spec.name} Looker download")]
    _check_region(looker_umr, spec, f"{spec.name} Looker download")

    in_24 = key.map(_umr_lookup(old_24, f"Last month's {spec.umr_24}", spec))
    in_25 = key.map(_umr_lookup(old_25, f"Last month's {spec.umr_25}", spec))
    proposed = in_24.fillna(in_25).fillna(looker_umr)

    out = new.copy()
    out[looker_umr.name] = proposed
    with pd.option_context("future.no_silent_downcasting", True):
        out = out.fillna(0).infer_objects()
    if spec.duplicate_key:
        out.insert(0, "__duplicate_key__", out[out.columns[0]])
        out.columns = spec.output_headers

    for col in DATE_COLUMNS:
        out[col] = out[col].map(_as_datetime)
    out["GICS Code"] = _clean_gics(out["GICS Code"])

    is_24 = (proposed == spec.umr_24).to_numpy()
    old_keys = set(old_24[old_24.columns[0]]) | set(old_25[old_25.columns[0]])
    unexpected = proposed[~proposed.isin(spec.umrs)].fillna("(blank)").value_counts()

    return RegionResult(
        spec=spec,
        file_24=out[is_24].reset_index(drop=True),
        file_25=out[~is_24].reset_index(drop=True),
        from_old_24=int(in_24.notna().sum()),
        from_old_25=int((in_24.isna() & in_25.notna()).sum()),
        from_looker=int((in_24.isna() & in_25.isna()).sum()),
        umr_changed_by_carry_forward=int((proposed != looker_umr).sum()),
        dropped_from_old=len(old_keys - set(key)),
        unexpected_umrs={str(k): int(v) for k, v in unexpected.items()},
    )


def deliverable_name(umr: str, stamp: str) -> str:
    """matches the Looker-style names we've been sending, like `B174010160SS24 Risk BDX 2026-09-04T1148.xlsx`"""
    return f"{umr} Risk BDX {stamp}.xlsx"


def write_deliverable(df: pd.DataFrame, path: Path, sheet: str) -> Path:
    """writes one deliverable; the only styling on the sent files is the date format"""
    wb = Workbook(write_only=True)
    ws = wb.create_sheet(sheet)
    ws.append(list(df.columns))
    date_positions = {i for i, c in enumerate(df.columns) if c in DATE_COLUMNS}
    for row in df.itertuples(index=False, name=None):
        cells = []
        for i, value in enumerate(row):
            if i in date_positions and isinstance(value, pd.Timestamp):
                cell = WriteOnlyCell(ws, value=value.to_pydatetime())
                cell.number_format = DATE_FORMAT
                cells.append(cell)
            else:
                cells.append(value.item() if hasattr(value, "item") else value)
        ws.append(cells)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
