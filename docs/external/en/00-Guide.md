# AI Usage Visibility — Administrator Guide

> **Who it's for:** Salesforce administrators who want visibility into **who uses Agentforce /
> GenAI, how much, and the estimated cost**. Everything is done **manually in the Salesforce UI** —
> no code, no command line, no package to install.

This guide is the entry point. It presents **two options** and points you to a detailed step-by-step
for each. A French version is available in the `../fr/` folder.

---

## ⚠️ Read this first — it's an estimate, not your invoice

This solution reads Salesforce's **standard AI usage telemetry** and turns it into readable reports
and **Flex Credit estimates**. It is an **adoption-visibility and steering tool**.

> **The Digital Wallet remains the single source of truth for billing.** The Flex Credit amounts
> shown here are *estimates* based on the current published rate card. Part of your consumption (for
> example data ingested via connectors) appears **only** in the Digital Wallet and is not covered here.
> Always reconcile with **Setup → Digital Wallet** before any budget or contractual decision.

---

## The two options

Two ways to get this visibility, from lightest to richest. **You don't need both** — pick the one
that matches the frequency you need and the investment you want to make.

| Option | What you get | Recurring cost | Effort | Step-by-step |
|---|---|---|---|---|
| **1 — On-demand queries** | Answers on demand in the Query Editor | **None** — you only pay per run | Lowest | [`02-Option-1-On-Demand-Queries.md`](02-Option-1-On-Demand-Queries.md) |
| **2 — Report & Dashboard** | A native Report + Dashboard, per user, refreshed | **Low, recurring** (compute) | Medium | [`03-Option-2-Report-and-Dashboard.md`](03-Option-2-Report-and-Dashboard.md) |

> **Our recommendation:** start with **Option 1** to explore the data at zero recurring cost. Move to
> **Option 2** when you want a dashboard that refreshes automatically and can be shared with your team.

---

## Where to start

1. **Prerequisite (one time)** — activate the User data stream so user names resolve:
   [`01-Prerequisite-Data-Stream-User.md`](01-Prerequisite-Data-Stream-User.md).
2. **Option 1** — on-demand queries: [`02-Option-1-On-Demand-Queries.md`](02-Option-1-On-Demand-Queries.md).
3. **Option 2** — report & dashboard: [`03-Option-2-Report-and-Dashboard.md`](03-Option-2-Report-and-Dashboard.md).

---

## Understanding the cost

- **Option 1** has **no recurring cost** — you are only billed for each query you run.
- **Option 2** uses **background compute** (a scheduled data refresh), which consumes a small amount of
  credits continuously — light at normal volume. You can reduce it by refreshing **less often** and
  using **incremental** refreshes.
- All compute is tracked, and all real billing lives, in the **Digital Wallet** (**Setup → Digital
  Wallet**). Check it for actual consumption.

> **Reminder:** the credit figures in the reports are **estimates** to help you plan. They do **not
> replace** the Digital Wallet, which is the authoritative record of what you are billed.

> **💡 A free extra view, straight from the Digital Wallet.** The Wallet also offers a built-in
> **"Usage by User ID"** report — no setup, no recurring cost ([Salesforce
> Help](https://help.salesforce.com/s/articleView?id=xcloud.wallet_custom_report_userid.htm&language=en_US&type=5)). It's handy as a
> quick cross-check, with **two things to keep in mind**: it shows a user **ID, not a readable name**,
> and the User ID is filled in **only for Employee Agent activity** (standard and custom agent actions)
> — usage from Service Agents, guests, external users or automations shows up without a user. So it's a
> useful complement, but **not a complete by-user picture** — that's what Options 1 and 2 give you.

---

## A note on Agentforce Coworker

If your org uses **Agentforce Coworker**, its usage is estimated **per conversation round-trip** (one
user question and its answer), which reflects how it is priced — rather than purely by text volume.
The queries and reports handle this for you; there is nothing to compute yourself. As always, the
**Digital Wallet** is the number to trust for billing.

---

## Quick reference

| You want to… | Use | Recurring cost |
|---|---|---|
| Check a figure occasionally | **Option 1** — Query Editor | None |
| Share a refreshed dashboard | **Option 2** — Report & Dashboard | Low |
| Know what you are actually billed | **Digital Wallet** (Setup) | — |

*Estimates use the current published rate card and may change. Always confirm with the Digital Wallet.*
