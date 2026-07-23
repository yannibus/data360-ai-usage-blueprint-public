-- =====================================================================
-- Requête 3 — Vue normalisée (usage par jour, prête pour graphiques)
-- =====================================================================
-- Objectif : la vue propre — chaque fonctionnalité distincte, usage sans
--            étiquette relabellisé "Non tagué", et un axe JOUR pour les
--            graphiques temporels.
-- Où        : Data Cloud > Query Editor. Coller, puis Run.
--            Pour isoler Coworker : filtrer fonctionnalite = 'AgentforceCoworker'.
-- =====================================================================
SELECT
    u."ssot__FullName__c"                                           AS utilisateur,
    u."ssot__Username__c"                                           AS identifiant,
    CASE
        WHEN a."GenAiGatewayFeatureName__c" IS NULL
            THEN 'Non tagué (Flows/Custom)'
        ELSE a."GenAiGatewayFeatureName__c"
    END                                                             AS fonctionnalite,
    CAST(a."Timestamp__c" AS DATE)                                  AS jour,
    a."IsMeteredIndicator__c"                                       AS facture,
    SUM(a."PromptTotalTokenCount__c")                               AS total_tokens,
    SUM(a."PromptInputTokenCount__c")                               AS tokens_entree,
    SUM(a."PromptCompletionTokenCount__c")                          AS tokens_sortie,
    COUNT(*)                                                        AS nb_appels,
    COUNT(DISTINCT a."AiAgentInteractionId__c")                     AS nb_aller_retours,
    SUM(a."UsageQuantity__c")                                       AS nb_actions,
    SUM(a."UsageQuantity__c") * 20                                  AS fc_actions_est,
    CEILING(SUM(a."PromptTotalTokenCount__c") / 2000.0) * 4         AS fc_tokens_est,
    CASE
        WHEN a."GenAiGatewayFeatureName__c" = 'AgentforceCoworker'
            THEN COUNT(DISTINCT a."AiAgentInteractionId__c") * 72
        ELSE (SUM(a."UsageQuantity__c") * 20)
             + (CEILING(SUM(a."PromptTotalTokenCount__c") / 2000.0) * 4)
    END                                                             AS fc_total_est
FROM "AiAgentGenerativeAiUsage_std__dlm" a
JOIN "ssot__User__dlm" u
    ON a."UserId__c" = u."ssot__Id__c"
GROUP BY
    u."ssot__FullName__c",
    u."ssot__Username__c",
    CASE
        WHEN a."GenAiGatewayFeatureName__c" IS NULL
            THEN 'Non tagué (Flows/Custom)'
        ELSE a."GenAiGatewayFeatureName__c"
    END,
    CAST(a."Timestamp__c" AS DATE),
    a."IsMeteredIndicator__c"
ORDER BY jour DESC, total_tokens DESC
LIMIT 200;
