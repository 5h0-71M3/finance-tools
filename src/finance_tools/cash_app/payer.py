"""Resolve the name(s) in a bank ``Description`` to real AR entities.

A bank description may name the **agency** (the broker) and/or the **insured**
(the policyholder). Either is enough to identify the invoice, so we resolve the
description against *both* dimensions independently and let the pipeline key on
whichever tied. A name "ties" when its best fuzzy score against that dimension's
entities clears a threshold — i.e. it corresponds to a *real* agency/insured,
not merely the closest of many.

The design is deliberately open for extension (SOLID): a dimension is just a
:class:`MatchDimension` describing which AR column holds its entity and how to
clean it. Adding, say, a "policy number" dimension is one entry in
:data:`DIMENSIONS`; indexing, resolution, keying, and matching all pick it up
unchanged. Scoring reuses the primitives validated in
:mod:`~finance_tools.cash_app.disambiguate` (payer extraction, stopword
tokenization, prefix-aware token similarity).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from finance_tools.cash_app.disambiguate import (
    _score,
    agency_name,
    extract_payer,
    normalize_tokens,
)

#: A name ties to an entity when its best score clears this bar.
DEFAULT_THRESHOLD = 0.6

#: Token-prefix length used to bucket entities for candidate generation. A name
#: only scores against entities that share a token *prefix* with it — the prefix
#: (not the whole token) so the bank's truncations still find their entity
#: ("VANCOUV" and "VANCOUVER" share "VANC"). Shrinks a full-master scan from
#: ~19K comparisons to a few hundred without changing which entity wins.
PREFIX_LEN = 4


def _prefixes(tokens) -> set[str]:
    return {t[:PREFIX_LEN] for t in tokens if t}


def _clean_insured(value: str) -> str:
    """Canonical insured name — just whitespace-folded (no system suffix)."""
    return " ".join(str(value).split())


@dataclass(frozen=True)
class MatchDimension:
    """One way to identify a receipt's invoice (agency, insured, ...).

    :param name: dimension label, also the key namespace (see
        :func:`~finance_tools.cash_app.keys.build_match_key`).
    :param ar_column: the open-AR column holding this dimension's entity.
    :param clean: fold a raw AR value to the canonical form used everywhere
        (the key seed, the index, the scoring tokens).
    """

    name: str
    ar_column: str
    clean: Callable[[str], str]

    def value_of(self, raw: object) -> str | None:
        """Canonical entity value for one AR cell, or ``None`` if blank."""
        if not isinstance(raw, str) or not raw.strip():
            return None
        cleaned = self.clean(raw)
        return cleaned or None


#: The active dimensions, in priority order. Extend here to add a new one.
AGENCY = MatchDimension("agency", "Name", agency_name)
INSURED = MatchDimension("insured", "Insured Name", _clean_insured)
DIMENSIONS: list[MatchDimension] = [AGENCY, INSURED]


@dataclass(frozen=True)
class Entity:
    """One distinct entity in a dimension's index.

    :param dimension: the owning dimension's name.
    :param value: canonical entity name (fed verbatim into the key seed).
    :param tokens: content tokens of ``value`` (stopwords dropped), precomputed.
    """

    dimension: str
    value: str
    tokens: tuple[str, ...]


class EntityIndex:
    """Distinct entities for one dimension, bucketed by token prefix.

    Iterable and sized (so callers can treat it like the entity list), but the
    point is :meth:`candidates`: given a description's tokens it returns only the
    entities worth scoring (those sharing a token prefix), so a resolve touches a
    few hundred names instead of all ~19K.
    """

    def __init__(self, entities: list[Entity]) -> None:
        self.entities = entities
        self._by_prefix: dict[str, list[Entity]] = {}
        for entity in entities:
            for prefix in _prefixes(entity.tokens):
                self._by_prefix.setdefault(prefix, []).append(entity)

    def __iter__(self):
        return iter(self.entities)

    def __len__(self) -> int:
        return len(self.entities)

    def candidates(self, tokens) -> list[Entity]:
        """Entities sharing at least one token prefix with ``tokens`` (deduped)."""
        seen: dict[int, Entity] = {}
        for prefix in _prefixes(tokens):
            for entity in self._by_prefix.get(prefix, ()):
                seen[id(entity)] = entity
        return list(seen.values())


def build_index(ar: pd.DataFrame, dimension: MatchDimension) -> EntityIndex:
    """Build the distinct-entity index for ``dimension`` from the open-AR report.

    Dedups the dimension's column to one :class:`Entity` per canonical value
    (the first spelling wins), skipping values that tokenize to nothing (all
    stopwords) and so carry no signal to match on.
    """
    if dimension.ar_column not in ar.columns:
        return EntityIndex([])
    seen: dict[str, Entity] = {}
    for raw in ar[dimension.ar_column].dropna().unique():
        value = dimension.value_of(raw)
        if value is None:
            continue
        tokens = tuple(normalize_tokens(value))
        if not tokens:
            continue
        seen.setdefault(value, Entity(dimension.name, value, tokens))
    return EntityIndex(list(seen.values()))


def payer_tokens(description: str) -> list[str]:
    """Content tokens of the payer named in a bank description (ACH form aware)."""
    return normalize_tokens(extract_payer(description))


def score_tokens(tokens: list[str], name: str) -> float:
    """Score already-tokenized payer text against a single entity ``name``."""
    name_tokens = normalize_tokens(name)
    return _score(tokens, name_tokens) if tokens and name_tokens else 0.0


def resolve_entity(
    description: str,
    index: EntityIndex,
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> tuple[Entity | None, float]:
    """Resolve a bank description to the best-scoring entity in ``index``.

    Only entities sharing a token prefix with the description are scored (see
    :class:`EntityIndex`), which is what makes a full-master resolve fast.

    :returns: ``(entity, score)`` when the top score clears ``threshold`` (the
        name ties to a real entity), else ``(None, best_score)`` so the caller
        can leave the receipt unkeyed on this dimension.
    """
    tokens = payer_tokens(description)
    if not tokens or not len(index):
        return None, 0.0

    best, best_score = None, 0.0
    for entity in index.candidates(tokens):
        score = _score(tokens, list(entity.tokens))
        if score > best_score:
            best, best_score = entity, score
    if best is not None and best_score >= threshold:
        return best, best_score
    return None, best_score
