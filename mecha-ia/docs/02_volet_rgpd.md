# Volet RGPD et sécurité des données — Projet IA MECHA

## 1. Contexte

Le prototype MECHA utilise **exclusivement des données publiques ou synthétiques** (contrainte cahier des charges, section V). Aucune donnée réelle d'entreprise ni personnelle n'est traitée dans cette phase.

Le présent document décrit néanmoins **le dispositif RGPD qui devrait être appliqué** en cas de bascule sur données réelles (industrialisation).

## 2. Typologie des données concernées (cas industrialisation)

| Catégorie | Exemple | Personnelle ? | Sensible ? |
|---|---|---|---|
| Télémétrie machine | Température, vibration, vitesse broche | Non | Non |
| État machine | Codes défaut, marche/arrêt | Non | Non |
| Historique maintenance | Intervention, cause, durée | Indirect (via ID opérateur) | Non |
| Identifiant opérateur | Matricule, badge | **Oui** | Non |
| Log SCADA/MES | Utilisateur ayant validé un ordre | **Oui** | Non |

Les données **techniques** (capteurs, machines) ne relèvent **pas** du RGPD. Les données **d'opérateurs** (matricule, intervention nominative) en relèvent.

## 3. Principes appliqués

### 3.1 Minimisation
Seules les variables utiles au modèle sont collectées. Les identifiants opérateurs ne sont **pas** injectés dans les features ML.

### 3.2 Pseudonymisation
Les matricules opérateur sont remplacés par un hash SHA-256 salé avant stockage analytique. La table de correspondance reste dans le SI RH, non accessible à la plateforme IA.

### 3.3 Finalité
Usage limité à : maintenance prédictive, détection d'anomalies, pilotage industriel. **Interdiction** d'usage RH (évaluation individuelle, productivité par opérateur).

### 3.4 Conservation
- Télémétrie brute : 90 jours (InfluxDB)
- Données agrégées / features : 3 ans (PostgreSQL)
- Historique interventions : durée légale métier

### 3.5 Sécurité
Traitée à part, section 4 (concept DIC).

## 4. Sécurité des données — concept DIC

Trois exigences : **D**isponibilité, **I**ntégrité, **C**onfidentialité. État réel du prototype, sans complaisance. Trois états : **Implémenté**, **Partiel**, **Absent** (cible d'industrialisation).

### 4.1 Disponibilité — la donnée est accessible quand on en a besoin

| Mesure | État | Où |
|---|---|---|
| Healthchecks + démarrage ordonné des services | Implémenté | `docker-compose.yml` (postgres, influxdb) |
| Fonctionnement dégradé : Grafana lit PostgreSQL en direct, une panne de l'API ne masque pas les dernières prédictions | Implémenté | Choix d'architecture |
| Redémarrage automatique des conteneurs | Absent | `restart: unless-stopped` à ajouter |
| Sauvegarde des volumes de données | Absent | `pg_data`, `influx_data` |
| Rétention maîtrisée du brut (90 j) | Cible | InfluxDB |
| Redondance | Absent — hôte Docker unique, point de défaillance unique | Cible : réplication PostgreSQL |

### 4.2 Intégrité — la donnée est exacte et non altérée

| Mesure | État | Où |
|---|---|---|
| Bornes physiques + winsorisation IQR par machine | Implémenté | `src/cleaning.py` |
| Détection de capteur défaillant (≥ 3 aberrations) | Implémenté | Table `alertes_capteur` |
| Contraintes de schéma (clés primaires, NOT NULL, typage) | Implémenté (14) | `docker/init.sql` |
| Intégrité de l'évaluation : aucune fuite entre apprentissage et test | Implémenté | `GroupKFold` groupé par `machine_id` |
| Traçabilité du modèle (méthode de validation, scores) | Implémenté | Bloc `validation` de `metadata.json` |
| Cohérence temporelle (horodatage, synchronisation) | Partiel | Hypothèse 1 cycle = 1 h, documentée |
| Clés étrangères vers `shared.machines` | Absent | Rien n'empêche une prédiction sur une machine inconnue |

### 4.3 Confidentialité — la donnée n'est accessible qu'aux personnes habilitées

| Mesure | État | Où |
|---|---|---|
| Comptes applicatifs séparés, moindre privilège | Implémenté | `grafana_ro`/`metabase_ro` en SELECT seul, `api_rw` en écriture, `search_path` par rôle |
| Aucune donnée personnelle traitée | Implémenté | Données publiques/synthétiques (cf. §1) |
| Pseudonymisation des matricules opérateur | Cible | §3.2 |
| Secrets hors du code | Absent | Mots de passe en clair dans `init.sql`, `src/api/main.py`, `grafana/provisioning/datasources/postgres.yml` |
| Chiffrement en transit (TLS) | Absent | Tous les flux en clair |
| Exposition réseau | Partiel | PostgreSQL (5432) et InfluxDB (8086) publiés sur l'hôte — à restreindre au réseau interne Docker |
| Segmentation OT/IT | Cible | Broker MQTT en zone OT, plateforme IA en zone IT |
| Journalisation des accès | Absent | Cible : audit des consultations |

### 4.4 Actions prioritaires avant tout passage en production

1. Sortir les secrets du code (variables d'environnement + secrets manager), et changer toutes les valeurs par défaut.
2. Restreindre l'exposition réseau : ne plus publier 5432 et 8086 sur l'hôte.
3. Ajouter `restart: unless-stopped` et une sauvegarde planifiée des volumes.
4. Activer TLS sur les flux externes.

Les points 1 et 2 sont les plus critiques : ils exposent aujourd'hui la base de données complète à quiconque atteint l'hôte.

## 5. Rôle du DPO

Le DPO de MECHA doit :
- Valider le registre des traitements avant mise en production
- Auditer la table de correspondance (hash ↔ matricule)
- Valider les mentions d'information aux opérateurs (art. 13 RGPD)
- Être consulté avant tout usage secondaire des données

## 6. Analyse d'impact (AIPD)

Une AIPD est **recommandée** avant industrialisation, car :
- Traitement à grande échelle (multi-sites)
- Croisement de sources (SCADA + RH + maintenance)
- Risque de dérive vers un usage de surveillance individuelle

## 7. Information des opérateurs

Note d'information à afficher en atelier + insertion dans le règlement intérieur :
- Nature des données collectées
- Finalité (maintenance prédictive, **pas** de suivi individuel)
- Durées de conservation
- Droit d'accès, rectification, opposition
- Contact DPO

## 8. Limites du prototype actuel

Comme les données sont synthétiques, aucune obligation RGPD ne s'applique **au prototype**. Toutefois, le code est conçu pour supporter la pseudonymisation dès le premier passage sur données réelles (module `cleaning/pseudonymize.py` prévu).
