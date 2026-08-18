<template>
  <div class="env-setup-panel">
    <h2 class="sr-only">Assumption preparation</h2>
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
            <span class="step-title">Create generated perspectives</span>
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
            They are scenario devices, not observations of real people.
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
            this generated run.
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
                  map—not sampled people or observations of individual behavior.
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
                  <span class="dim-title">generated memory context</span>
                  <span class="dim-desc"
                    >Generated context used during the run</span
                  >
                </div>
                <div class="dimension-card">
                  <span class="dim-title">Generated connection patterns</span>
                  <span class="dim-desc"
                    >Connections used inside this generated scenario</span
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
  addLog("Creating generated perspectives and starting conditions…");
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
      // Check if this is a profile validation error (Gate 1)
      const errorMsg = res.error || "Unknown error";
      if (errorMsg.includes("diverse profiles") || errorMsg.includes("validation") || errorMsg.includes("decision parameters")) {
        failPreparation(
          `Profile validation failed: The system could not generate sufficiently diverse profiles from your source material. This may occur when source documents lack varied perspectives. Please try again or consider enriching your input documents.`,
        );
      } else {
        failPreparation(
          `The assumptions could not be prepared: ${errorMsg}`,
        );
      }
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
        // Check if this is a profile validation error (Gate 1)
        const errorMsg = data.error || "Unknown error";
        if (errorMsg.includes("diverse profiles") || errorMsg.includes("validation")) {
          failPreparation(
            `Profile generation validation failed: ${errorMsg}. The system could not generate sufficiently diverse profiles. Please try again, or consider adjusting your source documents to include more varied perspectives.`,
          );
        } else {
          failPreparation(
            `Scenario preparation failed: ${errorMsg}`,
          );
        }
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
  color: var(--paper);
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: clamp(1.5rem, 3vw, 3rem);
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* Preparation Banner */
.preparation-banner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1.5rem;
  align-items: center;
  padding: 1.5rem 2rem;
  background: var(--ink-deep);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border: 1px solid rgba(242, 235, 221, 0.1);
  border-radius: var(--radius-lg);
  color: var(--paper);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.preparation-banner::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(135deg, rgba(242,235,221,0.05) 0%, rgba(242,235,221,0) 100%);
  pointer-events: none;
}

.preparation-banner > div:first-child {
  display: grid;
  gap: 0.4rem;
  z-index: 1;
}

.preparation-label {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.85rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.preparation-banner strong {
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.preparation-banner p,
.empty-state,
.readiness-note {
  margin: 0;
  color: var(--paper-muted);
  font-size: 0.9rem;
  line-height: 1.5;
}

.preparation-banner.is-error {
  border-color: var(--signal-rule);
  background: var(--signal-faint);
  box-shadow: none;
}

.preparation-banner.is-error .preparation-label,
.badge.error {
  color: var(--signal-soft);
}

.preparation-banner.is-completed .preparation-label {
  color: var(--attention);
}

.preparation-progress {
  grid-column: 1 / -1;
  height: 4px;
  background: rgba(242, 235, 221, 0.1);
  border-radius: 2px;
  overflow: hidden;
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
}

.preparation-progress span {
  display: block;
  height: 100%;
  background: var(--signal);
  box-shadow: 0 0 10px var(--signal);
  transition: width 0.3s ease-out;
}

.retry-button {
  z-index: 1;
  padding: 0.75rem 1.5rem;
  background: var(--signal-tint);
  border: 1px solid var(--signal-rule);
  color: var(--signal-soft);
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  cursor: pointer;
  transition: all 0.2s ease;
}

.retry-button:hover {
  background: var(--signal-wash);
  transform: translateY(-1px);
}

/* Step Card */
.step-card {
  background: var(--ink-deep);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: var(--radius-lg);
  padding: 2rem;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
}

.step-card:hover {
  border-color: rgba(242, 235, 221, 0.15);
  background: rgba(20, 30, 50, 0.5);
}

.step-card.active {
  border-color: var(--signal);
  box-shadow: none;
  background: var(--ink-soft);
}

.step-card.active::before {
  content: '';
  position: absolute;
  top: -1px; left: -1px; right: -1px; bottom: -1px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--signal-rule), transparent 40%);
  z-index: -1;
  opacity: 0.5;
  pointer-events: none;
}

