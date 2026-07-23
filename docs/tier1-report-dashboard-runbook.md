# Tier 2b — Native Report + Dashboard via a custom DMO (Runbook)

> **Purpose:** stand up an admin-owned, native Data Cloud **Report + Dashboard** that shows AI
> usage **per named user**, reproducing the cockpit's story without an LWC.
> **Target org: the reference org only.**
>
> **Read this first — it renames the deliverable.** An earlier draft of this runbook tried to
> build a native report by *joining two DMOs in the report/Custom-Report-Type builder*. **That is
> impossible** for this telemetry DMO (see "Why the direct report fails" below). The supported
> path — confirmed by official Salesforce docs (2026-07-09) — is to **materialize the
> join with a Batch Data Transform into a custom DMO, then report on that DMO.** Because that is
> recurring compute, this deliverable is **Tier 2b**, not the zero-cost Tier 1. (Tier 1 = the SQL
> query pack in the Query Editor, which joins DMOs in-SQL at no recurring cost.)

## Why the direct report fails (platform truth — don't retry it)

- The raw DMO `AiAgentGenerativeAiUsage_std__dlm` exposes only `UserId__c` (a raw Id), not a name.
- A Data 360 **Custom Report Type cannot relate this DMO to `ssot__User__dlm`**: the relationship
  is not surfaced in the builder ("**The selected object has no further relatable objects**"),
  regardless of which DMO is primary. This is a platform limit on this system DMO, not a config bug.
- Therefore the user *name* can only reach a native report if the join is **materialized first**,
  via either a Calculated Insight (Tier 2a, already deployed) or a **Batch Data Transform → custom
  DMO** (this runbook). Both are recurring compute.
- **A report on the existing CI (`AI_Usage_By_User__cio`) is possible** (Reports → New Report →
  Data 360 → the CI) but it is **summary-only**: no metric/gauge/table dashboard tiles, no detail
  rows, no report formulas. If summary charts are enough, use the CI and skip this runbook. Use the
  custom DMO below when you want the full designed dashboard (KPI tiles, detail, formulas).

## Source objects & fields (already populated on the reference org)

DMO **`AiAgentGenerativeAiUsage_std__dlm`** (the "many"/child):
- `GenAiGatewayFeatureName__c` (feature; each value is a DISTINCT product — `EmployeeAssistant` and `AgentforceCoworker` are SEPARATE agent types, never merge them; NULL = untagged)
- `PromptTotalTokenCount__c`, `PromptInputTokenCount__c`, `PromptCompletionTokenCount__c`
- `UsageQuantity__c` (actions), `IsMeteredIndicator__c` (true = billable), `Timestamp__c`, `UserId__c`

DMO **`ssot__User__dlm`** (the "one"/parent): `ssot__Id__c`, `ssot__FullName__c`, `ssot__Username__c`
Join key: `AiAgentGenerativeAiUsage_std__dlm.UserId__c = ssot__User__dlm.ssot__Id__c`.

The canonical logic these steps materialize lives in `queries/03-usage-normalized.sql` (and is the
same expression the deployed CI encodes).

---

## Step 0 — Prerequisites (verify once)

1. **Setup → Data Cloud → Data Cloud Settings**: confirm *Data Cloud Reports* is enabled.
2. Confirm the **User** data stream is active so `ssot__User__dlm` is populated (else names are raw `005…` Ids).
3. You need the **Data Cloud** permission set license + *Create and Customize Reports* / *Report Builder*.
4. Confirm `UserId__c` and `ssot__Id__c` are the **same data type** (Text) — a mismatch silently breaks the join.

## Step 1 — Create the Batch Data Transform

1. **Data Cloud app → Data Transforms tab** (if hidden: **More** → Data Transforms) → **New**.
2. Select **Batch Data Transform** → **Next**.
3. Source type **Data Model Objects** → pick your Data Space (a DMO transform is locked to one space).
4. **Add Input Data**: add `AiAgentGenerativeAiUsage_std__dlm` (select the fields above) and
   `ssot__User__dlm` (select `ssot__Id__c`, `ssot__FullName__c`, `ssot__Username__c`).
