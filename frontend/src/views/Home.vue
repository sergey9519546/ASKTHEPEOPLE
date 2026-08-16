<template>
  <div class="public-signal-home">
    <TruthRail />
    <a class="skip-link" href="#decision">Skip to the decision</a>

    <header class="signal-masthead">
      <button class="brand-block" type="button" aria-label="ASKTHEPEOPLE / Synthetic Decision Explorer home" @click="scrollToSection('decision')">
        <span>ASKTHEPEOPLE</span>
        <span>SYNTHETIC DECISION EXPLORER</span>
      </button>

      <div class="masthead-copy">
        <p class="masthead-kicker">Synthetic scenario explorer</p>
        <h1>See the paths before you choose.</h1>
        <p class="masthead-summary">
          Stress-test a decision with source-informed synthetic scenarios.
        </p>
      </div>

      <div class="masthead-disclosure" aria-label="Important methodology disclosure">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="9"></circle>
          <path d="M12 10v6M12 7.4v.2"></path>
        </svg>
        <span><strong>0 human respondents</strong> · Not a forecast</span>
      </div>

      <nav class="signal-nav" aria-label="Page sections">
        <button class="nav-tab active" type="button" @click="scrollToSection('decision')">
          The decision
        </button>
        <button class="nav-tab" type="button" @click="scrollToSection('method')">
          Map the scenarios
        </button>
        <button class="nav-tab" type="button" @click="scrollToSection('validate')">
          Validate with people
        </button>
        <button class="settings-button" type="button" aria-label="Open model settings" @click="openSettings()">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 7h10M18 7h2M4 17h2M10 17h10M14 4v6M6 14v6"></path>
          </svg>
          <span>Settings</span>
        </button>
      </nav>
    </header>

    <main id="main-content">
      <section id="decision" class="decision-section" aria-labelledby="decision-heading">
        <div class="decision-composer">
          <div class="question-field">
            <div class="composer-header-row">
              <label for="decision-question">The decision</label>
              <div class="readiness-badge" :class="sourceReadiness.levelClass">
                <span class="readiness-dot"></span>
                <span class="readiness-text">{{ sourceReadiness.label }} ({{ sourceReadiness.score }}%)</span>
              </div>
            </div>

            <!-- Quick-Start Archetype Chips -->
            <div class="archetype-chips-row" aria-label="Decision starter templates">
              <span class="chips-label">Quick Starts:</span>
              <button
                v-for="preset in decisionPresets"
                :key="preset.id"
                type="button"
                class="archetype-chip"
                :title="preset.description"
                @click="applyPreset(preset)"
              >
                <span class="chip-icon">{{ preset.icon }}</span>
                <span>{{ preset.label }}</span>
              </button>
            </div>

            <textarea
              id="decision-question"
              v-model="formData.simulationRequirement"
              maxlength="4000"
              rows="3"
              placeholder="What could happen if…"
              aria-describedby="decision-helper decision-error"
            ></textarea>
            <p id="decision-helper" class="field-helper">
              Write one concrete choice and the outcome you want to examine.
            </p>
            <aside class="route-grammar-legend" aria-label="Route grammar — node codes used in this decision workspace">
              <strong class="grammar-label">Route grammar</strong>
              <span class="grammar-items">
                <span class="grammar-item" title="Decision">D-01</span>
                <span class="grammar-item" title="Source material">SM-01</span>
                <span class="grammar-item" title="Starting condition">SC-01</span>
                <span class="grammar-item" title="Assumption">A-01</span>
                <span class="grammar-item" title="Critical uncertainty">U-01</span>
                <span class="grammar-item" title="Generated profile / decision lens">GP-01</span>
                <span class="grammar-item" title="Possible path">P-01</span>
                <span class="grammar-item" title="Synthetic action">SA-01</span>
                <span class="grammar-item" title="Decision consideration">DC-01</span>
                <span class="grammar-item" title="Validation question">VQ-01</span>
                <span class="grammar-item" title="Related run record">RR-01</span>
              </span>
              <span class="grammar-note">Sequence only. No probability or time.</span>
            </aside>
            <details class="decision-details">
              <summary>Add a workspace name or extra context</summary>
              <div class="decision-details-grid">
                <label for="project-name">
                  <span>Workspace name <small>Optional</small></span>
                  <input
                    id="project-name"
                    v-model="formData.projectName"
                    type="text"
                    maxlength="120"
                    placeholder="A short name for this run"
                  />
                </label>
                <label for="decision-context">
                  <span>Extra context <small>Optional</small></span>
                  <textarea
                    id="decision-context"
                    v-model="formData.additionalContext"
                    maxlength="8000"
                    rows="2"
                    placeholder="Constraints, audience, location, or timeframe"
                  ></textarea>
                </label>
              </div>
            </details>
            <p v-if="questionError" id="decision-error" class="field-error" role="alert">
              {{ questionError }}
            </p>
          </div>

          <div
            class="source-material"
            :class="{ dragging: isDragOver, populated: files.length > 0 }"
            @dragover.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
            @drop.prevent="handleDrop"
          >
            <input
              ref="fileInput"
              type="file"
              multiple
              accept=".pdf,.md,.txt"
              hidden
              @change="handleFileSelect"
            />

            <button
              class="source-dropzone"
              type="button"
              :aria-label="files.length ? 'Add more source material' : 'Add source material'"
              @click="triggerFileInput"
            >
              <svg class="source-icon" viewBox="0 0 32 32" aria-hidden="true">
                <path d="M8 3h11l6 6v20H8zM19 3v7h6M12 16h9M12 21h9"></path>
              </svg>
              <div>
                <strong>{{ files.length ? "Add more source material" : "Add source material (optional)" }}</strong>
                <span>PDF, Markdown, or TXT · 10 files / 50 MB maximum</span>
              </div>
            </button>

            <div v-if="files.length" class="source-files">
              <div class="source-files-heading">
                <span>{{ files.length }} {{ files.length === 1 ? "source" : "sources" }} ready</span>
                <span class="add-more">Add more</span>
              </div>
              <ul>
                <li v-for="(file, index) in files" :key="`${file.name}-${index}`">
                  <span class="file-name">{{ file.name }}</span>
                  <button
                    type="button"
                    :aria-label="`Remove ${file.name}`"
                    @click.stop="removeFile(index)"
                  >
                    Remove
                  </button>
                </li>
              </ul>
            </div>

            <!-- URL ingestion -->
            <div class="url-ingestion">
              <label for="source-urls">Or paste URLs (one per line)</label>
              <textarea
                id="source-urls"
                v-model="urlInput"
                placeholder="https://example.com/article&#10;https://example.com/research.pdf"
                rows="3"
                :disabled="fetchingUrls"
              ></textarea>
              <button
                type="button"
                class="fetch-urls-button"
                :disabled="!urlInput.trim() || fetchingUrls || files.length >= 10"
                @click="fetchUrls"
              >
                {{ fetchingUrls ? "Fetching..." : "Fetch URLs" }}
              </button>
              <p v-if="urlFetchError" class="url-error" role="alert">{{ urlFetchError }}</p>
            </div>
          </div>

          <div class="composer-action">
            <button
              class="primary-action"
              type="button"
              :disabled="!canSubmit || loading"
              :aria-describedby="!canSubmit ? 'decision-prerequisites' : undefined"
              @click="startSimulation"
            >
              <span>{{ loading ? "Opening workspace" : "Map the scenarios" }}</span>
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 12h13M14 7l5 5-5 5"></path>
              </svg>
            </button>
            <label class="use-policy-ack">
              <input v-model="usePolicyAcknowledged" type="checkbox" required />
              <span>
                I understand this is synthetic exploration, not human evidence
                or a consequential-decision tool.
              </span>
            </label>
            <p
              v-if="!canSubmit"
              id="decision-prerequisites"
              class="submission-requirements"
              aria-live="polite"
            >
              Before you can continue: {{ submissionRequirements.join(" · ") }}.
            </p>
            <p>
              Sources give the scenario its starting material; they do not
              validate an outcome.
            </p>
          </div>
        </div>

        <p v-if="fileError" class="source-error" role="alert">{{ fileError }}</p>
      </section>

      <section id="method" class="method-section" aria-labelledby="method-heading">
        <header class="section-heading">
          <p>How the workspace works</p>
          <h2 id="method-heading">One decision. Several plausible paths.</h2>
          <span>Each branch is a synthetic possibility to inspect, challenge, and validate.</span>
        </header>

        <div
          ref="routeMap"
          class="route-map"
          aria-label="How a run flows: optional source material informs reviewed assumptions; the assumptions branch into three equal-weight possible paths of synthetic actions; the synthetic run ends at a hard break, and validation with people happens outside the system."
        >
          <article class="route-stage stage-source">
            <header class="stage-head">
              <span class="stage-index">01</span>
              <span class="stage-name">Source</span>
            </header>
            <div class="source-tile">
              <svg viewBox="0 0 32 32" aria-hidden="true">
                <path d="M8 3h11l6 6v20H8zM19 3v7h6M12 16h9M12 21h9"></path>
              </svg>
              <strong>Source material (optional)</strong>
              <span>Upload files to ground the scenarios in context, or explore with the decision alone.</span>
            </div>
          </article>

          <div class="route-link" aria-hidden="true"><span class="link-line"></span></div>

          <article class="route-stage stage-gate">
            <header class="stage-head">
              <span class="stage-index">02</span>
              <span class="stage-name">Assumptions</span>
            </header>
            <div class="gate-tile">
              <span class="gate-diamond" aria-hidden="true">A</span>
              <ol>
                <li><span>01</span> Who is affected?</li>
                <li><span>02</span> What may change?</li>
                <li><span>03</span> What stays uncertain?</li>
              </ol>
            </div>
          </article>

          <div class="route-fan" aria-hidden="true">
            <svg viewBox="0 0 24 120" preserveAspectRatio="none">
              <path pathLength="100" d="M0 60 H9 V20 H24"></path>
              <path pathLength="100" d="M0 60 H24"></path>
              <path pathLength="100" d="M0 60 H9 V100 H24"></path>
            </svg>
          </div>

          <article class="route-stage stage-paths">
            <header class="stage-head">
              <span class="stage-index">03</span>
              <span class="stage-name">Possible paths</span>
            </header>
            <div class="lane">
              <span class="lane-id">P-01</span>
              <div class="lane-track">
                <span class="lane-rule" aria-hidden="true"></span>
                <span class="lane-node">
                  <span class="node-mark" aria-hidden="true"></span>
                  <span class="node-label">Early response</span>
                </span>
                <span class="lane-node">
                  <span class="node-mark" aria-hidden="true"></span>
                  <span class="node-label">Second-order effect</span>
                </span>
                <span class="lane-node">
                  <span class="node-mark" aria-hidden="true"></span>
                  <span class="node-label">Longer-term outcome</span>
                </span>
              </div>
            </div>
            <div class="lane">
              <span class="lane-id">P-02</span>
              <div class="lane-track">
                <span class="lane-rule" aria-hidden="true"></span>
                <span class="lane-node">
                  <span class="node-mark" aria-hidden="true"></span>
                  <span class="node-label">Different response</span>
                </span>
                <span class="lane-node">
                  <span class="node-mark" aria-hidden="true"></span>
                  <span class="node-label">New pressure</span>
                </span>
                <span class="lane-node">
                  <span class="node-mark" aria-hidden="true"></span>
                  <span class="node-label">Alternative outcome</span>
                </span>
              </div>
            </div>
            <div class="lane">
              <span class="lane-id">P-03</span>
              <div class="lane-track">
                <span class="lane-rule" aria-hidden="true"></span>
                <span class="lane-node">
                  <span class="node-mark" aria-hidden="true"></span>
                  <span class="node-label">Edge case</span>
                </span>
                <span class="lane-node">
                  <span class="node-mark" aria-hidden="true"></span>
                  <span class="node-label">Unintended effect</span>
                </span>
                <span class="lane-node">
                  <span class="node-mark" aria-hidden="true"></span>
                  <span class="node-label">Risk to examine</span>
                </span>
              </div>
            </div>
          </article>

          <div class="route-break">
            <span class="break-rule" aria-hidden="true"></span>
            <span class="break-label">Synthetic run ends</span>
          </div>

          <article id="validate" class="route-stage stage-validate">
            <header class="stage-head">
              <span class="stage-index">04</span>
              <span class="stage-name">Validate with people</span>
            </header>
            <div class="validate-tile">
              <span class="validate-eyebrow">Outside the synthetic run</span>
              <svg viewBox="0 0 40 32" aria-hidden="true">
                <circle cx="20" cy="8" r="5"></circle>
                <circle cx="8" cy="13" r="4"></circle>
                <circle cx="32" cy="13" r="4"></circle>
                <path d="M11 28c0-6 4-10 9-10s9 4 9 10M1 28c0-5 3-8 7-8 2 0 4 1 5 3M39 28c0-5-3-8-7-8-2 0-4 1-5 3"></path>
              </svg>
              <strong>Take the paths outside</strong>
              <span>Use them to structure research and real conversations.</span>
            </div>
          </article>

          <p class="route-legend">
            All paths carry equal weight — spacing shows sequence only, not time or likelihood. Branches form only at reviewed assumptions.
          </p>
        </div>
      </section>

      <section id="scenarios" class="runs-section" aria-labelledby="runs-heading">
        <header class="section-heading light">
          <p>Your work</p>
          <h2 id="runs-heading">Recent scenario runs</h2>
          <span>Continue from the latest saved workspace.</span>
        </header>

        <div v-if="historyLoading" class="run-skeletons" role="status">
          <span class="visually-hidden">Loading recent scenario runs</span>
          <div v-for="index in 2" :key="index" class="run-skeleton"></div>
        </div>

        <div v-else-if="historyError" class="inline-state error-state" role="alert">
          <span class="state-index" aria-hidden="true">!</span>
          <div>
            <strong>Recent runs could not be loaded.</strong>
            <span>{{ historyError }}</span>
          </div>
          <button type="button" @click="fetchHistory">Try again</button>
        </div>

        <div v-else-if="simulationHistory.length === 0" class="inline-state empty-state">
          <span class="state-index">01</span>
          <div>
            <strong>No scenario runs yet</strong>
            <span>Add a decision and source material above to begin.</span>
          </div>
          <button type="button" @click="scrollToSection('decision')">Start with a decision</button>
        </div>

        <ol v-else class="run-list">
          <li v-for="(run, index) in simulationHistory" :key="run.simulation_id">
            <button
              type="button"
              @click="openSavedRun(run)"
            >
              <span class="run-index">{{ String(index + 1).padStart(2, "0") }}</span>
              <span class="run-main">
                <strong>{{ run.simulation_requirement || "Untitled decision" }}</strong>
                <span>
                  {{ formatDate(run.created_at) }}
                  <template v-if="run.forked_from">
                    <span class="run-branch">{{ branchLabel(run) }}</span>
                  </template>
                </span>
              </span>
              <span class="run-status">{{
                formatStatus(run.runner_status || run.status)
              }}</span>
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 12h13M14 7l5 5-5 5"></path>
              </svg>
            </button>
          </li>
        </ol>
      </section>

      <section id="templates" class="templates-section" aria-labelledby="templates-heading">
        <header class="section-heading">
          <p>Starting points</p>
          <h2 id="templates-heading">Frame a sharper question</h2>
          <span>Use a prompt structure, then rewrite it for your real decision.</span>
        </header>

        <div v-if="templatesLoading" class="template-skeletons" role="status">
          <span class="visually-hidden">Loading question starters</span>
          <div v-for="index in 2" :key="index" class="template-skeleton"></div>
        </div>

        <div v-else-if="templatesError" class="inline-state error-state dark-state" role="alert">
          <span class="state-index" aria-hidden="true">!</span>
          <div>
            <strong>Question starters could not be loaded.</strong>
            <span>You can still write your own decision above.</span>
          </div>
          <button type="button" @click="fetchTemplates">Try again</button>
        </div>

        <div v-else-if="templates.length === 0" class="inline-state dark-state">
          <strong>No question starters are available.</strong>
          <span>You can still write your own decision above.</span>
        </div>

        <div v-else class="template-list">
          <button
            v-for="(template, index) in templates"
            :key="template.id"
            type="button"
            @click="selectTemplate(template)"
          >
            <span class="template-number">{{ String(index + 1).padStart(2, "0") }}</span>
            <span class="template-copy">
              <strong>{{ template.name }}</strong>
              <span>{{ template.description }}</span>
            </span>
            <span class="template-use">Use this frame</span>
          </button>
        </div>
      </section>
    </main>

    <footer class="signal-footer">
      <div class="footer-statement">
        <strong>ASK THE PEOPLE</strong>
        <span>A tool for exploring synthetic scenarios before real-world research.</span>
      </div>
      <div class="footer-disclosure">
        <span>Outputs are generated, not observed.</span>
        <span>Do not treat them as observations from people or forecasts.</span>
      </div>
    </footer>

    <SettingsModal v-if="settingsOpen" @close="closeSettings()" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getTemplates } from "../api/graph";
