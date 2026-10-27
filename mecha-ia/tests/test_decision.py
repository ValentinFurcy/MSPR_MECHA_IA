"""Tests unitaires — règle de décision du classifieur (src/decision.py)."""
import numpy as np

from src.decision import predire_avec_seuil

CLASSES = np.array(["a_risque", "a_surveiller", "normal"])


def test_cible_retenue_des_que_le_seuil_est_atteint():
    # a_risque n'est pas la classe la plus probable, mais dépasse le seuil
    proba = np.array([[0.30, 0.10, 0.60]])
    assert predire_avec_seuil(proba, CLASSES, seuil=0.25)[0] == "a_risque"


def test_sous_le_seuil_la_classe_la_plus_probable_parmi_les_autres():
    proba = np.array([[0.20, 0.50, 0.30]])
    assert predire_avec_seuil(proba, CLASSES, seuil=0.25)[0] == "a_surveiller"


def test_sous_le_seuil_jamais_la_cible_meme_si_elle_est_la_plus_probable():
    # Seuil > 0.5 : a_risque majoritaire mais insuffisant -> on prend la suivante
    proba = np.array([[0.55, 0.15, 0.30]])
    assert predire_avec_seuil(proba, CLASSES, seuil=0.60)[0] == "normal"


def test_seuil_atteint_exactement():
    proba = np.array([[0.25, 0.25, 0.50]])
    assert predire_avec_seuil(proba, CLASSES, seuil=0.25)[0] == "a_risque"


def test_abaisser_le_seuil_ne_fait_jamais_baisser_le_nombre_d_alertes():
    proba = np.random.default_rng(0).dirichlet([1, 1, 1], size=500)
    n_alertes = [
        (predire_avec_seuil(proba, CLASSES, s) == "a_risque").sum()
        for s in (0.6, 0.4, 0.2, 0.1)
    ]
    assert n_alertes == sorted(n_alertes)


def test_ordre_des_classes_respecte():
    classes = np.array(["normal", "a_risque", "a_surveiller"])
    proba = np.array([[0.50, 0.40, 0.10]])
    assert predire_avec_seuil(proba, classes, seuil=0.35)[0] == "a_risque"
