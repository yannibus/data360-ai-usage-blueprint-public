-- =====================================================================
-- Query 3 — Normalized view (usage per day, chart-ready)
-- =====================================================================
-- Goal  : the clean view — each distinct feature, untagged usage
--         relabelled "Untagged", and a DAY axis for time charts.
-- Where : Data Cloud > Query Editor. Paste, then Run.
--         To isolate Coworker: filter feature = 'AgentforceCoworker'.
-- =====================================================================
SELECT
    u."ssot__FullName__c"                                           AS user_name,
    u."ssot__Username__c"                                           AS username,
    CASE
        WHEN a."GenAiGatewayFeatureName__c" IS NULL
            THEN 'Untagged (Flows/Custom)'
        ELSE a."GenAiGatewayFeatureName__c"
    END                                                             AS feature,
    CAST(a."Timestamp__c" AS DATE)                                  AS usage_day,
    a."IsMeteredIndicator__c"                                       AS is_metered,
    SUM(a."PromptTotalTokenCount__c")                               AS total_tokens,
    SUM(a."PromptInputTokenCount__c")                               AS input_tokens,
    SUM(a."PromptCompletionTokenCount__c")                          AS output_tokens,
    COUNT(*)                                                        AS nb_calls,
    COUNT(DISTINCT a."AiAgentInteractionId__c")                     AS nb_roundtrips,
    SUM(a."UsageQuantity__c")                                       AS nb_actions,
    SUM(a."UsageQuantity__c") * 20                                  AS est_fc_actions,
    CEILING(SUM(a."PromptTotalTokenCount__c") / 2000.0) * 4         AS est_fc_tokens,
    CASE
        WHEN a."GenAiGatewayFeatureName__c" = 'AgentforceCoworker'
            THEN COUNT(DISTINCT a."AiAgentInteractionId__c") * 72
        ELSE (SUM(a."UsageQuantity__c") * 20)
             + (CEILING(SUM(a."PromptTotalTokenCount__c") / 2000.0) * 4)
    END                                                             AS est_fc_total
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
