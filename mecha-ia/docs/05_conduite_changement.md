# Conduite du changement — Projet IA MECHA

## 1. Enjeu

Introduire une solution IA dans un environnement industriel où les décisions reposent historiquement sur l'expertise humaine et les indicateurs SCADA. Le risque principal est **le rejet par les équipes terrain** si l'outil est perçu comme un contrôle ou un remplacement.

## 2. Acteurs concernés

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

## 3. Messages clés à porter

| Cible | Message |
|---|---|
| Techniciens | « L'IA vous fait gagner du temps, elle ne vous remplace pas. Votre expertise reste centrale. » |
| Responsables | « Meilleure priorisation des interventions, réduction des arrêts non planifiés. » |
| Opérateurs | « Aucune surveillance individuelle. Les données concernent uniquement les machines. » |
| Direction | « ROI mesurable, alignement Industrie 4.0, avantage compétitif. » |
| CSE | « Finalité maintenance uniquement, engagement écrit sur non-usage RH. » |

## 4. Plan de formation

| Public | Format | Durée | Contenu |
|---|---|---|---|
| Responsables maintenance | Atelier présentiel | 1 jour | Interprétation des scores, gestion des alertes, retours terrain |
| Techniciens | Session terrain | 2h × 2 | Prise en main dashboard, workflow alerte |
| Direction | Démonstration | 1h | Lecture du TRS consolidé, indicateurs stratégiques |
| DSI | Formation technique | 2 jours | Docker, Postgres, Grafana, procédures d'exploitation |

**Support** : guide utilisateur (1-2 pages), tutoriels vidéo courts (< 5 min), FAQ intranet, référent local par site.

## 5. Déploiement progressif

### Phase 1 — Pilote (3 mois)
- 1 site, 1 ligne, 3 machines critiques
- Équipe restreinte de 5 techniciens volontaires
- Objectif : validation technique + retours utilisateurs
- Critères de succès : rappel ≥ 80%, adoption ≥ 70% des alertes traitées

### Phase 2 — Extension site (3 mois)
- Extension à toutes les machines du site pilote
- Formation de tous les techniciens du site
- Objectif : stabilisation opérationnelle

### Phase 3 — Roll-out national (6 mois)
- Déploiement sur les 2 autres sites France
- Adaptation aux spécificités locales
- Objectif : uniformisation des pratiques

### Phase 4 — International (6 mois)
- Déploiement Espagne (2 sites)
- Localisation (langue, référentiels)
- Objectif : couverture complète des 5 usines

## 6. Points de vigilance

| Risque | Mitigation |
|---|---|
| Rejet par les équipes terrain | Impliquer des techniciens volontaires dès la phase pilote comme ambassadeurs |
| Faux positifs répétés | Boucle de retour terrain systématique, réentraînement mensuel |
| Perception « big brother » | Communication CSE en amont, engagement écrit sur non-usage RH |
| Dépendance à un référent unique | Formation croisée, documentation complète |
| Dérive du modèle non détectée | MLflow + revue trimestrielle des performances |
| Résistance managériale intermédiaire | Sponsor visible côté direction industrielle |

## 7. Indicateurs de suivi du changement

- **Adoption** : % d'alertes traitées avec retour terrain saisi
- **Satisfaction** : enquête trimestrielle utilisateurs (échelle 1-5)
- **Performance métier** : évolution du taux d'arrêts non planifiés
- **Performance modèle** : rappel, précision, dérive (MLflow)
- **Formation** : % d'utilisateurs formés par site

## 8. Gouvernance

- **Comité de pilotage mensuel** : direction industrielle, DSI, chef de projet IA
- **Comité utilisateurs trimestriel** : responsables maintenance des sites déployés
- **Revue technique mensuelle** : data scientist + DSI (performance modèle, incidents)
