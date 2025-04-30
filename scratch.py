from datetime import date

from src.file_handling.directory_handler import FOLDERS
from src.tasks.carrier_ad_hoc import lloyds_umr_bound_against
from src.tasks.close import Closer

######################################################################################
# Arch Mapping
######################################################################################
# arch_ns = Directory.DOWNLOADS.open("DataQualityBlankSTMResults619.csv")
# from_arch = Directory.DOWNLOADS.open("Arch assigned Coalition ITD policy numbers.xlsx")
#
# filter_is_missing_policy_number = arch_ns["Arch Policy Number"].isna()
# arch_ns = arch_ns[filter_is_missing_policy_number]
# arch_ns_mapping = {arch_number: True for arch_number in arch_ns["Arch Policy Number"]}
#
# print(arch_ns.info())
# print(from_arch.info())


######################################################################################
# ARCH SPLITTING for uploads
######################################################################################
# def split_df_into_chunks(df, chunk_size=10000) -> list[pd.DataFrame]:
#     chunks = []  # storing the chunked dataframe
#     number_of_chunks = math.ceil(len(df) / chunk_size)
#     for i in range(number_of_chunks):
#         chunks.append(df[i*chunk_size: (i+1)*chunk_size])
#     return chunks
#
#
# arch_ed_file = Directory.DOWNLOADS.open("Arch Recon - 2025.03.19 - EL Review.xlsx", sheet_name=1)
# arch_blank = Directory.DOWNLOADS.open("DataQualityBlankSTMResults44.csv")
#
# print("BEFORE")
# print(len(arch_ed_file[arch_ed_file["Internal ID"].isna()]))
# print(arch_blank.info())
# print(arch_ed_file.info())
# print("===")
# print()
#
# arch_blank = arch_blank[["Internal ID", "Transaction ID (ExtID)"]]
# backup = arch_ed_file[~arch_ed_file["Arch_Policy_Number"].isna()].merge(arch_blank, how="left", right_on="Transaction ID (ExtID)", left_on="POLICY1_EXTID", suffixes=("_ed", None)).reset_index(drop=True)
# backup = backup[backup["Transaction ID (ExtID)"].isin(arch_ed_file["POLICY1_EXTID"])]
#
# _move_iid = backup.pop("Internal ID")
# backup.insert(0, "Internal ID", _move_iid)
#
# print("AFTER")
# print(len(backup[backup["Internal ID"].isna()]))
# print(backup.info())
# print("===")
# print()
#
# print("---")
# print(len(backup["Internal ID"].isna()))
#
# chunked_dfs = split_df_into_chunks(backup)
# for idx, chunk in enumerate(chunked_dfs):
#     chunk.to_csv(Directory.DOWNLOADS.path / f"Arch Upload - {date.today()} - {idx + 1} of {len(chunked_dfs)}.csv", index=False)

######################################################################################


