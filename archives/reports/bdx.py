from datetime import date

from dirlin.pipeline import Report

from archives.reports.metadata.bdx.allianz_aus import allianz_aus_field_mapping
from archives.reports.metadata.bdx.allianz_germany import allianz_germany_field_mapping, \
    allianz_germany_float_columns, allianz_germany_cash_columns
from archives.reports.metadata.bdx.allianz_uk import allianz_uk_field_mapping
from archives.reports.metadata.bdx.arch import (
    arch_field_mapping,
    arch_cash_columns,
    arch_float_columns,
    arch_int_columns
)

from archives.reports.metadata.bdx.allianz_us import (
    allianz_us_field_mapping,
    allianz_cash_columns,
    allianz_float_columns,
    allianz_int_columns
)

from archives.reports.metadata.bdx.ascot import (
    ascot_field_mapping,
    ascot_float_columns,
    ascot_int_columns,
    ascot_cash_columns
)

from archives.reports.metadata.bdx.lloyds_non_us import (
    lloyds_can_field_mapping,
    lloyds_cash_columns,
    lloyds_float_columns,
    lloyds_int_columns
)

from archives.reports.metadata.bdx.vantage import (
    vantage_field_mapping,
    vantage_cash_columns,
    vantage_float_columns,
    vantage_int_columns
)

##############################
# DATE AND NAME HANDLING
##############################
previous_month = date.today().month - 1
year = date.today().year if previous_month != 12 else date.today().year - 1

_allianz_aus_format_aus = f"AllianzAUSAccountCurrentResults - {year}.{previous_month} (AUS Format)"
_allianz_aus_format_uk = f"AllianzAUSAccountCurrentResults - {year}.{previous_month} (UK Format)"
_allianz_uk_primary = f"AllianzAccountUKCurrentResults - {previous_month}.{year} - Primary"
_allianz_uk_excess = f"AllianzAccountUKCurrentResults - {previous_month}.{year} - Excess"
_lloyds_uk_2023 = f"LloydsUKAccountCurrent - {previous_month}.{year} (2023)"
_lloyds_uk_2024 = f"LloydsUKAccountCurrent - {previous_month}.{year} (2024)"
_lloyds_canada_2023 = f"LloydsCanadaAccountCurrent - {previous_month}.{year} (2023)"
_lloyds_canada_2024 = f"LloydsCanadaAccountCurrent - {previous_month}.{year} (2024)"

###############################
# REPORT CREATION
###############################

ArchBDX = Report(
    name_convention="Arch",
    field_mapping=arch_field_mapping,
    column_type_floats=arch_float_columns,
    column_type_ints=arch_int_columns,
    column_type_cash=arch_cash_columns,
    key_cash_column="tbp"
)


AllianzAusFormatAusBDX = Report(
    name_convention=_allianz_aus_format_aus,
    field_mapping=allianz_aus_field_mapping,
    key_cash_column="tbp"
)

AllianzAusFormatUKBDX = Report(
    name_convention=_allianz_aus_format_uk,
    field_mapping=allianz_uk_field_mapping,
    column_type_floats=allianz_float_columns,
    column_type_ints=allianz_int_columns,
    column_type_cash=allianz_cash_columns,
    key_cash_column="tbp"
)

AllianzDEBDX = Report(
    name_convention="AllianzDEAccountCurrentResults",
    field_mapping=allianz_germany_field_mapping,
    column_type_floats=allianz_germany_float_columns,
    column_type_cash=allianz_germany_cash_columns,
    key_cash_column="tbp"
)

AllianzUKPrimaryBDX = Report(
    name_convention=_allianz_uk_primary,
    field_mapping=allianz_uk_field_mapping,
    column_type_floats=allianz_float_columns,
    column_type_ints=allianz_int_columns,
    column_type_cash=allianz_cash_columns,
    key_cash_column="tbp"
)

AllianzUKExcessBDX = Report(
    name_convention=_allianz_uk_excess,
    field_mapping=allianz_uk_field_mapping,
    column_type_floats=allianz_float_columns,
    column_type_ints=allianz_int_columns,
    column_type_cash=allianz_cash_columns,
    key_cash_column="tbp"
)

AllianzUsBDX = Report(
    name_convention="AllianzAccountCurrentResults",
    field_mapping=allianz_us_field_mapping,
    column_type_floats=allianz_float_columns,
    column_type_ints=allianz_int_columns,
    column_type_cash=allianz_cash_columns,
    key_cash_column="tbp"
)

AscotBDX = Report(
    name_convention="AscotMonthlyAccountCurrent",
    field_mapping=ascot_field_mapping,
    column_type_floats=ascot_float_columns,
    column_type_ints=ascot_int_columns,
    column_type_cash=ascot_cash_columns,
    key_cash_column="tbp"
)

LloydsUK2023BDX = Report(
    name_convention=_lloyds_uk_2023,
    field_mapping=lloyds_can_field_mapping,
    column_type_floats=lloyds_float_columns,
    column_type_ints=lloyds_int_columns,
    column_type_cash=lloyds_cash_columns,
    key_cash_column="tbp"

)

LloydsUK2024BDX = Report(
    name_convention=_lloyds_uk_2024,
    field_mapping=lloyds_can_field_mapping,
    column_type_floats=lloyds_float_columns,
    column_type_ints=lloyds_int_columns,
    column_type_cash=lloyds_cash_columns,
    key_cash_column="tbp"

)

LloydsCanada2023BDX = Report(
    name_convention=_lloyds_canada_2023,
    field_mapping=lloyds_can_field_mapping,
    column_type_floats=lloyds_float_columns,
    column_type_ints=lloyds_int_columns,
    column_type_cash=lloyds_cash_columns,
    key_cash_column="tbp"

)

LloydsCanada2024BDX = Report(
    name_convention=_lloyds_canada_2024,
    field_mapping=lloyds_can_field_mapping,
    column_type_floats=lloyds_float_columns,
    column_type_ints=lloyds_int_columns,
    column_type_cash=lloyds_cash_columns,
    key_cash_column="tbp"

)

VantageBDX = Report(
    name_convention="VantageAccountCurrentResults",
    field_mapping=vantage_field_mapping,
    column_type_floats=vantage_float_columns,
    column_type_ints=vantage_int_columns,
    column_type_cash=vantage_cash_columns,
    key_cash_column="tbp"
)