import { getSimulationHistory } from "../api/simulation";
import { fetchSourceUrls } from "../api/sources.js";
import SettingsModal from "../components/SettingsModal.vue";
import TruthRail from "../components/TruthRail.vue";
import {
  closeSettings,
  openSettings,
  settingsOpen,
} from "../composables/useCommandPalette.js";
import { setPendingUpload } from "../store/pendingUpload.js";
import { savedRunDestination } from "../utils/workflow.js";

const router = useRouter();
const formData = ref({
  simulationRequirement: "",
  projectName: "",
  additionalContext: "",
});
const files = ref([]);
const loading = ref(false);
const isDragOver = ref(false);
const fileInput = ref(null);
const templates = ref([]);
const simulationHistory = ref([]);
const historyLoading = ref(true);
const templatesLoading = ref(true);
const historyError = ref("");
const templatesError = ref("");
const fileError = ref("");
const questionError = ref("");
const usePolicyAcknowledged = ref(false);
const urlInput = ref("");
const fetchingUrls = ref(false);
const urlFetchError = ref("");
const MAX_SOURCE_FILES = 10;
const MAX_SOURCE_BYTES = 50 * 1024 * 1024;

const decisionPresets = [
  {
    id: "transit",
    icon: "01",
    label: "Public Transit Fare",
    description: "Assess commuter impact, revenue, and ridership response.",
    requirement: "What could happen if the city increases peak-hour bus fare by 15% to fund weekend rapid transit expansion?",
    projectName: "Transit Fare Revision",
    context: "Focus on low-income commuters, authority revenue, traffic congestion, and community feedback."
  },
  {
    id: "remote-work",
    icon: "02",
    label: "Hybrid Work Mandate",
    description: "Examine team retention, productivity, and culture risks.",
    requirement: "What could happen if our enterprise mandates 3 days in-office per week for all product and engineering teams?",
    projectName: "Hybrid Work Policy Shift",
    context: "Assess senior retention, team collaboration velocity, office space utilization, and hiring competitiveness."
  },
  {
    id: "ai-pricing",
    icon: "03",
    label: "SaaS AI Tiering",
    description: "Evaluate subscriber conversion, usage caps, and churn.",
    requirement: "What could happen if we introduce a usage-based token quota tier for existing enterprise SaaS subscribers?",
    projectName: "SaaS AI Tiering Strategy",
    context: "Evaluate power-user conversion, support volume, churn risk among SMB accounts, and gross margin impact."
  },
  {
    id: "healthcare",
    icon: "04",
    label: "Clinic Hours Expansion",
    description: "Analyze staff workload, patient access, and ER load.",
    requirement: "What could happen if the regional hospital system shifts primary care clinic operating hours to 7 AM – 9 PM daily?",
    projectName: "Clinic Hours Expansion",
    context: "Examine nurse overtime strain, emergency room load reduction, working parent access, and patient satisfaction."
  }
];

