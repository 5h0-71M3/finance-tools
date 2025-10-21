# Soft Delete File For Aspen
from datetime import date

from finance_tools.io import FOLDERS


DIR = FOLDERS()


# USE THE CLI VERSION 2025/07/08
def aspen_sd(f: FOLDERS):
    """used for pulling a Soft Delete Report for Aspen.
    This is part of their final deliverable.
    """
    df = f.get_master_log()
    df.to_excel(f.DOWNLOADS / f"All Master Log - Soft Deletes - {date.today()}.xlsx")


if __name__ == "__main__":
    aspen_sd(DIR)
