import datetime

from src.io.directory_handler import FOLDERS
from src.pipeline import TransactionLifecycle
from src.pipeline.core.policy_stack.creation import SortingAlgoInfo

f = FOLDERS()


def test_standard_sorting():
    report = f.get_stm_transactions()
    # cpn = ["C-4LPY-058865-CYBER-2025"]  # the test
    # report = report[report["--Coalition Policy Number--"].isin(cpn)].copy()

    algo = SortingAlgoInfo()  # standard
    pipline = TransactionLifecycle(report)

    ordered_df = pipline._order_itd(report, sorting_algo=algo)
    final_columns = [
        "Internal ID",
        "-------------Transaction ID-------------",
        "Description",
        "Endorsement Number",
        "--Coalition Policy Number--",
        "Soft Delete",
        "Module",
        "Binder Edit",
        "TBP",
        "Binder Edit Index",
        "Soft Delete Index",
        "Mod Index",
        "Policy Index",
        "Sequence Index",
    ]
    ordered_df[final_columns].to_csv(f.DOWNLOADS / f"Standard Order - Test - {datetime.datetime.now().strftime('%d%m%Y_%H_%M_%S')} - all.csv")




