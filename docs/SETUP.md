# SETUP — Data360 AI Usage Blueprint

End-to-end reproduction guide. Follow only the tier(s) you need — they are independent.
Everything here is authored in English; the LWC cockpit ships with a French translation
(`translations/fr.translation-meta.xml`) that activates automatically for FR users.

> **Target org:** deploy/validate on your own Data-Cloud-enabled org. **Always confirm the
> target org before deploying** — see step 0.

---

## 0. Confirm your target org (do this every time)

```bash
sf config get target-org          # what "default" points at right now
sf org display --target-org <alias>   # confirm instance + user before any deploy
```

Pass `--target-org <alias>` explicitly on every command below. The default org can silently
drift; an accidental deploy to the wrong org is the most common mistake with this blueprint.

---

## 1. Prerequisites (both tiers)

| # | Requirement | How to check | Fix if missing |
|---|---|---|---|
| 1 | **Data Cloud provisioned** | Setup → *Data Cloud Setup* shows a data space | Enable Data Cloud (licenses `Data Cloud` / `Customer Data Platform`) |
| 2 | **Agentforce / GenAI usage happening** | Query `AiAgentGenerativeAiUsage_std__dlm` returns rows | Use an Agentforce agent / GenAI feature; the platform auto-populates the DMO |
| 3 | **Data Stream User active** | Query `ssot__User__dlm` returns rows | **UI-only step, see §1.1** |

### 1.1 Activate the Data Stream User (UI-only — not metadata)

Without it, usage rows carry only the raw `005…` User Id and **names never resolve**.

1. **Data Cloud Setup → Salesforce CRM (or the Salesforce connector) → Data Streams**.
2. Add / edit the CRM data stream and **check the `User` object**.
3. Save and let it run once. Confirm: `SELECT COUNT(*) FROM ssot__User__dlm` > 0.

This is a clickops prerequisite on every org — it cannot ship as metadata. Flag it to whoever
reproduces the blueprint.

### 1.2 Verify the telemetry schema (optional sanity check)

```bash
sf api request rest "/services/data/v64.0/ssot/queryv2" --method POST \
  --body '{"sql":"SELECT COUNT(*) FROM AiAgentGenerativeAiUsage_std__dlm"}' \
  --target-org <alias>
```

The Data Cloud Query API endpoint used throughout is `POST /services/data/v64.0/ssot/queryv2`
with body `{"sql":"..."}`.

---

## 2. Tier 1 — SQL pay-per-look (zero recurring cost)

No deployment, no materialization. You spend only when you run a query.

Open **Data Cloud app → Query Editor**, paste one of the three queries below, and run. The join
to `ssot__User__dlm` lives **inside the SQL**, so names resolve on demand — nothing is materialized.
The same queries live as files under `queries/` in this repo.

> **Feature pitfall (applies to all three):** each `GenAiGatewayFeatureName__c` value is a DISTINCT
> product. `EmployeeAssistant` and `AgentforceCoworker` are **separate agent types** — never merge
> them. `AgentforceCoworker` was renamed from the old `AESSearchAgent` the week of 22/29 June 2026.
> To isolate Coworker: `WHERE feature = 'AgentforceCoworker'`.

### Query 1 — GenAI usage per user (`queries/01-genai-usage-per-user.sql`)

Who uses which AI feature, and at what token volume.

```sql
SELECT
    u."ssot__FullName__c"                         AS user_name,
    u."ssot__Username__c"                         AS username,
    a."GenAiGatewayFeatureName__c"                AS feature,
    SUM(a."PromptTotalTokenCount__c")             AS total_tokens,
    SUM(a."PromptInputTokenCount__c")             AS input_tokens,
    SUM(a."PromptCompletionTokenCount__c")        AS completion_tokens,
    COUNT(*)                                      AS nb_interactions
FROM "AiAgentGenerativeAiUsage_std__dlm" a
JOIN "ssot__User__dlm" u
    ON a."UserId__c" = u."ssot__Id__c"
GROUP BY
    u."ssot__FullName__c",
    u."ssot__Username__c",
    a."GenAiGatewayFeatureName__c"
ORDER BY total_tokens DESC
LIMIT 50;
```