.step-card.completed {
  opacity: 0.7;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid rgba(242, 235, 221, 0.08);
  padding-bottom: 1rem;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.step-num {
  font-family: var(--font-mono);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--signal);
}

.step-title {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 500;
  color: var(--paper);
  letter-spacing: 0.02em;
}

.badge {
  font-size: 0.7rem;
  padding: 0.3rem 0.75rem;
  border-radius: var(--radius-full);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.badge.success {
  background: var(--attention-tint);
  color: var(--attention);
  border: 1px solid var(--attention-rule);
}
.badge.processing {
  background: var(--signal-tint);
  color: var(--signal-soft);
  border: 1px solid var(--signal-rule);
  animation: pulse-glow 2s infinite;
}
.badge.accent {
  background: rgba(139, 92, 246, 0.15);
  color: var(--signal-soft);
  border: 1px solid rgba(139, 92, 246, 0.3);
}
.badge.pending {
  background: var(--ink-raised);
  color: var(--paper-muted);
  border: 1px solid rgba(242, 235, 221, 0.1);
}

@keyframes pulse-glow {
  0%, 100% { outline-offset: 0.18rem; }
  50% { outline-offset: 0.35rem; }
}

.api-note {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--signal);
  margin-bottom: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.description {
  font-size: 0.95rem;
  line-height: 1.6;
  margin-bottom: 2rem;
  color: var(--paper-muted);
}

/* Profiles */
.profiles-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.profile-card {
  background: var(--ink-deep);
  backdrop-filter: none;
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: var(--radius-md);
  padding: 1.25rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.profile-card:hover {
  background: var(--ink-raised);
  border-color: var(--signal);
  box-shadow: var(--shadow-sm);
  transform: translateY(-3px);
}

.profile-header {
  display: flex;
  flex-direction: column;
}

.profile-realname {
  display: block;
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 1.1rem;
  color: var(--paper);
}

.profile-username {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--paper-muted);
}

.profile-meta {
  margin: 0.25rem 0;
}

.profile-profession {
  font-family: var(--font-sans);
  font-size: 0.65rem;
  font-weight: 700;
  background: var(--signal-tint);
  color: var(--signal-soft);
  border: 1px solid var(--signal-rule);
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-full);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.profile-bio {
  font-size: 0.8rem;
  line-height: 1.5;
  color: var(--paper-muted);
  height: 2.4rem;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.profile-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: auto;
}

.topic-tag {
  font-family: var(--font-sans);
  font-size: 0.65rem;
  font-weight: 600;
  border: 1px solid var(--signal-rule);
  background: var(--signal-faint);
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-sm);
  color: var(--signal-soft);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.topic-more {
  font-size: 0.65rem;
  color: var(--paper-muted);
  align-self: center;
}

/* Config Blocks */
.config-block {
  margin-top: 1.5rem;
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: var(--radius-md);
  padding: 1.5rem;
  background: var(--ink-deep);
  margin-bottom: 1.5rem;
  transition: border-color 0.3s ease;
}

.config-block:hover {
  border-color: rgba(242, 235, 221, 0.15);
}

.config-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
  border-bottom: 1px solid rgba(242, 235, 221, 0.08);
  padding-bottom: 0.75rem;
}

.config-block-title {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 1rem;
  text-transform: uppercase;
  color: var(--paper);
  letter-spacing: 0.05em;
}

.config-block-badge {
  font-family: var(--font-sans);
  font-size: 0.65rem;
  font-weight: 700;
  background: rgba(139, 92, 246, 0.15);
  color: var(--signal-soft);
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-full);
  border: 1px solid rgba(139, 92, 246, 0.3);
  text-transform: uppercase;
}

.platforms-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.25rem;
}