5. Add a **Join node** between the two inputs (hover the connector → Add Node → Join):
   - Join type **Inner Join**. ⚠️ The builder auto-arranges **User on the LEFT, Usage on the right**,
     so a *Left Join* would keep every User (mostly zero-usage) and bloat the report. **Inner Join
     is correct here**: symmetric, keeps only users with real AI usage, and matches the deployed CI's
     `JOIN` exactly → the native report shows the same numbers as the LWC cockpit.
   - Note: Inner Join **drops NULL-`UserId__c` rows** (the *Untagged/Flows* usage, which has no user by
     definition). That's fine for a per-user report; the SQL query pack (Tier 1) still surfaces Untagged.
   - Join key auto-detected: `User Id (ssot__Id__c) = User ID (UserId__c)`. Leave the right-column API
     prefix as-is.

## Step 2 — Normalize (optional Formula node) + write to a new custom DMO

1. Optional **Formula / Transform node** to reproduce `queries/03` normalization:
   - `feature_normalized` = `CASE WHEN GenAiGatewayFeatureName__c IS NULL THEN 'Untagged' ELSE GenAiGatewayFeatureName__c END` (only NULL is relabelled — each feature stays distinct; do NOT merge `EmployeeAssistant` into `AgentforceCoworker`)
   - `usage_day` = `date_trunc('day', Timestamp__c)`
   - `estimated_fc` = `(UsageQuantity__c * 20) + CEILING(PromptTotalTokenCount__c / 2000.0) * 4`
     (Feb-2026 rate card; **estimate only — Digital Wallet is billing source of truth**).
   (You can also aggregate here, or leave detail rows and aggregate in the report.)
2. Add an **Output node → Create New** DMO. **Create the DMO from this Output node** — a DMO created
   from the Data Model tab will NOT be selectable here. Name it e.g. `AI_Usage_Report__dlm`, map the
   fields, set a **primary key** + FQK.
3. **Save** the transform (name it, e.g. "AI Usage — User Join").
4. **Run Now** (Data Transforms tab → triangle next to the transform → Run Now). Then **Schedule**
   (day/hour interval) — choose **incremental** to bill only changed rows.

## Step 3 — Verify the custom DMO is populated (the reference org) — VERIFIED 2026-07-09

The Output node created DMO **`AI_Usage_report__dlm`** (note the lowercase `report`). User fields keep
their plain names (`FullName__c`, `Username__c`, `Department__c`, `Title__c`, `ManagerId__c`…); the
usage fields are **prefixed `AIA_`** (`AIA_PromptTotalTokenCount__c`, `AIA_GenAiGatewayFeatureName__c`,
`AIA_UsageQuantity__c`, `AIA_IsMeteredIndicator__c`, `AIA_Timestamp__c`, `AIA_UserId__c`). Rows are
**detail-level** (one per usage interaction). Primary key = `AIA_Id__c` (the usage-row Id).

```apex
ConnectApi.CdpQueryInput qi = new ConnectApi.CdpQueryInput();
qi.sql = 'SELECT FullName__c, AIA_GenAiGatewayFeatureName__c, COUNT(*), SUM(AIA_PromptTotalTokenCount__c) '
       + 'FROM AI_Usage_report__dlm GROUP BY FullName__c, AIA_GenAiGatewayFeatureName__c ORDER BY 4 DESC';
ConnectApi.CdpQueryOutputV2 out = ConnectApi.CdpQuery.queryANSISQLV2(qi);
System.debug('GROUPS=' + (out.data == null ? 0 : out.data.size()));
```
**Result:** the custom DMO returns detail rows per user × feature, and the aggregate token
totals match the cockpit. Feature groups include the **Untagged** bucket (NULL feature).

> **Inner-join nuance confirmed:** the inner join drops rows with a NULL **user**, NOT rows with a NULL
> **feature**. Since all the reference org usage is attributed to a user, the Untagged (NULL-feature) bucket survives —
> so this DMO carries both the user names AND the Untagged usage. Best of both.

## Step 4 — Deploy the native Report(s) — NOW DEPLOYABLE METADATA (verified 2026-07-09)

**Upgrade:** the reports are no longer clickops. Once the custom DMO exists, the platform auto-generates
its report type (`CustomEntity$AI_Usage_Report__dlm`, capital-R — verified via
`GET /services/data/v64.0/analytics/reportTypes`), so the reports ship as `force-app` metadata:

```bash
sf project deploy start -d force-app/main/default/reports --target-org <alias>
```

Three reports land in an **"AI Usage Governance"** folder (`force-app/main/default/reports/`):

