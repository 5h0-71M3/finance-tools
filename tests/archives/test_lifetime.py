from datetime import datetime
from decimal import Decimal

import pandas as pd
from dirlin import Folder

from archives.insured_page.objects.enums.netsuite import EnumDescription
from archives.report import NodeTransaction, SequencePipeline


def test_transaction_node_init():
    key = 4529910
    exid = "CCP1001174-06-CA-1000-RN"
    report_date = datetime(2024, 4, 14)
    create_date = datetime(2024, 4, 14, 12, 18)
    description = EnumDescription("Issuance")

    t = NodeTransaction(key, exid, "ifasd9fiasd0f9iasd09f", description, report_date, create_date, create_date, Decimal(f"2.00"), "No")
    assert isinstance(t, NodeTransaction)


def test_pipeline():
    df = Folder("/Users/shomendoza/Downloads").open_recent("DataQualityDailyTransactionCheckAllTransactionsSTMResults59")

    for d in ["T Effective Date", "Date Created", "Effective Date"]:
        df[d] = pd.to_datetime(df[d], errors="coerce")

    df = df[df["--Coalition Policy Number--"] == "C-4MQ0-072564-CYBER-2023"].copy()
    df = df.sort_values(by=["Internal ID", "Date Created"])
    print(df["Internal ID"])

    enum_mapping = {
        "Cancellation - Flat": EnumDescription.cancellation_flat,
        "Cancellation - Pro-Rated": EnumDescription.cancellation_pro,
        "Endorsement": EnumDescription.endorsement,
        "Issuance": EnumDescription.issuance,
        "Reinstatement": EnumDescription.reinstatement,
        "soft delete": EnumDescription.soft_delete,
    }

    nodes = [
        NodeTransaction(
            key=k,
            transaction_id=tid,
            description=enum_mapping[d],
            policy_uuid=puuid,
            report_date=rd,
            create_date=cd,
            effective_date=ed,
            premium=p,
            be_sd=besd
        ) for k, tid, puuid, rd, cd, ed, p, d, besd in zip(
            df["Internal ID"],
            df["-------------Transaction ID-------------"],
            df["Policy UUID"],
            df["T Effective Date"],
            df["Date Created"],
            df["Effective Date"],
            df["TBP"],
            df["Description"],
            df["Binder Edit/Soft Delete Complete"]
        )
    ]

    pipeline = SequencePipeline()
    result = pipeline.run_pipline(nodes, verbose=True)
    print(result)
