# Fortegra BDX Process

# Overview

This page describes how to build the monthly **Fortegra** BDX file by hand in Excel, without running the Python script.

Fortegra is a US Surplus Lines cyber carrier. The business is written through the **Coalition, Inc** (US) subsidiary entity and reported on the **Day 10** cadence. Because Fortegra is a US cyber line, the US-specific formatting rules apply: zip-code formatting, coverage/limit formatting, and `Surplus 3.0`. Fortegra also has a set of "V2" premium-breakdown columns that must always be filled.

The file is built in Excel but **delivered as a CSV**. See the save-as note under General Formatting.

---

# Sources

Below are the current reports required to complete the Fortegra BDX file.

## NetSuite

- **Fortegra Account Current** (`FortegraAccountCurrent` saved search) - the main BDX file. Pulled from the production **Account Current / Day 10** folder.

  > **Note:** use the production saved search; link TBD.

  > **Note:** pull the report from the production Account Current / Day 10 folder, **not** from Downloads.

  > **Note:** the saved search is set to `Modified Date` within the previous day, so make sure to edit it and remove that filter, go to Preview, then Run, before exporting.

- **Limits Report** - report used for the limit/coverage columns. Used to tie out and format the coverage columns consistently.
  - https://5118830.app.netsuite.com/app/common/search/searchresults.nl?searchid=8180

## Looker Reports

- **Endorsement Report** - used to create the package keys.
  - https://thecoalitionworkshop.looker.com/looks/3073

- **Industries Report** - used for different industry codes and policyholder information.
  - https://thecoalitionworkshop.looker.com/looks/4136?toggle=dat,vis

## Google Sheets

- **OTC Commission Rate Google Sheet** (the "OTC sheet", maintained by Emily + the OTC team) - the source of truth for Fortegra's commission rate and brokerage fee.
  - https://docs.google.com/spreadsheets/d/1yHG90_XFwbneIrGhwgpDMNjelcn2BK90j36lu5BEijo/edit?gid=1587427731#gid=1587427731

---

# Reports

This section describes every report that must be pulled, joined, or renamed into the Fortegra file.

## Fortegra Account Current (primary)

The `FortegraAccountCurrent` NetSuite saved search is the spine of the BDX file. Pull it from the production Account Current / Day 10 folder (not Downloads), remove the `Modified Date` filter, Preview, then Run and export.

Note that Fortegra's column names are idiosyncratic and must be matched exactly:

- `Fortegra %` - the quota share (a percentage field). In the master this maps to `Fortegra Quota Share`.
- `Fortegra Bound Premium`, `Fortegra Net Premium` - carrier premium columns.
- `Coalition Commission $` - the carrier commission paid to Coalition (a dollar amount).
- `Coalition Commission%` - the commission percentage. **Note there is no space before the `%`.** This percentage is used for both the coalition and the carrier percent-commission calculations.
- `Total Limit` - the base limit.
- `Transaction ID` - the external identifier (also the join key for the Looker lookups).
- `Surplus 3.0` - a Yes/No flag (see Formatting).

The commission-to-coalition value rolls up under the master header `Fortegra % Commission To Coalition`.

### Fortegra "V2" premium-breakdown columns

The following six columns must **all** be filled (never blank) on the final file:

1. `Fortegra Bound Premium`
2. `Fortegra Net Premium`
3. `Fortegra Bound Premium Less TRIA`
4. `Coalition Commission $`
5. `Fortegra Bound Cyber Premium Less TRIA`
6. `Fortegra Net Cyber Premium`

## Limits Report (NetSuite)

Source: NetSuite (`searchid=8180`). Used to tie out and format the coverage/limit columns. Because coverages from NetSuite are at the aggregate transaction level, they must be multiplied by `Fortegra %` and aligned to the sign of `Total Bound Premium` (see Coverage Field Formatting). It is recommended to do the coverage formatting once on the Limits Report and use it as the source of truth.

Join key: this report ties out against the limit columns of the Account Current report (e.g. `Total Limit` and the coverage list).

## Industries Report (Looker)

Source: Looker (`looks/4136`). Used for industry codes and policyholder information. Join on `Transaction ID`. Keep the following fields:

- `Transaction ID` - for the lookup (`Vlookup`, `Xlookup`, `Index-Match`, etc.)
- `Quote N Employees` - renamed to `Employee Count` in the BDX.
- `Excess Attachment Point` - renamed to `Attachment Point` in the BDX.

If there are any duplicates in the Industries Report, drop the duplicated rows. Note that the Looker report will lose data if a policy has been soft-deleted or cancelled. `Attachment Point` should follow the Coverage Field Formatting steps.

## Endorsement Report (Looker)

Source: Looker (`looks/3073`). Used to derive `Package Keys`, joined on `Transaction ID`. Package keys are a JSON payload and are currently hard to extract by hand - see Current Pending / Known Gaps.

---

# Formatting

These are the by-hand transformations the analyst applies in Excel.

## Carrier Specific

### Date Format

The following date fields must be formatted to `m/d/yyyy h:mm:ss` (Python strftime `%m/%d/%Y %-H:%M:%S`). For example, `3/31/2026` becomes `3/31/2026 0:00:00`.

1. `Date Created`
2. `Policy Effective Date`
3. `Policy Expiration Date`
4. `Transaction Effective Date`
5. `Transaction Effective (Bind) Date`
6. `Account Current Month End`
7. `Retroactive Short Date`

### Zip Code Formatting

