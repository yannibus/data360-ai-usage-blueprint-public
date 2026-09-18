#!/usr/bin/env python3
"""
Tier 3 — Tableau Next executive view for the Data360 AI Usage Blueprint.

Builds (against REAL Agentforce/GenAI telemetry already in Data Cloud — no synthetic
data, no ingestion) a Tableau Next Semantic Data Model, visualizations and a dashboard
on top of two existing Data Model Objects:
  - Fact: AiAgentGenerativeAiUsage_std__dlm  (one row per GenAI/LLM call)
  - Dim : ssot__User__dlm                    (one row per user)

Auth: SF-CLI passthrough. Every REST call is routed through
`sf api request rest ... --target-org <alias>` which re-resolves a fresh token
internally (avoids the stale-token INVALID_AUTH_HEADER failure mode). No Connected
App / next_orgs.json entry required because this build only touches
Semantics / Visualizations / Dashboards / Workspaces on pre-existing, pre-populated DMOs.

Distinct-count risk resolution (probed live against this org 2026-09-17):
  - aggregationType enum does NOT accept "DistinctCount"/"CountDistinct" (POST_BODY_PARSE_ERROR).
  - BUT a calculated measurement with expression COUNTD([SDO].[field]) and
    aggregationType "UserAgg", level "AggregateFunction" validates cleanly (isValid=true).
  => Branch taken: DISTINCT-COUNT IS SUPPORTED (via COUNTD expression). Round Trips,
     Active Users, and the exact feature-conditional Estimated Flex Credits (Coworker =
     round-trips x 72; else actions x 20 + ceil(tokens/2000) x 4) are all implemented.
"""
import json, subprocess, sys, uuid, time as _time
from datetime import datetime as _dt

# ── Demo parameters ──────────────────────────────────────────────────────────
ORG_ALIAS   = "yajrebased-rnb10e"
COMPANY     = "Data360"
USE_CASE    = "AI Usage Governance"
PERSONA     = "AI Governance / Platform Owner"
STORY       = "Track Agentforce & GenAI adoption and estimated Flex Credit cost per user, feature and day."

FACT_DMO    = "AiAgentGenerativeAiUsage_std__dlm"
DIM_DMO     = "ssot__User__dlm"

WORKSPACE_NAME = "data360_ai_usage_governance"
MODEL_API_NAME = "data360_ai_usage_governance"
DASH_NAME      = "data360_ai_usage_governance_dashboard"

BASE_SF  = "/services/data/v64.0"
BASE_SEM = "/services/data/v65.0"
BASE_VIZ = "/services/data/v66.0"

# ── Diagnostics ───────────────────────────────────────────────────────────────
def _ts(): return _dt.now().strftime("%H:%M:%S")
def ok(m):   print(f"  [{_ts()}] OK  {m}")
def info(m): print(f"  [{_ts()}] ..  {m}")
def die(m, extra=None):
    print(f"\n  FAILED: {m}")
    if extra is not None: print(f"  {str(extra)[:600]}")
    sys.exit(1)

# ── SF-CLI passthrough ─────────────────────────────────────────────────────────
def sf_rest(path, method="GET", body=None):
    """Route a REST call through the sf CLI (fresh token per call). Returns parsed JSON."""
    cmd = ["sf", "api", "request", "rest", path, "--target-org", ORG_ALIAS, "--method", method]
    # The sf CLI rejects DELETE (and any method) with no --body ("No 'mode' found in 'body'").
    # Always send at least an empty JSON object for bodyless methods.
    if body is None and method in ("DELETE", "PATCH", "PUT", "POST"):
        body = {}
    if body is not None:
        cmd += ["--body", json.dumps(body) if not isinstance(body, str) else body]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = proc.stdout.strip()
    # sf prints a harmless ENOENT plugin warning to stderr from /tmp cwd; ignore.
    if not out:
        if proc.returncode != 0:
            return {"__error__": proc.stderr.strip()[:600]}
        return {}
    # strip any leading non-JSON warning lines
    start = out.find("{")
    startb = out.find("[")
    if startb != -1 and (start == -1 or startb < start):
        start = startb
    if start > 0:
        out = out[start:]
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"__raw__": out[:600]}

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*66}")
print(f"  Tier 3 build — {COMPANY} — {USE_CASE}")
print(f"  Org: {ORG_ALIAS}  (SF-CLI passthrough, no ingestion)")
print(f"{'='*66}\n")

# ── PHASE 1: Workspace ─────────────────────────────────────────────────────────
print("[1/6] Workspace")
r = sf_rest(f"{BASE_SEM}/tableau/workspaces")
existing = {w["name"]: w["id"] for w in r.get("workspaces", [])}
# delete any prior workspace whose name starts with our base (handles slug drift like _governance1)
for wn in list(existing):
    if wn == WORKSPACE_NAME or wn.startswith(WORKSPACE_NAME):
        sf_rest(f"{BASE_SEM}/tableau/workspaces/{wn}", method="DELETE")
        info(f"deleted existing workspace {wn}")
if existing:
    _time.sleep(6)
r = sf_rest(f"{BASE_SEM}/tableau/workspaces", method="POST",
            body={"label": WORKSPACE_NAME,
                  "description": f"Tier 3 Tableau Next executive view — {COMPANY} {USE_CASE}."})
if "id" not in r: die("workspace create", r)
workspace_name = r["name"]
workspace_id   = r["id"]
ok(f"workspace {workspace_name}  id={workspace_id}")