| Report (metadata file) | Grouping | Summaries | Mirrors |
|---|---|---|---|
| **AI Usage per User** (`AI_Usage_per_User`) | User Name → Feature | Σ total/input/completion tokens, Σ actions, Record Count | `01-genai-usage-per-user.sql` |
| **Est. Flex Credits per User** (`AI_Usage_Est_Flex_Credits_per_User`) | User Name → Is Metered | Σ actions, Σ tokens | `02-flex-credits-per-user.sql` |
| **AI Usage over Time** (`AI_Usage_over_Time`) | Timestamp (by Day) → Feature | Σ tokens, Σ actions | `03-usage-normalized.sql` |

Column API names (from the report type describe): user fields plain (`FullName__c`, `Username__c`,
`Department__c`, `Title__c`); usage fields `AIA_`-prefixed (`AIA_PromptTotalTokenCount__c`,
`AIA_PromptInputTokenCount__c`, `AIA_PromptCompletionTokenCount__c`, `AIA_UsageQuantity__c`,
`AIA_IsMeteredIndicator__c`, `AIA_GenAiGatewayFeatureName__c`, `AIA_Timestamp__c`). Reports carry a
`INTERVAL_CUSTOM` time-frame filter on `AIA_Timestamp__c`. Because the DMO is materialized, these support
**detail rows, formulas, and metric tiles** (unlike a CI report).

> **Report-XML gotchas learned on the reference org (for reuse):** custom summary-formula `datatype` rejects both
> `double` and `Number` (dropped it — column `<aggregateTypes>Sum</aggregateTypes>` already gives
> subtotals + grand total); chart summaries need `<chartSummaries>` with an explicit `<aggregate>Sum</aggregate>`
> (not `summaryColumn`); `legendPosition` is invalid on a single-series bar (omit it).

**Verified live (the reference org, 2026-07-09):** ran `AI Usage per User` via the Analytics API — grand total
the grand total (input + completion tokens, record count, and actions), grouped by user → matches the cockpit exactly.

## Step 5 — Deploy the Dashboard — NOW DEPLOYABLE METADATA (verified 2026-07-09)

The dashboard is also `force-app` metadata (`dashboards/AI_Usage_Governance/AI_Usage_Adoption`):

```bash
sf project deploy start -d force-app/main/default/dashboards --target-org <alias>
```

Grid layout (12-col), "AI Usage — Adoption", sourced from the 3 reports above:
1. **3 KPI metric tiles** — Total Tokens, Total Actions, Interactions.
2. **Line chart** (full width) — tokens over time.
3. **Bar** — tokens by user; **Bar** — actions by user (metered split).
Dashboard **description** carries the disclaimer: *"Estimated Flex Credits — Digital Wallet is the billing
source of truth. Refreshes on the Data Transform schedule."*

> **Dashboard-XML gotchas learned on the reference org (for reuse):** grid wrapper is `<dashboardGridLayout>` (NOT
> `gridLayout`) and each cell's inner element is `<dashboardComponent>` (NOT `dashboardGridComponent`);
> horizontal bars use `componentType`=`Bar` (not `HorizontalBar`, which is report-only); Metric/Gauge/Table
> components require `indicatorLowColor`/`indicatorMiddleColor`/`indicatorHighColor`; `titleSize` must be in
> {8,9,10,12,14,18,24,36}. Best way to learn the schema: retrieve an existing grid dashboard from the org.

## Step 6 — Access & handoff

- Share the report folder + dashboard with the target profile/permset (read).
- For the client demo: run the transform once live so the report numbers match the cockpit.

## Cost & limits to know (Trust — don't overpromise)

- **This is recurring compute.** The Batch Data Transform bills on `max(rows read, rows written)`,
  ~**400 credits / 1M rows** (order-of-magnitude, third-party rate card; ~25× a batch CI per row) —
  light at demo volume, real at scale. Incremental runs + lower frequency cut it. Digital Wallet tracks it.
- **Redundancy with the CI:** the deployed CI already performs this exact join and materializes
  `user_name`. This path exists only because a CI report is summary-only. Don't run both unless you
  need both the LWC (2a) and the full native dashboard (2b).
- Native Data 360 report limits: 2,000 rows in run mode; export ≤ 50,000 rows / 100 MB; no joined
  reports, no cross filters, no inline edit.
- **i18n (FR demos):** Data Cloud report columns are **not translated** — plan labels accordingly.
- **Only the transform + its custom DMO are clickops** (Data-Kit-packageable only, not clean `sfdx`
  retrieve) → for those two, this runbook IS the transferable artifact. **The 3 reports and the dashboard
  ARE clean `force-app` metadata** (`reports/` + `dashboards/`) and redeploy in one `sf project deploy`
  once the custom DMO exists on the target org. Verified live on the reference org 2026-07-09.
