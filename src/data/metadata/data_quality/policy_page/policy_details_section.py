def validate_nj_sla_code(
        nj_sla: str,
        issued_date: str,
        insured_state: str,
        market: str
) -> bool:
    """
    Checks if the nj_sla_code is valid.

    :param nj_sla: the current NJ SLA code in Netsuite
    :param issued_date: date the policy was signed (issued)
    :param insured_state: the state of the policyholder
    :param market: the market the policy is in (Surplus, Admitted)

    :return: pass / fail
    """
    invalid_codes = ["dummy", "wwwww", "12345"]
    # do they qualify for a NJ SLA code? Only applies to NJ insured and Surplus market.
    if insured_state != "NJ" or market != "SURPLUS":
        return True
    # These are not yet issued, so they are expected not to have updated NJ SLA codes.
    if nj_sla == "" and issued_date == "":
        return False
    # These are issued with no codes. CHECK THE LOOKER REPORT FOR THESE.
    elif nj_sla == "" and issued_date != "":
        return False
    # The NJ SLA code is in the list of invalid codes
    if str(nj_sla).split("-")[0].lower() in invalid_codes:
        return False
    return True
