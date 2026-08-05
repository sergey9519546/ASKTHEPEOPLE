/**
 * Composable for managing run status polling and simulation controls
 * Handles live status updates, stop functionality, and error recovery
 */

import { ref, computed, onMounted, onUnmounted } from 'vue';
import { getRunStatusDetail, stopSimulation } from '../api/simulation';

export function useRunStatus(simulationId, pollIntervalMs = 5000) {
  const runStatus = ref(null);
  const recentActions = ref([]);
  const isSimRunning = computed(() =>
    ['running', 'starting'].includes(
      String(runStatus.value?.runner_status || '').toLowerCase()
    )
  );
  
  const pollingError = ref('');
  const isReconnecting = ref(false);
  const isStopping = ref(false);
  const confirmingStop = ref(false);
  const runStatusLoadState = ref('loading');
  
  let statusTimer = null;
  let statusPollInFlight = null;

  const runStatusLabel = (status) => {
    const labels = {
      starting: 'Starting',
      running: 'Running',
      completed: 'Complete',
      stopped: 'Stopped',
      failed: 'Needs attention',
      interrupted: 'Interrupted',
    };
    return labels[String(status || '').toLowerCase()] || 'Idle';
  };

  const platformLabel = (platform) =>
    platform === 'reddit' ? 'Topic community' : 'Short-post channel';

  const actionLabel = (action) => {
    const labels = {
      CREATE_POST: 'Created a post',
      CREATE_COMMENT: 'Added a comment',
      LIKE_POST: 'Liked a post',
      LIKE_COMMENT: 'Liked a comment',
      REPOST: 'Shared a post',
      QUOTE_POST: 'Quoted a post',
      FOLLOW: 'Followed a profile',
      SEARCH_POSTS: 'Searched posts',
      UPVOTE_POST: 'Upvoted a post',
      DOWNVOTE_POST: 'Downvoted a post',
      DO_NOTHING: 'Took no action',
    };
    return (
      labels[action] ||
      String(action || 'Recorded an action').replaceAll('_', ' ')
    );
  };

  async function fetchRunStatus() {
    if (statusPollInFlight) return statusPollInFlight;

    try {
      statusPollInFlight = getRunStatusDetail(simulationId.value);
      const response = await statusPollInFlight;
      
      if (response.success) {
        runStatus.value = response.data;
        recentActions.value = (response.data.recent_actions || []).slice(-8);
        pollingError.value = '';
        runStatusLoadState.value = 'ready';
      } else {
        throw new Error(response.error || 'Failed to fetch run status');
      }
    } catch (error) {
      console.error('Run status polling error:', error);
      pollingError.value = error.message || 'Lost connection to run status';
      runStatusLoadState.value = 'error';
    } finally {
      statusPollInFlight = null;
    }
  }

  function startPolling() {
    stopPolling();
    runStatusLoadState.value = 'loading';
    fetchRunStatus();
    statusTimer = setInterval(fetchRunStatus, pollIntervalMs);
  }

  function stopPolling() {
    if (statusTimer) {
      clearInterval(statusTimer);
      statusTimer = null;
    }
  }

  async function reconnectRunStatus() {
    isReconnecting.value = true;
    pollingError.value = '';
    
    try {
      await fetchRunStatus();
      if (!pollingError.value) {
        startPolling();
      }
    } finally {
      isReconnecting.value = false;
    }
  }

  async function handleStopSimulation() {
    if (!simulationId.value) return;

    isStopping.value = true;
    confirmingStop.value = false;

    try {
      const response = await stopSimulation(simulationId.value);
      if (response.success) {
        await fetchRunStatus();
      } else {
        throw new Error(response.error || 'Failed to stop simulation');
      }
    } catch (error) {
      console.error('Stop simulation error:', error);
      throw error;
    } finally {
      isStopping.value = false;
    }
  }

  onMounted(() => {
    startPolling();
  });

  onUnmounted(() => {
    stopPolling();
  });

  return {
    runStatus,
    recentActions,
    isSimRunning,
    pollingError,
    isReconnecting,
    isStopping,
    confirmingStop,
    runStatusLoadState,
    runStatusLabel,
    platformLabel,
    actionLabel,
    startPolling,
    stopPolling,
    reconnectRunStatus,
    handleStopSimulation,
  };
}
