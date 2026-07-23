# Option 1 — On-demand queries (no recurring cost)

> **The lightest option.** You run a query whenever you want an answer; nothing runs in the
> background, so there is **no recurring cost** — you only pay per run.
> **Prerequisite:** [the User data stream must be activated](01-Prerequisite-Data-Stream-User.md).

## What you get

Three ready-to-use queries to paste into the Query Editor:

| Query | What it answers | File |
|---|---|---|
| **1 — Usage per user** | Who uses which feature, and at what token volume | [`queries/01-usage-per-user.sql`](queries/01-usage-per-user.sql) |
| **2 — Estimated Flex Credits** | The credit estimate per user × feature | [`queries/02-flex-credits-per-user.sql`](queries/02-flex-credits-per-user.sql) |
| **3 — Normalized view** | The clean view, with a per-day axis for trends | [`queries/03-normalized-usage.sql`](queries/03-normalized-usage.sql) |

## Steps

1. Open the **Data Cloud** app → **Query Editor** tab.
2. Open one of the three `.sql` files above and **copy its entire content**.
3. **Paste it** into the Query Editor.
4. Click **Run**.
5. Read the results directly in the grid, or export them (grid export button).

## How to read the results

- **`feature`** — the AI product that generated the usage. Each value is a distinct product
  (e.g. `EmployeeAssistant`, `AgentforceCoworker`). `Untagged` = usage with no label (Flows, custom
  components); it is real consumption, worth watching.
- **`is_metered`** — `true` = billed usage; `false` = usage included in the license.
- **`nb_roundtrips`** — the number of user questions (question/answer exchanges). This is the billing
  unit for Agentforce Coworker.
- **`est_fc_total`** — the **estimate** of Flex Credits. See the reminder below.

## Tips

- **Isolate Agentforce Coworker:** add `WHERE a."GenAiGatewayFeatureName__c" = 'AgentforceCoworker'`
  before the `GROUP BY`.
- **Change the period:** add a date filter, e.g.
  `WHERE a."Timestamp__c" >= '2026-01-01T00:00:00Z'`.
- **See more rows:** increase the `LIMIT` value at the bottom of the query.

> ⚠️ **Important reminder.** The credit columns (`est_fc_...`) are **estimates** based on the published
> rate card. The **Digital Wallet** (**Setup → Digital Wallet**) remains the **billing source of
> truth**. Use these queries to steer **adoption**, not to verify an invoice.

---

**Want a dashboard that refreshes on its own?** Move to
[Option 2 — Report & Dashboard](03-Option-2-Report-and-Dashboard.md).
