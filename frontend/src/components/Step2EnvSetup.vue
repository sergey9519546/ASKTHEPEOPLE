<template>
  <div class="env-setup-panel">
    <div class="scroll-container">
      <!-- Step 01: Agent Profile Generation -->
      <div
        class="step-card"
        :class="{ active: phase === 1, completed: phase > 1 }"
      >
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">01</span>
            <span class="step-title">Agent Profile Generation</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 1" class="badge success">COMPLETED</span>
            <span v-else-if="phase === 1" class="badge processing"
              >{{ profiles.length }} / {{ expectedTotal || "?" }}</span
            >
            <span v-else class="badge pending">WAITING</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">GET /api/simulation/profiles/realtime</p>
          <p class="description">
            LLM populates agent personalities, backgrounds, and interest vectors
            based on extracted reality seeds from the knowledge graph.
          </p>

          <!-- Profiles Grid -->
          <div v-if="profiles.length > 0" class="profiles-list">
            <div
              v-for="profile in displayProfiles"
              :key="profile.id"
              class="profile-card"
              @click="selectProfile(profile)"
            >
              <div class="profile-header">
                <span class="profile-realname">{{ profile.name }}</span>
                <span class="profile-username">@{{ profile.username }}</span>
              </div>
              <div class="profile-meta">
                <span class="profile-profession">{{
                  profile.profession || "Agent"
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
            </div>
          </div>

          <div class="action-section" v-if="profiles.length > 6">
            <button
              class="action-btn secondary"
              @click="showProfilesDetail = !showProfilesDetail"
            >
              {{ showProfilesDetail ? "COLLAPSE" : "VIEW ALL AGENTS" }}
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
            <span class="step-title">Simulation Configuration</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 2" class="badge success">COMPLETED</span>
            <span v-else-if="phase === 2" class="badge processing"
              >GENERATING</span
            >
            <span v-else class="badge pending">WAITING</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">GET /api/simulation/config/realtime</p>
          <p class="description">
            Defining platform dynamics, posting frequencies, narrative
            directions, and temporal parameters for the simulation environment.
          </p>

          <!-- Config Blocks -->
          <div v-if="simulationConfig" class="config-detail-panel">
            <!-- Platform Strategy -->
            <div class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">PLATFORM DYNAMICS</span>
                <span class="config-block-badge">DUAL-MODE</span>
              </div>
              <div class="platforms-grid">
                <div class="platform-card">
                  <div class="platform-card-header">
                    <span class="platform-name">X (TWITTER)</span>
                  </div>
                  <div class="platform-params">
                    <div class="param-row">
                      <span class="param-label">Max Posts/Day</span>
                      <span class="param-value">{{
                        simulationConfig.platform_config?.twitter
                          ?.max_posts_per_day
                      }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">Interaction Rate</span>
                      <span class="param-value">{{
                        simulationConfig.platform_config?.twitter
                          ?.interaction_rate
                      }}</span>
                    </div>
                  </div>
                </div>
                <div class="platform-card">
                  <div class="platform-card-header">
                    <span class="platform-name">REDDIT</span>
                  </div>
                  <div class="platform-params">
                    <div class="param-row">
                      <span class="param-label">Comments/Post</span>
                      <span class="param-value">{{
                        simulationConfig.platform_config?.reddit
                          ?.comments_per_post
                      }}</span>
                    </div>
                    <div class="param-row">
                      <span class="param-label">Subreddit Depth</span>
                      <span class="param-value">DEEP</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Time Config -->
            <div class="config-block">
              <div class="config-block-header">
                <span class="config-block-title">TEMPORAL PARAMETERS</span>
              </div>
              <div class="config-grid">
                <div class="config-item">
                  <span class="config-item-label">TOTAL HOURS</span>
                  <span class="config-item-value">{{
                    simulationConfig.time_config?.total_simulation_hours
                  }}</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">MIN / ROUND</span>
                  <span class="config-item-value">{{
                    simulationConfig.time_config?.minutes_per_round
                  }}</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">TIME STEP</span>
                  <span class="config-item-value">DYNAMIC</span>
                </div>
                <div class="config-item">
                  <span class="config-item-label">TIMEZONE</span>
                  <span class="config-item-value">UTC</span>
                </div>
              </div>
            </div>
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
            <span class="step-title">Narrative Orchestration</span>
          </div>
          <div class="step-status">
            <span v-if="phase > 3" class="badge success">ORCHESTRATED</span>
            <span v-else-if="phase === 3" class="badge processing"
              >DEFINING</span
            >
            <span v-else class="badge pending">WAITING</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">LLM NARRATIVE ENGINE</p>
          <p class="description">
            Synthesizing reality seeds into a coherent social narrative with
            emergent behavior patterns and conflict points.
          </p>

          <div
            v-if="simulationConfig?.event_config"
            class="orchestration-content"
          >
            <!-- Narrative Direction -->
            <div class="narrative-box">
              <span class="box-label"
                >NARRATIVE TRAJECTORY <span class="special-icon">✦</span></span
              >
              <p class="narrative-text">
                {{ simulationConfig.event_config.narrative_direction }}
              </p>
            </div>

            <!-- Hot Topics -->
            <div class="narrative-box topics-section">
              <span class="box-label">REALITY SEED HOTSPOTS</span>
              <div class="hot-topics-grid">
                <span
                  v-for="topic in simulationConfig.event_config.hot_topics"
                  :key="topic"
                  class="hot-topic-tag"
                  >#{{ topic }}</span
                >
              </div>
            </div>

            <!-- Initial Posts -->
            <div
              v-if="simulationConfig.event_config.initial_posts?.length"
              class="initial-posts-section"
            >
              <span class="box-label">SEED PROPAGATION (INITIAL POSTS)</span>
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
                      <span class="post-role">AGENT_{{ post.agent_id }}</span>
                      <div class="post-agent-info">
                        <span class="post-username"
                          >@{{ getAgentUsername(post.agent_id) }}</span
                        >
                        <span class="post-id">#{{ post.platform }}</span>
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
            <span class="step-title">Simulation Activation</span>
          </div>
          <div class="step-status">
            <span v-if="phase >= 4" class="badge success">READY</span>
            <span v-else class="badge pending">WAITING</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">EXECUTION ENGINE READY</p>
          <p class="description">
            Environment configuration complete. Finalize simulation parameters
            and initiate the temporal loop.
          </p>

          <!-- Rounds Configuration -->
          <div class="rounds-config-section">
            <div class="rounds-header">
              <div class="header-left">
                <span class="section-title">Temporal Depth</span>
                <span class="section-desc"
                  >Define the number of rounds for this simulation
                  iteration.</span
                >
              </div>
              <div class="header-right">
                <label class="switch-control">
                  <input type="checkbox" v-model="useCustomRounds" />
                  <span class="switch-track"></span>
                  <span class="switch-label">{{
                    useCustomRounds ? "CUSTOM" : "AUTO-CONFIG"
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
                      <span class="val-unit">Rounds</span>
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
                      type="range"
                      v-model.number="customMaxRounds"
                      min="10"
                      max="200"
                      step="5"
                      class="minimal-slider"
                      :style="{
                        '--percent': ((customMaxRounds - 10) / 190) * 100 + '%',
                      }"
                    />
                    <div class="range-marks">
                      <span>10</span>
                      <span
                        class="mark-recommend"
                        :class="{ active: customMaxRounds === 40 }"
                        @click="customMaxRounds = 40"
                        >RECO: 40</span
                      >
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
                      <span class="val-unit">Rounds</span>
                    </div>
                    <div class="auto-content">
                      <div class="auto-meta-row">
                        <span class="duration-badge"
                          >DURATION:
                          {{
                            simulationConfig?.time_config
                              ?.total_simulation_hours || "?"
                          }}H</span
                        >
                      </div>
                      <div class="auto-desc">
                        <p>Optimized for maximum coverage of reality seeds.</p>
                        <p
                          class="highlight-tip"
                          @click="useCustomRounds = true"
                        >
                          Manual override available ➝
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </Transition>
            </div>
          </div>

          <!-- Final Action -->
          <div class="action-section">
            <button
              class="action-btn"
              :disabled="phase < 4"
              @click="handleStartSimulation"
            >
              INITIATE SIMULATION ENGINE ➝
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Profile Detail Modal -->
    <Transition name="modal">
      <div
        v-if="selectedProfile"
        class="profile-modal-overlay"
        @click.self="selectedProfile = null"
      >
        <div class="profile-modal">
          <div class="modal-header">
            <div class="modal-header-info">
              <div class="modal-name-row">
                <span class="modal-realname">{{ selectedProfile.name }}</span>
                <span class="modal-username"
                  >@{{ selectedProfile.username }}</span
                >
              </div>
              <span class="modal-profession">{{
                selectedProfile.profession || "Agent"
              }}</span>
            </div>
            <button class="close-btn" @click="selectedProfile = null">×</button>
          </div>

          <div class="modal-body">
            <!-- Basic Info -->
            <div class="modal-info-grid">
              <div class="info-item">
                <span class="info-label">Apparent Age</span>
                <span class="info-value"
                  >{{ selectedProfile.age || "-" }} yrs</span
                >
              </div>
              <div class="info-item">
                <span class="info-label">Apparent Gender</span>
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
                <span class="info-label">Apparent MBTI</span>
                <span class="info-value mbti">{{
                  selectedProfile.mbti || "-"
                }}</span>
              </div>
            </div>

            <!-- Bio -->
            <div class="modal-section">
              <span class="section-label">Agent Profile Bio</span>
              <p class="section-bio">
                {{ selectedProfile.bio || "No bio available" }}
              </p>
            </div>

            <!-- Interested Topics -->
            <div
              class="modal-section"
              v-if="selectedProfile.interested_topics?.length"
            >
              <span class="section-label">Reality Seed Topics</span>
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
              <span class="section-label">Detailed Persona Background</span>

              <div class="persona-dimensions">
                <div class="dimension-card">
                  <span class="dim-title">Event Trajectory</span>
                  <span class="dim-desc">Full behavior path in this event</span>
                </div>
                <div class="dimension-card">
                  <span class="dim-title">Behavior Profiling</span>
                  <span class="dim-desc"
                    >Behavioral habits and style preferences</span
                  >
                </div>
                <div class="dimension-card">
                  <span class="dim-title">Unique Memory Imprints</span>
                  <span class="dim-desc"
                    >Memories formed from reality seeds</span
                  >
                </div>
                <div class="dimension-card">
                  <span class="dim-title">Social Relation Network</span>
                  <span class="dim-desc"
                    >Individual connections and interaction graph</span
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

    <!-- Bottom Info / Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span class="log-title">SYSTEM DASHBOARD</span>
        <span class="log-id">{{ simulationId || "NO SIMULATION" }}</span>
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
  systemLogs: Array,
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
      addLog(
        "Starting generation of dual-platform simulation configuration...",
      );
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
  const calculatedRounds = Math.floor((totalHours * 60) / minutesPerRound);
  return Math.max(calculatedRounds, 40);
});

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
    return profile?.username || `agent_${agentId}`;
  }
  return `agent_${agentId}`;
};

