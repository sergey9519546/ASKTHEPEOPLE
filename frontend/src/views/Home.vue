<template>
  <div class="public-signal-home">
    <a class="skip-link" href="#decision">Skip to the decision</a>

    <header class="signal-masthead">
      <button
        class="brand-block"
        type="button"
        aria-label="ASKTHEPEOPLE, synthetic decision explorer. Go to the decision composer."
        @click="scrollToSection('decision')"
      >
        <span class="brand-wordmark">ASKTHEPEOPLE</span>
        <span class="brand-descriptor">Synthetic Decision Explorer</span>
      </button>

      <h1 class="masthead-title">
        Write one decision. Inspect the paths it could take.
      </h1>

      <div class="masthead-tools">
        <p class="masthead-disclosure" aria-label="Important methodology disclosure">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="9"></circle>
            <path d="M12 10v6M12 7.4v.2"></path>
          </svg>
          <span><strong>0 human respondents</strong> · Not a forecast</span>
        </p>
        <button
          class="settings-button"
          type="button"
          aria-label="Open model settings"
          @click="openSettings()"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 7h10M18 7h2M4 17h2M10 17h10M14 4v6M6 14v6"></path>
          </svg>
          <span>Settings</span>
        </button>
      </div>
    </header>

    <main id="main-content">
      <section id="decision" class="decision-section" aria-labelledby="decision-heading">
        <h2 id="decision-heading" class="section-title">The decision</h2>

        <div class="decision-composer">
          <div class="question-field">
            <div class="composer-header-row">
              <label for="decision-question">The decision</label>
              <div class="readiness-badge" :class="sourceReadiness.levelClass">
                <span class="readiness-dot" aria-hidden="true"></span>
                <span class="readiness-text">{{ sourceReadiness.label }}</span>
              </div>
            </div>

            <div class="preset-row" role="group" aria-labelledby="preset-label">
              <span id="preset-label" class="preset-label">Quick starts</span>
              <button
                v-for="preset in decisionPresets"
                :key="preset.id"
                type="button"
                class="preset-button"
                :title="preset.description"
                @click="applyPreset(preset)"
              >
                {{ preset.label }}
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
            <p v-if="questionError" id="decision-error" class="field-error" role="alert">
              {{ questionError }}
            </p>
          </div>
        </div>

        <details class="disclosure context-disclosure">
          <summary class="disclosure-summary">
            <span class="disclosure-head">
              <span class="disclosure-title">Optional context</span>
              <span class="disclosure-hint">
                A workspace name and anything you already know about the setting.
              </span>
            </span>
          </summary>
          <div class="disclosure-body">
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
          </div>
        </details>

        <details
          class="disclosure source-disclosure"
          :open="files.length > 0 || urlInput.trim().length > 0"
        >
          <summary class="disclosure-summary">
            <span class="disclosure-head">
              <span class="disclosure-title">Add starting material (optional)</span>
              <span class="disclosure-hint">
                Sources ground the scenarios; they do not validate an outcome.
              </span>
              <span v-if="files.length" class="disclosure-count">
                {{ files.length }} {{ files.length === 1 ? "source" : "sources" }} added
              </span>
            </span>
          </summary>
          <div class="disclosure-body">
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
                accept=".pdf,.md,.txt,.docx,.xlsx"
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
                  <strong>{{ files.length ? "Add more source material" : "Source material (optional)" }}</strong>
                  <span>PDF, Markdown, TXT, DOCX, or XLSX · 10 files / 50 MB maximum</span>
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
                      class="file-remove u-target"
                      type="button"
                      :aria-label="`Remove ${file.name}`"
                      @click.stop="removeFile(index)"
                    >
                      Remove
                    </button>
                  </li>
                </ul>
              </div>

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
          </div>
        </details>

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
              I understand this is generated exploration, not human evidence
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
        </div>

        <p v-if="fileError" class="source-error" role="alert">{{ fileError }}</p>
      </section>

      <section id="method" class="method-section" aria-labelledby="method-heading">
        <h2 id="method-heading" class="section-title">How a run flows</h2>

        <ol class="flow-strip">
          <li class="flow-stage">
            <span class="flow-index">01</span>
            <span class="flow-name">Source</span>
            <span class="flow-detail">Optional starting material grounds the scenarios.</span>
          </li>
          <li class="flow-stage">
            <span class="flow-index">02</span>
            <span class="flow-name">Assumptions</span>
            <span class="flow-detail">Reviewed assumptions are the only place branches form.</span>
          </li>
          <li class="flow-stage">
            <span class="flow-index">03</span>
            <span class="flow-name">Possible paths</span>
            <span class="flow-detail">Equal-weight paths carry generated actions in sequence.</span>
          </li>
          <li id="validate" class="flow-stage">
            <span class="flow-index">04</span>
            <span class="flow-name">Validate with people</span>
            <span class="flow-detail">Validation with people happens outside the generated run.</span>
          </li>
        </ol>

        <p class="flow-note">
          All paths carry equal weight — spacing shows sequence only, not time or likelihood.
        </p>
      </section>

      <div class="work-lists">
        <section id="scenarios" class="runs-section" aria-labelledby="runs-heading">
          <h2 id="runs-heading" class="section-title">Recent scenario runs</h2>
          <p class="section-note">Continue from the latest saved workspace.</p>

          <p class="visually-hidden" role="status">
            <template v-if="historyLoading">Loading recent scenario runs.</template>
            <template v-else-if="!historyError">
              Loaded {{ simulationHistory.length }} recent scenario runs.
            </template>
          </p>

          <div class="list-region" :aria-busy="historyLoading ? 'true' : 'false'">
            <div v-if="historyLoading" class="run-skeletons" aria-hidden="true">
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
                <span>Add a decision and starting material above to begin.</span>
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
          </div>
        </section>

        <section id="templates" class="templates-section" aria-labelledby="templates-heading">
          <h2 id="templates-heading" class="section-title">Question starters</h2>
          <p class="section-note">
            Use a prompt structure, then rewrite it for your own decision.
          </p>

          <p class="visually-hidden" role="status">
            <template v-if="templatesLoading">Loading question starters.</template>
            <template v-else-if="!templatesError">
              Loaded {{ templates.length }} question starters.
            </template>
          </p>

          <div class="list-region" :aria-busy="templatesLoading ? 'true' : 'false'">
            <div v-if="templatesLoading" class="template-skeletons" aria-hidden="true">
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

            <div v-else-if="templates.length === 0" class="inline-state empty-state dark-state">
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
                <span class="template-copy u-prose">
                  <strong>{{ template.name }}</strong>
                  <span>{{ template.description }}</span>
                </span>
                <span class="template-use">Use this frame</span>
              </button>
            </div>
          </div>
        </section>
      </div>

      <aside class="reference-band" aria-labelledby="grammar-heading">
        <h2 id="grammar-heading" class="section-title">Route grammar</h2>
        <p class="section-note">Reference codes for the records this workspace writes.</p>

        <aside class="route-grammar-legend" aria-label="Route grammar — node codes used in this decision workspace">
          <strong class="grammar-label">Node codes</strong>
          <span class="grammar-items">
            <span class="grammar-item" title="Decision">D-01</span>
            <span class="grammar-item" title="Source material">SM-01</span>
            <span class="grammar-item" title="Starting condition">SC-01</span>
            <span class="grammar-item" title="Assumption">A-01</span>
            <span class="grammar-item" title="Critical uncertainty">U-01</span>
            <span class="grammar-item" title="Generated profile / decision lens">GP-01</span>
            <span class="grammar-item" title="Possible path">P-01</span>
            <span class="grammar-item" title="generated action">SA-01</span>
            <span class="grammar-item" title="Decision consideration">DC-01</span>
            <span class="grammar-item" title="Validation question">VQ-01</span>
            <span class="grammar-item" title="Related run record">RR-01</span>
          </span>
          <span class="grammar-note">Sequence only. No probability or time.</span>
        </aside>
      </aside>
    </main>

    <footer class="signal-footer">
      <div class="footer-statement">
        <strong>ASKTHEPEOPLE</strong>
        <span>Synthetic Decision Explorer — generated scenario exploration before real-world research.</span>
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
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { getTemplates } from "../api/graph";
import { getSimulationHistory } from "../api/simulation";
import { fetchSourceUrls } from "../api/sources.js";
import SettingsModal from "../components/SettingsModal.vue";
import {
  closeSettings,
  openSettings,
  settingsOpen,
} from "../composables/useCommandPalette.js";
import { useWorkspaceState } from "../composables/useWorkspaceState.js";
import { setPendingUpload } from "../store/pendingUpload.js";
import { savedRunDestination } from "../utils/workflow.js";

