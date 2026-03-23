<template>
  <div class="simulation-panel">
    <!-- Top Control Bar -->
    <div class="control-bar">
      <div class="status-group">
        <!-- Twitter/Info Plaza Platform Status -->
        <div
          class="platform-status twitter"
          :class="{
            active: runStatus.twitter_running,
            completed: runStatus.twitter_completed,
          }"
        >
          <div class="platform-header">
            <svg
              class="platform-icon"
              viewBox="0 0 24 24"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="2" y1="12" x2="22" y2="12"></line>
              <path
                d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
              ></path>
            </svg>
            <span class="platform-name">Info Plaza (X)</span>
            <span v-if="runStatus.twitter_completed" class="status-badge">
              <svg
                viewBox="0 0 24 24"
                width="12"
                height="12"
                fill="none"
                stroke="currentColor"
                stroke-width="3"
              >
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </span>
          </div>
          <div class="platform-stats">
            <span class="stat">
              <span class="stat-label">ROUND</span>
              <span class="stat-value mono"
                >{{ runStatus.twitter_current_round || 0
                }}<span class="stat-total"
                  >/{{ runStatus.total_rounds || maxRounds || "-" }}</span
                ></span
              >
            </span>
            <span class="stat">
              <span class="stat-label">Elapsed Time</span>
              <span class="stat-value mono">{{ twitterElapsedTime }}</span>
            </span>
            <span class="stat">
              <span class="stat-label">ACTS</span>
              <span class="stat-value mono">{{
                runStatus.twitter_actions_count || 0
              }}</span>
            </span>
          </div>
          <!-- Available Actions Tooltip -->
          <div class="actions-tooltip">
            <div class="tooltip-title">Available Actions</div>
            <div class="tooltip-actions">
              <span class="tooltip-action">POST</span>
              <span class="tooltip-action">LIKE</span>
              <span class="tooltip-action">REPOST</span>
              <span class="tooltip-action">QUOTE</span>
              <span class="tooltip-action">FOLLOW</span>
              <span class="tooltip-action">IDLE</span>
            </div>
          </div>
        </div>

        <!-- Reddit/Topic Community Platform Status -->
        <div
          class="platform-status reddit"
          :class="{
            active: runStatus.reddit_running,
            completed: runStatus.reddit_completed,
          }"
        >
          <div class="platform-header">
            <svg
              class="platform-icon"
              viewBox="0 0 24 24"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
              ></path>
            </svg>
            <span class="platform-name">Topic Community (Reddit)</span>
            <span v-if="runStatus.reddit_completed" class="status-badge">
              <svg
                viewBox="0 0 24 24"
                width="12"
                height="12"
                fill="none"
                stroke="currentColor"
                stroke-width="3"
              >
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </span>
          </div>
          <div class="platform-stats">
            <span class="stat">
              <span class="stat-label">ROUND</span>
              <span class="stat-value mono"
                >{{ runStatus.reddit_current_round || 0
                }}<span class="stat-total"
                  >/{{ runStatus.total_rounds || maxRounds || "-" }}</span
                ></span
              >
            </span>
            <span class="stat">
              <span class="stat-label">Elapsed Time</span>
              <span class="stat-value mono">{{ redditElapsedTime }}</span>
            </span>
            <span class="stat">
              <span class="stat-label">ACTS</span>
              <span class="stat-value mono">{{
                runStatus.reddit_actions_count || 0
              }}</span>
            </span>
          </div>
          <!-- Available Actions Tooltip -->
          <div class="actions-tooltip">
            <div class="tooltip-title">Available Actions</div>
            <div class="tooltip-actions">
              <span class="tooltip-action">POST</span>
              <span class="tooltip-action">COMMENT</span>
              <span class="tooltip-action">LIKE</span>
              <span class="tooltip-action">DISLIKE</span>
              <span class="tooltip-action">SEARCH</span>
              <span class="tooltip-action">TREND</span>
              <span class="tooltip-action">FOLLOW</span>
              <span class="tooltip-action">MUTE</span>
              <span class="tooltip-action">REFRESH</span>
              <span class="tooltip-action">IDLE</span>
            </div>
          </div>
        </div>
      </div>

      <div class="action-controls">
        <button
          class="final-action-btn"
          :disabled="!canGenerateReport || isGeneratingReport"
          @click="handleNextStep"
        >
          <span v-if="isGeneratingReport" class="spinner-sm"></span>
          {{
            isGeneratingReport
              ? "GENERATING REPORT..."
              : "GENERATE CONVERSION REPORT ➝"
          }}
        </button>
      </div>
    </div>

    <!-- Preflight / Diagnostics Strip -->
    <div
      class="contract-strip"
      v-if="preflight || diagnostics || diagnosticsError"
    >
      <div
        class="contract-card"
        :class="preflight?.status === 'failed' ? 'contract-failed' : 'contract-ok'"
      >
        <span class="contract-label">Preflight</span>
        <span class="contract-value">{{ preflight?.status || "loading" }}</span>
        <span class="contract-meta" v-if="preflight">
          {{ preflight.failed_checks?.length || 0 }} FAILED CHECKS
        </span>
      </div>

      <div class="contract-card" v-if="diagnostics">
        <span class="contract-label">Canonical Agents</span>
        <span class="contract-value">{{
          diagnostics.canonical_agents?.length || 0
        }}</span>
        <span class="contract-meta">
          {{ diagnostics.entity_type_registry?.length || 0 }} NORMALIZED ROLES
        </span>
      </div>

      <div class="contract-card" v-if="diagnostics">
        <span class="contract-label">Bootstrap Graph</span>
        <span class="contract-value">{{
          diagnostics.relationship_bootstrap?.length || 0
        }}</span>
        <span class="contract-meta">RELATIONSHIP SEEDS Loaded</span>
      </div>

      <div class="contract-card" v-if="diagnostics?.model_resolution?.actor">
        <span class="contract-label">Actor Model</span>
        <span class="contract-value">{{
          diagnostics.model_resolution.actor.model_name || "unknown"
        }}</span>
        <span class="contract-meta">
          {{ diagnostics.model_resolution.actor.provider_mode || "unknown" }}
        </span>
      </div>

      <div class="contract-card contract-error" v-if="diagnosticsError">
        <span class="contract-label">Diagnostics</span>
        <span class="contract-value">UNAVAILABLE</span>
        <span class="contract-meta">{{ diagnosticsError }}</span>
      </div>
    </div>

    <!-- Main Content: Dual Timeline -->
    <div class="main-content-area" ref="scrollContainer">
      <!-- Timeline Header -->
      <div class="timeline-header" v-if="allActions.length > 0">
        <div class="timeline-stats">
          <span class="total-count"
            >TOTAL EVENTS: <span class="mono">{{ allActions.length }}</span></span
          >
          <span class="platform-breakdown">
            <span class="breakdown-item twitter">
              <svg
                class="mini-icon"
                viewBox="0 0 24 24"
                width="12"
                height="12"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="2" y1="12" x2="22" y2="12"></line>
                <path
                  d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
                ></path>
              </svg>
              <span class="mono">{{ twitterActionsCount }}</span>
            </span>
            <span class="breakdown-divider">/</span>
            <span class="breakdown-item reddit">
              <svg
                class="mini-icon"
                viewBox="0 0 24 24"
                width="12"
                height="12"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
                ></path>
              </svg>
              <span class="mono">{{ redditActionsCount }}</span>
            </span>
          </span>
        </div>
      </div>

      <!-- Timeline Feed -->
      <div class="timeline-feed">
        <div class="timeline-axis"></div>

        <TransitionGroup name="timeline-item">
          <div
            v-for="action in chronologicalActions"
            :key="
              action._uniqueId ||
              action.id ||
              `${action.timestamp}-${action.agent_id}`
            "
            class="timeline-item-wrapper"
            :class="action.platform"
          >
            <div class="timeline-marker">
              <div class="marker-dot"></div>
            </div>

            <div class="timeline-card">
              <div class="card-header">
                <div class="agent-info">
                  <div class="avatar-placeholder">
                    {{ (action.agent_name || "A")[0] }}
                  </div>
                  <span class="agent-name">{{ action.agent_name }}</span>
                </div>

                <div class="header-meta">
                  <div class="platform-indicator">
                    <svg
                      v-if="action.platform === 'twitter'"
                      viewBox="0 0 24 24"
                      width="12"
                      height="12"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <circle cx="12" cy="12" r="10"></circle>
                      <line x1="2" y1="12" x2="22" y2="12"></line>
                      <path
                        d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
                      ></path>
                    </svg>
                    <svg
                      v-else
                      viewBox="0 0 24 24"
                      width="12"
                      height="12"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
                      ></path>
                    </svg>
                  </div>
                  <div
                    class="action-badge"
                    :class="getActionTypeClass(action.action_type)"
                  >
                    {{ getActionTypeLabel(action.action_type) }}
                  </div>
                </div>
              </div>

              <div class="card-body">
                <!-- CREATE_POST -->
                <div
                  v-if="
                    action.action_type === 'CREATE_POST' &&
                    action.action_args?.content
                  "
                  class="content-text main-text"
                >
                  {{ action.action_args.content }}
                </div>

                <!-- QUOTE_POST -->
                <template v-if="action.action_type === 'QUOTE_POST'">
                  <div
                    v-if="action.action_args?.quote_content"
                    class="content-text"
                  >
                    {{ action.action_args.quote_content }}
                  </div>
                  <div
                    v-if="action.action_args?.original_content"
                    class="quoted-block"
                  >
                    <div class="quote-header">
                      <svg
                        class="icon-small"
                        viewBox="0 0 24 24"
                        width="12"
                        height="12"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                      >
                        <path
                          d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"
                        ></path>
                        <path
                          d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"
                        ></path>
                      </svg>
                      <span class="quote-label"
                        >@{{
                          action.action_args.original_author_name || "User"
                        }}</span
                      >
                    </div>
                    <div class="quote-text">
                      {{
                        truncateContent(action.action_args.original_content, 150)
                      }}
                    </div>
                  </div>
                </template>

                <!-- REPOST -->
                <template v-if="action.action_type === 'REPOST'">
                  <div class="repost-info">
                    <svg
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <polyline points="17 1 21 5 17 9"></polyline>
                      <path d="M3 11V9a4 4 0 0 1 4-4h14"></path>
                      <polyline points="7 23 3 19 7 15"></polyline>
                      <path d="M21 13v2a4 4 0 0 1-4 4H3"></path>
                    </svg>
                    <span class="repost-label"
                      >Reposted from @{{
                        action.action_args?.original_author_name || "User"
                      }}</span
                    >
                  </div>
                  <div
                    v-if="action.action_args?.original_content"
                    class="repost-content"
                  >
                    {{
                      truncateContent(action.action_args.original_content, 200)
                    }}
                  </div>
                </template>

                <!-- LIKE_POST -->
                <template v-if="action.action_type === 'LIKE_POST'">
                  <div class="like-info">
                    <svg
                      class="icon-small filled"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="currentColor"
                    >
                      <path
                        d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
                      ></path>
                    </svg>
                    <span class="like-label"
                      >Liked @{{
                        action.action_args?.post_author_name || "User"
                      }}'s post</span
                    >
                  </div>
                  <div
                    v-if="action.action_args?.post_content"
                    class="liked-content"
                  >
                    "{{ truncateContent(action.action_args.post_content, 120) }}"
                  </div>
                </template>

                <!-- CREATE_COMMENT -->
                <template v-if="action.action_type === 'CREATE_COMMENT'">
                  <div v-if="action.action_args?.content" class="content-text">
                    {{ action.action_args.content }}
                  </div>
                  <div v-if="action.action_args?.post_id" class="comment-context">
                    <svg
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="12"
                      height="12"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
                      ></path>
                    </svg>
                    <span>Reply to post #{{ action.action_args.post_id }}</span>
                  </div>
                </template>

                <!-- SEARCH_POSTS -->
                <template v-if="action.action_type === 'SEARCH_POSTS'">
                  <div class="search-info">
                    <svg
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <circle cx="11" cy="11" r="8"></circle>
                      <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                    <span class="search-label">Search Query:</span>
                    <span class="search-query"
                      >"{{ action.action_args?.query || "" }}"</span
                    >
                  </div>
                </template>

                <!-- FOLLOW -->
                <template v-if="action.action_type === 'FOLLOW'">
                  <div class="follow-info">
                    <svg
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"
                      ></path>
                      <circle cx="8.5" cy="7" r="4"></circle>
                      <line x1="20" y1="8" x2="20" y2="14"></line>
                      <line x1="23" y1="11" x2="17" y2="11"></line>
                    </svg>
                    <span class="follow-label"
                      >Followed @{{
                        action.action_args?.target_user ||
                        action.action_args?.user_id ||
                        "User"
                      }}</span
                    >
                  </div>
                </template>

                <!-- UPVOTE / DOWNVOTE -->
                <template
                  v-if="
                    action.action_type === 'UPVOTE_POST' ||
                    action.action_type === 'DOWNVOTE_POST'
                  "
                >
                  <div class="vote-info">
                    <svg
                      v-if="action.action_type === 'UPVOTE_POST'"
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <polyline points="18 15 12 9 6 15"></polyline>
                    </svg>
                    <svg
                      v-else
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                    <span class="vote-label"
                      >{{
                        action.action_type === "UPVOTE_POST"
                          ? "Upvoted"
                          : "Downvoted"
                      }}
                      Post</span
                    >
                  </div>
                  <div
                    v-if="action.action_args?.post_content"
                    class="voted-content"
                  >
                    "{{ truncateContent(action.action_args.post_content, 120) }}"
                  </div>
                </template>

                <!-- DO_NOTHING -->
                <template v-if="action.action_type === 'DO_NOTHING'">
                  <div class="idle-info">
                    <svg
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <circle cx="12" cy="12" r="10"></circle>
                      <line x1="12" y1="8" x2="12" y2="12"></line>
                      <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    <span class="idle-label">Action Skipped (Idle)</span>
                  </div>
                </template>

                <!-- Unknown fallback -->
                <div
                  v-if="
                    ![
                      'CREATE_POST',
                      'QUOTE_POST',
                      'REPOST',
                      'LIKE_POST',
                      'CREATE_COMMENT',
                      'SEARCH_POSTS',
                      'FOLLOW',
                      'UPVOTE_POST',
                      'DOWNVOTE_POST',
                      'DO_NOTHING',
                    ].includes(action.action_type) && action.action_args?.content
                  "
                  class="content-text"
                >
                  {{ action.action_args.content }}
                </div>
              </div>

              <div class="card-footer">
                <span class="time-tag"
                  >ROUND {{ action.round_num }} •
                  {{ formatActionTime(action.timestamp) }}</span
                >
              </div>
            </div>
          </div>
        </TransitionGroup>

        <div v-if="allActions.length === 0" class="waiting-state">
          <div class="spinner-sm"></div>
          <span>Synchronizing simulation nodes...</span>
        </div>
      </div>
    </div>

    <!-- Bottom Info / Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span class="log-title">SIMULATION MONITOR</span>
        <span class="log-id">{{ simulationId || "NO_SIMULATION" }}</span>
      </div>
      <div class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import { useRouter } from "vue-router";
