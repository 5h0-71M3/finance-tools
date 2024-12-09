def validate_surcharge(
        total_surcharge: float,
        subtotal_surcharge: list[float] | float,
        variance_cap: float = 0.02
) -> bool:
    """Confirms that the surcharge breakdown matches the surcharge total.

    I'm making this so any surcharge can be calculated, against the 'total' surcharge amount.

    :param variance_cap: the highest variance we want before marking it as an error
    :param total_surcharge: the field that holds the total surcharge amount
    :param subtotal_surcharge: the sub-fields that should total the surcharge amount

    :return: pass / fail
    """
    counter = 0
    if isinstance(subtotal_surcharge, list):
        for surcharge in subtotal_surcharge:
            counter += surcharge
        subtotal_surcharge = counter

    # the difference is less than 5 cents, so we pass it
    if abs(subtotal_surcharge - total_surcharge) < variance_cap:
        return True
    return False


def validate_pliga_fee(
        insured_state: str,
        pliga_fee: float,
) -> bool:
    """
    This is a NJ state surcharge that only applies to the state of NJ.
    Any other insured state should have and not have this fee.

    :param insured_state: state of the policyholder
    :param pliga_fee: the NJ fee (Prob Liability Insurance Guaranty Association Surcharge)

    :return: pass / fail
    """
    insured_state = insured_state.upper()

    # Does not apply to non-NJ states, and no fees associated with them
    if insured_state != "NJ" and pliga_fee == 0:
        return True
    # non-NJ state with a PLIGA fee should fail
    elif insured_state != "NJ" and 0 > pliga_fee > 0:
        return False
    # The state is in NJ and there is no PLIGA fee - confirm this
    if insured_state == "NJ" and pliga_fee == 0:
        return False
    return True


def validate_kentucky_surcharges(
        insured_state: str,
        ky_insurance_surcharge: float,
        ky_municipal_tax: float,
        ky_collection_fee: float,
        total_surcharge: float
) -> bool:
    """
    Still need to confirm this as a lot of transactions are actually empty on the KY portion, but this checks to make sure that the transactions tie out

    :param insured_state: Kentucky, the state of the policy where these surcharges apply to
    :param ky_insurance_surcharge: the Kentucky Insurance surcharge field
    :param ky_municipal_tax: the Kentucky Municipal tax field
    :param ky_collection_fee: the Kentucky Collection fee field
    :param total_surcharge: the total surcharge of the transaction
    :return: pass / fail
    """
    insured_state = insured_state.upper()

    if insured_state != "KY" and all((ky_insurance_surcharge == 0, ky_municipal_tax == 0, ky_collection_fee == 0)):
        return True
    elif insured_state != "KY" and any((ky_insurance_surcharge != 0, ky_municipal_tax != 0, ky_collection_fee != 0)):
        return False
    return validate_surcharge(total_surcharge=total_surcharge, subtotal_surcharge=[ky_insurance_surcharge, ky_municipal_tax, ky_collection_fee])

