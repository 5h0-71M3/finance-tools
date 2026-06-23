# Chaucer BDX Process

# Overview

This page describes how to build the monthly **Chaucer** BDX file by hand in Excel,
without running the pipeline script.

Chaucer is a **US Surplus Lines cyber** carrier. Premium is written through the
**Coalition, Inc** (US) subsidiary entity and reported on the **Day 10** cadence.
Chaucer takes a quota share of each policy, so most of the carrier-facing money columns
(`Chaucer Bound Premium`, `Chaucer Net Premium`, `Chaucer TRIA`) are derived from the
total policy values multiplied by Chaucer's share (`Chaucer %`).

The build is: pull the Chaucer Account Current report from NetSuite, format it per the
rules below, tie out the coverage/limit columns against the Limits Report, and verify
the commission rate against the OTC sheet by hand. The file is built in Excel and sent
as a CSV.

---

# Sources

Below are the current reports required to complete the Chaucer BDX File.

## NetSuite

- **`ChaucerAccountCurrent`** (Account Current saved search) - the main BDX File. Pull
  this from the production **Account Current / Day 10** folder. Do **not** use any copy
  saved in Downloads.

  > **Note:** use the production saved search; link TBD.

  > **Note:** the saved search is set to filter `Modified Date` within the previous day,
  > so make sure to edit it, remove that filter, go to Preview, then Run before exporting.