### Query 2 — Estimated Flex Credits per user (`queries/02-flex-credits-per-user.sql`)

Translates raw usage into an **estimate** of Flex Credits, per user × feature, split by billable
(`is_metered`) vs included. Rate card (Feb 2026): **20 FC / action**; **4 FC / 2000 tokens**.
**Estimation only — the Digital Wallet remains the billing source of truth.**

> **Agentforce Coworker is metered PER ROUND-TRIP, not per token: 72 FC / round-trip**
> (Salesforce pricing rule). A round-trip = one distinct `AiAgentInteractionId__c` (one user
> question, whatever the number of internal LLM calls it triggers). This was validated live on
> a reference org: four controlled questions each produced exactly **+1** distinct
> `AiAgentInteractionId__c`, regardless of token volume (short and long questions alike). The per-token
> formula over/under-charged Coworker by up to 3×, so Query 2/3 apply a **feature-conditional**
> rule: `AgentforceCoworker → COUNT(DISTINCT AiAgentInteractionId__c) * 72`; every other feature
> keeps `actions*20 + ceil(tokens/2000)*4`. Also note `nb_interactions` (`COUNT(*)`, raw LLM
> calls) ≠ `nb_roundtrips` (`COUNT(DISTINCT AiAgentInteractionId__c)`, user questions).

```sql
SELECT
    u."ssot__FullName__c"                                            AS user_name,
    u."ssot__Username__c"                                            AS username,
    a."GenAiGatewayFeatureName__c"                                   AS feature,
    a."IsMeteredIndicator__c"                                        AS is_metered,
    SUM(a."UsageQuantity__c")                                        AS nb_actions,
    COUNT(DISTINCT a."AiAgentInteractionId__c")                      AS nb_roundtrips,
    SUM(a."UsageQuantity__c") * 20                                   AS estimated_fc_actions,
    SUM(a."PromptTotalTokenCount__c")                                AS total_tokens,
    CEILING(SUM(a."PromptTotalTokenCount__c") / 2000.0) * 4          AS estimated_fc_tokens,
    -- Coworker is billed per round-trip (72 FC); every other feature per action+token.
    CASE
        WHEN a."GenAiGatewayFeatureName__c" = 'AgentforceCoworker'
            THEN COUNT(DISTINCT a."AiAgentInteractionId__c") * 72
        ELSE (SUM(a."UsageQuantity__c") * 20)
             + (CEILING(SUM(a."PromptTotalTokenCount__c") / 2000.0) * 4)
    END                                                             AS total_estimated_fc
FROM "AiAgentGenerativeAiUsage_std__dlm" a
JOIN "ssot__User__dlm" u
    ON a."UserId__c" = u."ssot__Id__c"
GROUP BY
    u."ssot__FullName__c",
    u."ssot__Username__c",
    a."GenAiGatewayFeatureName__c",
    a."IsMeteredIndicator__c"
ORDER BY total_estimated_fc DESC
LIMIT 50;
```

### Query 3 — Normalized usage (`queries/03-usage-normalized.sql`)

The clean view: each feature kept **distinct**, `NULL` feature relabelled `Untagged`, plus a day
axis for time charts. This is the exact logic the Calculated Insight `AI_Usage_By_User__cio` encodes.

