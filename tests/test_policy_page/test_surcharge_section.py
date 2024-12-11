from src.data.metadata.check.policy_page.surcharge_section import validate_surcharge, validate_pliga_fee, \
    validate_kentucky_surcharges


class TestSurchargeSection:
    def test_validate_surcharge(self):
        """Assert validation_surcharge function works with .03 variance as cap

        """
        surcharge_total = 100
        a = 10
        b = 70
        c = 10
        d = 10.02
        s_error = 10.03

        to_pass = validate_surcharge(
            total_surcharge=surcharge_total,
            subtotal_surcharge=[a, b, c, d]
        )

        to_error = validate_surcharge(
            total_surcharge=surcharge_total,
            subtotal_surcharge=[a, b, c, d, s_error]
        )

        assert to_pass is True
        assert to_error is False

    def test_validate_pliga_fee(self):
        """Asserts that PLIGA fees are applied to the correct state

        """
        valid_state = "nj"
        non_valid_state = "ky"
        surcharge = 10
        no_surcharge = 0

        # In New Jersey
        false_no_fee = validate_pliga_fee(insured_state=valid_state, pliga_fee=no_surcharge)
        true_valid = validate_pliga_fee(insured_state=valid_state, pliga_fee=surcharge)

        # Non-New Jersey
        false_non_state = validate_pliga_fee(insured_state=non_valid_state, pliga_fee=surcharge)
        true_non_state = validate_pliga_fee(insured_state=non_valid_state, pliga_fee=no_surcharge)

        assert false_no_fee is False
        assert true_valid is True
        assert false_non_state is False
        assert true_non_state is True

    def test_validate_kentucky_surcharge(self):
        valid_state = "ky"
        invalid_state = "ny"

        ky_ins = 10
        ky_muni = 80
        ky_collection = 10
        total = 100

        pass_all_valid = validate_kentucky_surcharges(valid_state, ky_ins, ky_muni, ky_collection, total)
        fail_non_state_with_values = validate_kentucky_surcharges(invalid_state, ky_ins, ky_muni, ky_collection, total)
        pass_non_state_no_values = validate_kentucky_surcharges(invalid_state, 0, 0, 0, total)
        fail_surcharge_total_variance = validate_kentucky_surcharges(valid_state, ky_ins, ky_muni, ky_collection, 200)

        assert pass_all_valid is True
        assert fail_non_state_with_values is False
        assert pass_non_state_no_values is True
        assert fail_surcharge_total_variance is False
