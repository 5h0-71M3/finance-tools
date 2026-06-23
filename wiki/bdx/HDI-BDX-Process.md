# HDI BDX Process

# Overview

This page describes how to build the monthly **HDI** BDX file by hand in Excel, without running the
Python script. The line of business is **HDI Canada** (cyber), reported under the subsidiary entity
**Coalition Insurance Solutions Canada Inc.** (`CANADA`). HDI is reported on the **Day 10** cadence.

The starting point is the HDI Canada Account Current report pulled from NetSuite. A handful of
supporting reports are merged in for coverage tie-out and (where applicable) industry/endorsement
lookups. Once everything is joined and formatted, the file is built in Excel and sent as a CSV.

> **Note:** HDI is a **Canada** book, so the US-specific rules do not apply. Validation uses the
> generic **"Basic"** validation (not the US validation). That means there is **no TRIA check, no
> earned/unearned check, and no Surplus 3.0 requirement** for HDI, and the **US 5-digit zip-code
> rule does not apply** (Canadian postal codes are alphanumeric).

---

# Sources

Below are the current reports required to complete the HDI BDX file.

## NetSuite

- **HDI Canada Account Current** (`HDICanadaAccountCurrent`) — the main BDX file. Pull from the
  production Account Current / Day 10 folder.
- **Limits Report** (NetSuite saved search) — report used for the coverage/limit columns:
  https://5118830.app.netsuite.com/app/common/search/searchresults.nl?searchid=8180

> **Note:** the primary report is the production saved search **`HDICanadaAccountCurrent`**, pulled
> from the production Account Current / Day 10 folder — **not** from Downloads. Use the production
> saved search; link TBD.

> **Note:** NetSuite saved searches are typically set to filter `Modified Date` within the previous
> day. Edit the search, remove that filter, go to Preview, then Run before exporting.

## Looker Reports

- **Industries Report** (Looker) — used for industry codes and policyholder information
  (`Employee Count`, `Attachment Point`):
  https://thecoalitionworkshop.looker.com/looks/4136?toggle=dat,vis
- **Endorsement Report** (Looker) — used to create the package keys:
  https://thecoalitionworkshop.looker.com/looks/3073

