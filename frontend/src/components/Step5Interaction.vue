<template>
  <div class="followup-brief">
    <a class="skip-link" href="#followup-main">Skip to follow-up questions</a>

    <header class="followup-masthead">
      <div class="masthead-copy">
        <p class="route-label">
          <span>05</span>
          Ask follow-up questions
        </p>
        <h1>Ask what the report means. Test what it missed.</h1>
        <p>
          Start with an explanation of the report. Fictional profile and group
          responses are separate tools—and never responses from real people.
        </p>
      </div>

      <aside class="truth-stamp" aria-label="Important interpretation limits">
        <span>Scenario exploration only</span>
        <strong>0 human respondents</strong>
        <b>Not a forecast</b>
        <small>Generated answers can be plausible and still be wrong.</small>
      </aside>
    </header>

    <nav class="followup-modes" aria-label="Follow-up question modes">
      <div class="mode-guide" aria-hidden="true">
        <span>Choose a follow-up mode</span>
        <small>Four ways to question the run</small>
      </div>
      <button
        type="button"
        :class="{ active: activeTab === 'chat' && chatTarget === 'report_agent' }"
        :aria-pressed="activeTab === 'chat' && chatTarget === 'report_agent'"
        @click="selectReportAgentChat"
      >
        <span>01</span>
        <strong>Explain the report</strong>
        <small>Interpret the existing synthetic report</small>
      </button>
      <button
        type="button"
        class="fictional-mode"
        :class="{ active: activeTab === 'chat' && chatTarget === 'agent' }"
        :aria-pressed="activeTab === 'chat' && chatTarget === 'agent'"
        @click="selectProfileChat"
      >
        <span>02</span>
        <strong>Ask a fictional profile</strong>
        <small>Generate one in-character response</small>
      </button>
      <button
        type="button"
        class="fictional-mode"
        :class="{ active: activeTab === 'group_responses' }"
        :aria-pressed="activeTab === 'group_responses'"
        @click="selectGroupResponsesTab"
      >
        <span>03</span>
        <strong>Ask a fictional group</strong>
        <small>Compare several generated responses</small>
      </button>
      <button
        type="button"
        :class="{ active: activeTab === 'opinion_map' }"
        :aria-pressed="activeTab === 'opinion_map'"
        @click="selectOpinionMapTab"
      >
        <span>04</span>
        <strong>View the run map</strong>
        <small>Inspect generated interaction patterns</small>
      </button>
    </nav>

    <section
      v-if="workspaceLoadState === 'loading'"
      id="followup-main"
      class="workspace-state is-loading"
      role="status"
      aria-live="polite"
      tabindex="-1"
      data-testid="workspace-loading"
    >
      <div class="workspace-state-copy">
        <span class="workspace-state-index" aria-hidden="true">05</span>
        <div>
          <p>Opening the follow-up workspace</p>
          <h2>Connecting the report, profile briefs, and run status.</h2>
          <small>Nothing is being treated as empty while these records load.</small>
        </div>
      </div>
      <div class="workspace-state-route" aria-hidden="true">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </section>

    <section
      v-else-if="workspaceLoadState === 'error'"
      id="followup-main"
      class="workspace-state is-error"
      role="alert"
      tabindex="-1"
      data-testid="workspace-load-error"
    >
      <div class="workspace-state-copy">
        <span class="workspace-state-index" aria-hidden="true">!</span>
        <div>
          <p>Follow-up workspace needs attention</p>
          <h2>The run context could not be opened.</h2>
          <small>{{ workspaceLoadError }}</small>
        </div>
      </div>
      <button
        type="button"
        :disabled="isRetryingWorkspace"
        @click="retryWorkspaceLoad"
      >
        {{ isRetryingWorkspace ? "Retrying…" : "Retry workspace connection" }}
      </button>
    </section>

    <section
      v-else-if="loadWarnings.length > 0"
      class="workspace-state is-warning"
      role="status"
      aria-live="polite"
      data-testid="workspace-load-warning"
    >
      <div class="workspace-state-copy">
        <span class="workspace-state-index" aria-hidden="true">!</span>
        <div>
          <p>Some run context is unavailable</p>
          <h2>Available tools remain open; missing records are marked.</h2>
          <ul>
            <li v-for="warning in loadWarnings" :key="warning">
              {{ warning }}
            </li>
          </ul>
        </div>
      </div>
      <button
        type="button"
        :disabled="isRetryingWorkspace"
        @click="retryWorkspaceLoad"
      >
        {{ isRetryingWorkspace ? "Retrying…" : "Retry missing records" }}
      </button>
    </section>

    <section
      v-if="workspaceLoadState === 'ready' && pollingError"
      class="connection-state"
      role="alert"
      data-testid="run-status-disconnected"
    >
      <div>
        <p>Live run updates disconnected</p>
        <span>{{ pollingError }}</span>
      </div>
      <button
        type="button"
        :disabled="isReconnecting"
        @click="reconnectRunStatus"
      >
        {{ isReconnecting ? "Reconnecting…" : "Reconnect live updates" }}
      </button>
    </section>

    <section
      v-if="workspaceLoadState === 'ready' && isSimRunning"
      class="run-live-note"
      aria-live="polite"
    >
      <div>
        <strong>The scenario run is still active.</strong>
        <span>
          Follow-up answers may change as more generated actions are recorded.
        </span>
      </div>
      <div class="stop-controls">
        <button
          type="button"
          class="stop-run"
          :disabled="isStopping"
          @click="
            confirmingStop
              ? handleStopSimulation()
              : (confirmingStop = true)
          "
        >
          {{
            isStopping
              ? "Stopping…"
              : confirmingStop
                ? "Confirm stop"
                : "Stop the run"
          }}
        </button>
        <button
          v-if="confirmingStop && !isStopping"
          type="button"
          class="keep-running"
          @click="confirmingStop = false"
        >
          Keep running
        </button>
      </div>
      <p v-if="stopError" class="inline-error" role="alert">{{ stopError }}</p>
    </section>

    <main
      v-if="workspaceLoadState === 'ready'"
      id="followup-main"
      class="followup-main"
      tabindex="-1"
    >
      <section
        v-if="activeTab === 'chat'"
        class="conversation-sheet"
        :class="{ 'is-fictional': chatTarget === 'agent' }"
        aria-labelledby="conversation-heading"
      >
        <header class="answer-boundary">
          <p class="section-kicker">
            {{
              chatTarget === "report_agent"
                ? "Report explanation"
                : "Fictional generated dialogue"
            }}
          </p>
          <h2 id="conversation-heading">{{ conversationHeading }}</h2>
          <p>{{ conversationBoundary }}</p>

          <button
            v-if="chatTarget === 'agent'"
            type="button"
            class="change-profile"
            aria-controls="fictional-profile-options"
            :aria-expanded="showAgentDropdown"
            @click="toggleAgentDropdown"
          >
            {{
              selectedAgent
                ? `Change ${profileName(selectedAgent, selectedAgentIndex)}`
                : "Choose a fictional profile"
            }}
          </button>

          <dl class="answer-facts">
            <div>
              <dt>Answer source</dt>
              <dd>
                {{
                  chatTarget === "report_agent"
                    ? "AI interpretation of this report"
                    : "New fictional response"
                }}
              </dd>
            </div>
            <div>
              <dt>People consulted</dt>
              <dd>0</dd>
            </div>
          </dl>
        </header>

        <div class="conversation-column">
          <section
            v-if="showAgentDropdown"
            class="profile-picker"
            aria-label="Choose a fictional generated profile"
            @keydown.esc.stop="showAgentDropdown = false"
          >
            <header>
              <div>
                <p class="section-kicker">Fictional profiles</p>
                <h3>Choose who the model should portray.</h3>
              </div>
              <button
                type="button"
                class="close-picker"
                aria-label="Close profile chooser"
                @click="showAgentDropdown = false"
              >
                Close
              </button>
            </header>
            <p class="picker-warning">
              These are generated character briefs, not recruited participants.
            </p>
            <div
              v-if="profileLoadState === 'loading'"
              class="profile-load-state"
              role="status"
            >
              Loading fictional profile briefs…
            </div>
            <div
              v-else-if="profileLoadState === 'error'"
              class="profile-load-state is-error"
              role="alert"
              data-testid="profile-load-error"
            >
              <strong>Fictional profiles could not be loaded.</strong>
              <span>This is a connection problem, not an empty profile set.</span>
              <button type="button" @click="retryWorkspaceLoad">
                Retry profile connection
              </button>
            </div>
            <div v-else-if="profiles.length === 0" class="empty-state">
              No generated profiles are available for this run.
            </div>
            <div
              v-else
              id="fictional-profile-options"
              class="profile-list"
              role="group"
              aria-label="Fictional profile choices"
            >
              <button
                v-for="(profile, profileIndex) in profiles"
                :key="profile.id ?? profileIndex"
                type="button"
                :aria-pressed="selectedAgentIndex === profileIndex"
                @click="selectAgent(profile, profileIndex)"
              >
                <span>{{ String(profileIndex + 1).padStart(2, "0") }}</span>
                <strong>{{ profileName(profile, profileIndex) }}</strong>
                <small>{{ profileRole(profile) }} · fictional</small>
              </button>
            </div>
          </section>

          <form class="question-composer" @submit.prevent="sendMessage">
            <p class="composer-kicker">Start here · ask one clear question</p>
            <label for="followup-question">
              {{
                chatTarget === "report_agent"
                  ? "Your follow-up question"
                  : "Question for the fictional profile"
              }}
            </label>
            <div>
              <textarea
                id="followup-question"
                v-model="chatInput"
                maxlength="4000"
                :placeholder="questionPlaceholder"
                :disabled="
                  isSending || (!selectedAgent && chatTarget === 'agent')
                "
                @keydown.enter.exact.prevent="sendMessage"
              ></textarea>
              <button
                type="submit"
                :disabled="
                  !chatInput.trim() ||
                  isSending ||
                  (!selectedAgent && chatTarget === 'agent')
                "
              >
                Ask
              </button>
            </div>
            <p>
              {{
                chatTarget === "report_agent"
                  ? "Answers interpret generated material already in this run."
                  : "This creates new fictional material; it does not contact anyone."
              }}
            </p>
            <p v-if="conversationError" class="inline-error" role="alert">
              {{ conversationError }}
            </p>
          </form>

          <div ref="chatMessages" class="messages-list" aria-live="polite">
            <div v-if="chatHistory.length === 0" class="conversation-empty">
              <p class="section-kicker">Start here</p>
              <h3>
                {{
                  chatTarget === "report_agent"
                    ? "Question the report, not a person."
                    : selectedAgent
                      ? `Ask a fictional version of ${profileName(
                          selectedAgent,
                          selectedAgentIndex,
                        )}.`
                      : "Choose a fictional profile before asking."
                }}
              </h3>
              <p>
                {{
                  chatTarget === "report_agent"
                    ? "Use follow-ups to expose assumptions, missing paths, and what should be validated next."
                    : "The reply will be generated on demand from the profile brief and scenario context."
                }}
              </p>
              <div
                v-if="chatTarget === 'report_agent' || selectedAgent"
                class="suggested-questions"
              >
                <button
                  v-for="question in currentSuggestions"
                  :key="question"
                  type="button"
                  @click="useSuggestedQuestion(question)"
                >
                  {{ question }}
                </button>
              </div>
            </div>

            <article
              v-for="(message, messageIndex) in chatHistory"
              :key="`${message.timestamp}-${messageIndex}`"
              class="conversation-message"
              :class="[
                message.role,
                {
                  'is-fictional':
                    message.answer_type === 'fictional_profile_response',
                },
              ]"
            >
              <header>
                <span>{{ messageLabel(message) }}</span>
                <time>{{ formatTime(message.timestamp) }}</time>
              </header>
              <div class="answer-copy">{{ message.content }}</div>
              <footer
                v-if="
                  message.role === 'assistant' &&
                  message.answer_type === 'fictional_profile_response'
                "
              >
                Fictional response generated on request · 0 human respondents
              </footer>
              <footer v-else-if="message.role === 'assistant'">
                Report explanation · adds no observations from people or
                real-world validation
              </footer>
            </article>

            <div v-if="isSending" class="answer-loading" role="status">
              <span aria-hidden="true"></span>
              <p>
                {{
                  chatTarget === "report_agent"
                    ? "Preparing a report explanation…"
                    : "Generating fictional dialogue…"
                }}
              </p>
            </div>
          </div>

        </div>
      </section>

      <section
        v-else-if="activeTab === 'group_responses'"
        class="group-question-sheet"
        aria-labelledby="group-heading"
      >
        <header class="group-intro">
          <p class="section-kicker">Fictional group responses</p>
          <h2 id="group-heading">Compare generated viewpoints—not people.</h2>
          <p>
            Ask one question across several fictional profiles. The answers are
            new model outputs, not interviews, survey responses, or a sample.
          </p>
          <div class="fictional-warning">
            0 human respondents · generated on request · requires outside validation
          </div>
        </header>

        <div class="group-builder">
          <section class="profile-selection" aria-labelledby="select-profiles">
            <header>
              <div>
                <p>Step 1</p>
                <h3 id="select-profiles">Choose fictional profiles</h3>
              </div>
              <strong>{{ selectedAgents.size }} selected</strong>
            </header>
            <div
              v-if="profileLoadState === 'loading'"
              class="profile-load-state"
              role="status"
            >
              Loading fictional profile briefs…
            </div>
            <div
              v-else-if="profileLoadState === 'error'"
              class="profile-load-state is-error"
              role="alert"
              data-testid="group-profile-load-error"
            >
              <strong>Fictional profiles could not be loaded.</strong>
              <span>This is a connection problem, not an empty profile set.</span>
              <button type="button" @click="retryWorkspaceLoad">
                Retry profile connection
              </button>
            </div>
            <div v-else-if="profiles.length === 0" class="empty-state">
              No generated profiles are available for this run.
            </div>
            <div v-else class="profile-checklist">
              <label
                v-for="(profile, profileIndex) in profiles"
                :key="profile.id ?? profileIndex"
                :class="{ checked: selectedAgents.has(profileIndex) }"
              >
                <input
                  type="checkbox"
                  :checked="selectedAgents.has(profileIndex)"
                  @change="toggleAgentSelection(profileIndex)"
                />
                <span>{{ String(profileIndex + 1).padStart(2, "0") }}</span>
                <strong>{{ profileName(profile, profileIndex) }}</strong>
                <small>{{ profileRole(profile) }}</small>
              </label>
            </div>
            <div class="selection-actions">
              <button type="button" @click="selectAllAgents">Select all</button>
              <button type="button" @click="clearAgentSelection">Clear</button>
            </div>
          </section>

          <form class="group-composer" @submit.prevent="askSelectedProfiles">
            <p>Step 2</p>
            <label for="group-question">Ask one shared question</label>
            <textarea
              id="group-question"
              v-model="groupQuestion"
              maxlength="2000"
              placeholder="What would make this fictional profile reconsider its response?"
            ></textarea>
            <button
              type="submit"
              :disabled="
                selectedAgents.size === 0 ||
                !groupQuestion.trim() ||
                isAskingGroup
              "
            >
              {{
                isAskingGroup
                  ? "Generating responses…"
                  : "Generate fictional responses"
              }}
            </button>
            <small>
              The same prompt is sent to each selected character brief.
            </small>
            <p v-if="groupError" class="inline-error" role="alert">
              {{ groupError }}
            </p>
          </form>
        </div>

        <section
          v-if="groupResponses.length > 0"
          class="group-results"
          aria-labelledby="group-results-heading"
        >
          <header>
            <div>
              <p class="section-kicker">Generated comparison</p>
              <h2 id="group-results-heading">Fictional responses</h2>
            </div>
            <button
              type="button"
              :disabled="isExporting"
              @click="handleExportGeneratedResponses"
            >
              {{ isExporting ? "Preparing CSV…" : "Download responses (CSV)" }}
            </button>
          </header>
          <article
            v-for="(response, responseIndex) in groupResponses"
            :key="`${response.agent_name}-${responseIndex}`"
          >
            <header>
              <span>{{ String(responseIndex + 1).padStart(2, "0") }}</span>
              <div>
                <h3>{{ response.agent_name }}</h3>
                <p>{{ response.profession || "Fictional generated profile" }}</p>
              </div>
            </header>
            <div class="response-copy">{{ response.answer }}</div>
            <footer>
              Fictional response · generated on request · 0 human respondents
            </footer>
          </article>
        </section>
      </section>

      <section
        v-else-if="activeTab === 'opinion_map'"
        class="run-map-sheet"
        aria-labelledby="run-map-heading"
      >
        <header>
          <p class="section-kicker">Generated interaction map</p>
          <h2 id="run-map-heading">See patterns inside this run.</h2>
          <p>
            The map describes generated interactions. It is not human evidence,
            a population estimate, or evidence of what people believe.
          </p>
          <strong>0 human respondents · not a forecast</strong>
        </header>
        <div class="map-frame">
          <OpinionMap :simulationId="simulationId" />
        </div>
      </section>
    </main>

    <details v-if="workspaceLoadState === 'ready'" class="secondary-record">
      <summary>
        <span>Report context, generated traces, and diagnostics</span>
        <small>Secondary record · closed by default</small>
      </summary>

      <div class="secondary-grid">
        <section class="report-context-record">
          <h2>Report context</h2>
          <div
            v-if="reportContextLoadState === 'error'"
            class="record-load-error"
            role="alert"
          >
            <strong>The report context could not be loaded.</strong>
            <span>This record is unavailable; it is not an empty report.</span>
            <button type="button" @click="retryWorkspaceLoad">
              Retry report connection
            </button>
          </div>
          <div v-else-if="!reportOutline" class="record-empty">
            The report context is not available yet.
          </div>
          <template v-else>
            <h3>{{ reportOutline.title || "Scenario report" }}</h3>
            <p>{{ reportOutline.summary }}</p>
            <details
              v-for="(section, sectionIndex) in contextSections"
              :key="`${sectionIndex}-${section.title}`"
              class="context-section"
            >
              <summary>
                <span>{{ String(sectionIndex + 1).padStart(2, "0") }}</span>
                {{ section.title }}
              </summary>
              <div>{{ section.content || "Section text is not available." }}</div>
            </details>
          </template>
        </section>

        <section class="run-record">
          <h2>Run record</h2>
          <dl>
            <div>
              <dt>Status</dt>
              <dd>
                {{
                  runStatusLoadState === "error"
                    ? "Updates unavailable"
                    : runStatusLabel(runStatus?.runner_status)
                }}
              </dd>
            </div>
            <div>
              <dt>Round</dt>
              <dd>
                {{ runStatus?.current_round || 0 }}/{{
                  runStatus?.total_rounds || "?"
                }}
              </dd>
            </div>
            <div>
              <dt>Generated actions</dt>
              <dd>{{ runStatus?.total_actions_count || 0 }}</dd>
            </div>
            <div>
              <dt>Report ID</dt>
              <dd>{{ reportId || "Unavailable" }}</dd>
            </div>
            <div>
              <dt>Simulation ID</dt>
              <dd>{{ simulationId || "Unavailable" }}</dd>
            </div>
          </dl>

          <label class="advanced-control">
            <input v-model="bypassPromptOpt" type="checkbox" />
            <span>
              <strong>Send exact wording</strong>
              <small>
                Advanced: bypass prompt optimization for fictional profile
                responses.
              </small>
            </span>
          </label>
        </section>

        <section class="trace-record">
          <h2>Recent generated activity</h2>
          <p v-if="recentActions.length === 0" class="record-empty">
            No generated activity has been recorded yet.
          </p>
          <ol v-else>
            <li
              v-for="(action, actionIndex) in recentActions"
              :key="`${action.timestamp}-${actionIndex}`"
            >
              <header>
                <strong>{{ actionLabel(action.action_type) }}</strong>
                <time>{{ formatTime(action.timestamp) }}</time>
              </header>
              <p>
                {{ action.agent_name || "Generated profile" }} ·
                {{ platformLabel(action.platform) }}
              </p>
              <blockquote v-if="action.action_args?.text">
                {{ truncate(action.action_args.text, 180) }}
              </blockquote>
            </li>
          </ol>
        </section>

        <section class="diagnostic-record">
          <h2>Workspace messages</h2>
          <p v-if="!systemLogs?.length" class="record-empty">
            No diagnostic messages are available.
          </p>
          <ol v-else>
            <li v-for="(log, logIndex) in systemLogs" :key="logIndex">
              <time>{{ log.time }}</time>
              <span>{{ log.msg }}</span>
            </li>
          </ol>
        </section>
      </div>
    </details>
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  reactive,
  ref,
  watch,
} from "vue";
import {
  chatWithReport,
  getAgentLog,
  getReport,
  normalizeAgentLogEntry,
  normalizeLogPage,
} from "../api/report";
import {
  askSyntheticProfiles,
  exportGeneratedResponsesCSV,
  getRunStatusDetail,
  getSimulationProfilesRealtime,
  stopSimulation,
} from "../api/simulation";
import OpinionMap from "./OpinionMap.vue";