import {
  startSimulation,
  stopSimulation,
  getRunStatus,
  getRunStatusDetail,
  getSimulationDiagnostics,
  getSimulationPreflight,
} from "../api/simulation";
import { generateReport } from "../api/report";

const props = defineProps({
  simulationId: String,
  maxRounds: Number,
  minutesPerRound: {
    type: Number,
    default: 15, // Updated default to 15m/round for precision
  },
  projectData: Object,
  graphData: Object,
  systemLogs: Array,
});

const emit = defineEmits(["go-back", "next-step", "add-log", "update-status"]);
const router = useRouter();

// State
const isGeneratingReport = ref(false);
const phase = ref(0); // 0: Idle, 1: Running, 2: Completed
const isStarting = ref(false);
const isStopping = ref(false);
const startError = ref(null);
const runStatus = ref({});
const allActions = ref([]);
const actionIds = ref(new Set());
const scrollContainer = ref(null);
const preflight = ref(null);
const diagnostics = ref(null);
const diagnosticsError = ref(null);

const chronologicalActions = computed(() => {
  return allActions.value;
});

const twitterActionsCount = computed(() => {
  return allActions.value.filter((a) => a.platform === "twitter").length;
});

const redditActionsCount = computed(() => {
  return allActions.value.filter((a) => a.platform === "reddit").length;
});