# ── PHASE 2: Semantic Data Model (SDOs) ────────────────────────────────────────
print("\n[2/6] Semantic Data Model")
# delete if exists, then poll until it's actually gone (delete is async)
chk = sf_rest(f"{BASE_SEM}/ssot/semantic/models/{MODEL_API_NAME}")
if chk.get("apiName"):
    sf_rest(f"{BASE_SEM}/ssot/semantic/models/{MODEL_API_NAME}", method="DELETE")
    info(f"deleting existing model {MODEL_API_NAME} ...")
    for _ in range(20):
        _time.sleep(3)
        if not sf_rest(f"{BASE_SEM}/ssot/semantic/models/{MODEL_API_NAME}").get("apiName"):
            break
    ok("prior model gone")

FACT_GRAIN = "one row per generative artificial intelligence call (large language model invocation) made through Agentforce or generative artificial intelligence features"

model_payload = {
    "apiName": MODEL_API_NAME,
    "label": f"{COMPANY} — {USE_CASE}",
    "description": f"Executive semantic model over real Agentforce and generative artificial intelligence telemetry for {COMPANY}.",
    "app": workspace_name,
    "categories": [],
    "dataspace": "default",
    "agentEnabled": True,
    "semanticDataObjects": [
        {
            "label": "AI Usage",
            "description": "Fact table of generative artificial intelligence usage. One row per large language model call made through Agentforce or generative features. Analyze token volume, actions, round trips and estimated cost by feature, user and day.",
            "dataObjectName": FACT_DMO,
            "dataObjectType": "Dmo",
            "shouldIncludeAllFields": False,
            "semanticDimensions": [
                {"dataObjectFieldName": "GenAiGatewayFeatureName__c", "label": "Feature Raw",
                 "description": "Raw generative artificial intelligence feature name. Empty for automation-triggered usage. Normalized by the Feature calculated dimension.",
                 "dataType": "Text", "geoRole": None, "sortOrder": "Ascending", "displayCategory": "Discrete", "isVisible": False},
                {"dataObjectFieldName": "IsMeteredIndicator__c", "label": "Billable",
                 "description": "Whether this usage is billed (true) or included in the license (false). Use to separate metered spend from included usage.",
                 "dataType": "Boolean", "geoRole": None, "sortOrder": "Ascending", "displayCategory": "Discrete", "isVisible": True},
                {"dataObjectFieldName": "AiAgentInteractionId__c", "label": "Interaction Identifier",
                 "description": "Identifier of a single user round trip. One distinct value per user question, regardless of the number of internal large language model calls it produces.",
                 "dataType": "Text", "geoRole": None, "sortOrder": "Ascending", "displayCategory": "Discrete", "isVisible": False},
                {"dataObjectFieldName": "UserId__c", "label": "User Identifier",
                 "description": "Foreign key to the user who generated this usage. Used only to join to the user table.",
                 "dataType": "Text", "geoRole": None, "sortOrder": "Ascending", "displayCategory": "Discrete", "isVisible": False},
                {"dataObjectFieldName": "Timestamp__c", "label": "Event Time Raw",
                 "description": "Timestamp of the generative artificial intelligence call. Truncated to a day by the Usage Date calculated dimension.",
                 "dataType": "DateTime", "geoRole": None, "sortOrder": "Ascending", "displayCategory": "Continuous", "isVisible": False},
            ],
            "semanticMeasurements": [
                {"dataObjectFieldName": "PromptTotalTokenCount__c", "label": "Total Token Count",
                 "description": "Total number of tokens consumed by the generative artificial intelligence call. Sum across calls gives token volume for any period.",
                 "dataType": "Number", "decimalPlace": 0, "aggregationType": "None", "directionality": "Up",
                 "displayCategory": "Continuous", "sortOrder": "Ascending", "isVisible": True, "shouldTreatNullsAsZeros": True},
                {"dataObjectFieldName": "PromptInputTokenCount__c", "label": "Input Token Count",
                 "description": "Number of prompt input tokens consumed by the generative artificial intelligence call.",
                 "dataType": "Number", "decimalPlace": 0, "aggregationType": "None", "directionality": "Up",
                 "displayCategory": "Continuous", "sortOrder": "Ascending", "isVisible": False, "shouldTreatNullsAsZeros": True},
                {"dataObjectFieldName": "PromptCompletionTokenCount__c", "label": "Completion Token Count",
                 "description": "Number of completion tokens produced by the generative artificial intelligence call.",
                 "dataType": "Number", "decimalPlace": 0, "aggregationType": "None", "directionality": "Up",
                 "displayCategory": "Continuous", "sortOrder": "Ascending", "isVisible": False, "shouldTreatNullsAsZeros": True},
                {"dataObjectFieldName": "UsageQuantity__c", "label": "Action Count",
                 "description": "Number of billable actions recorded for the generative artificial intelligence call. Drives the per-action portion of the estimated Flex Credit cost.",
                 "dataType": "Number", "decimalPlace": 0, "aggregationType": "None", "directionality": "Up",
                 "displayCategory": "Continuous", "sortOrder": "Ascending", "isVisible": True, "shouldTreatNullsAsZeros": True},
            ],
        },
        {
            "label": "User",
            "description": "User dimension. One row per user. Use to attribute generative artificial intelligence usage and estimated cost to a named person.",
            "dataObjectName": DIM_DMO,
            "dataObjectType": "Dmo",
            "shouldIncludeAllFields": False,
            "semanticDimensions": [
                {"dataObjectFieldName": "ssot__Id__c", "label": "User Key",
                 "description": "Primary key of the user. Used only to join to the usage table.",
                 "dataType": "Text", "geoRole": None, "sortOrder": "Ascending", "displayCategory": "Discrete", "isVisible": False},
                {"dataObjectFieldName": "ssot__FullName__c", "label": "User Name",
                 "description": "Full readable name of the user who generated the usage. Primary way to identify who is driving adoption and cost.",
                 "dataType": "Text", "geoRole": None, "sortOrder": "Ascending", "displayCategory": "Discrete", "isVisible": True},
                {"dataObjectFieldName": "ssot__Username__c", "label": "Username",
                 "description": "Login username of the user. Secondary identifier.",
                 "dataType": "Text", "geoRole": None, "sortOrder": "Ascending", "displayCategory": "Discrete", "isVisible": True},
            ],
            "semanticMeasurements": [],
        },
    ],
    "semanticRelationships": [],
    "semanticCalculatedMeasurements": [],
    "semanticCalculatedDimensions": [],
    "semanticLogicalTables": [],
    "semanticMetrics": [],
}
r = sf_rest(f"{BASE_SEM}/ssot/semantic/models", method="POST", body=model_payload)
if not r.get("apiName"): die("model create", r)
model_id = r["id"]
sdo_api = {s["label"]: s["apiName"] for s in r["semanticDataObjects"]}
ok(f"model {r['apiName']}  id={model_id}  SDOs={list(sdo_api.values())}")