const props = defineProps({
  reportId: String,
  simulationId: String,
  systemLogs: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["add-log", "update-status"]);

const STATUS_POLL_INTERVAL_MS = 5000;

const activeTab = ref("chat");
const chatTarget = ref("report_agent");
const showAgentDropdown = ref(false);
const selectedAgent = ref(null);
const selectedAgentIndex = ref(null);
const isSending = ref(false);
const isStopping = ref(false);
const confirmingStop = ref(false);
const isExporting = ref(false);
const chatInput = ref("");
const chatHistory = ref([]);
const chatHistoryCache = reactive({});
const profiles = ref([]);
const conversationError = ref("");
const stopError = ref("");

const runStatus = ref(null);
const recentActions = ref([]);
const workspaceLoadState = ref("loading");
const workspaceLoadError = ref("");
const loadWarnings = ref([]);
const reportContextLoadState = ref("loading");
const profileLoadState = ref("loading");
const runStatusLoadState = ref("loading");
const pollingError = ref("");
const isRetryingWorkspace = ref(false);
const isReconnecting = ref(false);
let statusTimer = null;
let statusPollInFlight = null;
let loadRequestId = 0;
let activeContextKey = "";

const reportOutline = ref(null);
const generatedSections = ref({});
const currentSectionIndex = ref(null);

const selectedAgents = ref(new Set());
const groupQuestion = ref("");
const groupResponses = ref([]);
const isAskingGroup = ref(false);
const groupError = ref("");
const bypassPromptOpt = ref(false);

const chatMessages = ref(null);

const runStatusLabel = (status) => {
  const labels = {
    starting: "Starting",
    running: "Running",
    completed: "Complete",
    stopped: "Stopped",
    failed: "Needs attention",
    interrupted: "Interrupted",
  };
  return labels[String(status || "").toLowerCase()] || "Idle";
};

const platformLabel = (platform) =>
  platform === "reddit" ? "Topic community" : "Short-post channel";

const actionLabel = (action) => {
  const labels = {
    CREATE_POST: "Created a post",
    CREATE_COMMENT: "Added a comment",
    LIKE_POST: "Liked a post",
    LIKE_COMMENT: "Liked a comment",
    REPOST: "Shared a post",
    QUOTE_POST: "Quoted a post",
    FOLLOW: "Followed a profile",
    SEARCH_POSTS: "Searched posts",
    UPVOTE_POST: "Upvoted a post",
    DOWNVOTE_POST: "Downvoted a post",
    DO_NOTHING: "Took no action",
  };
  return (
    labels[action] ||
    String(action || "Recorded an action").replaceAll("_", " ")
  );
};

const profileName = (profile, index) =>
  profile?.username ||
  profile?.name ||
  `Fictional profile ${Number(index ?? 0) + 1}`;

const profileRole = (profile) =>
  profile?.profession || profile?.bio || "Generated character brief";

const isSimRunning = computed(() =>
  ["running", "starting"].includes(
    String(runStatus.value?.runner_status || "").toLowerCase(),
  ),
);

const conversationHeading = computed(() => {
  if (chatTarget.value === "report_agent") {
    return "Ask for an explanation of the report.";
  }
  return selectedAgent.value
    ? `Ask a fictional version of ${profileName(
        selectedAgent.value,
        selectedAgentIndex.value,
      )}.`
    : "Choose a fictional profile to begin.";
});

const conversationBoundary = computed(() =>
  chatTarget.value === "report_agent"
    ? "This AI explains and challenges the existing synthetic report. It does not add testimony, field research, or real-world validation."
    : "Each reply is newly generated in character from a fictional profile brief. It is not something a person said or believes.",
);

const questionPlaceholder = computed(() =>
  chatTarget.value === "report_agent"
    ? "Which assumptions matter most, and what should be validated first?"
    : selectedAgent.value
      ? "What would make this fictional profile respond differently?"
      : "Choose a fictional profile first.",
);

const currentSuggestions = computed(() =>
  chatTarget.value === "report_agent"
    ? [
        "Which assumptions have the greatest effect on these paths?",
        "What plausible path may be missing from the report?",
        "What should we validate with people first?",
      ]
    : [
        "What would change this fictional profile’s response?",
        "Which part of the scenario concerns this fictional profile most?",
        "What important context is missing from this character brief?",
      ],
);

const contextSections = computed(() => {
  const sections = reportOutline.value?.sections;
  if (!Array.isArray(sections)) return [];
  return sections.map((section, index) => ({
    title:
      typeof section === "string"
        ? section
        : section?.title || `Report section ${index + 1}`,
    content:
      (typeof section === "object" ? section?.content : "") ||
      generatedSections.value[index + 1] ||
      "",
  }));
});

const addLog = (message) => emit("add-log", message);

const formatTime = (timestamp) => {
  if (!timestamp) return "";
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) return String(timestamp);
  return parsed.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
  });
};