```sql
SELECT
    u."ssot__FullName__c"                                           AS user_name,
    u."ssot__Username__c"                                           AS username,
    CASE
        WHEN a."GenAiGatewayFeatureName__c" IS NULL
            THEN 'Untagged (Flows/Custom)'
        ELSE a."GenAiGatewayFeatureName__c"
    END                                                             AS feature_normalized,
    CAST(a."Timestamp__c" AS DATE)                                  AS usage_day,
    a."IsMeteredIndicator__c"                                       AS is_metered,
    SUM(a."PromptTotalTokenCount__c")                               AS total_tokens,
    SUM(a."PromptInputTokenCount__c")                               AS input_tokens,
    SUM(a."PromptCompletionTokenCount__c")                          AS completion_tokens,
    COUNT(*)                                                        AS nb_interactions,
    COUNT(DISTINCT a."AiAgentInteractionId__c")                     AS nb_roundtrips,
    SUM(a."UsageQuantity__c")                                       AS nb_actions,
    SUM(a."UsageQuantity__c") * 20                                  AS estimated_fc_actions,
    CEILING(SUM(a."PromptTotalTokenCount__c") / 2000.0) * 4         AS estimated_fc_tokens,
    -- Coworker is billed per round-trip (72 FC); every other feature per action+token.
    CASE
        WHEN a."GenAiGatewayFeatureName__c" = 'AgentforceCoworker'
            THEN COUNT(DISTINCT a."AiAgentInteractionId__c") * 72
        ELSE (SUM(a."UsageQuantity__c") * 20)
             + (CEILING(SUM(a."PromptTotalTokenCount__c") / 2000.0) * 4)
    END                                                             AS total_estimated_fc
FROM "AiAgentGenerativeAiUsage_std__dlm" a
JOIN "ssot__User__dlm" u
    ON a."UserId__c" = u."ssot__Id__c"
GROUP BY
    u."ssot__FullName__c",
    u."ssot__Username__c",
    CASE
        WHEN a."GenAiGatewayFeatureName__c" IS NULL
            THEN 'Untagged (Flows/Custom)'
        ELSE a."GenAiGatewayFeatureName__c"
    END,
    CAST(a."Timestamp__c" AS DATE),
    a."IsMeteredIndicator__c"
ORDER BY usage_day DESC, total_tokens DESC
LIMIT 200;
```

---

## 3. Tier 2a — LWC cockpit on the Calculated Insight (the "wow")

Recurring CI compute. Ships as clean deployable metadata.

### 3.1 Deploy

```bash
# from the project root
sf project deploy start --target-org <alias>
```

This deploys, among others:
- `mktCalcInsightObjectDefs/AI_Usage_By_User` — the Calculated Insight definition.
- `classes/AiUsageCockpitController` — Apex reading the CI via `ConnectApi.CdpQuery.queryANSISQLV2`
  (native Data Cloud query, **no HTTP callout, no Named Credential**).
- `lwc/aiUsageCockpit` — the cockpit component (hand-built SVG charts, brand-2026 styling).
- `labels/CustomLabels` + `translations/fr.translation-meta.xml` — EN labels + FR translation.
- `flexipages/AI_Usage_Cockpit_Page`, `tabs/AI_Usage_Cockpit_Page`,
  `applications/AI_Usage_Governance`, `permissionsets/AI_Usage_Cockpit_User`.

### 3.2 Let the CI materialize

A newly deployed CI must run once before it returns rows. Open **Data Cloud → Calculated
Insights → AI Usage By User → Run/Refresh** (or wait for its schedule). Confirm:

```bash
sf api request rest "/services/data/v64.0/ssot/queryv2" --method POST \
  --body '{"sql":"SELECT feature_normalized__c, SUM(total_tokens__c) FROM AI_Usage_By_User__cio GROUP BY feature_normalized__c"}' \
  --target-org <alias>
```

### 3.3 Grant access + place the component

1. Assign the permission set:
   ```bash
   sf org assign permset --name AI_Usage_Cockpit_User --target-org <alias>
   ```
2. Open the **AI Usage Governance** app (App Launcher) → the **AI Usage Cockpit** tab. The
   FlexiPage already hosts the component. To place it elsewhere, edit any Lightning page and drag
   the **aiUsageCockpit** custom component onto it.

> **Browser-verify tip:** hard-navigate to the
> Lightning domain — `https://<instance>.lightning.force.com/lightning/n/AI_Usage_Cockpit_Page` —
> rather than the `.my.salesforce.com` frontdoor, which can fail to resolve custom tab routes.

---

## 4. Tier 2b — Native Report + Dashboard on a custom DMO

Recurring transform compute. The **transform + custom DMO are clickops**; the **3 reports + the
grid dashboard are deployable metadata**.

1. Build the **Batch Data Transform → custom DMO** by following the full runbook:
   **`docs/tier1-report-dashboard-runbook.md`** (step-by-step, with every builder gotcha).
   The output DMO must be named **`AI_Usage_report__dlm`** (lowercase `report` — this is the exact
   name to use) so the platform's auto-generated report type
   `CustomEntity$AI_Usage_Report__dlm` (capital `R`) matches the packaged reports.
