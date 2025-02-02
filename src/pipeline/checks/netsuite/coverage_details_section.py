def recon_aggregate_total_limit_balance(
        platform_coverage_dict: dict,
        coalition_policy_number: str,
        netsuite_aggregate_total_limit_balance: int
):
    """
    Anything recon related will compare two reports together.
    This check will compare what the Total Limit Balance is on the Platform compared to Netsuite.

    :return: pass / fail
    """

    # Key and Error Handling
    if coalition_policy_number not in platform_coverage_dict.keys():
        raise KeyError(f"Missing coalition policy {coalition_policy_number} in the dict")
    platform_coverage = platform_coverage_dict[coalition_policy_number]

    if any(
            item not in platform_coverage for item in (
                    "bound_agg_limit_sublimit", "policy_agg_limit_sublimit", "quote_agg_limit_sublimit")
    ):
        raise KeyError(f"Missing aggregate limit keys in the dict")

    # Actual Limit Balance Check
    if abs(netsuite_aggregate_total_limit_balance) - abs(platform_coverage["bound_agg_limit_sublimit"]) > .02:
        return False
    elif abs(netsuite_aggregate_total_limit_balance) - abs(platform_coverage["policy_agg_limit_sublimit"]) > .02:
        return False
    elif abs(netsuite_aggregate_total_limit_balance) - abs(platform_coverage["quote_agg_limit_sublimit"]) > .02:
        return False
    return True


def validate_limit_signature_matches_tbp(tbp: float, base_limit: int) -> bool:
    """the signature of the limit columns match the tbp signature (+ vs -)

    :return: pass / fail
    """
    if tbp < 0:
        if base_limit <= 0:
            return True
    else:
        if base_limit >= 0:
            return True
    return False