const truncate = (value, length) => {
  const text = String(value || "");
  return text.length > length ? `${text.substring(0, length)}…` : text;
};

const messageLabel = (message) => {
  if (message.role === "user") return "Your question";
  if (message.answer_type === "fictional_profile_response") {
    return `Fictional response · ${
      message.speaker_name ||
      profileName(selectedAgent.value, selectedAgentIndex.value)
    }`;
  }
  return "Report explanation";
};

const useSuggestedQuestion = (question) => {
  chatInput.value = question;
};

const pollStatus = async () => {
  if (!props.simulationId) {
    runStatusLoadState.value = "error";
    pollingError.value =
      "Live run updates cannot connect because this workspace has no run ID.";
    return false;
  }
  if (statusPollInFlight) return statusPollInFlight;

  statusPollInFlight = (async () => {
    try {
      const response = await getRunStatusDetail(props.simulationId);
      if (!response?.success || !response.data) {
        throw new Error("run_status_unavailable");
      }

      runStatus.value = response.data;
      recentActions.value = response.data.recent_actions || [];
      runStatusLoadState.value = "ready";
      pollingError.value = "";
      emit(
        "update-status",
        ["running", "starting"].includes(response.data.runner_status)
          ? "processing"
          : "ready",
      );
      return true;
    } catch {
      const shouldAnnounce = !pollingError.value;
      runStatusLoadState.value = "error";
      pollingError.value =
        "The last confirmed status remains on screen. Reconnect to check for newer run activity.";
      emit("update-status", "error");
      if (shouldAnnounce) {
        addLog(
          "Live run updates disconnected. Existing report content remains available.",
        );
      }
      return false;
    } finally {
      statusPollInFlight = null;
    }
  })();

  return statusPollInFlight;
};

const reconnectRunStatus = async () => {
  if (isReconnecting.value) return;
  isReconnecting.value = true;
  const reconnected = await pollStatus();
  if (reconnected) addLog("Live run updates reconnected.");
  isReconnecting.value = false;
};