.platform-card {
  padding: 1.25rem;
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: var(--radius-md);
  background: var(--ink-raised);
  transition: all 0.3s ease;
}

.platform-card:hover {
  border-color: var(--signal-rule);
  background: var(--ink-raised);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.platform-name {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 0.9rem;
  margin-bottom: 1rem;
  display: block;
  color: var(--signal);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.param-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-sans);
  font-size: 0.8rem;
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid rgba(242, 235, 221, 0.05);
}
.param-row:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.param-label {
  color: var(--paper-muted);
}

.param-value {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--paper);
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
}

.config-item {
  text-align: center;
  padding: 1.25rem 1rem;
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: var(--radius-md);
  background: var(--ink-raised);
  transition: all 0.3s ease;
}

.config-item:hover {
  border-color: rgba(242, 235, 221, 0.15);
  background: var(--ink-raised);
  transform: translateY(-2px);
}

.config-item-label {
  display: block;
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--paper-muted);
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.config-item-value {
  font-family: var(--font-mono);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--paper);
}

/* Narrative */
.narrative-box {
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: var(--radius-md);
  padding: 1.5rem;
  background: var(--ink-deep);
  margin-bottom: 1.25rem;
  transition: border-color 0.3s ease;
}
.narrative-box:hover {
  border-color: rgba(242, 235, 221, 0.15);
}

.box-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 0.75rem;
  margin-bottom: 0.75rem;
  color: var(--signal);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.narrative-text {
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--paper);
}

.hot-topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.hot-topic-tag {
  background: var(--signal-tint);
  color: var(--signal-soft);
  border: 1px solid var(--signal-rule);
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.posts-timeline {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  margin-top: 1rem;
}

.timeline-item {
  display: flex;
  gap: 1.25rem;
}

.timeline-marker {
  width: 2px;
  background: linear-gradient(180deg, var(--signal), transparent);
  flex-shrink: 0;
  border-radius: 2px;
  opacity: 0.7;
}

.timeline-content {
  flex: 1;
  padding: 1.25rem;
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: var(--radius-md);
  background: var(--ink-raised);
}

.post-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  border-bottom: 1px solid rgba(242, 235, 221, 0.05);
  padding-bottom: 0.5rem;
}

.post-role {
  font-family: var(--font-sans);
  font-weight: 700;
  font-size: 0.65rem;
  color: var(--paper-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.post-agent-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.post-username {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--signal-soft);
}

.post-id {
  font-size: 0.65rem;
  padding: 0.1rem 0.4rem;
  background: rgba(242,235,221,0.1);
  border-radius: var(--radius-sm);
  color: var(--paper);
}

.post-text {
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--paper);
}

/* Activation / Slider */
.rounds-config-section {
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  margin: 1.5rem 0;
  background: var(--ink-deep);
}

.rounds-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.section-title {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 500;
  color: var(--paper);
  display: block;
  margin-bottom: 0.25rem;
  letter-spacing: 0.02em;
}

.section-desc {
  font-size: 0.85rem;
  color: var(--paper-muted);
}

.switch-control {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.switch-track {
  width: 44px;
  height: 24px;
  background: var(--ink-raised);
  border-radius: 12px;
  position: relative;
  transition: background 0.3s ease;
  border: 1px solid rgba(242, 235, 221, 0.15);
}

.switch-track::after {
  content: "";
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  background: var(--paper);
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

input:checked + .switch-track {
  background: var(--signal);
  border-color: var(--signal);
}

input:checked + .switch-track::after {
  transform: translateX(20px);
}

.switch-label {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--paper);
}

.val-num {
  font-size: 3rem;
  font-weight: 400;
  font-family: var(--font-display);
  color: var(--paper);
  line-height: 1;
}

.val-unit {
  font-size: 1rem;
  color: var(--paper-muted);
  margin-left: 0.25rem;
}

.slider-display {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 1rem;
}

.slider-meta-info {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--signal);
  background: var(--signal-tint);
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-sm);
}

