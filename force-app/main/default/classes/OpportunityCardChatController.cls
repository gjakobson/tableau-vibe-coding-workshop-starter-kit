public with sharing class OpportunityCardChatController {
    private static final String DEFAULT_MODEL = 'sfdc_ai__DefaultOpenAIGPT4OmniMini';
    private static final String PROMPT_VERSION = 'v2-intent-routed';

    public class ChatResponse {
        @AuraEnabled public String answer;
        @AuraEnabled public String source;
        @AuraEnabled public String modelName;
    }

    @AuraEnabled(cacheable=false)
    public static ChatResponse chatOpportunity(
        String opportunityId,
        String opportunityName,
        String stage,
        Decimal amount,
        Decimal probability,
        String leadSource,
        String nextStep,
        String userQuestion,
        Map<String, Object> request
    ) {
        // Support both invocation styles:
        // 1) flat args from LWC imperative call
        // 2) nested { request: { ... } } payload from older cached bundles
        Map<String, Object> nested = request == null ? new Map<String, Object>() : request;
        opportunityId = firstNonBlank(opportunityId, asString(nested.get('opportunityId')));
        opportunityName = firstNonBlank(opportunityName, asString(nested.get('opportunityName')));
        stage = firstNonBlank(stage, asString(nested.get('stage')));
        amount = amount == null ? asDecimal(nested.get('amount')) : amount;
        probability = probability == null ? asDecimal(nested.get('probability')) : probability;
        leadSource = firstNonBlank(leadSource, asString(nested.get('leadSource')));
        nextStep = firstNonBlank(nextStep, asString(nested.get('nextStep')));
        userQuestion = firstNonBlank(userQuestion, asString(nested.get('userQuestion')));

        String normalizedQuestion = String.isBlank(userQuestion)
            ? '(empty question captured by client)'
            : userQuestion.trim();

        String opportunityContext =
            'Opportunity ID: ' + safe(opportunityId) + '\n' +
            'Opportunity: ' + safe(opportunityName) + '\n' +
            'Stage: ' + safe(stage) + '\n' +
            'Amount: ' + String.valueOf(amount) + '\n' +
            'Probability: ' + String.valueOf(probability) + '%\n' +
            'Lead Source: ' + safe(leadSource) + '\n' +
            'Next Step: ' + safe(nextStep);

        String intent = detectIntent(normalizedQuestion);
        String prompt = buildPromptV2(normalizedQuestion, opportunityContext, intent, probability, stage);

        ChatResponse response = new ChatResponse();
        try {
            aiplatform.ModelsAPI.createGenerations_Request genRequest =
                new aiplatform.ModelsAPI.createGenerations_Request();
            genRequest.modelName = DEFAULT_MODEL;
            genRequest.body = new aiplatform.ModelsAPI_GenerationRequest();
            genRequest.body.prompt = prompt;

            aiplatform.ModelsAPI modelsApi = new aiplatform.ModelsAPI();
            aiplatform.ModelsAPI.createGenerations_Response genResponse =
                modelsApi.createGenerations(genRequest);

            String generatedText =
                genResponse != null &&
                genResponse.Code200 != null &&
                genResponse.Code200.generation != null
                    ? genResponse.Code200.generation.generatedText
                    : null;

            if (String.isBlank(generatedText)) {
                throw new AuraHandledException('Model returned an empty response.');
            }

            response.source = 'models-api-' + PROMPT_VERSION + '-' + intent;
            response.modelName = DEFAULT_MODEL;
            response.answer = generatedText;
        } catch (Exception e) {
            // Keep workshop flow working even if model access is not configured.
            response.source = 'scaffold-fallback';
            response.modelName = DEFAULT_MODEL;
            response.answer =
                'Real model call was unavailable, so fallback response is shown.\n\n' +
                'Reason:\n' + e.getMessage() + '\n\n' +
                'Question:\n' + normalizedQuestion + '\n\n' +
                'Current opportunity context:\n' + opportunityContext + '\n\n' +
                'To enable real answers, confirm this org has Models API access and the model name is available.';
        }
        return response;
    }

    private static String safe(String input) {
        return String.isBlank(input) ? 'N/A' : input;
    }

    private static String asString(Object input) {
        if (input == null) return null;
        return String.valueOf(input);
    }

    private static String firstNonBlank(String primary, String fallback) {
        return String.isBlank(primary) ? fallback : primary;
    }

    private static Decimal asDecimal(Object input) {
        if (input == null) return null;
        try {
            return Decimal.valueOf(String.valueOf(input));
        } catch (Exception e) {
            return null;
        }
    }

    private static String detectIntent(String question) {
        String q = String.valueOf(question).toLowerCase();
        if (q.contains('compare') || q.contains('versus') || q.contains('vs')) return 'comparison';
        if (q.contains('risk') || q.contains('probability') || q.contains('why is')) return 'risk';
        if (q.contains('next') || q.contains('improve') || q.contains('close')) return 'next_steps';
        if (q.contains('summary') || q.contains('recap')) return 'summary';
        return 'general';
    }

    private static String buildPromptV2(
        String question,
        String opportunityContext,
        String intent,
        Decimal probability,
        String stage
    ) {
        String intentInstructions;
        if (intent == 'comparison') {
            intentInstructions =
                'Focus on relative positioning versus typical similar opportunities. ' +
                'Point out what is better/worse and why that matters.';
        } else if (intent == 'risk') {
            intentInstructions =
                'Prioritize root-cause diagnosis. Explain the top 3 drivers lowering win likelihood.';
        } else if (intent == 'next_steps') {
            intentInstructions =
                'Prioritize concrete execution. Give a 7-day action plan with owner-ready steps.';
        } else if (intent == 'summary') {
            intentInstructions =
                'Provide an executive-ready summary with key risks, opportunities, and recommendation.';
        } else {
            intentInstructions =
                'Provide practical deal coaching tailored to the question.';
        }

        return
            'You are an expert enterprise sales coach for an account executive.\n' +
            'Prompt version: ' + PROMPT_VERSION + '\n' +
            'Intent: ' + intent + '\n\n' +
            'Style rules:\n' +
            '- Be specific to the provided opportunity context only.\n' +
            '- Do NOT use generic filler.\n' +
            '- If data is missing, say exactly what is missing and the impact.\n' +
            '- Keep answer under 220 words.\n\n' +
            'Output format (exact headings):\n' +
            'Top Risks:\n' +
            '- 3 bullets max\n' +
            'Confidence Read:\n' +
            '- 2 bullets max, include win-probability interpretation\n' +
            'Next Best Actions (7 days):\n' +
            '- 4 numbered actions, each action-oriented and specific\n\n' +
            'Additional instruction for this intent:\n' + intentInstructions + '\n\n' +
            'Question:\n' + question + '\n\n' +
            'Opportunity context:\n' + opportunityContext + '\n' +
            'Stage hint: ' + safe(stage) + '\n' +
            'Probability hint: ' + String.valueOf(probability) + '%';
    }
}