const handleStopSimulation = async () => {
  if (!props.simulationId || isStopping.value) return;
  isStopping.value = true;
  stopError.value = "";
  try {
    const response = await stopSimulation({
      simulation_id: props.simulationId,
    });
    if (response.success) {
      addLog("Scenario run stopped.");
      await pollStatus();
    }
  } catch (error) {
    stopError.value =
      error?.message || "The scenario run could not be stopped.";
    addLog(`The scenario run could not be stopped: ${stopError.value}`);
  } finally {
    isStopping.value = false;
    confirmingStop.value = false;
  }
};

const handleExportGeneratedResponses = async () => {
  if (groupResponses.value.length === 0 || isExporting.value) return;
  isExporting.value = true;
  try {
    const response = await exportGeneratedResponsesCSV(
      props.simulationId,
      groupResponses.value,
    );
    const payload = response?.data || response;
    const url = window.URL.createObjectURL(
      payload instanceof Blob
        ? payload
        : new Blob([payload], { type: "text/csv" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute(
      "download",
      `ATP_FICTIONAL_RESPONSES_${props.simulationId}.csv`,
    );
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    addLog("Fictional generated responses exported to CSV.");
  } catch (error) {
    addLog(
      `The generated responses could not be downloaded: ${
        error?.message || error
      }`,
    );
  } finally {
    isExporting.value = false;
  }
};

const saveChatToCache = () => {
  const key =
    chatTarget.value === "report_agent"
      ? "report"
      : `agent_${selectedAgentIndex.value}`;
  chatHistoryCache[key] = [...chatHistory.value];
};

const selectReportAgentChat = () => {
  if (activeTab.value === "chat") saveChatToCache();
  chatTarget.value = "report_agent";
  activeTab.value = "chat";
  chatHistory.value = chatHistoryCache.report || [];
  showAgentDropdown.value = false;
  conversationError.value = "";
};

const selectProfileChat = () => {
  if (activeTab.value === "chat") saveChatToCache();
  chatTarget.value = "agent";
  activeTab.value = "chat";
  chatHistory.value =
    selectedAgentIndex.value == null
      ? []
      : chatHistoryCache[`agent_${selectedAgentIndex.value}`] || [];
  showAgentDropdown.value = !selectedAgent.value;
  conversationError.value = "";
};

const toggleAgentDropdown = () => {
  showAgentDropdown.value = !showAgentDropdown.value;
};

const selectAgent = (profile, profileIndex) => {
  if (activeTab.value === "chat") saveChatToCache();
  selectedAgent.value = profile;
  selectedAgentIndex.value = profileIndex;
  chatTarget.value = "agent";
  chatHistory.value = chatHistoryCache[`agent_${profileIndex}`] || [];
  showAgentDropdown.value = false;
  activeTab.value = "chat";
  conversationError.value = "";
};

const selectGroupResponsesTab = () => {
  if (activeTab.value === "chat") saveChatToCache();
  activeTab.value = "group_responses";
  showAgentDropdown.value = false;
};

const selectOpinionMapTab = () => {
  if (activeTab.value === "chat") saveChatToCache();
  activeTab.value = "opinion_map";
  showAgentDropdown.value = false;
};

const scrollToBottom = () => {
  nextTick(() => {
    if (chatMessages.value) {
      chatMessages.value.scrollTop = chatMessages.value.scrollHeight;
    }
  });
};

const sendMessage = async () => {
  if (
    !chatInput.value.trim() ||
    isSending.value ||
    (chatTarget.value === "agent" && !selectedAgent.value)
  ) {
    return;
  }

  const question = chatInput.value.trim();
  chatInput.value = "";
  conversationError.value = "";
  chatHistory.value.push({
    role: "user",
    content: question,
    timestamp: new Date().toISOString(),
  });
  scrollToBottom();
  isSending.value = true;

  try {
    if (chatTarget.value === "report_agent") {
      const response = await chatWithReport({
        simulation_id: props.simulationId,
        message: question,
        chat_history: chatHistory.value
          .slice(-6)
          .map((message) => ({
            role: message.role,
            content: message.content,
          })),
      });
      if (response.success) {
        chatHistory.value.push({
          role: "assistant",
          answer_type: "report_explanation",
          content:
            response.data?.response ||
            response.data?.answer ||
            "No explanation was returned.",
          timestamp: new Date().toISOString(),
        });
      }
    } else {
      const response = await askSyntheticProfiles({
        simulation_id: props.simulationId,
        questions: [
          {
            agent_id: selectedAgentIndex.value,
            prompt: question,
          },
        ],
        bypass_prompt_optimization: bypassPromptOpt.value,
      });
      if (response.success) {
        const results = response.data?.result?.results || {};
        const generatedResponse =
          results[`reddit_${selectedAgentIndex.value}`]?.response ||
          results[`twitter_${selectedAgentIndex.value}`]?.response;
        chatHistory.value.push({
          role: "assistant",
          answer_type: "fictional_profile_response",
          speaker_name: profileName(
            selectedAgent.value,
            selectedAgentIndex.value,
          ),
          content: generatedResponse || "No fictional response was returned.",
          timestamp: new Date().toISOString(),
        });
      }
    }
  } catch (error) {
    conversationError.value =
      error?.message || "The follow-up question could not be answered.";
    addLog(
      `The follow-up question could not be answered: ${
        conversationError.value
      }`,
    );
  } finally {
    isSending.value = false;
    scrollToBottom();
    saveChatToCache();
  }
};

const toggleAgentSelection = (profileIndex) => {
  const selection = new Set(selectedAgents.value);
  if (selection.has(profileIndex)) selection.delete(profileIndex);
  else selection.add(profileIndex);
  selectedAgents.value = selection;
};

const selectAllAgents = () => {
  selectedAgents.value = new Set(profiles.value.map((_, index) => index));
};

const clearAgentSelection = () => {
  selectedAgents.value = new Set();
};

const askSelectedProfiles = async () => {
  if (
    selectedAgents.value.size === 0 ||
    !groupQuestion.value.trim() ||
    isAskingGroup.value
  ) {
    return;
  }

  isAskingGroup.value = true;
  groupError.value = "";
  addLog(
    `Generating responses from ${selectedAgents.value.size} fictional profiles…`,
  );
  try {
    const response = await askSyntheticProfiles({
      simulation_id: props.simulationId,
      questions: Array.from(selectedAgents.value).map((profileIndex) => ({
        agent_id: profileIndex,
        prompt: groupQuestion.value.trim(),
      })),
      bypass_prompt_optimization: bypassPromptOpt.value,
    });
    if (response.success) {
      const results = response.data?.result?.results || {};
      groupResponses.value = Array.from(selectedAgents.value).map(
        (profileIndex) => {
          const profile = profiles.value[profileIndex];
          const answer =
            results[`reddit_${profileIndex}`]?.response ||
            results[`twitter_${profileIndex}`]?.response ||
            "No fictional response was returned.";
          return {
            agent_name: profileName(profile, profileIndex),
            profession: profileRole(profile),
            answer,
          };
        },
      );
    }
  } catch (error) {
    groupError.value =
      error?.message || "The fictional responses could not be generated.";
    addLog(`The fictional responses could not be generated: ${groupError.value}`);
  } finally {
    isAskingGroup.value = false;
  }
};

const applyReportDocument = (document) => {
  if (!document || typeof document !== "object") return;
  if (document.outline) {
    reportOutline.value = document.outline;
    if (Array.isArray(document.outline.sections)) {
      document.outline.sections.forEach((section, index) => {
        if (typeof section === "object" && section?.content) {
          generatedSections.value[index + 1] = section.content;
        }
      });
    }
  }
};

const applyAgentLogs = (response) => {
  const logs = normalizeLogPage(response).logs.map(normalizeAgentLogEntry);
  logs.forEach((log) => {
    if (log.action === "planning_complete" && log.outline) {
      reportOutline.value = log.outline;
    }
    if (log.action === "section_start") {
      currentSectionIndex.value = Number(log.section_index) || null;
    }
    if (log.action === "section_complete") {
      generatedSections.value[Number(log.section_index)] = log.content;
      currentSectionIndex.value = null;
    }
  });
};

const resetForNewContext = () => {
  reportOutline.value = null;
  generatedSections.value = {};
  currentSectionIndex.value = null;
  profiles.value = [];
  selectedAgent.value = null;
  selectedAgentIndex.value = null;
  selectedAgents.value = new Set();
  groupResponses.value = [];
  chatHistory.value = [];
  Object.keys(chatHistoryCache).forEach((key) => {
    delete chatHistoryCache[key];
  });
};

const settledSuccessfully = (result) =>
  result.status === "fulfilled" && result.value?.success !== false;

const loadData = async ({ retry = false } = {}) => {
  const requestId = ++loadRequestId;
  const contextKey = `${props.reportId || ""}:${props.simulationId || ""}`;
  if (contextKey !== activeContextKey) {
    activeContextKey = contextKey;
    resetForNewContext();
  }

  workspaceLoadState.value = "loading";
  workspaceLoadError.value = "";
  loadWarnings.value = [];
  reportContextLoadState.value = "loading";
  profileLoadState.value = "loading";
  runStatusLoadState.value = "loading";
  if (retry) isRetryingWorkspace.value = true;

  if (!props.reportId || !props.simulationId) {
    workspaceLoadState.value = "error";
    workspaceLoadError.value =
      "This link is missing the report or run identifier needed to open follow-up tools.";
    reportContextLoadState.value = "error";
    profileLoadState.value = "error";
    runStatusLoadState.value = "error";
    isRetryingWorkspace.value = false;
    return;
  }

  const [reportResult, logResult, profileResult] = await Promise.allSettled([
    getReport(props.reportId),
    getAgentLog(props.reportId, 0),
    getSimulationProfilesRealtime(props.simulationId, "reddit"),
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
    reportContextLoadState.value = "ready";
  } else {
    reportContextLoadState.value = "error";
    warnings.push("Report context is disconnected.");
  }

  if (profilesLoaded) {
    profiles.value = profileResult.value.data?.profiles || [];
    profileLoadState.value = "ready";
  } else {
    profileLoadState.value = "error";
    warnings.push("Fictional profile briefs are disconnected.");
  }

  const runStatusLoaded = await pollStatus();
  if (requestId !== loadRequestId) return;

  if (!reportLoaded && !logsLoaded && !profilesLoaded && !runStatusLoaded) {
    workspaceLoadState.value = "error";
    workspaceLoadError.value =
      "The report, fictional profile briefs, and live run status are all disconnected. Check the connection and try again.";
    addLog("The follow-up workspace could not open its run context.");
  } else {
    workspaceLoadState.value = "ready";
    loadWarnings.value = warnings;
  }

  if (requestId === loadRequestId) {
    isRetryingWorkspace.value = false;
  }
};

const retryWorkspaceLoad = () => loadData({ retry: true });

const handleDocumentClick = (event) => {
  if (
    !event.target.closest(".profile-picker") &&
    !event.target.closest(".fictional-mode") &&
    !event.target.closest(".change-profile")
  ) {
    showAgentDropdown.value = false;
  }
};

onMounted(() => {
  loadData();
  statusTimer = window.setInterval(pollStatus, STATUS_POLL_INTERVAL_MS);
  document.addEventListener("click", handleDocumentClick);
});

onUnmounted(() => {
  loadRequestId += 1;
  document.removeEventListener("click", handleDocumentClick);
  if (statusTimer) window.clearInterval(statusTimer);
});

watch(
  [() => props.reportId, () => props.simulationId],
  () => loadData(),
);
</script>

<style scoped>
.followup-brief {
  min-height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--ink-soft); backdrop-filter: none;
  color: var(--paper);
  font-family: var(--font-sans);
}

.skip-link {
  position: absolute;
  top: 0.75rem;
  left: 0.75rem;
  z-index: 10;
  padding: 0.7rem 0.9rem;
  transform: translateY(-180%);
  border: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--signal);
  color: var(--paper);
  font-weight: 700;
  text-decoration: none;
  transition: transform 180ms var(--ease-out);
}

.skip-link:focus {
  transform: translateY(0);
}

.followup-masthead {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(15rem, 21rem);
  gap: clamp(1.5rem, 4vw, 4rem);
  align-items: end;
  min-height: 14rem;
  padding: clamp(1.5rem, 2.4vw, 2.4rem);
  overflow: hidden;
  border-bottom: 0.55rem solid var(--signal);
  background: var(--ink-deep); backdrop-filter: none;
  color: var(--paper);
}

.followup-masthead::after {
  position: absolute;
  right: clamp(17rem, 26vw, 25rem);
  bottom: -4rem;
  width: 8rem;
  height: 130%;
  transform: rotate(7deg);
  background: var(--signal);
  content: "";
  pointer-events: none;
}

.masthead-copy,
.truth-stamp {
  position: relative;
  z-index: 1;
}

.route-label,
.section-kicker {
  margin: 0 0 0.9rem;
  font-family: var(--font-display);
  font-size: 0.9rem;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.route-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--signal);
}

.route-label span {
  display: grid;
  width: 2.6rem;
  height: 2.6rem;
  place-items: center;
  border: 2px solid currentColor;
}

.followup-masthead h1 {
  max-width: 14ch;
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(2.8rem, 4vw, 4.4rem);
  font-weight: 400;
  letter-spacing: -0.02em;
  line-height: 0.88;
}

.masthead-copy > p:last-child {
  max-width: 53rem;
  margin: 0.8rem 0 0;
  padding-top: 0.6rem;
  border-top: 1px solid var(--line-dark);
  color: var(--paper-muted);
  font-size: 0.92rem;
  line-height: 1.45;
}

.truth-stamp {
  display: grid;
  align-content: end;
  min-height: 8.5rem;
  padding: 0.95rem;
  border: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--signal);
  color: var(--paper);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
}