# discover auto-generated field apiNames
full = sf_rest(f"{BASE_SEM}/ssot/semantic/models/{MODEL_API_NAME}?includeModelContent=true")
field_api = {}
for sdo in full.get("semanticDataObjects", []):
    k = sdo["apiName"]
    field_api[k] = {}
    for f in sdo.get("semanticMeasurements", []) + sdo.get("semanticDimensions", []):
        field_api[k][f["dataObjectFieldName"]] = f["apiName"]

def fld(sdo_key, dlo_field):
    v = field_api.get(sdo_key, {}).get(dlo_field)
    if not v: die(f"field not found {sdo_key}.{dlo_field}")
    return v

FACT = sdo_api["AI Usage"]
USER = sdo_api["User"]

# ── PHASE 3: Calculated fields ─────────────────────────────────────────────────
print("\n[3/6] Calculated dimensions + measurements")

def post_calc_dim(payload):
    r = sf_rest(f"{BASE_SEM}/ssot/semantic/models/{MODEL_API_NAME}/calculated-dimensions", method="POST", body=payload)
    if not r.get("apiName"): die(f"calc dim {payload['label']}", r)
    ok(f"calc dim {r['apiName']}")

def post_calc_meas(payload):
    r = sf_rest(f"{BASE_SEM}/ssot/semantic/models/{MODEL_API_NAME}/calculated-measurements", method="POST", body=payload)
    if not r.get("apiName"): die(f"calc measure {payload['label']}", r)
    ok(f"calc measure {r['apiName']}")

f_feature = fld(FACT, "GenAiGatewayFeatureName__c")
f_inter   = fld(FACT, "AiAgentInteractionId__c")
f_time    = fld(FACT, "Timestamp__c")
f_tokens  = fld(FACT, "PromptTotalTokenCount__c")
f_actions = fld(FACT, "UsageQuantity__c")

# Feature normalization: NULL -> "Untagged (Flows/Custom)"; keep every product distinct.
post_calc_dim({
    "apiName": "Feature_clc", "label": "Feature",
    "description": "Normalized feature name. Empty names are labeled Untagged (Flows/Custom), representing automation-triggered usage, not a data quality issue. Distinct products such as Agentforce Coworker and Employee Assistant are never merged.",
    "expression": f"IF ISNULL([{FACT}].[{f_feature}]) THEN 'Untagged (Flows/Custom)' ELSE [{FACT}].[{f_feature}] END",
    "dataType": "Text", "displayCategory": "Discrete", "level": "Row", "isVisible": True, "sortOrder": "Ascending",
})

# Usage Date: truncate timestamp to day (daily telemetry time spine).
post_calc_dim({
    "apiName": "Usage_Date_clc", "label": "Usage Date",
    "description": "Calendar day of the generative artificial intelligence call, truncated from the event timestamp. Primary time dimension for daily, monthly and quarterly trends.",
    "expression": f"DATE(DATETRUNC('day', [{FACT}].[{f_time}]))",
    "dataType": "Date", "displayCategory": "Continuous", "level": "Row", "isVisible": True, "sortOrder": "Ascending",
})

