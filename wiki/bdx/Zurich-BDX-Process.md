# Zurich BDX Process

# Overview

This page describes how to build the monthly **Zurich** BDX file by hand in Excel, without running the Python script.

Zurich is our **MPL** book (Management / Professional Liability) — **not** the cyber book. The reported subsidiary entity is **Coalition, Inc** (US), and Zurich is reported on the **Day 10** cadence.

> **Note:** Zurich is the carrier with the thinnest automation in the codebase. There is **no Zurich-specific validation class** and **no Zurich record-level QA checks** (unlike Chaucer, Fortegra, HDI, and Hartford). Read `# Current Pending / Known Gaps` carefully — for Zurich you must eyeball the derivation formulas and coverage tie-outs by hand, because nothing checks them automatically.

The single most important difference from the cyber carriers: **Zurich is not pulled from a standalone NetSuite "Account Current" saved search.** Zurich is reported off the **MPL Master File**. See `# Reports`.

---

# Sources

Below are the current sources required to complete the Zurich BDX File.

## Primary source — MPL Master File

- **MPL Master File** — the file named `MasterFile-MPL`, on its `master` tab. This is the primary source for the Zurich BDX. There is no separate Zurich Account Current saved search.

The relevant columns on the `master` tab are:

- `Zurich Quota Share`
- `Reported - Zurich`
- `Reported - Zurich Date`
- `Zurich % Commission to Coalition` (commission header)

The "Zurich happy path" in the workflow is straightforward: for **US-subsidiary MPL rows with a positive `Zurich Quota Share`**, mark `Reported - Zurich` = `Yes` and stamp the **Day-10 report date** into `Reported - Zurich Date`. Those are the rows that belong in this month's BDX.

## NetSuite

- **Limits Report** (NetSuite saved search) — used to tie out and format the coverage / limit columns. The Vantage example uses `searchid=8180`:
  https://5118830.app.netsuite.com/app/common/search/searchresults.nl?searchid=8180

> **Note:** NetSuite saved searches are typically set to filter `Modified Date` within the previous day. Edit the search, remove that filter, go to Preview, then Run, before exporting.

## Looker

- **Industries Report** (Looker) — used by the cyber book for industry codes and policyholder info (`Quote N Employees` → `Employee Count`, `Excess Attachment Point` → `Attachment Point`, joined on `Transaction ID`):
  https://thecoalitionworkshop.looker.com/looks/4136?toggle=dat,vis
- **Endorsement Report** (Looker) — used by the cyber book to derive `Package Keys`:
  https://thecoalitionworkshop.looker.com/looks/3073

> **Note:** The Industries and Endorsement Looker lookups are part of the **cyber** book workflow. It is **not confirmed** that they apply to the MPL / Zurich book. Do not assume they do — see `# Current Pending / Known Gaps`.

## Other

- **OTC Commission Rate Google Sheet** (the "OTC sheet", maintained by Emily + the OTC team) — the source of truth for the Coalition Commission %:
  https://docs.google.com/spreadsheets/d/1yHG90_XFwbneIrGhwgpDMNjelcn2BK90j36lu5BEijo/edit?gid=1587427731#gid=1587427731

---

# Reports

## MPL Master File (primary)

- **Source system:** the `MasterFile-MPL` workbook, `master` tab.
- **Used for:** this is the spine of the Zurich BDX. Select the rows that are US-subsidiary (`Coalition, Inc`) MPL transactions with a positive `Zurich Quota Share`, mark `Reported - Zurich` = `Yes`, and stamp the Day-10 report date into `Reported - Zurich Date`.
- **Join key:** `Internal ID` (used to join the Limits Report and any other lookups back onto the master rows).
- **Key columns:** `Zurich Quota Share`, `Reported - Zurich`, `Reported - Zurich Date`, `Zurich % Commission to Coalition`.

## Limits Report (NetSuite)

- **Source system:** NetSuite saved search (Vantage uses `searchid=8180`).
- **Used for:** coverage / limit tie-out and formatting. Pulled coverages are at the aggregate transaction level, so they must be multiplied by the Zurich quota share and sign-aligned to `Total Bound Premium` (see `# Formatting`).
- **Join key:** `Internal ID`.

> **Note:** The standard Limits Report lists the **cyber** coverage columns (reproduced in `# Formatting` as a reference). MPL has its own coverage / limit fields, which are **not** the same list. Confirm the MPL coverage fields with the OTC / MPL team before relying on the cyber list — see `# Current Pending / Known Gaps`.

