# Cartographie des données — MECHA

Inventaire des sources disponibles, sélection de celles qui alimentent la solution IA, et réduction de l'espace de travail du modèle.

## 1. Sources disponibles

| Source | Contenu | Granularité | Propriétaire | Couverture des 5 sites | Données personnelles |
|---|---|---|---|---|---|
| **Capteurs IoT machines** | Températures, vitesses, vibrations, états machine, temps de cycle | Seconde à minute | Direction industrielle | 3 sites FR complets, 2 sites ES partiels | Non |
| **SCADA** | Supervision atelier, états de ligne, alarmes | Seconde | DSI | Hétérogène selon site | Indirect (utilisateur ayant acquitté) |
| **MES** | Ordres de fabrication, temps de cycle, rebuts | Ordre / pièce | DSI | Hétérogène | Indirect (opérateur ayant validé) |
| **GMAO / historique maintenance** | Interventions, causes, durées, pièces changées | Événement | Maintenance | Partiel, parfois hors outil | Indirect (matricule intervenant) |
| **Contrôle qualité** | Non-conformités, mesures dimensionnelles | Pièce / lot | Direction qualité | Complète | Non |
| **ERP** | Coûts, contrats, délais | Commande | Direction financière | Complète | Oui (RH) |

Volume attendu côté capteurs : environ **10 000 points/minute** tous sites confondus, soit ~14,4 M points/jour et ~1,3 milliard de points sur 90 jours de rétention (source : `03_entretien_client.md` §2.2).

## 2. Réduction de l'espace de l'IA

### 2.1 Au niveau des sources

| Source | Retenue | Justification |
|---|---|---|
| Capteurs IoT machines | **Oui** | Porte le signal de dégradation, seule source à la granularité requise |
| GMAO / historique maintenance | Cible | Indispensable pour obtenir de vrais labels de panne ; qualité insuffisante à ce jour |
| SCADA / MES | Cible | Apporte le contexte de production (mode, charge), utile en variable explicative |
| Contrôle qualité | Non | Relève d'un autre cas d'usage (dérive qualité), hors périmètre du prototype |
| ERP | Non | Hors finalité maintenance ; contient des données RH, exclu par principe de minimisation |

Écarter l'ERP n'est pas qu'un choix technique : c'est l'application directe de la limitation de finalité (`02_volet_rgpd.md` §3.3) et de l'engagement de non-usage RH pris devant le CSE.

### 2.2 Au niveau des variables

Le jeu source expose **21 capteurs**, dont **10 sont retenus** et renommés au vocabulaire MECHA :

| Capteur source | Nom MECHA | Capteur source | Nom MECHA |
|---|---|---|---|
| `sensor_2` | `temperature_moteur` | `sensor_12` | `vibration_axe_y` |
| `sensor_3` | `temperature_lubrifiant` | `sensor_14` | `debit_refroidissement` |
| `sensor_4` | `temperature_carter` | `sensor_15` | `humidite_ambiante` |
| `sensor_7` | `pression_hydraulique` | `sensor_21` | `indice_usure_outil` |
| `sensor_9` | `vitesse_broche` | `sensor_11` | `vibration_axe_x` |

Onze capteurs sont écartés : `sensor_1, 5, 6, 8, 10, 13, 16, 17, 18, 19, 20`.

**Critère de réduction retenu pour les données réelles** : écarter les capteurs à variance nulle (aucun signal) puis les capteurs redondants (corrélation forte entre eux, information déjà portée par un capteur conservé).

**État actuel** : ce critère n'est pas discriminant sur le jeu de repli — aucun capteur n'est constant et la corrélation avec la progression d'usure est identique entre retenus et écartés (|r| = 0,795 des deux côtés, 9 200 lignes vérifiées).
La sélection des 10 capteurs est donc une **convention de modélisation** au vocabulaire MECHA, à re-justifier statistiquement sur données réelles.

Aucune des sources industrielles listées en §1 n'alimente le prototype à ce stade : il s'appuie sur un jeu public ou synthétique dont l'origine, le dictionnaire, les hypothèses et les limites sont décrits dans `06_documentation_dataset_ml.md`.

## 3. Outils de collecte et de traitement (ETL)

| Étape | Outil | Justification | État |
|---|---|---|---|
| Collecte capteurs | MQTT | Standard IoT industriel, léger, QoS configurable | Cible |
| Transport / tampon | Apache Kafka | Découplage producteurs/consommateurs, rejeu possible | Cible |
| Stockage brut | InfluxDB | Base temporelle, compression et downsampling natifs | Implémenté |
| Nettoyage / transformation | Python, pandas, scikit-learn | Logique partagée entre entraînement et inférence (`src/cleaning.py`) | Implémenté |
| Stockage exploitable | PostgreSQL | Schéma par site, comptes à moindre privilège | Implémenté |
| Orchestration | `scripts/run_pipeline.py` | Suffisant au volume prototype ; Airflow en cible multi-sites | Implémenté |

Dans le prototype, la chaîne MQTT/Kafka est remplacée par `scripts/load_sensors_to_influx.py`, qui rejoue les données comme si elles provenaient des capteurs. Justification des choix par couche : `01_choix_techniques.md`.

## 4. Rôle du DPO

Le DPO est consulté sur trois points de cette cartographie : l'exclusion de l'ERP et des données RH du périmètre, la pseudonymisation des matricules dans l'historique GMAO avant tout usage analytique, et la validation du registre des traitements pour les sources SCADA et MES qui tracent indirectement l'activité des opérateurs. Détail : `02_volet_rgpd.md` §5.

## 5. Limites

- Cartographie établie à partir du cahier des charges et de l'entretien client simulé, sans audit des systèmes réels.
- Volumes et taux de couverture par site sont des ordres de grandeur déclaratifs, non mesurés.
- La qualité réelle des données GMAO n'a pas pu être évaluée ; c'est le principal risque pesant sur le passage à des labels de panne réels.
