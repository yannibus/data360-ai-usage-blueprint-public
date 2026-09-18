# Tableau Next — Executive View (Tier 3)

An independent, optional 4th path for the same question this blueprint answers everywhere
else — *who uses AI, how much, and at what estimated cost* — built on **Tableau Next**
(Semantic Data Model + Visualizations + Dashboard) instead of SQL, a Calculated Insight, or a
native Report/Dashboard.

> **Positioning.** This does not replace Tier 1 (SQL), Tier 2a (LWC cockpit on a Calculated
> Insight), or Tier 2b (native Report/Dashboard on a custom DMO). It is a separate,
> independent path for an executive/governance audience who wants a Concierge-enabled,
> conversational dashboard. Adopt it, ignore it, or run it alongside the others — nothing
> here touches Tier 1/2a/2b's artifacts.

---

## What it's built on

Unlike Tier 2a/2b, this tier does **not** depend on a Calculated Insight or a Batch Data
Transform. It builds the Semantic Data Model directly on the two DMOs that are already
populated by the platform:

| DMO | Role | Grain |
|---|---|---|
| `AiAgentGenerativeAiUsage_std__dlm` | Fact ("AI Usage") | one row per generative AI call (LLM invocation) |
| `ssot__User__dlm` | Dimension ("User") | one row per user |

Join: `AiAgentGenerativeAiUsage_std__dlm.UserId__c = ssot__User__dlm.ssot__Id__c`.

No synthetic data, no new ingestion, no clickops transform — same prerequisites as the rest of
this blueprint (`docs/SETUP.md` §1): Data Cloud provisioned, GenAI usage happening, Data Stream
User activated.

## Business logic encoded in the Semantic Data Model

Same rules as `queries/02-flex-credits-per-user.sql` / `queries/03-usage-normalized.sql`, now
expressed as Tableau Next calculated dimensions/measurements instead of SQL:

- **Feature normalization** (`Feature_clc`): `GenAiGatewayFeatureName__c IS NULL` →
  `"Untagged (Flows/Custom)"`. `AgentforceCoworker` and `EmployeeAssistant` are always kept
  distinct, never merged.
- **Usage Date** (`Usage_Date_clc`): the event timestamp truncated to day — the time spine for
  daily/monthly/quarterly trends.
- **Estimated Flex Credits** (`Estimated_Flex_Credits_clc`): feature-conditional, same Feb 2026
  rate card as the rest of the blueprint —
  `AgentforceCoworker → COUNTD(AiAgentInteractionId__c) × 72`; every other feature →
  `SUM(UsageQuantity__c) × 20 + CEILING(SUM(PromptTotalTokenCount__c) / 2000) × 4`.
  **Estimate only — the Digital Wallet remains the billing source of truth.**

### The distinct-count risk — resolved

The Tier 2a Calculated Insight engine cannot use `COUNT(DISTINCT ...)` as a measure (see
`docs/PACKAGING.md`), which is why Tier 2a's Coworker figure can fall back to a per-token
estimate on some orgs. The Tableau Next Semantic Data Model does **not** have that limitation:
`aggregationType: "DistinctCount"` on a plain measurement is rejected by the API
(`POST_BODY_PARSE_ERROR`), but a **calculated measurement** with expression
`COUNTD([table].[field])` and `aggregationType: "UserAgg"` validates cleanly. Confirmed live
against this org on 2026-09-17. So `Round Trips` and `Active Users` are exact distinct counts,
and `Estimated Flex Credits` applies the Coworker 72-FC-per-round-trip rule exactly — no
approximation needed on this tier.

## Metrics

| Metric | API name | Aggregation | Notes |
|---|---|---|---|
| Total Tokens | `total_tokens_mtc` | Sum | Token volume, any period |
| Total Actions | `total_actions_mtc` | Sum | Drives the per-action FC estimate |
| Interactions | `interactions_mtc` | Count | Raw LLM call count — **not** user questions |
| Round Trips | `round_trips_mtc` | Count Distinct (`COUNTD`) | One per real user question |
| Estimated Flex Credits | `estimated_flex_credits_mtc` | Sum of calc field | Feature-conditional, see above |
| Active Users | `active_users_mtc` | Count Distinct (`COUNTD`) | Distinct users in the period |

Dimensions available for slicing: **Feature** (normalized), **Billable** (`IsMeteredIndicator__c`),
**User Name**. Time grains: `Day`, `Month`, `Quarter`.