## Industries Report / Endorsement Report (Looker) — applicability unconfirmed

- **Source system:** Looker.
- **Used for (cyber book):** the Industries Report supplies `Employee Count` / `Attachment Point`; the Endorsement Report supplies `Package Keys`.
- **Join key (cyber book):** `Transaction ID`.

> **Note:** These two Looker lookups are documented here only because they are part of the cyber workflow. Whether they feed the MPL / Zurich file at all is **unconfirmed**. Do not pull or join them into the Zurich file until confirmed — see `# Current Pending / Known Gaps`.

---

# Formatting

These are the transformations the analyst performs by hand in Excel. Because there is no Zurich validation class, treat every step here as something you must verify manually.

1. **Select the Zurich rows.** On the `master` tab of `MasterFile-MPL`, filter to US-subsidiary (`Coalition, Inc`) MPL rows with a **positive `Zurich Quota Share`**. These are the BDX rows. Set `Reported - Zurich` = `Yes` and stamp the **Day-10 report date** into `Reported - Zurich Date`.

2. **Date format.** Format all date columns to `m/d/yyyy h:mm:ss` (Python `%m/%d/%Y %-H:%M:%S`). For example, `3/31/2026` → `3/31/2026 0:00:00`. Apply to the date columns present in the Zurich file (e.g. `Date Created`, `Policy Effective Date`, `Policy Expiration Date`, `Transaction Effective Date`, `Transaction Effective (Bind) Date`, `Account Current Month End`, and the Zurich report date).

3. **Zip code format (US — applies to Zurich).** `Insured Zip Code` and `Broker Zip Code` must be the full 5-digit code with leading zeros (e.g. `531` → `00531`). Zurich is a US book, so this applies.

4. **Percentage fields.** `Zurich Quota Share %`, `Coalition Commission %`, and any `Broker Commission %` must show two decimals with a trailing `%` (e.g. `0.321` → `32.10%`).

5. **Coverage / limit fields.** For each coverage / limit column:
   - empty cells coalesce to `0`;
   - values are integers, no decimals (`10000.0` → `10000`);
   - if coverages are pulled at the aggregate transaction level from NetSuite, multiply each by the Zurich quota share;
   - align each coverage's sign to the sign of `Total Bound Premium` (if TBP is negative, the coverages must be negative, and vice versa).

   > **Note:** It is cleaner to do the coalesce / integer / sign-align work once on the Limits Report and use it as the source of truth, then multiply by the quota share. **But:** the cyber limits list (below) is the cyber reference — MPL has its own coverage fields. Confirm the MPL field list before applying this blindly (see Known Gaps).

6. **Retro Short Date.** If `Retro Short Date` holds the `1900-01-00` value, blank it out — that value breaks the load. The 1970 value loads fine, so leave it.

7. **Confirm the commission rate manually.** There is **no** OTC commission-rate auto-check for Zurich. Confirm the Coalition Commission % by hand against the OTC sheet (link in Sources). Do not assume a rate.

8. **Save as CSV.** The file is built in Excel but **sent as CSV**. Use `Save As` → CSV directly from the Excel file so the text formatting (leading zeros, `%`, dates) is preserved. Do **not** reopen the CSV and resave, or you will lose the formatting.

## Manual sanity-check formulas (no automated check exists for Zurich)