.minimal-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  background: linear-gradient(to right, var(--signal) 0%, var(--signal) var(--percent, 50%), rgba(242, 235, 221, 0.1) var(--percent, 50%), rgba(242, 235, 221, 0.1) 100%);
  border-radius: var(--radius-full);
  outline: none;
  cursor: pointer;
  margin: 1rem 0;
}

.minimal-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--paper);
  border: 3px solid var(--signal);
  box-shadow: none;
  cursor: pointer;
  transition: transform 0.1s;
}
.minimal-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.range-marks {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--paper-muted);
}

.mark-recommend {
  background: none;
  border: none;
  color: var(--signal);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 4px;
}
.mark-recommend:hover {
  color: var(--paper);
}

.auto-info-card {
  display: flex;
  align-items: center;
  gap: 2rem;
  background: rgba(0,0,0,0.1);
  padding: 1.5rem;
  border-radius: var(--radius-md);
  border: 1px solid rgba(242,235,221,0.05);
}

.auto-meta-row {
  margin-bottom: 0.5rem;
}

.duration-badge {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  background: rgba(242,235,221,0.1);
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-sm);
  color: var(--paper);
}

.highlight-tip {
  background: none;
  border: none;
  color: var(--signal);
  cursor: pointer;
  padding: 0;
  font-size: 0.85rem;
  margin-top: 0.5rem;
  text-decoration: underline;
  text-underline-offset: 4px;
}
.highlight-tip:hover {
  color: var(--paper);
}

.rounds-unavailable {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.5rem;
  border: 1px dashed rgba(242,235,221,0.2);
  border-radius: var(--radius-md);
  text-align: center;
  color: var(--paper-muted);
}
.rounds-unavailable strong {
  color: var(--paper);
  font-weight: 500;
  font-family: var(--font-display);
  font-size: 1.1rem;
}

/* Action Button */
.action-btn {
  width: 100%;
  padding: 1rem;
  background: var(--signal);
  color: var(--ink);
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 1rem;
  font-family: var(--font-display);
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: none;
}

.action-btn:hover:not(:disabled) {
  box-shadow: 0.35rem 0.35rem 0 var(--signal-deep);
  transform: translateY(-2px);
  background: var(--signal-strong);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.action-btn.secondary {
  background: rgba(242,235,221,0.05);
  color: var(--paper);
  border: 1px solid rgba(242,235,221,0.1);
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  margin-top: 1rem;
  box-shadow: none;
}
.action-btn.secondary:hover {
  background: rgba(242,235,221,0.1);
}

/* Modal */
.profile-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(9, 13, 22, 0.85);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1.5rem;
}

.profile-modal {
  background: var(--ink-deep);
  border: 1px solid rgba(242, 235, 221, 0.1);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 800px;
  max-height: 85vh;
  overflow-y: auto;
  padding: 2.5rem;
  position: relative;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
  color: var(--paper);
}

.modal-header {
  border-bottom: 1px solid rgba(242, 235, 221, 0.1);
  padding-bottom: 1.5rem;
  margin-bottom: 1.5rem;
}

