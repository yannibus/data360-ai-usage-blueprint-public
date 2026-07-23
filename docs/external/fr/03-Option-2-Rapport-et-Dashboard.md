# Option 2 — Rapport & Dashboard natifs (faible coût récurrent)

> **Pour aller plus loin que les requêtes ponctuelles.** Vous obtenez un **Rapport** et un
> **Dashboard** Salesforce natifs, par utilisateur nommé, qui **se rafraîchissent automatiquement**
> et se partagent avec votre équipe. Tout se construit **manuellement dans l'UI**.
> **Prérequis :** [le data stream User doit être activé](01-Prerequis-Data-Stream-User.md).

## Pourquoi une étape de préparation des données

La télémétrie d'usage AI et les noms d'utilisateurs vivent dans deux jeux de données séparés. Un
rapport natif ne sait pas les relier directement. Il faut donc d'abord **fusionner les deux** dans un
nouvel objet, une fois, à l'aide d'un **Data Transform** (une transformation de données planifiée).
Ce nouvel objet devient la source de vos rapports.

C'est cette transformation planifiée qui génère un **faible coût récurrent** (voir la fin de ce
document).

---

## Étape 1 — Créer le Data Transform (fusion des données)

1. Ouvrez l'app **Data Cloud** → onglet **Data Transforms** (si masqué : **More** → Data Transforms).
2. Cliquez **New** → choisissez **Batch Data Transform** → **Next**.
3. Type de source : **Data Model Objects**. Sélectionnez votre **Data Space**.
4. **Ajoutez deux sources** :
   - **`AiAgentGenerativeAiUsage_std__dlm`** (la télémétrie d'usage AI),
   - **`ssot__User__dlm`** (les utilisateurs — nom, identifiant).
5. Ajoutez un **nœud Join** entre les deux (survolez le connecteur → **Add Node → Join**) :
   - Type **Inner Join**.
   - Clé de jointure : **`UserId__c` = `ssot__Id__c`** (généralement détectée automatiquement).
   - *À savoir :* l'Inner Join ne garde que les utilisateurs ayant un usage AI réel — c'est ce que
     vous voulez pour un rapport par utilisateur.

## Étape 2 — Écrire le résultat dans un nouvel objet

1. (Optionnel) Ajoutez un **nœud Formula** pour nettoyer les données — par exemple relabelliser
   l'usage sans étiquette en « Non tagué », ou ajouter une colonne « jour ». Ce n'est pas obligatoire.
2. Ajoutez un **nœud Output → Create New**.
   - ⚠️ **Créez le nouvel objet depuis ce nœud Output.** Un objet créé ailleurs (onglet Data Model)
     ne sera pas sélectionnable ici.
   - Nommez-le, par exemple **`AI_Usage_Report`**, mappez les champs, définissez une **clé primaire**.
3. **Enregistrez** le transform (donnez-lui un nom parlant, par ex. « AI Usage — Jointure User »).

## Étape 3 — Exécuter et planifier

1. Depuis l'onglet **Data Transforms**, à côté de votre transform, cliquez sur **Run Now** pour un
   premier remplissage.
2. Puis définissez une **planification (Schedule)** — quotidienne suffit dans la plupart des cas.
   - Choisissez un rafraîchissement **incrémental** pour ne traiter que les nouvelles lignes et
     **limiter le coût**.

## Étape 4 — Créer le Rapport

1. Allez dans **Reports → New Report**.
2. Dans le sélecteur de type de rapport, choisissez la catégorie **Data 360** → sélectionnez votre
   nouvel objet (**`AI_Usage_Report`**).
3. Construisez le rapport :
   - **Groupez par Utilisateur**, puis par **Fonctionnalité**.
   - Ajoutez des **totaux (Sum)** sur les tokens et les actions.
   - Ajoutez éventuellement un regroupement par **date (par jour)** pour une vue temporelle.
4. **Enregistrez** dans un dossier de rapports dédié (par ex. « AI Usage Governance »).

> Vous pouvez créer plusieurs rapports sur le même objet : usage par utilisateur, crédits estimés,
> usage dans le temps.

## Étape 5 — Créer le Dashboard

1. Allez dans **Dashboards → New Dashboard**.
2. Ajoutez des composants pointant vers le(s) rapport(s) de l'étape 4 :
   - des **indicateurs clés** (tokens totaux, actions totales, nombre d'aller-retours),
   - un **graphique d'évolution dans le temps**,
   - une **répartition par utilisateur** et **par fonctionnalité**.
3. **Enregistrez** dans le même dossier et **partagez** dossier + dashboard avec les profils concernés
   (accès en lecture).

---

## Comprendre le coût

- Cette option repose sur un **rafraîchissement planifié** des données (le Data Transform), qui
  consomme une petite quantité de crédits **en continu** — léger à volume normal.
- Pour réduire ce coût : rafraîchissez **moins souvent** et utilisez des rafraîchissements
  **incrémentaux**.
- La consommation réelle est tracée dans le **Digital Wallet** (**Setup → Digital Wallet**).

> ⚠️ **Rappel important.** Les crédits affichés dans les rapports sont des **estimations** basées sur
> la grille tarifaire publiée. Le **Digital Wallet** reste la **source de vérité de facturation**.
> Utilisez ces rapports pour piloter l'**adoption**, pas pour vérifier une facture.

---

**Besoin d'une réponse rapide et gratuite plutôt qu'un dashboard permanent ?** Voir l'
[Option 1 — Requêtes à la demande](02-Option-1-Requetes-a-la-demande.md).
