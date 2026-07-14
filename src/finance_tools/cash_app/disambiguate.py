"""Pick the right invoice when an amount key matches several open invoices.

The deterministic match key (subsidiary + currency + amount) is not always
unique: many open invoices can share an amount within a subsidiary. For those
*ambiguous* receipts we fall back to the one extra signal the bank gives us, the
free-text ``Description``, and fuzzy-match the payer named there against each
candidate invoice's agency (``Name``).

Customer names never line up exactly between the two documents (the bank
truncates and abbreviates), so this is deliberately a *scored* tiebreaker, not
part of the exact-equality match key. It only commits to a candidate when one
clearly wins; anything borderline stays in review. Validated against the bank's
remittance answer key, the defaults resolve a chunk of the ambiguous set with no
wrong picks — precision is favored over recall on purpose, since a misapplied
payment is worse than one left for a human.
"""
from __future__ import annotations

import html
import re
from difflib import SequenceMatcher

import pandas as pd

#: Words that appear across most agency names and so don't help tell two
#: candidates apart. Dropped before scoring on both sides.
STOPWORDS = {
    "INSURANCE", "AGENCY", "AGENCIES", "SERVICES", "SERVICE", "GROUP", "INC",
    "LLC", "LTD", "THE", "COMPANY", "CO", "BROKERS", "BROKER", "BROKERAGE",
    "DBA", "AND", "OF", "SOLUTIONS",
}

#: ACH descriptions carry the payer as ``COMPANY NAME: X SEC CODE: ...``.
_COMPANY_NAME = re.compile(r"COMPANY NAME:\s*(.*?)\s*SEC CODE", re.IGNORECASE)
#: Agency names trail a ``" - AGENCIES-C-<uuid>"`` (or ACCOUNTS) system suffix.
_AGENCY_SUFFIX = re.compile(r"\s+-\s+(?:AGENCIES|ACCOUNTS)-C-.*$", re.IGNORECASE)

#: A candidate wins only if its score clears this bar AND beats the runner-up by
#: at least ``DEFAULT_MARGIN``. Tuned against the remittance answer key.
DEFAULT_THRESHOLD = 0.6
DEFAULT_MARGIN = 0.15


def extract_payer(description: str) -> str:
    """Pull the payer text out of a bank description (ACH form if present)."""
    text = html.unescape(str(description))
    match = _COMPANY_NAME.search(text)
    return match.group(1) if match else text


def normalize_tokens(text: str) -> list[str]:
    """Upper-case, strip punctuation, and drop stopwords -> content tokens."""
    text = html.unescape(str(text))
    text = re.sub(r"[^A-Za-z0-9 ]", " ", text).upper()
    return [t for t in text.split() if t and t not in STOPWORDS]


def agency_name(name: str) -> str:
    """Strip the ``" - AGENCIES-C-..."`` system suffix off an AR Name."""
    return _AGENCY_SUFFIX.sub("", str(name)).strip()


def _score(payer_tokens: list[str], candidate_tokens: list[str]) -> float:
    """Mean best-token similarity of the payer against a candidate agency.

    Each payer token scores its closest candidate token (a prefix match counts
    near-perfect, to tolerate the bank truncating names like
    ``"Insurance Offic"`` -> ``"Insurance Office of America"``).
    """
    if not payer_tokens or not candidate_tokens:
        return 0.0
    total = 0.0
    for p in payer_tokens:
        best = max(
            (SequenceMatcher(None, p, c).ratio() for c in candidate_tokens),
            default=0.0,
        )
        if any(c.startswith(p) or p.startswith(c) for c in candidate_tokens):
            best = max(best, 0.95)
        total += best
    return total / len(payer_tokens)


def disambiguate(
    description: str,
    candidates: pd.DataFrame,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    margin: float = DEFAULT_MARGIN,
) -> tuple[pd.Series | None, float]:
    """Choose the single best invoice for a receipt, or decline.

    :param description: the bank receipt's free-text description.
    :param candidates: the open invoices sharing this receipt's match key.
    :returns: ``(winning_invoice_row, score)`` when one candidate clearly wins,
        otherwise ``(None, best_score)`` so the receipt stays in review.
    """
    payer_tokens = normalize_tokens(extract_payer(description))
    if not payer_tokens:
        return None, 0.0

    scored = sorted(
        (
            (_score(payer_tokens, normalize_tokens(agency_name(row["Name"]))), idx)
            for idx, row in candidates.iterrows()
        ),
        reverse=True,
        key=lambda pair: pair[0],
    )
    best_score, best_idx = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    if best_score >= threshold and (best_score - runner_up) >= margin:
        return candidates.loc[best_idx], best_score
    return None, best_score
