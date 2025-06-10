def validate_quota_share_total():
    ...


def validate_net_premium(
        tbp: float,
        coalition_commission_percent: float,
        net_premium: float,
) -> bool:
    """Expected formula TBP * (1-commission%)

    :param tbp: the total premium of the policy
    :param coalition_commission_percent: the Coalition Commission percent of the policy
    :param net_premium:

    :return: bool of the results and the expected value
    """
    option_variance_cap: float = .02
    try:
        expected_net_premium = round(tbp * (1 - coalition_commission_percent), 2)
    except TypeError:
        raise TypeError(f"{tbp}, {coalition_commission_percent}")

    if expected_net_premium - net_premium > option_variance_cap:
        return False
    return True


def validate_carrier_bound_premium(
        tbp: float,
        carrier_bound_premium: float,
        carrier_quota_share: float,
) -> bool:
    """Expected formula for Carrier Bound Premium => TBP x Quota Share

    :param tbp: the total premium of the policy
    :param carrier_bound_premium: the carrier premium amount
    :param carrier_quota_share: the quota split of the carrier

    :return: pass / fail
    """
    option_variance_cap: float = .02
    try:
        expected_carrier_bound_premium = round(tbp * carrier_quota_share, 2)
    except TypeError as te:
        raise TypeError(f"{tbp}, {carrier_quota_share}: {te}")
    if abs(expected_carrier_bound_premium - carrier_bound_premium) > option_variance_cap:
        return False
    return True


def validate_carrier_net_premium(
        tbp: float,
        carrier_net_premium: float,
        carrier_percent_commission: float,
        carrier_quota_share: float,
) -> bool:
    """Expected Formula for Carrier Net Premium => (TBP * Quota Share) - ((TBP * Quota Share) * Carrier Commission Percent)

    :param tbp: the total premium of the policy
    :param carrier_net_premium: TBP x Quota Share of the policy less Coalition Commission
    :param carrier_percent_commission: the Coalition Commission percent of the policy
    :param carrier_quota_share: the quota split of the carrier

    :return: pass / fail
    """
    option_variance_cap: float = .02
    expected_carrier_net_premium = round(tbp * ((1 - carrier_percent_commission) * carrier_quota_share), 2)
    if abs(expected_carrier_net_premium - carrier_net_premium) > option_variance_cap:
        return False
    return True


def validate_carrier_commission_to_coalition(
        carrier_bound_premium: float,
        carrier_percent_commission: float,
        carrier_commission_to_coalition: float,
) -> bool:
    """
    Validates the carrier commission amount

    :param carrier_bound_premium: the carrier premium amount
    :param carrier_percent_commission: the Coalition Commission percent of the policy
    :param carrier_commission_to_coalition: Carrier Bound Premium x Carrier Commission Percent

    :return: pass / fail
    """
    option_variance_cap: float = .02
    expected_carrier_commission = round(carrier_bound_premium * carrier_percent_commission, 2)
    if abs(expected_carrier_commission - carrier_commission_to_coalition) > option_variance_cap:
        return False
    return True
