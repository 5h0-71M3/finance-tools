from datetime import datetime, timedelta

import pandas as pd
import pgeocode

_us_state_codes = {
    "AK": "Alaska",
    "AL": "Alabama",
    "AR": "Arkansas",
    "AZ": "Arizona",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DC": "District of Columbia",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "IA": "Iowa",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "MA": "Massachusetts",
    "MD": "Maryland",
    "ME": "Maine",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MO": "Missouri",
    "MS": "Mississippi",
    "MT": "Montana",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "NE": "Nebraska",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NV": "Nevada",
    "NY": "New York",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VA": "Virginia",
    "VT": "Vermont",
    "WA": "Washington",
    "WI": "Wisconsin",
    "WV": "West Virginia",
    "WY": "Wyoming",
}


def check_zip_code_matches(zip_codes: pd.Series, states: pd.Series) -> pd.Series:
    # Initialize the library for the United States ('us').
    # The first time you run this, it will download the data file.
    nomi = pgeocode.Nominatim('us')

    # --- ZIP Code Lookup ---
    expected_states = zip_codes.apply(lambda zc: nomi.query_postal_code(zc))
    return pd.Series(expected_states == states)


def expected_state(zip_codes: str) -> str:
    nomi = pgeocode.Nominatim('us')
    expected_states = nomi.query_postal_code(zip_codes)
    return expected_states.loc["state_name"]


def zip_code_variances(
        zip_codes: pd.Series,
        states: pd.Series,
) -> pd.DataFrame:
    _p_start = datetime.now()

    print(f"Creating new DataFrame...{datetime.now()}")
    _start = datetime.now()
    # === Clean the Data and Align It ===
    zip_codes = zip_codes.fillna("Missing")
    zip_codes = zip_codes.str.split("-").str[0]

    states = states.fillna("Missing")
    df = pd.concat([zip_codes, states], axis=1)
    df.columns = ["Insured Zip Code", "Insured State Code"]
    nomi = pgeocode.Nominatim('us')
    _end = datetime.now()
    d4 = f"{int((_end - _start).total_seconds() // 60)}m {round((_end - _start).total_seconds() % 60, 2)*100}s"
    print(f"New DataFrame created...{d4}")

    print()
    print("---")
    print()

    # === Setting the Hashmap for Correct Zip-State pairs ===
    _start = datetime.now()
    print(f"Identifying unique zip codes...{_start}")
    unique_zips = zip_codes.unique().tolist()
    correct_states = {
        z: nomi.query_postal_code(z).loc["state_name"] for z in unique_zips if z is not None
    }  # zips by unique zips
    _end = datetime.now()
    d1 = f"{int((_end - _start).total_seconds() // 60)}m {round((_end - _start).total_seconds() % 60, 2)*100}s"
    print(f"Unique zip codes identified...{d1}")

    print()
    print("---")
    print()

    print(f"Creating mapping for states...{datetime.now()}")
    _start = datetime.now()
    _end = datetime.now()
    d2 = f"{int((_end - _start).total_seconds() // 60)}m {round((_end - _start).total_seconds() % 60, 2)*100}s"
    print(f"State mapping created...{d2}")

    print()
    print("---")
    print()

    # === Using the Map to Create Second Column and create DataFrame ===
    print(f"Applying expected states to existing states...{datetime.now()}")
    _start = datetime.now()
    df["Expected State"] = [_tie_zip_code(correct_states, z) for z in df["Insured Zip Code"].values]
    _end = datetime.now()
    d3 = f"{int((_end - _start).total_seconds() // 60)}m {round((_end - _start).total_seconds() % 60, 2)*100}s"
    print(f"Expected states applied...{d3}")

    print()
    print("---")
    print()

    print(f"Matching Results...{datetime.now()}")
    _start = datetime.now()
    df["Insured State"] = [_tie_zip_code(_us_state_codes, ns) for ns in df["Insured State Code"]]
    df["Checked"] = df["Insured State"] == df["Expected State"]
    _end = datetime.now()
    d5 = f"{int((_end - _start).total_seconds() // 60)}m {round((_end - _start).total_seconds() % 60, 2)*100}s"
    print(f"Results matched...{d5}")

    print()
    print("---")
    print()

    _p_end = datetime.now()
    print(f"Total Runtime: {_p_end - _p_start}")
    print(f"Unique Zipcodes: {d1}")
    print(f"State Mapping: {d2}")
    print(f"Applying Mapping: {d3}")
    print(f"New DataFrame: {d4}")
    print(f"Matched Results: {d5}")
    return df


def _tie_zip_code(mapping: dict, code: str | int) -> str | None:
    try:
        return mapping[code]
    except KeyError:
        if "-" in code:
            code = code.split("-")[0]
            try:
                return mapping[code]
            except KeyError:
                print(f"{code} is not a valid zip code")
                return None
        print(f"Invalid Code: {code}")
    return None

