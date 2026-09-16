# Data360 — AI Usage Blueprint

Monitor **Agentforce / GenAI usage per user** on standard Salesforce **Data Cloud (Data 360)** telemetry. Reproducible, shareable, 100% Trust-compliant — built entirely on real standard data models, nothing fabricated.

> Turn the question *"who uses our AI, how much, and what does it cost?"* into a deployable answer, on any org that has Agentforce + Data Cloud.

---

## Two adoption tiers (pick one, or both)

The blueprint is split into **two decoupled tiers** so a client is never forced into recurring Data Cloud credit cost.

> **Platform truth up front (Trust) — it's ID vs *name*:** the raw AI-telemetry DMO carries only a raw `UserId`, never a name. Two distinct realities follow:
>
> - **By User *ID*, natively, zero recurring cost:** the **Digital Wallet** ships a standard *"Usage by User ID"* report on the `TenantEnrichedUsageEvent` DLO — no SQL, no materialization. But **`User ID` populates only for Employee Agent events** (`Agentforce_StandardAction`, `Agentforce_CustomAction`) — not Service Agents, guests, external, or automation — so it's a partial by-user view, and it shows an ID, not a readable name. Treat it as a complementary third path, orthogonal to the two tiers below.
> - **By readable *name*:** getting the user *name* onto a native report still requires *materializing* the join first — recurring compute. So the only way to see **names** at **zero recurring cost** is the SQL Query Editor (Tier 1). That reality shapes the two tiers below.

### Tier 1 — SQL pay-per-look · *truly zero recurring cost*
The 3 monitoring SQL queries, run in the Data Cloud **Query Editor**. The join to the User DMO happens **inside the SQL** (the query engine joins DMOs freely), so **names resolve on demand**.
- **Nothing materialized → no scheduled credit consumption.** You spend only when you run a query.
- The genuinely lightweight, reversible entry point.
- **Adopt this if** you want visibility fast, cheap, and reversible.

### Tier 2 — Materialized restitution · *opt-in, recurring compute*
The join is **materialized** so it can drive visual, native restitution. Two independent variants:

**2a — LWC cockpit on a Calculated Insight** (the "wow"). `AI_Usage_By_User__cio` pre-aggregates + normalizes; the **LWC cockpit** (`aiUsageCockpit`) renders KPI cards, usage-over-time, feature breakdown, top users, billable vs included. Recurring CI compute; LWC wired **exclusively** on the CI.

**2b — Native Report + Dashboard on a custom DMO.** A **Batch Data Transform** joins the telemetry DMO × User DMO and writes a **custom DMO**, which is fully reportable — so you get a native, admin-owned **Report & Dashboard** (KPI tiles, detail rows, formulas) with no LWC. Recurring transform compute. **Only the transform + custom DMO are clickops**; the 3 reports and the grid dashboard on top are **deployable `force-app` metadata** (`reports/` + `dashboards/`), so once the DMO exists they redeploy to any org in one `sf project deploy`.

> **2a vs 2b:** the CI (2a) is also reportable, but a report on a CI is *summary-only* (no metric/gauge/table dashboard tiles, no detail rows). Use **2b's custom DMO** when you need the full native dashboard; use **2a** for the polished LWC. They're independent — pick either, both, or neither.

> **The tiers are independent.** Tier 1 (SQL) works even if nothing is ever materialized. Start with Tier 1; add Tier 2a and/or 2b when the value is proven.

---

## What's in the box

