# Option 2 — Native Report & Dashboard (low recurring cost)

> **A native Salesforce Report and Dashboard, per named user, that refresh automatically and can be
> shared with your team.**
> This option materializes the data in the background → **low recurring compute cost**.
> **Prerequisite:** [the User data stream must be activated](01-Prerequisite-Data-Stream-User.md).

## Why these steps (the principle)

The AI usage data and the user names live in **two separate objects** in Data Cloud. A native report
cannot relate them directly. So you first **merge the two into a single object** — that is the job of
the **Data Transform** below. Once that new object exists, you build a classic report and dashboard on
top of it.

The flow: **Data Transform → new object → Report → Dashboard.**

---

## Step 1 — Create the Data Transform (the merge)

1. Open the **Data Cloud** app → **Data Transforms** tab (if hidden: **More** menu).
2. Click **New** → **Batch Data Transform** → **Next**.
3. **Source type: Data Model Objects.** Choose your **Data Space**.
4. **Add two input sources:**
   - **`AiAgentGenerativeAiUsage_std__dlm`** (the AI usage data) — select the fields:
     `GenAiGatewayFeatureName__c`, `PromptTotalTokenCount__c`, `PromptInputTokenCount__c`,
     `PromptCompletionTokenCount__c`, `UsageQuantity__c`, `IsMeteredIndicator__c`, `Timestamp__c`,
     `UserId__c`, `AiAgentInteractionId__c`.
   - **`ssot__User__dlm`** (the users) — select `ssot__Id__c`, `ssot__FullName__c`,
     `ssot__Username__c`.
5. **Add a Join node** between the two (hover the connector → **Add Node → Join**):
   - **Type: Inner Join.**
   - **Join key:** `User Id (ssot__Id__c) = User ID (UserId__c)` (usually auto-detected).
   - *Why Inner Join:* it keeps only the users who have real AI usage (not the zero-usage
     accounts), which gives a readable report and correct figures.

## Step 2 — Write the result to a new object

1. *(Optional)* Add a **Formula node** to prepare ready-to-use columns, e.g.:
   - `feature` = `CASE WHEN GenAiGatewayFeatureName__c IS NULL THEN 'Untagged' ELSE GenAiGatewayFeatureName__c END`
   - `day` = `date_trunc('day', Timestamp__c)`
2. Add an **Output node → Create New**. **Create the new object from this Output node** (an object
   created elsewhere will not be selectable here). Name it e.g. **`AI_Usage_Report`**, map the fields,
   and set a **primary key**.
3. **Save** the transform (give it a name, e.g. "AI Usage — User Join").
4. Click **Run Now** for an initial load, then set a **Schedule** (daily is usually enough; choose
   **incremental** to only bill changed rows).

## Step 3 — Verify the new object is populated

1. Open the **Query Editor** and run (adjust the name if you chose a different one):

   ```sql
   SELECT COUNT(*) FROM AI_Usage_Report__dlm;
   ```

2. The result must be **greater than 0**. Otherwise, recheck that the transform ran (Step 2.4).

## Step 4 — Create the Report

1. Go to **Reports** → **New Report**.
2. In the type selector, choose the **Data 360** category → select your new object (`AI_Usage_Report`).
3. Build the report:
   - **Group by** *User name*, then by *Feature*.
   - **Add columns:** total tokens, number of actions, number of round-trips.
   - **Add sums** (Sum) on the numeric columns to get subtotals and the grand total.
   - *(Optional)* A second report grouped by *Date (by day)* for the time trend, and a third by
     *Billed / Included*.
4. **Save** the report(s) in a dedicated folder (e.g. "AI Usage Governance").

## Step 5 — Create the Dashboard

1. Go to **Dashboards** → **New Dashboard**.
2. Add components based on the report(s) from Step 4, for example:
   - **3 metric tiles (Metric):** total tokens, total actions, total round-trips.
   - **A line chart (Line):** usage over time.
   - **A bar chart (Bar):** usage per user.
3. In the dashboard **description**, add the reminder:
   *"Estimated Flex Credits — the Digital Wallet remains the billing source of truth.
   Refreshed on the Data Transform schedule."*
4. **Save** and **share** the report folder + the dashboard with the relevant profiles (read access).

---

## Cost & things to watch

- This option relies on a **scheduled refresh** (the Data Transform) → **recurring compute**, light at
  normal volume. **Refreshing less often** and **incrementally** reduces the cost.
- The **Digital Wallet** (**Setup → Digital Wallet**) tracks real compute and remains the **billing
  source of truth**.
- Native Data 360 report limits to know: ~2,000 rows in run mode; export ≤ 50,000 rows; no joined
  reports.

> ⚠️ **Reminder.** The credits shown are **estimates** for adoption steering, not your invoice. Always
> reconcile with the Digital Wallet.

---

**Only need quick summary charts?** [Option 1](02-Option-1-On-Demand-Queries.md) (on-demand queries)
may be enough, at zero cost.
