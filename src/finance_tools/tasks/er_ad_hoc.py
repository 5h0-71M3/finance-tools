from collections import Counter
from datetime import date

import pandas as pd

from finance_tools.io import FOLDERS

f = FOLDERS()


def er_limit_from_looker():
    df = f.DOWNLOADS.open_recent("exec_risks")

    df["Endorsements Coverage Endorsement Form Codes"] = df["Endorsements Coverage Endorsement Form Codes"].fillna("Missing")
    cov_endt_form_codes = [str(code).strip() for li in df["Endorsements Coverage Endorsement Form Codes"].str.split(",") for code in li]
    coverage_endt_codes_counter = Counter(cov_endt_form_codes)
    erp_codes = (
        "ERUSP-50EN-00A073-0225-01",
        "ERUSP-50EN-00A071-0625-01",
        "ERUSP-50EN-00A050-1023-01",
        "U-PCNPP-3135GB CW 03 20"
    )

    only_erp_codes = {k: v for k, v in coverage_endt_codes_counter.items() if k in erp_codes}

    affected_policies = [
        pol for pol, code in zip(df["Quotes, Binders & Policies Quote Coalition Policy Number"], df["Endorsements Coverage Endorsement Form Codes"])
        if any(
            ("ERUSP-50EN-00A073-0225-01" in str(code).split(", "),
             "ERUSP-50EN-00A071-0625-01" in str(code).split(", "),
             "ERUSP-50EN-00A050-1023-01" in str(code).split(", "),)
        )
    ]

    mapl = {"Affected Policies": affected_policies, "Notes": ["Need ERP marked" for _ in affected_policies]}
    pd.DataFrame.from_dict(mapl).to_csv(f.DOWNLOADS / f"ERP Endorsements Not Mapped in Netsuite - {date.today()}.csv")


def handle_er_limit_merge():
    df = f.DOWNLOADS.open_recent("exec_risks")

    # RUN-OFF ENDORSEMENT (REMOVE SUCCESSOR ENTITY) - ERUSP-50EN-00A073-0225-01
    # RUN-OFF ENDORSEMENT - ERUSP-50EN-00A071-0625-01
    # EXTENDED REPORTING PERIOD ELECTED - ERUSP-50EN-00A050-1023-01

    # HANDLING THE LOOKER REPORT FOR THE ER CODES
    df["Endorsements Coverage Endorsement Form Codes"] = df["Endorsements Coverage Endorsement Form Codes"].fillna("Missing")
    cov_endt_form_codes = [str(code).strip() for li in df["Endorsements Coverage Endorsement Form Codes"].str.split(",") for code in li]
    coverage_endt_codes_counter = Counter(cov_endt_form_codes)
    erp_codes = (
        "ERUSP-50EN-00A073-0225-01",
        "ERUSP-50EN-00A071-0625-01",
        "ERUSP-50EN-00A050-1023-01",
        "U-PCNPP-3135GB CW 03 20"
    )

    only_erp_codes = {k: v for k, v in coverage_endt_codes_counter.items() if k in erp_codes}
    # not_in_ns = df[df["Endorsements Coverage Endorsement Form Codes"] == "U-PCNPP-3135GB CW 03 20"].copy()

    print(coverage_endt_codes_counter)
    print(only_erp_codes)
    print("ALL POLICIES ON LOOKER UNDER U-PCNPP-3135GB CW 03 20:")
    # print(not_in_ns["Quotes, Binders & Policies Quote Coalition Policy Number"])
    print("POLICIES IN LOOKER, NOT IN NS")
    print()
    print("***")

    ###########################
    # HANDLING FOR THE ONES IN THE ERP REPORT FROM NS
    ###########################

    # THESE ARE WHAT IS COMING INTO NETSUITE
    pl = f.get_policy_list()

    # The filters
    er_coverages = pl["LOB"] == "Management Liability"
    erp_endt = pl["Extended Reporting Period"] == "Yes"

    er_erp_coverages = pl[er_coverages & erp_endt].copy()
    also_in_ns = df[df["Quotes, Binders & Policies Quote Coalition Policy Number"].isin(er_erp_coverages["Coalition Policy Number"])].copy()

    # Wrangling the codes into lists we can check against
    cleaned_coverage_code = [str(code).strip() for row in also_in_ns["Endorsements Coverage Endorsement Form Codes"].str.split(",") for code in row]
    cleaned_quote_code = [str(code).strip() for row in also_in_ns["Endorsements Quote Endorsement Form Codes"].str.split(",") for code in row]
    cleaned_coverage_name = [str(code).strip() for row in also_in_ns["Endorsements Coverage Endorsement Names"].str.split(",") for code in row]
    code_in_netsuite = [
        pol
        for pol, code in zip(also_in_ns["Quotes, Binders & Policies Quote Coalition Policy Number"], also_in_ns["Endorsements Coverage Endorsement Form Codes"])
        if any(("ERUSP-50EN-00A050-1023-01" in str(code).split(", "), "U-PCNPP-3135GB CW 03 20" in str(code).split(", ")))
    ]

    coverage_counter = Counter(cleaned_coverage_code)
    quote_counter = Counter(cleaned_quote_code)
    name_counter = Counter(cleaned_coverage_name)

    print(code_in_netsuite)
    print(coverage_counter)
    print(quote_counter)
    print(name_counter)

    # MY GOAL HERE IS TO MARK DOWN WHICH ONES ARE IN LOOKER, BUT MISSING IN NS FOR "U-PCNPP-3135GB CW 03 20"
    df["Split Codes"] = "U-PCNPP-3135GB CW 03 20" in [str(code).strip() for code in df["Endorsements Coverage Endorsement Form Codes"].str.split(",")]
    # src = df.apply(lambda row: "U-PCNPP-3135GB CW 03 20" in row)

    # policies_affected = df[src]["Quotes, Binders & Policies Quote Coalition Policy Number"].isin(code_in_netsuite)

    print("***")
    print("UPDATED SECTION")
    print("---")
    print(df["Split Codes"].unique())
    # print(df["Has Code"].head())
    # print(policies_affected)

    ########################################################################################################


if __name__ == "__main__":
    er_limit_from_looker()
