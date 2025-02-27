import inspect

from src.pipeline.checks.bdx import carrier_tria_zero_if_total_is_zero, transaction_id_is_nan, \
    earned_unearned_field_is_zero, package_key_missing_on_expected_transactions, stamp_duty_breakdown_matches_sd_total


class Validation:
    @classmethod
    def _get_all_functions_in_class(cls) -> dict:
        base_functions = {
            name: fn for name, fn in cls.__base__.__dict__.items() if inspect.isfunction(fn)
        }
        curr_functions = {
            name: fn for name, fn in cls.__dict__.items() if inspect.isfunction(fn)
        }
        return base_functions | curr_functions

    @classmethod
    def _get_all_params_in_class(cls) -> dict:
        all_params = {}
        for k, v in cls._get_function_param().items():
            for p in v:
                if p not in all_params:
                    all_params[p] = None
        return all_params

    @classmethod
    def _get_function_param(cls) -> dict:
        _function_params = {
            check_name: {
                p: None for p in inspect.get_annotations(fn) if p not in ('return',)
            } for check_name, fn in cls._get_all_functions_in_class().items()
        }
        for check_name, fn in cls._get_all_functions_in_class().items():
            print("I AM SIG")
            print(inspect.signature(fn))
            print("I AM ANNO")
            print(inspect.get_annotations(fn))
        return _function_params


class BaseChecks(Validation):
    tria_zero_if_total_zero = carrier_tria_zero_if_total_is_zero
    transaction_id_not_nan = transaction_id_is_nan
    earned_unearned = earned_unearned_field_is_zero

    @classmethod
    def check_breakdown(cls):
        print(cls._get_function_param())
        print(cls._get_all_params_in_class())


class SecondLayerChecks(BaseChecks):
    pacakge_key = package_key_missing_on_expected_transactions

    @classmethod
    def check_breakdown(cls):
        print(cls._get_function_param())
        print(cls._get_all_params_in_class())


class ThirdLayerChecks(SecondLayerChecks):
    stamp_duty_breakdown = stamp_duty_breakdown_matches_sd_total

    @classmethod
    def check_breakdown(cls):
        print(cls._get_all_params_in_class())
        print(cls._get_all_functions_in_class())


x = BaseChecks()

print()
print("***")
print()

y = SecondLayerChecks()

print()
print("***")
print()

z = ThirdLayerChecks()
z.check_breakdown()