Fortegra is a US carrier, so the following fields must be a full 5-digit code with leading zeros. For example, `531` becomes `00531`.

1. `Insured Zip Code`
2. `Broker Zip Code`

### Percentage Field Formatting

The following fields must show two decimal places with a trailing `%`. For example, `0.321` becomes `32.10%`.

1. `Fortegra %` (quota share)
2. `Coalition Commission%` (note: no space before the `%`)

### Commission Rate Check (vs the OTC Google Sheet)

Verify Fortegra's commission rate against the OTC Google Sheet (the `fortegra_commission_rate_matches_google_sheet` check). The OTC sheet rate for Fortegra is:

- **30.00%** for policies effective **before 1/1/2025**.
- **32.00%** effective **on/after 1/1/2025**.
- Brokerage fee of **1.25%** applies (on the post-1/1/2025 rate).

Confirm that `Coalition Commission%` matches the correct rate for each policy's effective date before continuing.

### Fortegra V2 Premium-Breakdown Columns

Confirm the six V2 columns are all filled (the `fortegra_v2_columns_are_blank` check fails if any are blank): `Fortegra Bound Premium`, `Fortegra Net Premium`, `Fortegra Bound Premium Less TRIA`, `Coalition Commission $`, `Fortegra Bound Cyber Premium Less TRIA`, `Fortegra Net Cyber Premium`. None of these may be left blank.

### Surplus 3.0

`Surplus 3.0` must be filled Yes/No and never left blank (the `surplus_3_0_filled` check).

### Premium and Commission Sanity Checks

Spot-check the derived premium relationships by hand (tolerance is ±0.02):

1. **Fortegra Bound Premium** = `Total Bound Premium` × `Fortegra %` (the `validate_carrier_bound_premium` check).
2. **Fortegra Net Premium** = (`Total Bound Premium` × `Fortegra %`) × (1 − `Coalition Commission%`) (the `validate_carrier_net_premium` check).
3. **Commission to Coalition** = `Fortegra Bound Premium` × `Coalition Commission%` (the `validate_carrier_commission_to_coalition` check). This rolls up under `Fortegra % Commission To Coalition`.
4. **Limit signature** must match the sign of `Total Bound Premium` (a 0 base limit is fine) (the `validate_limit_signature_matches_tbp` check).
5. **Transaction ID** must not be blank/`nan` (the `transaction_id_is_nan` check).

> **Note:** TRIA - since Fortegra is a US carrier, if `Total TRIA` is 0 the carrier TRIA must also be 0, and vice versa. The `Fortegra Bound Premium Less TRIA` and `Fortegra Bound Cyber Premium Less TRIA` columns reflect this.

### Industry Fields from Looker

Format the Industries Report pulled from Looker and join it on `Transaction ID`. Keep `Transaction ID` (lookup key), `Quote N Employees` (renamed to `Employee Count`), and `Excess Attachment Point` (renamed to `Attachment Point`). Drop any duplicate rows. `Attachment Point` follows Coverage Field Formatting.

### Retro Short Date Field

For dates, it is just the `1900-01-00` value that causes a load problem. The 1970 date works fine. If the `Retro Short Date` field has the `1900-01-00` value, erase it so it is blank.

## General Formatting

### Coverage Field Formatting

It is optional but recommended to use the Limits Report to tie and format the limits, as it allows reuse and checks. The coverage list this applies to is at the end of this section.

1. Values need to be filled. Empty cells coalesce to `0`.
2. Each cell must be an integer, with no decimals (`10000.0` becomes `10000`).
3. If the coverages are pulled directly from NetSuite, they are at the aggregate transaction level and must be multiplied by the quota share - specifically `Fortegra %`.
4. Binder edits and soft deletes do not always reverse the coverages correctly, so make sure each coverage is aligned with the premium column. Align each coverage to the sign of `Total Bound Premium`: if `Total Bound Premium` is positive, each coverage must be positive; if negative, each coverage must be negative.

> **Note:** This process of formatting and aligning each coverage is repeated for all carriers, which is why it is recommended to do this step once on the Limits Report and use it as a source of truth, multiplying by the quota share column.

### Save-As Note

> **Note:** the file gets saved as an Excel file but gets sent as a CSV. When you `Save As` a CSV from an Excel file, the formatting keeps shape. If you open the CSV file and resave, you will lose the formatting (leading zeros, `%`, dates) you need to keep.

### The limits

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

Remove the following columns if they are in the report:

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

The below items would be something to go over as a group on best next steps.

## Fortegra Account Current saved-search link

The production saved search name is `FortegraAccountCurrent`, pulled from the Account Current / Day 10 folder. The exact saved-search URL is not yet documented here.

> **Note:** use the production saved search; link TBD.

## Package Keys

It is currently unclear how an analyst can extract `Package Keys` from the Endorsement Report by hand. The Package Key is written as a JSON payload, so Excel may be limited here. In the meantime, the proposal is that this gets pulled and saved in a shared folder, or that the analyst uses the script to pull the `Package Key` into the Policy List file they have in hand. It is also uncertain whether package keys apply to Fortegra in the same way they do for Vantage - confirm with the group.

## Industries / Endorsement lookup applicability

The Industries Report (`Employee Count` / `Attachment Point` joined on `Transaction ID`) and the Endorsement Report (package keys) follow the same pattern as Vantage. Whether every one of these lookups is required for Fortegra has not been independently confirmed - flag for review rather than assume.
