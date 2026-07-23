# Option 1 — Requêtes à la demande (aucun coût récurrent)

> **L'option la plus légère.** Vous lancez une requête quand vous voulez une réponse ; rien ne tourne
> en arrière-plan, donc **aucun coût récurrent** — vous ne payez qu'à l'exécution.
> **Prérequis :** [le data stream User doit être activé](01-Prerequis-Data-Stream-User.md).

## Ce que vous obtenez

Trois requêtes prêtes à l'emploi, à coller dans le Query Editor :

| Requête | Ce qu'elle répond | Fichier |
|---|---|---|
| **1 — Usage par utilisateur** | Qui utilise quelle fonctionnalité, à quel volume de tokens | [`requetes/01-usage-par-utilisateur.sql`](requetes/01-usage-par-utilisateur.sql) |
| **2 — Flex Credits estimés** | L'estimation de crédits par utilisateur × fonctionnalité | [`requetes/02-flex-credits-par-utilisateur.sql`](requetes/02-flex-credits-par-utilisateur.sql) |
| **3 — Vue normalisée** | La vue propre, avec un axe par jour pour les tendances | [`requetes/03-usage-normalise.sql`](requetes/03-usage-normalise.sql) |

## Étapes

1. Ouvrez l'app **Data Cloud** → onglet **Query Editor**.
2. Ouvrez l'un des trois fichiers `.sql` ci-dessus, **copiez tout son contenu**.
3. **Collez-le** dans le Query Editor.
4. Cliquez sur **Run**.
5. Lisez les résultats directement dans la grille, ou exportez-les (bouton d'export de la grille).

## Comment lire les résultats

- **`fonctionnalite`** — le produit AI qui a généré l'usage. Chaque valeur est un produit distinct
  (par ex. `EmployeeAssistant`, `AgentforceCoworker`). `Non tagué` = usage sans étiquette (Flows,
  composants custom) ; c'est de la consommation réelle, à surveiller.
- **`facture` (is_metered)** — `true` = usage facturé ; `false` = usage inclus dans la licence.
- **`nb_aller_retours`** — le nombre de questions utilisateur (échanges question/réponse). C'est
  l'unité de facturation d'Agentforce Coworker.
- **`fc_total_est`** — l'**estimation** de Flex Credits. Voir le rappel ci-dessous.

## Astuces

- **Isoler Agentforce Coworker :** ajoutez `WHERE a."GenAiGatewayFeatureName__c" = 'AgentforceCoworker'`
  avant le `GROUP BY`.
- **Changer la période :** ajoutez un filtre sur la date, par ex.
  `WHERE a."Timestamp__c" >= '2026-01-01T00:00:00Z'`.
- **Voir plus de lignes :** augmentez la valeur du `LIMIT` en bas de la requête.

> ⚠️ **Rappel important.** Les colonnes de crédits (`fc_...`) sont des **estimations** basées sur la
> grille tarifaire publiée. Le **Digital Wallet** (**Setup → Digital Wallet**) reste la **source de
> vérité de facturation**. Utilisez ces requêtes pour piloter l'**adoption**, pas pour vérifier une
> facture.

---

**Envie d'un tableau de bord qui se rafraîchit tout seul ?** Passez à l'
[Option 2 — Rapport & Dashboard](03-Option-2-Rapport-et-Dashboard.md).
