from dirlin.pipeline import Report

from src.pipeline.reports.metadata.bdx.arch import (
    arch_field_mapping,
    arch_cash_columns,
    arch_float_columns,
    arch_int_columns
)

from src.pipeline.reports.metadata.bdx.allianz_us import (
    allianz_us_field_mapping,
    allianz_cash_columns,
    allianz_float_columns,
    allianz_int_columns
)

ArchBDX = Report(
    name_convention="Arch",
    field_mapping=arch_field_mapping,
    column_type_floats=arch_float_columns,
    column_type_ints=arch_int_columns,
    column_type_cash=arch_cash_columns,
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
