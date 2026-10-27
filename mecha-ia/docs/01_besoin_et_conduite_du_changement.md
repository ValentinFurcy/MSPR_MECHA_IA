# Besoin client et conduite du changement

Le besoin exprimé par MECHA (entretien client simulé) et l'accompagnement des équipes métiers.

## 1. Compte-rendu d'entretien client

**Date** : Entretien simulé (encadrant pédagogique jouant le rôle du client)
**Interlocuteurs côté MECHA** : Directeur industriel, Responsable maintenance, DSI
**Interlocuteurs équipe projet** : Chef de projet IA, Data scientist, Data engineer
**Durée** : 1h

---

### 1.1 Guide d'entretien utilisé

#### Thème 1 — Contexte et enjeux
1. Quels sont les 3 principaux irritants opérationnels actuels sur les lignes de production ?
2. Quel est le coût moyen d'un arrêt non planifié (heure ou journée) ?
3. Quelles sont les machines les plus critiques ? Combien y en a-t-il par site ?
4. Existe-t-il un historique structuré des pannes ?

#### Thème 2 — Données disponibles
5. Quels capteurs sont déjà déployés ? Sur quelles machines ?
6. À quelle fréquence les données remontent-elles ?
7. Quel est le taux de disponibilité réel des capteurs (pannes capteur, réseau) ?
8. Les données de maintenance sont-elles saisies dans un outil unique (GMAO) ou dispersées ?

#### Thème 3 — Utilisateurs et usages
9. Qui utilisera la solution au quotidien ? Sur quel support (poste fixe, tablette atelier) ?
10. Quel est le niveau technique moyen des équipes maintenance ?
11. Quel délai d'anticipation d'une panne serait utile (24h, 7j, 30j) ?
12. Comment les alertes sont-elles gérées aujourd'hui ?

#### Thème 4 — Contraintes
13. Contraintes de sécurité IT (réseau OT/IT segmenté ?)
14. Contraintes RGPD (données opérateurs) ?
15. Budget cible et calendrier attendu ?
16. Intégration avec l'existant (SCADA, MES, GMAO) ?

---

### 1.2 Synthèse des besoins collectés

#### 1.2.1 Besoins métier prioritaires

| # | Besoin | Priorité | Portage |
|---|---|---|---|
| B1 | Détecter les dérives machine **avant** panne (fenêtre 24-72h) | **Haute** | Maintenance |
| B2 | Alerter les équipes terrain en temps réel (< 5 min) | **Haute** | Maintenance |
| B3 | Consolider un TRS multi-sites pour la direction | **Haute** | Direction |
| B4 | Prioriser les interventions par criticité machine | Moyenne | Maintenance |
| B5 | Historiser les décisions pour audit qualité (aéronautique) | Moyenne | Qualité |
| B6 | Comparer la performance entre les 5 sites | Moyenne | Direction |

#### 1.2.2 Contraintes techniques

- Réseau OT/IT segmenté : la solution IA vit côté IT, les capteurs côté OT communiquent via un broker MQTT sécurisé
- Sites hétérogènes : 3 sites France équipés IoT complet, 2 sites Espagne partiellement équipés
- Volume attendu : ~10 000 points/min tous sites confondus
- Aucun contact direct avec les opérateurs pour cette phase (démarche descendante)

#### 1.2.3 Contraintes organisationnelles

- Équipes maintenance formées aux outils papier + SCADA basique, **peu à l'analytique**
- Turn-over faible → formation utile long terme
- Direction demande un ROI démontrable sous 6 mois (phase pilote sur 1 site)

#### 1.2.4 Points d'attention soulevés

- **Refus explicite** de tout usage RH des données (suivi individuel)
- Crainte des équipes terrain d'être « remplacées » par l'IA → nécessité d'un accompagnement
- DSI insiste sur la **portabilité** (Docker, pas de dépendance cloud propriétaire)
- Qualité insiste sur la **traçabilité** de chaque prédiction (auditabilité)

### 1.3 Décisions issues de l'entretien

