from src.data.policy_page import validate_net_premium, validate_carrier_bound_premium, \
    validate_carrier_net_premium, validate_carrier_commission_to_coalition


class TestCarrierDetailsSection:
    tbp = 1000
    commission_perc = .01
    net_premium = 990
    quota = .5

    def test_validate_net_premium(self):
        valid_net = validate_net_premium(
            total_bound_premium=self.tbp,
            coalition_commission_percent=self.commission_perc,
            net_premium=self.net_premium
        )

        assert valid_net is True

    def test_validate_carrier_bound_premium(self):
        carrier_bound_premium = self.tbp * self.quota

        valid_carrier_bound = validate_carrier_bound_premium(
            total_bound_premium=self.tbp,
            carrier_bound_premium=carrier_bound_premium,
            quota_share=self.quota
        )

        assert valid_carrier_bound is True

    def test_validate_carrier_net_premium(self):
        carrier_bound = self.tbp * self.quota
        carrier_comm = carrier_bound * self.commission_perc
        carrier_net = carrier_bound - carrier_comm

        valid_carrier_net = validate_carrier_net_premium(
            total_bound_premium=self.tbp,
            carrier_net_premium=carrier_net,
            carrier_commission_percent=self.commission_perc,
            quota_share=self.quota
        )

        assert valid_carrier_net is True

    def test_validate_carrier_commission(self):
        carrier_bound = self.tbp * self.quota
        carrier_comm = carrier_bound * self.commission_perc

        print(carrier_comm)

        valid_comm = validate_carrier_commission_to_coalition(
            carrier_bound_premium=carrier_bound,
            carrier_commission_percent=self.commission_perc,
            carrier_commission_amount=carrier_comm
        )
        assert valid_comm is True