const totalTopicsCount = computed(() => {
  return profiles.value.reduce((sum, p) => {
    return sum + (p.interested_topics?.length || 0);
  }, 0);
});

const addLog = (msg) => {
  emit("add-log", msg);
};

const handleStartSimulation = () => {
  const params = {};
  if (useCustomRounds.value) {
    params.maxRounds = customMaxRounds.value;
    addLog(
      `Initiating simulation with custom rounds: ${customMaxRounds.value}`,
    );
  } else {
    addLog(
      `Initiating simulation with auto-config rounds: ${autoGeneratedRounds.value}`,
    );
  }
  emit("next-step", params);
};

const truncateBio = (bio) => {
  if (bio && bio.length > 80) {
    return bio.substring(0, 80) + "...";
  }
  return bio || "";
};

const selectProfile = (profile) => {
  selectedProfile.value = profile;
};

const startPrepareSimulation = async () => {
  if (!props.simulationId) {
    addLog("Error: Missing simulationId");
    emit("update-status", "error");
    return;
  }

  phase.value = 1;
  addLog(`Simulation instance created: ${props.simulationId}`);
  addLog("Preparing simulation environment...");
  emit("update-status", "processing");

  try {
    const res = await prepareSimulation({
      simulation_id: props.simulationId,
      use_llm_for_profiles: true,
      parallel_profile_count: 5,
    });

    if (res.success && res.data) {
      if (res.data.already_prepared) {
        addLog("Existing preparation detected, loading data...");
        await loadPreparedData();
        return;
      }

      taskId.value = res.data.task_id;
      addLog(`Preparation task initiated`);
      addLog(`  └─ Task ID: ${res.data.task_id}`);

      if (res.data.expected_entities_count) {
        expectedTotal.value = res.data.expected_entities_count;
        addLog(`Read ${res.data.expected_entities_count} entities from Graph`);
      }

      startPolling();
      startProfilesPolling();
    } else {
      addLog(`Preparation failed: ${res.error || "Unknown error"}`);
      emit("update-status", "error");
    }
  } catch (err) {
    addLog(`Preparation exception: ${err.message}`);
    emit("update-status", "error");
  }
};