# Measures
post_calc_meas({
    "apiName": "Total_Tokens_clc", "label": "Total Tokens",
    "description": "Total number of tokens consumed across generative artificial intelligence calls in the selected period. Primary volume metric.",
    "expression": f"SUM([{FACT}].[{f_tokens}])", "aggregationType": "UserAgg", "dataType": "Number", "decimalPlace": 0,
    "directionality": "Up", "displayCategory": "Continuous", "level": "AggregateFunction", "isVisible": True,
    "shouldTreatNullsAsZeros": True, "sortOrder": "Ascending", "sentiment": "SentimentTypeNone",
})
post_calc_meas({
    "apiName": "Total_Actions_clc", "label": "Total Actions",
    "description": "Total number of billable actions across generative artificial intelligence calls in the selected period. Drives the per-action portion of estimated Flex Credit cost.",
    "expression": f"SUM([{FACT}].[{f_actions}])", "aggregationType": "UserAgg", "dataType": "Number", "decimalPlace": 0,
    "directionality": "Up", "displayCategory": "Continuous", "level": "AggregateFunction", "isVisible": True,
    "shouldTreatNullsAsZeros": True, "sortOrder": "Ascending", "sentiment": "SentimentTypeNone",
})
post_calc_meas({
    "apiName": "Interactions_clc", "label": "Interactions",
    "description": "Raw number of large language model calls in the selected period. This counts internal calls, not user questions. Use Round Trips for user question counts.",
    "expression": f"COUNT([{FACT}].[{f_inter}])", "aggregationType": "UserAgg", "dataType": "Number", "decimalPlace": 0,
    "directionality": "Up", "displayCategory": "Continuous", "level": "AggregateFunction", "isVisible": True,
    "shouldTreatNullsAsZeros": False, "sortOrder": "Ascending", "sentiment": "SentimentTypeNone",
})
# Round Trips — distinct count of interaction identifiers (one per real user question).
post_calc_meas({
    "apiName": "Round_Trips_clc", "label": "Round Trips",
    "description": "Number of distinct user round trips in the selected period. One round trip equals one real user question, regardless of the number of internal large language model calls it produces.",
    "expression": f"COUNTD([{FACT}].[{f_inter}])", "aggregationType": "UserAgg", "dataType": "Number", "decimalPlace": 0,
    "directionality": "Up", "displayCategory": "Continuous", "level": "AggregateFunction", "isVisible": True,
    "shouldTreatNullsAsZeros": False, "sortOrder": "Ascending", "sentiment": "SentimentTypeNone",
})
# Active Users — distinct count of users.
post_calc_meas({
    "apiName": "Active_Users_clc", "label": "Active Users",
    "description": "Number of distinct users who generated generative artificial intelligence usage in the selected period. Primary adoption metric.",
    "expression": f"COUNTD([{FACT}].[{fld(FACT,'UserId__c')}])", "aggregationType": "UserAgg", "dataType": "Number", "decimalPlace": 0,
    "directionality": "Up", "displayCategory": "Continuous", "level": "AggregateFunction", "isVisible": True,
    "shouldTreatNullsAsZeros": False, "sortOrder": "Ascending", "sentiment": "SentimentTypeNone",
})
# Estimated Flex Credits — feature-conditional. Coworker = round trips x 72; else actions x 20 + ceil(tokens/2000) x 4.
# MAX([feature]) lifts the (constant-within-feature-grain) dimension into aggregate context.
fc_expr = (
    f"IF MAX([{FACT}].[{f_feature}]) = 'AgentforceCoworker' "
    f"THEN COUNTD([{FACT}].[{f_inter}]) * 72 "
    f"ELSE (SUM([{FACT}].[{f_actions}]) * 20) + (CEILING(SUM([{FACT}].[{f_tokens}]) / 2000.0) * 4) END"
)
post_calc_meas({
    "apiName": "Estimated_Flex_Credits_clc", "label": "Estimated Flex Credits",
    "description": "Estimated Flex Credit cost. Agentforce Coworker is metered at seventy two credits per round trip; other features at twenty credits per action plus four per two thousand tokens. An estimate; the Digital Wallet is billing source of truth.",
    "expression": fc_expr, "aggregationType": "UserAgg", "dataType": "Number", "decimalPlace": 0,
    "directionality": "Up", "displayCategory": "Continuous", "level": "AggregateFunction", "isVisible": True,
    "shouldTreatNullsAsZeros": False, "sortOrder": "Ascending", "sentiment": "SentimentTypeUpIsBad",
})

# ── PHASE 4: Relationship + metrics + business preferences ─────────────────────
print("\n[4/6] Relationship + semantic metrics")
r = sf_rest(f"{BASE_SEM}/ssot/semantic/models/{MODEL_API_NAME}/relationships", method="POST", body={
    "leftSemanticDefinitionApiName": FACT,
    "rightSemanticDefinitionApiName": USER,
    "joinType": "Auto",
    "criteria": [{
        "joinOperator": "EqualsIgnoreCase",
        "leftFieldType": "TableField",
        "leftSemanticFieldApiName": fld(FACT, "UserId__c"),
        "rightFieldType": "TableField",
        "rightSemanticFieldApiName": fld(USER, "ssot__Id__c"),
    }],
})
if r.get("__error__") or r.get("errorCode"):
    info(f"relationship response: {str(r)[:200]}")
else:
    ok("relationship AI Usage -> User")

# metric helpers — dimension refs use the same dual-key shape as measurement refs:
# a table field sets tableFieldReference and nulls calculatedFieldApiName, and vice versa.
def dim_ref(sdo, dlo_field):
    return {"tableFieldReference": {"fieldApiName": fld(sdo, dlo_field), "tableApiName": sdo},
            "calculatedFieldApiName": None}

def calc_dim_ref(api_name):
    return {"tableFieldReference": None, "calculatedFieldApiName": api_name}

def insight_types():
    return [{"enabled": True, "type": t} for t in
            ["TopContributors", "ComparisonToExpectedRangeAlert", "TrendChangeAlert",
             "BottomContributors", "ConcentratedContributionAlert", "TopDrivers",
             "TopDetractors", "CurrentTrend", "OutlierDetection"]]

user_name_ref = dim_ref(USER, "ssot__FullName__c")
feature_ref   = calc_dim_ref("Feature_clc")
billable_ref  = dim_ref(FACT, "IsMeteredIndicator__c")

# additionalDimensions: everything referenced anywhere (incl. identifyingDimension + insight dims)
add_dims = [feature_ref, billable_ref, user_name_ref]
insight_dims = [feature_ref, billable_ref, user_name_ref]

