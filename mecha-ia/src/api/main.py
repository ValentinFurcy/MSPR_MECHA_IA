"""API REST — Exposition des résultats IA MECHA.

Endpoints :
    GET  /health              → état de l'API
    GET  /predictions/{site}  → dernières prédictions par site
    POST /predictions/{site}  → insérer de nouvelles prédictions (pipeline ML)
    GET  /alertes/{site}      → alertes actives par site
"""

import os

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="MECHA IA — API Prédictions", version="1.0")

SITES = ["site_fr1", "site_fr2", "site_fr3", "site_es1", "site_es2"]

# Seuils de RUL (1 cycle = 1 heure). Doivent rester alignés sur la fonction
# shared.niveau_depuis_rul() de docker/init.sql, qui pilote l'affichage Grafana.
#   RUL <= 8  -> a_risque      (dont RUL <= 4 : intervention avant fin de poste)
#   RUL <= 24 -> a_surveiller
#   au-delà   -> normal
SEUIL_CRITIQUE = 4
SEUIL_A_RISQUE = 8
SEUIL_A_SURVEILLER = 24

def get_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "postgres"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DB", "mecha"),
        user=os.getenv("PG_USER", "api_rw"),
        password=os.getenv("PG_PASSWORD", "api_mecha_2026"),
    )

def validate_site(site: str):
    if site not in SITES:
        raise HTTPException(404, f"Site inconnu. Sites valides : {SITES}")


class PredictionIn(BaseModel):
    machine_id: str
    cycle_number: int
    rul_predit: int
    risk_level_predit: str
    anomaly_score: float | None = None
    modele_classification: str | None = None
    modele_regression: str | None = None
    capteur_principal: str | None = None  # capteur le plus anormal (score-Z) pour cette prédiction


@app.get("/health")
def health():
    try:
        conn = get_conn()
        conn.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:  # noqa: BLE001 — un healthcheck ne doit jamais planter, quelle que soit l'erreur
        # Un healthcheck ne doit jamais planter, quel que soit le type
        # d'erreur (timeout réseau, DNS, credentials...), pas seulement
        # psycopg2.Error.
        return {"status": "error", "database": str(e)}


@app.get("/predictions/{site}")
def get_predictions(site: str, machine_id: str | None = None, limit: int = 100):
    validate_site(site)
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = f"SELECT * FROM {site}.predictions ORDER BY timestamp DESC LIMIT %s"
    params = [limit]
    if machine_id:
        query = f"SELECT * FROM {site}.predictions WHERE machine_id = %s ORDER BY timestamp DESC LIMIT %s"
        params = [machine_id, limit]
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return {"site": site, "count": len(rows), "predictions": rows}


@app.post("/predictions/{site}")
def insert_prediction(site: str, pred: PredictionIn):
    validate_site(site)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO {site}.predictions
            (machine_id, cycle_number, rul_predit, risk_level_predit,
             anomaly_score, modele_classification, modele_regression, capteur_principal)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (pred.machine_id, pred.cycle_number, pred.rul_predit,
          pred.risk_level_predit, pred.anomaly_score,
          pred.modele_classification, pred.modele_regression, pred.capteur_principal))
    new_id = cur.fetchone()[0]

    # Auto-alerte, 2 niveaux, décidés par le RUL prédit et lui seul :
    #   - "critique" : RUL <= 4h — intervention avant la fin du poste en cours.
    #   - "urgent"   : RUL <= 8h (seuil a_risque) — à planifier, pas immédiat.
    # risk_level_predit n'entre plus dans la décision : il vient du classifieur,
    # qui contredit le régresseur sur ~13 % des lignes (class_weight="balanced"
    # le pousse à sur-prédire a_risque). On alertait donc sur des machines dont
    # le RUL affiché disait « à surveiller ». La colonne reste stockée pour la
    # traçabilité du modèle, mais l'exploitation suit le RUL.
    niveau_alerte = None
    capteur_suffix = f" — capteur principal : {pred.capteur_principal}" if pred.capteur_principal else ""
    if pred.rul_predit <= SEUIL_CRITIQUE:
        niveau_alerte = "critique"
        message = f"Intervention nécessaire dans les {SEUIL_CRITIQUE} prochaines heures (RUL estimé : {pred.rul_predit}h){capteur_suffix}"
    elif pred.rul_predit <= SEUIL_A_RISQUE:
        niveau_alerte = "urgent"
        message = f"RUL estimé : {pred.rul_predit}h — intervention à planifier{capteur_suffix}"

    if niveau_alerte:
        cur.execute(f"""
            INSERT INTO {site}.alertes (machine_id, niveau, message)
            VALUES (%s, %s, %s)
        """, (pred.machine_id, niveau_alerte, message))

    conn.commit()
    conn.close()
    return {"id": new_id, "site": site, "alerte_generee": niveau_alerte is not None, "niveau_alerte": niveau_alerte}


@app.get("/alertes/{site}")
def get_alertes(site: str, actives_only: bool = True):
    validate_site(site)
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    where = "WHERE acquittee = FALSE" if actives_only else ""
    cur.execute(f"SELECT * FROM {site}.alertes {where} ORDER BY timestamp DESC LIMIT 50")
    rows = cur.fetchall()
    conn.close()
    return {"site": site, "count": len(rows), "alertes": rows}


class AlerteCapteurIn(BaseModel):
    machine_id: str
    capteur: str
    nb_aberrations: int
    premier_cycle: int | None = None
    dernier_cycle: int | None = None


@app.get("/alertes-capteurs/{site}")
def get_alertes_capteurs(site: str, actives_only: bool = True):
    """Alertes capteur défaillant (cause instrumentale, distincte d'une alerte machine)."""
    validate_site(site)
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    where = "WHERE acquittee = FALSE" if actives_only else ""
    cur.execute(f"SELECT * FROM {site}.alertes_capteur {where} ORDER BY detecte_at DESC LIMIT 50")
    rows = cur.fetchall()
    conn.close()
    return {"site": site, "count": len(rows), "alertes_capteurs": rows}


@app.post("/alertes-capteurs/{site}")
def insert_alerte_capteur(site: str, alerte: AlerteCapteurIn):
    """Enregistre une alerte capteur (déclenchée à partir de 3 valeurs aberrantes détectées)."""
    validate_site(site)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO {site}.alertes_capteur
            (machine_id, capteur, nb_aberrations, premier_cycle, dernier_cycle)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (alerte.machine_id, alerte.capteur, alerte.nb_aberrations,
          alerte.premier_cycle, alerte.dernier_cycle))
    new_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return {"id": new_id, "site": site}