- [Limits Report](https://5118830.app.netsuite.com/app/common/search/searchresults.nl?searchid=8180) -
  report used for the limit columns. Use it as the single source of truth for the
  coverage/limit formatting (see Coverage Field Formatting).

## Looker Reports

- [Industries Report](https://thecoalitionworkshop.looker.com/looks/4136?toggle=dat,vis) -
  used for different industry codes and policyholder information (`Employee Count`,
  `Attachment Point`), joined on `Transaction ID`.
- [Endorsement Report](https://thecoalitionworkshop.looker.com/looks/3073) - used to
  create the package keys. (See Known Gaps - package keys are a JSON payload and are
  currently hard to extract by hand.)

## OTC / Commission

- [OTC Commission Rate Google Sheet](https://docs.google.com/spreadsheets/d/1yHG90_XFwbneIrGhwgpDMNjelcn2BK90j36lu5BEijo/edit?gid=1587427731#gid=1587427731) -
  source of truth for Chaucer's Coalition Commission % and brokerage fee. Because the
  automated commission-rate check is disabled for Chaucer (see Known Gaps), you must
  verify the rate against this sheet manually.

---

# Reports

This section covers the reports that get pulled, joined, and renamed into the Chaucer file.

## Chaucer Account Current (primary)

The `ChaucerAccountCurrent` saved search is the spine of the BDX file. Pull it from the
production Account Current / Day 10 folder (not Downloads). Key Chaucer-specific columns:

- `Chaucer %` - Chaucer's quota share (a percentage field). This is renamed to
  `Chaucer Quota Share` in the master file.
- `Total Gross Written Premium (GWP)` - the total bound premium (TBP) basis for Chaucer.
- `Chaucer Bound Premium`, `Chaucer Net Premium`, `Chaucer TRIA` - the carrier-level
  money columns, derived from GWP and `Chaucer %`.
- `Aggregate Total Limit` - the base limit for the limit-signature tie-out.
- `Transaction ID` - the external / transaction identifier (must not be blank).
- `Coalition Commission %`, `Surplus 3.0`.

## Limits Report (NetSuite)

Used to tie out and format the coverage/limit columns consistently. Because Chaucer
coverages are pulled at the aggregate transaction level, format the limits once on the
Limits Report and use it as the source of truth, then multiply each coverage by
`Chaucer %`. Join back to the Account Current report on `Transaction ID`. See Coverage
Field Formatting for the rule details and the full limits list.

## Industries Report (Looker)

Pulled from Looker and joined to the BDX on `Transaction ID` (`Vlookup`, `Xlookup`,
`Index-Match`, etc.). Keep the following fields:

- `Transaction ID` - for the lookup.
- `Quote N Employees` - renamed to `Employee Count` in the BDX.
- `Excess Attachment Point` - renamed to `Attachment Point` in the BDX.

If there are duplicates in the Industries Report, feel free to drop the duplicated rows.
Note that the Looker report will lose data if a policy has been soft deleted or cancelled.
`Attachment Point` should follow the same steps as Coverage Field Formatting.

## Endorsement Report (Looker)

Used to derive `Package Keys`. As with Vantage, the package keys are a JSON payload that
is hard to extract by hand - see Known Gaps.

---

# Formatting

Apply the following transformations by hand in Excel.

## Carrier Specific

1. **Date format** - convert the date columns to `m/d/yyyy h:mm:ss` (Python strftime
   `%m/%d/%Y %-H:%M:%S`). For example, `3/31/2026` becomes `3/31/2026 0:00:00`. Typical
   date columns: `Date Created`, `Policy Effective Date`, `Policy Expiration Date`,
   `Transaction Effective Date`, `Transaction Effective (Bind) Date`,
   `Account Current Month End`, `Retroactive Short Date`.

2. **Zip code format** - because Chaucer is a US carrier, format `Insured Zip Code` and
   `Broker Zip Code` to a full 5-digit code with leading zeros (e.g. `531` becomes
   `00531`).

3. **Percentage fields** - format `Chaucer %` (the quota share) and `Coalition Commission %`
   to two decimal places with a trailing `%` (e.g. `0.321` becomes `32.10%`).

4. **Surplus 3.0** - the `Surplus 3.0` column must be filled with `Yes`/`No`. It must
   never be left blank. Confirm every row has a value before saving.

5. **Retro Short Date** - if `Retro Short Date` (or `Retroactive Short Date`) holds the
   `1900-01-00` value, blank it out. The 1970 value loads fine; only `1900-01-00` breaks
   the load.

## Commission Rate (verify manually)

> **Note:** the automated Chaucer commission-rate check is **disabled** in code because
> the Chaucer report is missing a column the calculation needs. You must verify the
> commission rate **by hand** against the OTC sheet.

6. **Verify the commission rate against the OTC sheet.** For Chaucer, the OTC sheet lists:
   - **33.50%** for policies effective **before 7/1/2024**;
   - **34.50%** for policies effective **on or after 7/1/2024**;
   - brokerage fee **1.00%**.

   Check each row's `Policy Effective Date` against the cutoff and confirm
   `Coalition Commission %` matches the correct band. Do not rely on the script for this.

## Coverage Field Formatting (General)

7. The Limits Report ties and formats the limits. The coverage list this applies to is at
   the end of this section. Apply the following:
   - Empty cells coalesce to `0` (an empty cell becomes `0`).
   - Each cell is an integer, no decimals (`10000.0` becomes `10000`).
   - Coverages pulled directly from NetSuite are at the aggregate transaction level, so
     multiply each coverage by the quota share - specifically `Chaucer %`.
   - Align each coverage's sign to the sign of `Total Bound Premium`. If TBP is positive,
     each coverage must be positive; if TBP is negative, each coverage must be negative
     (binder edits and soft deletes do not always reverse coverages correctly).

   > **Note:** this format-and-align process repeats for every carrier, which is why it is
   > recommended to do it once on the Limits Report, use that as the source of truth, and
   > multiply by the quota share column.

## Sanity Checks (mirror the script's QA)

Before saving, confirm the following by hand. These mirror the automated checks the
pipeline runs for Chaucer (script tolerance is +/- 0.02):

8. **`Surplus 3.0` filled** - every row has `Yes` or `No`, never blank.

9. **Chaucer Bound Premium** = `Total Gross Written Premium (GWP)` x `Chaucer %`.

10. **Limit signature matches TBP** - the sign of the base limit (`Aggregate Total Limit`)
    matches the sign of `Total Bound Premium`. A `0` base limit is fine.

11. **Transaction ID not blank** - `Transaction ID` is populated on every row (no blanks
    or `nan`).

12. **TRIA alignment** - because Chaucer is a US carrier: if `Total TRIA` is `0` then
    `Chaucer TRIA` must also be `0`, and vice versa.

For reference, the other Chaucer-derived relationships are:
- **Chaucer Net Premium** = (`GWP` x `Chaucer %`) x (1 - `Coalition Commission %`).
- **Chaucer % Commission to Coalition** = `Chaucer Bound Premium` x `Coalition Commission %`.

## The limits

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

## Save-as note

> **Note:** the file gets built as an Excel file but gets sent as a CSV. When you
> `Save As` a CSV from an Excel file, the formatting keeps its shape. If you open the CSV
> file and resave, you will lose the formatting you need to keep (leading zeros, `%`,
> dates).

---

# Renames and Deletions

## Remove Columns

Remove the following columns if they are in the report:

1. `Quote Coalition Policy Number`
2. `Internal ID.1`
3. `Reputational Harm Loss.1`

## Final Column Renames

- `Chaucer %` -> `Chaucer Quota Share`
- `SIR / Attachment Point` -> `SIR`
- `Run-Off` -> `Run Off [Y/N]`
- `Run-Off Start Date` -> `Run Off Start Date`
- `Run-Off End Date` -> `Run Off End Date`

The commission-to-coalition column carries the master header
`Chaucer % Commission to Coalition`.

---

# Current Pending / Known Gaps

The below would be something to go over as a group on best next steps.

## Commission rate check (disabled)

The automated Chaucer commission-rate validation is disabled in code because the Chaucer
report is missing a column the calculation needs. Until that column is added, the analyst
must verify the commission rate manually against the OTC sheet (33.50% before 7/1/2024,
34.50% on/after, 1.00% brokerage fee). See Commission Rate in Formatting.

## Package Keys

It is currently unclear how an analyst can extract the `Package Keys` from the
[Endorsement Report](https://thecoalitionworkshop.looker.com/looks/3073) by hand - the
payload is written as JSON, so Excel is limited here. In the meantime, the proposal is to
pull and save the package keys in a shared folder, or to use the script to pull the
`Package Key` into the Policy List file the analyst has in hand. It is not yet confirmed
whether package keys apply to Chaucer; treat this as a known gap.

## Saved-search link

The production `ChaucerAccountCurrent` saved-search URL is not recorded here yet; the
report is referenced by name and pulled from the Account Current / Day 10 folder. Link TBD.
