"""Tests unitaires — winsorisation, détection de capteur défaillant."""
import pandas as pd
import numpy as np
import pytest

from src.cleaning import winsorize_by_machine, detect_sensor_alerts, clean_and_bound_simple, capteur_principal


def make_machine_data(n_cycles=50, seed=42):
    """Une machine, un capteur stable + quelques valeurs aberrantes injectées."""
    rng = np.random.default_rng(seed)
    values = rng.normal(500, 5, n_cycles)
    return pd.DataFrame({
        "machine_id": 1,
        "cycle_number": range(1, n_cycles + 1),
        "sensor_1": values,
    })


def test_winsorize_caps_extreme_values():
    df = make_machine_data()
    # Injecte 2 valeurs extrêmes bien au-delà de l'IQR
    df.loc[10, "sensor_1"] = 9999
    df.loc[20, "sensor_1"] = -9999

    df_clean, events, n_capped = winsorize_by_machine(df, ["sensor_1"], k=3.0)

    assert n_capped == 2
    assert df_clean.loc[10, "sensor_1"] < 9999
    assert df_clean.loc[20, "sensor_1"] > -9999


def test_winsorize_preserves_normal_values():
    df = make_machine_data()
    df_clean, events, n_capped = winsorize_by_machine(df, ["sensor_1"], k=3.0)

    # Aucune valeur aberrante injectée -> rien ne doit être écrêté
    assert n_capped == 0
    pd.testing.assert_series_equal(df["sensor_1"], df_clean["sensor_1"])


def test_winsorize_preserves_degradation_trend():
    """Une tendance de dégradation progressive (pas des outliers ponctuels)
    ne doit pas être détruite par la winsorisation."""
    n = 100
    trend = np.linspace(500, 600, n)  # dégradation linéaire progressive
    df = pd.DataFrame({"machine_id": 1, "cycle_number": range(1, n + 1), "sensor_1": trend})

    df_clean, events, n_capped = winsorize_by_machine(df, ["sensor_1"], k=3.0)

    # La tendance de fin de vie ne doit quasiment pas être touchée (k=3 large)
    assert n_capped <= 2
    # La dernière valeur doit rester proche de sa valeur d'origine
    assert abs(df_clean["sensor_1"].iloc[-1] - trend[-1]) < 10


def test_winsorize_events_reference_correct_machine_and_cycle():
    df = make_machine_data()
    df.loc[15, "sensor_1"] = 9999

    df_clean, events, n_capped = winsorize_by_machine(df, ["sensor_1"], k=3.0)

    assert len(events) == 1
    assert events[0]["machine_id"] == 1
    assert events[0]["sensor"] == "sensor_1"
    assert events[0]["cycle_number"] == 16  # cycle_number = index + 1


def test_sensor_alert_triggers_at_threshold():
    events = [
        {"machine_id": 1, "sensor": "sensor_1", "cycle_number": 10},
        {"machine_id": 1, "sensor": "sensor_1", "cycle_number": 11},
        {"machine_id": 1, "sensor": "sensor_1", "cycle_number": 12},
    ]
    alerts = detect_sensor_alerts(events, threshold=3)

    assert len(alerts) == 1
    assert alerts.iloc[0]["machine_id"] == 1
    assert alerts.iloc[0]["sensor"] == "sensor_1"
    assert alerts.iloc[0]["nb_aberrations"] == 3


def test_sensor_alert_does_not_trigger_below_threshold():
    events = [
        {"machine_id": 1, "sensor": "sensor_1", "cycle_number": 10},
        {"machine_id": 1, "sensor": "sensor_1", "cycle_number": 11},
    ]
    alerts = detect_sensor_alerts(events, threshold=3)

    assert len(alerts) == 0