#######################################################################################
# Sample File for Surplus
#######################################################################################
# limit_file = Directory.DOWNLOADS.open("DataQualityLimitsSTMResults385.csv", )
#
# ac_path = Directory.ACCOUNT_CURRENT.path / "2025-02"
# arch = Directory.DOWNLOADS.open("ArchAccountCurrentwithReinsuranceUpdatedResults990.csv")
# chaucer = Directory.as_custom_folder_path(ac_path).open_recent("ChaucerAccountCurrent-February 2025 (post July 2024)", recurse=True)
# fortegra = Directory.as_custom_folder_path(ac_path).open_recent("FortegraAccountCurrent - February - 2025.02", recurse=True)
# allianz = Directory.as_custom_folder_path(ac_path).open_recent("AllianzAccountCurrentResults - 02.2025", recurse=True)
# aspen = Directory.as_custom_folder_path(ac_path).open_recent("AspenAccountCurrent - 2025.02", recurse=True)
# vantage = Directory.as_custom_folder_path(ac_path).open_recent("VantageAccountCurrentResults202502", recurse=True)
# carriers = [
#     (arch, "Arch"),
#     (chaucer, "Chaucer"),
#     (fortegra, "Fortegra"),
#     (allianz, "Allianz"),
#     (aspen, "Aspen"),
#     (vantage, "Vantage")
# ]
#
# # Formatting the Limit File to get it ready for merging and formatting
# used_columns = ["Aggregate Total Limit", "Business Interruption And Extra"]
# for column in used_columns:
#     limit_file[column] = pd.to_numeric(limit_file[column], errors='coerce').fillna(0)
#
# # Formatting based on the Surplus 3.0 File provided by Michael
# limit_file["Breach Response Separate Limit"] = [5_000_000 if agg > 5000000 else 0 for agg in limit_file["Aggregate Total Limit"]]
# limit_file["Direct Business Interruption Security"] = [agg for agg in limit_file["Aggregate Total Limit"]]
# limit_file["Direct Business Interruption Shutdown"] = [agg for agg in limit_file["Aggregate Total Limit"]]
# limit_file["Direct Business Interruption System"] = [agg for agg in limit_file["Aggregate Total Limit"]]
# limit_file["Contingent Business Interruption"] = [bi for bi in limit_file["Business Interruption And Extra"]]
# limit_file["Contingent Business Interruption Security"] = [bi for bi in limit_file["Business Interruption And Extra"]]
# limit_file["Contingent Business Interruption System"] = [bi for bi in limit_file["Business Interruption And Extra"]]
# limit_file["Contingent Business Interruption Shutdown"] = [bi for bi in limit_file["Business Interruption And Extra"]]
# limit_file["Contingent Business Interruption Non IT Security"] = [(bi * .5) for bi in limit_file["Business Interruption And Extra"]]
# limit_file["Contingent Business Interruption Non IT System"] = [bi * .25 for bi in limit_file["Business Interruption And Extra"]]
# limit_file["Missed Bid"] = [500_000 for _ in limit_file["Internal ID"]]
# limit_file["Corrective Action Plan"] = [250_000 for _ in limit_file["Internal ID"]]
# limit_file["Enhanced Privacy"] = [100_000 for _ in limit_file["Internal ID"]]
# limit_file["Per Event Limit"] = [0 for _ in limit_file["Internal ID"]]
#
# surplus_3_columns = [
#     "Internal ID",
#     "Breach Response Separate Limit",
#     "Direct Business Interruption Security",
#     "Direct Business Interruption Shutdown",
#     "Direct Business Interruption System",
#     "Contingent Business Interruption",
#     "Contingent Business Interruption Security",
#     "Contingent Business Interruption System",
#     "Contingent Business Interruption Shutdown",
#     "Contingent Business Interruption Non IT Security",
#     "Contingent Business Interruption Non IT System",
#     "Missed Bid",
#     "Corrective Action Plan",
#     "Enhanced Privacy",
#     "Per Event Limit"
# ]
# limit_file = limit_file[surplus_3_columns].copy()
#
# for carrier in carriers:
#     df = carrier[0].merge(limit_file, on="Internal ID", how="left")
#     df.to_csv(Directory.DOWNLOADS.path / f"{carrier[1]} - Surplus 3_0 - Sample - {date.today()}.csv", index=False)

######################################################################################

# (carrier, quota_share) ex. Ascot
# (carrier, quota_share, subsidiary) ex. Allianz US
# carrier, quota_share, subsidiary, UMR) ex. Lloyds UK
# (carrier, quota_share, subsidiary, excess layer) ex. Allianz UK

# Soft Delete File For Aspen
# f = FOLDERS()
# df = f.get_master_log()
# df.to_excel(f.DOWNLOADS / f"All Master Log - Soft Deletes - {date.today()}.xlsx")

###########################
# FOLDER CALLS AND REPORTS
###########################
f = FOLDERS()
pl = f.get_policy_list()
##########################
# df = f.get_master_log(tab="master")
# print(df.head())
# df.to_csv(f.DOWNLOADS / f"ITD Master Log - Reported - {date.today()}.csv")

# df = export_masterfile_reported()
# df.to_csv(f.DOWNLOADS / f"Reported Masterfile - {date.today()}.csv")
# print(df)

# pl = f.DOWNLOADS.open_recent("PolicyList")
# df = gather_concat_reports(policy_list=pl)
# df.to_csv(f.DOWNLOADS / f"policy_list - expected vs on master {date.today()}.csv")

# find_erp_with_inactive_policy()
#f.generate_arch_number_upload()
# confirm_arch_commissions(write=True)

# match_arch_policy_number()


#######################
# CLOSE
#######################
# c = Closer()
#
# df = c.close_month(pl)
# df.to_csv(f.DOWNLOADS / f"Close Report_{date.today()}.csv")
#########################

# Lloyds Request
df = lloyds_umr_bound_against()
df.to_excel(f.DOWNLOADS / f"Request (Grouped) - Lloyds UK and Canada - 2024 UMR - 2025.04 Policy Effective Date.xlsx")
