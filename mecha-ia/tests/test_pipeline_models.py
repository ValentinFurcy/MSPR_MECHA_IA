"""Tests unitaires — export/chargement des modèles (notebook -> pipeline).

Utilise des modèles factices (pas ceux du notebook, trop lourds/lents à
réentraîner en CI) pour valider le contrat entre l'export du notebook et
le chargement dans scripts/run_pipeline.py : mêmes noms de fichiers, même
structure de métadonnées, mêmes clés attendues.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor


@pytest.fixture
def fake_models_dir(tmp_path):
    """Reproduit la structure outputs/models/ générée par le notebook (section 14)."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    X = pd.DataFrame(
        np.random.default_rng(42).normal(size=(50, 3)),
        columns=["temperature_moteur", "vibration_axe_x", "pression_hydraulique"],
    )
    y_clf = np.random.default_rng(1).choice(["normal", "a_surveiller", "a_risque"], size=50)
    y_reg = np.random.default_rng(2).integers(0, 200, size=50)

    clf = RandomForestClassifier(n_estimators=5, random_state=42).fit(X, y_clf)
    reg = RandomForestRegressor(n_estimators=5, random_state=42).fit(X, y_reg)

    joblib.dump(clf, models_dir / "model_classification.joblib")
    joblib.dump(reg, models_dir / "model_regression.joblib")

    metadata = {
        "features": ["temperature_moteur", "vibration_axe_x", "pression_hydraulique"],
        "sensor_rename": {"sensor_2": "temperature_moteur", "sensor_11": "vibration_axe_x", "sensor_7": "pression_hydraulique"},
        "model_classification": "RandomForestClassifier",
        "model_regression": "RandomForestRegressor",
        "classification_uses_label_encoder": False,
        "risk_level_bins": [-1, 15, 50, None],
        "risk_level_labels": ["a_risque", "a_surveiller", "normal"],
        "sensor_alert_threshold": 3,
        "feature_stats": {
            "temperature_moteur": {"mean": float(X["temperature_moteur"].mean()), "std": float(X["temperature_moteur"].std())},
            "vibration_axe_x": {"mean": float(X["vibration_axe_x"].mean()), "std": float(X["vibration_axe_x"].std())},
            "pression_hydraulique": {"mean": float(X["pression_hydraulique"].mean()), "std": float(X["pression_hydraulique"].std())},
        },
        "validation": {
            "methode": "GroupKFold",
            "n_splits": 5,
            "groupes": "machine_id",
            "recall_a_risque_cv": 0.766,
            "recall_a_risque_cv_ecart_type": 0.037,
            "mae_cv_cycles": 19.9,
            "mae_cv_ecart_type": 0.2,
        },
    }
    (models_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    return models_dir


def test_models_load_successfully(fake_models_dir):
    clf = joblib.load(fake_models_dir / "model_classification.joblib")
    reg = joblib.load(fake_models_dir / "model_regression.joblib")
    assert hasattr(clf, "predict")
    assert hasattr(reg, "predict")


def test_metadata_has_required_keys(fake_models_dir):
    metadata = json.loads((fake_models_dir / "metadata.json").read_text())
    required = {
        "features", "sensor_rename", "model_classification", "model_regression",
        "classification_uses_label_encoder", "risk_level_labels", "sensor_alert_threshold",
        "feature_stats", "validation",
    }
    assert required.issubset(metadata.keys())


def test_metadata_documents_cross_validation(fake_models_dir):
    """Contrat d'auditabilité : metadata.json doit tracer *comment* les modèles
    ont été validés (méthode, nombre de folds, variable de groupement), pour
    qu'un audit qualité puisse rejouer la validation sans relire le notebook.

    Le groupement par `machine_id` n'est pas un détail : c'est lui qui garantit
    l'absence de fuite de données entre apprentissage et test."""
    metadata = json.loads((fake_models_dir / "metadata.json").read_text())
    validation = metadata["validation"]

    assert validation["methode"] == "GroupKFold"
    assert validation["groupes"] == "machine_id"
    assert validation["n_splits"] >= 2
    assert 0.0 <= validation["recall_a_risque_cv"] <= 1.0
    assert validation["recall_a_risque_cv_ecart_type"] >= 0
    assert validation["mae_cv_cycles"] >= 0


def test_metadata_feature_stats_covers_all_features(fake_models_dir):
    """Le contrat pour capteur_principal() : chaque feature du modèle doit
    avoir ses statistiques de référence (mean/std), sinon le score-Z ne peut
    pas être calculé pour ce capteur."""
    metadata = json.loads((fake_models_dir / "metadata.json").read_text())
    assert set(metadata["features"]).issubset(set(metadata["feature_stats"].keys()))
    for stats in metadata["feature_stats"].values():
        assert "mean" in stats and "std" in stats


def test_metadata_features_match_sensor_rename_values(fake_models_dir):
    """Le contrat entre le notebook et le pipeline : chaque feature listée
    doit être une valeur du mapping sensor_rename (sinon le pipeline ne
    saura pas quelle colonne renommer pour l'obtenir)."""
    metadata = json.loads((fake_models_dir / "metadata.json").read_text())
    assert set(metadata["features"]).issubset(set(metadata["sensor_rename"].values()))


def test_model_predicts_with_correct_feature_count(fake_models_dir):
    metadata = json.loads((fake_models_dir / "metadata.json").read_text())
    clf = joblib.load(fake_models_dir / "model_classification.joblib")
    reg = joblib.load(fake_models_dir / "model_regression.joblib")

    X_new = pd.DataFrame(
        np.random.default_rng(99).normal(size=(5, len(metadata["features"]))),
        columns=metadata["features"],
    )

    risk_pred = clf.predict(X_new)
    rul_pred = reg.predict(X_new)

    assert len(risk_pred) == 5
    assert len(rul_pred) == 5
    assert all(r in metadata["risk_level_labels"] for r in risk_pred)


def test_rul_predictions_are_non_negative(fake_models_dir):
    """Le RUL prédit ne devrait jamais être négatif (contrainte métier :
    un temps restant avant panne ne peut pas être négatif)."""
    metadata = json.loads((fake_models_dir / "metadata.json").read_text())
    reg = joblib.load(fake_models_dir / "model_regression.joblib")

    X_new = pd.DataFrame(
        np.random.default_rng(7).normal(size=(20, len(metadata["features"]))),
        columns=metadata["features"],
    )
    rul_pred = reg.predict(X_new)

    # Le modèle entraîné sur des cibles >= 0 ne doit pas extrapoler en négatif
    # de façon significative (les RF ne prédisent jamais hors de la plage d'entraînement).
    assert rul_pred.min() >= 0
