# Day 5 carrier validations — pipeui reference

Each Day 5 carrier's validation set, ported from the legacy `carriers.py` classes.
Functions are defined **once** and reused across carriers (pipeui collapses identical
functions by content hash; bind each source's columns at attach time in the app).

## Where each function lives
| Function | Location | Shape |
|---|---|---|
| `validate_carrier_bound_premium` (scalar) | `shared/` | `-> bool` |
| `validate_carrier_net_premium` | `vantage/` | `-> bool` |
| `validate_carrier_commission_to_coalition` | `vantage/` | `-> bool` |
| `validate_limit_signature_matches_tbp` | `vantage/` | `-> bool` |
| `transaction_id_is_nan` | `vantage/` | `-> pd.Series[bool]` |
| `carrier_tria_zero_if_total_is_zero` | `vantage/` | `-> pd.Series[bool]` |
| `earned_unearned_field_is_zero` | `vantage/` | `-> pd.Series[bool]` |
| `surplus_3_0_filled` | `vantage/` | `-> pd.Series[bool]` |
| `allianz_commission_rate_matches_google_sheet` | `shared/` | `-> pd.Series[bool]` |
| `lloyds_uk_canada_commission_rate_matches_google_sheet` | `shared/` | `-> pd.Series[bool]` |
| `package_key_missing_on_expected_transactions` | `allianz_us/` | `-> pd.Series[bool]` |
| `gwp_breakdown_matches_premium_total` | `allianz_aus/` | `-> pd.Series[bool]` |
| `gross_premium_amount_equals_base_gst_stamp_duty` | `allianz_aus/` | `-> pd.Series[bool]` |
| `stamp_duty_breakdown_matches_sd_total` | `allianz_aus/` | `-> pd.Series[bool]` |

> Note: multi-column checks (net/commission/limit/bound_premium and any with 2+ bound
> columns) will not run until pipeui supports binding more than one column per validation.

## Per-carrier check sets + column bindings

### Allianz US (legacy `AllianzUSValidation`)
`package_key_missing_on_expected_transactions`, `surplus_3_0_filled`,
`allianz_commission_rate_matches_google_sheet`, `validate_carrier_bound_premium`,
`validate_carrier_net_premium`, `validate_carrier_commission_to_coalition`,
`validate_limit_signature_matches_tbp`, `transaction_id_is_nan`
- transaction_description → "Transaction Description", soft_delete → "Soft Delete",
  external_id → "External ID", package_key → "Package Keys", surplus_3_0 → "Surplus 3.0",
  policy_effective_date → "Policy Effective Date", coalition_percent_commission → "Coalition Commission %",
  tbp → "Total Bound Premium", carrier_bound_premium → "Allianz Bound Premium",
  carrier_net_premium → "Allianz Net Premium", carrier_quota_share → "Allianz Quota Share %",
  carrier_percent_commission → "Coalition Commission %",
  carrier_commission_to_coalition → "Allianz $ Commission To Coalition",
  base_limit → "Aggregate Total Limit"

### Allianz UK (legacy `AllianzUKValidation`)
`allianz_commission_rate_matches_google_sheet`, `validate_carrier_bound_premium`,
`validate_carrier_net_premium`, `validate_carrier_commission_to_coalition`,
`validate_limit_signature_matches_tbp`, `transaction_id_is_nan`
- carrier_commission_to_coalition → "Allianz Commission to Coalition" (differs from US);
  carrier_bound_premium → "Allianz Bound Premium", carrier_net_premium → "Allianz Net Premium",
  carrier_quota_share → "Allianz Quota Share %", tbp → "Total Bound Premium",
  coalition/carrier_percent_commission → "Coalition Commission %",
  policy_effective_date → "Policy Effective Date", base_limit → "Aggregate Total Limit",
  external_id → "External ID"

### Allianz Germany / Allianz Denmark (legacy `AllianzBasicValidation`)
`allianz_commission_rate_matches_google_sheet`, `validate_carrier_bound_premium`,
`validate_carrier_net_premium`, `validate_carrier_commission_to_coalition`,
`validate_limit_signature_matches_tbp`, `transaction_id_is_nan`
- carrier_bound_premium → "Allianz Bound Premium", carrier_net_premium → "Allianz Net Premium",
  carrier_quota_share → "Allianz Quota Share %", tbp → "Total Bound Premium",
  coalition/carrier_percent_commission → "Coalition Commission %",
  policy_effective_date → "Policy Effective Date", base_limit → "Aggregate Total Limit",
  external_id → "External ID"
- carrier_commission_to_coalition: legacy map has no Allianz-specific column here (falls back
  to a multi-column list); bind to the Allianz commission-to-coalition column for these reports.

### Allianz AUS (legacy `AustraliaValidation`)
`gwp_breakdown_matches_premium_total`, `gross_premium_amount_equals_base_gst_stamp_duty`,
`stamp_duty_breakdown_matches_sd_total` (inherits NO base checks)
- See `allianz_aus/validations.py` docstring for the full GWP/stamp-duty column map;
  tbp → "Annual Gross Written Premium".

### Ascot (legacy `BasicValidationUS`)
`carrier_tria_zero_if_total_is_zero`, `earned_unearned_field_is_zero`,
`validate_carrier_bound_premium`, `validate_carrier_net_premium`,
`validate_carrier_commission_to_coalition`, `validate_limit_signature_matches_tbp`,
`transaction_id_is_nan`
- carrier_tria → "Gross TRIA - Ascot", total_tria → "Total TRIA",
  total_earned_premium → "Total Earned Premium", total_unearned_premium → "Total Unearned Premium",
  carrier_bound_premium → "Gross Premium - Ascot", carrier_net_premium → "Ascot Net Premium",
  carrier_quota_share → "Ascot Quota Share %", carrier_commission_to_coalition → "Ascot $ Commission To Coalition",
  carrier_percent_commission → "Coalition Commission %", tbp → "Total Bound Premium",
  base_limit → "Aggregate Total Limit", external_id → "External ID"

### Lloyds Canada (legacy `LloydsValidation`)
`lloyds_uk_canada_commission_rate_matches_google_sheet`, `earned_unearned_field_is_zero`,
`validate_carrier_bound_premium`, `validate_carrier_net_premium`,
`validate_carrier_commission_to_coalition`, `validate_limit_signature_matches_tbp`,
`transaction_id_is_nan`
- carrier_bound_premium → "Bound Premium", carrier_net_premium → "Net Premium to London in USD (GWP",
  carrier_quota_share → "Lloyds Quota Share %", carrier_commission_to_coalition → "Lloyds Commission to Coalition",
  policy_effective_date → "Policy Effective Date", coalition/carrier_percent_commission → "Coalition Commission %",
  total_earned_premium → "Total Earned Premium", total_unearned_premium → "Total Unearned Premium",
  tbp → "Total Bound Premium", base_limit → "Aggregate Total Limit", external_id → "External ID"

### Lloyds UK (legacy `LloydsUnitedStatesValidation`)
`validate_carrier_bound_premium`, `validate_carrier_net_premium`,
`validate_carrier_commission_to_coalition`, `validate_limit_signature_matches_tbp`,
`transaction_id_is_nan`
- carrier_bound_premium → "$ GWP written through Lloyd's quota share",
  carrier_quota_share → "% GWP written through Lloyd's quota share",
  carrier_commission_to_coalition → "Coverholder Commission Amount",
  carrier_net_premium → "Net Premium to London in USD (GWP less Coverholder Commission)",
  carrier_percent_commission / coalition_percent_commission → "Coverholder Commission %",
  tbp → "Total Gross Written Premium (GWP)", base_limit → "Sum Insured Amount (Aggregate Total Limit)",
  external_id → "Coalition Transaction ID"