.truth-stamp span,
.truth-stamp b {
  font-family: var(--font-display);
  font-size: 0.9rem;
  font-weight: 400;
  letter-spacing: 0.055em;
  text-transform: uppercase;
}

.truth-stamp strong {
  max-width: 8ch;
  margin: 0.6rem 0 0.25rem;
  font-family: var(--font-display);
  font-size: clamp(2.35rem, 3vw, 3.2rem);
  font-weight: 400;
  line-height: 0.85;
  text-transform: uppercase;
}

.truth-stamp small {
  max-width: 27ch;
  margin-top: 0.55rem;
  font-size: 0.7rem;
  line-height: 1.4;
}

.followup-modes {
  display: grid;
  grid-template-columns: minmax(10rem, 0.62fr) repeat(4, minmax(0, 1fr));
  border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--ink-raised); backdrop-filter: none;
}

.mode-guide {
  display: grid;
  align-content: center;
  min-height: 5rem;
  padding: 0.75rem clamp(0.8rem, 2vw, 2rem);
  border-right: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--ink-deep); backdrop-filter: none;
  color: var(--paper);
}

.mode-guide span {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.92rem;
  letter-spacing: 0.045em;
  line-height: 1;
  text-transform: uppercase;
}

.mode-guide small {
  margin-top: 0.35rem;
  color: var(--paper-dim);
  font-size: 0.62rem;
  line-height: 1.25;
}

.followup-modes button {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  column-gap: 0.8rem;
  align-items: center;
  min-height: 5rem;
  padding: 0.75rem clamp(0.7rem, 1.5vw, 1.35rem);
  border: 0;
  border-right: 1px solid rgba(242, 235, 221, 0.1);
  border-radius: var(--radius-md);
  background: var(--ink-raised); backdrop-filter: none;
  color: var(--paper);
  text-align: left;
  transition:
    background-color 180ms var(--ease-out),
    color 180ms var(--ease-out),
    transform 180ms var(--ease-out);
}

.followup-modes button:last-child {
  border-right: 0;
}

.followup-modes button:hover,
.followup-modes button.active {
  background: var(--signal);
  color: var(--paper);
  transform: translateY(-0.2rem);
}

.followup-modes button.fictional-mode.active {
  box-shadow: inset 0 -0.45rem 0 var(--warning);
}

.followup-modes button:active,
.question-composer button:active:not(:disabled) {
  transform: translateY(1px);
}

.followup-modes button > span {
  grid-row: 1 / span 2;
  font-family: var(--font-display);
  font-size: 1.7rem;
}

.followup-modes strong {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 400;
  letter-spacing: 0.03em;
  line-height: 1;
  text-transform: uppercase;
}

.followup-modes small {
  margin-top: 0.2rem;
  font-size: 0.64rem;
  line-height: 1.25;
}

.workspace-state {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1.25rem 2rem;
  align-items: center;
  padding: 1.1rem clamp(1rem, 4vw, 4rem);
  border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--ink-raised); backdrop-filter: none;
  color: var(--paper);
}

.workspace-state-copy {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 1rem;
  align-items: center;
}

.workspace-state-index {
  display: grid;
  width: 3rem;
  height: 3rem;
  place-items: center;
  border: 2px solid currentColor;
  background: var(--signal);
  font-family: var(--font-display);
  font-size: 1.45rem;
}

