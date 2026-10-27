"""Pipeline d'inférence — InfluxDB -> nettoyage -> prédiction -> PostgreSQL.

Étapes :
    1. Lit les dernières lectures capteurs par machine depuis InfluxDB
    2. Applique les bornes physiques (la winsorisation du notebook demande
       l'historique complet d'une machine, indisponible sur un seul relevé)
       et détecte les capteurs suspects (>= 3 aberrations)
    3. Charge les modèles entraînés (outputs/models/) et prédit risk_level + RUL
    4. Envoie les résultats à l'API (qui écrit dans PostgreSQL et génère les
       alertes automatiquement)

Usage :
    python scripts/run_pipeline.py --site site_fr1
"""

import argparse
import json
import os
import sys
from pathlib import Path

import joblib
import pandas as pd
import requests
from influxdb_client import InfluxDBClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.cleaning import capteur_principal, clean_and_bound_simple
from src.decision import predire_avec_seuil

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "mecha-dev-token-change-me")
INFLUX_ORG = os.getenv("INFLUX_ORG", "mecha")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "raw_data")
API_URL = os.getenv("API_URL", "http://localhost:8000")

MODELS_DIR = Path("outputs/models")
SEUIL_ALERTE_CAPTEUR = 3


def load_models():
    metadata = json.loads((MODELS_DIR / "metadata.json").read_text())
    clf = joblib.load(MODELS_DIR / "model_classification.joblib")
    reg = joblib.load(MODELS_DIR / "model_regression.joblib")
    le = None
    if metadata.get("classification_uses_label_encoder"):
        le = joblib.load(MODELS_DIR / "label_encoder.joblib")
    return clf, reg, le, metadata


def fetch_from_influx(site: str) -> pd.DataFrame:
    """Récupère la dernière lecture de chaque machine pour le site donné."""
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -30d)
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> filter(fn: (r) => r.site == "{site}")
          |> group(columns: ["machine_id", "_field"])
          |> last()
    '''
    tables = client.query_api().query(query, org=INFLUX_ORG)
    client.close()

    rows = {}
    for table in tables:
        for rec in table.records:
            mid = rec.values["machine_id"]
            rows.setdefault(mid, {"machine_id": mid})
            rows[mid][rec.get_field()] = rec.get_value()

    df = pd.DataFrame(rows.values())
    return df


def main(site: str):
    clf, reg, le, meta = load_models()
    sensor_rename = meta["sensor_rename"]
    features = meta["features"]

    print(f"Lecture InfluxDB (site={site})...")
    df = fetch_from_influx(site)
    if df.empty:
        print("Aucune donnée trouvée dans InfluxDB pour ce site. "
              "Lance d'abord scripts/load_sensors_to_influx.py.")
        return

    sensor_cols_raw = list(sensor_rename.keys())
    df, sensor_alerts = clean_and_bound_simple(df, sensor_cols_raw)

    df = df.rename(columns=sensor_rename)
    missing = [f for f in features if f not in df.columns]
    if missing:
        print(f"Colonnes manquantes, ignorées : {missing}")
        for f in missing:
            df[f] = 0.0

    X = df[features].fillna(0)

    # Prédictions — même règle de décision que le notebook (seuil sur P(a_risque))
    classes = le.classes_ if le is not None else clf.classes_
    seuil = meta.get("seuil_decision_a_risque")
    if seuil is not None:
        risk_pred = predire_avec_seuil(clf.predict_proba(X), classes, seuil)
    elif le is not None:
        risk_pred = le.inverse_transform(clf.predict(X))
    else:
        risk_pred = clf.predict(X)
    rul_pred = reg.predict(X).round(0).astype(int)

    print(f"{len(df)} machines traitées. Envoi vers l'API ({API_URL})...")

    feature_stats = meta.get("feature_stats", {})

    for i, row in df.iterrows():
        cp = capteur_principal(row.to_dict(), feature_stats) if feature_stats else None
        payload = {
            "machine_id": row["machine_id"],
            "cycle_number": int(row.get("cycle_number", 0)),
            "rul_predit": int(rul_pred[i]),
            "risk_level_predit": str(risk_pred[i]),
            "modele_classification": meta["model_classification"],
            "modele_regression": meta["model_regression"],
            "capteur_principal": cp,
        }
        r = requests.post(f"{API_URL}/predictions/{site}", json=payload)
        status = "OK" if r.status_code == 200 else f"ERREUR {r.status_code}"
        print(f"  {row['machine_id']} -> risk={payload['risk_level_predit']}, "
              f"RUL={payload['rul_predit']} cycles, capteur_principal={cp} [{status}]")

    # Alertes capteur (>= 3 valeurs aberrantes détectées sur ce passage)
    for machine_id, n_bad in sensor_alerts.items():
        if n_bad >= SEUIL_ALERTE_CAPTEUR:
            payload = {
                "machine_id": machine_id,
                "capteur": "multiple",
                "nb_aberrations": n_bad,
            }
            requests.post(f"{API_URL}/alertes-capteurs/{site}", json=payload)
            print(f"  ALERTE CAPTEUR : {machine_id} ({n_bad} valeurs aberrantes)")

    print("Pipeline terminé.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="site_fr1")
    args = parser.parse_args()
    main(args.site)