2. Once the DMO exists and has run once, deploy the report layer:
   ```bash
   sf project deploy start \
     -d force-app/main/default/reports \
     -d force-app/main/default/dashboards \
     --target-org <alias>
   ```
3. Open the **AI Usage — Adoption** dashboard (folder *AI Usage Governance*).

> Why 2b exists next to 2a: a report **on the CI** is summary-only (no metric/gauge/table tiles,
> no detail rows). The custom DMO removes those limits so the native dashboard matches the design.
> If summary charts suffice, report directly on the CI and skip the transform entirely.

---

## 5. Cost & Trust notes (say these out loud in a demo)

- **Tier 1 = zero recurring cost.** You pay per query run, nothing is materialized.
- **Tier 2a (CI) and 2b (transform) = recurring compute**, tracked in the **Digital Wallet**.
  The batch transform is billed on `max(rows read, rows written)` (~400 credits / 1M rows,
  order-of-magnitude) — light at demo volume, honest to disclose at client scale.
- **Flex Credit figures are estimates** (Feb-2026 rate card). The **Digital Wallet is the billing
  source of truth**; connector-data consumption (e.g. SharePoint ingestion) appears only there.
- **Agentforce Coworker is metered per round-trip: 72 FC / round-trip** (one round-trip = one
  distinct `AiAgentInteractionId__c` = one user question). Validated live. The Tier 1 SQL
  (`queries/02`, `03`) applies this exact rule; every other feature keeps the per-action/per-token
  estimate.
- **Tier 2a cockpit caveat on Coworker:** the reference CI was published at a coarser grain
  before this rule was known, and the platform refuses to add the interaction dimension to an
  **already-published** CI. So on the reference org the cockpit still shows Coworker at the per-token estimate;
  the exact 72/round-trip figure comes from the Tier 1 SQL. A **fresh** deploy of
  `mktCalcInsightObjectDefs/AI_Usage_By_User` uses the correct round-trip grain from the start —
  **verified 2026-07-10 on a fresh Data-Cloud org:** the interaction-grain CI
  `sf project deploy start` succeeds (`Created MktCalcInsightObjectDef`) where the same grain change
  is *rejected* on the already-published CI. Note: the CI only **materializes/validates at
  runtime once its source DMOs exist** — on an org with no Agentforce telemetry yet
  (`AiAgentGenerativeAiUsage_std__dlm` / `ssot__User__dlm` absent) the definition deploys and
  registers but the engine reports "does not exist in data space context" until the DMOs are present
  and it runs. So on a real client org (telemetry present) the fresh-grain CI is the correct path;
  the runtime grammar of `MAX(72)`/interaction grain is proven-deployable, not yet proven-materialized
  on populated fresh data.
- **Complementary native path — Wallet "Usage by User ID" (free, but by ID not name).** For a zero-setup, zero-recurring view *by User ID*, the **Digital Wallet** ships a standard report on the `TenantEnrichedUsageEvent` DLO ([SF help: *Create a Report on Usage by User ID*](https://help.salesforce.com/s/articleView?id=xcloud.wallet_custom_report_userid.htm&language=en_US&type=5)). It surfaces a raw **ID, not a name**, on a **different object at a different grain** than this blueprint (billing-event grain vs `AiAgentGenerativeAiUsage_std__dlm`'s AI-interaction grain), so it does **not** replace Tier 1/2. **Coverage caveat:** `User ID` populates **only for Employee Agent events** (`Agentforce_StandardAction`, `Agentforce_CustomAction`) — Service Agents, guests, external and automation stay blank. Position it as a quick native cross-check on billed usage. (The `TenantEnrichedUsageEvent` DLO is org-conditional — e.g. absent on the reference org as of 2026-07-22.)
- Everything is built on **real standard Data Cloud models** — nothing fabricated.

---

## 6. Uninstall / rollback

- Tier 1: nothing to remove (no metadata).
- Tier 2a: `sf project delete source` the deployed components, then delete the CI from the Data
  Cloud UI (a published/"in use" CI cannot be removed via the metadata API — deactivate/delete it
  from **Data Cloud → Calculated Insights** first).
- Tier 2b: delete the reports/dashboard metadata, then delete the Batch Data Transform and its
  custom DMO from the Data Cloud UI.