> **Note:** the Looker lookups were validated against the US/Vantage book. Their applicability to the
> HDI Canada book is not confirmed — see [Current Pending / Known Gaps](#current-pending--known-gaps).

## Other

- **OTC Commission Rate Google Sheet** (the "OTC sheet", maintained by Emily + the OTC team) — the
  source of truth for HDI's Coalition Commission % and brokerage fee:
  https://docs.google.com/spreadsheets/d/1yHG90_XFwbneIrGhwgpDMNjelcn2BK90j36lu5BEijo/edit?gid=1587427731#gid=1587427731

---

# Reports

This section covers every report that must be pulled, joined, or renamed into the HDI file.

## HDI Canada Account Current (primary)

- **Source system:** NetSuite, saved search `HDICanadaAccountCurrent`.
- **Used for:** the main BDX file — one row per transaction, carrying premium, commission, policy,
  and policyholder fields.
- **Notes:** pull from the production Account Current / Day 10 folder (not Downloads). Remove the
  `Modified Date` filter, Preview, then Run before exporting (see Sources note).

## Limits Report (coverage tie-out)

- **Source system:** NetSuite, `searchid=8180`.
- **Used for:** tying out and formatting the coverage/limit columns consistently. NetSuite returns
  coverages at the aggregate transaction level, so they must be scaled by the quota share (see
  Formatting). Doing the coverage formatting once on the Limits Report and reusing it as a source of
  truth is recommended.
- **Join key:** `Transaction ID`.
- **Columns pulled:** the coverage/limit columns listed in [Coverage / limit field list]
  (#coverage--limit-field-list), including the TBP basis `Total Bound Premium`, the base limit
  `Aggregate Total Limit`, and `SIR / Attachment Point`.

## Industries Report (Looker) — as applicable

- **Source system:** Looker, `looks/4136`.
- **Used for:** industry codes and policyholder information.
- **Join key:** `Transaction ID` (use `VLOOKUP` / `XLOOKUP` / `INDEX-MATCH`).
- **Columns pulled / renamed:**
  - `Transaction ID` — for the lookup.
  - `Quote N Employees` → `Employee Count` in the BDX.
  - `Excess Attachment Point` → `Attachment Point` in the BDX.
- **Notes:** if there are duplicates in the Industries Report, drop the duplicated rows. The Looker
  report will lose data if a policy has been soft-deleted or cancelled. `Attachment Point` should
  follow the same steps as Coverage / limit formatting. **Applicability to the Canada book is not
  confirmed — see Known Gaps.**

## Endorsement Report (Looker) — as applicable

- **Source system:** Looker, `looks/3073`.
- **Used for:** deriving the `Package Keys`.
- **Join key:** `Transaction ID`.
- **Notes:** package keys are a JSON payload and are currently hard to extract by hand.
  **Applicability to the Canada book is not confirmed — see Known Gaps.**

---

# Formatting

These are the by-hand steps in Excel. They are written at the level of *what* transformation is
needed, not Excel mechanics.

1. **Date format.** Format the date columns to `m/d/yyyy h:mm:ss` (Python `%m/%d/%Y %-H:%M:%S`). For
   example, `3/31/2026` becomes `3/31/2026 0:00:00`. Typical date columns: `Date Created`,
   `Policy Effective Date`, `Policy Expiration Date`, `Transaction Effective Date`,
   `Transaction Effective (Bind) Date`, `Account Current Month End`, `Retroactive Short Date`.

2. **Skip the US zip-code rule.** HDI is a Canada book, so the US 5-digit leading-zero zip rule does
   **not** apply. Canadian postal codes are alphanumeric — leave them as-is.

3. **Percentage fields.** Format `HDI Quota Share %` and `Coalition Commission %` so they show two
   decimal places with a trailing `%` sign. For example, `0.321` becomes `32.10%`.

4. **Coverage / limit fields.** For every coverage column in the list below:
   - (a) Coalesce empty cells to `0`.
   - (b) Make each value an integer (no decimals): `10000.0` becomes `10000`.
   - (c) If coverages are pulled at the aggregate transaction level from NetSuite, multiply each by
     `HDI Quota Share %`.
   - (d) Align each coverage's sign to the sign of `Total Bound Premium`. If TBP is positive, the
     coverages must be positive; if TBP is negative, the coverages must be negative. A `0` base
     limit (`Aggregate Total Limit`) is acceptable.

   Recommended: do this once on the Limits Report and use it as the source of truth, then multiply
   by the quota share.

5. **Retro Short Date.** If `Retro Short Date` holds the `1900-01-00` value, blank it out. The 1970
   value loads fine; only `1900-01-00` breaks the load.

6. **Sanity-check the derived premium/commission columns.** These are the relationships the script's
   Basic validation enforces (tolerance ±0.02). Confirm each by hand:
   - `HDI Bound Premium` = `Total Bound Premium` × `HDI Quota Share %`
     *(validate_carrier_bound_premium)*
   - `HDI Net Premium` = (`Total Bound Premium` × `HDI Quota Share %`) × (1 − `Coalition Commission %`)
     *(validate_carrier_net_premium)*
   - `HDI $ Commission to Coalition` = `HDI Bound Premium` × `Coalition Commission %`
     *(validate_carrier_commission_to_coalition)*
   - **Limit signature** matches the `Total Bound Premium` sign (a `0` base limit is fine)
     *(validate_limit_signature_matches_tbp)*
   - `Transaction ID` must not be blank / `nan` *(transaction_id_is_nan)*

7. **Confirm the Coalition Commission % manually.** There is **no** automatic commission-rate check
   defined for HDI. Confirm the `Coalition Commission %` by hand against the OTC sheet (see Sources).
   Do not assume a rate.

8. **Save-as note.** The file is built in Excel but **sent as CSV**. Use `Save As` → CSV from the
   Excel file so the formatting (the `%` signs, dates, integers) is preserved. Do **not** reopen the
   CSV and resave, or you will lose the formatting.

## Coverage / limit field list

The coverage formatting rule (step 4) applies to these fields:

```
Network and Information Security
Regulatory Fines and Penalties
Multimedia Content
PCI Fines and Assessments
Breach Response
Breach Response Costs
Crisis Management and Public Relationship
Cyber Extortion
Business Interruption And Extra Expense
Digital Asset Restoration
Funds Transfer Fraud
Reputation Repair
BI/PD - Third Party
BI/PD - First Party
Pollution
Systems Integrity Restoration
Computer Replacement
Technology E&O
Service Fraud
Reputational Harm Loss
Proof of Loss Preparation Expenses
Invoice Manipulation Sublimit
Phising Sublimit
Funds Transfer Liability Sublimit
Criminal Reward Sublimit
Court Attendance Sublimit
MPL Sublimit
Aggregate Total Limit
Total Limit
Vantage Limit of Liability
SIR / Attachment Point
Breach Response Separate Limit
DBI Security Failure
DBI Voluntary Shutdown
DBI Systems Failure
Contingent Business Interruption (CBI)
CBI Security Failure
CBI System Failure
CBI Voluntary Shutdown
CBI Non IT Security Failure
CBI Non IT System Failure
Missed Bid
Corrective Action Plan
Enhanced Privacy
Per Event Limit
Non-IT Vendor CBI
Attachment Point
```

---

# Renames and Deletions

## Remove columns

Remove the following columns if they are in the report:

1. `Quote Coalition Policy Number`
2. `Internal ID.1`
3. `Reputational Harm Loss.1`

## Final column renames

- `SIR / Attachment Point` → `SIR`
- `Run-Off` → `Run Off [Y/N]`
- `Run-Off Start Date` → `Run Off Start Date`
- `Run-Off End Date` → `Run Off End Date`

> **Note:** the HDI master uses its own headers for the carrier-derived fields. The quota share field
> is `HDI Quota Share %` in the report and is referred to as `HDI Quota Share` in the master. The
> commission-to-coalition field maps to the master header `HDI % Commission To Coalition`. `External
> ID` is the external identifier used to tie records.

---

# Current Pending / Known Gaps

- **Looker lookups for the Canada book.** The Industries Report (`looks/4136`) and Endorsement Report
  (`looks/3073`), and their join on `Transaction ID`, were validated against the US/Vantage book.
  Whether they populate correctly for the HDI Canada book (and whether `Employee Count` /
  `Attachment Point` / `Package Keys` are required for HDI) has not been confirmed. Validate as a
  group before relying on them.
- **Package Keys.** As with other carriers, there is currently no clear way for an analyst to extract
  the `Package Keys` from the Endorsement Report by hand — they are a JSON payload. Proposed interim
  approach: pull and save them in a shared folder, or use the script to pull `Package Key` into the
  Policy List file.
- **Account Current saved-search URL.** The exact NetSuite URL for `HDICanadaAccountCurrent` is not
  documented here. Reference the production saved search by name until the link is added.
- **Coalition Commission %.** There is no auto-check for HDI's commission rate. The analyst must
  confirm `Coalition Commission %` against the OTC sheet each cycle; the rate is not hard-coded here.
