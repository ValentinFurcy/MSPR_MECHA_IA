"""Simule l'envoi des capteurs IoT vers InfluxDB.

En production, ce rôle est joué par la chaîne Capteurs -> MQTT -> Kafka ->
InfluxDB (voir architecture). Cette chaîne reste théorique dans ce prototype
(cf. docs/01_choix_techniques.md). Ce script en tient lieu : il relit les
données brutes livrées (data/mecha_dataset_raw.csv, exportées par le notebook) et
les injecte dans InfluxDB comme si elles venaient réellement des capteurs,
avec des timestamps réels et incrémentaux.

Usage :
    python scripts/load_sensors_to_influx.py
    python scripts/load_sensors_to_influx.py --speed 0.01   # pause entre points (secondes)
"""

import argparse
import os
import time
from pathlib import Path

import pandas as pd
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "mecha-dev-token-change-me")
INFLUX_ORG = os.getenv("INFLUX_ORG", "mecha")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "raw_data")

RAW_CSV = Path("data/mecha_dataset_raw.csv")


def main(speed: float, site: str):
    if not RAW_CSV.exists():
        raise FileNotFoundError(
            f"{RAW_CSV} introuvable — lance la commande depuis mecha-ia/ "
            "(le fichier est versionné dans data/)."
        )

    df = pd.read_csv(RAW_CSV)
    sensor_cols = [c for c in df.columns if c.startswith("sensor_")]

    # Cycle max par machine : nécessaire pour calculer un timestamp cohérent
    # (le dernier cycle de chaque machine doit être le plus récent, pas le premier)
    max_cycle_per_machine = df.groupby("machine_id")["cycle_number"].transform("max")

    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    print(f"Envoi de {len(df)} points vers InfluxDB ({INFLUX_URL}, bucket={INFLUX_BUCKET})...")
    now = pd.Timestamp.utcnow()

    points = []
    for i, row in df.iterrows():
        # Timestamp simulé : 1 cycle = 1 heure. Le DERNIER cycle de chaque
        # machine (fin de vie, cycle_number == max) doit être le plus proche
        # de "maintenant" — sinon last() récupère le début de vie au lieu de
        # l'état actuel de la machine.
        cycles_avant_fin_de_vie = max_cycle_per_machine.loc[i] - row["cycle_number"]
        ts = now - pd.Timedelta(hours=int(cycles_avant_fin_de_vie))

        point = (
            Point("sensor_reading")
            .tag("machine_id", f"MECHA-USI-{int(row['machine_id']):03d}")
            .tag("site", site)
            .field("cycle_number", int(row["cycle_number"]))
        )
        for col in sensor_cols:
            point = point.field(col, float(row[col]))
        point = point.time(ts)
        points.append(point)

        if len(points) >= 500:
            write_api.write(bucket=INFLUX_BUCKET, record=points)
            points = []
            print(f"  {i+1}/{len(df)} points envoyés...")
            if speed:
                time.sleep(speed)

    if points:
        write_api.write(bucket=INFLUX_BUCKET, record=points)

    client.close()
    print("Terminé.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--speed", type=float, default=0.0, help="Pause en secondes entre lots de 500 points")
    parser.add_argument("--site", default="site_fr1", help="Tag de site à appliquer")
    args = parser.parse_args()
    main(args.speed, args.site)
