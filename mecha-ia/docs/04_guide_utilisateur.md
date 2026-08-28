# Guide utilisateur métier — Solution IA MECHA

**Public** : Responsable maintenance, chef d'atelier, technicien terrain
**Version** : 1.0 — Prototype

---

## 1. Ce que fait la solution

La solution surveille en continu les machines de production et signale **avant qu'une panne survienne** les situations anormales. Elle fournit :

- Un **score de risque** par machine (0 à 100)
- Une **alerte** quand le seuil critique est franchi
- Une **estimation du temps restant** avant intervention nécessaire
- Un **tableau de bord** temps réel accessible depuis navigateur

## 2. Ce qu'elle ne fait pas

- Elle **ne remplace pas** l'expertise terrain : c'est un outil d'aide à la décision
- Elle **ne diagnostique pas** la cause précise de la panne, elle signale le risque
- Elle **ne pilote pas** les machines : aucune action automatique n'est déclenchée
- Elle **ne suit pas** les opérateurs individuellement

## 3. Comment l'utiliser au quotidien

### 3.1 Consultation du dashboard (Grafana)
1. Se connecter à `http://mecha-ia.local:3000`
2. Sélectionner son site et sa ligne
3. Consulter la carte des machines : **vert** (OK), **orange** (à surveiller), **rouge** (intervention recommandée)

### 3.2 Réception d'une alerte
- Notification par mail + affichage dans le dashboard
- Contenu : machine concernée, RUL estimé, niveau (urgent/critique), **capteur principal** (celui qui explique le plus la dégradation), historique 24h
- **Action attendue** : alerte "critique" → intervention dans les 4h ; alerte "urgent" → à planifier

**Le "capteur principal"** indique quel capteur présente la valeur la plus anormale par rapport au comportement habituel de la machine — c'est le premier endroit à inspecter. Exemple : `capteur_principal = vibration_axe_x` signifie que la vibration mesurée s'écarte le plus de la normale, davantage que la température ou la pression.

### 3.3 Retour terrain (important pour améliorer la solution)
Après chaque alerte, saisir dans le dashboard :
- **Alerte pertinente ?** (oui/non)
- **Cause identifiée** (menu déroulant)
- **Action réalisée**

Ces retours permettent au modèle de s'améliorer dans le temps.

## 4. Comment interpréter les résultats

La solution ne calcule pas un score arbitraire : elle prédit un **RUL** (temps
restant estimé avant intervention nécessaire, en heures) et un **niveau de
risque**. Deux niveaux d'alerte en découlent :

| RUL prédit | Niveau d'alerte | Signification | Action |
|---|---|---|---|
| > 50h | — (normal) | Fonctionnement normal | Aucune |
| 15h – 50h | — (à surveiller) | Dérive possible | Contrôle visuel prochain tour |
| 5h – 15h | 🟠 **urgent** | Anomalie probable, pas immédiate | Planifier l'intervention |
| ≤ 4h | 🔴 **critique** | Intervention nécessaire avant fin de poste | Intervention **dans les 4h** |

**Pourquoi 4h précisément** : ça correspond à la durée d'un poste de travail
en atelier — une alerte "critique" signifie concrètement "à traiter avant la
fin de votre poste actuel", pas "dans les jours qui viennent".

**Important** : le RUL prédit est une **estimation**, pas une certitude.
Sur le jeu de test, le modèle se trompe en moyenne de ~19h (MAE). Une
alerte "critique" à RUL=2h peut en réalité correspondre à une machine qui
tiendra encore plusieurs heures — c'est pourquoi l'inspection humaine reste
la décision finale.

## 5. Limites et conditions d'usage

- **Machines couvertes** : uniquement les centres d'usinage équipés IoT (à date : 15 machines sur site pilote)
- **Historique nécessaire** : le modèle a besoin de 30 jours de données stables pour une nouvelle machine
- **Fiabilité dégradée** si un capteur est HS : un bandeau d'avertissement s'affiche
- **Pas d'usage en mode dégradé réseau** : les alertes peuvent être retardées

## 6. Qui contacter ?

| Problème | Contact |
|---|---|
| Dashboard inaccessible | DSI — support niveau 1 |
| Alerte suspecte / faux positif récurrent | Data scientist référent |
| Capteur en panne | Maintenance instrumentation |
| Demande d'évolution | Chef de projet IA |

## 7. FAQ

**Q : Dois-je regarder le dashboard en permanence ?**
Non. Les alertes vous parviennent par mail. Un point de synthèse en début de poste suffit.

**Q : Que faire si je ne suis pas d'accord avec une alerte ?**
Marquer « alerte non pertinente » avec commentaire. Le modèle s'ajustera.

**Q : Mes données personnelles sont-elles collectées ?**
Non. La solution ne trace que les machines, pas les opérateurs.

**Q : Que se passe-t-il si l'IA se trompe ?**
La décision finale reste humaine. L'IA est un outil d'aide, pas un décideur.
