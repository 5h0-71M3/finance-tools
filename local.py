from datetime import date

# from finance_tools.bar.core.checks.zipcodes import zip_code_variances
from finance_tools.io import FOLDERS
from finance_tools.io.directory_handler import get_master_files, data_cleaner

# df = f.get_policy_list()
# df["Expected State"] = df["Insured Zip Code"].apply(lambda z: expected_state(z))
# df.to_csv(f"With Expected Zip - {date.today()} - policy_list.csv")

# df = f.DOWNLOADS.find_and_combine("Exec Risks Zurich Premium Report")
# df.to_csv(f.DOWNLOADS / f"Exec Risk - ITD - {date.today()}.csv")


# path = f.DESKTOP / f"Antares Looker" / "Antares (Sho Copy) - ITD - 2025-09-12.csv"
# df = f.DESKTOP.open(path)
#
# pol = [
#     "C-4LPB-194125-MLPSME-2025",
#     "C-4LPM-128185-MLPSME-2025",
#     "C-4LPM-128188-MLPSME-2025",
#     "C-4LQV-199649-MLPSME-2025",
#     "C-4LR7-020341-MLPSME-2025",
#     "C-4LWD-116244-MLPSME-2025",
#     "C-4M0U-065345-MLPSME-2025",
#     "C-4LPD-116796-MLPSME-2025",
#
#     "C-4LPO-083808-MLPSME-2025",
#     "C-4LQ8-212648-MLPSME-2025",
#     "C-4LR7-019920-MLPSME-2025",
#     "C-4LR7-020267-MLPSME-2025",
#     "C-4LRL-036945-MLPSME-2024",
#     "C-4M0D-222835-MLPSME-2025",
# ]
#
# columns = ["Policy Number", "Quote Coalition Policy Number"]
#
# pop1 = df[df["Policy Number"].isin(pol)].copy()
# pop2 = df[df["Quote Coalition Policy Number"].isin(pol)].copy()
#
# final = pd.concat([pop1, pop2])
# final.to_csv(f.DESKTOP / f"Antares Looker" / f"Antares ITD - Select Policies - {date.today()} - 3.csv")

# zips = (
#     "20705",
#     "30080",
#     "19901",
#     "07960",
#     "19001",
# )
#
# _expected_state = [expected_state(z) for z in zips]
# print(_expected_state)

# pl = f.get_policy_list()
# subsidiary_mask = pl["Subsidiary [Agency Customer]"] == "ProForma : GAAP : MGA Consolidation : Coalition, Inc"
# pl = pl[subsidiary_mask].copy()
# pl = pl.set_index("Internal ID", drop=True)
#
# df = zip_code_variances(zip_codes=pl["Insured Zip Code"], states=pl["Insured State"])
# df.to_csv(f.DOWNLOADS / f"Zip Code Variances - ITD - {date.today()}.csv")

# data_cleaner(
#     f.DESKTOP / f"Masters",
#     export_path=f.DOWNLOADS,
#     query_path=f.DEVELOPER / "finance-tools/src/finance_tools/core/sql/master_file.sql.j2",
#     out_path=f.DOWNLOADS / f"Masters.parquet"
# )


#


# df = get_master_files()
# df.to_csv(f.DOWNLOADS / f"First duckdb - {date.today()} - query.csv")
# print(df.info())

if __name__ == "__main__":
    f = FOLDERS()
    ...
