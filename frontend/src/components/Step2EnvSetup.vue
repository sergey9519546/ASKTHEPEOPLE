<template>
  <div class="env-setup-panel">
    <div class="scroll-container">
      <section
        class="preparation-banner"
        :class="`is-${preparationStatus}`"
        :role="preparationStatus === 'error' ? 'alert' : 'status'"
        aria-live="polite"
      >
        <div>
          <span class="preparation-label">Assumption preparation</span>
          <strong>{{ preparationTitle }}</strong>
          <p>{{ preparationMessage }}</p>
        </div>
        <div
          v-if="preparationStatus === 'processing'"
          class="preparation-progress"
          role="progressbar"
          aria-label="Assumption preparation progress"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuenow="prepareProgress"
        >
          <span :style="{ width: `${prepareProgress}%` }"></span>
        </div>
        <button
          v-if="preparationStatus === 'error'"
          class="retry-button"
          type="button"
          @click="startPrepareSimulation"
        >
          Try preparation again
        </button>
      </section>

      <!-- Step 01: Agent Profile Generation -->
      <div
        class="step-card"
        :class="{ active: phase === 1, completed: phase > 1 }"
      >
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">01</span>
            <span class="step-title">Create synthetic perspectives</span>
          </div>
          <div class="step-status">
            <span v-if="preparationStatus === 'error'" class="badge error">NEEDS ATTENTION</span>
            <span v-else-if="profiles.length > 0 && phase > 1" class="badge success"
              >COMPLETED</span
            >
            <span v-else-if="preparationStatus === 'processing' && phase >= 1" class="badge processing"
              >{{ profiles.length }} / {{ expectedTotal || "?" }}</span
            >
            <span v-else class="badge pending">WAITING</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">GENERATED PROFILES · NOT REAL PEOPLE</p>
          <p class="description">
            Fictional profiles are generated from patterns in the source map.
            They are scenario devices, not sampled respondents or digital twins.
          </p>

          <!-- Profiles Grid -->
          <div v-if="profiles.length > 0" class="profiles-list">
            <button
              v-for="profile in displayProfiles"
              :key="profile.id"
              class="profile-card"
              type="button"
              :aria-label="`Review generated profile ${profile.name || profile.username}`"
              @click="selectProfile(profile)"
            >
              <div class="profile-header">
                <span class="profile-realname">{{ profile.name }}</span>
                <span class="profile-username">@{{ profile.username }}</span>
              </div>
              <div class="profile-meta">
                <span class="profile-profession">{{
                  profile.profession || "Generated profile"
                }}</span>
              </div>
              <p class="profile-bio">{{ truncateBio(profile.bio) }}</p>
              <div class="profile-topics">
                <span
                  v-for="topic in profile.interested_topics?.slice(0, 3)"
                  :key="topic"
                  class="topic-tag"
                  >{{ topic }}</span
                >
                <span
                  v-if="profile.interested_topics?.length > 3"
                  class="topic-more"
                  >+{{ profile.interested_topics.length - 3 }}</span
                >
              </div>
            </button>
          </div>
          <p v-else class="empty-state">
            Generated profiles will appear here when they are ready.
          </p>

          <div class="action-section" v-if="profiles.length > 6">
            <button
              class="action-btn secondary"
              type="button"
              @click="showProfilesDetail = !showProfilesDetail"
            >
              {{ showProfilesDetail ? "Show fewer" : "View all profiles" }}
            </button>
          </div>
        </div>
      </div>

      <!-- Step 02: Simulation Configuration -->
      <div
        class="step-card"
        :class="{ active: phase === 2, completed: phase > 2 }"
      >
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">02</span>
            <span class="step-title">Set the scenario rules</span>
          </div>
          <div class="step-status">
            <span v-if="preparationStatus === 'error'" class="badge error">NEEDS ATTENTION</span>
            <span v-else-if="phase > 2" class="badge success">COMPLETED</span>
            <span v-else-if="phase === 2" class="badge processing"
              >GENERATING</span
            >
            <span v-else class="badge pending">WAITING</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">ASSUMPTIONS</p>
          <p class="description">
            Review the channels, timing, and participation rules that will shape
            this synthetic run.
          </p>

          <!-- Config Blocks -->
          <div v-if="simulationConfig" class="config-detail-panel">
            <section class="assumption-brief" aria-label="Scenario assumption brief">
              <article>
                <span>Where activity happens</span>
                <strong>Two generated conversation spaces</strong>
                <p>
                  One favors short, fast-moving posts. The other keeps
                  discussion grouped around shared topics.
                </p>
              </article>
              <article>
                <span>Who takes part</span>
                <strong>{{ profiles.length }} fictional perspectives</strong>
                <p>
                  These profiles are scenario devices created from the source
                  map—not sampled people or predicted individuals.
                </p>
              </article>
              <article>
                <span>How long it runs</span>
                <strong>{{ plainRunLength }}</strong>
                <p>
                  The same starting conditions are applied across both spaces
                  so their generated activity can be compared.
                </p>
              </article>
            </section>

            <details class="advanced-assumptions">
              <summary>
                <span>
                  <strong>Advanced model settings</strong>
                  <small>Optional raw weights and timing</small>
                </span>
                <span aria-hidden="true">+</span>
              </summary>
              <div class="advanced-assumptions-body">
                <!-- Platform Strategy -->
                <div class="config-block">
                  <div class="config-block-header">
                    <span class="config-block-title">CONVERSATION SPACES</span>
                    <span class="config-block-badge">TWO SPACES</span>
                  </div>
                  <div class="platforms-grid">
                    <div class="platform-card">
                      <div class="platform-card-header">
                        <span class="platform-name">SHORT-POST CHANNEL</span>
                      </div>
                      <div class="platform-params">
                        <div class="param-row">
                          <span class="param-label">Recency weighting</span>
                          <span class="param-value">{{
                            simulationConfig.twitter_config?.recency_weight ??
                            simulationConfig.platform_config?.twitter?.recency_weight ??
                            "—"
                          }}</span>
                        </div>
                        <div class="param-row">
                          <span class="param-label">Viral threshold</span>
                          <span class="param-value">{{
                            simulationConfig.twitter_config?.viral_threshold ??
                            simulationConfig.platform_config?.twitter?.viral_threshold ??
                            "—"
                          }}</span>
                        </div>
                      </div>
                    </div>
                    <div class="platform-card">
                      <div class="platform-card-header">
                        <span class="platform-name">TOPIC COMMUNITY</span>
                      </div>
                      <div class="platform-params">
                        <div class="param-row">
                          <span class="param-label">Relevance weighting</span>
                          <span class="param-value">{{
                            simulationConfig.reddit_config?.relevance_weight ??
                            simulationConfig.platform_config?.reddit?.relevance_weight ??
                            "—"
                          }}</span>
                        </div>
                        <div class="param-row">
                          <span class="param-label">Echo-chamber strength</span>
                          <span class="param-value">{{
                            simulationConfig.reddit_config?.echo_chamber_strength ??
                            simulationConfig.platform_config?.reddit?.echo_chamber_strength ??
                            "—"
                          }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Time Config -->
                <div class="config-block">
                  <div class="config-block-header">
                    <span class="config-block-title">RUN LENGTH</span>
                  </div>
                  <div class="config-grid">
                    <div class="config-item">
                      <span class="config-item-label">SIMULATED HOURS</span>
                      <span class="config-item-value">{{
                        simulationConfig.time_config?.total_simulation_hours
                      }}</span>
                    </div>
                    <div class="config-item">
                      <span class="config-item-label">MINUTES PER ROUND</span>
                      <span class="config-item-value">{{
                        simulationConfig.time_config?.minutes_per_round
                      }}</span>
                    </div>
                    <div class="config-item">
                      <span class="config-item-label">PACING</span>
                      <span class="config-item-value">ADAPTIVE</span>
                    </div>
                    <div class="config-item">
                      <span class="config-item-label">TIMEZONE</span>
                      <span class="config-item-value">UTC</span>
                    </div>
                  </div>
                </div>
              </div>
            </details>
          </div>
        </div>
      </div>

      <!-- Step 03: Narrative Orchestration -->
      <div
        class="step-card"
        :class="{ active: phase === 3, completed: phase > 3 }"
      >
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">03</span>
            <span class="step-title">Define the starting conditions</span>
          </div>
          <div class="step-status">
            <span v-if="preparationStatus === 'error'" class="badge error">NEEDS ATTENTION</span>
            <span v-else-if="phase > 3" class="badge success">READY</span>
            <span v-else-if="phase === 3" class="badge processing"
              >DEFINING</span
            >
            <span v-else class="badge pending">WAITING</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">SCENARIO START</p>
          <p class="description">
            These prompts establish what the generated profiles encounter first.
            Inspect them for assumptions or framing bias before continuing.
          </p>

          <div
            v-if="simulationConfig?.event_config"
            class="orchestration-content"
          >
            <!-- Narrative Direction -->
            <div class="narrative-box">
              <span class="box-label"
                >STARTING DIRECTION</span
              >
              <p class="narrative-text">
                {{ simulationConfig.event_config.narrative_direction }}
              </p>
            </div>

            <!-- Hot Topics -->
            <div class="narrative-box topics-section">
              <span class="box-label">TOPICS TO INTRODUCE</span>
              <div class="hot-topics-grid">
                <span
                  v-for="topic in simulationConfig.event_config.hot_topics"
                  :key="topic"
                  class="hot-topic-tag"
                  >{{ topic }}</span
                >
              </div>
            </div>

            <!-- Initial Posts -->
            <div
              v-if="simulationConfig.event_config.initial_posts?.length"
              class="initial-posts-section"
            >
              <span class="box-label">OPENING MESSAGES</span>
              <div class="posts-timeline">
                <div
                  v-for="(post, idx) in simulationConfig.event_config
                    .initial_posts"
                  :key="idx"
                  class="timeline-item"
                >
                  <div class="timeline-marker"></div>
                  <div class="timeline-content">
                    <div class="post-header">
                      <span class="post-role">Generated profile</span>
                      <div class="post-agent-info">
                        <span class="post-username"
                          >@{{ getAgentUsername(post.poster_agent_id ?? post.agent_id) }}</span
                        >
                        <span class="post-id">{{ platformLabel(post.platform) }}</span>
                      </div>
                    </div>
                    <p class="post-text">{{ post.content }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 04: Simulation Activation -->
      <div
        class="step-card"
        :class="{ active: phase === 4, completed: phase >= 4 }"
      >
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">04</span>
            <span class="step-title">Ready to run</span>
          </div>
          <div class="step-status">
            <span v-if="canStartSimulation" class="badge success">READY</span>
            <span v-else class="badge pending">WAITING</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">CHECK THE ASSUMPTIONS BEFORE CONTINUING</p>
          <p v-if="canStartSimulation" class="description">
            The starting conditions are ready. Choose the run length, then
            start the scenarios.
          </p>
          <p v-else class="description">
            Scenario length becomes available only after the profiles, timing
            rules, and starting conditions pass preparation.
          </p>

          <!-- Rounds Configuration -->
          <div v-if="hasValidConfig" class="rounds-config-section">
            <div class="rounds-header">
              <div class="header-left">
                <span class="section-title">Scenario length</span>
                <span class="section-desc"
                  >Choose how long the generated interactions should
                  continue.</span
                >
              </div>
              <div class="header-right">
                <label class="switch-control">
                  <input type="checkbox" v-model="useCustomRounds" />
                  <span class="switch-track"></span>
                  <span class="switch-label">{{
                    useCustomRounds ? "CUSTOM" : "SUGGESTED"
                  }}</span>
                </label>
              </div>
            </div>

            <!-- Rounds Select -->
            <div class="rounds-content">
              <Transition name="fade" mode="out-in">
                <!-- Custom Slider -->
                <div v-if="useCustomRounds" key="manual" class="manual-config">
                  <div class="slider-display">
                    <div class="slider-main-value">
                      <span class="val-num">{{ customMaxRounds }}</span>
                      <span class="val-unit">Steps</span>
                    </div>
                    <div class="slider-meta-info">
                      EST.
                      {{
                        (
                          (customMaxRounds *
                            (simulationConfig?.time_config?.minutes_per_round ||
                              15)) /
                          60
                        ).toFixed(1)
                      }}
                      HOURS
                    </div>
                  </div>
                  <div class="range-wrapper">
                    <input
                      id="scenario-rounds"
                      type="range"
                      v-model.number="customMaxRounds"
                      min="10"
                      max="200"
                      step="5"
                      class="minimal-slider"
                      aria-label="Number of scenario steps"
                      :aria-valuetext="`${customMaxRounds} scenario steps, about ${customEstimatedHours} simulated hours`"
                      :style="{
                        '--percent': ((customMaxRounds - 10) / 190) * 100 + '%',
                      }"
                    />
                    <div class="range-marks">
                      <span>10</span>
                      <button
                        class="mark-recommend"
                        :class="{ active: customMaxRounds === 40 }"
                        type="button"
                        @click="customMaxRounds = 40"
                        >SUGGESTED: 40
                      </button>
                      <span>200</span>
                    </div>
                  </div>
                </div>

                <!-- Auto Config Info -->
                <div v-else key="auto" class="auto-config">
                  <div class="auto-info-card">
                    <div class="auto-value">
                      <span class="val-num">{{
                        autoGeneratedRounds || "..."
                      }}</span>
                      <span class="val-unit">Steps</span>
                    </div>
                    <div class="auto-content">
                      <div class="auto-meta-row">
                        <span class="duration-badge"
                          >SIMULATED TIME:
                          {{
                            simulationConfig?.time_config
                              ?.total_simulation_hours || "?"
                          }}H</span
                        >
                      </div>
                      <div class="auto-desc">
                        <p>Suggested from the source map and starting conditions.</p>
                        <button
                          class="highlight-tip"
                          type="button"
                          @click="useCustomRounds = true"
                        >
                          Choose a different length →
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </Transition>
            </div>
          </div>
          <div v-else class="rounds-unavailable">
            <strong>Scenario length is not available yet</strong>
            <span>
              Complete preparation first; the suggested length is calculated
              from the prepared timing rules.
            </span>
          </div>

          <!-- Final Action -->
          <div class="action-section">
            <button
              class="action-btn"
              type="button"
              :disabled="!canStartSimulation"
              :aria-describedby="!canStartSimulation ? 'run-prerequisites' : undefined"
              @click="handleStartSimulation"
            >
              RUN THE SCENARIOS →
            </button>
            <p
              v-if="!canStartSimulation"
              id="run-prerequisites"
              class="readiness-note"
              aria-live="polite"
            >
              {{ startRequirement }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Profile Detail Modal -->
    <Transition name="modal">
      <div
        v-if="selectedProfile"
        class="profile-modal-overlay"
        @click.self="closeProfile"
      >
        <div
          ref="profileDialog"
          class="profile-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="profile-modal-title"
          tabindex="-1"
          @keydown="handleProfileKeydown"
        >
          <div class="modal-header">
            <div class="modal-header-info">
              <div class="modal-name-row">
                <span id="profile-modal-title" class="modal-realname">{{
                  selectedProfile.name
                }}</span>
                <span class="modal-username"
                  >@{{ selectedProfile.username }}</span
                >
              </div>
              <span class="modal-profession">{{
                selectedProfile.profession || "Generated profile"
              }}</span>
            </div>
            <button
              ref="profileCloseButton"
              class="close-btn"
              type="button"
              aria-label="Close generated profile"
              @click="closeProfile"
            >
              ×
            </button>
          </div>

          <div class="modal-body">
            <!-- Basic Info -->
            <div class="modal-info-grid">
              <div class="info-item">
                <span class="info-label">Generated age</span>
                <span class="info-value"
                  >{{ selectedProfile.age || "-" }} yrs</span
                >
              </div>
              <div class="info-item">
                <span class="info-label">Generated gender</span>
                <span class="info-value">{{
                  { male: "Male", female: "Female", other: "Other" }[
                    selectedProfile.gender
                  ] || selectedProfile.gender
                }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Country/Region</span>
                <span class="info-value">{{
                  selectedProfile.country || "-"
                }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Generated personality label</span>
                <span class="info-value mbti">{{
                  selectedProfile.mbti || "-"
                }}</span>
              </div>
            </div>

            <!-- Bio -->
            <div class="modal-section">
              <span class="section-label">Generated profile background</span>
              <p class="section-bio">
                {{ selectedProfile.bio || "No bio available" }}
              </p>
            </div>

            <!-- Interested Topics -->
            <div
              class="modal-section"
              v-if="selectedProfile.interested_topics?.length"
            >
              <span class="section-label">Generated scenario topics</span>
              <div class="topics-grid">
                <span
                  v-for="topic in selectedProfile.interested_topics"
                  :key="topic"
                  class="topic-item"
                  >{{ topic }}</span
                >
              </div>
            </div>

            <!-- Detailed Persona -->
            <div class="modal-section" v-if="selectedProfile.persona">
              <span class="section-label">Scenario behavior notes</span>

              <div class="persona-dimensions">
                <div class="dimension-card">
                  <span class="dim-title">Possible event path</span>
                  <span class="dim-desc">A generated path within this scenario</span>
                </div>
                <div class="dimension-card">
                  <span class="dim-title">Response tendencies</span>
                  <span class="dim-desc"
                    >Behavioral habits and style preferences</span
                  >
                </div>
                <div class="dimension-card">
                  <span class="dim-title">Synthetic memory context</span>
                  <span class="dim-desc"
                    >Generated context used during the run</span
                  >
                </div>
                <div class="dimension-card">
                  <span class="dim-title">Generated connection patterns</span>
                  <span class="dim-desc"
                    >Connections used inside this synthetic scenario</span
                  >
                </div>
              </div>

              <div class="persona-content">
                <p class="section-persona">{{ selectedProfile.persona }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <div class="activity-status" role="status" aria-live="polite">
      <span>Current status</span>
      <strong>{{ latestActivityMessage }}</strong>
    </div>
    <details v-if="systemLogs?.length" class="activity-disclosure">
      <summary>
        Detailed activity
        <span>{{ systemLogs.length }} {{ systemLogs.length === 1 ? "update" : "updates" }}</span>
      </summary>
      <div class="activity-list">
        <div class="activity-line" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="activity-time">{{ log.time }}</span>
          <span>{{ log.msg }}</span>
        </div>
      </div>
    </details>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import {
  getPrepareStatus,
  getSimulationConfigRealtime,
  getSimulationProfilesRealtime,
  prepareSimulation,
} from "../api/simulation";

const props = defineProps({
  simulationId: String,
  projectData: Object,
  graphData: Object,
  systemLogs: { type: Array, default: () => [] },
});

const emit = defineEmits(["go-back", "next-step", "add-log", "update-status"]);

// State
const phase = ref(0);
const taskId = ref(null);
const prepareProgress = ref(0);
const currentStage = ref("");
const progressMessage = ref("");
const profiles = ref([]);
const entityTypes = ref([]);
const expectedTotal = ref(null);
const simulationConfig = ref(null);
const selectedProfile = ref(null);
const showProfilesDetail = ref(true);
const preparationStatus = ref("idle");
const preparationError = ref("");
const profileDialog = ref(null);
const profileCloseButton = ref(null);
let profileReturnTarget = null;

let lastLoggedMessage = "";
let lastLoggedProfileCount = 0;
let lastLoggedConfigStage = "";

// Simulation rounds configuration
const useCustomRounds = ref(false);
const customMaxRounds = ref(40);

// Watch stage to update phase
watch(currentStage, (newStage) => {
  if (
    newStage === "Generating Agent Profiles" ||
    newStage === "generating_profiles"
  ) {
    phase.value = 1;
  } else if (
    newStage === "Generating Simulation Config" ||
    newStage === "generating_config"
  ) {
    phase.value = 2;
    if (!configTimer) {
      addLog("Drafting the conversation spaces and starting conditions…");
      startConfigPolling();
    }
  } else if (
    newStage === "Preparing Simulation Scripts" ||
    newStage === "copying_scripts"
  ) {
    phase.value = 2;
  }
});

const autoGeneratedRounds = computed(() => {
  if (!simulationConfig.value?.time_config) {
    return null;
  }
  const totalHours = simulationConfig.value.time_config.total_simulation_hours;
  const minutesPerRound = simulationConfig.value.time_config.minutes_per_round;
  if (!totalHours || !minutesPerRound) {
    return null;
  }
  const calculatedRounds = Math.round((totalHours * 60) / minutesPerRound);
  return Math.min(200, Math.max(calculatedRounds, 40));
});

const resolvedMaxRounds = computed(() =>
  Number(useCustomRounds.value ? customMaxRounds.value : autoGeneratedRounds.value),
);
const hasValidRounds = computed(
  () =>
    Number.isInteger(resolvedMaxRounds.value) &&
    resolvedMaxRounds.value >= 10 &&
    resolvedMaxRounds.value <= 200,
);
const hasValidConfig = computed(() => {
  const config = simulationConfig.value;
  const hasPlatformRules = Boolean(
    config?.platform_config ||
      config?.twitter_config ||
      config?.reddit_config ||
      Object.keys(config?.platform_profiles || {}).length,
  );
  return Boolean(
    config &&
      Number(config.time_config?.total_simulation_hours) > 0 &&
      Number(config.time_config?.minutes_per_round) > 0 &&
      config.event_config &&
      typeof config.event_config === "object" &&
      hasPlatformRules,
  );
});
const canStartSimulation = computed(
  () =>
    preparationStatus.value === "completed" &&
    profiles.value.length > 0 &&
    hasValidConfig.value &&
    hasValidRounds.value,
);
const customEstimatedHours = computed(() =>
  (
    (Number(customMaxRounds.value) *
      Number(simulationConfig.value?.time_config?.minutes_per_round || 15)) /
    60
  ).toFixed(1),
);
const plainRunLength = computed(() => {
  const hours = Number(
    simulationConfig.value?.time_config?.total_simulation_hours,
  );
  if (!Number.isFinite(hours) || hours <= 0) {
    return "Timing is being prepared";
  }
  return `About ${hours} simulated ${hours === 1 ? "hour" : "hours"}`;
});
const preparationTitle = computed(() => {
  const labels = {
    idle: "Waiting to begin",
    processing: "Building the assumptions",
    completed: "Assumptions ready for review",
    error: "Preparation needs attention",
  };
  return labels[preparationStatus.value];
});
const preparationMessage = computed(() => {
  if (preparationStatus.value === "error") return preparationError.value;
  if (preparationStatus.value === "completed") {
    return `${profiles.value.length} generated profiles and the scenario rules are ready. Review them before running.`;
  }
  if (preparationStatus.value === "processing") {
    return (
      progressMessage.value ||
      currentStage.value ||
      "Creating generated profiles and scenario rules…"
    );
  }
  return "Preparation will start when this step opens.";
});
const startRequirement = computed(() => {
  if (preparationStatus.value === "error") {
    return "Fix the preparation error above and try again.";
  }
  if (profiles.value.length === 0) return "At least one generated profile is required.";
  if (!hasValidConfig.value) return "Valid timing, platform, and starting-condition rules are required.";
  if (!hasValidRounds.value) {
    return "Choose between 10 and 200 whole-number scenario steps.";
  }
  return "Wait until assumption preparation finishes.";
});
const latestActivityMessage = computed(
  () => props.systemLogs.at(-1)?.msg || preparationMessage.value,
);

let pollTimer = null;
let profilesTimer = null;
let configTimer = null;

// Polling intervals (ms)
const STATUS_POLL_INTERVAL_MS = 2000;
const PROFILES_POLL_INTERVAL_MS = 3000;
const CONFIG_POLL_INTERVAL_MS = 2000;

const displayProfiles = computed(() => {
  if (showProfilesDetail.value) {
    return profiles.value;
  }
  return profiles.value.slice(0, 6);
});

const getAgentUsername = (agentId) => {
  if (profiles.value && profiles.value.length > agentId && agentId >= 0) {
    const profile = profiles.value[agentId];
    return profile?.username || `profile_${agentId}`;
  }
  return `profile_${agentId}`;
};

const platformLabel = (platform) =>
  platform === "reddit" ? "Topic community" : "Short-post channel";

const totalTopicsCount = computed(() => {
  return profiles.value.reduce((sum, p) => {
    return sum + (p.interested_topics?.length || 0);
  }, 0);
});

const addLog = (msg) => {
  emit("add-log", msg);
};

const handleStartSimulation = () => {
  if (!canStartSimulation.value) return;
  const maxRounds = resolvedMaxRounds.value;
  addLog(
    `Running ${maxRounds} ${useCustomRounds.value ? "chosen" : "suggested"} scenario rounds.`,
  );
  emit("next-step", { maxRounds });
};

const truncateBio = (bio) => {
  if (bio && bio.length > 80) {
    return bio.substring(0, 80) + "...";
  }
  return bio || "";
};

const selectProfile = (profile) => {
  profileReturnTarget = document.activeElement;
  selectedProfile.value = profile;
  nextTick(() => profileCloseButton.value?.focus());
};

const closeProfile = () => {
  selectedProfile.value = null;
  nextTick(() => {
    if (profileReturnTarget?.isConnected) profileReturnTarget.focus();
  });
};

const handleProfileKeydown = (event) => {
  if (event.key === "Escape") {
    event.preventDefault();
    closeProfile();
    return;
  }
  if (event.key !== "Tab") return;

  const focusable = Array.from(
    profileDialog.value?.querySelectorAll(
      'button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ) || [],
  );
  if (!focusable.length) {
    event.preventDefault();
    profileDialog.value?.focus();
    return;
  }
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
};

const stopAllPolling = () => {
  stopPolling();
  stopProfilesPolling();
  stopConfigPolling();
};

const failPreparation = (message) => {
  stopAllPolling();
  preparationStatus.value = "error";
  preparationError.value =
    message || "The assumptions could not be prepared. Try again.";
  addLog(preparationError.value);
  emit("update-status", "error");
};

const completePreparation = () => {
  if (profiles.value.length === 0) {
    failPreparation(
      "Preparation finished without any generated profiles. Try preparation again.",
    );
    return false;
  }
  if (!hasValidConfig.value || !hasValidRounds.value) {
    failPreparation(
      "Preparation returned incomplete scenario rules. Try preparation again.",
    );
    return false;
  }
  stopAllPolling();
  phase.value = 4;
  prepareProgress.value = 100;
  preparationStatus.value = "completed";
  preparationError.value = "";
  addLog("The assumptions are ready to review.");
  emit("update-status", "completed");
  return true;
};

const startPrepareSimulation = async () => {
  stopAllPolling();
  preparationStatus.value = "processing";
  preparationError.value = "";
  prepareProgress.value = 0;
  progressMessage.value = "";
  currentStage.value = "";
  taskId.value = null;
  profiles.value = [];
  entityTypes.value = [];
  expectedTotal.value = null;
  simulationConfig.value = null;
  lastLoggedMessage = "";
  lastLoggedProfileCount = 0;
  lastLoggedConfigStage = "";
  if (!props.simulationId) {
    failPreparation(
      "The scenario workspace reference is missing. Reopen the run and try again.",
    );
    return;
  }

  phase.value = 1;
  addLog("Scenario workspace opened.");
  addLog("Creating synthetic perspectives and starting conditions…");
  emit("update-status", "processing");

  try {
    const res = await prepareSimulation({
      simulation_id: props.simulationId,
      use_llm_for_profiles: true,
      parallel_profile_count: 5,
    });

    if (res.success && res.data) {
      if (res.data.already_prepared) {
        addLog("A saved preparation was found. Loading it now…");
        await loadPreparedData();
        return;
      }

      taskId.value = res.data.task_id;
      addLog("Scenario preparation started.");

      if (res.data.expected_entities_count) {
        expectedTotal.value = res.data.expected_entities_count;
        addLog(`Found ${res.data.expected_entities_count} source-map entities.`);
      }

      startPolling();
      startProfilesPolling();
    } else {
      failPreparation(
        `The assumptions could not be prepared: ${res.error || "Unknown error"}`,
      );
    }
  } catch (err) {
    failPreparation(`The assumptions could not be prepared: ${err.message}`);
  }
};

const startPolling = () => {
  stopPolling();
  pollTimer = setInterval(pollPrepareStatus, STATUS_POLL_INTERVAL_MS);
};

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

const startProfilesPolling = () => {
  stopProfilesPolling();
  profilesTimer = setInterval(fetchProfilesRealtime, PROFILES_POLL_INTERVAL_MS);
};

const stopProfilesPolling = () => {
  if (profilesTimer) {
    clearInterval(profilesTimer);
    profilesTimer = null;
  }
};

const pollPrepareStatus = async () => {
  if (!taskId.value && !props.simulationId) return;

  try {
    const res = await getPrepareStatus({
      task_id: taskId.value,
      simulation_id: props.simulationId,
    });

    if (res.success && res.data) {
      const data = res.data;
      prepareProgress.value = data.progress || 0;
      progressMessage.value = data.message || "";

      if (data.progress_detail) {
        currentStage.value = data.progress_detail.current_stage_name || "";
        const detail = data.progress_detail;
        const logKey = `${detail.current_stage}-${detail.current_item}-${detail.total_items}`;
        if (logKey !== lastLoggedMessage && detail.item_description) {
          lastLoggedMessage = logKey;
          const stageInfo = `[${detail.stage_index}/${detail.total_stages}]`;
          if (detail.total_items > 0) {
            addLog(
              `${stageInfo} ${detail.current_stage_name}: ${detail.current_item}/${detail.total_items} - ${detail.item_description}`,
            );
          } else {
            addLog(
              `${stageInfo} ${detail.current_stage_name}: ${detail.item_description}`,
            );
          }
        }
      } else if (data.message) {
        const match = data.message.match(/\[(\d+)\/(\d+)\]\s*([^:]+)/);
        if (match) {
          currentStage.value = match[3].trim();
        }
        if (data.message !== lastLoggedMessage) {
          lastLoggedMessage = data.message;
          addLog(data.message);
        }
      }

      if (
        data.status === "completed" ||
        data.status === "ready" ||
        data.already_prepared
      ) {
        addLog("Scenario preparation complete.");
        stopPolling();
        stopProfilesPolling();
        await loadPreparedData();
      } else if (data.status === "failed") {
        failPreparation(
          `Scenario preparation failed: ${data.error || "Unknown error"}`,
        );
      }
    } else {
      failPreparation(
        `The preparation status could not be checked: ${res.error || "No status was returned."}`,
      );
    }
  } catch (err) {
    failPreparation(
      `The preparation status could not be checked: ${err.message || "Connection error"}`,
    );
  }
};

const fetchProfilesRealtime = async (surfaceFailure = false) => {
  if (!props.simulationId) {
    if (surfaceFailure) failPreparation("The scenario workspace reference is missing.");
    return false;
  }

  try {
    const res = await getSimulationProfilesRealtime(
      props.simulationId,
      "reddit",
    );

    if (res.success && res.data) {
      profiles.value = res.data.profiles || [];
      if (res.data.total_expected) {
        expectedTotal.value = res.data.total_expected;
      }
      const types = new Set();
      profiles.value.forEach((p) => {
        if (p.entity_type) types.add(p.entity_type);
      });
      entityTypes.value = Array.from(types);

      const currentCount = profiles.value.length;
      if (currentCount > 0 && currentCount !== lastLoggedProfileCount) {
        lastLoggedProfileCount = currentCount;
        const total = expectedTotal.value || "?";
        const latestProfile = profiles.value[currentCount - 1];
        const profileName =
          latestProfile?.name ||
          latestProfile?.username ||
          `Profile_${currentCount}`;
        if (currentCount === 1) {
          addLog("Creating generated profiles…");
        }
        addLog(
          `Generated profile ${currentCount}/${total}: ${profileName} (${latestProfile?.profession || "Profile"})`,
        );

        if (expectedTotal.value && currentCount >= expectedTotal.value) {
          addLog(`All ${currentCount} generated profiles are ready.`);
        }
      }
      return true;
    }
    if (surfaceFailure) {
      failPreparation(
        `Generated profiles could not be loaded: ${res.error || "No profile data was returned."}`,
      );
    }
    return false;
  } catch (err) {
    if (surfaceFailure) {
      failPreparation(
        `Generated profiles could not be loaded: ${err.message || "Connection error"}`,
      );
    } else if (import.meta.env.DEV) {
      console.warn("Failed to fetch profiles:", err);
    }
    return false;
  }
};

const startConfigPolling = () => {
  stopConfigPolling();
  configTimer = setInterval(fetchConfigRealtime, CONFIG_POLL_INTERVAL_MS);
};

const stopConfigPolling = () => {
  if (configTimer) {
    clearInterval(configTimer);
    configTimer = null;
  }
};

const fetchConfigRealtime = async () => {
  if (!props.simulationId) return;

  try {
    const res = await getSimulationConfigRealtime(props.simulationId);

    if (res.success && res.data) {
      const data = res.data;
      if (
        data.generation_stage &&
        data.generation_stage !== lastLoggedConfigStage
      ) {
        lastLoggedConfigStage = data.generation_stage;
        if (data.generation_stage === "generating_profiles") {
          addLog("Creating generated profile details…");
        } else if (data.generation_stage === "generating_config") {
          addLog("Drafting scenario rules from the source map…");
        }
      }

      if (
        data.config &&
        (data.config_generated ||
          data.generation_stage === "completed" ||
          data.is_generating === false)
      ) {
        simulationConfig.value = data.config;
        addLog("Scenario rules are ready.");

        if (data.summary) {
          addLog(`Generated profiles: ${data.summary.total_agents}`);
          addLog(`Simulated duration: ${data.summary.simulation_hours} hours`);
          addLog(`Opening messages: ${data.summary.initial_posts_count}`);
          addLog(`Introduced topics: ${data.summary.hot_topics_count}`);
          addLog(
            `Channel readiness: short posts ${data.summary.has_twitter_config ? "ready" : "missing"}, topic community ${data.summary.has_reddit_config ? "ready" : "missing"}`,
          );
        }

        stopConfigPolling();
        await fetchProfilesRealtime();
        completePreparation();
      }
    } else {
      failPreparation(
        `Scenario rules could not be loaded: ${res.error || "No configuration data was returned."}`,
      );
    }
  } catch (err) {
    failPreparation(
      `Scenario rules could not be loaded: ${err.message || "Connection error"}`,
    );
  }
};

const loadPreparedData = async () => {
  phase.value = 2;
  addLog("Loading saved assumptions…");
  const profilesLoaded = await fetchProfilesRealtime(true);
  if (!profilesLoaded || preparationStatus.value === "error") return;
  addLog(`Loaded ${profiles.value.length} generated profiles.`);

  try {
    const res = await getSimulationConfigRealtime(props.simulationId);
    if (res.success && res.data) {
      if (
        res.data.config &&
        (res.data.config_generated ||
          res.data.generation_stage === "completed" ||
          res.data.is_generating === false)
      ) {
        simulationConfig.value = res.data.config;
        addLog("Scenario rules loaded.");
        completePreparation();
      } else {
        addLog("The scenario rules are still being prepared…");
        startConfigPolling();
      }
    } else {
      failPreparation(
        `The saved assumptions could not be loaded: ${res.error || "No configuration data was returned."}`,
      );
    }
  } catch (err) {
    failPreparation(`The saved assumptions could not be loaded: ${err.message}`);
  }
};

onMounted(() => {
  addLog("Assumption review opened.");
  startPrepareSimulation();
});

onUnmounted(() => {
  stopPolling();
  stopProfilesPolling();
  stopConfigPolling();
});
</script>

<style scoped>
.env-setup-panel {
  height: 100%;
  background-color: transparent;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  font-family: var(--font-sans);
  color: var(--text-primary);
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Step Card */
.step-card {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  padding: 24px;
  transition: all 0.25s ease;
  position: relative;
}

.step-card:hover {
  border-color: rgba(255, 255, 255, 0.15);
}

.step-card.active {
  border-color: var(--primary);
  box-shadow: 0 0 25px rgba(99, 102, 241, 0.15);
  background: rgba(99, 102, 241, 0.04);
}

.step-card.completed {
  opacity: 0.5;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 12px;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-num {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--primary), var(--accent-purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.step-title {
  font-weight: 700;
  font-size: 13px;
  color: var(--text-primary);
}

.badge {
  font-size: 9px;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge.success {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.badge.processing {
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border: 1px solid rgba(99, 102, 241, 0.3);
}
.badge.accent {
  background: rgba(139, 92, 246, 0.15);
  color: #c4b5fd;
  border: 1px solid rgba(139, 92, 246, 0.3);
}
.badge.pending {
  background: rgba(30, 41, 59, 0.4);
  color: var(--text-muted);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.api-note {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-muted);
  margin-bottom: 10px;
  font-weight: 600;
}

.description {
  font-size: 12px;
  line-height: 1.6;
  margin-bottom: 20px;
  color: var(--text-secondary);
}

/* Profiles */
.profiles-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.profile-card {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  padding: 16px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.profile-card:hover {
  background: rgba(99, 102, 241, 0.08);
  border-color: var(--primary);
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.25);
  transform: translateY(-2px);
}

.profile-realname {
  display: block;
  font-weight: 700;
  font-size: 14px;
  color: var(--text-primary);
}

.profile-username {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  color: var(--text-secondary);
}

.profile-meta {
  margin: 8px 0;
}

.profile-profession {
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 700;
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border: 1px solid rgba(99, 102, 241, 0.3);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.profile-bio {
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-muted);
  height: 33px;
  overflow: hidden;
}

.profile-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.topic-tag {
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 600;
  border: 1px solid rgba(99, 102, 241, 0.25);
  background: rgba(99, 102, 241, 0.08);
  padding: 3px 8px;
  border-radius: var(--radius-full);
  color: #a5b4fc;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

/* Config Blocks */
.config-block {
  margin-top: 24px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  padding: 24px;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(8px);
  margin-bottom: 24px;
}

.config-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 10px;
}

.config-block-title {
  font-weight: 700;
  font-size: 13px;
  text-transform: uppercase;
  color: var(--text-primary);
  letter-spacing: 0.5px;
}

.config-block-badge {
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 700;
  background: rgba(139, 92, 246, 0.15);
  color: #c4b5fd;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(139, 92, 246, 0.3);
  text-transform: uppercase;
}

.platforms-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.platform-card {
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-sm);
  background: rgba(30, 41, 59, 0.4);
  transition: all 0.2s ease;
}

.platform-card:hover {
  border-color: rgba(99, 102, 241, 0.3);
  background: rgba(30, 41, 59, 0.6);
}

.platform-name {
  font-weight: 700;
  font-size: 11px;
  margin-bottom: 12px;
  display: block;
  background: linear-gradient(135deg, var(--primary), var(--accent-purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.param-row {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-sans);
  font-size: 11px;
  margin-bottom: 6px;
}

.param-label {
  font-weight: 600;
  color: var(--text-secondary);
}

.param-value {
  font-family: var(--font-mono);
  font-weight: 700;
  color: var(--text-primary);
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.config-item {
  text-align: center;
  padding: 16px 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-sm);
  background: rgba(30, 41, 59, 0.4);
  transition: all 0.2s ease;
}

.config-item:hover {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(30, 41, 59, 0.6);
}

.config-item-label {
  display: block;
  font-size: 9px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.config-item-value {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--primary), var(--accent-purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Narrative */
.narrative-box {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  padding: 24px;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(8px);
  margin-bottom: 16px;
}

.box-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 10px;
  margin-bottom: 12px;
  background: linear-gradient(135deg, var(--accent-purple), var(--accent-rose));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.narrative-text {
  font-size: 12px;
  line-height: 1.7;
  color: var(--text-primary);
}

.hot-topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hot-topic-tag {
  background: rgba(244, 63, 94, 0.15);
  color: #fda4af;
  border: 1px solid rgba(244, 63, 94, 0.3);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
}

.posts-timeline {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.timeline-item {
  display: flex;
  gap: 16px;
}

.timeline-marker {
  width: 2px;
  background: linear-gradient(180deg, var(--primary), var(--accent-purple));
  flex-shrink: 0;
  border-radius: 2px;
  box-shadow: 0 0 8px rgba(99, 102, 241, 0.5);
}

.timeline-content {
  flex: 1;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-sm);
  background: rgba(30, 41, 59, 0.4);
}

.post-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 6px;
}

.post-role {
  font-family: var(--font-sans);
  font-weight: 700;
  font-size: 10px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.post-text {
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-primary);
}

/* Activation / Slider */
.rounds-config-section {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  padding: 24px;
  margin: 24px 0;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(8px);
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  background: linear-gradient(135deg, var(--text-primary), var(--text-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  display: block;
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}

.switch-control {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
}

.switch-track {
  width: 44px;
  height: 24px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 12px;
  position: relative;
  transition: background 0.2s ease;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.switch-track::after {
  content: "";
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background: #f8fafc;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: transform 0.2s ease;
}

input:checked + .switch-track {
  background: linear-gradient(135deg, var(--primary), var(--accent-purple));
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.4);
}

input:checked + .switch-track::after {
  transform: translateX(20px);
}

.val-num {
  font-size: 2.5rem;
  font-weight: 700;
  font-family: var(--font-mono);
  background: linear-gradient(135deg, var(--primary), var(--accent-purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.minimal-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  background: linear-gradient(to right, var(--primary) 0%, var(--accent-purple) var(--percent, 50%), rgba(30, 41, 59, 0.6) var(--percent, 50%), rgba(30, 41, 59, 0.6) 100%);
  border-radius: var(--radius-full);
  outline: none;
  cursor: pointer;
}

.minimal-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ffffff;
  border: 3px solid var(--primary);
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.5);
  cursor: pointer;
}

.auto-info-card {
  display: flex;
  align-items: center;
  gap: 24px;
}

.auto-value {
  text-align: center;
  min-width: 120px;
}

/* Action Button */
.action-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, var(--primary), var(--accent-purple)) !important;
  color: #ffffff !important;
  border: 1px solid rgba(139, 92, 246, 0.4) !important;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.25);
}

.action-btn:hover:not(:disabled) {
  box-shadow: 0 0 30px rgba(99, 102, 241, 0.4);
  transform: translateY(-1px);
}

.action-btn.secondary {
  background: rgba(30, 41, 59, 0.5) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  color: var(--text-secondary) !important;
  padding: 8px 16px;
  font-size: 11px;
  margin-top: 12px;
  box-shadow: none;
}
.action-btn.secondary:hover {
  background: rgba(99, 102, 241, 0.1) !important;
  color: var(--text-primary) !important;
  border-color: rgba(99, 102, 241, 0.3) !important;
}

/* Modal */
.profile-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(9, 13, 22, 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}

.profile-modal {
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 800px;
  max-height: 85vh;
  overflow-y: auto;
  padding: 32px;
  position: relative;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
  color: var(--text-primary);
}

.modal-header {
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 20px;
  margin-bottom: 24px;
}

.modal-header h3 {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.modal-realname {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--text-primary), #cbd5e1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.modal-info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.info-label {
  display: block;
  font-size: 9px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.dimension-card {
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  background: rgba(30, 41, 59, 0.4);
}

.dim-title {
  display: block;
  font-weight: 700;
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-primary);
  margin-bottom: 2px;
  letter-spacing: 0.5px;
}

.dim-desc {
  font-size: 10px;
  color: var(--text-secondary);
}

.section-persona {
  font-size: 12px;
  line-height: 1.7;
  margin-top: 20px;
  color: var(--text-primary);
}

/* System Logs */
.system-logs {
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(12px);
  padding: 20px;
  color: var(--text-primary);
  min-height: 180px;
  display: flex;
  flex-direction: column;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.log-title {
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--primary), var(--accent-purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.log-content {
  margin-top: 10px;
  height: 100px;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  flex-grow: 1;
  color: var(--text-secondary);
}

.log-time {
  color: #94a3b8;
  margin-right: 8px;
}

.close-btn {
  position: absolute;
  top: 24px;
  right: 24px;
  font-size: 24px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  font-weight: 400;
  color: var(--text-secondary);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(244, 63, 94, 0.15);
  border-color: rgba(244, 63, 94, 0.3);
  color: #fda4af;
}

/* Public Signal: assumptions as an inspectable paper brief */
.env-setup-panel {
  border: 0;
  background: var(--paper);
  color: var(--ink);
}

.scroll-container {
  gap: 1rem;
  padding: clamp(0.85rem, 2vw, 1.5rem);
  background:
    linear-gradient(rgba(17, 21, 19, 0.045) 1px, transparent 1px),
    var(--paper);
  background-size: 100% 2.4rem;
}

.step-card,
.step-card.active,
.step-card.completed {
  padding: clamp(1rem, 2vw, 1.45rem);
  border: 1px solid var(--line-light) !important;
  border-radius: 0;
  background: var(--paper-strong) !important;
  color: var(--ink);
  opacity: 1;
  box-shadow: 0.4rem 0.4rem 0 var(--line-light) !important;
  backdrop-filter: none;
}

.step-card.active,
.step-card:hover {
  border-color: var(--ink) !important;
  box-shadow: 0.4rem 0.4rem 0 var(--signal) !important;
  transform: none;
}

.card-header {
  margin: calc(clamp(1rem, 2vw, 1.45rem) * -1)
    calc(clamp(1rem, 2vw, 1.45rem) * -1) 1.25rem;
  padding: 0.75rem clamp(1rem, 2vw, 1.45rem);
  border-color: var(--ink);
  background: var(--ink-deep) !important;
}

.step-num {
  background: none;
  color: var(--signal) !important;
  -webkit-text-fill-color: currentColor;
}

.step-title,
.card-header .step-title {
  color: var(--paper) !important;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 500;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.badge,
.badge.success,
.badge.processing,
.badge.accent {
  border: 1px solid var(--signal);
  border-radius: 0;
  background: var(--signal);
  color: var(--ink);
  white-space: nowrap;
}

.badge.pending {
  border-color: var(--line-dark);
  border-radius: 0;
  background: var(--ink-raised);
  color: var(--paper-muted);
}

.api-note {
  color: var(--signal-text) !important;
  font-family: var(--font-display);
  font-size: 0.78rem;
  letter-spacing: 0.04em;
}

.description,
.profile-bio,
.param-label,
.section-desc,
.auto-desc,
.modal-body,
.dim-desc {
  color: var(--ink-muted) !important;
}

.description {
  font-size: 0.88rem;
}

.profile-card,
.config-block,
.config-detail-panel,
.platform-card,
.narrative-box,
.rounds-config-section,
.auto-info-card,
.timeline-content,
.dimension-card,
.info-item {
  border: 1px solid var(--line-light) !important;
  border-radius: 0;
  background: var(--paper) !important;
  color: var(--ink);
  box-shadow: none !important;
}

.profile-card:hover,
.platform-card:hover {
  border-color: var(--ink) !important;
  background: var(--signal-soft) !important;
  transform: none;
}

.profile-card {
  width: 100%;
  align-items: stretch;
  justify-content: flex-start;
  font-family: var(--font-sans);
  text-align: left;
  text-transform: none;
}

.profile-realname,
.profile-username,
.profile-profession,
.config-block-title,
.platform-name,
.param-value,
.config-item-label,
.config-item-value,
.box-label,
.narrative-text,
.post-text,
.section-title,
.val-num,
.val-unit,
.duration-badge,
.modal-realname,
.modal-username,
.modal-profession,
.info-label,
.info-value,
.dim-title,
.section-persona {
  color: var(--ink) !important;
}

.topic-tag,
.hot-topic-tag,
.topic-item,
.config-block-badge,
.post-role,
.profile-profession {
  border: 1px solid var(--line-light);
  border-radius: 0;
  background: var(--signal-soft);
  color: var(--ink);
}

.config-block-header,
.platform-card-header,
.rounds-header,
.post-header {
  border-color: var(--line-light);
  background: var(--paper-strong);
}

.minimal-slider {
  accent-color: var(--signal-deep);
}

.auto-value {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 0.4rem;
}

.action-btn {
  border-color: var(--signal) !important;
  border-radius: 0;
  background: var(--signal) !important;
  color: var(--ink) !important;
  font-family: var(--font-display);
  box-shadow: none;
}

.action-btn:hover:not(:disabled) {
  border-color: var(--ink) !important;
  background: var(--signal-strong) !important;
  box-shadow: none;
}

.profile-modal-overlay {
  background: rgba(12, 16, 15, 0.92);
  backdrop-filter: none;
}

.profile-modal {
  border: 1px solid var(--signal);
  border-radius: 0;
  background: var(--paper);
  color: var(--ink);
  box-shadow: 0.8rem 0.8rem 0 var(--signal-deep);
}

.profile-modal .modal-header {
  border-color: var(--ink);
  background: var(--signal);
}

.profile-modal .close-btn {
  border-color: var(--ink);
  border-radius: 0;
  background: var(--ink);
  color: var(--paper);
}

.preparation-banner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1rem;
  align-items: center;
  padding: 1rem 1.2rem;
  border: 1px solid var(--ink);
  background: var(--paper-strong);
  color: var(--ink);
  box-shadow: 0.4rem 0.4rem 0 var(--signal);
}

.preparation-banner > div:first-child {
  display: grid;
  gap: 0.25rem;
}

.preparation-label {
  color: var(--signal-text);
  font-family: var(--font-display);
  font-size: 0.78rem;
  letter-spacing: 0.045em;
  text-transform: uppercase;
}

.preparation-banner strong {
  font-family: var(--font-display);
  font-size: 1.4rem;
  font-weight: 500;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.preparation-banner p,
.empty-state,
.readiness-note {
  margin: 0;
  color: var(--ink-muted);
  font-size: 0.78rem;
  line-height: 1.45;
}

.preparation-banner.is-error {
  border-color: var(--error-text);
  box-shadow: 0.4rem 0.4rem 0 var(--error);
}

.preparation-banner.is-error .preparation-label,
.badge.error {
  color: var(--error-text);
}

.preparation-banner.is-completed .preparation-label {
  color: var(--success-text);
}

.preparation-progress {
  grid-column: 1 / -1;
  height: 0.45rem;
  overflow: hidden;
  border: 1px solid var(--ink);
  background: var(--line-light);
}

.preparation-progress span {
  display: block;
  height: 100%;
  background: var(--signal);
  transition: width 220ms var(--ease-out);
}

.retry-button {
  border-color: var(--ink);
  background: var(--ink);
  color: var(--paper);
  font-family: var(--font-display);
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.badge.error {
  border: 1px solid var(--error);
  border-radius: 0;
  background: var(--paper);
}

.empty-state {
  padding: 0.85rem;
  border: 1px dashed var(--line-light);
}

.readiness-note {
  margin-top: 0.7rem;
  text-align: left;
}

.rounds-unavailable {
  display: grid;
  gap: 0.3rem;
  margin: 1.2rem 0;
  padding: 1rem;
  border: 1px dashed var(--line-light);
  background: var(--paper);
}

.rounds-unavailable strong {
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 500;
  letter-spacing: 0.025em;
  text-transform: uppercase;
}

.rounds-unavailable span {
  color: var(--ink-muted);
  font-size: 0.78rem;
  line-height: 1.45;
}

.range-marks {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  margin-top: 0.7rem;
  color: var(--ink-muted);
  font-size: 0.68rem;
}

.range-marks > :last-child {
  text-align: right;
}

.mark-recommend,
.highlight-tip {
  min-height: 2rem;
  padding: 0.25rem 0.45rem;
  border: 0;
  background: transparent;
  color: var(--signal-text);
  font-size: 0.7rem;
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 0.18rem;
}

.mark-recommend:hover,
.highlight-tip:hover {
  background: var(--signal-soft);
  color: var(--ink);
}

.minimal-slider:focus-visible {
  outline: 3px solid var(--signal);
  outline-offset: 4px;
}

.activity-status {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.8rem;
  align-items: baseline;
  padding: 0.85rem 1rem;
  border-top: 1px solid var(--line-dark);
  background: var(--ink-deep);
  color: var(--paper);
}

.activity-status > span,
.activity-disclosure summary {
  font-family: var(--font-display);
  font-size: 0.78rem;
  letter-spacing: 0.045em;
  text-transform: uppercase;
}

.activity-status strong {
  overflow: hidden;
  color: var(--paper-muted);
  font-size: 0.78rem;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-disclosure {
  border-top: 1px solid var(--line-dark);
  background: var(--ink);
  color: var(--paper);
}

.activity-disclosure summary {
  display: flex;
  justify-content: space-between;
  padding: 0.7rem 1rem;
  color: var(--paper-muted);
  cursor: pointer;
}

.activity-disclosure summary span {
  color: var(--paper-dim);
  font-family: var(--font-sans);
  font-size: 0.68rem;
  letter-spacing: 0;
  text-transform: none;
}

.activity-list {
  max-height: 9rem;
  overflow-y: auto;
  padding: 0 1rem 0.75rem;
  border-top: 1px solid var(--line-dark);
}

.activity-line {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.65rem;
  padding-top: 0.45rem;
  color: var(--paper-muted);
  font-size: 0.72rem;
  line-height: 1.35;
}

.activity-time {
  color: var(--paper-dim);
  font-variant-numeric: tabular-nums;
}

.profile-modal:focus {
  outline: none;
}

.config-detail-panel {
  border: 0 !important;
  background: transparent !important;
}

.assumption-brief {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border: 1px solid var(--ink);
  background: var(--ink-deep);
  color: var(--paper);
}

.assumption-brief article {
  min-width: 0;
  padding: 1rem;
  border-right: 1px solid var(--line-dark);
}

.assumption-brief article:last-child {
  border-right: 0;
}

.assumption-brief span,
.advanced-assumptions summary strong {
  display: block;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.78rem;
  font-weight: 500;
  letter-spacing: 0.045em;
  text-transform: uppercase;
}

.assumption-brief strong {
  display: block;
  margin-top: 0.55rem;
  color: var(--paper);
  font-family: var(--font-display);
  font-size: clamp(1.15rem, 2vw, 1.55rem);
  font-weight: 500;
  line-height: 1.02;
}

.assumption-brief p {
  margin: 0.65rem 0 0;
  color: var(--paper-muted);
  font-size: 0.78rem;
  line-height: 1.45;
}

.advanced-assumptions {
  margin-top: 0.8rem;
  border: 1px solid var(--line-light);
  background: var(--paper);
}

.advanced-assumptions summary {
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  padding: 0.8rem 1rem;
  color: var(--ink);
  cursor: pointer;
  list-style: none;
}

.advanced-assumptions summary::-webkit-details-marker {
  display: none;
}

.advanced-assumptions summary strong {
  color: var(--ink);
}

.advanced-assumptions summary small {
  display: block;
  margin-top: 0.15rem;
  color: var(--ink-muted);
  font-size: 0.7rem;
}

.advanced-assumptions summary > span:last-child {
  color: var(--signal-text);
  font-family: var(--font-display);
  font-size: 1.5rem;
  line-height: 1;
}

.advanced-assumptions[open] summary > span:last-child {
  transform: rotate(45deg);
}

.advanced-assumptions-body {
  padding: 0 1rem 1rem;
  border-top: 1px solid var(--line-light);
}

.advanced-assumptions-body .config-block {
  margin: 1rem 0 0;
}

@media (max-width: 620px) {
  .profiles-list,
  .platforms-grid,
  .config-grid,
  .assumption-brief,
  .modal-info-grid,
  .persona-dimensions {
    grid-template-columns: 1fr;
  }

  .assumption-brief article {
    border-right: 0;
    border-bottom: 1px solid var(--line-dark);
  }

  .assumption-brief article:last-child {
    border-bottom: 0;
  }

  .rounds-header,
  .auto-info-card {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.8rem;
  }

  .preparation-banner {
    grid-template-columns: 1fr;
  }

  .activity-status {
    grid-template-columns: 1fr;
    gap: 0.2rem;
  }
}
</style>
