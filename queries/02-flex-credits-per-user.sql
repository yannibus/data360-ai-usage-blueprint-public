-- =====================================================================
-- Query 2 — Estimated Flex Credits per user
-- =====================================================================
-- Goal    : translate raw usage into an ESTIMATE of Flex Credits consumed,
--           per user x feature, split by billable (is_metered) vs included.
-- Run in  : Data Cloud > Query Editor, OR /services/data/v64.0/ssot/queryv2
--
-- Rate card (Feb. 2026) used below:
--   Standard Action     : 20 FC / action
--   Standard/Basic Prompt:  4 FC / 2000 tokens
--   Agentforce Coworker : 72 FC / round-trip  (Salesforce pricing rule)
-- Formulas:
--   estimated_fc_actions = SUM(UsageQuantity__c) * 20
--   estimated_fc_tokens  = CEILING(SUM(PromptTotalTokenCount__c) / 2000.0) * 4
--   total_estimated_fc   = for AgentforceCoworker: COUNT(DISTINCT round-trips) * 72
--                          for every other feature: the two formulas above summed
--
-- ⚠️ COWORKER IS METERED PER ROUND-TRIP, NOT PER TOKEN.
--    A "round-trip" = one distinct AiAgentInteractionId__c (one user question,
--    whatever the number of internal LLM calls it spawns). Validated with controlled
--    questions: each question produces exactly one distinct AiAgentInteractionId__c,
--    regardless of token volume.
--    The per-token formula over/under-charged Coworker by up to 3x; the flat 72 FC
--    is the correct model. All other features keep the per-action/per-token model.
--
-- is_metered (IsMeteredIndicator__c):
--   true  = usage is billed
--   false = usage included in the license
--
-- ⚠️ ESTIMATION ONLY. The Digital Wallet remains the billing source of truth.
--    Flex Credit data available since 2026-05-29 (no retro-history).
--    Data-connector consumption (SharePoint, ingestion) is NOT here — Digital
--    Wallet only. This query pilots AI ADOPTION per user; the Wallet pilots
--    global billing. Both are complementary and necessary.
-- =====================================================================

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
