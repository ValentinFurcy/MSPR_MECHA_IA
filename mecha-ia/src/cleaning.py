"""Logique de nettoyage partagée — utilisée par le notebook d'entraînement,
le pipeline d'inférence temps réel (scripts/run_pipeline.py) et les tests
unitaires. Une seule source de vérité pour éviter la divergence entre
l'entraînement et la production.
"""

import pandas as pd


def winsorize_by_machine(df: pd.DataFrame, cols: list, k: float = 3.0):
    """Écrête les valeurs aberrantes par machine et par capteur (IQR).

    Utilisé en contexte batch (notebook) où on dispose de l'historique
    complet d'une machine pour calculer les quartiles.

    k=3.0 (large) : ne touche que les vraies anomalies statistiques, pas la
    dégradation progressive normale en fin de vie machine.

    Retourne (df nettoyé, liste d'événements d'écrêtage) — chaque événement
    est un dict {machine_id, sensor, cycle_number}, utilisé ensuite pour
    détecter un capteur défaillant (voir detect_sensor_alerts).
    """
    df = df.copy()
    outlier_events = []
    n_capped = 0

    for machine_id, group in df.groupby("machine_id"):
        idx = group.index
        for col in cols:
            q1, q3 = group[col].quantile([0.25, 0.75])
            iqr = q3 - q1
            low, high = q1 - k * iqr, q3 + k * iqr
            mask = (df.loc[idx, col] < low) | (df.loc[idx, col] > high)
            n_capped += mask.sum()
            for c in df.loc[idx][mask]["cycle_number"]:
                outlier_events.append({"machine_id": machine_id, "sensor": col, "cycle_number": c})
            df.loc[idx, col] = df.loc[idx, col].clip(low, high)

    return df, outlier_events, n_capped


def detect_sensor_alerts(outlier_events: list, threshold: int = 3) -> pd.DataFrame:
    """Regroupe les événements d'écrêtage par (machine, capteur) et retourne
    les couples ayant atteint le seuil d'alerte (capteur suspect).
    """
    df_events = pd.DataFrame(outlier_events)
    if df_events.empty:
        return pd.DataFrame(columns=["machine_id", "sensor", "nb_aberrations", "premier_cycle", "dernier_cycle"])

    counts = (
        df_events.groupby(["machine_id", "sensor"])
        .agg(nb_aberrations=("cycle_number", "count"),
             premier_cycle=("cycle_number", "min"),
             dernier_cycle=("cycle_number", "max"))
        .reset_index()
    )
    return counts[counts["nb_aberrations"] >= threshold].copy()


def clean_and_bound_simple(df: pd.DataFrame, sensor_cols: list):
    """Nettoyage simplifié pour le contexte streaming (pipeline temps réel) :
    pas d'historique disponible pour calculer un IQR sur un seul relevé, donc
    on se limite aux bornes physiques absolues (valeur négative = impossible).

    Retourne (df nettoyé, dict {machine_id: nb_valeurs_negatives}).
    """
    df = df.copy()
    sensor_alert_counts = {}
    for _, row in df.iterrows():
        n_bad = sum(1 for c in sensor_cols if c in row and row[c] is not None and row[c] < 0)
        if n_bad > 0:
            sensor_alert_counts[row["machine_id"]] = n_bad
    for c in sensor_cols:
        if c in df.columns:
            df[c] = df[c].clip(lower=0)
    return df, sensor_alert_counts


def capteur_principal(row: dict, feature_stats: dict) -> str:
    """Détermine quel capteur est le plus anormal pour une machine donnée,
    via un score-Z (écart à la moyenne d'entraînement, normalisé par
    l'écart-type) — celui avec le score le plus élevé en valeur absolue.

    Répond à "pourquoi cette machine a-t-elle besoin de maintenance" au
    niveau de la machine individuelle, contrairement à l'importance globale
    des features (moyenne sur tout le jeu de données) qui ne dit rien sur
    un cas précis.

    `feature_stats` : dict {feature: {"mean": float, "std": float}},
    calculé sur le jeu d'entraînement et exporté dans metadata.json.
    """
    z_scores = {}
    for f, stats in feature_stats.items():
        if f not in row:
            continue
        std = stats["std"] if stats["std"] > 0 else 1e-6
        z_scores[f] = abs((row[f] - stats["mean"]) / std)
    if not z_scores:
        return "inconnu"
    return max(z_scores, key=z_scores.get)
