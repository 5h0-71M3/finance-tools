"""Not sure how to stress the importance, but this page is pretty important"""

from enum import Enum


class Subsidiaries(Enum):
    us = "ProForma : GAAP : MGA Consolidation : Coalition, Inc"
    canada = "ProForma : GAAP : MGA Consolidation : Coalition, Inc : Coalition Insurance Solutions Canada Inc."
    uk = "ProForma : GAAP : MGA Consolidation : Coalition, Inc : Coalition Risk Solutions Ltd."
    aus = "ProForma : GAAP : MGA Consolidation : Coalition, Inc : Coalition AUS"
    deu = "ProForma : GAAP : MGA Consolidation : Coalition, Inc : Germany GmbH"


def _reported_headers():
    # Part 1: Get Headers from the Masterfile related to Reported
    reported_headers = [
        "Reported - Allianz UK",
        "Reported - Allianz USA",
        "Reported - Arch CAN",
        "Reported - Argo",
        "Reported - Ascot",
        "Reported - Chaucer",
        "Reported - Fortegra",
        "Reported - Lloyds USA",
        "Reported - Lloyds CAN",
        "Reported - Lloyds UK",
        "Reported - Swiss Re USA",
        "Reported - Swiss Re CAN",
        "Reported - Vantage",
        "Reported - Zurich"
    ]
    return reported_headers


def _reported_date_headers():
    # Part 2: Get headers from the Masterfile related to Report Date
    reported_date_headers = [
        "Reported - Allianz UK Date",
        "Reported - Allianz USA Date",
        "Reported - Arch CAN Date",
        "Reported - Arch USA Date",
        "Reported - Argo Date",
        "Reported - Ascot Date",
        "Reported - Chaucer Date",
        "Reported - Fortegra Date",
        "Reported - Lloyds USA Date",
        "Reported - Lloyds CAN Date",
        "Reported - Lloyds UK Date",
        "Reported - Swiss Re USA Date",
        "Reported - Swiss Re CAN Date",
        "Reported - Vantage Date",
        "Reported - Zurich Date"
    ]
    return reported_date_headers


def _quota_share_headers():
    # Part 3: Get headers related to quota share to create the file
    quota_share_headers = [
        "Allianz Quota Share",
        "Arch Quota Share",
        "Argo %",
        "Ascot Quota Share",
        "Aspen Quota Share",
        "Chaucer Quota Share",
        "Fortegra Quota Share",
        "Hartford Quota Share",
        "HDI Quota Share",
        "Lloyds Quota Share",
        "MSIG Quota Share",
        "Swiss Re %",
        "Vantage Quota Share",
        "Zurich Quota Share",
    ]
    return quota_share_headers