const applyPreset = (preset) => {
  formData.value.simulationRequirement = preset.requirement;
  formData.value.projectName = preset.projectName;
  formData.value.additionalContext = preset.context;
  usePolicyAcknowledged.value = true;
};

const sourceReadiness = computed(() => {
  const reqLen = formData.value.simulationRequirement.trim().length;
  const fileCount = files.value.length;
  const hasUrls = urlInput.value.trim().length > 0;
  const ctxLen = formData.value.additionalContext.trim().length;

  let score = 0;
  if (reqLen >= 12) score += 35;
  if (reqLen >= 60) score += 15;
  if (fileCount > 0) score += Math.min(fileCount * 15, 30);
  if (hasUrls) score += 10;
  if (ctxLen > 20) score += 10;

  if (score >= 75) {
    return { score, label: "High-Precision Scenario", levelClass: "level-high" };
  } else if (score >= 40) {
    return { score, label: "Grounded Scenario", levelClass: "level-medium" };
  } else {
    return { score, label: "Initial Prompt", levelClass: "level-low" };
  }
});

const canSubmit = computed(
  () =>
    formData.value.simulationRequirement.trim().length >= 12 &&
    usePolicyAcknowledged.value,
);

const submissionRequirements = computed(() => {
  const requirements = [];
  if (formData.value.simulationRequirement.trim().length < 12) {
    requirements.push("a specific decision");
  }
  // Source material is now optional — removed from requirements
  if (!usePolicyAcknowledged.value) {
    requirements.push("the use-policy check");
  }
  return requirements;
});

const fetchHistory = async () => {
  historyLoading.value = true;
  historyError.value = "";
  try {
    const res = await getSimulationHistory(3);
    if (res.success && Array.isArray(res.data)) {
      simulationHistory.value = res.data;
    } else {
      historyError.value = res.error || "The workspace did not return any saved runs.";
    }
  } catch (error) {
    historyError.value = error?.message || "Check the connection and try again.";
  } finally {
    historyLoading.value = false;
  }
};

const fetchTemplates = async () => {
  templatesLoading.value = true;
  templatesError.value = "";
  try {
    const res = await getTemplates();
    if (res.success && Array.isArray(res.data)) {
      templates.value = res.data;
    } else {
      templatesError.value = res.error || "The workspace did not return any starters.";
    }
  } catch (error) {
    templatesError.value = error?.message || "Check the connection and try again.";
  } finally {
    templatesLoading.value = false;
  }
};

const triggerFileInput = () => fileInput.value?.click();

const handleFileSelect = (event) => {
  addFiles(Array.from(event.target.files || []));
  event.target.value = "";
};

const addFiles = (newFiles) => {
  const acceptedExtensions = ["pdf", "md", "txt"];
  const supportedFiles = newFiles.filter((file) =>
    acceptedExtensions.includes(file.name.split(".").pop()?.toLowerCase()),
  );
  const unsupportedCount = newFiles.length - supportedFiles.length;
  const existingKeys = new Set(files.value.map((file) => `${file.name}-${file.size}`));
  let totalBytes = files.value.reduce((sum, file) => sum + file.size, 0);
  let limitCount = 0;

  supportedFiles.forEach((file) => {
    const key = `${file.name}-${file.size}`;
    if (existingKeys.has(key)) return;
    if (
      files.value.length >= MAX_SOURCE_FILES ||
      totalBytes + file.size > MAX_SOURCE_BYTES
    ) {
      limitCount += 1;
      return;
    }
    files.value.push(file);
    existingKeys.add(key);
    totalBytes += file.size;
  });

  const messages = [];
  if (unsupportedCount > 0) {
    messages.push(
      `${unsupportedCount} unsupported ${
        unsupportedCount === 1 ? "file was" : "files were"
      } skipped; use PDF, Markdown, or TXT.`,
    );
  }
  if (limitCount > 0) {
    messages.push(
      `${limitCount} ${
        limitCount === 1 ? "file was" : "files were"
      } skipped; add up to 10 files and 50 MB total.`,
    );
  }
  fileError.value = messages.join(" ");
};

const removeFile = (index) => {
  files.value.splice(index, 1);
};

const fetchUrls = async () => {
  urlFetchError.value = "";
  
  const urls = urlInput.value
    .split("\n")
    .map((u) => u.trim())
    .filter((u) => u.startsWith("http://") || u.startsWith("https://"));
  
  if (urls.length === 0) {
    urlFetchError.value = "Enter at least one valid URL (must start with http:// or https://)";
    return;
  }
  
  if (urls.length > 10) {
    urlFetchError.value = "Maximum 10 URLs at a time";
    return;
  }
  
  if (files.value.length + urls.length > MAX_SOURCE_FILES) {
    urlFetchError.value = `Would exceed ${MAX_SOURCE_FILES} file limit (currently ${files.value.length} files)`;
    return;
  }
  
  fetchingUrls.value = true;
  
  try {
    const data = await fetchSourceUrls(urls);
    
    if (!data.success) {
      urlFetchError.value = data.error || "Failed to fetch URLs";
      return;
    }
    
    // Add fetched files to the files array
    // Convert API response format to File-like objects
    for (const fileData of data.files) {
      // Create a synthetic File object that matches what file upload produces
      const blob = new Blob([`Fetched from: ${fileData.source_url}`], { type: "text/plain" });
      const file = new File([blob], fileData.name, { type: "text/plain" });
      // Store the source URL as a property for later reference
      file.sourceUrl = fileData.source_url;
      files.value.push(file);
    }
    
    // Clear input after successful fetch
    urlInput.value = "";
    
    // Show errors for any failed URLs
    if (data.errors && data.errors.length > 0) {
      const failedCount = data.errors.length;
      const successCount = data.files.length;
      urlFetchError.value = `Fetched ${successCount} URL${successCount === 1 ? "" : "s"}. ${failedCount} failed.`;
    }
  } catch (error) {
    urlFetchError.value =
      error?.code === "ACCESS_REQUIRED"
        ? "Access key required or invalid."
        : "Failed to fetch URLs. Check the source and try again.";
  } finally {
    fetchingUrls.value = false;
  }
};