const formatElapsedTime = (currentRound) => {
  if (!currentRound || currentRound <= 0) return "0h 0m";
  const totalMinutes = currentRound * props.minutesPerRound;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours}h ${minutes}m`;
};

const twitterElapsedTime = computed(() => {
  return formatElapsedTime(runStatus.value.twitter_current_round || 0);
});

const redditElapsedTime = computed(() => {
  return formatElapsedTime(runStatus.value.reddit_current_round || 0);
});

const canGenerateReport = computed(() => {
  return phase.value === 2 && runStatus.value.runner_status !== "interrupted";
});

const addLog = (msg) => {
  emit("add-log", msg);
};

const fetchExecutionContracts = async () => {
  if (!props.simulationId) return;

  diagnosticsError.value = null;
  try {
    const [preflightRes, diagnosticsRes] = await Promise.all([
      getSimulationPreflight(props.simulationId),
      getSimulationDiagnostics(props.simulationId),
    ]);

    if (preflightRes.success) {
      preflight.value = preflightRes.data;
    }

    if (diagnosticsRes.success) {
      diagnostics.value = diagnosticsRes.data;
    } else {
      diagnosticsError.value =
        diagnosticsRes.error || "failed to load diagnostics";
    }
  } catch (err) {
    diagnosticsError.value = err.message || "failed to load diagnostics";
  }
};

const resetAllState = () => {
  phase.value = 0;
  runStatus.value = {};
  allActions.value = [];
  actionIds.value = new Set();
  prevTwitterRound.value = 0;
  prevRedditRound.value = 0;
  startError.value = null;
  isStarting.value = false;
  isStopping.value = false;
  stopPolling();
};

const doStartSimulation = async () => {
  if (!props.simulationId) {
    addLog("Error: Missing simulationId");
    return;
  }

  resetAllState();
  isStarting.value = true;
  startError.value = null;
  addLog("Initiating dual-platform parallel simulation engine...");
  emit("update-status", "processing");

  try {
    const params = {
      simulation_id: props.simulationId,
      platform: "parallel",
      force: true,
      enable_graph_memory_update: true,
    };

    if (props.maxRounds) {
      params.max_rounds = props.maxRounds;
      addLog(`Setting temporal depth: ${props.maxRounds} rounds`);
    }

    const res = await startSimulation(params);

    if (res.success && res.data) {
      if (res.data.force_restarted) {
        addLog("✓ Flushed legacy logs, restarting from seed state");
      }
      addLog("✓ Simulation engine initiated successfully");
      addLog(`  └─ Engine PID: ${res.data.process_pid || "-"}`);

      phase.value = 1;
      runStatus.value = res.data;

      startStatusPolling();
      startDetailPolling();
    } else {
      startError.value = res.error || "failed to start";
      addLog(`✗ Initiation failed: ${res.error || "unknown error"}`);
      emit("update-status", "error");
    }
  } catch (err) {
    startError.value = err.message;
    addLog(`✗ Initiation exception: ${err.message}`);
    emit("update-status", "error");
  } finally {
    isStarting.value = false;
  }
};

let statusTimer = null;
let detailTimer = null;

const startStatusPolling = () => {
  statusTimer = setInterval(fetchRunStatus, 2000);
};

const startDetailPolling = () => {
  detailTimer = setInterval(fetchRunStatusDetail, 3000);
};

const stopPolling = () => {
  if (statusTimer) {
    clearInterval(statusTimer);
    statusTimer = null;
  }
  if (detailTimer) {
    clearInterval(detailTimer);
    detailTimer = null;
  }
};

const prevTwitterRound = ref(0);
const prevRedditRound = ref(0);

const fetchRunStatus = async () => {
  if (!props.simulationId) return;

  try {
    const res = await getRunStatus(props.simulationId);

    if (res.success && res.data) {
      const data = res.data;
      runStatus.value = data;

      if (data.runner_status === "interrupted") {
        addLog(`Simulation Interrupted: ${data.error || "runtime failure"}`);
        phase.value = 2;
        stopPolling();
        emit("update-status", "error");
        return;
      }

      if (data.twitter_current_round > prevTwitterRound.value) {
        addLog(
          `[PLAZA] R${data.twitter_current_round}/${data.total_rounds} | T:${data.twitter_simulated_hours || 0}h | A:${data.twitter_actions_count}`,
        );
        prevTwitterRound.value = data.twitter_current_round;
      }

      if (data.reddit_current_round > prevRedditRound.value) {
        addLog(
          `[COMMUNITY] R${data.reddit_current_round}/${data.total_rounds} | T:${data.reddit_simulated_hours || 0}h | A:${data.reddit_actions_count}`,
        );
        prevRedditRound.value = data.reddit_current_round;
      }

      const isCompleted =
        data.runner_status === "completed" || data.runner_status === "stopped";
      const platformsCompleted = checkPlatformsCompleted(data);

      if (isCompleted || platformsCompleted) {
        addLog("✓ Simulation cycle complete");
        phase.value = 2;
        stopPolling();
        emit("update-status", "completed");
      }
    }
  } catch (err) {
    console.warn("Run status poll failed:", err);
  }
};

const checkPlatformsCompleted = (data) => {
  if (!data) return false;
  const twitterCompleted = data.twitter_completed === true;
  const redditCompleted = data.reddit_completed === true;
  const twitterEnabled =
    data.twitter_actions_count > 0 || data.twitter_running || twitterCompleted;
  const redditEnabled =
    data.reddit_actions_count > 0 || data.reddit_running || redditCompleted;
  if (!twitterEnabled && !redditEnabled) return false;
  if (twitterEnabled && !twitterCompleted) return false;
  if (redditEnabled && !redditCompleted) return false;
  return true;
};

const fetchRunStatusDetail = async () => {
  if (!props.simulationId) return;

  try {
    const res = await getRunStatusDetail(props.simulationId);

    if (res.success && res.data) {
      const serverActions = res.data.all_actions || [];
      serverActions.forEach((action) => {
        const actionId =
          action.id ||
          `${action.timestamp}-${action.platform}-${action.agent_id}-${action.action_type}`;
        if (!actionIds.value.has(actionId)) {
          actionIds.value.add(actionId);
          allActions.value.push({
            ...action,
            _uniqueId: actionId,
          });
        }
      });
    }
  } catch (err) {
    console.warn("Detail status poll failed:", err);
  }
};

const getActionTypeLabel = (type) => {
  const labels = {
    CREATE_POST: "POST",
    REPOST: "REPOST",
    LIKE_POST: "LIKE",
    CREATE_COMMENT: "COMMENT",
    LIKE_COMMENT: "LIKE",
    DO_NOTHING: "IDLE",
    FOLLOW: "FOLLOW",
    SEARCH_POSTS: "SEARCH",
    QUOTE_POST: "QUOTE",
    UPVOTE_POST: "UPVOTE",
    DOWNVOTE_POST: "DOWNVOTE",
  };
  return labels[type] || type || "UNKNOWN";
};

const getActionTypeClass = (type) => {
  const classes = {
    CREATE_POST: "badge-post",
    REPOST: "badge-blue",
    LIKE_POST: "badge-red",
    CREATE_COMMENT: "badge-yellow",
    LIKE_COMMENT: "badge-red",
    QUOTE_POST: "badge-post",
    FOLLOW: "badge-black",
    SEARCH_POSTS: "badge-black",
    UPVOTE_POST: "badge-blue",
    DOWNVOTE_POST: "badge-red",
    DO_NOTHING: "badge-idle",
  };
  return classes[type] || "badge-default";
};

const truncateContent = (content, maxLength = 100) => {
  if (!content) return "";
  if (content.length > maxLength) return content.substring(0, maxLength) + "...";
  return content;
};

const formatActionTime = (timestamp) => {
  if (!timestamp) return "";
  try {
    return new Date(timestamp).toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
};

const handleNextStep = async () => {
  if (!props.simulationId) {
    addLog("Error: Missing simulationId");
    return;
  }
  if (isGeneratingReport.value) return;

  isGeneratingReport.value = true;
  addLog("Initiating report synthesis engine...");

  try {
    const res = await generateReport({
      simulation_id: props.simulationId,
      force_regenerate: true,
    });

    if (res.success && res.data) {
      const reportId = res.data.report_id;
      addLog(`✓ Report synthesis task initiated: ${reportId}`);
      router.push({ name: "Report", params: { reportId } });
    } else {
      addLog(`✗ Report synthesis failed: ${res.error || "unknown error"}`);
      isGeneratingReport.value = false;
    }
  } catch (err) {
    addLog(`✗ Report synthesis exception: ${err.message}`);
    isGeneratingReport.value = false;
  }
};

onMounted(() => {
  addLog("Step 3 Simulation Initialized");
  fetchExecutionContracts();
  if (props.simulationId) {
    doStartSimulation();
  }
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.simulation-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--atp-white);
  font-family: var(--font-sans);
  overflow: hidden;
  color: var(--atp-black);
}

/* Control Bar */
.control-bar {
  background: var(--atp-white);
  padding: 24px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: var(--border-width) solid var(--atp-black);
  z-index: 10;
}

.status-group {
  display: flex;
  gap: 24px;
}

.platform-status {
  padding: 16px 24px;
  background: var(--atp-white);
  border: 2px solid var(--atp-black);
  position: relative;
  transition: all 0.2s;
}

.platform-status.twitter {
  border-bottom: 8px solid var(--atp-blue);
}
.platform-status.reddit {
  border-bottom: 8px solid var(--atp-red);
}

.platform-status.active {
  background: var(--atp-yellow);
}

.platform-status.completed {
  background: var(--atp-black);
  color: var(--atp-white);
}

.actions-tooltip {
  position: absolute;
  top: 100%;
  left: 0;
  width: 100%;
  margin-top: 12px;
  padding: 16px;
  background: var(--atp-black);
  color: var(--atp-white);
  border: 2px solid var(--atp-black);
  opacity: 0;
  visibility: hidden;
  z-index: 100;
  pointer-events: none;
}

.platform-status:hover .actions-tooltip {
  opacity: 1;
  visibility: visible;
}

.tooltip-title {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 900;
  color: var(--atp-yellow);
  text-transform: uppercase;
  margin-bottom: 12px;
}

.tooltip-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tooltip-action {
  font-family: var(--font-mono);
  font-size: 10px;
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 6px;
}

.platform-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.platform-name {
  font-weight: 900;
  text-transform: uppercase;
  font-size: 0.85rem;
}

.platform-stats {
  display: flex;
  gap: 24px;
}

.stat {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 10px;
  font-weight: 900;
  opacity: 0.5;
  text-transform: uppercase;
}

.stat-value {
  font-size: 1rem;
  font-weight: 900;
}

.final-action-btn {
  padding: 20px 40px;
  background: var(--atp-black);
  color: var(--atp-white);
  border: var(--border-width) solid var(--atp-black);
  font-weight: 900;
  text-transform: uppercase;
  cursor: pointer;
  font-family: var(--font-mono);
  transition: all 0.1s;
}

.final-action-btn:hover:not(:disabled) {
  background: var(--atp-blue);
  transform: translate(-4px, -4px);
  box-shadow: 6px 6px 0 var(--atp-yellow);
}

.final-action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* Contracts */
.contract-strip {
  display: flex;
  gap: 12px;
  padding: 16px 32px;
  background: #f9f9f9;
  border-bottom: 2px solid var(--atp-black);
}

.contract-card {
  flex: 1;
  padding: 12px 16px;
  background: var(--atp-white);
  border: 2px solid var(--atp-black);
  display: flex;
  flex-direction: column;
}

.contract-label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 900;
  opacity: 0.5;
  text-transform: uppercase;
}

.contract-value {
  font-weight: 900;
  text-transform: uppercase;
  margin: 4px 0;
}

.contract-meta {
  font-size: 10px;
  font-weight: 700;
}

.contract-ok {
  background: var(--atp-white);
}

.contract-failed {
  border-color: var(--atp-red);
  color: var(--atp-red);
}

/* Timeline */
.main-content-area {
  flex: 1;
  overflow-y: auto;
  background: var(--atp-white);
}

.timeline-header {
  padding: 12px 32px;
  border-bottom: 2px solid var(--atp-black);
  position: sticky;
  top: 0;
  background: var(--atp-white);
  z-index: 5;
}

.timeline-stats {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 900;
  text-transform: uppercase;
}

.timeline-feed {
  padding: 40px 32px;
  max-width: 900px;
  margin: 0 auto;
  position: relative;
}

.timeline-axis {
  position: absolute;
  left: 48px;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--atp-black);
}

.timeline-item-wrapper {
  display: flex;
  gap: 32px;
  margin-bottom: 40px;
  position: relative;
}

.timeline-marker {
  width: 32px;
  z-index: 2;
  display: flex;
  justify-content: center;
  padding-top: 10px;
}

.marker-dot {
  width: 16px;
  height: 16px;
  background: var(--atp-white);
  border: 4px solid var(--atp-black);
}

.twitter .marker-dot {
  background: var(--atp-blue);
}
.reddit .marker-dot {
  background: var(--atp-red);
}

.timeline-card {
  flex: 1;
  background: var(--atp-white);
  border: var(--border-width) solid var(--atp-black);
  padding: 32px;
  box-shadow: 10px 10px 0 rgba(0, 0, 0, 0.05);
}

.twitter .timeline-card {
  border-left: 12px solid var(--atp-blue);
}
.reddit .timeline-card {
  border-left: 12px solid var(--atp-red);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  border-bottom: 1px solid #eee;
  padding-bottom: 12px;
}

.agent-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar-placeholder {
  width: 32px;
  height: 32px;
  background: var(--atp-black);
  color: var(--atp-white);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
}

.agent-name {
  font-weight: 900;
  text-transform: uppercase;
}

.action-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 900;
  padding: 4px 12px;
  border: 2px solid var(--atp-black);
  text-transform: uppercase;
}

.badge-post {
  background: var(--atp-yellow);
}
.badge-blue {
  background: var(--atp-blue);
  color: #fff;
}
.badge-red {
  background: var(--atp-red);
  color: #fff;
}
.badge-yellow {
  background: var(--atp-yellow);
}
.badge-black {
  background: var(--atp-black);
  color: #fff;
}

.content-text {
  font-size: 1.1rem;
  line-height: 1.6;
  font-weight: 500;
}

.quoted-block {
  margin-top: 20px;
  padding: 20px;
  border: 2px dashed var(--atp-black);
}

.quote-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 700;
}

.repost-info,
.like-info,
.search-info,
.follow-info,
.vote-info,
.idle-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  font-weight: 700;
  text-transform: uppercase;
  font-size: 0.85rem;
}

.card-footer {
  margin-top: 24px;
  border-top: 1px solid #eee;
  padding-top: 12px;
}

.time-tag {
  font-family: var(--font-mono);
  font-size: 11px;
  opacity: 0.5;
  font-weight: 900;
}

/* Logs */
.system-logs {
  background: #000;
  padding: 40px;
  border-top: var(--border-width) solid var(--atp-black);
  color: #fff;
}

.log-title {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 900;
  color: var(--atp-blue);
  letter-spacing: 4px;
}

.log-content {
  margin-top: 20px;
  height: 120px;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: 12px;
}

/* Animations */
.timeline-item-enter-active {
  transition: all 0.5s ease;
}
.timeline-item-enter-from {
  opacity: 0;
  transform: translateY(30px);
}

.spinner-sm {
  width: 20px;
  height: 20px;
  border: 4px solid rgba(0, 38, 254, 0.2);
  border-top-color: var(--atp-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}

.mono {
  font-family: var(--font-mono);
}
</style>
