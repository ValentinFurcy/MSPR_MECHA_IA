# Guide utilisateur métier — Solution IA MECHA

**Public** : Responsable maintenance, chef d'atelier, technicien terrain
**Version** : 1.0 — Prototype

---

## 1. Ce que fait la solution

La solution surveille en continu les machines de production et signale **avant qu'une panne survienne** les situations anormales. Elle fournit :

- Une **estimation du temps restant** avant intervention nécessaire (RUL, en heures)
- Un **niveau de risque** par machine : normal, à surveiller, à risque
- Une **alerte** (urgent ou critique) quand le RUL passe sous les seuils
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
3. Consulter la liste *Machines à intervenir*, triée du RUL le plus faible au plus élevé : **vert** (normal), **orange** (à surveiller), **rouge** (à risque)

### 3.2 Réception d'une alerte
- Affichage dans le dashboard (rafraîchi chaque minute). La notification par mail n'est pas disponible dans le prototype
- Contenu : machine concernée, RUL estimé, niveau (urgent/critique), **capteur principal** (le capteur le plus éloigné de son comportement habituel)
- **Action attendue** : alerte "critique" → intervention dans les 4h ; alerte "urgent" → à planifier

**Le "capteur principal"** indique quel capteur présente la valeur la plus anormale par rapport au comportement habituel de la machine — c'est le premier endroit à inspecter. Exemple : `capteur_principal = vibration_axe_x` signifie que la vibration mesurée s'écarte le plus de la normale, davantage que la température ou la pression.

### 3.3 Retour terrain (important pour améliorer la solution)
Après chaque alerte, transmettre au référent IA du site :
- **Alerte pertinente ?** (oui/non)
- **Cause identifiée**
- **Action réalisée**

Ces retours sont intégrés au réentraînement mensuel du modèle. Un formulaire de saisie dans l'outil est prévu en évolution.

## 4. Comment interpréter les résultats

La solution prédit un **RUL** (temps restant estimé avant intervention
nécessaire, en heures). Le niveau de risque affiché et les alertes en découlent :

| RUL prédit | Niveau affiché | Alerte | Action |
|---|---|---|---|
| > 24h | normal | — | Aucune |
| 9h – 24h | à surveiller | — | Contrôle visuel au prochain tour |
| 5h – 8h | à risque | 🟠 **urgent** | Planifier l'intervention |
| ≤ 4h | à risque | 🔴 **critique** | Intervention **dans les 4h** |

**Pourquoi 4h précisément** : ça correspond à la durée d'un poste de travail
en atelier — une alerte "critique" signifie concrètement "à traiter avant la
fin de votre poste actuel", pas "dans les jours qui viennent".

**Important** : le RUL prédit est une **estimation**, pas une certitude.
En validation, le modèle se trompe en moyenne d'environ 20h (MAE). Une
alerte "critique" à RUL=2h peut en réalité correspondre à une machine qui
tiendra encore plusieurs heures — c'est pourquoi l'inspection humaine reste
la décision finale.

## 5. Limites et conditions d'usage

- **Machines couvertes** : uniquement les centres d'usinage équipés IoT (phase pilote : 3 machines d'un site France)
- **Historique nécessaire** : le modèle a besoin de 30 jours de données stables pour une nouvelle machine
- **Fiabilité dégradée** si un capteur est HS : il apparaît dans le panneau *Alertes capteur*
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
Non. Un point en début de poste et à la mi-poste suffit : une alerte critique laisse 4h pour intervenir.

**Q : Que faire si je ne suis pas d'accord avec une alerte ?**
Le signaler au référent IA avec un commentaire. Le retour est pris en compte au réentraînement suivant.

**Q : Mes données personnelles sont-elles collectées ?**
Non. La solution ne trace que les machines, pas les opérateurs.

**Q : Que se passe-t-il si l'IA se trompe ?**
La décision finale reste humaine. L'IA est un outil d'aide, pas un décideur.
