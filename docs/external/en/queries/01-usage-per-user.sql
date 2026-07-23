-- =====================================================================
-- Query 1 — AI usage per user
-- =====================================================================
-- Goal  : who uses which AI feature, and at what volume.
-- Where : Data Cloud > Query Editor. Paste, then Run.
-- =====================================================================
SELECT
    u."ssot__FullName__c"                         AS user_name,
    u."ssot__Username__c"                         AS username,
    a."GenAiGatewayFeatureName__c"                AS feature,
    SUM(a."PromptTotalTokenCount__c")             AS total_tokens,
    SUM(a."PromptInputTokenCount__c")             AS input_tokens,
    SUM(a."PromptCompletionTokenCount__c")        AS output_tokens,
    COUNT(*)                                      AS nb_calls,
    COUNT(DISTINCT a."AiAgentInteractionId__c")   AS nb_roundtrips
FROM "AiAgentGenerativeAiUsage_std__dlm" a
JOIN "ssot__User__dlm" u
    ON a."UserId__c" = u."ssot__Id__c"
GROUP BY
    u."ssot__FullName__c",
    u."ssot__Username__c",
    a."GenAiGatewayFeatureName__c"
ORDER BY total_tokens DESC
LIMIT 50;
