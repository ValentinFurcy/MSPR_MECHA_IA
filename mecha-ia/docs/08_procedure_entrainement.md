# Procédure d'entraînement — lot, mini-lot, online

Notebook : section 17. Sorties : `outputs/benchmark_modes_entrainement.csv`, `outputs/benchmark_taux_apprentissage.csv`

## 1. Les trois modes

| Mode | Principe | Quand c'est le bon choix |
|---|---|---|
| **Lot** (*batch*) | Tout l'historique, un seul ajustement | Le jeu tient en mémoire, réentraînement planifié |
| **Mini-lot** | Paquets de N lignes, ajustements successifs | Le jeu ne tient plus en mémoire, réentraînement fréquent |
| **Online** | Une ligne à la fois, à son arrivée | Flux continu, adaptation immédiate, pas de stockage |

## 2. Protocole

Les trois modes portent sur **le même modèle** : la Logistic Regression retenue a un équivalent incrémental exact, `SGDClassifier(loss="log_loss")` — même fonction de coût, optimisée par descente de gradient stochastique, donc compatible `partial_fit`.

Deux contraintes apparaissent hors du mode batch :

| Contrainte | Pourquoi | Réponse |
|---|---|---|
| `class_weight="balanced"` refusé par `partial_fit` | En incrémental, la distribution des classes n'est pas connue d'avance | Poids calculés sur l'historique puis **figés** (`a_risque` 3.82, `a_surveiller` 1.75, `normal` 0.46) |
| Le `StandardScaler` doit être figé | On ne peut pas re-normaliser rétroactivement des données déjà apprises | Scaler ajusté une fois, puis versionné avec le modèle |

Mini-lot et online mélangent les données (SGD suppose des échantillons i.i.d.). Sans mélange, le modèle voit une machine entière d'affilée — que des cycles `normal`, puis que des `a_risque` — et oscille.

## 3. Résultats

| Mode | Recall `a_risque` | Précision `a_risque` | F1 macro | Temps |
|---|---|---|---|---|
| **Lot (batch)** | **0.762** ✅ | 0.601 | **0.743** ✅ | 0.03 s |
| Mini-lot (256, 5 époques) | 0.638 | 0.607 | 0.732 | 0.26 s |
| Online (1 passe, mélangé) | 0.006 | 1.000 | 0.532 | 7.1 s |
| Online (ordre d'arrivée réel) | 0.494 | 0.603 | 0.705 | 7.2 s |

**Le recall seul est trompeur** : une version antérieure de ce test donnait 0.944 de recall en online, pour une précision de 0.398 — le modèle prédisait `a_risque` sur 20 % des lignes contre 9 % en réalité. Un modèle qui crie au loup gonfle son recall et devient inutilisable en atelier. D'où le suivi conjoint recall + précision dans ce tableau.

## 4. Le taux d'apprentissage décide de tout en incrémental

En batch, scikit-learn gère la convergence. En incrémental, c'est au concepteur de la régler :

| `learning_rate` | Recall | Précision | F1 macro |
|---|---|---|---|
| `optimal` (défaut sklearn) | 0.325 | 0.788 | 0.665 |
| `constant`, `eta0=0.01` | **0.762** | 0.565 | 0.723 |
| `constant`, `eta0=0.001` | 0.638 | 0.607 | **0.732** |
| `constant`, `eta0=0.0001` | 0.006 | 1.000 | 0.522 |
| `adaptive`, `eta0=0.01` | **0.762** | 0.565 | 0.723 |

Le recall passe de **0.006 à 0.762** selon le seul `eta0` : trop faible, le modèle n'apprend rien ; trop fort, il oscille. Avec `eta0=0.01`, le mini-lot **atteint le recall du batch** (0.762) pour un F1 légèrement inférieur (0.723 vs 0.743).

## 5. Décision pour MECHA

**Mode retenu : lot (batch), réentraînement planifié.**

- Meilleur sur les deux métriques qui comptent (recall 0.762, F1 0.743) et le plus rapide (0.03 s) au volume actuel.
- Le mini-lot ne se justifie pas tant que l'historique tient en mémoire. Il devient la voie d'industrialisation au-delà : à ~10 000 points/min tous sites (cf. `03_entretien_client.md`), soit ~14 M de points/jour, l'historique complet cessera de tenir en RAM.
- **L'online est écarté** : une passe unique ne suffit pas à converger, et le résultat dépend fortement de l'ordre d'arrivée (F1 0.532 à 0.705 selon l'ordre). Inadapté à une décision de maintenance auditable.

**Fréquence de réentraînement** : mensuelle en phase pilote, alignée sur la boucle de retour terrain (cf. `05_conduite_changement.md`), avec réentraînement déclenché si le recall en production passe sous 0.70.

## 6. Limites

- Comparaison sur le jeu de repli synthétique (`seed=42`), résultats déterministes et reproductibles.
- Pas d'optimisation d'hyperparamètres au-delà du taux d'apprentissage.
- Le mini-lot n'a pas été testé sur un flux réellement continu (données rejouées depuis un fichier).
