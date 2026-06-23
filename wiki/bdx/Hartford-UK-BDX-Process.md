# Hartford UK BDX Process

# Overview

This page walks an analyst through building the **Hartford UK** monthly BDX file by hand in
Excel, without running the Python script. Hartford UK is our cyber line of business written
through the UK subsidiary entity **Coalition Risk Solutions Ltd.** It is reported on the
**Day 10** cadence.

Because Hartford UK is a UK book, it uses the generic **Basic** validation (not the US-specific
one). In practice that means a few US-only steps you may have seen on other carriers do **not**
apply here: there is no TRIA check, no earned/unearned premium check, no Surplus 3.0 requirement,
and the US 5-digit zip-code rule does **not** apply (UK postcodes are alphanumeric). Date,
percentage, and coverage/limit formatting all still apply.

The high-level flow is the same as every other carrier: pull the Hartford UK Account Current
report from NetSuite, tie out coverages against the Limits Report, apply the formatting rules,
sanity-check the derived premium columns, do the renames and deletions, then `Save As` CSV.

---

# Sources

Below are the current reports required to complete the Hartford UK BDX file.

## NetSuite

- **Hartford UK Account Current** (`HartFordUKAccountCurrentResults` saved search) - the main
  BDX file. Pulled from the production **Account Current / Day 10** folder, **not** from
  Downloads.

  > **Note:** use the production saved search; link TBD.

  > **Note:** the saved search is set to filter `Modified Date` within the previous day, so
  > make sure to **edit** the search, **remove** that filter, go to **Preview**, then **Run**
  > before exporting.

