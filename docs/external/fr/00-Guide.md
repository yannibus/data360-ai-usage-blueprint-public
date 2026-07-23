# Visibilité sur l'usage AI — Guide administrateur

> **Pour qui :** administrateurs Salesforce qui veulent de la visibilité sur **qui utilise Agentforce /
> GenAI, combien, et le coût estimé**. Tout se fait **manuellement dans l'UI Salesforce** — pas de code,
> pas de ligne de commande, pas de package à installer.

Ce guide est le point d'entrée. Il présente **deux options** et vous renvoie vers un pas-à-pas détaillé
pour chacune. Une version anglaise est disponible dans le dossier `../en/`.

---

## ⚠️ À lire d'abord — c'est une estimation, pas votre facture

Cette solution lit la **télémétrie standard d'usage AI** de Salesforce et la transforme en rapports
lisibles et en **estimations** de crédits. C'est un **outil de pilotage et de visibilité de l'adoption**.

> **Le Digital Wallet reste l'unique source de vérité pour la facturation.** Les montants en Flex Credits
> affichés ici sont des *estimations* basées sur la grille tarifaire publiée actuelle. Une partie de la
> consommation (par exemple les données ingérées via des connecteurs) n'apparaît **que** dans le Digital
> Wallet et n'est pas couverte ici. Toujours réconcilier avec **Setup → Digital Wallet** avant toute
> décision de budget ou contractuelle.

---

## Les deux options

Deux façons d'obtenir cette visibilité, de la plus légère à la plus riche. **Vous n'avez pas besoin des
deux** — choisissez celle qui correspond à la fréquence dont vous avez besoin et à l'investissement
souhaité.

| Option | Ce que vous obtenez | Coût récurrent | Effort | Pas-à-pas |
|---|---|---|---|---|
| **1 — Requêtes à la demande** | Des réponses à la demande dans le Query Editor | **Aucun** — vous ne payez qu'à l'exécution | Le plus faible | [`02-Option-1-Requetes-a-la-demande.md`](02-Option-1-Requetes-a-la-demande.md) |
| **2 — Rapport & Dashboard** | Un Report + Dashboard natif, par utilisateur, rafraîchi | **Faible, récurrent** (compute) | Moyen | [`03-Option-2-Rapport-et-Dashboard.md`](03-Option-2-Rapport-et-Dashboard.md) |

> **Notre recommandation :** commencez par l'**Option 1** pour explorer les données à coût récurrent nul.
> Passez à l'**Option 2** quand vous voulez un dashboard qui se rafraîchit automatiquement et se partage
> avec votre équipe.

---

## Par où commencer

1. **Prérequis (une seule fois)** — activer le data stream User pour que les noms d'utilisateurs se
   résolvent : [`01-Prerequis-Data-Stream-User.md`](01-Prerequis-Data-Stream-User.md).
2. **Option 1** — requêtes à la demande : [`02-Option-1-Requetes-a-la-demande.md`](02-Option-1-Requetes-a-la-demande.md).
3. **Option 2** — rapport & dashboard : [`03-Option-2-Rapport-et-Dashboard.md`](03-Option-2-Rapport-et-Dashboard.md).

---

## Comprendre le coût

- L'**Option 1** n'a **aucun coût récurrent** — vous n'êtes facturé que pour chaque requête exécutée.
- L'**Option 2** utilise du **compute en arrière-plan** (un rafraîchissement planifié des données), qui
  consomme une petite quantité de crédits en continu — léger à volume normal. Vous pouvez la réduire en
  rafraîchissant **moins souvent** et en utilisant des rafraîchissements **incrémentaux**.
- Tout le compute est tracké, et toute la facturation réelle vit, dans le **Digital Wallet** (**Setup →
  Digital Wallet**). Consultez-le pour la consommation réelle.

> **Rappel :** les chiffres de crédits dans les rapports sont des **estimations** pour vous aider à
> planifier. Ils ne **remplacent pas** le Digital Wallet, qui est l'enregistrement faisant foi de ce qui
> vous est facturé.

> **💡 Une vue supplémentaire gratuite, directement dans le Digital Wallet.** Le Wallet propose aussi un
> rapport intégré **« Usage by User ID »** — sans configuration ni coût récurrent ([aide
> Salesforce](https://help.salesforce.com/s/articleView?id=xcloud.wallet_custom_report_userid.htm&language=en_US&type=5)). Pratique comme
> recoupement rapide, avec **deux points à garder en tête** : il affiche un **ID utilisateur, pas un nom
> lisible**, et cet ID n'est renseigné **que pour l'activité des Employee Agents** (actions d'agent
> standard et personnalisées) — l'usage des Service Agents, invités, utilisateurs externes ou automations
> apparaît sans utilisateur. C'est donc un complément utile, mais **pas une vue par utilisateur complète**
> — c'est ce qu'apportent les Options 1 et 2.

---

## Une note sur Agentforce Coworker

Si votre org utilise **Agentforce Coworker**, son usage est estimé **par aller-retour de conversation**
(une question utilisateur et sa réponse), ce qui reflète son mode de tarification — plutôt que purement au
volume de texte. Les requêtes et rapports gèrent cela pour vous ; vous n'avez rien à calculer. Comme
toujours, le **Digital Wallet** est le chiffre à retenir pour la facturation.

---

## Aide-mémoire

| Vous voulez… | Utiliser | Coût récurrent |
|---|---|---|
| Vérifier un chiffre ponctuellement | **Option 1** — Query Editor | Aucun |
| Partager un dashboard rafraîchi | **Option 2** — Report & Dashboard | Faible |
| Savoir ce qui vous est réellement facturé | **Digital Wallet** (Setup) | — |

*Les estimations utilisent la grille tarifaire publiée actuelle et peuvent changer. Toujours confirmer
avec le Digital Wallet.*
