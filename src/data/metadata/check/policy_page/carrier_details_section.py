def validate_net_premium(
        total_bound_premium: float,
        coalition_commission_percent: float,
        net_premium: float,
        variance_cap: float = .02
) -> tuple[bool, float]:
    """Expected formula TBP * (1-commission%)

    :param variance_cap: the highest variance we want before marking it as an error
    :param total_bound_premium: the total premium of the policy
    :param coalition_commission_percent: the Coalition Commission percent of the policy
    :param net_premium:

    :return: bool of the results and the expected value
    """
    expected_net_premium = round(total_bound_premium * (1 - coalition_commission_percent), 2)
    if abs(expected_net_premium - net_premium) > variance_cap:
        return False, expected_net_premium
    return True, expected_net_premium


def validate_carrier_bound_premium(
        total_bound_premium: float,
        carrier_bound_premium: float,
        quota_share: float,
        variance_cap: float = .02
) -> bool:
    """Expected formula for Carrier Bound Premium => TBP x Quota Share

    :param total_bound_premium: the total premium of the policy
    :param carrier_bound_premium: the carrier premium amount
    :param quota_share: the quota split of the carrier
    :param variance_cap: the highest variance we want before marking it as an error

    :return: pass / fail
    """
    expected_carrier_bound_premium = round(total_bound_premium * quota_share, 2)
    if abs(expected_carrier_bound_premium - carrier_bound_premium) > variance_cap:
        return False
    return True


def validate_carrier_net_premium(
        total_bound_premium,
        carrier_net_premium: float,
        carrier_commission_percent: float,
        quota_share: float,
        variance_cap: float = .02
) -> tuple[bool, float]:
    """Expected Formula for Carrier Net Premium => (TBP * Quota Share) - ((TBP * Quota Share) * Carrier Commission Percent)

    :param total_bound_premium: the total premium of the policy
    :param carrier_net_premium: TBP x Quota Share of the policy less Coalition Commission
    :param carrier_commission_percent: the Coalition Commission percent of the policy
    :param quota_share: the quota split of the carrier
    :param variance_cap: the highest variance we want before marking it as an error

    :return: pass / fail
    """
    expected_carrier_net_premium = round(total_bound_premium * ((1 - carrier_commission_percent) * quota_share), 2)
    if abs(expected_carrier_net_premium - carrier_net_premium) > variance_cap:
        return False, expected_carrier_net_premium
    return True, expected_carrier_net_premium


def validate_carrier_commission_to_coalition(
        carrier_bound_premium: float,
        carrier_commission_percent: float,
        carrier_commission_amount: float,
        variance_cap: float = .02
) -> bool:
    """
    Validates the carrier commission amount

    :param carrier_bound_premium: the carrier premium amount
    :param carrier_commission_percent: the Coalition Commission percent of the policy
    :param carrier_commission_amount: Carrier Bound Premium x Carrier Commission Percent
    :param variance_cap: the highest variance we want before marking it as an error

    :return: pass / fail
    """
    expected_carrier_commission = round(carrier_bound_premium * carrier_commission_percent, 2)
    if abs(expected_carrier_commission - carrier_commission_amount) > variance_cap:
        # print(
        #     f"Expected Carrier Commission: {expected_carrier_commission}\n"
        #     f"Given Carrier Commission: {carrier_commission_amount}"
        # )
        return False
    return True
