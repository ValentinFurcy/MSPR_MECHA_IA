# Procédure d'entraînement — lot, mini-lot, online

Notebook : section 18. Sorties : `outputs/benchmark_modes_entrainement.csv`, `outputs/benchmark_taux_apprentissage.csv`

## 1. Données d'apprentissage

| Choix | Justification |
|---|---|
| 40 machines en apprentissage, 10 en test, **découpage par machine** | Une machine n'est jamais vue à la fois à l'entraînement et à l'évaluation |
| Les 10 capteurs retenus (`11_cartographie_donnees.md` §2.2) | Variables disponibles en temps réel, sans donnée personnelle |
| Cible : niveau de risque dérivé du RUL (seuils 8 / 24) | Mêmes seuils que l'exploitation |
| Pondération des classes | `a_risque` ne représente que 5 % des lignes |

## 2. Les trois modes

| Mode | Principe | Quand c'est le bon choix |
|---|---|---|
| **Lot** (*batch*) | Tout l'historique, un seul ajustement | Le jeu tient en mémoire, réentraînement planifié |
| **Mini-lot** | Paquets de N lignes, ajustements successifs | Le jeu ne tient plus en mémoire, réentraînement fréquent |
| **Online** | Une ligne à la fois, à son arrivée | Flux continu, adaptation immédiate, pas de stockage |

## 3. Protocole

Les trois modes portent sur **le même modèle** : la Logistic Regression retenue a un équivalent incrémental exact, `SGDClassifier(loss="log_loss")` — même fonction de coût, optimisée par descente de gradient stochastique, donc compatible `partial_fit`.

Deux contraintes apparaissent hors du mode lot :

| Contrainte | Pourquoi | Réponse |
|---|---|---|
| `class_weight="balanced"` refusé par `partial_fit` | En incrémental, la distribution des classes n'est pas connue d'avance | Poids calculés sur l'historique puis **figés** (`a_risque` 6.79, `a_surveiller` 3.82, `normal` 0.39) |
| Le `StandardScaler` doit être figé | On ne peut pas re-normaliser rétroactivement des données déjà apprises | Scaler ajusté une fois, puis versionné avec le modèle |

Mini-lot et online mélangent les données (SGD suppose des échantillons indépendants). Sans mélange, le modèle voit une machine entière d'affilée — que des cycles `normal`, puis que des `a_risque` — et oscille.

Les trois modes sont comparés avec la règle de décision par défaut (classe la plus probable), avant le réglage du seuil décrit dans `07_justification_modele.md` §6.

## 4. Résultats

| Mode | Rappel `a_risque` | Précision `a_risque` | F1 macro | Temps |
|---|---|---|---|---|
| **Lot (batch)** | **0.611** ✅ | **0.433** ✅ | **0.610** ✅ | 0.02 s |
| Mini-lot (256, 5 époques) | 0.567 | 0.331 | 0.606 | 0.19 s |
| Online (1 passe, mélangé) | 0.356 | 0.234 | 0.543 | 6.3 s |
| Online (ordre d'arrivée réel) | 0.511 | 0.245 | 0.553 | 6.2 s |

**Le rappel seul ne suffit pas** : un modèle qui prédit `a_risque` trop souvent gonfle son rappel et devient inutilisable en atelier. D'où le suivi conjoint rappel + précision, et la comparaison de la répartition des classes prédites avec la réalité (notebook).

Le mini-lot est **instable d'une époque à l'autre** (rappel 0,28 → 0,78 → 0,13 → 0,56 → 0,57 sur les 5 époques) : avec une classe à 5 %, chaque paquet de 256 lignes n'en contient qu'une douzaine.

## 5. Ajuster l'apprentissage par le taux d'apprentissage

En lot, scikit-learn gère la convergence. En incrémental, c'est au concepteur de régler le taux d'apprentissage (mini-lot, 5 époques) :

| `learning_rate` | Rappel | Précision | F1 macro |
|---|---|---|---|
| `optimal` (défaut sklearn) | **0.622** | **0.403** | 0.590 |
| `constant`, `eta0=0.01` | 0.533 | 0.393 | **0.619** |
| `constant`, `eta0=0.001` | 0.567 | 0.331 | 0.606 |
| `constant`, `eta0=0.0001` | 0.133 | 0.197 | 0.488 |
| `adaptive`, `eta0=0.01` | 0.533 | 0.393 | 0.619 |

Trop faible (`eta0=0.0001`), le modèle n'apprend presque rien : rappel 0,13. Bien réglé, le mini-lot rejoint le lot (rappel 0,62 avec `optimal`, F1 0,62 avec `eta0=0.01`), sans le dépasser sur les deux métriques à la fois.

## 6. Décision pour MECHA

**Mode retenu : lot (batch), réentraînement planifié.**

- Meilleur compromis rappel / précision / F1, et le plus rapide (0,02 s) au volume actuel.
- Le mini-lot ne se justifie pas tant que l'historique tient en mémoire. Il devient la voie d'industrialisation au-delà : à ~10 000 points/min tous sites (cf. `03_entretien_client.md`), soit ~14 M de points/jour, l'historique complet cessera de tenir en RAM.
- **L'online est écarté** : une passe unique ne suffit pas à converger, et le résultat dépend fortement de l'ordre d'arrivée (rappel 0,36 à 0,51). Inadapté à une décision de maintenance auditable.

**Fréquence de réentraînement** : mensuelle en phase pilote, alignée sur la boucle de retour terrain (cf. `05_conduite_changement.md`), avec réentraînement anticipé si le rappel en production passe sous 0,80. Le seuil de décision est recalculé à chaque réentraînement.

## 7. Limites

- Comparaison sur le jeu synthétique (`seed=42`), résultats déterministes et reproductibles.
- Pas d'optimisation d'hyperparamètres au-delà du taux d'apprentissage.
- Le mini-lot n'a pas été testé sur un flux réellement continu (données rejouées depuis un fichier).