| Path | Tier | Nature |
|---|---|---|
| `queries/01-genai-usage-per-user.sql` | 1 | Tokens per user × feature |
| `queries/02-flex-credits-per-user.sql` | 1 | Estimated Flex Credits + metered split |
| `queries/03-usage-normalized.sql` | 1 | Clean view (distinct features kept apart + NULL→Untagged + day axis) |
| `force-app/.../AI_Usage_By_User` (Calculated Insight) | 2a | Deployable metadata, Data-Kit-packageable |
| `force-app/.../lwc/aiUsageCockpit` | 2a | LWC cockpit |
| `force-app/.../classes/AiUsageCockpitController` | 2a | Apex → Data Cloud Query API (`ConnectApi.CdpQuery`) |
| Batch Data Transform → custom DMO | 2b | **Clickops** — see `docs/SETUP.md` (Data-Kit-packageable only) |
| `force-app/.../reports/AI_Usage_Governance/*` (3 reports) | 2b | **Deployable metadata** — on the custom DMO's report type |
| `force-app/.../dashboards/AI_Usage_Governance/AI_Usage_Adoption` | 2b | **Deployable metadata** — grid dashboard (KPI tiles + charts) |

---

## Prerequisites (both tiers)

1. **Data Cloud provisioned** on the org (licenses `Data Cloud` / `Customer Data Platform`).
2. **Agentforce / GenAI usage happening** → the standard DMO `AiAgentGenerativeAiUsage_std__dlm` is auto-populated by the platform.
3. **Data Stream User activated** → creates `ssot__User__dlm` so usage rows carry readable names, not raw `005…` IDs. This is a **one-time UI step** (Data Cloud Setup → Salesforce CRM Connector → check `User`). Inactive by default. See `docs/SETUP.md`.

> ⚠️ **Flex Credit numbers are estimates.** The **Digital Wallet remains the billing source of truth**. This blueprint pilots *AI adoption per user*; the Wallet pilots *global billing*. Data-connector consumption (SharePoint, ingestion) appears only in the Wallet. Flex Credit data exists since 2026-05-29 (no retro-history).
>
> 💡 **Complementary native path — Wallet "Usage by User ID".** For a zero-setup, zero-recurring-cost view *by User ID*, the Digital Wallet exposes a standard report on the `TenantEnrichedUsageEvent` DLO ([SF help: *Create a Report on Usage by User ID*](https://help.salesforce.com/s/articleView?id=xcloud.wallet_custom_report_userid.htm&language=en_US&type=5)). It shows an **ID, not a name**, and `User ID` **populates only for Employee Agent events** (`Agentforce_StandardAction` / `Agentforce_CustomAction`) — Service Agents, guests, external and automation are blank. Useful as a quick cross-check on billed usage; not a substitute for the per-name, per-feature view this blueprint delivers.

---

## Quick start

- **Tier 1 (SQL):** open Data Cloud → Query Editor → paste `queries/03-usage-normalized.sql` → run. Names resolve in-query, zero recurring cost.
- **Tier 2a (LWC cockpit):** `sf project deploy start --target-org <your-org>` → **(manual)** run/refresh the CI once in Data Cloud → Calculated Insights so it materializes → assign the permission set → drop `aiUsageCockpit` on a Lightning page.
- **Tier 2b (native report/dashboard):** verify `ssot__User__dlm` and `AiAgentGenerativeAiUsage_std__dlm` have rows, then **(manual)** build the Batch Data Transform + custom DMO per `docs/SETUP.md` (clickops), then `sf project deploy start -d force-app/main/default/reports -d force-app/main/default/dashboards --target-org <your-org>` to ship the 3 reports + the "AI Usage — Adoption" dashboard.

See `docs/SETUP.md` for the full reproduction guide (including recovery steps if a Calculated
Insight deploy gets stuck) and `docs/PACKAGING.md` for the metadata-vs-clickops breakdown.

---

## Disclaimer

This is an **unofficial, community-built reference asset** — not a Salesforce product, and not
officially supported by, or affiliated with, Salesforce. It is provided **as-is**, for educational
and demonstration purposes.

- **Flex Credit figures are planning estimates**, based on a **February 2026** rate card that may
  change. The **Digital Wallet in your own org is the only billing source of truth.** Do not use
  these estimates for contractual or financial commitments.
- Built entirely on **standard, documented Data Cloud data models** — nothing fabricated — but
  behavior, field names, and metering rules can evolve; **validate against your own org** before
  relying on any output.

---

*Reusable reference asset. Source language English; French translation shipped for user-facing labels.*
