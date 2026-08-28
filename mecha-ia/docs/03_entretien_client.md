# Compte-rendu d'entretien client — MECHA

**Date** : Entretien simulé (encadrant pédagogique jouant le rôle du client)
**Interlocuteurs côté MECHA** : Directeur industriel, Responsable maintenance, DSI
**Interlocuteurs équipe projet** : Chef de projet IA, Data scientist, Data engineer
**Durée** : 1h

---

## 1. Guide d'entretien utilisé

### Thème 1 — Contexte et enjeux
1. Quels sont les 3 principaux irritants opérationnels actuels sur les lignes de production ?
2. Quel est le coût moyen d'un arrêt non planifié (heure ou journée) ?
3. Quelles sont les machines les plus critiques ? Combien y en a-t-il par site ?
4. Existe-t-il un historique structuré des pannes ?

### Thème 2 — Données disponibles
5. Quels capteurs sont déjà déployés ? Sur quelles machines ?
6. À quelle fréquence les données remontent-elles ?
7. Quel est le taux de disponibilité réel des capteurs (pannes capteur, réseau) ?
8. Les données de maintenance sont-elles saisies dans un outil unique (GMAO) ou dispersées ?

### Thème 3 — Utilisateurs et usages
9. Qui utilisera la solution au quotidien ? Sur quel support (poste fixe, tablette atelier) ?
10. Quel est le niveau technique moyen des équipes maintenance ?
11. Quel délai d'anticipation d'une panne serait utile (24h, 7j, 30j) ?
12. Comment les alertes sont-elles gérées aujourd'hui ?

### Thème 4 — Contraintes
13. Contraintes de sécurité IT (réseau OT/IT segmenté ?)
14. Contraintes RGPD (données opérateurs) ?
15. Budget cible et calendrier attendu ?
16. Intégration avec l'existant (SCADA, MES, GMAO) ?

---

## 2. Synthèse des besoins collectés

### 2.1 Besoins métier prioritaires

| # | Besoin | Priorité | Portage |
|---|---|---|---|
| B1 | Détecter les dérives machine **avant** panne (fenêtre 24-72h) | **Haute** | Maintenance |
| B2 | Alerter les équipes terrain en temps réel (< 5 min) | **Haute** | Maintenance |
| B3 | Consolider un TRS multi-sites pour la direction | **Haute** | Direction |
| B4 | Prioriser les interventions par criticité machine | Moyenne | Maintenance |
| B5 | Historiser les décisions pour audit qualité (aéronautique) | Moyenne | Qualité |
| B6 | Comparer la performance entre les 5 sites | Moyenne | Direction |

### 2.2 Contraintes techniques

- Réseau OT/IT segmenté : la solution IA vit côté IT, les capteurs côté OT communiquent via un broker MQTT sécurisé
- Sites hétérogènes : 3 sites France équipés IoT complet, 2 sites Espagne partiellement équipés
- Volume attendu : ~10 000 points/min tous sites confondus
- Aucun contact direct avec les opérateurs pour cette phase (démarche descendante)

### 2.3 Contraintes organisationnelles

- Équipes maintenance formées aux outils papier + SCADA basique, **peu à l'analytique**
- Turn-over faible → formation utile long terme
- Direction demande un ROI démontrable sous 6 mois (phase pilote sur 1 site)

### 2.4 Points d'attention soulevés

- **Refus explicite** de tout usage RH des données (suivi individuel)
- Crainte des équipes terrain d'être « remplacées » par l'IA → nécessité d'un accompagnement
- DSI insiste sur la **portabilité** (Docker, pas de dépendance cloud propriétaire)
- Qualité insiste sur la **traçabilité** de chaque prédiction (auditabilité)

## 3. Décisions issues de l'entretien

- **Cas d'usage retenu pour le prototype** : détection d'anomalies + prédiction dégradation sur un type de machine critique (centre d'usinage)
- **Périmètre pilote** : 1 site France, 3 machines
- **Métriques de succès** : rappel ≥ 80% sur pannes réelles, moins de 15% de faux positifs
- **Livraison prototype** : fin de MSPR, données simulées
- **Prochaine étape post-MSPR** : POC sur données réelles anonymisées 1 site
