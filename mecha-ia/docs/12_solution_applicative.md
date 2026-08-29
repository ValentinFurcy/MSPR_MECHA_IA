# Solution applicative — exploitation des résultats IA

Comment les prédictions du modèle deviennent une décision de maintenance actionnable.

## 1. Architecture applicative

```
Pipeline IA                    Stockage                 Restitution
-----------                    --------                 -----------
run_pipeline.py                                         Grafana
  lit InfluxDB                                            dashboard Maintenance (par site)
  nettoie (src/cleaning)                                  dashboard Pilotage (multi-sites)
  charge les .joblib    -->  API REST  -->  PostgreSQL      ^
  prédit RUL + risque       (FastAPI)      predictions      | SQL lecture seule
                                           alertes          |
                                           alertes_capteur --+
```

Trois composants, trois responsabilités : le **pipeline** produit les prédictions, l'**API** les valide et applique les règles métier, **Grafana** les restitue. L'API est le seul point d'écriture ; Grafana lit la base directement en compte restreint, ce qui permet aux dashboards de rester consultables même si l'API est indisponible.

## 2. Mécanismes d'intégration

| Flux | Mécanisme | Détail |
|---|---|---|
| Pipeline → API | HTTP REST | `POST /predictions/{site}`, `POST /alertes-capteurs/{site}` |
| API → PostgreSQL | psycopg2 | Compte `api_rw`, schéma par site |
| Grafana → PostgreSQL | SQL direct | Compte `grafana_ro`, lecture seule |
| Notebook → Pipeline | Fichiers | `outputs/models/*.joblib` + `metadata.json` (contrat de features) |
| Consommateur tiers → API | HTTP REST | `GET /predictions/{site}`, `GET /alertes/{site}` — point d'entrée pour une intégration GMAO |

## 3. Paramétrage applicatif

### 3.1 Règles de transformation des résultats IA

Le modèle produit un RUL et une classe de risque. L'API en dérive les alertes, à l'insertion :

| Condition | Alerte générée | Délai d'action attendu |
|---|---|---|
| `rul_predit <= 4` | **critique** | Avant la fin du poste (4 h) |
| `risk_level_predit = 'a_risque'` et `rul_predit > 4` | **urgent** | À planifier |
| Sinon | aucune | — |

Les deux cas sont exclusifs : le seuil `a_risque` est RUL < 15, donc RUL ≤ 4 implique toujours `a_risque`.

### 3.2 Seuils

| Seuil | Valeur | Où | Origine |
|---|---|---|---|
| `normal` / `a_surveiller` | RUL = 50 cycles | `metadata.json` (`risk_level_bins`) | Convention métier, à valider terrain |
| `a_surveiller` / `a_risque` | RUL = 15 cycles | `metadata.json` | Idem |
| Alerte critique | RUL ≤ 4 | `src/api/main.py` | Durée d'un poste d'atelier |
| Capteur suspect | 3 valeurs aberrantes | `src/cleaning.py`, `metadata.json` | Évite de traiter un défaut instrumental comme une panne mécanique |

### 3.3 Fréquence de mise à jour

| Élément | Fréquence |
|---|---|
| Exécution du pipeline | À la demande (`docker compose run pipeline`) ; cible : horaire planifiée |
| Rafraîchissement dashboard maintenance | 1 minute |
| Rafraîchissement dashboard pilotage | 5 minutes |
| Rechargement des dashboards provisionnés | 30 secondes |
| Réentraînement du modèle | Mensuel (cf. `08_procedure_entrainement.md`) |

## 4. Formalisme de configuration

Quatre formalismes, chacun versionné dans Git :

| Formalisme | Fichier | Rôle |
|---|---|---|
| **SQL** | Requêtes des panneaux, dans les JSON de dashboard | Règles de sélection et de tri métier |
| **YAML** | `grafana/provisioning/**` | Déclaration de la source de données et des dashboards |
| **JSON** | `outputs/models/metadata.json` | Contrat entre le notebook et le pipeline (features, seuils, validation) |
| **Variables d'environnement** | `.env` | Connexions, secrets, images déployées |

Exemple de règle métier exprimée en SQL — priorisation des interventions, panneau principal du dashboard maintenance :

```sql
SELECT machine_id, rul_predit, risk_level_predit, capteur_principal
FROM (SELECT DISTINCT ON (machine_id) machine_id, "timestamp", rul_predit,
             risk_level_predit, capteur_principal
      FROM ${site}.predictions
      ORDER BY machine_id, "timestamp" DESC) d
WHERE risk_level_predit IN ('a_risque', 'a_surveiller')
ORDER BY rul_predit ASC
```

Le `DISTINCT ON` ne retient que la dernière prédiction connue de chaque machine : un technicien doit voir l'état courant du parc, pas l'historique.

## 5. Écrans et usages par rôle

| Rôle | Écran | Usage attendu |
|---|---|---|
| Technicien maintenance | Dashboard **Maintenance prédictive** → *Machines à intervenir* | Ordre de passage de la tournée : la machine au RUL le plus faible d'abord. La colonne *Capteur à inspecter* indique où regarder en premier |
| Technicien instrumentation | → *Alertes capteur* | Distingue un défaut de mesure d'une dégradation mécanique réelle |
| Responsable maintenance | → *État du parc* et *Tendance* | Charge d'intervention à venir, dérive du parc sur 7 jours |
| Chef d'atelier / production | → *État du parc* | Anticipe les arrêts sur les lignes concernées |
| Direction industrielle | Dashboard **Pilotage industriel** | Comparaison des 5 usines, priorisation des investissements |

Le sélecteur `Site` en haut du dashboard maintenance bascule entre les 5 usines sans dupliquer les écrans.

## 6. Limites

- **Pas d'acquittement depuis l'interface** : les colonnes `acquittee` / `acquittee_par` existent en base, mais Grafana est en lecture seule. L'acquittement passe aujourd'hui par l'API. Un écran de saisie reste à construire.
- **Pas de notification sortante** : ni mail ni SMS. Les alertes décrites dans `04_guide_utilisateur.md` supposent ce canal, qui n'est pas implémenté.
- **Pas de retour terrain saisissable** : la boucle d'amélioration décrite dans `05_conduite_changement.md` suppose un formulaire qui n'existe pas encore.
- **Metabase non provisionné** : le service démarre vierge, ses tableaux de bord direction sont à construire manuellement.
- **Jeu de démonstration figé** : `scripts/seed_demo.sql` sert à montrer les écrans sans exécuter tout le pipeline. Les dashboards ont été vérifiés sur ce jeu (Grafana 13.2, PostgreSQL 16, 11 requêtes exécutées sous le compte `grafana_ro`), pas encore sur un flux issu du pipeline complet.
