-- =====================================================================
-- Query 1 — GenAI usage per user
-- =====================================================================
-- Goal    : identify who uses which AI feature, and at what token volume.
-- Run in  : Data Cloud > Query Editor, OR
--           POST /services/data/v64.0/ssot/queryv2  body {"sql":"..."}
-- Join    : AiAgentGenerativeAiUsage_std__dlm.UserId__c = ssot__User__dlm.ssot__Id__c
-- Prereq  : Data Stream User active (ssot__User__dlm populated). Without it,
--           results only expose raw UserId (005xx...) — unreadable.
--
-- PITFALLS (read before aggregating):
--   1. Each feature is a DISTINCT product — do NOT merge them. Per Salesforce
--      official doc "Tracking Agentforce Coworker Usage" (2026-06-22):
--        * Agentforce Coworker = feature 'AgentforceCoworker' (renamed from the
--          old 'AESSearchAgent' the week of June 22/29 2026 — 'AESSearchAgent'
--          no longer appears going forward).
--        * 'EmployeeAssistant' is a SEPARATE agent type, NOT Coworker. Keep it apart.
--      To track Coworker specifically: WHERE feature = 'AgentforceCoworker'.
--   2. feature = NULL  -> untagged usage (Flows, custom components). Do not
--      drop it: it is real consumption to watch.
--   3. Do NOT sum across features blindly — units differ downstream (actions
--      vs tokens vs minutes). Filter by feature before aggregating.
--   4. nb_interactions vs nb_roundtrips — these are NOT the same:
--        * nb_interactions = COUNT(*)                            = raw telemetry
--          rows = individual LLM calls. One user question can spawn 1, 2 or 3+
--          LLM calls (reasoning, generation, tool calls). Verified live the reference org.
--        * nb_roundtrips   = COUNT(DISTINCT AiAgentInteractionId__c) = actual
--          user questions (one round-trip = one AiAgentInteractionId, whatever
--          the number of internal LLM calls). This is the Coworker billing unit
--          (72 FC / round-trip). See queries/02.
-- =====================================================================

SELECT
    u."ssot__FullName__c"                         AS user_name,
    u."ssot__Username__c"                         AS username,
    a."GenAiGatewayFeatureName__c"                AS feature,
    SUM(a."PromptTotalTokenCount__c")             AS total_tokens,
    SUM(a."PromptInputTokenCount__c")             AS input_tokens,
    SUM(a."PromptCompletionTokenCount__c")        AS completion_tokens,
    COUNT(*)                                      AS nb_interactions,
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
