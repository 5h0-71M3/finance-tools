class FieldNamingConventions:
    nj_sla_query = {
        "Quote Coalition Policy Number": "quota_coalition_policy_number",
        "Quote Status": "quote_status",
        "Nj Transaction Number": "nj_transaction_number",
        "Quote Company Name": "quote_company_name",
        "Quote Company State": "quote_company_state",
        "Agency Surplus Lines Agent Number": "agency_surplus_lines_agent_number"
    }

    data_quality_transaction = {
        "Internal ID": "internal_id",
        "Insurance Program": "insurance_program",
        "Insured State": "insured_state",
        "Market": "market",
        "NJ Transaction Number": "nj_sla",
        "--Coalition Policy Number--": "coalition_policy_number",
        "-------------Transaction ID-------------": 'transaction_id',

        "T Effective Date": "date_effective",
        "Date Created": "date_created",
        "Policy Issued Date": "date_issued",

        "Description": "description",
        "Soft Delete": "soft_delete",
        "Binder Edit/Soft Delete Complete": "be_sd_complete",
        "Binder Edit": "binder_edit",
        "Module": "mod",

        "TBP": "tbp",
        "Endorsement Number": "endorsement_number",
        "Policy UUID": "policy_uuid",
        "Swiss Re Bound Premium": "sre_bound_premium",
        "Total TRIA": "total_tria",

        "Aspen Quota Share": "aspen_quota_share",
        "HDI Quota Share": "hdi_quota_share",
        "CIC Quota Share": "cic_quota_share",
        "Zurich Quota Share": "zurich_quota_share",
        "Vantage Quota Share": "vantage_quota_share",
        "Swiss Re %": "swissre_quota_share",
        "Lloyds_quota_share": "lloyds_quota_share",
        "Fortegra_Quota_Share": "fortegra_quota_share",
        "Chaucer Quota Share": "chaucer_quota_share",
        "Ascot Quota Share": "ascot_quota_share",
        "Arch Quota Share": "arch_quota_share",
        "Allianz Quota Share": "alliance_quota_share",

        "Aggregate Total Limit": "aggregate_limit",
        "SIR": "sir",
    }
