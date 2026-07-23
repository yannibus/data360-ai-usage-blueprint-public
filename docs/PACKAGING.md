# PACKAGING — what ships as metadata vs what is clickops

This blueprint is **mostly deployable `force-app` metadata**, with two Data Cloud artefacts that
can only be reproduced by hand (or shipped in a Data Kit). This file is the honest inventory:
what redeploys with `sf project deploy start`, what a human must build in the Data Cloud UI, and
why.

---

## 1. Deployable metadata (`sf project deploy start`)

Everything under `force-app/main/default/` deploys cleanly to any org that meets the
prerequisites in `docs/SETUP.md`.

| Component | Type | Tier | Notes |
|---|---|---|---|
| `AI_Usage_By_User` | `MktCalcInsightObjectDef` | 2a | The Calculated Insight definition. Must **run once** post-deploy to materialize. Grouped at **interaction grain** so Coworker bills at 72 FC/round-trip (see Coworker caveat below). |
| `AiUsageCockpitController` | `ApexClass` | 2a | Reads the CI via `ConnectApi.CdpQuery.queryANSISQLV2` — no callout, no Named Credential. |
| `aiUsageCockpit` | `LightningComponentBundle` | 2a | Cockpit LWC — hand-built SVG charts, brand-2026 styling, all strings via Custom Labels. |
| `CustomLabels` (28 `AI_Cockpit_*`) | `CustomLabels` | 2a | Source EN. Every user-facing string in the LWC. |
| `fr.translation-meta.xml` | `Translations` | 2a | French for all 28 labels + the app + the tab. Activates automatically for FR users. |
| `AI_Usage_Cockpit_Page` | `FlexiPage` | 2a | AppPage hosting the cockpit. |
| `AI_Usage_Cockpit_Page` | `CustomTab` | 2a | Tab pointing at the FlexiPage. |
| `AI_Usage_Governance` | `CustomApplication` | 2a | Lightning app bundling the tab. |
| `AI_Usage_Cockpit_User` | `PermissionSet` | 2a | Grants Apex + tab access. Assign post-deploy. |
| `AI_Usage_per_User` | `Report` | 2b | On report type `CustomEntity$AI_Usage_Report__dlm`. |
| `AI_Usage_Est_Flex_Credits_per_User` | `Report` | 2b | Estimated Flex Credits per user. |
| `AI_Usage_over_Time` | `Report` | 2b | Daily usage trend. |
| `AI_Usage_Governance` (reports folder) | `ReportFolder` | 2b | |
| `AI_Usage_Adoption` | `Dashboard` | 2b | Grid dashboard: 3 KPI tiles + line + 2 bars. |
| `AI_Usage_Governance` (dashboards folder) | `DashboardFolder` | 2b | |

**Tier 2b caveat:** the 3 reports + dashboard reference the report type
`CustomEntity$AI_Usage_Report__dlm`, which the platform **auto-generates only after** the custom
DMO `AI_Usage_report__dlm` exists (built via the clickops transform below; the DMO name is
lowercase `report`, the auto-generated report type is capital `R`). So deploy the report layer
**after** the DMO is created, or the deploy fails on a missing report type.

**Coworker 72 FC/round-trip caveat (Tier 2a):** the CI definition groups at interaction grain so
Agentforce Coworker is metered at its real rate (72 FC per distinct `AiAgentInteractionId__c`) on a
**fresh deploy**. On an org where this CI was **already published at a coarser grain**, the platform
refuses to add the interaction dimension ("not an eligible KQ dimension"), so that org keeps the
per-token estimate for Coworker in the cockpit — the exact figure then comes from the Tier 1 SQL
(`queries/02`). CI-engine limits also apply: no `CEILING` (per-token estimate is un-rounded in the
CI, a few-FC difference vs the SQL) and no `COUNT(DISTINCT)` as a measure (hence the interaction
grain rather than a distinct count). The new-org grain was reasoned from live PATCH rejections on
the reference org; validate on the first fresh deploy.

Also under `queries/` (not metadata, but part of the package): the 3 Tier-1 SQL files
(`01`, `02`, `03`) — copy/paste into the Data Cloud Query Editor.

---

## 2. Clickops — must be built in the Data Cloud UI

These cannot be retrieved as clean `sfdx` source. They are only packageable via a **Data Cloud
Data Kit**, or reproduced by hand from the runbook.

| Artefact | Tier | Why it can't ship as metadata | How to reproduce |
|---|---|---|---|
| **Data Stream User** activation | prereq | Connector config, org-specific, not source-trackable | `docs/SETUP.md` §1.1 (check the `User` object on the CRM data stream) |
| **Batch Data Transform** (`AiAgentGenerativeAiUsage` × `ssot__User__dlm`) | 2b | Data Cloud transform — Data-Kit-only | `docs/tier1-report-dashboard-runbook.md` |
| **Custom DMO** `AI_Usage_report__dlm` (transform output; lowercase `report`) | 2b | Transform-type DMO, created from the Output node | same runbook |

> The **CI materialization run** and the **transform schedule** are runtime actions, not
> artefacts — trigger them post-deploy from the Data Cloud UI (or their schedule).

---

## 3. Recommended install order

1. **Prerequisites** — Data Cloud provisioned, GenAI usage present, **Data Stream User active**
   (`docs/SETUP.md` §1).
2. **Deploy Tier 2a** — `sf project deploy start` (CI + Apex + LWC + labels + FR + app/tab/permset).
   Run the CI once; assign the permission set.
3. **(Optional) Tier 2b** — build the transform + custom DMO (clickops), run it, **then** deploy
   `reports/` + `dashboards/`.
4. **Tier 1** needs nothing installed — the SQL runs in the Query Editor at any time.