.workspace-state p,
.connection-state p {
  margin: 0 0 0.25rem;
  color: var(--paper-muted);
  font-family: var(--font-display);
  font-size: 0.78rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.workspace-state h2 {
  max-width: 42rem;
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(1.35rem, 2.2vw, 2rem);
  font-weight: 400;
  line-height: 1;
  text-transform: uppercase;
}

.workspace-state small,
.connection-state span {
  display: block;
  max-width: 56rem;
  margin-top: 0.35rem;
  color: var(--paper-muted);
  font-size: 0.76rem;
  line-height: 1.45;
}

.workspace-state ul {
  display: grid;
  gap: 0.2rem;
  margin: 0.55rem 0 0;
  padding-left: 1.1rem;
  color: var(--paper-muted);
  font-size: 0.76rem;
}

.workspace-state > button,
.connection-state > button,
.profile-load-state button,
.record-load-error button {
  min-height: 2.8rem;
  padding: 0.65rem 1rem;
  border: 1px solid rgba(242, 235, 221, 0.1);
  border-radius: var(--radius-md);
  background: var(--signal);
  color: var(--paper);
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
}

.workspace-state > button:active:not(:disabled),
.connection-state > button:active:not(:disabled),
.profile-load-state button:active:not(:disabled),
.record-load-error button:active:not(:disabled) {
  transform: translateY(1px);
}

.workspace-state.is-loading {
  min-height: 8.5rem;
  background: var(--ink-deep); backdrop-filter: none;
  color: var(--paper);
}

.workspace-state.is-loading p {
  color: var(--signal);
}

.workspace-state.is-loading small {
  color: var(--paper-muted);
}

.workspace-state-route {
  display: grid;
  width: min(21rem, 28vw);
  gap: 0.45rem;
}

.workspace-state-route span {
  height: 0.7rem;
  transform-origin: left;
  background: var(--line-dark);
  animation: workspace-route-pulse 1.2s var(--ease-out) infinite alternate;
}

.workspace-state-route span:nth-child(1) {
  width: 100%;
}

.workspace-state-route span:nth-child(2) {
  width: 72%;
  animation-delay: 120ms;
}

.workspace-state-route span:nth-child(3) {
  width: 46%;
  animation-delay: 240ms;
}

.workspace-state.is-error {
  border-bottom-color: var(--error);
  background: var(--ink-soft); backdrop-filter: none;
}

.workspace-state.is-error .workspace-state-index,
.workspace-state.is-warning .workspace-state-index {
  background: var(--warning);
}

.connection-state {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1rem;
  align-items: center;
  padding: 0.8rem clamp(1rem, 4vw, 4rem);
  border-bottom: 1px solid var(--signal-rule);
  background: var(--ink-deep); backdrop-filter: none;
  color: var(--paper);
}

.connection-state p {
  color: var(--signal);
}

.connection-state span {
  color: var(--paper-muted);
}

.run-live-note {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1rem;
  align-items: center;
  padding: 1rem clamp(1rem, 4vw, 4rem);
  border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--signal-soft);
}

.run-live-note > div:first-child {
  display: grid;
  gap: 0.2rem;
}

.run-live-note strong {
  font-family: var(--font-display);
  font-size: 1.05rem;
  font-weight: 400;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.run-live-note span {
  color: var(--paper-muted);
  font-size: 0.8rem;
}

.stop-controls {
  display: flex;
  gap: 0.5rem;
}

.stop-run,
.keep-running {
  min-height: 2.6rem;
  border: 1px solid rgba(242, 235, 221, 0.1);
  border-radius: var(--radius-md);
  font-size: 0.72rem;
  font-weight: 700;
}

.stop-run {
  background: var(--ink-deep); backdrop-filter: none;
  color: var(--paper);
}

.keep-running {
  background: transparent;
  color: var(--paper);
}

.run-live-note > .inline-error {
  grid-column: 1 / -1;
}

.followup-main {
  width: min(100%, 94rem);
  margin: 0 auto;
  padding: clamp(1.15rem, 2vw, 1.8rem) clamp(1rem, 4vw, 4rem)
    clamp(2rem, 3.5vw, 3.5rem);
  outline: none;
}

.conversation-sheet {
  display: grid;
  grid-template-columns: minmax(15rem, 0.55fr) minmax(0, 1.45fr);
  min-height: 36rem;
  border-top: 0.55rem solid var(--signal);
  border-right: 1px solid rgba(242, 235, 221, 0.1);
  border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  border-left: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--ink-raised); backdrop-filter: none;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.conversation-sheet.is-fictional {
  border-top-color: var(--warning);
}

.answer-boundary {
  display: flex;
  flex-direction: column;
  padding: clamp(1.5rem, 3vw, 2.5rem);
  background: var(--ink-deep); backdrop-filter: none;
  color: var(--paper);
}

.answer-boundary .section-kicker {
  color: var(--signal);
}

.conversation-sheet.is-fictional .answer-boundary .section-kicker {
  color: var(--attention);
}

.answer-boundary h2,
.group-intro h2,
.run-map-sheet > header h2,
.group-results > header h2 {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 400;
  letter-spacing: 0.005em;
  line-height: 0.95;
}

.answer-boundary h2 {
  font-size: clamp(2.5rem, 4vw, 4.2rem);
}

.answer-boundary > p:not(.section-kicker) {
  margin: 1.3rem 0 0;
  color: var(--paper-muted);
  font-size: 0.87rem;
  line-height: 1.55;
}

.change-profile {
  width: 100%;
  min-height: 3rem;
  margin-top: 1.5rem;
  justify-content: space-between;
  border: 2px solid var(--warning);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 0.95rem;
  font-weight: 400;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.change-profile::after {
  content: "↓";
  color: var(--attention);
  font-family: var(--font-sans);
  font-weight: 700;
}

.change-profile:hover {
  background: var(--warning);
  color: var(--paper);
}

.answer-facts {
  margin: auto 0 0;
}

.answer-facts > div {
  padding: 0.9rem 0;
  border-top: 1px solid var(--line-dark);
}

.answer-facts dt {
  color: var(--paper-dim);
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.answer-facts dd {
  margin: 0.3rem 0 0;
  color: var(--paper);
  font-size: 0.78rem;
  line-height: 1.4;
}

.conversation-column {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
}

.profile-picker {
  position: relative;
  z-index: 2;
  padding: 1.5rem;
  border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--signal-soft);
}

.profile-picker > header,
.group-results > header,
.profile-selection > header {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  justify-content: space-between;
}

.profile-picker h3,
.conversation-empty h3,
.profile-selection h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 400;
  line-height: 1;
}

.close-picker {
  border: 0;
  border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  background: transparent;
  color: var(--paper);
  font-size: 0.72rem;
}

.picker-warning {
  margin: 0.9rem 0 1.1rem;
  color: var(--paper-muted);
  font-size: 0.78rem;
}

.profile-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-top: 1px solid rgba(242, 235, 221, 0.1);
  border-left: 1px solid rgba(242, 235, 221, 0.1);
}

.profile-list button {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  column-gap: 0.75rem;
  align-items: center;
  min-height: 4.2rem;
  padding: 0.75rem;
  border-width: 0 2px 2px 0;
  border-color: var(--paper);
  border-radius: var(--radius-md);
  background: var(--ink-raised); backdrop-filter: none;
  color: var(--paper);
  text-align: left;
}

.profile-list button:hover,
.profile-list button[aria-pressed="true"] {
  background: var(--warning);
  color: var(--paper);
}

.profile-list button > span {
  grid-row: 1 / span 2;
  font-family: var(--font-display);
  font-size: 1.4rem;
}