def test_sensor_alert_separates_different_sensors():
    """2 aberrations sur sensor_1 + 2 sur sensor_2 sur la même machine ne
    doivent PAS se cumuler en une alerte : chaque capteur est indépendant."""
    events = [
        {"machine_id": 1, "sensor": "sensor_1", "cycle_number": 10},
        {"machine_id": 1, "sensor": "sensor_1", "cycle_number": 11},
        {"machine_id": 1, "sensor": "sensor_2", "cycle_number": 12},
        {"machine_id": 1, "sensor": "sensor_2", "cycle_number": 13},
    ]
    alerts = detect_sensor_alerts(events, threshold=3)

    assert len(alerts) == 0  # aucun des deux capteurs n'atteint 3 seul


def test_sensor_alert_separates_different_machines():
    """Le même capteur sur 2 machines différentes ne doit pas se cumuler."""
    events = [
        {"machine_id": 1, "sensor": "sensor_1", "cycle_number": 10},
        {"machine_id": 1, "sensor": "sensor_1", "cycle_number": 11},
        {"machine_id": 2, "sensor": "sensor_1", "cycle_number": 10},
    ]
    alerts = detect_sensor_alerts(events, threshold=3)

    assert len(alerts) == 0


def test_detect_sensor_alerts_empty_events():
    alerts = detect_sensor_alerts([], threshold=3)
    assert alerts.empty
    assert list(alerts.columns) == ["machine_id", "sensor", "nb_aberrations", "premier_cycle", "dernier_cycle"]


def test_clean_and_bound_simple_clips_negative_values():
    df = pd.DataFrame({
        "machine_id": ["M1", "M2"],
        "sensor_1": [500.0, -10.0],
        "sensor_2": [200.0, 300.0],
    })
    df_clean, alert_counts = clean_and_bound_simple(df, ["sensor_1", "sensor_2"])

    assert (df_clean["sensor_1"] >= 0).all()
    assert df_clean.loc[1, "sensor_1"] == 0.0
    assert "M2" in alert_counts
    assert "M1" not in alert_counts


def test_clean_and_bound_simple_no_alert_when_all_valid():
    df = pd.DataFrame({
        "machine_id": ["M1"],
        "sensor_1": [500.0],
    })
    df_clean, alert_counts = clean_and_bound_simple(df, ["sensor_1"])

    assert alert_counts == {}


def make_feature_stats():
    """Statistiques de référence factices : 2 capteurs, comportement normal connu."""
    return {
        "temperature_moteur": {"mean": 500.0, "std": 5.0},
        "vibration_axe_x": {"mean": 10.0, "std": 1.0},
    }


def test_capteur_principal_identifies_most_anomalous_sensor():
    stats = make_feature_stats()
    # temperature proche de la normale (z ~0.2), vibration très anormale (z=10)
    row = {"temperature_moteur": 501.0, "vibration_axe_x": 20.0}

    result = capteur_principal(row, stats)

    assert result == "vibration_axe_x"


def test_capteur_principal_picks_temperature_when_it_deviates_more():
    stats = make_feature_stats()
    row = {"temperature_moteur": 530.0, "vibration_axe_x": 10.5}  # z=6 vs z=0.5

    result = capteur_principal(row, stats)

    assert result == "temperature_moteur"


def test_capteur_principal_handles_zero_std_without_crashing():
    """Un capteur avec écart-type nul (valeur constante à l'entraînement) ne
    doit pas provoquer de division par zéro."""
    stats = {"capteur_constant": {"mean": 100.0, "std": 0.0}}
    row = {"capteur_constant": 105.0}

    result = capteur_principal(row, stats)

    assert result == "capteur_constant"


def test_capteur_principal_ignores_missing_features_in_row():
    """Si un capteur des feature_stats est absent de la ligne, il est ignoré
    plutôt que de faire planter le calcul."""
    stats = make_feature_stats()
    row = {"vibration_axe_x": 15.0}  # temperature_moteur absente

    result = capteur_principal(row, stats)

    assert result == "vibration_axe_x"


def test_capteur_principal_returns_unknown_when_no_matching_features():
    result = capteur_principal({"autre_colonne": 1.0}, make_feature_stats())
    assert result == "inconnu"