Deploying `reports/`+`dashboards/` before the custom DMO exists is the one ordering trap — the
auto-generated report type won't be there yet.

---

## 4. Data Kit packaging (optional, for full-fidelity transfer)

The Batch Data Transform and its transform-output DMO (`AI_Usage_report__dlm`) have **no standalone
metadata type** — they cannot be retrieved as clean `sfdx` source (verified on the reference org: the org exposes
`MktCalcInsightObjectDef` and `DataPackageKitDefinition`, but no deployable `DataTransform` /
`MktDataModelObject` type). A **Data Cloud Data Kit** is the supported way to move them between orgs.
The `force-app` metadata (CI, Apex, LWC, labels, reports, dashboard) still deploys separately via
`sf project deploy start`. For most demos the `force-app` deploy + the §2 clickops runbook is enough
and lighter than maintaining a Data Kit; build the kit only when you need repeatable full-fidelity
transfer to another org.

> **⚠️ Coworker grain caveat — read before adding the CI to the kit.** A Data Kit captures a
> **snapshot of the *currently published* CI definition** at packaging time (no live link). On the reference org
> the live CI is still the **per-token, coarse-grain** version (the platform refused the interaction
> dimension on an already-published CI — see §1). So a kit built on the reference org ships the **per-token
> Coworker model**, *not* the corrected 72 FC/round-trip interaction-grain model. To get the correct
> model on a fresh org, deploy the CI from **`force-app`** (`mktCalcInsightObjectDefs/AI_Usage_By_User`)
> — which is at interaction grain — and let the kit carry only the transform + DMO, **or** deploy the
> force-app CI *after* the kit and let it overwrite the kit's CI. Do not rely on the kit's CI for the
> round-trip billing.

### 4.1 Prerequisites

- **Data Cloud / Data 360 provisioned** on both source and target org — not available in
  scratch orgs or Trailhead Playgrounds.
- **Data Cloud Architect** permission set on the building/installing user.
- A **data space** pre-created on the target org.
- **You cannot install a kit in the org that created it** — testing the install needs a *second*
  Data-Cloud-enabled org. The install/test step below is documented but **not yet executed** —
  run it when a second Data-Cloud org is available.

### 4.2 Build the kit (clickops on the source org)

Data Kit authoring is **UI-only** (no `sf` verb creates or populates a kit; the CLI only
retrieves/deploys an already-built kit's manifest).

1. **Setup → Data Cloud Setup → Quick Find "Data Kits" → New.** Name it `AI_Usage_Governance_Kit`,
   add a description, **Save**.
2. Choose the **Data Kit Type**: **DevOps** for same-customer sandbox→prod (manifest + `sf deploy`),
   or **Standard** if you will wrap it in a 2GP managed package for cross-org/ISV distribution.
3. **Add components**, in dependency order (this order is what the *Publishing Sequence* tab expects):
   1. the custom DMO **`AI_Usage_report__dlm`** (Data Model section),
   2. the **Batch Data Transform** that writes to it (Data Transform section),
   3. the **Calculated Insight `AI_Usage_By_User`** (Calculated Insight section) — see the grain
      caveat above; you are shipping the reference org's *per-token* CI snapshot.
4. Open the auto-generated **Publishing Sequence** tab and confirm the order is DMO → Transform → CI
   (a CI hard-fails to deploy if its source objects aren't present first).

### 4.3 Distribute + install on a target org

**DevOps path (same customer, recommended for demos):**
1. **Developer Tools → Data Kits → Download Manifest** (`package.xml`) on the reference org.
2. `sf project retrieve start --manifest package.xml --target-org <alias>` (pulls the kit source).
3. `sf project deploy start --manifest package.xml --target-org <target>` (or attach to a Change Set).

**Managed-package path (cross-customer / ISV):** `sf package create -t Managed` → `sf package
version create` → `sf package version promote` → install the promoted `04t` version on the target
via its install URL ("Install for Admins Only"). Data 360 metadata must live in **its own package**
(cannot mix with the LWC/Apex/report metadata — those stay in the `force-app` deploy).

**Post-install on the target (clickops):** the kit *installs* the definitions but you must **deploy
the components**: Data Cloud → Calculated Insights → New → **"Create from a Data Kit"** → Deploy;
same for the Data Transform. Then **deploy the `force-app` CI on top** to restore the correct
round-trip grain (see caveat), assign the perm set, and run the transform + CI once.

### 4.4 Re-publishing after a source change

There is **no in-place push-update** for these component types (the UI "Update" flow is
CRM-data-stream-only). To ship a change: re-open the kit → Update → cut a **new package version**
(managed path) or re-download the manifest and redeploy (DevOps path) → reinstall/redeploy on the
target.

> **Sources:** Salesforce Developer docs *Packages and Data Kits* / *Deploy a Data Kit Using the
> CLI* / *Deploy Data Kit Components*; Metadata API *Data Cloud Metadata Types*
> (`DataPackageKitDefinition`); Trailhead *Create and Package a Data Kit* / *Create and Install a
> Data Kit*. Verified against the reference org's `sf org list metadata-types` (2026-07-10).

---

## 5. Component count summary

- **Deployable metadata:** 15 components (1 CI, 1 Apex, 1 LWC, 1 CustomLabels set, 1 Translations,
  1 FlexiPage, 1 Tab, 1 App, 1 PermSet, 3 Reports, 2 report/dashboard folders, 1 Dashboard).
- **Clickops:** 3 (Data Stream User activation, Batch Data Transform, custom DMO).
- **SQL query pack:** 3 files (Tier 1, copy/paste).
- **Optional Data Kit** (§4): packages the Transform + DMO (+ optionally the CI snapshot) for
  full-fidelity cross-org transfer — clickops build, install requires a second Data-Cloud org.