.modal-name-row {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.modal-realname {
  font-size: 2rem;
  font-weight: 500;
  font-family: var(--font-display);
  color: var(--paper);
}

.modal-username {
  font-family: var(--font-mono);
  font-size: 1rem;
  color: var(--paper-muted);
}

.modal-profession {
  font-size: 0.9rem;
  color: var(--signal);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}

.modal-info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.info-label {
  display: block;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--paper-muted);
  margin-bottom: 0.4rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-value {
  font-size: 1.1rem;
  font-weight: 500;
  color: var(--paper);
}

.info-value.mbti {
  font-family: var(--font-mono);
  color: var(--signal-soft);
}

.modal-section {
  margin-bottom: 2rem;
}

.section-label {
  display: block;
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 500;
  color: var(--paper);
  margin-bottom: 1rem;
}

.section-bio, .section-persona {
  font-size: 1rem;
  line-height: 1.6;
  color: var(--paper-muted);
}

.topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.topic-item {
  background: rgba(242,235,221,0.05);
  border: 1px solid rgba(242,235,221,0.1);
  padding: 0.4rem 0.8rem;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  color: var(--paper);
}

.persona-dimensions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.dimension-card {
  padding: 1rem;
  border: 1px solid rgba(242, 235, 221, 0.08);
  border-radius: var(--radius-md);
  background: var(--ink-raised);
}

.dim-title {
  display: block;
  font-weight: 600;
  font-size: 0.8rem;
  text-transform: uppercase;
  color: var(--signal);
  margin-bottom: 0.4rem;
  letter-spacing: 0.05em;
}

.dim-desc {
  font-size: 0.85rem;
  color: var(--paper-muted);
  line-height: 1.4;
}

/* System Logs */
.activity-status {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid rgba(242,235,221,0.05);
  background: rgba(0,0,0,0.2);
}

.activity-status span {
  font-family: var(--font-display);
  font-size: 0.85rem;
  color: var(--paper-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.activity-status strong {
  font-size: 0.95rem;
  color: var(--paper);
}

.activity-disclosure {
  background: rgba(0,0,0,0.3);
  border-top: 1px solid rgba(242,235,221,0.05);
}

.activity-disclosure summary {
  padding: 1rem 1.5rem;
  color: var(--paper-muted);
  cursor: pointer;
  font-size: 0.85rem;
  display: flex;
  justify-content: space-between;
  list-style: none;
}
.activity-disclosure summary::-webkit-details-marker {
  display: none;
}
.activity-disclosure summary:hover {
  background: rgba(242,235,221,0.02);
  color: var(--paper);
}

.activity-list {
  max-height: 200px;
  overflow-y: auto;
  padding: 0 1.5rem 1.5rem;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}

.activity-line {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.5rem;
  color: var(--paper-muted);
}

.activity-time {
  color: var(--paper-dim);
  flex-shrink: 0;
}

.close-btn {
  position: absolute;
  top: 1.5rem;
  right: 1.5rem;
  background: rgba(242,235,221,0.05);
  border: none;
  color: var(--paper);
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  font-size: 1.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.close-btn:hover {
  background: var(--signal-wash);
  color: var(--signal-soft);
  transform: rotate(90deg);
}

.assumption-brief {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1px;
  background: rgba(242,235,221,0.1);
  border: 1px solid rgba(242,235,221,0.1);
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-bottom: 1.5rem;
}

.assumption-brief article {
  background: var(--ink-soft);
  padding: 1.5rem;
}

.assumption-brief span {
  display: block;
  font-size: 0.75rem;
  color: var(--signal);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.assumption-brief strong {
  display: block;
  font-family: var(--font-display);
  font-size: 1.25rem;
  color: var(--paper);
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.assumption-brief p {
  font-size: 0.85rem;
  color: var(--paper-muted);
  line-height: 1.5;
  margin: 0;
}

.advanced-assumptions {
  border: 1px solid rgba(242,235,221,0.1);
  border-radius: var(--radius-md);
  background: rgba(0,0,0,0.2);
  overflow: hidden;
}

.advanced-assumptions summary {
  padding: 1rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  list-style: none;
}
.advanced-assumptions summary::-webkit-details-marker {
  display: none;
}
.advanced-assumptions summary:hover {
  background: rgba(242,235,221,0.02);
}

.advanced-assumptions summary strong {
  color: var(--paper);
  font-weight: 500;
  display: block;
}

.advanced-assumptions summary small {
  color: var(--paper-muted);
  font-size: 0.8rem;
}

.advanced-assumptions-body {
  padding: 0 1.5rem 1.5rem;
  border-top: 1px solid rgba(242,235,221,0.05);
}

/* Editorial assumption docket ------------------------------------------------
   Human review happens on paper. The prior dark, nested-card treatment made
   assumptions feel like telemetry instead of claims a decision-maker must
   inspect. These rules deliberately flatten the hierarchy into one document. */
.env-setup-panel {
  background: var(--paper);
  color: var(--ink);
}

.scroll-container {
  width: min(100%, 72rem);
  margin-inline: auto;
  padding: clamp(1rem, 2.5vw, 2.5rem);
  gap: 0;
  background: var(--paper);
}

.preparation-banner {
  padding: 1.25rem 0 1.1rem;
  border: 0;
  border-top: 4px solid var(--signal);
  border-bottom: 1px solid var(--line-light);
  border-radius: 0;
  background: var(--paper-transfer);
  color: var(--ink);
  box-shadow: none;
  transition: none;
}

.preparation-banner::before {
  display: none;
}

.preparation-banner p,
.empty-state,
.readiness-note {
  color: var(--ink-muted);
}

.preparation-banner.is-error {
  border-color: var(--signal);
  background: color-mix(in srgb, var(--signal) 10%, var(--paper));
}

.preparation-progress {
  height: 3px;
  border-radius: 0;
  background: var(--line-light);
}

.preparation-progress span {
  box-shadow: none;
  transition-duration: 180ms;
}

.retry-button {
  border-radius: 0;
  background: var(--signal);
  color: var(--ink);
  box-shadow: none;
}

.step-card,
.step-card:hover,
.step-card.active {
  padding: clamp(1.35rem, 2.5vw, 2rem) 0;
  border: 0;
  border-bottom: 1px solid var(--line-light);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  transition: none;
}

.step-card.active {
  box-shadow: inset 4px 0 0 var(--signal);
  padding-left: clamp(0.9rem, 2vw, 1.5rem);
}

.step-card.active::before {
  display: none;
}

.step-card.completed {
  opacity: 1;
}

.card-header {
  align-items: baseline;
  margin-bottom: 1.25rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid var(--ink);
}

.step-num {
  color: var(--signal-text);
  font-size: 0.85rem;
}

.step-title,
.section-title,
.config-block-title,
.profile-realname,
.narrative-text,
.param-value,
.config-item-value,
.switch-label,
.val-num,
.rounds-unavailable strong {
  color: var(--ink);
}

.badge,
.profile-profession,
.config-block-badge,
.topic-tag,
.hot-topic-tag,
.slider-meta-info,
.duration-badge {
  border-radius: 0;
}

.badge.success,
.badge.pending {
  border: 1px solid var(--line-light);
  background: transparent;
  color: var(--ink-muted);
}

.badge.processing {
  border: 1px solid var(--signal);
  background: transparent;
  color: var(--signal-text);
  animation: none;
}

.badge.accent,
.config-block-badge {
  border: 1px solid var(--attention-deep);
  background: var(--attention-tint);
  color: var(--attention-deep);
}

.api-note,
.box-label,
.platform-name {
  color: var(--signal-text);
  font-family: var(--font-sans);
}

.description,
.profile-bio,
.profile-username,
.topic-more,
.param-label,
.section-desc,
.range-marks,
.advanced-assumptions summary small,
.section-bio,
.section-persona,
.dim-desc,
.info-label {
  color: var(--ink-muted);
}

.profiles-list {
  grid-template-columns: 1fr;
  gap: 0;
  border-top: 1px solid var(--line-light);
}

.profile-card,
.profile-card:hover {
  display: grid;
  grid-template-columns: minmax(10rem, 0.75fr) minmax(8rem, 0.45fr) minmax(0, 1.5fr) minmax(10rem, 0.8fr);
  align-items: center;
  gap: 1rem;
  padding: 0.9rem 0;
  border: 0;
  border-bottom: 1px solid var(--line-light);
  border-radius: 0;
  background: transparent;
  color: var(--ink);
  text-align: left;
  box-shadow: none;
  transform: none;
  transition: background var(--duration-quick) var(--ease-quick);
}

.profile-card:hover {
  background: var(--signal-faint);
}

.profile-meta,
.profile-bio,
.profile-topics {
  margin: 0;
}

.profile-bio {
  height: auto;
}

.profile-profession,
.topic-tag,
.hot-topic-tag {
  border-color: var(--signal-rule);
  background: transparent;
  color: var(--signal-text);
}

.assumption-brief {
  grid-template-columns: 1fr;
  gap: 0;
  border: 1px solid var(--line-light);
  border-radius: 0;
  background: var(--line-light);
}

.assumption-brief article {
  display: grid;
  grid-template-columns: minmax(10rem, 0.6fr) minmax(12rem, 0.8fr) minmax(0, 1.4fr);
  gap: 1rem;
  align-items: baseline;
  padding: 1rem 1.15rem;
  background: var(--paper-transfer);
  border-bottom: 1px solid var(--line-light);
}

.assumption-brief article:last-child {
  border-bottom: 0;
}

.assumption-brief span,
.assumption-brief strong,
.assumption-brief p {
  margin: 0;
}

.assumption-brief span {
  color: var(--signal-text);
}

.assumption-brief strong {
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 1rem;
  font-weight: 700;
}

.assumption-brief p {
  color: var(--ink-muted);
}

:is(.advanced-assumptions, .config-block, .platform-card, .config-item, .narrative-box, .timeline-content, .rounds-config-section, .auto-info-card, .rounds-unavailable, .dimension-card) {
  border-color: var(--line-light);
  border-radius: 0;
  background: var(--paper-transfer);
  color: var(--ink);
  box-shadow: none;
}

:is(.config-block, .platform-card, .config-item, .narrative-box):hover {
  border-color: var(--line-light);
  background: var(--paper-transfer);
  box-shadow: none;
  transform: none;
}

.advanced-assumptions summary strong,
.post-text,
.post-id,
.info-value,
.section-label,
.topic-item,
.modal-realname,
.modal-username {
  color: var(--ink);
}

.advanced-assumptions summary:hover {
  background: var(--signal-faint);
}

.advanced-assumptions-body,
.config-block-header,
.param-row,
.post-header {
  border-color: var(--line-light);
}

.timeline-marker {
  background: var(--signal);
  border-radius: 0;
}

.rounds-unavailable {
  color: var(--ink-muted);
}

.switch-track {
  border-radius: 0;
  border-color: var(--line-light);
  background: var(--paper);
}

.switch-track::after {
  border-radius: 0;
  background: var(--ink);
  box-shadow: none;
}

.minimal-slider {
  border-radius: 0;
  background: linear-gradient(to right, var(--signal) 0%, var(--signal) var(--percent, 50%), var(--line-light) var(--percent, 50%), var(--line-light) 100%);
}

.minimal-slider::-webkit-slider-thumb {
  border-radius: 0;
  background: var(--paper);
}

.action-btn,
.action-btn.secondary {
  border-radius: 0;
  box-shadow: none;
}

.action-btn.secondary {
  border: 1px solid var(--ink);
  background: transparent;
  color: var(--ink);
}

.action-btn:hover:not(:disabled) {
  box-shadow: none;
  transform: translateY(-1px);
}

.profile-modal {
  border-radius: 0;
  border-color: var(--ink);
  background: var(--paper);
  color: var(--ink);
  box-shadow: 0.8rem 0.8rem 0 var(--signal-deep);
}

.modal-header {
  border-color: var(--line-light);
}

.close-btn {
  border: 1px solid var(--ink);
  border-radius: 0;
  background: var(--paper);
  color: var(--ink);
}

.close-btn:hover {
  background: var(--signal);
  color: var(--ink);
  transform: none;
}

.activity-status,
.activity-disclosure {
  border-color: var(--line-light);
  background: var(--paper-transfer);
}

.activity-status span,
.activity-disclosure summary,
.activity-line,
.activity-time {
  color: var(--ink-muted);
}

.activity-status strong,
.activity-disclosure summary:hover {
  color: var(--ink);
}

.activity-list {
  font-family: var(--font-sans);
}

@media (max-width: 768px) {
  .preparation-banner {
    grid-template-columns: 1fr;
  }
  .auto-info-card {
    flex-direction: column;
    align-items: flex-start;
  }
  .rounds-header {
    flex-direction: column;
    gap: 1rem;
  }
  .profile-card,
  .profile-card:hover,
  .assumption-brief article {
    grid-template-columns: 1fr;
  }
}
</style>
