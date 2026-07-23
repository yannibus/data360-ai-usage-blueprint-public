# Prérequis — Activer le data stream « User » (une seule fois)

> **À faire une seule fois par org, avant les Options 1 et 2.**
> Durée : ~5 minutes + le temps d'un premier rafraîchissement.

## Pourquoi cette étape

La télémétrie d'usage AI de Salesforce n'enregistre que l'**identifiant technique** de l'utilisateur
(un code du type `005…`), pas son nom. Pour que vos requêtes et vos rapports affichent des **noms
lisibles**, il faut que Data Cloud dispose des données de l'objet **User**. C'est le rôle du data
stream User.

**Sans cette étape :** tout fonctionne, mais chaque ligne montre un code `005…` au lieu d'un nom — donc
illisible pour un pilotage par utilisateur.

## Étapes

1. Allez dans **Configuration (Setup)** → recherchez **« Data Cloud »** → ouvrez **Data Cloud Setup**.
2. Ouvrez **Data Streams** (flux de données).
3. Repérez le flux du **connecteur Salesforce CRM** (celui qui relie votre org à Data Cloud).
   - S'il existe déjà : cliquez dessus pour l'éditer.
   - S'il n'existe pas encore : créez-le via **New** → connecteur **Salesforce CRM**.
4. Dans la liste des objets à inclure, **cochez l'objet `User`**.
5. **Enregistrez** et laissez le flux **s'exécuter une fois** (quelques minutes selon le volume).

## Vérifier que c'est bon

1. Ouvrez l'app **Data Cloud** → **Query Editor**.
2. Collez et exécutez :

   ```sql
   SELECT COUNT(*) FROM ssot__User__dlm;
   ```

3. Le résultat doit être **supérieur à 0**. Si c'est le cas, les noms se résoudront dans toutes les
   requêtes et rapports.

> Si le résultat est 0 ou la table introuvable : le flux n'a pas encore tourné, ou l'objet `User`
> n'est pas coché. Reprenez l'étape 4 et relancez le flux.

---

**Étape suivante :** choisissez votre option dans le [Guide](00-Guide.md) —
[Option 1](02-Option-1-Requetes-a-la-demande.md) ou [Option 2](03-Option-2-Rapport-et-Dashboard.md).
