"""Tests unitaires — nettoyage et features."""
import pandas as pd
import numpy as np
import pytest


def make_sample_data(n=100):
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "machine_id": np.repeat(range(1, 6), n // 5),
        "cycle_number": np.tile(range(1, n // 5 + 1), 5),
        **{f"sensor_{i}": rng.normal(400 + i * 10, 5, n) for i in range(1, 22)},
    })


def test_no_nan_after_dedup():
    df = make_sample_data()
    df_clean = df.drop_duplicates()
    assert df_clean.isna().sum().sum() == 0


def test_rul_positive():
    df = make_sample_data()
    df["RUL"] = df.groupby("machine_id")["cycle_number"].transform("max") - df["cycle_number"]
    assert (df["RUL"] >= 0).all()


def test_risk_level_no_missing():
    df = make_sample_data()
    df["RUL"] = df.groupby("machine_id")["cycle_number"].transform("max") - df["cycle_number"]
    df["risk_level"] = pd.cut(df["RUL"], bins=[-1, 8, 24, np.inf],
                               labels=["a_risque", "a_surveiller", "normal"])
    assert df["risk_level"].isna().sum() == 0


def test_machine_id_format():
    df = make_sample_data()
    df["machine_id"] = "MECHA-USI-" + df["machine_id"].astype(str).str.zfill(3)
    assert df["machine_id"].str.startswith("MECHA-USI-").all()
