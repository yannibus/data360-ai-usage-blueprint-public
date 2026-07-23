-- =====================================================================
-- Requête 1 — Usage AI par utilisateur
-- =====================================================================
-- Objectif : qui utilise quelle fonctionnalité AI, et à quel volume.
-- Où        : Data Cloud > Query Editor. Coller, puis Run.
-- =====================================================================
SELECT
    u."ssot__FullName__c"                         AS utilisateur,
    u."ssot__Username__c"                         AS identifiant,
    a."GenAiGatewayFeatureName__c"                AS fonctionnalite,
    SUM(a."PromptTotalTokenCount__c")             AS total_tokens,
    SUM(a."PromptInputTokenCount__c")             AS tokens_entree,
    SUM(a."PromptCompletionTokenCount__c")        AS tokens_sortie,
    COUNT(*)                                      AS nb_appels,
    COUNT(DISTINCT a."AiAgentInteractionId__c")   AS nb_aller_retours
FROM "AiAgentGenerativeAiUsage_std__dlm" a
JOIN "ssot__User__dlm" u
    ON a."UserId__c" = u."ssot__Id__c"
GROUP BY
    u."ssot__FullName__c",
    u."ssot__Username__c",
    a."GenAiGatewayFeatureName__c"
ORDER BY total_tokens DESC
LIMIT 50;