const handleDrop = (event) => {
  isDragOver.value = false;
  addFiles(Array.from(event.dataTransfer?.files || []));
};

const startSimulation = () => {
  const question = formData.value.simulationRequirement.trim();
  questionError.value =
    question.length < 12
      ? "Add a little more detail so the decision is specific enough to examine."
      : "";

  if (!canSubmit.value || loading.value) return;

  loading.value = true;
  setPendingUpload(
    files.value,
    question,
    usePolicyAcknowledged.value,
    formData.value.projectName.trim(),
    formData.value.additionalContext.trim(),
  );
  router
    .push({ name: "Process", params: { projectId: "new" } })
    .catch((error) => {
      questionError.value =
        error?.message || "The workspace could not be opened. Try again.";
      loading.value = false;
    });
};

const openSavedRun = (run) => {
  router.push(savedRunDestination(run));
};

const selectTemplate = (template) => {
  const parts = [template.prompt_base, template.suggested_ontology_goal].filter(Boolean);
  formData.value.simulationRequirement = parts.join("\n\n");
  questionError.value = "";
  scrollToSection("decision");
};

const scrollToSection = (id) => {
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
  document
    .getElementById(id)
    ?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
};

/* The method-section route map is a one-shot scroll reveal, not a mount
   autoplay. The diagram's CSS choreography (route-draw-x/y, route-draw-stroke,
   node-in) still drives the draw-in, but its play-state is paused until the
   diagram enters the viewport (see the `.route-map` play-state gate in
   <style>); revealing flips play-state to running so the designed delay
   ladder runs once and settles on `forwards`. The diagram's narrative is
   top→bottom (source 01 → validate 04) but it enters the viewport bottom-up,
   so a -25% bottom root anchor triggers once the top source tile reaches the
   lower 75% of screen: the narrative's start is on screen before play begins,
   instead of firing off-screen at mount and settling invisible. */
const routeMap = ref(null);
let routeRevealObserver = null;

onMounted(() => {
  const el = routeMap.value;
  if (!el) return;
  const revealImmediately =
    window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ||
    typeof IntersectionObserver === "undefined";
  if (revealImmediately) {
    el.classList.add("is-revealed");
    return;
  }
  routeRevealObserver = new IntersectionObserver(
    (entries, observer) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-revealed");
          observer.unobserve(entry.target);
        }
      }
    },
    { rootMargin: "0px 0px -25% 0px", threshold: 0 },
  );
  routeRevealObserver.observe(el);
});

onBeforeUnmount(() => {
  routeRevealObserver?.disconnect();
  routeRevealObserver = null;
});

const formatDate = (value) => {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
};

// Counterfactual branches carry forked_from / forked_at_turn from
// /api/simulation/history. Phrased as provenance of a synthetic run — a branch
// is another exploration, not an alternative outcome.
const branchLabel = (run) => {
  if (!run?.forked_from) return "";
  const parent = String(run.forked_from).replace(/^sim_/, "").slice(0, 6).toUpperCase();
  const turn = run.forked_at_turn;
  return turn === null || turn === undefined
    ? `Branched from ${parent}`
    : `Branched from ${parent} at turn ${turn}`;
};

const formatStatus = (status) => {
  const labels = {
    completed: "Ready to review",
    stopped: "Ready to review",
    starting: "Starting",
    running: "In progress",
    stopping: "Finishing",
    idle: "Ready to set up",
    ready: "Ready to set up",
    preparing: "Preparing",
    interrupted: "Needs attention",
    pending: "Waiting",
    failed: "Needs attention",
  };
  return labels[String(status).toLowerCase()] || "Saved";
};

fetchTemplates();
fetchHistory();
</script>

<style scoped>
.public-signal-home {
  position: relative;
  overflow: hidden;
  min-height: 100dvh;
  background: var(--ink);
  color: var(--paper);
}

.skip-link {
  position: fixed;
  top: 0.75rem;
  left: 0.75rem;
  z-index: 30;
  padding: 0.75rem 1rem;
  background: var(--signal);
  color: var(--ink);
  font-weight: 700;
  transform: translateY(-160%);
  transition: transform 180ms var(--ease-out);
}

.skip-link:focus {
  transform: translateY(0);
}

