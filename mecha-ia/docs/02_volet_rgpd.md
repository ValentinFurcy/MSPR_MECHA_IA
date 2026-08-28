# Volet RGPD — Projet IA MECHA

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
- Chiffrement au repos (Postgres, Influx) et en transit (TLS)
- Accès par rôle (RBAC) : ops, data scientist, direction, admin
- Journalisation des accès aux données pseudonymisées

## 4. Rôle du DPO

Le DPO de MECHA doit :
- Valider le registre des traitements avant mise en production
- Auditer la table de correspondance (hash ↔ matricule)
- Valider les mentions d'information aux opérateurs (art. 13 RGPD)
- Être consulté avant tout usage secondaire des données

## 5. Analyse d'impact (AIPD)

Une AIPD est **recommandée** avant industrialisation, car :
- Traitement à grande échelle (multi-sites)
- Croisement de sources (SCADA + RH + maintenance)
- Risque de dérive vers un usage de surveillance individuelle

## 6. Information des opérateurs

Note d'information à afficher en atelier + insertion dans le règlement intérieur :
- Nature des données collectées
- Finalité (maintenance prédictive, **pas** de suivi individuel)
- Durées de conservation
- Droit d'accès, rectification, opposition
- Contact DPO

## 7. Limites du prototype actuel

Comme les données sont synthétiques, aucune obligation RGPD ne s'applique **au prototype**. Toutefois, le code est conçu pour supporter la pseudonymisation dès le premier passage sur données réelles (module `cleaning/pseudonymize.py` prévu).