def carrier_info_tuples() -> dict[str, tuple]:
    """just a tuple with the carrier information we need to process the reported
    without needing to depend on too many functions or mapping

    (0) quota share header
    (1) carrier subsidiary name
    (2) carrier reported header
    (3) carrier reported date header
    (4) report date
    (5) misc header for getting the correct filter - None if empty
    (6) carrier commission %

    *Note that we didn't create a header function because we can get the headers
    for all specific types of header names by writing `header = [f[0] for f in mapping.values()]`

    **Note that we recommend putting the actual value listed above instead of going the reverse
    index position [-1] incase you add new values in the future. (5) used to be the last value,
    but now it's 6 as of date.


    Mapping:
        - "zurich_us": zurich_us,
        - "vantage_us": vantage_us,
        - "swissre_can": swissre_can,
        - "swissre_us": swissre_us,
        - "msig_aus": msig_aus,
        - "lloyds_us": lloyds_us,
        - "lloyds_uk": lloyds_uk,
        - "lloyds_can": lloyds_can,
        - "hdi_can": hdi_can,
        - "hartford_uk": hartford_uk,
        - "fortegra_us": fortegra_us,
        - "chaucer_us": chaucer_us,
        - "aspen_us": aspen_us,
        - "ascot_us": ascot_us,
        - "argo_us": argo_us,
        - "arch_us": arch_us,
        - "arch_can": arch_can,
        - "allianz_uk": allianz_uk,
        - "allianz_us": allianz_us,
        - "allianz_deu": allianz_deu,
        - "allianz_aus": allianz_aus,

    """

    # when adding new carriers, make sure to add it to the mapping
    zurich_us = (
        "Zurich Quota Share",
        Subsidiaries.us.value,
        "Reported -  Zurich",
        "Reported - Zurich Date",
        10,
        None,
        "Zurich % Commission to Coalition"
    )

    vantage_us = (
        "Vantage Quota Share",
        Subsidiaries.us.value,
        "Reported - Vantage",
        "Reported - Vantage Date",
        3,
        None,
        "Vantage % Commission To Coalition",
    )

    swissre_can = (
        "Swiss Re %",
        Subsidiaries.canada.value,
        "Reported - Swiss Re CAN",
        "Reported - Swiss Re CAN Date",
        15,
        None,
        "SRe %Commission to Coalition",
    )

    swissre_us = (
        "Swiss Re %",
        Subsidiaries.us.value,
        "Reported - Swiss Re USA",
        "Reported - Swiss Re USA Date",
        15,
        None,
        "SRe %Commission to Coalition",
    )

    msig_aus = (
        "MSIG Quota Share",
        Subsidiaries.aus.value,
        "Reported - MSIG",
        "Reported - MSIG Date",
        10,
        None,
        "MSIG % Commission To Coalition",
    )

    lloyds_us = (
        "Lloyds Quota Share",
        Subsidiaries.us.value,
        "Reported - Lloyds USA",
        "Reported - Lloyds USA Date",
        15,
        None,
        "Lloyds %Commission to Coalition",
    )

    lloyds_uk = (
        "Lloyds Quota Share",
        Subsidiaries.uk.value,
        "Reported - Lloyds UK",
        "Reported - Lloyds UK Date",
        5,
        None,
        "Lloyds %Commission to Coalition",
    )

    lloyds_can = (
        "Lloyds Quota Share",
        Subsidiaries.canada.value,
        "Reported - Lloyds CAN",
        "Reported - Lloyds CAN Date",
        5,
        None,
        "Lloyds %Commission to Coalition",
    )

    hdi_can = (
        "HDI Quota Share",
        Subsidiaries.canada.value,
        "Reported - HDI",
        "Reported - HDI Date",
        10,
        None,
        "HDI % Commission To Coalition"
    )

    hartford_uk = (
        "Hartford Quota Share",
        Subsidiaries.uk.value,
        "Reported - Hartford",
        "Reported - Hartford Date",
        10,
        None,
        "Hartford % Commission To Coalition",
    )

    fortegra_us = (
        "Fortegra Quota Share",
        Subsidiaries.us.value,
        "Reported - Fortegra",
        "Reported - Fortegra Date",
        10,
        None,
        "Fortegra % Commission To Coalition",
    )

    chaucer_us = (
        "Chaucer Quota Share",
        Subsidiaries.us.value,
        "Reported - Chaucer",
        "Reported - Chaucer Date",
        10,
        None,
        "Chaucer % Commission to Coalition",
    )

    aspen_us = (
        "Aspen Quota Share",
        Subsidiaries.us.value,
        "Reported - Aspen",
        "Reported - Aspen Date",
        10,
        None,
        "Aspen % Commission To Coalition",
    )

    ascot_us = (
        "Ascot Quota Share",
        Subsidiaries.us.value,
        "Reported - Ascot",
        "Reported - Ascot Date",
        5,
        None,
        "Ascot % Commission To Coalition",
    )

    argo_us = (
        "Argo %",
        Subsidiaries.uk.value,
        "Reported - Argo",
        "Reported - Argo Date",
        10,
        None,
        "Argo %Commission to Coalition",
    )

    arch_can = (
        "Arch Quota Share",
        Subsidiaries.uk.value,
        "Reported - Arch CAN",
        "Reported - Arch CAN Date",
        3,
        None,
        "Arch % Commission to Coalition",
    )

    arch_us = (
        "Arch Quota Share",
        Subsidiaries.us.value,
        "Reported - Arch USA",
        "Reported - Arch USA Date",
        3,
        None,
        "Arch % Commission to Coalition",
    )

    allianz_uk = (
        "Allianz Quota Share",
        Subsidiaries.uk.value,
        "Reported - Allianz UK",
        "Reported - Allianz UK Date",
        5,
        None,
        "Allianz % Commission To Coalition",
    )

    allianz_us = (
        "Allianz Quota Share",
        Subsidiaries.us.value,
        "Reported - Allianz USA",
        "Reported - Allianz USA Date",
        5,
        None,
        "Allianz % Commission To Coalition",
    )

    allianz_deu = (
        "Allianz Quota Share",
        Subsidiaries.deu.value,
        "Reported - Allianz DEU",
        "Reported - Allianz DEU Date",
        5,
        None,
        "Allianz % Commission To Coalition",
    )

    allianz_aus = (
        "Allianz Quota Share",
        Subsidiaries.aus.value,
        "Reported - Allianz AUS",
        "Reported - Allianz AUS Date",
        5,
        None,
        "Allianz % Commission To Coalition",
    )

    mapping = {
        "zurich_us": zurich_us,
        "vantage_us": vantage_us,
        "swissre_can": swissre_can,
        "swissre_us": swissre_us,
        "msig_aus": msig_aus,
        "lloyds_us": lloyds_us,
        "lloyds_uk": lloyds_uk,
        "lloyds_can": lloyds_can,
        "hdi_can": hdi_can,
        "hartford_uk": hartford_uk,
        "fortegra_us": fortegra_us,
        "chaucer_us": chaucer_us,
        "aspen_us": aspen_us,
        "ascot_us": ascot_us,
        "argo_us": argo_us,
        "arch_us": arch_us,
        "arch_can": arch_can,
        "allianz_uk": allianz_uk,
        "allianz_us": allianz_us,
        "allianz_deu": allianz_deu,
        "allianz_aus": allianz_aus,
    }
    return mapping
