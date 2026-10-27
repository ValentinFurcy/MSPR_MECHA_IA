"""Règle de décision du classifieur de risque — partagée entre le notebook
d'entraînement et le pipeline d'inférence (scripts/run_pipeline.py), pour que
la classe prédite soit calculée de la même façon dans les deux contextes.
"""

import numpy as np


def predire_avec_seuil(proba, classes, seuil: float, classe_cible: str = "a_risque"):
    """Prédit `classe_cible` dès que sa probabilité atteint `seuil`, sinon la
    classe la plus probable parmi les autres.

    Par défaut, un classifieur retient la classe de probabilité maximale. Pour
    une classe rare et coûteuse à rater (une panne), on abaisse le seuil à
    partir duquel on la déclare : le rappel augmente, au prix de davantage de
    fausses alertes. Le seuil est choisi en validation croisée (notebook,
    section 12) et exporté dans metadata.json.

    `proba` : sortie de predict_proba, colonnes dans l'ordre de `classes`.
    """
    proba = np.asarray(proba)
    classes = np.asarray(classes)
    i_cible = int(np.flatnonzero(classes == classe_cible)[0])

    autres = proba.copy()
    autres[:, i_cible] = -1.0
    pred = classes[autres.argmax(axis=1)].astype(object)
    pred[proba[:, i_cible] >= seuil] = classe_cible
    return pred
