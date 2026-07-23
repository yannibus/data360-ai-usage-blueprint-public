-- =====================================================================
-- Requête 2 — Estimation des Flex Credits par utilisateur
-- =====================================================================
-- Objectif : traduire l'usage en une ESTIMATION de Flex Credits, par
--            utilisateur x fonctionnalité, avec le détail facturé / inclus.
-- Où        : Data Cloud > Query Editor. Coller, puis Run.
--
-- Grille tarifaire (indicative) :
--   Action standard       : 20 FC / action
--   Prompt standard/basic :  4 FC / 2000 tokens
--   Agentforce Coworker   : 72 FC / aller-retour (une question utilisateur)
--
-- is_metered : true = usage facturé, false = usage inclus dans la licence.
--
-- ⚠️ ESTIMATION UNIQUEMENT. Le Digital Wallet reste la source de vérité de
--    facturation. Cette requête sert au pilotage de l'ADOPTION, pas à la facture.
-- =====================================================================
SELECT
    u."ssot__FullName__c"                                            AS utilisateur,
    u."ssot__Username__c"                                            AS identifiant,
    a."GenAiGatewayFeatureName__c"                                   AS fonctionnalite,
    a."IsMeteredIndicator__c"                                        AS facture,
    SUM(a."UsageQuantity__c")                                        AS nb_actions,
    COUNT(DISTINCT a."AiAgentInteractionId__c")                      AS nb_aller_retours,
    SUM(a."UsageQuantity__c") * 20                                   AS fc_actions_est,
    SUM(a."PromptTotalTokenCount__c")                                AS total_tokens,
    CEILING(SUM(a."PromptTotalTokenCount__c") / 2000.0) * 4          AS fc_tokens_est,
    -- Coworker est facturé à l'aller-retour (72 FC) ; les autres à l'action + token.
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
    a."GenAiGatewayFeatureName__c",
    a."IsMeteredIndicator__c"
ORDER BY fc_total_est DESC
LIMIT 50;