- [Limits Report](https://5118830.app.netsuite.com/app/common/search/searchresults.nl?searchid=8180) -
  report used for the limit/coverage columns, used to tie out and format the coverages
  consistently.

## Looker Reports

> **Note:** the two Looker lookups below are documented the way they work for other cyber books.
> Whether they are needed (or return complete data) for the UK book is uncertain - see
> Known Gaps before relying on them.

- [Industries Report](https://thecoalitionworkshop.looker.com/looks/4136?toggle=dat,vis) -
  used for industry codes and policyholder information (`Employee Count`, `Attachment Point`).
- [Endorsement Report](https://thecoalitionworkshop.looker.com/looks/3073) - used to create
  the package keys.

## Reference Sheets

- [OTC Commission Rate Google Sheet](https://docs.google.com/spreadsheets/d/1yHG90_XFwbneIrGhwgpDMNjelcn2BK90j36lu5BEijo/edit?gid=1587427731#gid=1587427731) -
  the source of truth for the Hartford UK `Coalition Commission %`. There is no auto-check for
  this rate, so confirm it manually here (see Reports).

---

# Reports

This section covers every report that gets pulled, joined, or renamed into the Hartford UK file.

## Hartford UK Account Current (primary)

- **Source:** NetSuite saved search `HartFordUKAccountCurrentResults`, from the production
  Account Current / Day 10 folder.
- **Use:** this is the BDX file itself - every other report is merged into it.
- **Key columns:**
  - `Hartford Quota Share %` - the quota share, a percentage field. (The master file calls this
    column `Hartford Quota Share`.)
  - `Hartford Bound Premium`, `Hartford Net Premium`, `Hartford Commission to Coalition` - the
    carrier-derived premium columns (sanity-checked in Formatting below).
  - `Total Bound Premium` - the TBP basis used to derive the carrier premiums.
  - `Aggregate Total Limit` - the base limit.
  - `External ID` - the external identifier.
  - `Coalition Commission %` - the commission rate (confirm manually against the OTC sheet).
- **Commission-to-coalition master header:** `Hartford % Commission To Coalition`.

> **Note:** there is no OTC commission-rate auto-check defined for Hartford. The analyst must
> confirm the `Coalition Commission %` manually against the OTC sheet. Do not assume a rate.

## Limits Report (NetSuite)

- **Source:** NetSuite [Limits Report](https://5118830.app.netsuite.com/app/common/search/searchresults.nl?searchid=8180).
- **Use:** the source of truth for the coverage/limit columns. Format and align the coverages
  once here, then bring them into the Hartford file (see Coverage Field Formatting). This
  avoids repeating the alignment work and lets you multiply by the quota share in one place.
- **Join key:** match on `Transaction ID` (the standard lookup key between the limits and the
  Account Current report).

## Industries Report (Looker)

- **Source:** Looker [Industries Report](https://thecoalitionworkshop.looker.com/looks/4136?toggle=dat,vis).
- **Use:** industry codes and policyholder information.
- **Join key:** `Transaction ID` (via `Vlookup`, `Xlookup`, `Index-Match`, etc.).
- **Columns pulled / renamed:**
  - `Transaction ID` - for the lookup.
  - `Quote N Employees` -> renamed to `Employee Count` in the BDX.
  - `Excess Attachment Point` -> renamed to `Attachment Point` in the BDX.
- If there are duplicate rows in the Industries Report, drop the duplicates. Note that the
  Looker report loses data if a policy has been soft deleted or cancelled.
- `Attachment Point` should then follow Coverage Field Formatting like the other coverages.

> **Note:** apply this lookup only if the Hartford UK book actually carries these fields. The
> UK book may not populate Industries data the same way the US cyber books do - flag any
> mismatch in Known Gaps rather than forcing the join.

## Endorsement Report (Looker)

- **Source:** Looker [Endorsement Report](https://thecoalitionworkshop.looker.com/looks/3073).
- **Use:** used to derive the `Package Keys`.
- **Join key:** package keys (the package payload tied to the transaction).

> **Note:** the package key is a JSON payload and is currently hard to extract by hand - see
> Known Gaps. Only attempt this if the UK book requires package keys in its BDX.

---

# Formatting

Do the following in Excel, in order. Stay at the level of *what* needs to change, not the exact
keystrokes.

1. **Date format.** Convert all date columns to the Python strftime `%m/%d/%Y %-H:%M:%S` -
   i.e. `m/d/yyyy h:mm:ss`. For example, `3/31/2026` becomes `3/31/2026 0:00:00`. Typical date
   columns: `Date Created`, `Policy Effective Date`, `Policy Expiration Date`,
   `Transaction Effective Date`, `Transaction Effective (Bind) Date`,
   `Account Current Month End`, and `Retroactive Short Date`.

2. **Skip the US zip-code rule.** Hartford UK is a UK book, so the US 5-digit leading-zero
   zip-code formatting does **not** apply (UK postcodes are alphanumeric). Leave
   `Insured Zip Code` / postcode fields as-is.

3. **Percentage fields.** Format `Hartford Quota Share %` and `Coalition Commission %` to two
   decimal places with a trailing `%` sign. For example, `0.321` becomes `32.10%`.

4. **Coverage / limit fields.** Apply these to the coverage columns (listed at the end of this
   section), ideally once on the Limits Report used as the source of truth:
   - Empty cells coalesce to `0`.
   - Values are integers, no decimals (`10000.0` -> `10000`).
   - If the coverages are pulled at the aggregate transaction level from NetSuite, multiply
     each by the quota share - specifically `Hartford Quota Share %`.
   - Align each coverage's sign to the sign of `Total Bound Premium`: if TBP is positive each
     coverage must be positive, and if TBP is negative each coverage must be negative. (Binder
     edits and soft deletes sometimes fail to reverse coverages correctly, so check this.)

5. **Retro Short Date.** If `Retro Short Date` holds the `1900-01-00` value, blank it out. The
   1970 value loads fine; only `1900-01-00` breaks the load.

6. **Confirm the commission rate.** There is no auto-check for Hartford's commission rate.
   Manually confirm `Coalition Commission %` against the OTC sheet before deriving premiums.

7. **Sanity-check the derived premium columns.** Hartford uses the generic Basic validation,
   so verify the following relationships by hand (tolerance is ±0.02). There is **no** TRIA
   check, **no** earned/unearned check, and **no** Surplus 3.0 requirement for Hartford.
   - `Hartford Bound Premium` = `Total Bound Premium` × `Hartford Quota Share %`.
   - `Hartford Net Premium` = (`Total Bound Premium` × `Hartford Quota Share %`) ×
     (1 − `Coalition Commission %`).
   - `Hartford Commission to Coalition` = `Hartford Bound Premium` × `Coalition Commission %`.
   - **Limit signature matches TBP:** the limit signature (sign) must match the
     `Total Bound Premium` sign. A `0` base limit (`Aggregate Total Limit`) is fine.
   - **Transaction ID present:** `Transaction ID` must not be blank / `nan` on any row.

8. **Save as CSV.** The file is built in Excel but **sent as CSV**. Use `Save As` -> CSV from
   the Excel file so the formatting (percentages, dates, coverage integers) is preserved. Do
   **not** reopen the CSV and resave - you will lose the formatting.

## The limits (coverage columns formatting rule #4 applies to)

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

## Remove Columns

Remove the following columns if they appear in the report:

- `Quote Coalition Policy Number`
- `Internal ID.1`
- `Reputational Harm Loss.1`

## Final Column Renames

- `SIR / Attachment Point` -> `SIR`
- `Run-Off` -> `Run Off [Y/N]`
- `Run-Off Start Date` -> `Run Off Start Date`
- `Run-Off End Date` -> `Run Off End Date`

---

# Current Pending / Known Gaps

The items below are best discussed as a group before relying on them by hand.

- **Hartford UK Account Current saved-search link.** The exact NetSuite URL for
  `HartFordUKAccountCurrentResults` is not yet documented here. Use the production saved search
  in the Account Current / Day 10 folder by name; link TBD.

- **Commission rate confirmation.** No auto-check exists for Hartford's commission rate. The
  `Coalition Commission %` must be confirmed manually against the OTC sheet each month. If the
  rate is unclear, raise it with the OTC team rather than guessing.

- **Industries Report applicability (UK book).** It is uncertain whether the UK book populates
  `Quote N Employees` / `Excess Attachment Point` the same way the US cyber books do. Confirm
  the Industries lookup returns complete data for Hartford UK before merging it; if it does
  not, the join should be skipped or revisited.

- **Package Keys.** The package key is a JSON payload from the Endorsement Report and there is
  currently no reliable way to extract it by hand in Excel. In the meantime, propose pulling and
  saving it in a shared folder, or using the script to pull the `Package Key` into the policy
  list. Confirm whether the UK BDX even requires package keys.