const startPolling = () => {
  pollTimer = setInterval(pollPrepareStatus, STATUS_POLL_INTERVAL_MS);
};

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

const startProfilesPolling = () => {
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
        addLog("✓ Preparation complete");
        stopPolling();
        stopProfilesPolling();
        await loadPreparedData();
      } else if (data.status === "failed") {
        addLog(`✗ Preparation failed: ${data.error || "Unknown error"}`);
        stopPolling();
        stopProfilesPolling();
      }
    }
  } catch (err) {
    if (import.meta.env.DEV) console.warn("Status polling failed:", err);
  }
};

const fetchProfilesRealtime = async () => {
  if (!props.simulationId) return;

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
          `Agent_${currentCount}`;
        if (currentCount === 1) {
          addLog(`Starting Agent profile generation...`);
        }
        addLog(
          `→ Agent profile ${currentCount}/${total}: ${profileName} (${latestProfile?.profession || "Agent"})`,
        );

        if (expectedTotal.value && currentCount >= expectedTotal.value) {
          addLog(`✓ All ${currentCount} Agent profiles generated`);
        }
      }
    }
  } catch (err) {
    if (import.meta.env.DEV) console.warn("Failed to fetch profiles:", err);
  }
};

const startConfigPolling = () => {
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
          addLog("Generating Agent profile configuration...");
        } else if (data.generation_stage === "generating_config") {
          addLog("Calling LLM to generate simulation config parameters...");
        }
      }

      if (data.config_generated && data.config) {
        simulationConfig.value = data.config;
        addLog("✓ Simulation configuration defined");

        if (data.summary) {
          addLog(`  ├─ Total Agents: ${data.summary.total_agents}`);
          addLog(`  ├─ Duration: ${data.summary.simulation_hours} hours`);
          addLog(`  ├─ Initial Posts: ${data.summary.initial_posts_count}`);
          addLog(`  ├─ Hot Topics: ${data.summary.hot_topics_count}`);
          addLog(
            `  └─ Platform Status: X ${data.summary.has_twitter_config ? "✓" : "✗"}, Reddit ${data.summary.has_reddit_config ? "✓" : "✗"}`,
          );
        }

        stopConfigPolling();
        phase.value = 4;
        addLog("✓ Environment setup complete, ready to activate simulation");
        emit("update-status", "completed");
      }
    }
  } catch (err) {
    if (import.meta.env.DEV) console.warn("Failed to fetch config:", err);
  }
};

const loadPreparedData = async () => {
  phase.value = 2;
  addLog("Loading existing configuration data...");
  await fetchProfilesRealtime();
  addLog(`Loaded ${profiles.value.length} Agent profiles`);

  try {
    const res = await getSimulationConfigRealtime(props.simulationId);
    if (res.success && res.data) {
      if (res.data.config_generated && res.data.config) {
        simulationConfig.value = res.data.config;
        addLog("✓ Simulation configuration loaded");
        phase.value = 4;
        emit("update-status", "completed");
      } else {
        addLog("Configuration still generating, waiting...");
        startConfigPolling();
      }
    }
  } catch (err) {
    addLog(`Failed to load configuration: ${err.message}`);
    emit("update-status", "error");
  }
};

const logContent = ref(null);
watch(
  () => props.systemLogs?.length,
  () => {
    nextTick(() => {
      if (logContent.value) {
        logContent.value.scrollTop = logContent.value.scrollHeight;
      }
    });
  },
);

onMounted(() => {
  if (props.simulationId) {
    addLog("Step 2 Environment Setup Initialized");
    startPrepareSimulation();
  }
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
</style>