- **Cas d'usage retenu pour le prototype** : détection d'anomalies + prédiction dégradation sur un type de machine critique (centre d'usinage)
- **Périmètre pilote** : 1 site France, 3 machines
- **Métriques de succès** : rappel ≥ 80% sur pannes réelles, moins de 15% de faux positifs
- **Livraison prototype** : fin de MSPR, données simulées
- **Prochaine étape post-MSPR** : POC sur données réelles anonymisées 1 site

---

## 2. Conduite du changement

### 2.1 Enjeu

Introduire une solution IA dans un environnement industriel où les décisions reposent historiquement sur l'expertise humaine et les indicateurs SCADA. Le risque principal est **le rejet par les équipes terrain** si l'outil est perçu comme un contrôle ou un remplacement.

### 2.2 Acteurs concernés

| Acteur | Rôle dans le projet | Impact du changement |
|---|---|---|
| **Direction générale** | Sponsor, arbitrage budgétaire | Faible — reçoit dashboards de synthèse |
| **Direction industrielle** | Pilote projet | Moyen — nouveau pilotage par la donnée |
| **Responsable maintenance** | Utilisateur clé | **Fort** — nouveaux workflows, alertes prédictives |
| **Techniciens maintenance** | Utilisateurs terrain | **Fort** — nouvel outil, nouveaux réflexes |
| **Opérateurs production** | Impactés indirects | Faible — pas d'usage direct, information nécessaire |
| **Qualité** | Consommateur des données | Moyen — nouvelle source de traçabilité |
| **DSI** | Exploitant technique | Moyen — nouvelle stack à maintenir |
| **DPO** | Conformité | Faible — validation en amont |
| **Représentants du personnel (CSE)** | Consultation obligatoire | Point de vigilance |

### 2.3 Messages clés à porter

| Cible | Message |
|---|---|
| Techniciens | « L'IA vous fait gagner du temps, elle ne vous remplace pas. Votre expertise reste centrale. » |
| Responsables | « Meilleure priorisation des interventions, réduction des arrêts non planifiés. » |
| Opérateurs | « Aucune surveillance individuelle. Les données concernent uniquement les machines. » |
| Direction | « ROI mesurable, alignement Industrie 4.0, avantage compétitif. » |
| CSE | « Finalité maintenance uniquement, engagement écrit sur non-usage RH. » |

### 2.4 Plan de formation

| Public | Format | Durée | Contenu |
|---|---|---|---|
| Responsables maintenance | Atelier présentiel | 1 jour | Lecture du RUL et des niveaux de risque, gestion des alertes, retours terrain |
| Techniciens | Session terrain | 2h × 2 | Prise en main dashboard, workflow alerte |
| Direction | Démonstration | 1h | Lecture du TRS consolidé, indicateurs stratégiques |
| DSI | Formation technique | 2 jours | Docker, Postgres, Grafana, procédures d'exploitation |

**Support** : guide utilisateur (1-2 pages), tutoriels vidéo courts (< 5 min), FAQ intranet, référent local par site.

### 2.5 Déploiement progressif

#### Phase 1 — Pilote (3 mois)
- 1 site, 1 ligne, 3 machines critiques
- Équipe restreinte de 5 techniciens volontaires
- Objectif : validation technique + retours utilisateurs
- Critères de succès : rappel ≥ 80%, adoption ≥ 70% des alertes traitées

#### Phase 2 — Extension site (3 mois)
- Extension à toutes les machines du site pilote
- Formation de tous les techniciens du site
- Objectif : stabilisation opérationnelle

#### Phase 3 — Roll-out national (6 mois)
- Déploiement sur les 2 autres sites France
- Adaptation aux spécificités locales
- Objectif : uniformisation des pratiques

#### Phase 4 — International (6 mois)
- Déploiement Espagne (2 sites)
- Localisation (langue, référentiels)
- Objectif : couverture complète des 5 usines

### 2.6 Points de vigilance

| Risque | Mitigation |
|---|---|
| Rejet par les équipes terrain | Impliquer des techniciens volontaires dès la phase pilote comme ambassadeurs |
| Faux positifs répétés | Boucle de retour terrain systématique, réentraînement mensuel |
| Perception « big brother » | Communication CSE en amont, engagement écrit sur non-usage RH |
| Dépendance à un référent unique | Formation croisée, documentation complète |
| Dérive du modèle non détectée | MLflow + revue trimestrielle des performances |
| Résistance managériale intermédiaire | Sponsor visible côté direction industrielle |

### 2.7 Indicateurs de suivi du changement

- **Adoption** : % d'alertes traitées avec retour terrain saisi
- **Satisfaction** : enquête trimestrielle utilisateurs (échelle 1-5)
- **Performance métier** : évolution du taux d'arrêts non planifiés
- **Performance modèle** : rappel, précision, dérive (MLflow)
- **Formation** : % d'utilisateurs formés par site

### 2.8 Gouvernance

- **Comité de pilotage mensuel** : direction industrielle, DSI, chef de projet IA
- **Comité utilisateurs trimestriel** : responsables maintenance des sites déployés
- **Revue technique mensuelle** : data scientist + DSI (performance modèle, incidents)