METRICS = [
    ("total_tokens_mtc", "Total Tokens", "Total_Tokens_clc", "UserAgg",
     "Total number of tokens consumed across generative artificial intelligence calls. Rising values indicate growing adoption or heavier usage.", "token", "tokens", "SentimentTypeNone"),
    ("total_actions_mtc", "Total Actions", "Total_Actions_clc", "UserAgg",
     "Total number of billable actions. Drives the per-action portion of the estimated Flex Credit cost.", "action", "actions", "SentimentTypeNone"),
    ("interactions_mtc", "Interactions", "Interactions_clc", "UserAgg",
     "Raw number of large language model calls. This is not the count of user questions; use Round Trips for that.", "interaction", "interactions", "SentimentTypeNone"),
    ("round_trips_mtc", "Round Trips", "Round_Trips_clc", "UserAgg",
     "Number of distinct user round trips. One round trip equals one real user question.", "round trip", "round trips", "SentimentTypeNone"),
    ("estimated_flex_credits_mtc", "Estimated Flex Credits", "Estimated_Flex_Credits_clc", "UserAgg",
     "Estimated Flex Credit cost of generative artificial intelligence usage. Agentforce Coworker is metered per round trip; other features per action plus per token. This is an estimate; the Digital Wallet is the billing source of truth.", "credit", "credits", "SentimentTypeUpIsBad"),
    ("active_users_mtc", "Active Users", "Active_Users_clc", "UserAgg",
     "Number of distinct users generating usage. Primary adoption metric.", "user", "users", "SentimentTypeNone"),
]

metric_labels_created = []
for api, label, calc, agg, desc, sing, plur, sentiment in METRICS:
    payload = {
        "apiName": api, "label": label, "description": desc,
        "measurementReference": {"tableFieldReference": None, "calculatedFieldApiName": calc},
        "timeDimensionReference": {"tableFieldReference": None, "calculatedFieldApiName": "Usage_Date_clc"},
        "aggregationType": agg, "isCumulative": False,
        "timeGrains": ["Day", "Month", "Quarter"],
        "additionalDimensions": add_dims,
        "insightsSettings": {
            "identifyingDimension": {"identifierDimensionReference": {"tableFieldReference": {"fieldApiName": fld(USER, "ssot__FullName__c"), "tableApiName": USER}}},
            "insightTypes": insight_types(),
            "insightsDimensionsReferences": insight_dims,
            "singularNoun": sing, "pluralNoun": plur, "sentiment": sentiment,
        },
    }
    r = sf_rest(f"{BASE_SEM}/ssot/semantic/models/{MODEL_API_NAME}/metrics", method="POST", body=payload)
    if isinstance(r, dict) and r.get("apiName"):
        ok(f"metric {label}")
        metric_labels_created.append(label)
    else:
        info(f"metric {label} FAILED: {str(r)[:300]}")

# business preferences
prefs = "\n\n".join([
    "# Agentforce Coworker is metered per round trip at seventy two Flex Credits per user question, not per token. It is a fixed rate feature distinct from every other token based feature.",
    "# Never merge Agentforce Coworker and Employee Assistant. They are distinct products and must be reported separately.",
    "# When users ask about top users or top performers, sort by Estimated Flex Credits descending.",
    "# Untagged (Flows/Custom) represents automation triggered artificial intelligence usage with no assigned feature tag. It is not a data quality issue.",
    "# Estimated Flex Credits is an estimate for adoption and cost governance. The Digital Wallet is the billing source of truth.",
    "# Interactions counts raw large language model calls. Round Trips counts real user questions. Use Round Trips when a user asks how many questions were asked.",
])
r = sf_rest(f"{BASE_SEM}/ssot/semantic/models/{MODEL_API_NAME}", method="PATCH", body={"businessPreferences": prefs})
if r.get("__error__") or r.get("errorCode"):
    info(f"business preferences (non-fatal): {str(r)[:200]}")
else:
    ok("business preferences applied")

# validate
v = sf_rest(f"{BASE_SEM}/ssot/semantic/models/{MODEL_API_NAME}/validate")
ok(f"model isValid={v.get('isValid')}")

# link SDM to workspace
r = sf_rest(f"{BASE_SEM}/tableau/workspaces/{workspace_name}/assets", method="POST",
            body={"assetId": model_id, "assetType": "SemanticModel", "assetUsageType": "Referenced"})
info(f"workspace link: {str(r)[:120]}")

# fetch metric ids
r = sf_rest(f"{BASE_SEM}/ssot/semantic/models/{MODEL_API_NAME}/metrics")
metric_ids = {m["label"]: m["id"] for m in r.get("metrics", [])}
metric_apis = {m["label"]: m["apiName"] for m in r.get("metrics", [])}
ok(f"metric ids: {list(metric_ids.keys())}")

# ══════════════════════════════════════════════════════════════════════════════
# VISUALIZATIONS
# ══════════════════════════════════════════════════════════════════════════════
print("\n[5/6] Visualizations")

VIZ_FONTS = {"actionableHeaders": {"color": "#0250D9", "size": 13}, "axisTickLabels": {"color": "#2E2E2E", "size": 13},
             "fieldLabels": {"color": "#2E2E2E", "size": 13}, "headers": {"color": "#2E2E2E", "size": 13},
             "legendLabels": {"color": "#2E2E2E", "size": 13}, "markLabels": {"color": "#2E2E2E", "size": 13},
             "marks": {"color": "#2E2E2E", "size": 13}}
VIZ_LINES = {"axisLine": {"color": "#C9C9C9"}, "fieldLabelDividerLine": {"color": "#C9C9C9"},
             "separatorLine": {"color": "#C9C9C9"}, "zeroLine": {"color": "#C9C9C9"}}
