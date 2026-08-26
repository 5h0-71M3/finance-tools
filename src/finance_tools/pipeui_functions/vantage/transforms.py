import pandas as pd


def parse_datetime_column(field: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(field, errors="coerce", format="mixed")
    formatted = parsed.dt.strftime("%-m/%-d/%y %-H:%M")
    fallback = field.astype(object).where(field.notna(), "")
    return formatted.where(formatted.notna(), fallback)
