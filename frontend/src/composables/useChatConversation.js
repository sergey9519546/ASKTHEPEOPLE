/**
 * Composable for managing chat conversations with AI agents
 * Handles report explanations and fictional profile interactions
 */

import { ref, reactive, computed } from 'vue';
import { chatWithReport } from '../api/report';
import { askSyntheticProfiles } from '../api/simulation';

export function useChatConversation(reportId, simulationId) {
  const isSending = ref(false);
  const chatInput = ref('');
  const chatHistory = ref([]);
  const chatHistoryCache = reactive({});
  const conversationError = ref('');
  const selectedAgent = ref(null);
  const selectedAgentIndex = ref(null);
  const chatTarget = ref('report_agent');
  const bypassPromptOpt = ref(false);

  const conversationHeading = computed(() => {
    if (chatTarget.value === 'report_agent') {
      return 'Ask for an explanation of the report.';
    }
    return selectedAgent.value
      ? `Ask a fictional version of ${selectedAgent.value?.username || selectedAgent.value?.name || `Fictional profile ${Number(selectedAgentIndex.value ?? 0) + 1}`}.`
      : 'Choose a fictional profile to begin.';
  });

  const conversationBoundary = computed(() =>
    chatTarget.value === 'report_agent'
      ? 'This AI explains and challenges the existing synthetic report. It does not add testimony, field research, or real-world validation.'
      : 'Each reply is newly generated in character from a fictional profile brief. It is not something a person said or believes.',
  );

  async function sendMessage(message, profiles = [], agent = null) {
    if (!message.trim()) return;

    isSending.value = true;
    conversationError.value = '';

    try {
      const userMsg = {
        role: 'user',
        content: message,
        timestamp: Date.now(),
      };

      chatHistory.value.push(userMsg);

      let response;
      if (chatTarget.value === 'report_agent') {
        response = await chatWithReport(reportId.value, message);
      } else {
        const targetProfile = agent || selectedAgent.value;
        const profileIndex = agent ? profiles.findIndex(p => p.id === agent.id) : selectedAgentIndex.value;
        response = await askSyntheticProfiles(
          simulationId.value,
          [profileIndex],
          message,
          targetProfile
        );
      }

      const aiMsg = {
        role: 'assistant',
        content: response.message || response.answer || 'No response generated.',
        timestamp: Date.now(),
        metadata: response.metadata || {},
      };

      chatHistory.value.push(aiMsg);
      chatInput.value = '';
      
      return aiMsg;
    } catch (error) {
      console.error('Chat error:', error);
      conversationError.value = error.message || 'Failed to send message';
      
      // Remove the user message if failed
      chatHistory.value.pop();
      
      throw error;
    } finally {
      isSending.value = false;
    }
  }

  function clearConversation() {
    chatHistory.value = [];
    conversationError.value = '';
    chatInput.value = '';
  }

  function setChatTarget(target, agent = null, index = null) {
    chatTarget.value = target;
    selectedAgent.value = agent;
    selectedAgentIndex.value = index;
    
    // Load cached history for this target
    const cacheKey = `${target}_${agent?.id || index || 'report'}`;
    if (chatHistoryCache[cacheKey]) {
      chatHistory.value = [...chatHistoryCache[cacheKey]];
    } else {
      clearConversation();
    }
  }

  function saveToCache() {
    const cacheKey = `${chatTarget.value}_${selectedAgent.value?.id || selectedAgentIndex.value || 'report'}`;
    chatHistoryCache[cacheKey] = [...chatHistory.value];
  }

  // Auto-save on history change
  watch(chatHistory, () => {
    saveToCache();
  }, { deep: true });

  return {
    isSending,
    chatInput,
    chatHistory,
    conversationError,
    selectedAgent,
    selectedAgentIndex,
    chatTarget,
    bypassPromptOpt,
    conversationHeading,
    conversationBoundary,
    sendMessage,
    clearConversation,
    setChatTarget,
  };
}
