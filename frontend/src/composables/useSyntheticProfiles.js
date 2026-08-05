/**
 * Composable for managing synthetic profiles
 * Handles profile loading, selection, and group interactions
 */

import { ref, computed } from 'vue';
import { getSimulationProfilesRealtime, askSyntheticProfiles, exportGeneratedResponsesCSV } from '../api/simulation';

export function useSyntheticProfiles(simulationId) {
  const profiles = ref([]);
  const profileLoadState = ref('loading');
  const selectedAgents = ref(new Set());
  const groupQuestion = ref('');
  const groupResponses = ref([]);
  const isAskingGroup = ref(false);
  const groupError = ref('');
  const isExporting = ref(false);
  const bypassPromptOpt = ref(false);

  const profileName = (profile, index) =>
    profile?.username ||
    profile?.name ||
    `Fictional profile ${Number(index ?? 0) + 1}`;

  const profileRole = (profile) =>
    profile?.profession || profile?.bio || 'Generated character brief';

  async function loadProfiles() {
    profileLoadState.value = 'loading';
    
    try {
      const response = await getSimulationProfilesRealtime(simulationId.value);
      
      if (response.success) {
        profiles.value = response.data?.profiles || [];
        profileLoadState.value = 'ready';
      } else {
        throw new Error(response.error || 'Failed to load profiles');
      }
    } catch (error) {
      console.error('Profile loading error:', error);
      profileLoadState.value = 'error';
      throw error;
    }
  }

  function toggleAgentSelection(profileIndex) {
    const selection = new Set(selectedAgents.value);
    if (selection.has(profileIndex)) {
      selection.delete(profileIndex);
    } else {
      selection.add(profileIndex);
    }
    selectedAgents.value = selection;
  }

  function selectAllAgents() {
    selectedAgents.value = new Set(profiles.value.map((_, index) => index));
  }

  function clearAgentSelection() {
    selectedAgents.value = new Set();
  }

  async function askSelectedProfiles(question) {
    if (!question.trim() || selectedAgents.value.size === 0) return;

    isAskingGroup.value = true;
    groupError.value = '';
    groupResponses.value = [];

    try {
      const questions = Array.from(selectedAgents.value).map((index) => ({
        agent_id: index,
        prompt: question,
      }));

      const response = await askSyntheticProfiles({
        simulation_id: simulationId.value,
        questions,
        bypass_prompt_optimization: bypassPromptOpt.value,
      });

      if (response.success) {
        const results = response.data?.result?.results || {};
        groupResponses.value = Array.from(selectedAgents.value).map((index) => {
          const profile = profiles.value[index];
          const platformKey = Object.keys(results).find(
            (key) => key.endsWith(`_${index}`)
          );
          const responseData = platformKey ? results[platformKey] : null;

          return {
            profile: {
              name: profileName(profile, index),
              role: profileRole(profile),
              original: profile,
            },
            response: responseData?.response || 'No response generated.',
            confidence: responseData?.confidence || null,
          };
        });
        
        groupQuestion.value = '';
      } else {
        throw new Error(response.error || 'Failed to get group responses');
      }
    } catch (error) {
      console.error('Group question error:', error);
      groupError.value = error.message || 'Failed to get responses from the group.';
      throw error;
    } finally {
      isAskingGroup.value = false;
    }
  }

  async function exportProfilesToCSV() {
    if (profiles.value.length === 0) return;

    isExporting.value = true;

    try {
      const response = await exportGeneratedResponsesCSV(simulationId.value);
      
      if (response.success) {
        const blob = new Blob([response.data], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `fictional_profiles_${simulationId.value}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } else {
        throw new Error(response.error || 'Failed to export profiles');
      }
    } catch (error) {
      console.error('Export error:', error);
      throw error;
    } finally {
      isExporting.value = false;
    }
  }

  return {
    profiles,
    profileLoadState,
    selectedAgents,
    groupQuestion,
    groupResponses,
    isAskingGroup,
    groupError,
    isExporting,
    bypassPromptOpt,
    profileName,
    profileRole,
    loadProfiles,
    toggleAgentSelection,
    selectAllAgents,
    clearAgentSelection,
    askSelectedProfiles,
    exportProfilesToCSV,
  };
}