const router = useRouter();
const { setContext } = useWorkspaceState();
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
  // Consent is an explicit act: a quick-start preset fills the form but must
  // never silently pre-accept the generated-exploration acknowledgment.
};

const sourceReadiness = computed(() => {
  // Neutral prompt-detail signal: describes what the workspace contains, never
  // a quality/precision claim (prompt length and file count cannot imply it).
  const hasContext = formData.value.additionalContext.trim().length > 0;
  const hasSources = files.value.length > 0 || urlInput.value.trim().length > 0;

  if (hasSources && hasContext) {
    return { label: "Decision + context + sources", levelClass: "level-high" };
  }
  if (hasSources) {
    return { label: "Decision + sources", levelClass: "level-medium" };
  }
  if (hasContext) {
    return { label: "Decision + context", levelClass: "level-medium" };
  }
  return { label: "Decision only", levelClass: "level-low" };
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
  const acceptedExtensions = ["pdf", "md", "txt", "docx", "xlsx"];
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
      // Create a generated File object that matches what file upload produces
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
  setContext({
    projectName: formData.value.projectName.trim(),
    simulationRequirement: question,
    additionalContext: formData.value.additionalContext.trim(),
  });
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
// /api/simulation/history. Phrased as provenance of a generated run — a branch
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
/* Decision-first Home.
   The view renders inside one panel of the desktop shell and that panel is
   roughly viewport-height, so the composer sits above the fold and everything
   secondary is either folded behind a native disclosure or below the fold.

   Palette discipline held throughout: signal red is a wayfinding edge, the
   primary action fill, and an active state - never body text on cream, and
   never a fill behind attention yellow. Attention yellow is the focus ring and
   small marks only. The display face is a single-weight condensed all-caps
   poster face, so it is used for nouns only (wordmark, section headings,
   stage numerals and names) and never below 1.25rem, and never for a label a
   user has to read in order to decide something. */

.public-signal-home {
  position: relative;
  min-height: 100%;
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

/* ---------------------------------------------------------------- header -- */

.signal-masthead {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.brand-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 0.1rem;
  min-height: var(--control-h-md);
  padding: 0.3rem 0.75rem;
  border: 0;
  border-left: var(--edge-wayfinding) solid var(--signal);
  border-radius: 0;
  background: transparent;
  color: var(--paper);
  text-align: left;
}

.brand-block:hover {
  border-color: var(--signal);
  background: var(--ink-raised);
  color: var(--paper);
}

/* The wordmark is a noun, so it keeps the display face - at poster size, where
   a single-weight condensed face still has the stroke contrast to be read. */
.brand-wordmark {
  font-family: var(--font-display);
  font-size: 1.5rem;
  line-height: var(--leading-display);
  letter-spacing: 0.02em;
}

.brand-descriptor {
  color: var(--paper-muted);
  font-size: 0.66rem;
  font-weight: 600;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

/* Orientation, not a hero. This is a line a person reads in order to act, so it
   is set in the text face at body size; the view has no hero headline. */
.masthead-title {
  margin: 0;
  color: var(--paper);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  font-weight: 600;
  line-height: var(--leading-snug);
  text-wrap: balance;
}

.masthead-tools {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
}

.masthead-disclosure {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  padding: 0.3rem 0.6rem;
  border: 1px solid var(--line-dark);
  color: var(--paper-muted);
  font-size: 0.72rem;
  line-height: var(--leading-snug);
}

.masthead-disclosure strong {
  color: var(--attention);
  font-weight: 700;
}

.masthead-disclosure svg {
  width: 1rem;
  flex: none;
  fill: none;
  stroke: var(--paper-dim);
  stroke-linecap: round;
  stroke-width: 1.8;
}

.settings-button {
  min-height: var(--control-h-md);
  padding: 0.3rem 0.75rem;
  border: 1px solid var(--line-dark);
  background: transparent;
  color: var(--paper);
  font-size: 0.76rem;
  font-weight: 600;
  white-space: nowrap;
}

.settings-button svg {
  width: 1rem;
  flex: none;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 1.8;
}

/* --------------------------------------------------------- section titles -- */

.section-title {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1.6rem;
  line-height: var(--leading-display);
  letter-spacing: 0.01em;
}

.section-note {
  max-width: var(--measure-prose);
  margin: var(--space-1) 0 0;
  color: var(--ink-muted);
  font-size: 0.76rem;
  line-height: var(--leading-snug);
}

/* -------------------------------------------------------------- composer -- */

.decision-section {
  padding: var(--space-5);
  background: var(--paper);
  color: var(--ink);
  scroll-margin-top: 1rem;
}

.decision-section .section-title {
  margin-bottom: var(--space-3);
}

.decision-composer {
  border: 1px solid var(--line-light);
  border-top: var(--edge-wayfinding) solid var(--ink);
  background: var(--paper-strong);
}

.question-field {
  display: flex;
  flex-direction: column;
  padding: var(--space-4);
}

.composer-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

/* A form label is read in order to decide something, so it is text face. */
.question-field label {
  font-family: var(--font-sans);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

/* The badge states what the workspace holds, never how good it is. Prompt
   length and file count cannot imply a quality or precision claim, so the
   levels differ by rule weight and text colour only - no score, no escalation. */
.readiness-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0.2rem 0.55rem;
  border: 1px solid var(--line-light);
  background: var(--paper-transfer);
  color: var(--ink-muted);
  font-family: var(--font-sans);
  font-size: 0.72rem;
  font-weight: 600;
  white-space: nowrap;
}

.readiness-dot {
  width: 0.4rem;
  height: 0.4rem;
  background: var(--ink-muted);
}

.readiness-badge.level-medium,
.readiness-badge.level-high {
  border-color: var(--ink-muted);
  color: var(--ink);
}

.readiness-badge.level-medium .readiness-dot,
.readiness-badge.level-high .readiness-dot {
  background: var(--ink);
}

.preset-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.preset-label {
  color: var(--ink-muted);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.preset-button {
  min-height: var(--control-h-sm);
  padding: 0.15rem 0.6rem;
  border: 1px solid var(--line-light);
  border-radius: 0;
  background: var(--paper);
  color: var(--ink);
  font-size: 0.75rem;
  font-weight: 600;
  line-height: var(--leading-tight);
  text-align: left;
}

.preset-button:hover {
  border-color: var(--ink);
  background: var(--paper-transfer);
  color: var(--ink);
}

.question-field textarea {
  width: 100%;
  min-height: 7.5rem;
  padding: var(--space-3) 0 var(--space-2) !important;
  border: 0 !important;
  border-bottom: 2px solid var(--line-light) !important;
  background: transparent !important;
  color: var(--ink) !important;
  font-family: var(--font-sans) !important;
  font-size: clamp(1.05rem, 1.4vw, 1.3rem) !important;
  line-height: var(--leading-snug) !important;
  resize: vertical;
}

.question-field textarea::placeholder {
  color: var(--ink-muted);
  opacity: 1;
}

.question-field textarea:focus {
  border-bottom-color: var(--ink) !important;
}

.field-helper {
  margin: var(--space-2) 0 0;
  color: var(--ink-muted);
  font-size: 0.78rem;
  line-height: var(--leading-snug);
}

.field-error,
.source-error {
  margin: var(--space-2) 0 0;
  color: var(--error-text);
  font-size: 0.78rem;
  font-weight: 600;
  line-height: var(--leading-snug);
}

/* ------------------------------------------------------------ disclosures -- */

.disclosure {
  margin-top: var(--space-3);
  border: 1px solid var(--line-light);
  background: var(--paper-strong);
}

/* The summary stays a list-item so the native disclosure marker survives; the
   flex row lives on an inner span. Native <details> is what makes both
   disclosures operable with Enter and Space with no extra key handling. */
.disclosure-summary {
  min-height: var(--control-h-md);
  padding: var(--space-2) var(--space-3);
  color: var(--ink);
  cursor: pointer;
  list-style-position: inside;
}

.disclosure-summary::marker {
  color: var(--ink-muted);
}

.disclosure-summary:hover {
  background: var(--paper-transfer);
}

.disclosure[open] > .disclosure-summary {
  border-bottom: 1px solid var(--line-light);
}

.disclosure-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.15rem var(--space-3);
}

.disclosure-title {
  font-family: var(--font-sans);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.disclosure-hint {
  color: var(--ink-muted);
  font-size: 0.76rem;
  font-weight: 500;
  line-height: var(--leading-snug);
}

/* Added files stay countable with the disclosure closed, so a user never has
   to reopen it to find out whether material is already attached. */
.disclosure-count {
  margin-left: auto;
  padding: 0.05rem 0.45rem;
  border: 1px solid var(--ink-muted);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 0.7rem;
  font-weight: 700;
  white-space: nowrap;
}

.disclosure-body {
  padding: var(--space-3);
}

.decision-details-grid {
  display: grid;
  grid-template-columns: minmax(10rem, 0.45fr) minmax(0, 1fr);
  gap: var(--space-3);
}

.decision-details-grid label {
  display: grid;
  gap: 0.3rem;
  margin: 0;
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 0.7rem;
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
  min-height: var(--control-h-lg);
  padding: 0.5rem 0.6rem !important;
  border: 1px solid var(--line-light) !important;
  border-radius: 0;
  background: var(--paper) !important;
  color: var(--ink) !important;
  font-family: var(--font-sans) !important;
  font-size: 0.78rem !important;
  font-weight: 500;
  line-height: var(--leading-snug);
}

.decision-details-grid textarea {
  min-height: 4rem;
}

/* ---------------------------------------------------------- source upload -- */

.source-material {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: var(--space-3);
}

.source-dropzone {
  width: 100%;
  min-width: 0;
  min-height: 5.5rem;
  align-items: center;
  justify-content: flex-start;
  gap: var(--space-4);
  padding: var(--space-3);
  border: 2px dashed var(--ink-muted);
  border-radius: 0;
  background: var(--paper);
  color: var(--ink);
  text-align: left;
  box-shadow: none;
}

.source-dropzone:hover,
.source-dropzone:focus-visible {
  border-color: var(--ink);
  background: var(--paper-transfer);
  color: var(--ink);
}

.source-material.dragging .source-dropzone {
  border-color: var(--ink);
  background: var(--paper-transfer);
  box-shadow: inset var(--edge-wayfinding) 0 0 0 var(--ink);
}

.source-icon {
  width: 2rem;
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
  font-size: 0.9rem;
}

.source-dropzone > div > span {
  margin-top: 0.15rem;
  color: var(--ink-muted);
  font-size: 0.74rem;
  line-height: var(--leading-snug);
}

.source-files {
  min-width: 0;
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--line-light);
  background: var(--paper);
}

.source-files-heading {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--space-1);
  font-size: 0.76rem;
  font-weight: 700;
}

.source-files-heading .add-more {
  color: var(--ink-muted);
  font-weight: 500;
}

.source-files ul {
  display: grid;
  gap: 0.2rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.source-files li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding-top: 0.2rem;
  border-top: 1px solid var(--line-light);
}

.source-files .file-name {
  overflow: hidden;
  color: var(--ink);
  font-size: 0.74rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-remove {
  min-height: var(--control-h-sm);
  flex: none;
  padding: 0 0.4rem;
  border: 1px solid transparent;
  border-radius: 0;
  background: transparent;
  color: var(--ink-muted);
  font-size: 0.7rem;
  text-decoration: underline;
}

.file-remove:hover {
  border-color: var(--ink-muted);
  background: transparent;
  color: var(--ink);
}

.url-ingestion {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: var(--space-3);
  border: 1px solid var(--line-light);
  background: var(--paper);
}

.url-ingestion label {
  color: var(--ink);
  font-size: 0.76rem;
  font-weight: 600;
}

.url-ingestion textarea {
  min-height: 4rem;
  padding: var(--space-2);
  border: 1px solid var(--line-light);
  border-radius: 0;
  background: var(--paper-strong);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 0.76rem;
  line-height: var(--leading-snug);
  resize: vertical;
}

.url-ingestion textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.fetch-urls-button {
  align-self: flex-start;
  min-height: var(--control-h-md);
  padding: 0 var(--space-4);
  border: 1px solid var(--ink-muted);
  border-radius: 0;
  background: var(--paper-strong);
  color: var(--ink);
  font-size: 0.76rem;
  font-weight: 600;
}

.fetch-urls-button:hover:not(:disabled) {
  border-color: var(--ink);
  background: var(--paper-transfer);
  color: var(--ink);
}

.url-error {
  margin: 0;
  padding: var(--space-1) var(--space-2);
  border-left: var(--edge-wayfinding) solid var(--error);
  color: var(--error-text);
  font-size: 0.72rem;
  line-height: var(--leading-snug);
}

/* ------------------------------------------------------- the one action -- */

.composer-action {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--line-light);
}

.primary-action {
  align-self: flex-start;
  min-height: var(--control-h-lg);
  padding: 0 var(--space-5);
  border: 1px solid var(--signal-deep);
  border-radius: 0;
  background: var(--signal);
  color: var(--ink);
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.primary-action:hover:not(:disabled) {
  border-color: var(--ink);
  background: var(--signal-strong);
  color: var(--ink);
}

.primary-action svg,
.run-list svg {
  width: 1.15rem;
  fill: none;
  stroke: currentColor;
  stroke-linecap: square;
  stroke-width: 2;
}

/* The consent checkbox is an explicit act. Nothing else in the view can set it:
   a quick-start preset fills the form and leaves this untouched. */
.use-policy-ack {
  display: grid;
  grid-template-columns: var(--target-min) minmax(0, 1fr);
  gap: var(--space-3);
  align-items: start;
  min-height: var(--control-h-md);
  max-width: var(--measure-tight);
  color: var(--ink);
  font-size: 0.78rem;
  font-weight: 600;
  line-height: var(--leading-snug);
  cursor: pointer;
}

.use-policy-ack input {
  width: 1.05rem;
  height: 1.05rem;
  margin: 0.15rem 0 0;
  border: 1px solid var(--ink);
  border-radius: 0;
  accent-color: var(--ink);
}

.submission-requirements {
  max-width: var(--measure-prose);
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border-left: var(--edge-wayfinding) solid var(--ink);
  background: var(--paper-transfer);
  color: var(--error-text);
  font-size: 0.76rem;
  font-weight: 600;
  line-height: var(--leading-snug);
}

/* ----------------------------------------------------------- flow strip -- */

/* Replaces the animated route diagram. The four stages are the same four
   statements it carried, stated once, statically: the fan is a fact about
   weight, not a thing to animate, and a scroll-triggered draw-in cost roughly a
   thousand lines of CSS to say nothing a list cannot. */
.method-section {
  padding: var(--space-5);
  border-top: 1px solid var(--line-dark);
  background:
    linear-gradient(rgba(242, 235, 221, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(242, 235, 221, 0.025) 1px, transparent 1px),
    var(--ink);
  background-size: 1.5rem 1.5rem;
  scroll-margin-top: 1rem;
}

.method-section .section-title {
  color: var(--paper);
}

.flow-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  margin: var(--space-3) 0 0;
  padding: 0;
  border: 1px solid var(--line-dark);
  background: var(--line-dark);
  list-style: none;
}

.flow-stage {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  padding: var(--space-3);
  background: var(--ink);
}

/* Position and stage name are nouns: display face, at or above 1.25rem, which is
   where a single-weight condensed all-caps face is still legible. */
.flow-index {
  color: var(--attention);
  font-family: var(--font-display);
  font-size: 1.25rem;
  line-height: var(--leading-display);
}

.flow-name {
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 1.25rem;
  line-height: var(--leading-display);
}

.flow-detail {
  margin-top: 0.15rem;
  color: var(--paper-muted);
  font-size: 0.78rem;
  line-height: var(--leading-snug);
  text-wrap: pretty;
}

.flow-note {
  max-width: var(--measure-prose);
  margin: var(--space-3) 0 0;
  color: var(--paper-muted);
  font-size: 0.76rem;
  line-height: var(--leading-snug);
}

/* ------------------------------------------------------------ the lists -- */

.work-lists {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(21rem, 1fr));
  align-items: start;
  border-top: 1px solid var(--line-dark);
}

.runs-section {
  padding: var(--space-5);
  background: var(--paper);
  color: var(--ink);
}

.templates-section {
  padding: var(--space-5);
  border-left: 1px solid var(--line-dark);
  background: var(--ink);
  color: var(--paper);
}

.templates-section .section-note {
  color: var(--paper-muted);
}

/* The region carries the busy state; the skeleton inside it is decorative and
   aria-hidden, and completion is announced by the visually-hidden live region.
   No focusable control lives inside a skeleton. */
.list-region {
  margin-top: var(--space-3);
}

.run-list {
  margin: 0;
  padding: 0;
  border-top: 2px solid var(--ink);
  list-style: none;
}

.run-list li {
  border-bottom: 1px solid var(--line-light);
}

.run-list button {
  display: grid;
  grid-template-columns: 2.25rem minmax(0, 1fr) auto 1.25rem;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  min-height: var(--control-h-lg);
  padding: var(--space-3) var(--space-2);
  border: 1px solid transparent;
  border-radius: 0;
  background: transparent;
  color: var(--ink);
  text-align: left;
}

.run-list button:hover {
  border-color: var(--line-light);
  background: var(--paper-strong);
  color: var(--ink);
}

.run-index,
.template-number,
.state-index {
  font-family: var(--font-sans);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.run-index,
.state-index {
  color: var(--ink-muted);
}

.template-number {
  color: var(--paper-dim);
}

.run-main {
  min-width: 0;
}

.run-main strong,
.run-main span {
  display: block;
}

/* A run title is long-form generated copy: text face at a readable measure and
   clamped to two lines, never a poster-sized display line. */
.run-main strong {
  display: -webkit-box;
  overflow: hidden;
  max-width: var(--measure-prose);
  font-family: var(--font-sans);
  font-size: 0.9rem;
  font-weight: 700;
  line-height: var(--leading-snug);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  text-overflow: ellipsis;
}

.run-main span {
  margin-top: 0.2rem;
  color: var(--ink-muted);
  font-size: 0.74rem;
  line-height: var(--leading-snug);
}

.run-status {
  color: var(--ink-muted);
  font-size: 0.74rem;
  font-weight: 600;
  white-space: nowrap;
}

/* `.run-main span` is display:block, so the branch marker is nested inside the
   date line and set back to inline to sit beside it rather than push the row
   taller. */
.run-branch {
  display: inline !important;
  margin-left: var(--space-2);
  padding: 0.05rem 0.35rem;
  border: 1px solid var(--line-light);
  color: var(--ink-muted);
  font-family: var(--font-sans);
  font-size: 0.66rem;
  font-weight: 700;
  white-space: nowrap;
}

.run-skeletons,
.template-skeletons {
  display: grid;
  gap: 1px;
  background: var(--line-light);
}

.template-skeletons {
  background: var(--line-dark);
}

.run-skeleton,
.template-skeleton {
  min-height: 3.75rem;
  background:
    linear-gradient(90deg, transparent, rgba(242, 235, 221, 0.55), transparent),
    var(--paper-strong);
  background-size: 50% 100%;
  animation: skeleton-pass 1.4s ease-in-out infinite;
}

.template-skeleton {
  background:
    linear-gradient(90deg, transparent, rgba(242, 235, 221, 0.14), transparent),
    var(--ink-soft);
  background-size: 50% 100%;
}

@keyframes skeleton-pass {
  from {
    background-position: -100% 0;
  }
  to {
    background-position: 200% 0;
  }
}

.inline-state {
  display: grid;
  grid-template-columns: 2.25rem minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  min-height: 5.5rem;
  padding: var(--space-3);
  border-top: 2px solid var(--ink);
  border-bottom: 1px solid var(--line-light);
}

/* The bare variant carries no index cell, so its own lines take the full row
   instead of landing in a column reserved for one. */
.inline-state > strong,
.inline-state > span:not(.state-index) {
  grid-column: 1 / -1;
}

.inline-state > div strong,
.inline-state > div span,
.inline-state > strong,
.inline-state > span {
  display: block;
}

.inline-state span {
  margin-top: 0.2rem;
  color: var(--ink-muted);
  font-size: 0.8rem;
  line-height: var(--leading-snug);
}

.inline-state button {
  border-color: var(--ink);
  background: var(--ink);
  color: var(--paper);
  font-size: 0.76rem;
}

.inline-state button:hover {
  border-color: var(--signal);
  background: var(--signal);
  color: var(--ink);
}

.error-state {
  border-top-color: var(--error);
}

.template-list {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  border-top: 1px solid var(--line-dark);
}

.template-list button {
  display: grid;
  grid-template-columns: 2.25rem minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  min-height: var(--control-h-lg);
  padding: var(--space-3) var(--space-2);
  border: 0;
  border-bottom: 1px solid var(--line-dark);
  border-radius: 0;
  background: transparent;
  color: var(--paper);
  text-align: left;
}

.template-list button:hover {
  border-bottom-color: var(--signal);
  background: var(--signal-faint);
  color: var(--paper);
}

.template-copy {
  min-width: 0;
}

.template-copy strong,
.template-copy span {
  display: block;
}

.template-copy strong {
  font-family: var(--font-sans);
  font-size: 0.86rem;
  font-weight: 700;
  line-height: var(--leading-snug);
}

/* Starter descriptions are long-form copy: text face, relaxed leading, and a
   readable measure. `.u-prose` carries the measure. */
.template-copy span {
  margin-top: 0.1rem;
  color: var(--paper-muted);
  font-size: 0.76rem;
  line-height: var(--leading-relaxed);
  text-wrap: pretty;
}

.template-use {
  color: var(--signal);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
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

/* ---------------------------------------------------------- reference -- */

.reference-band {
  padding: var(--space-5);
  border-top: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.reference-band .section-title {
  color: var(--paper);
}

.reference-band .section-note {
  color: var(--paper-dim);
}

/* Route grammar is reference material, so it is quiet, last, and off the flow
   path. The codes stay legible as tokens on a light chip. */
.route-grammar-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1) var(--space-3);
  margin-top: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--line-dark);
  background: var(--ink-soft);
  color: var(--paper-muted);
  font-family: var(--font-sans);
  font-size: 0.72rem;
  line-height: var(--leading-snug);
}

/* A legend label is read to look something up, so it is text face. */
.grammar-label {
  font-family: var(--font-sans);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}

.grammar-items {
  display: flex;
  flex-wrap: wrap;
  gap: 0.15rem 0.3rem;
}

.grammar-item {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
  padding: 0.1rem 0.35rem;
  border: 1px solid var(--line-dark);
  background: var(--paper);
  color: var(--ink-muted);
  font-family: var(--font-sans);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.grammar-note {
  margin-left: auto;
  color: var(--paper-muted);
  font-size: 0.7rem;
  font-style: italic;
  white-space: nowrap;
}

/* ------------------------------------------------------------- footer -- */

.signal-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-5);
  border-top: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.footer-statement,
.footer-disclosure {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  max-width: var(--measure-prose);
  color: var(--paper-muted);
  font-size: 0.74rem;
  line-height: var(--leading-snug);
}

.footer-statement strong {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 1.3rem;
  letter-spacing: 0.03em;
}

.footer-disclosure {
  text-align: right;
}

/* ------------------------------------------------------------ narrow -- */

@media (max-width: 900px) {
  .signal-masthead {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
  }

  .masthead-tools {
    justify-content: space-between;
  }

  .flow-strip {
    grid-template-columns: minmax(0, 1fr);
  }

  .templates-section {
    border-top: 1px solid var(--line-dark);
    border-left: 0;
  }

  .decision-details-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .reference-band,
  .decision-section,
  .runs-section,
  .templates-section,
  .method-section,
  .signal-footer {
    padding: var(--space-4);
  }
}

@media (max-width: 560px) {
  .masthead-disclosure {
    white-space: normal;
  }

  .composer-action .primary-action {
    width: 100%;
  }

  .run-list button,
  .template-list button {
    grid-template-columns: 2rem minmax(0, 1fr);
  }

  .run-list button > .run-status,
  .run-list button > svg {
    display: none;
  }

  .template-list button > .template-use {
    grid-column: 2;
  }

  .grammar-note {
    margin-left: 0;
  }
}

@media (prefers-contrast: more) {
  .grammar-item,
  .disclosure-count,
  .readiness-badge,
  .preset-button,
  .source-files,
  .url-ingestion {
    border-color: var(--line-strong);
  }
}

@media (prefers-reduced-motion: reduce) {
  :global(html) {
    scroll-behavior: auto;
  }

  .run-skeleton,
  .template-skeleton {
    animation: none;
  }
}
</style>