-- =====================================================================
-- Query 3 — Normalized usage (clean view, no Calculated Insight required)
-- =====================================================================
-- Goal    : the "correct" view Tier-1 users want without paying for a CI.
--           Keeps each GenAI feature DISTINCT (per Salesforce official doc
--           "Tracking Agentforce Coworker Usage", 2026-06-22): AgentforceCoworker
--           (formerly AESSearchAgent) and EmployeeAssistant are SEPARATE agent
--           types and must NOT be merged. Only fix applied: label NULL feature as
--           'Untagged (Flows/Custom)'. Adds a DAY axis (usage_day) for time charts.
--           NOTE: to isolate Coworker specifically, filter feature = 'AgentforceCoworker'.
--
-- This is exactly the logic the Calculated Insight AI_Usage_By_User encodes.
-- Use this SQL for Tier 1 (pay-per-look, no recurring credit). Use the CI +
-- LWC cockpit for Tier 2 (opt-in, pre-aggregated, recurring credit).
--
-- Run in  : Data Cloud > Query Editor, OR /services/data/v64.0/ssot/queryv2
-- =====================================================================

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
