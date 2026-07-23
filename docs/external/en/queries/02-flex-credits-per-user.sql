-- =====================================================================
-- Query 2 — Estimated Flex Credits per user
-- =====================================================================
-- Goal  : translate usage into an ESTIMATE of Flex Credits, per
--         user x feature, split by billed / included.
-- Where : Data Cloud > Query Editor. Paste, then Run.
--
-- Rate card (indicative):
--   Standard action        : 20 FC / action
--   Standard/basic prompt  :  4 FC / 2000 tokens
--   Agentforce Coworker    : 72 FC / round-trip (one user question)
--
-- is_metered: true = billed usage, false = usage included in the license.
--
-- WARNING: ESTIMATE ONLY. The Digital Wallet remains the billing source of
--          truth. Use this query to pilot ADOPTION, not to check an invoice.
-- =====================================================================
SELECT
    u."ssot__FullName__c"                                            AS user_name,
    u."ssot__Username__c"                                            AS username,
    a."GenAiGatewayFeatureName__c"                                   AS feature,
    a."IsMeteredIndicator__c"                                        AS is_metered,
    SUM(a."UsageQuantity__c")                                        AS nb_actions,
    COUNT(DISTINCT a."AiAgentInteractionId__c")                      AS nb_roundtrips,
    SUM(a."UsageQuantity__c") * 20                                   AS est_fc_actions,
    SUM(a."PromptTotalTokenCount__c")                                AS total_tokens,
    CEILING(SUM(a."PromptTotalTokenCount__c") / 2000.0) * 4          AS est_fc_tokens,
    -- Coworker is billed per round-trip (72 FC); others per action + token.
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
    a."GenAiGatewayFeatureName__c",
    a."IsMeteredIndicator__c"
ORDER BY est_fc_total DESC
LIMIT 50;
