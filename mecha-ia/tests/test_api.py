"""Tests unitaires — API FastAPI (src/api/main.py).

La connexion PostgreSQL est mockée : ces tests valident le comportement de
l'API (routes, validation, codes retour) sans nécessiter une vraie base.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "api"))
import main as api_main


@pytest.fixture
def client():
    return TestClient(api_main.app)


@pytest.fixture
def mock_db():
    """Remplace get_conn() par une connexion/curseur factices."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    with patch.object(api_main, "get_conn", return_value=mock_conn):
        yield mock_conn, mock_cursor


def test_health_ok(mock_db, client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_db_error(client):
    with patch.object(api_main, "get_conn", side_effect=Exception("connexion refusée")):
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "error"


def test_predictions_rejects_unknown_site(mock_db, client):
    response = client.get("/predictions/site_inconnu")
    assert response.status_code == 404


def test_predictions_accepts_valid_site(mock_db, client):
    _, mock_cursor = mock_db
    mock_cursor.fetchall.return_value = []
    response = client.get("/predictions/site_fr1")
    assert response.status_code == 200
    assert response.json()["site"] == "site_fr1"


def test_insert_prediction_valid_payload(mock_db, client):
    _, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = (1,)

    payload = {
        "machine_id": "MECHA-USI-001",
        "cycle_number": 42,
        "rul_predit": 18,
        "risk_level_predit": "a_risque",
    }
    response = client.post("/predictions/site_fr1", json=payload)

    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_insert_prediction_accepts_capteur_principal(mock_db, client):
    """capteur_principal est optionnel mais doit être accepté et stocké."""
    _, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = (1,)

    payload = {
        "machine_id": "MECHA-USI-001",
        "cycle_number": 42,
        "rul_predit": 18,
        "risk_level_predit": "a_risque",
        "capteur_principal": "vibration_axe_x",
    }
    response = client.post("/predictions/site_fr1", json=payload)

    assert response.status_code == 200
    # Vérifie que capteur_principal a bien été passé à la requête SQL d'insertion
    insert_call = mock_cursor.execute.call_args_list[0]
    assert "vibration_axe_x" in insert_call[0][1]


def test_insert_prediction_alert_message_includes_capteur_principal(mock_db, client):
    """Le message d'alerte doit mentionner le capteur principal quand fourni."""
    _, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = (1,)

    payload = {
        "machine_id": "MECHA-USI-001",
        "cycle_number": 1,
        "rul_predit": 2,
        "risk_level_predit": "a_risque",
        "capteur_principal": "vibration_axe_x",
    }
    client.post("/predictions/site_fr1", json=payload)

    # Le 2e execute() est l'insertion dans la table alertes
    alert_call = mock_cursor.execute.call_args_list[1]
    message = alert_call[0][1][2]
    assert "vibration_axe_x" in message


def test_insert_prediction_works_without_capteur_principal(mock_db, client):
    """capteur_principal reste optionnel — ne doit pas planter s'il est absent."""
    _, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = (1,)

    payload = {
        "machine_id": "MECHA-USI-001",
        "cycle_number": 1,
        "rul_predit": 2,
        "risk_level_predit": "a_risque",
    }
    response = client.post("/predictions/site_fr1", json=payload)

    assert response.status_code == 200


def test_insert_prediction_generates_alert_when_a_risque(mock_db, client):
    _, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = (1,)

    payload = {
        "machine_id": "MECHA-USI-001",
        "cycle_number": 42,
        "rul_predit": 7,
        "risk_level_predit": "a_risque",
    }
    response = client.post("/predictions/site_fr1", json=payload)

    assert response.json()["alerte_generee"] is True
    assert response.json()["niveau_alerte"] == "urgent"


def test_alerte_suit_le_rul_pas_le_classifieur(mock_db, client):
    """Le niveau d'alerte est decide par le RUL seul.

    Les deux cas ou classifieur et regresseur se contredisent :
      - classifieur "a_risque" mais RUL = 20 -> aucune alerte (RUL > 8) ;
      - classifieur "normal" mais RUL = 3    -> alerte critique quand meme.
    """
    _, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = (1,)

    faux_positif = {
        "machine_id": "MECHA-USI-001", "cycle_number": 1,
        "rul_predit": 20, "risk_level_predit": "a_risque",
    }
    response = client.post("/predictions/site_fr1", json=faux_positif)
    assert response.json()["alerte_generee"] is False

    faux_negatif = {
        "machine_id": "MECHA-USI-002", "cycle_number": 1,
        "rul_predit": 3, "risk_level_predit": "normal",
    }
    response = client.post("/predictions/site_fr1", json=faux_negatif)
    assert response.json()["niveau_alerte"] == "critique"


def test_bornes_des_seuils_alerte(mock_db, client):
    """Bornes exactes : 4 -> critique, 8 -> urgent, 9 -> plus d'alerte."""
    _, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = (1,)

    attendus = {4: "critique", 5: "urgent", 8: "urgent", 9: None, 24: None}
    for rul, niveau in attendus.items():
        payload = {
            "machine_id": "MECHA-USI-001", "cycle_number": 1,
            "rul_predit": rul, "risk_level_predit": "a_risque",
        }
        response = client.post("/predictions/site_fr1", json=payload)
        assert response.json()["niveau_alerte"] == niveau, f"RUL={rul}"


def test_insert_prediction_generates_critique_alert_under_4h(mock_db, client):
    _, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = (1,)

    payload = {
        "machine_id": "MECHA-USI-001",
        "cycle_number": 42,
        "rul_predit": 3,
        "risk_level_predit": "a_risque",
    }
    response = client.post("/predictions/site_fr1", json=payload)

    assert response.json()["alerte_generee"] is True
    assert response.json()["niveau_alerte"] == "critique"


def test_insert_prediction_critique_threshold_boundary(mock_db, client):
    """RUL = 4 doit déclencher 'critique' (seuil inclusif), RUL = 5 -> 'urgent'."""
    _, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = (1,)

    payload_4h = {
        "machine_id": "MECHA-USI-001", "cycle_number": 1,
        "rul_predit": 4, "risk_level_predit": "a_risque",
    }
    response = client.post("/predictions/site_fr1", json=payload_4h)
    assert response.json()["niveau_alerte"] == "critique"

    payload_5h = {
        "machine_id": "MECHA-USI-001", "cycle_number": 1,
        "rul_predit": 5, "risk_level_predit": "normal",  # le classifieur ne compte pas
    }
    response = client.post("/predictions/site_fr1", json=payload_5h)
    assert response.json()["niveau_alerte"] == "urgent"


def test_insert_prediction_no_alert_when_normal(mock_db, client):
    _, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = (1,)

    payload = {
        "machine_id": "MECHA-USI-001",
        "cycle_number": 42,
        "rul_predit": 200,
        "risk_level_predit": "normal",
    }
    response = client.post("/predictions/site_fr1", json=payload)

    assert response.json()["alerte_generee"] is False


def test_insert_prediction_rejects_missing_field(mock_db, client):
    payload = {"machine_id": "MECHA-USI-001"}  # champs requis manquants
    response = client.post("/predictions/site_fr1", json=payload)
    assert response.status_code == 422  # erreur de validation Pydantic


def test_insert_prediction_rejects_unknown_site(mock_db, client):
    payload = {
        "machine_id": "MECHA-USI-001",
        "cycle_number": 1,
        "rul_predit": 10,
        "risk_level_predit": "normal",
    }
    response = client.post("/predictions/site_inconnu", json=payload)
    assert response.status_code == 404


def test_alertes_capteur_insert(mock_db, client):
    _, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = (1,)

    payload = {
        "machine_id": "MECHA-USI-001",
        "capteur": "vibration_axe_x",
        "nb_aberrations": 3,
        "premier_cycle": 10,
        "dernier_cycle": 15,
    }
    response = client.post("/alertes-capteurs/site_fr1", json=payload)

    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_alertes_capteur_get(mock_db, client):
    _, mock_cursor = mock_db
    mock_cursor.fetchall.return_value = []
    response = client.get("/alertes-capteurs/site_fr1")
    assert response.status_code == 200
    assert response.json()["site"] == "site_fr1"