Because there is no Zurich QA class, verify these relationships yourself (the cyber carriers' script tolerance is ±0.02):

- **Zurich Bound Premium** = `Total Bound Premium` × `Zurich Quota Share %`
- **Zurich Net Premium** = (`TBP` × `Quota Share`) × (1 − `Coalition Commission %`)
- **Zurich Commission to Coalition** = `Zurich Bound Premium` × `Coalition Commission %`
- **Net Premium** = `TBP` × (1 − `Coalition Commission %`)
- **Limit signature** must match the `Total Bound Premium` sign (a `0` base limit is fine).
- **Transaction ID** must not be blank / `nan`.
- **TRIA** (US): if `Total TRIA` is `0` then the Zurich TRIA must also be `0`, and vice versa.

## The limits (cyber reference list — confirm MPL equivalents)

The coverage formatting in step 5 applies to these columns for the cyber book. **For MPL, treat this as a reference only** and confirm the actual MPL coverage fields with the OTC / MPL team.

```
limits = (
    "Network and Information Security",
    "Regulatory Fines and Penalties",
    "Multimedia Content",
    "PCI Fines and Assessments",
    "Breach Response",
    "Breach Response Costs",
    "Crisis Management and Public Relationship",
    "Cyber Extortion",
    "Business Interruption And Extra Expense",
    "Digital Asset Restoration",
    "Funds Transfer Fraud",
    "Reputation Repair",
    "BI/PD - Third Party",
    "BI/PD - First Party",
    "Pollution",
    "Systems Integrity Restoration",
    "Computer Replacement",
    "Technology E&O",
    "Service Fraud",
    "Reputational Harm Loss",
    "Proof of Loss Preparation Expenses",
    "Invoice Manipulation Sublimit",
    "Phising Sublimit",
    "Funds Transfer Liability Sublimit",
    "Criminal Reward Sublimit",
    "Court Attendance Sublimit",
    "MPL Sublimit",
    "Aggregate Total Limit",
    "Total Limit",
    "Vantage Limit of Liability",
    "SIR / Attachment Point",
    "Breach Response Separate Limit",
    "DBI Security Failure",
    "DBI Voluntary Shutdown",
    "DBI Systems Failure",
    "Contingent Business Interruption (CBI)",
    "CBI Security Failure",
    "CBI System Failure",
    "CBI Voluntary Shutdown",
    "CBI Non IT Security Failure",
    "CBI Non IT System Failure",
    "Missed Bid",
    "Corrective Action Plan",
    "Enhanced Privacy",
    "Per Event Limit",
    "Non-IT Vendor CBI",
    "Attachment Point"
)
```

---

# Renames and Deletions

## Remove Columns

Remove the following columns if they are present in the file:

1. `Quote Coalition Policy Number`
2. `Internal ID.1`
3. `Reputational Harm Loss.1`

## Final Column Renames

- `SIR / Attachment Point` → `SIR`
- `Run-Off` → `Run Off [Y/N]`
- `Run-Off Start Date` → `Run Off Start Date`
- `Run-Off End Date` → `Run Off End Date`

---

# Current Pending / Known Gaps

This is the most important section for Zurich. It has the least code coverage of any carrier, so the manual process carries more risk here than elsewhere. Treat each item below as something you must confirm yourself.

## No automated per-record validation

There is **no Zurich-specific validation class and no Zurich record-level QA checks** in the codebase — unlike Chaucer, Fortegra, HDI, and Hartford, which each have automated per-record checks. For Zurich:

- Nothing verifies the derivation formulas automatically. **Eyeball them by hand** using the manual sanity-check formulas in `# Formatting` (Bound = TBP × Quota Share, Net Premium, Commission to Coalition, etc.).
- Nothing checks limit-sign alignment, blank `Transaction ID`, or TRIA consistency for Zurich. Verify these manually.
- When in doubt, fall back on the **general shared formatting rules** in `# Formatting`; there are no Zurich-specific overrides in code to lean on.

## No commission-rate auto-check

There is **no OTC commission-rate auto-check for Zurich**. The analyst must confirm the Coalition Commission % manually against the OTC sheet (link in Sources). Do not fabricate or assume a rate.

## MPL coverage / limit fields are not the cyber list

The limits list reproduced in `# Formatting` is the **cyber** book's coverage list. MPL (Management / Professional Liability) has its **own** coverage / limit fields, which differ. **Confirm the MPL coverage / limit field list with the OTC / MPL team** before applying the coverage formatting (coalesce, integer, quota-share multiply, sign-align) — do not assume the cyber columns are correct for Zurich.

## Looker lookups — applicability to MPL unconfirmed

The **Industries Report** and **Endorsement Report** Looker lookups are part of the **cyber** workflow. It is **not confirmed** whether either feeds the MPL / Zurich file:

- It is unknown whether MPL rows carry `Employee Count` / `Attachment Point` from the Industries Report.
- It is unknown whether MPL needs `Package Keys` from the Endorsement Report. (Even for cyber, package keys are a JSON payload that is hard to extract by hand.)

Confirm with the OTC / MPL team before pulling or joining either Looker report into the Zurich file.

## Source is the master file, not a saved search — link TBD

Zurich is reported off the `MasterFile-MPL` `master` tab rather than a dedicated NetSuite Account Current saved search. There is no per-carrier saved-search URL for Zurich.

> **Note:** Use the production `MasterFile-MPL` workbook; canonical link / location TBD. Confirm with the OTC / MPL team which copy of the master file is authoritative for the reporting month.