.signal-masthead { min-height: 16rem;
  border-bottom: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.brand-block {
  grid-area: brand;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  min-width: 0;
  padding: 1.5rem clamp(1.25rem, 2.8vw, 3rem);
  overflow: hidden;
  border: 0;
  background: var(--ink-deep);
  color: var(--paper);
  font-family: var(--font-display);
  font-size: clamp(2.1rem, 2.5vw, 3.2rem);
  font-weight: 900;
  line-height: 0.78;
  letter-spacing: -0.025em;
  text-align: left;
  text-transform: uppercase;
  transform: none;
}

.brand-block::after {
  content: "";
  position: absolute;
  top: -15%;
  right: -2.75rem;
  width: 4.75rem;
  height: 130%;
  background: linear-gradient(105deg, transparent 40%, rgba(242, 235, 221, 0.08) 60%, transparent 80%);
  transform: rotate(4deg);
  transform-origin: center;
  pointer-events: none;
}

.brand-block:hover {
  background: var(--ink);
  color: var(--paper-strong);
}

.masthead-copy {
  grid-area: copy;
  align-self: end;
  padding: 2rem clamp(2rem, 4vw, 4.5rem) 1.4rem;
}

.masthead-kicker,
.section-heading > p {
  font-family: var(--font-display);
  font-size: 1rem;
  letter-spacing: 0.045em;
  text-transform: uppercase;
}

.masthead-kicker {
  margin-bottom: 0.55rem;
  color: var(--attention);
}

.masthead-copy h1 {
  max-width: 18ch;
  margin: 0;
  color: var(--paper);
  font-family: var(--font-display);
  font-size: clamp(2.65rem, 4vw, 4.5rem);
  font-weight: 900;
  line-height: 0.9;
  letter-spacing: -0.02em;
  text-wrap: balance;
}

.masthead-summary {
  max-width: 42rem;
  margin-top: 0.85rem;
  color: var(--paper-muted);
  font-size: clamp(1rem, 1.2vw, 1.25rem);
  line-height: 1.5;
}

.masthead-disclosure {
  grid-area: disclosure;
  align-self: end;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 1rem;
  margin: 0 2.4rem 1.6rem 0;
  color: var(--attention);
  font-size: 0.84rem;
  white-space: nowrap;
  background: transparent;
  border: 1px solid var(--attention-rule);
  border-radius: 0;
  box-shadow: none;
}

.masthead-disclosure strong {
  color: var(--paper);
  font-weight: 700;
}

.masthead-disclosure svg {
  width: 1.3rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
}

.signal-nav {
  grid-area: nav;
  display: flex;
  align-items: stretch;
  min-height: 4rem;
  padding-left: clamp(2rem, 4vw, 4.5rem);
}

.nav-tab,
.settings-button {
  min-height: 3rem;
  border: 0;
  border-left: 1px solid var(--line-dark);
  background: transparent;
  color: var(--paper-muted);
  font-family: var(--font-display);
  font-size: 1rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.nav-tab {
  padding: 0.8rem clamp(1rem, 2.3vw, 2.5rem);
}

.nav-tab.active {
  align-self: center;
  min-height: 3rem;
  margin-right: 0.8rem;
  border-left: 0;
  background: var(--signal);
  color: var(--ink);
}

.nav-tab:hover,
.settings-button:hover {
  background: var(--ink-soft);
  color: var(--paper);
}

.settings-button {
  display: inline-flex;
  gap: 0.55rem;
  align-items: center;
  margin-left: auto;
  padding: 0.8rem 2.2rem;
}

.settings-button svg {
  width: 1.15rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
}

.decision-section {
  padding: clamp(1rem, 2vw, 2rem);
  background: var(--ink);
  scroll-margin-top: 1rem;
}

.decision-composer {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(18rem, 0.65fr) minmax(18rem, 0.55fr);
  align-items: stretch;
  max-width: 104rem;
  min-height: 12rem;
  margin: 0 auto;
  background: var(--paper);
  color: var(--ink);
}

.question-field {
  display: flex;
  flex-direction: column;
  padding: 1.7rem 1.8rem 1.45rem;
  border-right: 1px solid var(--line-light);
}

.question-field label {
  margin-bottom: 0.5rem;
  font-family: var(--font-display);
  font-size: 1rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.question-field textarea {
  width: 100%;
  min-height: 5.2rem;
  padding: 0 0 0.5rem 0 !important;
  border: 0 !important;
  border-bottom: 2px solid var(--line-light) !important;
  background: transparent !important;
  color: var(--ink) !important;
  font-family: var(--font-display) !important;
  font-size: clamp(2rem, 3.1vw, 3.7rem) !important;
  font-weight: 900;
  line-height: 0.98;
  letter-spacing: -0.015em;
  resize: vertical;
  transition: border-color 200ms ease, box-shadow 200ms ease;
}

.question-field textarea::placeholder {
  color: #a3a098;
  opacity: 1;
}

.question-field textarea:focus {
  border-color: var(--signal) !important;
  box-shadow: none;
  outline: none;
}

.field-helper,
.composer-action p {
  margin-top: 0.65rem;
  color: var(--ink-muted);
  font-size: 0.78rem;
  line-height: 1.4;
}

.field-error,
.source-error {
  margin-top: 0.55rem;
  color: var(--error-text);
  font-size: 0.78rem;
  font-weight: 600;
}

.decision-details {
  margin-top: 0.65rem;
}

.decision-details summary {
  width: fit-content;
  color: var(--ink-muted);
  font-size: 0.74rem;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 0.18rem;
}

.decision-details-grid {
  display: grid;
  grid-template-columns: minmax(10rem, 0.45fr) minmax(0, 1fr);
  gap: 0.7rem;
  margin-top: 0.7rem;
}

.decision-details-grid label {
  display: grid;
  gap: 0.35rem;
  margin: 0;
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.035em;
}

.decision-details-grid label small {
  color: var(--ink-muted);
  font-size: inherit;
  font-weight: 500;
}

.decision-details-grid input,
.decision-details-grid textarea {
  min-height: 2.5rem;
  padding: 0.6rem 0.65rem !important;
  border: 1px solid var(--line-light) !important;
  background: var(--paper-strong) !important;
  color: var(--ink) !important;
  font-family: var(--font-sans) !important;
  font-size: 0.78rem !important;
  font-weight: 500;
  line-height: 1.3;
}

.decision-details-grid textarea {
  min-height: 3.5rem;
}

.source-material {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  gap: 0.75rem;
  padding: 1.5rem;
}

.source-dropzone {
  width: 100%;
  min-width: 0;
  min-height: 7rem;
  align-items: center;
  justify-content: flex-start;
  gap: 1rem;
  padding: 1.1rem;
  border: 2px dashed var(--ink-muted);
  background: var(--paper-strong);
  color: var(--ink);
  text-align: left;
  box-shadow: none;
  transition:
    transform 220ms var(--ease-out),
    background-color 220ms var(--ease-out),
    border-color 220ms var(--ease-out),
    box-shadow 220ms var(--ease-out);
}

.source-dropzone:hover,
.source-dropzone:focus-visible {
  border-color: var(--signal);
  background: var(--signal-soft);
  transform: translateY(-2px);
}

.source-material.dragging .source-dropzone {
  border-color: var(--signal);
  background: var(--signal-soft);
  transform: translateY(-2px);
  box-shadow: 0.45rem 0.45rem 0 var(--signal-deep);
}

.source-icon {
  width: 2.4rem;
  flex: 0 0 auto;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
}

.source-dropzone strong,
.source-dropzone span {
  display: block;
}

.source-dropzone strong {
  font-size: 0.95rem;
}

.source-dropzone > div > span {
  margin-top: 0.25rem;
  color: var(--ink-muted);
  font-size: 0.74rem;
}

.source-files {
  min-width: 0;
  width: 100%;
  padding: 0.7rem 0.8rem;
  border: 1px solid var(--line-light);
  background: var(--paper-strong);
}

.source-files-heading {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.55rem;
  font-size: 0.78rem;
  font-weight: 700;
}

.source-files-heading .add-more {
  color: var(--ink-muted);
  font-weight: 500;
}

.source-files ul {
  display: grid;
  gap: 0.35rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.source-files li {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  justify-content: space-between;
  padding-top: 0.35rem;
  border-top: 1px solid var(--line-light);
}

.source-files .file-name {
  overflow: hidden;
  color: var(--ink);
  font-size: 0.72rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-files button {
  padding: 0.25rem;
  border: 0;
  background: transparent;
  color: var(--ink-muted);
  font-size: 0.68rem;
  text-decoration: underline;
}

.source-files button:hover {
  background: transparent;
  color: var(--ink);
}

.url-ingestion {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 1rem 0.8rem;
  margin-top: 0.8rem;
  border: 1px solid var(--line-light);
  background: var(--paper-strong);
}

.url-ingestion label {
  color: var(--ink);
  font-size: 0.76rem;
  font-weight: 600;
}

.url-ingestion textarea {
  min-height: 4rem;
  padding: 0.5rem;
  border: 1px solid var(--line-dark);
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-mono, monospace);
  font-size: 0.72rem;
  line-height: 1.4;
  resize: vertical;
}

.url-ingestion textarea:focus {
  outline: 2px solid var(--signal);
  outline-offset: 2px;
}

.url-ingestion textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.fetch-urls-button {
  align-self: flex-start;
  padding: 0.5rem 1rem;
  border: 1px solid var(--line-dark);
  background: var(--paper-strong);
  color: var(--ink);
  font-size: 0.74rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 120ms var(--ease-quick);
}

.fetch-urls-button:hover:not(:disabled) {
  background: var(--signal-soft);
  border-color: var(--ink);
}

.fetch-urls-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.url-error {
  margin: 0;
  padding: 0.4rem 0.6rem;
  background: var(--error-soft);
  color: var(--error-text);
  font-size: 0.7rem;
  line-height: 1.3;
}

.composer-action {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.85rem;
  padding: 1.5rem;
  border-left: 1px solid var(--line-light);
}

.use-policy-ack {
  display: grid;
  grid-template-columns: 1rem minmax(0, 1fr);
  gap: 0.55rem;
  align-items: start;
  color: var(--ink);
  font-size: 0.72rem;
  font-weight: 600;
  line-height: 1.35;
  cursor: pointer;
}

.use-policy-ack input {
  width: 1rem;
  height: 1rem;
  margin: 0.05rem 0 0;
  border: 1px solid var(--ink);
  border-radius: 0;
  accent-color: var(--signal-deep);
}

.submission-requirements {
  padding-top: 0.7rem;
  border-top: 1px solid var(--line-light);
  color: var(--error-text) !important;
  font-weight: 650;
}

.primary-action {
  display: flex;
  min-height: 4.2rem;
  padding: 0.9rem 1.15rem;
  border: 1px solid var(--signal-deep);
  background: var(--signal);
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1.2rem;
  letter-spacing: 0.025em;
  text-transform: uppercase;
}

.primary-action:hover:not(:disabled) {
  border-color: var(--ink);
  background: var(--signal-strong);
  color: var(--ink);
  transform: translateY(-2px);
}

.primary-action svg,
.run-list svg {
  width: 1.35rem;
  fill: none;
  stroke: currentColor;
  stroke-linecap: square;
  stroke-width: 2;
}

.source-error {
  max-width: 104rem;
  margin-right: auto;
  margin-left: auto;
}

.method-section,
.templates-section {
  padding: clamp(3.5rem, 7vw, 7.5rem) clamp(1rem, 3.4vw, 4rem);
  background:
    linear-gradient(rgba(242, 235, 221, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(242, 235, 221, 0.025) 1px, transparent 1px),
    var(--ink);
  background-size: 1.5rem 1.5rem;
  scroll-margin-top: 1rem;
}

.section-heading {
  display: grid;
  grid-template-columns: minmax(10rem, 0.5fr) minmax(0, 1.15fr) minmax(16rem, 0.75fr);
  align-items: end;
  gap: 2rem;
  max-width: 104rem;
  margin: 0 auto 3rem;
}

.section-heading > p {
  color: var(--attention);
}

.section-heading h2 {
  margin: 0;
  color: var(--paper);
  font-family: var(--font-display);
  font-size: clamp(2.6rem, 4vw, 5rem);
  line-height: 0.92;
  letter-spacing: -0.015em;
  text-wrap: balance;
}

.section-heading > span {
  max-width: 31rem;
  color: var(--paper-muted);
  font-size: 0.95rem;
  line-height: 1.55;
  text-wrap: pretty;
}

/* Route Ledger — the route grammar drawn as one continuous route:
   source informs the assumption gate (the only object allowed to branch),
   three equal-weight possible paths carry synthetic actions in sequence,
   and a hard break ends the synthetic run before validation with people. */
.route-map {
  display: grid;
  grid-template-columns:
    minmax(10rem, 0.72fr)
    clamp(1.5rem, 2.5vw, 3rem)
    minmax(11rem, 0.85fr)
    clamp(1.75rem, 3vw, 3.5rem)
    minmax(24rem, 2.5fr)
    clamp(2rem, 3vw, 3.25rem)
    minmax(10rem, 0.72fr);
  max-width: 104rem;
  margin: 0 auto;
  border-top: 1px solid var(--line-dark);
  border-bottom: 1px solid var(--line-dark);
}

.route-stage {
  display: flex;
  min-width: 0;
  flex-direction: column;
  padding: 1.6rem 1.3rem 1.8rem;
}

.stage-head {
  display: flex;
  gap: 0.55rem;
  align-items: baseline;
  margin-bottom: 1.4rem;
}

.stage-index {
  color: var(--paper-dim);
  font-family: var(--font-display);
  font-size: 0.95rem;
  letter-spacing: 0.06em;
}

.stage-name {
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 0.95rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.stage-paths .stage-name {
  color: var(--signal);
}

.source-tile {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1.3rem;
  background: var(--paper);
  color: var(--ink);
  text-align: center;
}

.source-tile svg {
  width: 2.6rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
}

.source-tile strong {
  margin-top: 1rem;
  font-size: 0.96rem;
  line-height: 1.25;
}

.source-tile span {
  margin-top: 0.45rem;
  color: var(--ink-muted);
  font-size: 0.76rem;
  line-height: 1.45;
}

/* Trunk connector: source → assumption gate. */
.route-link {
  position: relative;
}

.link-line {
  position: absolute;
  top: 50%;
  right: 0;
  left: 0;
  height: 2px;
  background: var(--paper-muted);
  transform: scaleX(0);
  transform-origin: left;
  animation: route-draw-x var(--duration-base) var(--ease-out) 120ms forwards;
}

/* Assumption gate: paper review surface; the red diamond is the only
   object in the diagram allowed to create a branch. */
.gate-tile {
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: center;
  padding: 1.1rem 0.9rem;
  background: var(--paper);
  color: var(--ink);
}

.gate-diamond {
  position: relative;
  display: grid;
  width: 2.6rem;
  height: 2.6rem;
  place-items: center;
  margin: 0.4rem auto 1.1rem;
  color: var(--signal-deep);
  font-family: var(--font-display);
  font-size: 1rem;
}

.gate-diamond::before {
  content: "";
  position: absolute;
  inset: 0.34rem;
  border: 2px solid var(--signal);
  transform: rotate(45deg);
}

.gate-tile ol {
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
}

.gate-tile li {
  display: grid;
  grid-template-columns: 1.7rem 1fr;
  align-items: center;
  gap: 0.4rem;
  padding: 0.7rem 0.1rem;
  font-size: 0.78rem;
  line-height: 1.3;
}

.gate-tile li + li {
  border-top: 1px solid var(--line-light);
}

.gate-tile li span {
  color: var(--ink-muted);
  font-family: var(--font-mono);
  font-size: 0.68rem;
}

/* Branch fan: the gate emits three equal-weight lanes. */
.route-fan {
  min-width: 0;
}

.route-fan svg {
  display: block;
  width: 100%;
  height: 100%;
}

.route-fan path {
  fill: none;
  stroke: var(--paper-muted);
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
  stroke-dasharray: 100;
  stroke-dashoffset: 100;
  animation: route-draw-stroke var(--duration-base) var(--ease-out) 220ms forwards;
}

.route-fan path:nth-of-type(2) {
  animation-delay: 280ms;
}

.route-fan path:nth-of-type(3) {
  animation-delay: 340ms;
}

/* Lanes: equal weight, equal color, visible P-## identifiers. */
.lane {
  --lane-delay: 420ms;
  display: grid;
  flex: 1;
  grid-template-columns: 3.6rem minmax(0, 1fr);
  align-items: center;
  min-height: 4.8rem;
}

.stage-paths .lane:nth-child(3) {
  --lane-delay: 480ms;
}

.stage-paths .lane:nth-child(4) {
  --lane-delay: 540ms;
}

.lane-id {
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 1.02rem;
  letter-spacing: 0.05em;
}

.lane-track {
  position: relative;
  height: 4.6rem;
  min-width: 0;
}

.lane-rule {
  position: absolute;
  top: 50%;
  right: 0;
  left: 0;
  height: 2px;
  background: var(--paper);
  transform: scaleX(0);
  transform-origin: left;
  animation: route-draw-x var(--duration-base) var(--ease-out) var(--lane-delay) forwards;
}

.lane-node {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 30%;
  transform: translateX(-50%);
}

.lane-node:nth-of-type(2) {
  left: 18%;
}

.lane-node:nth-of-type(3) {
  left: 50%;
}

.lane-node:nth-of-type(4) {
  left: 82%;
}

.node-mark {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0.85rem;
  height: 0.85rem;
  border: 2px solid var(--paper);
  background: var(--ink);
  transform: translate(-50%, -50%);
  opacity: 0;
  animation: node-in var(--duration-quick) var(--ease-out) forwards;
}

.lane-node:nth-of-type(2) .node-mark,
.lane-node:nth-of-type(2) .node-label {
  animation-delay: calc(var(--lane-delay) + 40ms);
}

.lane-node:nth-of-type(3) .node-mark,
.lane-node:nth-of-type(3) .node-label {
  animation-delay: calc(var(--lane-delay) + 110ms);
}

.lane-node:nth-of-type(4) .node-mark,
.lane-node:nth-of-type(4) .node-label {
  animation-delay: calc(var(--lane-delay) + 180ms);
}

.node-label {
  position: absolute;
  top: calc(50% + 0.8rem);
  left: 50%;
  width: max-content;
  max-width: 7.5rem;
  color: var(--paper);
  font-size: 0.7rem;
  line-height: 1.25;
  text-align: center;
  transform: translateX(-50%);
  opacity: 0;
  animation: node-in var(--duration-quick) var(--ease-out) forwards;
}

/* The break: the synthetic run terminates here. Lanes stop dead at the
   dashed rule; validation lives on the other side of it. */
.route-break {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.6rem 0 1.8rem;
}

.break-rule {
  position: absolute;
  top: 1.6rem;
  bottom: 1.8rem;
  left: 50%;
  width: 0;
  border-left: 2px dashed var(--paper-dim);
  transform: translateX(-50%);
}

.break-label {
  position: relative;
  padding: 0.9rem 0.35rem;
  background: var(--ink);
  color: var(--paper-dim);
  font-family: var(--font-display);
  font-size: 0.66rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  writing-mode: vertical-rl;
}

/* Validation tile: the white transfer surface — outside the synthetic run. */
.validate-tile {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1.3rem 1.1rem;
  border: 1px solid var(--ink);
  background: var(--paper-transfer);
  color: var(--ink);
  text-align: center;
}

.validate-eyebrow {
  margin-bottom: 0.9rem;
  color: var(--ink-muted);
  font-family: var(--font-display);
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.validate-tile svg {
  width: 3.2rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
}

.validate-tile strong {
  margin-top: 0.9rem;
  font-size: 0.95rem;
  line-height: 1.25;
}

.validate-tile span {
  margin-top: 0.45rem;
  color: var(--ink-muted);
  font-size: 0.76rem;
  line-height: 1.45;
}

/* Grammar-required legend (route rules 1 and 9). */
.route-legend {
  grid-column: 1 / -1;
  margin: 0;
  padding: 0.85rem 1.3rem;
  border-top: 1px solid var(--line-dark);
  color: var(--paper-dim);
  font-family: var(--font-display);
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-align: center;
  text-transform: uppercase;
}

@keyframes route-draw-x {
  to {
    transform: scaleX(1);
  }
}

@keyframes route-draw-y {
  to {
    transform: scaleY(1);
  }
}

@keyframes route-draw-stroke {
  to {
    stroke-dashoffset: 0;
  }
}

@keyframes node-in {
  to {
    opacity: 1;
  }
}

/* The method section's route-map draw-in is a scroll-triggered one-shot, not a
   mount autoplay. Pausing the signature animations here holds each child at its
   base (pre-) state (opacity:0, transform:scaleX/Y(0), stroke-dashoffset:100)
   while hidden; when the IntersectionObserver bound to `routeMap` in <script
   setup> adds `.is-revealed`, the `--route-play` custom property flips to
   `running` and the designed delay ladder plays once, settling on `forwards`.
   One selector list drives both states so they cannot drift. The superset
   matches the prefers-reduced-motion reset set (minus the independent loading
   skeletons) so both layouts (desktop horizontal, mobile vertical) are gated;
   play-state is a no-op on elements that have no animation in a given layout.
   `:where()` keeps specificity 0 so this can't fight the animation declarations
   above or the reduced-motion block below. */
.route-map
  :where(
    .link-line,
    .lane-rule,
    .lane-track::before,
    .route-fan path,
    .route-fan::after,
    .node-mark,
    .node-label
  ) {
  animation-play-state: var(--route-play, paused);
}
.route-map.is-revealed {
  --route-play: running;
}

.runs-section {
  padding: clamp(3.5rem, 7vw, 7.5rem) clamp(1rem, 3.4vw, 4rem);
  background: var(--paper);
  color: var(--ink);
}

.section-heading.light > p {
  color: var(--signal-text);
}

.section-heading.light h2 {
  color: var(--ink);
}

.section-heading.light > span {
  color: var(--ink-muted);
}

.run-list,
.run-skeletons,
.inline-state,
.template-list,
.template-skeletons {
  max-width: 104rem;
  margin-right: auto;
  margin-left: auto;
}

.run-list {
  margin-top: 0;
  padding: 0;
  border-top: 2px solid var(--ink);
  list-style: none;
}

.run-list li {
  border-bottom: 1px solid var(--line-light);
}

.run-list button {
  display: grid;
  grid-template-columns: 4rem minmax(0, 1fr) minmax(8rem, auto) 2rem;
  align-items: center;
  gap: 1.2rem;
  width: 100%;
  min-height: 7.5rem;
  padding: 1.2rem 1rem;
  margin: 0.5rem 0;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--ink);
  text-align: left;
  transition: all 200ms ease;
}

.run-list button:hover {
  background: var(--paper-strong);
  border-color: var(--line-light);
  transform: translateY(-2px);
  box-shadow: 0 8px 20px -8px rgba(0, 0, 0, 0.05);
}

.run-index,
.template-number,
.state-index {
  color: var(--ink-muted);
  font-family: var(--font-mono);
  font-size: 0.72rem;
}

.run-main {
  min-width: 0;
}

.run-main strong,
.run-main span {
  display: block;
}

.run-main strong {
  overflow: hidden;
  font-family: var(--font-display);
  font-size: clamp(1.4rem, 2.3vw, 2.7rem);
  line-height: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.run-main span {
  margin-top: 0.45rem;
  color: var(--ink-muted);
  font-size: 0.74rem;
}

.run-status {
  color: var(--ink-muted);
  font-size: 0.76rem;
  font-weight: 600;
}

/* `.run-main span` is display:block, so the branch marker is nested inside the
   date line and set back to inline to sit beside it rather than push the row
   taller. */
.run-branch {
  display: inline !important;
  margin-left: 0.5rem;
  padding: 0.1rem 0.4rem;
  border: 1px solid var(--line-light);
  border-radius: 3px;
  font-family: var(--font-mono);
  font-size: 0.66rem;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.run-skeletons,
.template-skeletons {
  display: grid;
  gap: 1px;
  background: var(--line-light);
}

.run-skeleton,
.template-skeleton {
  min-height: 7rem;
  background:
    linear-gradient(90deg, transparent, rgba(242, 235, 221, 0.62), transparent),
    var(--paper-strong);
  background-size: 50% 100%;
  animation: skeleton-pass 1.4s ease-in-out infinite;
}

.inline-state {
  display: grid;
  grid-template-columns: 4rem minmax(0, 1fr) auto;
  align-items: center;
  gap: 1.2rem;
  min-height: 9rem;
  padding: 1.5rem;
  border-top: 2px solid var(--ink);
  border-bottom: 1px solid var(--line-light);
}

.inline-state > div strong,
.inline-state > div span,
.inline-state > strong,
.inline-state > span {
  display: block;
}

.inline-state span {
  margin-top: 0.3rem;
  color: var(--ink-muted);
  font-size: 0.82rem;
}

.inline-state button {
  border-color: var(--ink);
  background: var(--ink);
  color: var(--paper);
}

.inline-state button:hover {
  background: var(--signal);
  color: var(--ink);
}

.error-state {
  border-top-color: var(--error);
}

.template-list {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(0, 0.65fr);
  border-top: 1px solid var(--line-dark);
}

.template-list button {
  display: grid;
  grid-template-columns: 3rem minmax(0, 1fr) auto;
  align-items: center;
  gap: 1rem;
  min-height: 8rem;
  padding: 1.35rem;
  border: 0;
  border-right: 1px solid var(--line-dark);
  border-bottom: 1px solid var(--line-dark);
  background: transparent;
  color: var(--paper);
  text-align: left;
}

.template-list button:nth-child(4n + 2),
.template-list button:nth-child(4n + 3) {
  grid-column: auto;
}

.template-list button:hover {
  background: var(--signal);
  color: var(--ink);
}

.template-list button:hover .template-number,
.template-list button:hover .template-copy span {
  color: var(--ink-muted);
}

.template-copy strong,
.template-copy span {
  display: block;
}

.template-copy strong {
  font-family: var(--font-display);
  font-size: clamp(1.3rem, 2vw, 2rem);
  line-height: 1;
}

.template-copy span {
  max-width: 48ch;
  margin-top: 0.45rem;
  color: var(--paper-muted);
  font-size: 0.75rem;
  line-height: 1.45;
}

.template-number {
  color: var(--paper-dim);
}

.template-use {
  color: var(--signal);
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
}

.dark-state {
  border-color: var(--line-dark);
  color: var(--paper);
}

.dark-state span {
  color: var(--paper-muted);
}

.dark-state button {
  border-color: var(--signal);
  background: var(--signal);
  color: var(--ink);
}

.signal-footer {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  padding: 2.5rem clamp(1rem, 3.4vw, 4rem);
  border-top: 1px solid var(--line-dark);
  background: var(--ink);
}

.footer-statement,
.footer-disclosure {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  color: var(--paper-muted);
  font-size: 0.76rem;
  line-height: 1.5;
}

.footer-statement strong {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 1.3rem;
  letter-spacing: 0.035em;
}

.footer-disclosure {
  align-items: flex-end;
  text-align: right;
}

@keyframes skeleton-pass {
  from {
    background-position: -100% 0;
  }
  to {
    background-position: 200% 0;
  }
}

.route-grammar-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem 0.85rem;
  margin-top: 0.75rem;
  padding: 0.55rem 0.7rem;
  border: 1px solid var(--line-light);
  background: var(--paper-transfer);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 0.72rem;
  line-height: 1.35;
}

.grammar-label {
  font-family: var(--font-display);
  font-size: 0.72rem;
  letter-spacing: 0.035em;
  text-transform: uppercase;
  white-space: nowrap;
}

.grammar-items {
  display: flex;
  flex-wrap: wrap;
  gap: 0.15rem 0.35rem;
}

.grammar-item {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
  padding: 0.08rem 0.35rem;
  border: 1px solid var(--line-dark);
  background: var(--paper);
  color: var(--ink-muted);
  font-family: var(--font-mono);
  font-size: 0.62rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.grammar-item:hover {
  border-color: var(--signal);
  color: var(--signal-deep);
}

.grammar-note {
  margin-left: auto;
  color: var(--ink-muted);
  font-size: 0.62rem;
  font-style: italic;
  white-space: nowrap;
}

@media (max-width: 767px) {
  .route-grammar-legend {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.35rem;
  }
  .grammar-note {
    margin-left: 0;
  }
}

@media (max-width: 1050px) {
  .signal-masthead {
    grid-template-columns: minmax(12rem, 16rem) 1fr;
    grid-template-areas:
      "brand copy"
      "brand disclosure"
      "nav nav";
  }

  .masthead-disclosure {
    align-self: center;
    padding: 0 2rem 1rem;
  }

  .decision-composer {
    grid-template-columns: minmax(0, 1.4fr) minmax(16rem, 0.6fr);
  }

  .composer-action {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: minmax(14rem, 0.4fr) 1fr;
    align-items: center;
    gap: 1.2rem;
    border-top: 1px solid var(--line-light);
    border-left: 0;
  }

  .composer-action .primary-action {
    grid-row: 1 / span 2;
  }

  .composer-action .use-policy-ack,
  .composer-action p {
    grid-column: 2;
    margin: 0;
  }

  /* The route reflows vertically: source ↓ gate ↓ lanes ↓ break ↓ validate. */
  .route-map {
    display: block;
  }

  .route-stage {
    padding: 1.4rem 0;
  }

  .stage-head {
    margin-bottom: 1rem;
  }

  .route-link {
    height: 2.2rem;
  }

  .link-line {
    top: 0;
    bottom: 0;
    left: 50%;
    right: auto;
    width: 2px;
    height: auto;
    transform: scaleY(0);
    transform-origin: top;
    animation-name: route-draw-y;
  }

  .route-fan {
    height: 2.2rem;
  }

  .route-fan svg {
    display: none;
  }

  .route-fan::after {
    content: "";
    display: block;
    width: 2px;
    height: 100%;
    margin: 0 auto;
    background: var(--paper-muted);
    transform: scaleY(0);
    transform-origin: top;
    animation: route-draw-y var(--duration-base) var(--ease-out) 180ms forwards;
  }

  .lane {
    grid-template-columns: 3.2rem minmax(0, 1fr);
    min-height: 0;
    padding: 0.3rem 0;
  }

  .lane-track {
    height: auto;
  }

  .lane-rule {
    display: none;
  }

  .lane-track::before {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    left: calc(0.375rem - 1px);
    width: 2px;
    background: var(--paper);
    transform: scaleY(0);
    transform-origin: top;
    animation: route-draw-y var(--duration-base) var(--ease-out) var(--lane-delay) forwards;
  }

  .lane-node,
  .lane-node:nth-of-type(2),
  .lane-node:nth-of-type(3),
  .lane-node:nth-of-type(4) {
    position: relative;
    top: auto;
    bottom: auto;
    left: auto;
    width: auto;
    padding: 0.42rem 0 0.42rem 1.5rem;
    transform: none;
  }

  .node-mark {
    top: 0.55rem;
    left: 0;
    width: 0.75rem;
    height: 0.75rem;
    transform: none;
  }

  .node-label {
    position: static;
    max-width: none;
    text-align: left;
    transform: none;
  }

  .route-break {
    padding: 1.2rem 0 1.4rem;
  }

  .break-rule {
    top: 0.6rem;
    bottom: auto;
    left: 0;
    width: auto;
    height: 0;
    border-left: 0;
    border-top: 2px dashed var(--paper-dim);
    transform: none;
  }

  .break-label {
    padding: 0.8rem 0 0;
    background: none;
    writing-mode: horizontal-tb;
  }

  .validate-tile {
    flex-direction: row;
    gap: 1.1rem;
    padding: 1.1rem 1.2rem;
    text-align: left;
  }

  .validate-tile svg {
    width: 2.6rem;
    flex: 0 0 auto;
  }

  .validate-eyebrow {
    display: none;
  }

  .validate-tile strong,
  .validate-tile span {
    display: block;
    margin: 0;
  }
}

@media (max-width: 767px) {
  .signal-masthead {
    display: block;
    min-height: 0;
  }

  .brand-block {
    width: 100%;
    min-height: 5.75rem;
    padding: 0.8rem 1rem;
    font-size: 3.15rem;
  }

  .brand-block::after {
    right: -2rem;
  }

  .masthead-copy {
    padding: 1rem 1rem 0.65rem;
  }

  .masthead-kicker {
    margin-bottom: 0.3rem;
    font-size: 0.75rem;
  }

  .masthead-copy h1 {
    font-size: clamp(2.75rem, 13vw, 3.65rem);
  }

  .masthead-summary {
    margin-top: 0.5rem;
    font-size: 0.84rem;
    line-height: 1.35;
  }

  .masthead-disclosure {
    padding: 0 1rem 0.8rem;
    font-size: 0.72rem;
    white-space: normal;
  }

  .signal-nav {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    padding: 0;
    border-top: 1px solid var(--line-dark);
    min-height: 0;
  }

  .nav-tab {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 0;
    min-height: 2.55rem;
    padding: 0.55rem 0.3rem;
    font-size: 0.72rem;
    line-height: 1.1;
    text-align: center;
  }

  .nav-tab.active {
    display: inline-flex;
    margin: 0;
    min-height: 2.55rem;
    padding: 0.55rem 0.3rem;
  }

  .settings-button {
    grid-column: 1 / -1;
    justify-content: center;
    margin: 0;
    min-height: 2.35rem;
    padding: 0.45rem 1rem;
    border-top: 1px solid var(--line-dark);
  }

  .decision-section {
    padding: 0;
  }

  .decision-composer {
    display: block;
  }

  .question-field {
    padding: 1rem;
    border-right: 0;
  }

  .question-field textarea {
    min-height: 4rem;
    font-size: 2.05rem !important;
  }

  .decision-details-grid {
    grid-template-columns: 1fr;
  }

  .decision-details-grid textarea {
    font-size: 0.78rem !important;
  }

  .source-material {
    padding: 0.75rem 1rem;
    border-right: 0;
    border-left: 0;
  }

  .source-dropzone {
    min-height: 5.4rem;
    padding: 0.8rem;
  }

  .composer-action {
    display: block;
    padding: 0.75rem 1rem 1rem;
  }

  .composer-action .use-policy-ack,
  .composer-action p {
    margin-top: 0.8rem;
  }

  .primary-action {
    width: 100%;
    min-height: 3.5rem;
  }

  .section-heading {
    display: block;
    margin-bottom: 2rem;
  }

  .section-heading h2 {
    margin-top: 0.75rem;
    font-size: 3rem;
  }

  .section-heading > span {
    display: block;
    margin-top: 1rem;
  }

  .route-stage {
    padding: 1.2rem 0;
  }

  .source-tile,
  .validate-tile {
    min-height: 8.5rem;
  }

  .lane {
    grid-template-columns: 2.9rem minmax(0, 1fr);
  }

  .node-label {
    font-size: 0.72rem;
  }

  .route-legend {
    padding: 0.8rem 0.4rem;
    letter-spacing: 0.05em;
  }

  .run-list button {
    grid-template-columns: 2.5rem minmax(0, 1fr) 1.5rem;
    min-height: 6.3rem;
    gap: 0.65rem;
  }

  .run-status {
    display: none;
  }

  .run-main strong {
    white-space: normal;
  }

  .inline-state {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }

  .template-list {
    display: block;
  }

  .template-list button {
    grid-template-columns: 2rem minmax(0, 1fr);
    width: 100%;
    min-height: 7rem;
    border-right: 0;
  }

  .template-use {
    display: none;
  }

  .signal-footer {
    grid-template-columns: 1fr;
  }

  .footer-disclosure {
    align-items: flex-start;
    text-align: left;
  }
}

/* Quick Starts & Readiness Badge Styles */
.composer-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.6rem;
}

.readiness-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.25rem 0.65rem;
  border: 1px solid var(--line-dark);
  background: var(--ink-deep);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  transition: all var(--duration-quick) var(--ease-quick);
}

.readiness-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--paper-dim);
}

.readiness-badge.level-high {
  border-color: var(--success);
  color: var(--paper-strong);
}
.readiness-badge.level-high .readiness-dot {
  background: var(--success);
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.6);
  animation: readinessPulse 2s infinite ease-in-out;
}

.readiness-badge.level-medium {
  border-color: var(--signal);
  color: var(--paper-strong);
}
.readiness-badge.level-medium .readiness-dot {
  background: var(--signal);
  box-shadow: 0 0 8px rgba(56, 189, 248, 0.6);
  animation: readinessPulse 2s infinite ease-in-out;
}

@keyframes readinessPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.65; transform: scale(1.18); }
}

.readiness-badge.level-low {
  border-color: var(--line-dark);
  color: var(--paper-muted);
}

.archetype-chips-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.9rem;
}

.chips-label {
  color: var(--ink-muted);
  font-family: var(--font-display);
  font-size: 0.76rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.archetype-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.7rem;
  border: 1px solid var(--line-dark);
  background: var(--ink-soft);
  color: var(--paper);
  font-family: var(--font-sans);
  font-size: 0.78rem;
  font-weight: 550;
  cursor: pointer;
  transition: all var(--duration-quick) var(--ease-quick);
}

.archetype-chip:hover {
  border-color: var(--signal);
  background: var(--signal-tint);
  color: var(--paper-strong);
  transform: translateY(-1px);
}

.chip-icon {
  color: var(--attention);
  font-family: var(--font-display);
  font-size: 0.72rem;
  letter-spacing: 0.04em;
}

@media (prefers-reduced-motion: reduce) {
  :global(html) {
    scroll-behavior: auto;
  }

  .link-line,
  .lane-rule,
  .lane-track::before,
  .route-fan::after,
  .run-skeleton,
  .template-skeleton {
    animation: none;
    transform: none;
  }

  .route-fan path {
    animation: none;
    stroke-dashoffset: 0;
  }

  .node-mark,
  .node-label {
    animation: none;
    opacity: 1;
  }
}
</style>



