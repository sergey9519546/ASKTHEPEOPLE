/**
 * Composable for managing workspace loading state
 * Handles coordinated loading of report, profiles, and run status
 * with error recovery and warning aggregation
 */

import { ref, reactive } from 'vue';
import { getReport, getAgentLog } from '../api/report';
import { getSimulationProfilesRealtime } from '../api/simulation';

export function useWorkspaceLoader(reportId, simulationId, pollStatusFn, addLogFn) {
  const workspaceLoadState = ref('loading');
  const workspaceLoadError = ref('');
  const loadWarnings = ref([]);
  const reportContextLoadState = ref('loading');
  const profileLoadState = ref('loading');
  const runStatusLoadState = ref('loading');
  const isRetryingWorkspace = ref(false);
  
  let loadRequestId = 0;
  let activeContextKey = '';

  const settledSuccessfully = (result) =>
    result.status === 'fulfilled' && result.value?.success !== false;

  async function loadData({ retry = false } = {}) {
    const requestId = ++loadRequestId;
    const contextKey = `${reportId.value || ''}:${simulationId.value || ''}`;
    
    if (contextKey !== activeContextKey) {
      activeContextKey = contextKey;
      resetForNewContext();
    }

    workspaceLoadState.value = 'loading';
    workspaceLoadError.value = '';
    loadWarnings.value = [];
    reportContextLoadState.value = 'loading';
    profileLoadState.value = 'loading';
    runStatusLoadState.value = 'loading';
    
    if (retry) {
      isRetryingWorkspace.value = true;
    }

    if (!reportId.value || !simulationId.value) {
      workspaceLoadState.value = 'error';
      workspaceLoadError.value =
        'This link is missing the report or run identifier needed to open follow-up tools.';
      reportContextLoadState.value = 'error';
      profileLoadState.value = 'error';
      runStatusLoadState.value = 'error';
      isRetryingWorkspace.value = false;
      return;
    }

    const [reportResult, logResult, profileResult] = await Promise.allSettled([
      getReport(reportId.value),
      getAgentLog(reportId.value, 0),
      getSimulationProfilesRealtime(simulationId.value, 'reddit'),
    ]);

    if (requestId !== loadRequestId) return;

    const reportLoaded = settledSuccessfully(reportResult);
    const logsLoaded = settledSuccessfully(logResult);
    const profilesLoaded = settledSuccessfully(profileResult);
    const warnings = [];

    if (reportLoaded) {
      applyReportDocument(reportResult.value?.data ?? reportResult.value);
    }
    if (logsLoaded) {
      applyAgentLogs(logResult.value);
    }
    if (reportLoaded || logsLoaded) {
      reportContextLoadState.value = 'ready';
    } else {
      reportContextLoadState.value = 'error';
      warnings.push('Report context is disconnected.');
    }

    if (profilesLoaded) {
      // Profiles will be handled by useSyntheticProfiles
      profileLoadState.value = 'ready';
    } else {
      profileLoadState.value = 'error';
      warnings.push('Fictional profile briefs are disconnected.');
    }

    const runStatusLoaded = await pollStatusFn();
    if (requestId !== loadRequestId) return;

    if (!reportLoaded && !logsLoaded && !profilesLoaded && !runStatusLoaded) {
      workspaceLoadState.value = 'error';
      workspaceLoadError.value =
        'The report, fictional profile briefs, and live run status are all disconnected. Check the connection and try again.';
      if (addLogFn) {
        addLogFn('The follow-up workspace could not open its run context.');
      }
    } else {
      workspaceLoadState.value = 'ready';
      loadWarnings.value = warnings;
    }

    if (requestId === loadRequestId) {
      isRetryingWorkspace.value = false;
    }
  }

  function resetForNewContext() {
    workspaceLoadState.value = 'loading';
    workspaceLoadError.value = '';
    loadWarnings.value = [];
    reportContextLoadState.value = 'loading';
    profileLoadState.value = 'loading';
    runStatusLoadState.value = 'loading';
  }

  function applyReportDocument(reportData) {
    // To be implemented by parent component based on specific needs
    console.log('Report loaded:', reportData);
  }

  function applyAgentLogs(logData) {
    // To be implemented by parent component based on specific needs
    console.log('Agent logs loaded:', logData);
  }

  function retryWorkspaceLoad() {
    loadData({ retry: true });
  }

  return {
    workspaceLoadState,
    workspaceLoadError,
    loadWarnings,
    reportContextLoadState,
    profileLoadState,
    runStatusLoadState,
    isRetryingWorkspace,
    loadData,
    retryWorkspaceLoad,
    resetForNewContext,
  };
}