.profile-list button strong {
  overflow: hidden;
  font-size: 0.8rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-list button small {
  overflow: hidden;
  color: var(--paper-muted);
  font-size: 0.66rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-load-state,
.record-load-error {
  display: grid;
  gap: 0.45rem;
  align-items: start;
  justify-items: start;
  padding: 1rem;
  border: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--ink-raised); backdrop-filter: none;
  color: var(--paper-muted);
  font-size: 0.78rem;
}

.profile-load-state.is-error,
.record-load-error {
  border-left: 0.5rem solid var(--error);
}

.profile-load-state strong,
.record-load-error strong {
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 400;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.profile-load-state button,
.record-load-error button {
  margin-top: 0.35rem;
}

.messages-list {
  min-height: 20rem;
  max-height: 38rem;
  flex: 1;
  padding: clamp(1.2rem, 3vw, 2.5rem);
  overflow-y: auto;
  background: var(--ink-raised); backdrop-filter: none;
}

.conversation-empty {
  display: grid;
  align-content: center;
  min-height: 15rem;
  max-width: 42rem;
}

.conversation-empty .section-kicker {
  color: var(--paper-muted);
}

.conversation-empty h3 {
  max-width: 19ch;
  font-size: clamp(2.2rem, 4vw, 3.8rem);
}

.conversation-empty > p:not(.section-kicker) {
  max-width: 53ch;
  margin: 1rem 0 0;
  color: var(--paper-muted);
  line-height: 1.55;
}

.suggested-questions {
  display: grid;
  margin-top: 1.2rem;
  border-top: 1px solid rgba(242, 235, 221, 0.1);
}

.suggested-questions button {
  justify-content: flex-start;
  min-height: 3rem;
  padding: 0.7rem 0;
  border: 0;
  border-bottom: 1px solid var(--line-light);
  background: transparent;
  color: var(--paper);
  font-size: 0.78rem;
  text-align: left;
}

.suggested-questions button::before {
  margin-right: 0.25rem;
  color: var(--signal-deep);
  content: "→";
  font-weight: 700;
}

.suggested-questions button:hover {
  background: var(--signal-soft);
  color: var(--paper);
  transform: translateX(0.25rem);
}

.conversation-message {
  max-width: 48rem;
  margin-bottom: 1.5rem;
  padding: 1rem 1.1rem;
  border-top: 1px solid rgba(242, 235, 221, 0.1);
  border-bottom: 1px solid var(--line-light);
  background: var(--ink-soft); backdrop-filter: none;
}

.conversation-message.user {
  max-width: 37rem;
  margin-left: auto;
  border-top-color: var(--signal-deep);
  border-left: 0.45rem solid var(--signal);
}

.conversation-message.assistant.is-fictional {
  border-top-color: var(--warning);
  border-left: 0.45rem solid var(--warning);
}

.conversation-message > header {
  display: flex;
  gap: 1rem;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.conversation-message > header span {
  font-family: var(--font-display);
  font-size: 0.85rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.conversation-message > header time {
  color: var(--paper-muted);
  font-family: var(--font-mono);
  font-size: 0.6rem;
}

.answer-copy,
.response-copy {
  color: #292d2a;
  font-size: 0.91rem;
  line-height: 1.65;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.conversation-message > footer {
  margin-top: 0.9rem;
  padding-top: 0.7rem;
  border-top: 1px solid var(--line-light);
  color: var(--paper-muted);
  font-size: 0.66rem;
  font-weight: 600;
  line-height: 1.4;
  text-transform: uppercase;
}

.answer-loading {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  padding: 1rem 0;
  color: var(--paper-muted);
}

.answer-loading span {
  width: 1rem;
  height: 1rem;
  border: 2px solid var(--line-light);
  border-top-color: var(--paper);
  animation: followup-spin 800ms linear infinite;
}

.answer-loading p {
  margin: 0;
  font-size: 0.8rem;
}

.question-composer {
  padding: 1rem clamp(1.2rem, 3vw, 2.5rem);
  border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--signal);
}

.conversation-sheet.is-fictional .question-composer {
  background: var(--warning);
}

.composer-kicker {
  margin: 0 0 0.35rem;
  font-size: 0.66rem;
  font-weight: 800;
  letter-spacing: 0.055em;
  line-height: 1;
  text-transform: uppercase;
}

.question-composer > label,
.group-composer > label {
  display: block;
  margin-bottom: 0.55rem;
  font-family: var(--font-display);
  font-size: 1rem;
  letter-spacing: 0.045em;
  text-transform: uppercase;
}

.question-composer > div {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
}

.question-composer textarea,
.group-composer textarea {
  width: 100%;
  min-height: 4.3rem;
  padding: 0.85rem;
  border: 1px solid rgba(242, 235, 221, 0.1);
  border-radius: var(--radius-md);
  background: var(--ink-raised); backdrop-filter: none;
  color: var(--paper);
  line-height: 1.45;
  resize: vertical;
}

.question-composer button,
.group-composer > button {
  min-width: 7rem;
  border: 1px solid rgba(242, 235, 221, 0.1);
  border-left: 0;
  border-radius: var(--radius-md);
  background: var(--signal);
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 400;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.question-composer button:hover:not(:disabled),
.group-composer > button:hover:not(:disabled) {
  background: var(--ink-deep); backdrop-filter: none;
  color: var(--paper);
}

.question-composer button {
  background: var(--ink-deep); backdrop-filter: none;
  color: var(--paper);
}

.question-composer button:hover:not(:disabled) {
  background: var(--ink-raised); backdrop-filter: none;
  color: var(--paper);
}

.question-composer > p:not(.composer-kicker),
.group-composer > small {
  display: block;
  margin: 0.6rem 0 0;
  color: var(--paper-muted);
  font-size: 0.7rem;
  line-height: 1.4;
}

.inline-error {
  margin: 0.6rem 0 0;
  color: var(--error) !important;
  font-size: 0.76rem !important;
  font-weight: 700;
}

.group-question-sheet,
.run-map-sheet {
  border-top: 0.55rem solid var(--warning);
}

.group-intro,
.run-map-sheet > header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(15rem, 0.4fr);
  gap: 1rem 4rem;
  align-items: end;
  padding: clamp(1.5rem, 4vw, 3.5rem);
  border-right: 1px solid rgba(242, 235, 221, 0.1);
  border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  border-left: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--ink-deep); backdrop-filter: none;
  color: var(--paper);
}

.group-intro .section-kicker,
.run-map-sheet > header .section-kicker {
  grid-column: 1 / -1;
  color: var(--attention);
}

.group-intro h2,
.run-map-sheet > header h2 {
  max-width: 15ch;
  font-size: clamp(2.8rem, 5vw, 5rem);
}

.group-intro > p:not(.section-kicker),
.run-map-sheet > header > p:not(.section-kicker) {
  margin: 0;
  color: var(--paper-muted);
  line-height: 1.55;
}

.fictional-warning,
.run-map-sheet > header > strong {
  grid-column: 1 / -1;
  padding: 0.8rem 1rem;
  border-left: 0.45rem solid var(--warning);
  background: var(--ink-soft);
  color: var(--paper);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.group-builder {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(18rem, 0.6fr);
  gap: 3rem;
  padding: clamp(2rem, 5vw, 4rem) 0;
}

.profile-selection {
  min-width: 0;
}

.profile-selection > header {
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(242, 235, 221, 0.1);
}

.profile-selection > header p,
.group-composer > p {
  margin: 0 0 0.3rem;
  color: var(--paper-muted);
  font-family: var(--font-display);
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.profile-selection > header > strong {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 400;
  text-transform: uppercase;
}

.profile-checklist {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-left: 1px solid rgba(242, 235, 221, 0.1);
}

.profile-checklist label {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr);
  column-gap: 0.65rem;
  align-items: center;
  min-height: 4.2rem;
  padding: 0.7rem;
  border-right: 1px solid rgba(242, 235, 221, 0.1);
  border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--ink-raised); backdrop-filter: none;
  cursor: pointer;
}

.profile-checklist label.checked {
  background: var(--warning);
}

.profile-checklist input {
  width: 1rem;
  height: 1rem;
  accent-color: var(--paper);
}

.profile-checklist label > span {
  grid-row: 1 / span 2;
  grid-column: 2;
  font-family: var(--font-display);
  font-size: 1.25rem;
}

.profile-checklist label > strong,
.profile-checklist label > small {
  grid-column: 3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-checklist label > strong {
  font-size: 0.78rem;
}

.profile-checklist label > small {
  color: var(--paper-muted);
  font-size: 0.65rem;
}

.selection-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.8rem;
}

.selection-actions button {
  border: 0;
  border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  background: transparent;
  color: var(--paper);
  font-size: 0.7rem;
}

.group-composer {
  align-self: start;
  padding: 1.4rem;
  border: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--ink-raised); backdrop-filter: none;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.group-composer textarea {
  min-height: 10rem;
}

.group-composer > button {
  width: 100%;
  min-height: 3.4rem;
  margin-top: 0.8rem;
  border-left: 1px solid rgba(242, 235, 221, 0.1);
}

.group-results {
  padding-top: 3rem;
  border-top: 1px solid rgba(242, 235, 221, 0.1);
}

.group-results > header {
  margin-bottom: 2rem;
}

.group-results > header h2 {
  font-size: clamp(2.5rem, 4vw, 4.2rem);
}

.group-results > header button {
  min-height: 2.8rem;
  border: 1px solid rgba(242, 235, 221, 0.1);
  border-radius: var(--radius-md);
  background: var(--signal);
  color: var(--paper);
  font-size: 0.72rem;
  font-weight: 700;
}

.group-results > article {
  display: grid;
  grid-template-columns: minmax(12rem, 0.36fr) minmax(0, 1fr);
  gap: 1.5rem 3rem;
  padding: 1.5rem 0;
  border-top: 1px solid rgba(242, 235, 221, 0.1);
}

.group-results > article > header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.8rem;
}

.group-results > article > header > span {
  grid-row: 1 / span 2;
  font-family: var(--font-display);
  font-size: 2rem;
}

.group-results > article h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.3rem;
  font-weight: 400;
  line-height: 1;
}

.group-results > article header p {
  margin: 0.3rem 0 0;
  color: var(--paper-muted);
  font-size: 0.68rem;
}

.group-results > article > footer {
  grid-column: 2;
  padding-left: 0.8rem;
  border-left: 0.35rem solid var(--warning);
  color: var(--paper-muted);
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: uppercase;
}

.run-map-sheet {
  border-top-color: var(--signal);
}

.run-map-sheet > header .section-kicker {
  color: var(--signal);
}

.run-map-sheet > header > strong {
  border-left-color: var(--signal);
}

.map-frame {
  min-height: 34rem;
  border-right: 1px solid rgba(242, 235, 221, 0.1);
  border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  border-left: 1px solid rgba(242, 235, 221, 0.1);
  background: var(--ink-soft);
}

.empty-state,
.record-empty {
  padding: 1rem 0;
  color: var(--paper-muted);
  font-size: 0.8rem;
}

.secondary-record {
  border-top: 0.55rem solid var(--signal);
  background: var(--ink-deep); backdrop-filter: none;
  color: var(--paper);
}

.secondary-record > summary {
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  min-height: 5.5rem;
  padding: 1.2rem clamp(1rem, 5vw, 5rem);
  list-style: none;
  cursor: pointer;
}

.secondary-record > summary::-webkit-details-marker {
  display: none;
}

.secondary-record > summary::before {
  display: grid;
  width: 2rem;
  height: 2rem;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--signal-rule);
  color: var(--signal);
  content: "+";
  font-size: 1.25rem;
}

.secondary-record[open] > summary::before {
  content: "−";
}