> **Two Table-visualization gotchas** (both hit and fixed live on this org — see the detail
> table's field/style setup in the build script for the working pattern):
> 1. **`function` must match the calc measurement's own `aggregationType`.** Every calculated
>    measurement in this model (`Total_Tokens_clc`, `Estimated_Flex_Credits_clc`, etc.) is itself
>    `aggregationType: "UserAgg"` (it already wraps its own `SUM(...)`/`COUNTD(...)` expression).
>    A visualization field referencing one of these with `"function": "Sum"` double-aggregates.
> 2. **Table mode requires every field — including measures — to be `displayCategory: "Discrete"`.**
>    `"Continuous"` triggers axis initialization, and Table mode's `style.axis` can only hold
>    continuous fields (it must be present but `{}` when there are none).
>
> Both mistakes are accepted silently by the API at creation time and only fail when the
> visualization is opened, rendering a generic **"Can't show visualization"** card.

## Dashboard — "AI Usage & Cost — Executive View"

- Dark navy header band + purpose line.
- Filters: Usage Date (last 90 days default) + Feature.
- 4 KPI cards: Total Tokens, Estimated Flex Credits, Active Users, Round Trips.
- Chart: Estimated Flex Credits — daily trend, **Area** mark (filled), single accent color
  (`#0176D3`, Salesforce Lightning Blue) — reads as a modern SaaS trend, not a plain line.
- Chart: Estimated Flex Credits by Feature, colored by Billable vs Included (stacked bar).
- Detail table: User × Feature × Total Tokens × Estimated Flex Credits.

**Visual refresh.** All three visualizations and every dashboard card use native, off-the-shelf
Tableau Next chart types and style options — no custom rendering. Two deliberate style choices
replace the default CRM-Analytics-era look: zebra row banding is removed everywhere
(`shading.banding.rows.color` set equal to the background instead of a gray stripe), and widget
corner radius is `10` instead of the default `4` for a softer, rounder card. A native **Donut**
mark type was tried for the feature breakdown and rejected by the live API's validation
(`"axis"`/`"panes"` requirements could not be satisfied with the documented schema in this org's
API version) — kept the proven stacked bar instead of forcing an unstable workaround.

## Concierge (Analytics Agent) sample questions

- "Show me total tokens by feature this month"
- "Which user has the highest estimated Flex Credit usage?"
- "Show me AI usage trend over the last 30 days"
- "Which features are underused?"

Avoid root-cause ("why is X declining?") and cross-filter-vs-benchmark questions — known
Concierge failure patterns, not specific to this model.

## Concierge enablement — already handled by the build script

The build script creates the semantic model with `"agentEnabled": true` set directly in the
model payload — confirmed live on the field (`GET .../ssot/semantic/models/<name>` returns
`"agentEnabled": true`). There is **no separate manual toggle to flip** for a model created
this way (the "Analytics Agent Readiness" UI toggle some Data Cloud docs reference is for
models created through the builder UI, where it defaults off — API-created models set it at
creation time instead). The Concierge/Agentforce panel should appear directly on the
**dashboard** (`AI Usage & Cost — Executive View`) or on individual metric pages — not in the
Semantic Model Builder's "AI Optimization" menu, which is unrelated to this flag.

## Packaging — mostly deployable `force-app` metadata, one clickops piece

Corrected from an earlier assumption: **the Workspace, the 3 visualizations and the dashboard
are genuinely deployable `sfdx` metadata** — confirmed live by retrieving and dry-run
redeploying them against this org with zero diff:

| Component | Type | Path |
|---|---|---|
| `data360_ai_usage_governance` | `AnalyticsWorkspace` | `force-app/.../analyticsWorkspaces/*.uawork-meta.xml` |
| `data360_ai_usage_governance_cost_trend` | `AnalyticsVisualization` | `force-app/.../analyticsVisualizations/*.uaviz-meta.xml` |
| `data360_ai_usage_governance_cost_feature` | `AnalyticsVisualization` | `force-app/.../analyticsVisualizations/*.uaviz-meta.xml` |
| `data360_ai_usage_governance_detail_table` | `AnalyticsVisualization` | `force-app/.../analyticsVisualizations/*.uaviz-meta.xml` |
| `data360_ai_usage_governance_dashboard` | `AnalyticsDashboard` | `force-app/.../analyticsDashboards/*.uadash-meta.xml` |

**The one clickops-only piece is the Semantic Data Model itself** (`/ssot/semantic/models/...`)
— there is no `AnalyticsSemanticModel` (or equivalent) metadata type in this org's Metadata API
registry (checked the full 440-type list). This mirrors Tier 2b exactly: the custom DMO + Batch
Data Transform are clickops, but the reports/dashboard built on top of it are deployable
metadata. Here, the Semantic Data Model is clickops, but the workspace/visualizations/dashboard
built on top of it are deployable metadata.

**Same ordering trap as Tier 2b applies:** the `AnalyticsWorkspace` and `AnalyticsVisualization`/
`AnalyticsDashboard` records reference the semantic model by API name (`data360_ai_usage_governance`).
Deploying this metadata to an org where that semantic model does not exist yet will very likely
fail or deploy into a broken/unlinked state — build the Semantic Data Model first.

### Two ways to reproduce this tier

1. **From zero** (no Semantic Data Model on the target org yet) — run the build script, which
   creates the Semantic Data Model *and* the workspace/visualizations/dashboard in one pass:
   ```bash
   python3 tableau_next/data360_ai_usage_governance_next_demo.py
   ```
   Idempotent — deletes and recreates the workspace, semantic model and dashboard by name every
   run. Authenticates via SF-CLI passthrough (`sf api request rest ... --target-org <alias>`,
   edit `ORG_ALIAS` at the top of the file) — no Connected App or credentials file needed, since
   this tier only touches Semantics/Visualizations/Dashboards/Workspaces on DMOs that already
   exist and are already populated; it does not ingest anything.
2. **Redeploy visuals only** (the Semantic Data Model already exists — e.g. rebuilt once, or
   provisioned via a Data Cloud Data Kit) — deploy just the metadata layer:
   ```bash
   sf project deploy start -o <alias> \
     -d force-app/main/default/analyticsWorkspaces \
     -d force-app/main/default/analyticsVisualizations \
     -d force-app/main/default/analyticsDashboards
   ```

## Teardown

Delete the workspace `data360_ai_usage_governance` from Data 360 → Workspaces (deletes the
semantic model, visualizations and dashboard with it). No other tier is affected.
