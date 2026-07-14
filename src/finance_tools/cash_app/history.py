"""A learned, version-controlled ledger of who pays for whom.

We have no authoritative table of which agency pays on behalf of which other
agency, so we infer one from the runs themselves. The *exact* tier is ground
truth: when an amount is unique within a subsidiary/currency exactly one open
invoice can have cleared, so if the payer named on that receipt is a *different*
agency than the invoice's customer, that is a real, observed "A pays for B"
relationship. Each such observation is counted here.

Over successive runs this accumulates a ``payer -> {customer: count}`` graph
that a later (Phase 2) tier can trust to auto-apply cross-agency receipts. It is
stored as JSON inside the package so it is committed and shared, not regenerated
per machine. Keys are the cleaned agency names
(:func:`~finance_tools.cash_app.disambiguate.agency_name`) so entries stay
human-readable and stable across the two documents' naming quirks.
"""
from __future__ import annotations

import json
from pathlib import Path

#: Committed ledger location: alongside the cash_app source so it is shared.
DEFAULT_LEDGER_PATH = Path(__file__).with_name("payer_history.json")


class PayerLedger:
    """Counts of observed ``payer_agency -> customer_agency`` payments."""

    def __init__(
        self,
        data: dict[str, dict[str, int]] | None = None,
        *,
        path: Path = DEFAULT_LEDGER_PATH,
    ) -> None:
        self._path = Path(path)
        self._data: dict[str, dict[str, int]] = data or {}

    @classmethod
    def load(cls, path: Path = DEFAULT_LEDGER_PATH) -> "PayerLedger":
        """Load the ledger from ``path``; empty if the file does not exist yet."""
        path = Path(path)
        data = json.loads(path.read_text()) if path.exists() else {}
        return cls(data=data, path=path)

    def observe(self, payer_agency: str, customer_agency: str) -> None:
        """Record one observed payment of ``payer_agency`` for ``customer_agency``."""
        row = self._data.setdefault(payer_agency, {})
        row[customer_agency] = row.get(customer_agency, 0) + 1

    def covered_customers(self, payer_agency: str) -> dict[str, int]:
        """Return ``{customer_agency: count}`` this payer has been seen paying for."""
        return dict(self._data.get(payer_agency, {}))

    def covers(self, payer_agency: str, customer_agency: str) -> bool:
        """Whether ``payer_agency`` has ever been observed paying ``customer_agency``."""
        return self._data.get(payer_agency, {}).get(customer_agency, 0) > 0

    def save(self) -> None:
        """Persist the ledger to its JSON file (sorted, for stable diffs)."""
        self._path.write_text(
            json.dumps(self._data, indent=2, sort_keys=True) + "\n"
        )