.secondary-record > summary span {
  margin-right: auto;
  font-family: var(--font-display);
  font-size: 1.2rem;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.secondary-record > summary small {
  color: var(--paper-dim);
  font-family: var(--font-mono);
  font-size: 0.62rem;
  text-transform: uppercase;
}

.secondary-grid {
  display: grid;
  grid-template-columns: 1.25fr 0.7fr 1fr 0.8fr;
  gap: 1px;
  border-top: 1px solid var(--line-dark);
  background: var(--line-dark);
}

.secondary-grid > section {
  min-width: 0;
  padding: clamp(1rem, 2.5vw, 2.2rem);
  background: var(--ink-deep); backdrop-filter: none;
}

.secondary-grid h2 {
  margin: 0 0 1.2rem;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 400;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.report-context-record > h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.6rem;
  font-weight: 400;
}

.report-context-record > p {
  color: var(--paper-muted);
  font-size: 0.76rem;
  line-height: 1.5;
}

.context-section {
  border-top: 1px solid var(--line-dark);
}

.context-section > summary {
  display: flex;
  gap: 0.7rem;
  padding: 0.75rem 0;
  color: var(--paper-muted);
  font-size: 0.72rem;
  cursor: pointer;
}

.context-section > summary span {
  color: var(--signal);
  font-family: var(--font-display);
}

.context-section > div {
  max-height: 15rem;
  padding: 0 0 1rem;
  overflow: auto;
  color: var(--paper-dim);
  font-size: 0.7rem;
  line-height: 1.5;
  white-space: pre-wrap;
}

.run-record dl {
  margin: 0;
}

.run-record dl > div {
  padding: 0.75rem 0;
  border-top: 1px solid var(--line-dark);
}

.run-record dt {
  color: var(--paper-dim);
  font-size: 0.62rem;
  text-transform: uppercase;
}

.run-record dd {
  margin: 0.25rem 0 0;
  overflow-wrap: anywhere;
  font-family: var(--font-mono);
  font-size: 0.69rem;
}

.advanced-control {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.7rem;
  margin-top: 1.2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--line-dark);
  cursor: pointer;
}

.advanced-control input {
  margin-top: 0.2rem;
  accent-color: var(--signal);
}

.advanced-control span {
  display: grid;
  gap: 0.25rem;
}

.advanced-control strong {
  font-size: 0.72rem;
}

.advanced-control small {
  color: var(--paper-dim);
  font-size: 0.65rem;
  line-height: 1.4;
}

.trace-record ol,
.diagnostic-record ol {
  max-height: 28rem;
  margin: 0;
  padding: 0;
  overflow: auto;
  list-style: none;
}

.trace-record li,
.diagnostic-record li {
  padding: 0.75rem 0;
  border-top: 1px solid var(--line-dark);
}

.trace-record li header {
  display: flex;
  gap: 0.7rem;
  align-items: baseline;
  justify-content: space-between;
}

.trace-record li strong {
  color: var(--paper);
  font-size: 0.7rem;
}

.trace-record time,
.diagnostic-record time {
  color: var(--signal);
  font-family: var(--font-mono);
  font-size: 0.58rem;
}

.trace-record li > p {
  margin: 0.35rem 0 0;
  color: var(--paper-dim);
  font-size: 0.64rem;
}

.trace-record blockquote {
  margin: 0.55rem 0 0;
  padding-left: 0.6rem;
  border-left: 0.25rem solid var(--warning);
  color: var(--paper-muted);
  font-size: 0.68rem;
  line-height: 1.45;
}

.diagnostic-record li {
  display: grid;
  grid-template-columns: 3.5rem minmax(0, 1fr);
  gap: 0.6rem;
  color: var(--paper-muted);
  font-family: var(--font-mono);
  font-size: 0.62rem;
  line-height: 1.4;
}

@keyframes followup-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes workspace-route-pulse {
  from {
    opacity: 0.35;
    transform: scaleX(0.76);
  }

  to {
    opacity: 1;
    transform: scaleX(1);
  }
}

@media (max-width: 1100px) {
  .followup-masthead {
    grid-template-columns: minmax(0, 1fr) minmax(14rem, 18rem);
  }

  .followup-masthead::after {
    right: 17rem;
  }

  .followup-modes {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .mode-guide {
    grid-column: 1 / -1;
    min-height: 3rem;
    border-right: 0;
    border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  }

  .mode-guide small {
    display: none;
  }

  .followup-modes button:nth-of-type(2) {
    border-right: 0;
  }

  .followup-modes button:nth-of-type(-n + 2) {
    border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  }

  .secondary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 800px) {
  .followup-masthead {
    grid-template-columns: 1fr;
    gap: 2.5rem;
  }

  .followup-masthead::after {
    top: auto;
    right: 0;
    bottom: 0;
    width: 35%;
    height: 4rem;
    transform: skewX(-20deg);
  }

  .truth-stamp {
    min-height: 0;
  }

  .conversation-sheet {
    grid-template-columns: 1fr;
  }

  .conversation-column {
    order: -1;
  }

  .answer-boundary {
    min-height: 0;
  }

  .answer-facts {
    margin-top: 2rem;
  }

  .group-intro,
  .run-map-sheet > header,
  .group-builder,
  .group-results > article {
    grid-template-columns: 1fr;
  }

  .group-intro > *,
  .run-map-sheet > header > *,
  .group-results > article > footer {
    grid-column: auto;
  }

  .group-results > article > footer {
    margin-left: 0;
  }
}

@media (max-width: 600px) {
  .followup-masthead {
    min-height: 0;
    gap: 0.75rem;
    padding: 0.85rem 1rem 1rem;
  }

  .followup-masthead h1 {
    max-width: none;
    font-size: clamp(1.95rem, 8vw, 2.25rem);
    line-height: 0.9;
  }

  .route-label {
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    font-size: 0.78rem;
  }

  .route-label span {
    width: 2rem;
    height: 2rem;
  }

  .masthead-copy > p:last-child {
    display: none;
  }

  .truth-stamp {
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-rows: auto auto;
    align-content: center;
    align-items: center;
    column-gap: 1rem;
    min-height: 0;
    padding: 0.55rem 0.65rem;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
  }

  .truth-stamp span {
    grid-column: 1 / -1;
    grid-row: 1;
  }

  .truth-stamp strong {
    grid-column: 1;
    grid-row: 2;
    max-width: none;
    margin: 0.25rem 0 0;
    font-size: 1.55rem;
    line-height: 0.95;
  }

  .truth-stamp b {
    grid-column: 2;
    grid-row: 2;
    text-align: right;
  }

  .truth-stamp small {
    display: none;
  }

  .mode-guide {
    min-height: 2.35rem;
    padding: 0.45rem 0.65rem;
  }

  .mode-guide span {
    font-size: 0.78rem;
  }

  .followup-modes {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .followup-modes button,
  .followup-modes button:nth-of-type(2) {
    min-height: 3.35rem;
    padding: 0.4rem 0.55rem;
    border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  }

  .followup-modes button:nth-of-type(odd) {
    border-right: 1px solid rgba(242, 235, 221, 0.1);
  }

  .followup-modes button:nth-of-type(even) {
    border-right: 0;
  }

  .followup-modes button:nth-of-type(n + 3) {
    border-bottom: 0;
  }

  .followup-modes button > span {
    font-size: 1.2rem;
  }

  .followup-modes strong {
    font-size: 0.78rem;
  }

  .followup-modes button small {
    display: none;
  }

  .run-live-note {
    grid-template-columns: 1fr;
  }

  .workspace-state,
  .connection-state {
    grid-template-columns: 1fr;
    padding: 0.85rem 1rem;
  }

  .workspace-state-copy {
    align-items: start;
    gap: 0.7rem;
  }

  .workspace-state-index {
    width: 2.4rem;
    height: 2.4rem;
    font-size: 1.1rem;
  }

  .workspace-state h2 {
    font-size: 1.25rem;
  }

  .workspace-state-route {
    width: 100%;
  }

  .workspace-state > button,
  .connection-state > button {
    width: 100%;
  }

  .stop-controls {
    flex-wrap: wrap;
  }

  .followup-main {
    padding: 0.65rem 0.55rem 2rem;
  }

  .conversation-sheet {
    border-right-width: 2px;
    border-bottom-width: 2px;
    border-left-width: 2px;
    box-shadow: none;
  }

  .answer-boundary,
  .messages-list,
  .profile-picker {
    padding: 1rem;
  }

  .question-composer {
    padding: 0.75rem;
  }

  .messages-list {
    min-height: 13rem;
  }

  .conversation-empty {
    min-height: 11rem;
  }

  .composer-kicker {
    margin-bottom: 0.3rem;
  }

  .question-composer > label {
    margin-bottom: 0.4rem;
    font-size: 0.92rem;
  }

  .question-composer textarea {
    min-height: 3.5rem;
  }

  .answer-boundary h2 {
    font-size: 2.7rem;
  }

  .profile-list,
  .profile-checklist {
    grid-template-columns: 1fr;
  }

  .question-composer > div {
    grid-template-columns: minmax(0, 1fr) 5rem;
  }

  .question-composer button {
    min-width: 5rem;
    min-height: 0;
    border-top: 1px solid rgba(242, 235, 221, 0.1);
    border-left: 0;
  }

  .conversation-message,
  .conversation-message.user {
    max-width: 100%;
  }

  .group-intro,
  .run-map-sheet > header {
    padding: 1.2rem;
  }

  .group-intro h2,
  .run-map-sheet > header h2 {
    font-size: 3rem;
  }

  .group-builder {
    gap: 2rem;
  }

  .group-composer {
    box-shadow: none;
  }

  .group-results > header {
    align-items: stretch;
    flex-direction: column;
  }

  .group-results > article {
    gap: 1rem;
  }

  .secondary-record > summary {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .secondary-record > summary small {
    width: 100%;
    padding-left: 3rem;
  }

  .secondary-grid {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .skip-link,
  .followup-modes button,
  .suggested-questions button {
    transition: none;
  }

  .answer-loading span {
    animation: none;
  }

  .workspace-state-route span {
    animation: none;
  }
}
</style>