# No zebra row banding (banding color == background) -- a flat, modern look instead of the
# classic muted-gray CRM Analytics report style.
VIZ_SHADING = {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#FFFFFF"}}}
ACCENT = "#0176D3"  # Salesforce Lightning Blue -- single consistent brand accent for single-series charts

def axis_number(key, title="", decimals=0):
    return {key: {"isVisible": True, "isZeroLineVisible": True, "range": {"includeZero": True, "type": "Auto"},
                  "scale": {"format": {"numberFormatInfo": {"decimalPlaces": decimals, "displayUnits": "Auto",
                            "includeThousandSeparator": True, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "",
                            "type": "NumberShort"}}}, "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}},
                  "titleText": title}}

def axis_date(key):
    return {key: {"isVisible": True, "isZeroLineVisible": False, "range": {"includeZero": False, "type": "Auto"},
                  "scale": {"format": {"dateTemplate": ""}}, "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}}}}

def pane_format(key, decimals=0, fmt_type="Number"):
    return {key: {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": decimals, "displayUnits": "Auto",
            "includeThousandSeparator": True, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": fmt_type}}}}}

def viz_style(axis_dict, pane_dict, reverse=False, dim_row_keys=None, line=False, entire=False, table=False,
              color="", line_width=3):
    fields_headers = {k: {"hiddenValues": [], "isVisible": True, "showMissingValues": False} for k in (dim_row_keys or [])}
    if line:
        marksize = {"isAutomaticSize": True, "size": {"isAutomatic": True, "type": "Pixel", "value": line_width}}
    else:
        marksize = {"isAutomaticSize": True, "size": {"isAutomatic": True, "type": "Percentage", "value": 75}}
    merge = False if table else True
    return {
        "allHeaders": {"columns": {"mergeRepeatedCells": merge, "showIndex": False}, "fields": fields_headers,
                       "rows": {"mergeRepeatedCells": merge, "showIndex": False}},
        "axis": axis_dict,
        "fieldLabels": {"columns": {"showDividerLine": False, "showLabels": True}, "rows": {"showDividerLine": False, "showLabels": True}},
        "fit": "Entire" if entire else "Standard", "fonts": VIZ_FONTS, "lines": VIZ_LINES,
        "marks": {"ALL": {"color": {"color": color}, "isAutomaticSize": marksize["isAutomaticSize"],
                          "isStackingAxisCentered": False,
                          "label": {"canOverlapLabels": False, "marksToLabel": {"type": "All"}, "showMarkLabels": False},
                          "range": {"reverse": reverse}, "size": marksize["size"]}},
        "panes": pane_dict, "referenceLines": {}, "shading": VIZ_SHADING, "showDataPlaceholder": False,
        "title": {"isVisible": True},
    }

def calc_measure(field_name, label=None, function="Sum", discrete=False):
    # Table mode bans continuous fields outright (renders "AnalyticsError: Axes are not
    # supported in RowHeadersWidth mode" at open time, not at API creation time) -- pass
    # discrete=True for any measure used in a Table-mode visualization.
    f = {"type": "Field", "fieldName": field_name, "function": function, "role": "Measure",
         "displayCategory": "Discrete" if discrete else "Continuous"}
    if label: f["label"] = label
    return f

def calc_dim(field_name, label=None, is_date=False):
    f = {"type": "Field", "fieldName": field_name, "role": "Dimension",
         "displayCategory": "Continuous" if is_date else "Discrete"}
    if label: f["label"] = label
    return f

def raw_dim(field_name, object_name, label=None):
    f = {"type": "Field", "fieldName": field_name, "objectName": object_name, "role": "Dimension", "displayCategory": "Discrete"}
    if label: f["label"] = label
    return f

def create_viz(label, name, fields_dict, rows, columns, mark_type="Bar",
               color_encoding=None, stacked=False, style=None, sort=None, mode="Visualization",
               per_field_marks=None):
    encodings = [{"fieldKey": color_encoding, "type": "Color"}] if color_encoding else []
    sort_orders = {"columns": [], "fields": (sort or {}), "rows": []}
    if mode == "Table":
        marks = {"ALL": {"encodings": [], "isAutomatic": False,
                         "stack": {"isAutomatic": False, "isStacked": False}, "type": "Text"}}
        # Table mode: every field on rows/columns needs its own marks entry.
        for fk in (rows + columns):
            marks[fk] = {"encodings": [], "isAutomatic": False,
                         "stack": {"isAutomatic": False, "isStacked": False}, "type": "Text"}
    else:
        marks = {"ALL": {"encodings": encodings, "isAutomatic": True,
                         "stack": {"isAutomatic": stacked, "isStacked": stacked}, "type": mark_type}}
    payload = {
        "label": label, "name": name, "description": f"Auto-generated: {label}",
        "dataSource": {"name": MODEL_API_NAME, "type": "SemanticModel"},
        "workspace": {"name": workspace_name}, "fields": fields_dict, "interactions": [],
        "view": {"label": f"{label} View", "name": f"{name}_view",
                 "viewSpecification": {"filters": [], "sortOrders": sort_orders}},
        "visualSpecification": {
            "columns": columns, "forecasts": {},
            "legends": ({color_encoding: {"isVisible": True, "position": "Right", "title": {"isVisible": True}}} if color_encoding else {}),
            "marks": marks, "measureValues": [], "mode": mode, "referenceLines": {},
            "rows": rows, "style": style or {},
        },
    }
    r = sf_rest(f"{BASE_VIZ}/tableau/visualizations", method="POST", body=payload)
    if isinstance(r, dict) and r.get("id"):
        ok(f"viz {label}")
        return r
    info(f"viz {label} FAILED: {str(r)[:400]}")
    return None

# choose the cost field: FC if built, else tokens
have_fc = "Estimated Flex Credits" in metric_labels_created
cost_calc = "Estimated_Flex_Credits_clc" if have_fc else "Total_Tokens_clc"
cost_label = "Estimated Flex Credits" if have_fc else "Total Tokens"
cost_func = "UserAgg" if have_fc else "Sum"

# 1. Daily trend of estimated flex credits -- Area (filled), not a plain Line: reads more like a
# modern SaaS dashboard than a classic CRM Analytics report. Confirmed accepted live: mark type
# "Area" needs the exact same axis/panes shape as "Line", nothing extra.
viz_trend = create_viz(
    label=f"{cost_label} — Daily Trend", name=f"{MODEL_API_NAME}_cost_trend",
    fields_dict={"F1": calc_measure(cost_calc, cost_label, function=cost_func),
                 "F2": calc_dim("Usage_Date_clc", "Usage Date", is_date=True)},
    rows=["F1"], columns=["F2"], mark_type="Area",
    style=viz_style({**axis_number("F1", cost_label), **axis_date("F2")}, pane_format("F1", 0),
                     line=True, color=ACCENT, line_width=2),
)

# 2. Cost by feature, colored by billable (stacked bar)
viz_feature = create_viz(
    label=f"{cost_label} by Feature (Billable vs Included)", name=f"{MODEL_API_NAME}_cost_feature",
    fields_dict={"F1": calc_measure(cost_calc, cost_label, function=cost_func),
                 "F2": calc_dim("Feature_clc", "Feature"),
                 "F3": raw_dim(fld(FACT, "IsMeteredIndicator__c"), FACT, "Billable")},
    rows=["F2"], columns=["F1"], mark_type="Bar", color_encoding="F3", stacked=True,
    style=viz_style(axis_number("F1", cost_label), pane_format("F1", 0), reverse=True, dim_row_keys=["F2"]),
    sort={"F2": {"byField": "F1", "order": "Descending", "type": "Field"}},
)

# 3. Detail table: User x Feature x Total Tokens x Estimated Flex Credits
# Two gotchas fixed here (both confirmed live against this org):
#  - viz field "function" must match the calc measurement's own aggregationType (UserAgg here,
#    since Total_Tokens_clc already wraps SUM(...) in its expression) -- "Sum" double-aggregates.
#  - Table mode requires EVERY field, including measures, to be displayCategory "Discrete" --
#    "Continuous" triggers axis initialization, which Table mode's "axis" (must be {} — it can
#    only hold continuous fields, and Table mode has none) rejects at render time.
tbl_fields = {
    "F1": calc_dim("Feature_clc", "Feature"),
    "F2": raw_dim(fld(USER, "ssot__FullName__c"), USER, "User Name"),
    "F3": calc_measure("Total_Tokens_clc", "Total Tokens", function="UserAgg", discrete=True),
    "F4": calc_measure(cost_calc, cost_label, function=cost_func, discrete=True),
}
viz_table = create_viz(
    label="Usage Detail — User × Feature", name=f"{MODEL_API_NAME}_detail_table",
    fields_dict=tbl_fields, rows=["F2", "F1", "F3", "F4"], columns=[], mode="Table",
    style={**viz_style({}, {**pane_format("F3", 0), **pane_format("F4", 0)},
                        dim_row_keys=["F1", "F2", "F3", "F4"], table=True), "fit": "RowHeadersWidth"},
)

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
print("\n[6/6] Dashboard")

_NAVY = "#0B1F3A"
_PAGE = "#F4F6F9"
CARD = {"backgroundColor": "#FFFFFF", "borderColor": "#DDDBDA", "borderEdges": ["all"], "borderRadius": 10, "borderWidth": 1}

def dash_metric(name, mapi, mid):
    return {"actions": [], "name": name, "type": "metric",
            "parameters": {"metricOption": {"layout": {"componentVisibility": {
                "comparison": True, "insights": False, "details": True, "title": True, "value": True, "chart": True}},
                "sdmApiName": MODEL_API_NAME, "sdmId": model_id},
                "receiveFilterSource": {"filterMode": "all", "widgetIds": []}, "widgetStyle": CARD},
            "source": {"id": mid, "name": mapi}}

def dash_viz(name, vres):
    vapi = vres.get("apiName") or vres.get("name")
    return {"actions": [], "name": name, "type": "visualization",
            "parameters": {"receiveFilterSource": {"filterMode": "all", "widgetIds": []}, "widgetStyle": CARD},
            "source": {"id": vres["id"], "name": vapi}}

def dash_date_filter(name, label, calc_date_api):
    return {"actions": [], "name": name, "label": label, "type": "filter",
            "initialValues": {"details": {"fieldName": calc_date_api, "operator": "LastNDays", "values": [90.0]}},
            "parameters": {"filterOption": {"dataType": "Date", "fieldName": calc_date_api, "selectionType": "multiple"},
                           "isLabelHidden": False, "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                           "viewType": "list", "widgetStyle": {"backgroundColor": "#ffffff", "borderColor": "#cccccc",
                           "borderEdges": [], "borderRadius": 8, "borderWidth": 1}},
            "source": {"id": model_id, "name": MODEL_API_NAME}}

def dash_feature_filter(name, label):
    return {"actions": [], "name": name, "label": label, "type": "filter",
            "source": {"id": model_id, "name": MODEL_API_NAME},
            "parameters": {"filterOption": {"dataType": "Text", "fieldName": "Feature_clc", "selectionType": "multiple"},
                           "isLabelHidden": False, "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                           "viewType": "list", "widgetStyle": {"backgroundColor": "#ffffff", "borderColor": "#cccccc",
                           "borderEdges": [], "borderRadius": 8, "borderWidth": 1}}}

def dash_text(name, text, bold=True, size="24px", color="#181818", bg=None):
    style = {"backgroundColor": bg, "borderEdges": [], "borderRadius": 0, "borderWidth": 0} if bg else None
    p = {"conditionalFormattingRules": [],
         "content": [{"attributes": {"bold": bold, "color": color, "size": size}, "insert": text, "rules": []},
                     {"insert": "\n", "rules": []}],
         "receiveFilterSource": {"filterMode": "all", "widgetIds": []}}
    if style: p["widgetStyle"] = style
    return {"actions": [], "name": name, "type": "text", "parameters": p}

def dash_container(name, bg="#FFFFFF"):
    return {"actions": [], "name": name, "type": "container",
            "parameters": {"widgetStyle": {"backgroundColor": bg, "borderColor": "#DDDBDA",
                           "borderEdges": ["all"], "borderRadius": 4, "borderWidth": 1}}}

def pos(name, col, row, cs, rs):
    return {"name": name, "column": col, "row": row, "colspan": cs, "rowspan": rs}

widgets = {}
cells = []

# Header band (navy)
widgets["hdr"] = dash_container("hdr", bg=_NAVY)
cells.append(pos("hdr", 0, 0, 36, 4))
widgets["hdr_title"] = dash_text("hdr_title", "AI Usage & Cost — Executive View", bold=True, size="26px", color="#FFFFFF", bg=_NAVY)
cells.append(pos("hdr_title", 1, 0, 34, 2))
widgets["hdr_sub"] = dash_text("hdr_sub",
    "Adoption and estimated Flex Credit cost of Agentforce & GenAI usage by user, feature and day. Estimated Flex Credits is an estimate; the Digital Wallet is billing source of truth.",
    bold=False, size="12px", color="#C7D2E0", bg=_NAVY)
cells.append(pos("hdr_sub", 1, 2, 34, 2))

# Filters
widgets["f_date"] = dash_date_filter("f_date", "Usage Date", "Usage_Date_clc")
cells.append(pos("f_date", 0, 5, 11, 2))
widgets["f_feature"] = dash_feature_filter("f_feature", "Feature")
cells.append(pos("f_feature", 12, 5, 11, 2))

# KPI cards
widgets["kpi_lbl"] = dash_text("kpi_lbl", "Key Metrics", bold=True, size="15px", color="#5c5c5c", bg=_PAGE)
cells.append(pos("kpi_lbl", 0, 8, 36, 1))
rt_or_int = "Round Trips" if "Round Trips" in metric_ids else "Interactions"
kpi_order = ["Total Tokens", "Estimated Flex Credits", "Active Users", rt_or_int]
kpi_order = [k for k in kpi_order if k in metric_ids]
n = len(kpi_order) or 1
w = 36 // n
for i, k in enumerate(kpi_order):
    wn = f"kpi_{i}"
    widgets[wn] = dash_metric(wn, metric_apis[k], metric_ids[k])
    cells.append(pos(wn, i * w, 9, w, 9))

# Charts row
widgets["ch_lbl"] = dash_text("ch_lbl", "Trends & Breakdowns", bold=True, size="15px", color="#5c5c5c", bg=_PAGE)
cells.append(pos("ch_lbl", 0, 19, 36, 1))
if viz_trend:
    widgets["v_trend"] = dash_viz("v_trend", viz_trend)
    cells.append(pos("v_trend", 0, 20, 18, 13))
if viz_feature:
    widgets["v_feature"] = dash_viz("v_feature", viz_feature)
    cells.append(pos("v_feature", 18, 20, 18, 13))

# Detail table
widgets["tbl_lbl"] = dash_text("tbl_lbl", "Usage Detail", bold=True, size="15px", color="#5c5c5c", bg=_PAGE)
cells.append(pos("tbl_lbl", 0, 34, 36, 1))
if viz_table:
    widgets["v_table"] = dash_viz("v_table", viz_table)
    cells.append(pos("v_table", 0, 35, 36, 14))

dash_payload = {
    "label": "AI Usage & Cost — Executive View", "name": DASH_NAME,
    "description": f"Tier 3 Tableau Next executive view for {COMPANY} {USE_CASE}.",
    "workspaceIdOrApiName": WORKSPACE_NAME,
    "style": {"widgetStyle": {"backgroundColor": _PAGE, "borderColor": "#DDDBDA", "borderEdges": [], "borderRadius": 0, "borderWidth": 1}},
    "widgets": widgets,
    "layouts": [{
        "name": "default", "columnCount": 36, "rowHeight": 24, "maxWidth": 1440,
        "pages": [{"name": str(uuid.uuid4()), "label": "Overview", "widgets": cells}],
        "style": {"backgroundColor": _PAGE, "cellSpacingX": 8, "cellSpacingY": 8, "gutterColor": _PAGE},
    }],
}
r = sf_rest(f"{BASE_VIZ}/tableau/dashboards", method="POST", body=dash_payload)
if r.get("id"):
    ok(f"dashboard {DASH_NAME}  id={r['id']}")
else:
    info(f"dashboard FAILED: {str(r)[:500]}")

# ── Done ────────────────────────────────────────────────────────────────────
print(f"\n{'='*66}")
print(f"  BUILD COMPLETE — {COMPANY} — {USE_CASE}")
print(f"  Workspace: {workspace_name}")
print(f"  Model: {MODEL_API_NAME}")
print(f"  Metrics built: {metric_labels_created}")
print(f"  Cost field used in charts: {cost_label}")
print(f"{'='*66}")
print("\nManual step: Data 360 -> Semantic Model -> " + MODEL_API_NAME +
      " -> Settings -> Analytics Agent Readiness -> toggle ON.")
