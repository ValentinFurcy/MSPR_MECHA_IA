"""Génère docs/architecture_mecha.png — schéma d'architecture de la solution.

Usage (depuis mecha-ia/) :
    python docs/architecture_mecha.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

COULEURS = {
    "cible": ("#f1f0ec", "#8a8a8a"),
    "stockage": ("#e4eefc", "#2b5aa8"),
    "traitement": ("#e3f2ec", "#2a7a5c"),
    "exposition": ("#fdf0e2", "#c47a1e"),
    "restitution": ("#e6f2da", "#4c8a1f"),
}

fig, ax = plt.subplots(figsize=(16, 11))
ax.set_xlim(0, 16)
ax.set_ylim(0, 11)
ax.axis("off")


def boite(x, y, w, h, titre, details, famille, pointille=False):
    fond, bord = COULEURS[famille]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15",
                                facecolor=fond, edgecolor=bord, linewidth=2,
                                linestyle="--" if pointille else "-"))
    ax.text(x + w / 2, y + h - 0.32, titre, ha="center", va="center",
            fontsize=12, fontweight="bold", color=bord)
    ax.text(x + w / 2, y + (h - 0.55) / 2, details, ha="center", va="center",
            fontsize=9, color="#333333", linespacing=1.4)
    return (x, y, w, h)


def fleche(depart, arrivee, texte="", pointille=False, couleur="#555555"):
    ax.add_patch(FancyArrowPatch(depart, arrivee, arrowstyle="-|>", mutation_scale=16,
                                 linewidth=1.6, color=couleur,
                                 linestyle="--" if pointille else "-"))
    if texte:
        mx, my = (depart[0] + arrivee[0]) / 2, (depart[1] + arrivee[1]) / 2
        ax.text(mx, my + 0.15, texte, ha="center", va="bottom", fontsize=8.5,
                color=couleur, style="italic",
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})


ax.text(8, 10.6, "Architecture de la solution IA — MECHA", ha="center",
        fontsize=17, fontweight="bold", color="#1d3461")

# Bandes de couches
for y, nom in [(9.05, "ACQUISITION"), (6.75, "STOCKAGE BRUT\n& TRAITEMENT"),
               (4.45, "EXPOSITION\n& STOCKAGE"), (1.85, "RESTITUTION")]:
    ax.text(0.15, y, nom, rotation=90, ha="center", va="center", fontsize=9,
            fontweight="bold", color="#9a9a9a")
for y in (8.15, 5.65, 3.2):
    ax.plot([0.4, 15.8], [y, y], color="#dddddd", linewidth=0.8, linestyle=":")

# Acquisition
capteurs = boite(0.6, 8.4, 3.0, 1.4, "Capteurs IoT", "Machines des 5 usines", "cible", True)
mqtt = boite(4.3, 8.4, 3.0, 1.4, "MQTT → Kafka", "Collecte et transport\ndu flux capteurs", "cible", True)
simu = boite(8.2, 8.4, 3.6, 1.4, "load_sensors_to_influx.py",
             "Rejoue data/mecha_dataset_raw.csv\ncomme un flux capteurs", "traitement")
notebook = boite(12.4, 8.4, 3.3, 1.4, "Notebook d'entraînement",
                 "Préparation, comparaison,\nvalidation croisée, export", "traitement")

# Stockage brut & traitement
influx = boite(4.3, 5.95, 3.0, 1.5, "InfluxDB", "Séries temporelles brutes\nbucket raw_data", "stockage")
pipeline = boite(8.2, 5.95, 3.6, 1.5, "Pipeline d'inférence",
                 "run_pipeline.py\nnettoyage (src/cleaning.py)\nseuil de décision (src/decision.py)",
                 "traitement")
modeles = boite(12.4, 5.95, 3.3, 1.5, "Modèles (.joblib)",
                "Logistic Regression : état machine\nRandom Forest : RUL\nmetadata.json", "traitement")

# Exposition & stockage
api = boite(8.2, 3.5, 3.6, 1.6, "API FastAPI",
            "Seul point d'écriture\nAlertes : RUL ≤ 8 urgent, ≤ 4 critique", "exposition")
postgres = boite(4.3, 3.5, 3.0, 1.6, "PostgreSQL",
                 "1 schéma par usine\npredictions, alertes,\nalertes_capteur", "stockage")
mlflow = boite(12.4, 3.5, 3.3, 1.6, "MLflow", "Suivi des modèles,\nréentraînement", "cible", True)

# Restitution
grafana = boite(2.0, 0.6, 4.3, 1.9, "Grafana",
                "Maintenance prédictive (par usine)\nPilotage industriel (5 usines)\nlecture seule (grafana_ro)",
                "restitution")
metabase = boite(7.2, 0.6, 4.3, 1.9, "Metabase",
                 "Tableaux de bord direction\n(service démarré, à configurer)", "restitution")

# Flux
fleche((3.6, 9.1), (4.3, 9.1), pointille=True)
fleche((5.8, 8.4), (5.8, 7.45), pointille=True)
fleche((8.2, 8.75), (7.3, 7.1), "écriture")
fleche((7.3, 6.7), (8.2, 6.7), "derniers relevés")
fleche((14.05, 8.4), (14.05, 7.45), "export")
fleche((12.4, 6.7), (11.8, 6.7))
fleche((10.0, 5.95), (10.0, 5.1), "POST /predictions")
fleche((8.2, 4.3), (7.3, 4.3), "écriture")
fleche((5.0, 3.5), (4.6, 2.5), "SQL")
fleche((6.6, 3.5), (8.4, 2.5), "SQL")
fleche((14.05, 5.1), (14.05, 5.95), pointille=True)

# Légende
legende = [("Traitement (implémenté)", "traitement", False),
           ("Stockage", "stockage", False),
           ("Exposition des résultats", "exposition", False),
           ("Restitution", "restitution", False),
           ("Cible, non déployé dans le prototype", "cible", True)]
for i, (texte, famille, pointille) in enumerate(legende):
    fond, bord = COULEURS[famille]
    x = 12.2
    y = 2.45 - i * 0.42
    ax.add_patch(FancyBboxPatch((x, y), 0.45, 0.26, boxstyle="round,pad=0.01,rounding_size=0.05",
                                facecolor=fond, edgecolor=bord, linewidth=1.5,
                                linestyle="--" if pointille else "-"))
    ax.text(x + 0.6, y + 0.13, texte, va="center", fontsize=9, color="#333333")

sortie = Path(__file__).with_suffix(".png")
fig.savefig(sortie, dpi=130, bbox_inches="tight", facecolor="white")
print(f"Sauvegardé : {sortie}")
