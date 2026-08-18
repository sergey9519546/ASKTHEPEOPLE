<template>
  <div class="settings-overlay" @click.self="close">
    <section
      ref="settingsSheet"
      class="settings-sheet"
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-title"
      :aria-busy="loading"
    >
      <header class="settings-header">
        <div class="settings-index" aria-hidden="true">SET</div>
        <div>
          <p>Workspace controls</p>
          <h2 id="settings-title">Settings</h2>
        </div>
        <button
          ref="closeButton"
          class="close-button"
          type="button"
          aria-label="Close settings"
          @click="close"
        >
          Close
        </button>
      </header>

      <div class="settings-body">
        <section class="access-strip" aria-labelledby="access-title">
          <div>
            <p class="section-number">01 / Access</p>
            <h3 id="access-title">Deployment access</h3>
            <p>
              {{
                hasAccessKey
                  ? "This browser tab has an access key. It is removed when the tab closes."
                  : "No access key is stored in this browser tab."
              }}
            </p>
          </div>
          <button
            v-if="hasAccessKey"
            class="secondary-action"
            type="button"
            @click="forgetAccessKey"
          >
            Forget access key
          </button>
        </section>

        <div v-if="loading" class="settings-state" role="status">
          <span class="state-marker" aria-hidden="true"></span>
          <div>
            <strong>Checking this deployment</strong>
            <span>Reading which controls are available here.</span>
          </div>
        </div>

        <div v-else-if="loadError" class="settings-state is-error" role="alert">
          <span class="state-marker" aria-hidden="true">!</span>
          <div>
            <strong>Settings could not be read</strong>
            <span>{{ loadError }}</span>
          </div>
          <button type="button" class="secondary-action" @click="loadSettings">
            Try again
          </button>
        </div>

        <template v-else-if="!runtimeSettingsEnabled">
          <section class="managed-panel" aria-labelledby="managed-title">
            <p class="section-number">02 / Model service</p>
            <h3 id="managed-title">Managed by this deployment</h3>
            <p>
              Model credentials and endpoints are set by the deployment owner.
              They cannot be viewed or changed from this browser.
            </p>

            <dl class="service-status">
              <div>
                <dt>Scenario model</dt>
                <dd :class="{ ready: configured.LLM_API_KEY_CONFIGURED }">
                  {{ configured.LLM_API_KEY_CONFIGURED ? "Configured" : "Not configured" }}
                </dd>
              </div>
              <div>
                <dt>Report model</dt>
                <dd :class="{ ready: configured.LLM_BOOST_API_KEY_CONFIGURED }">
                  {{
                    configured.LLM_BOOST_API_KEY_CONFIGURED
                      ? "Separate model configured"
                      : "Uses scenario model"
                  }}
                </dd>
              </div>
              <div>
                <dt>Source-map memory</dt>
                <dd :class="{ ready: configured.ZEP_API_KEY_CONFIGURED }">
                  {{ configured.ZEP_API_KEY_CONFIGURED ? "Configured" : "Not configured" }}
                </dd>
              </div>
              <div>
                <dt>Research search</dt>
                <dd :class="{ ready: configured.BRAVE_SEARCH_API_KEY_CONFIGURED }">
                  {{
                    configured.BRAVE_SEARCH_API_KEY_CONFIGURED
                      ? "Configured"
                      : "Not configured"
                  }}
                </dd>
              </div>
            </dl>

            <p class="managed-note">
              To change these values, update the deployment environment and restart the
              service. Runtime editing is intentionally off.
            </p>
          </section>
        </template>

        <template v-else>
          <section class="preset-section" aria-labelledby="provider-title">
            <div class="section-heading">
              <div>
                <p class="section-number">02 / Provider</p>
                <h3 id="provider-title">Choose a starting point</h3>
              </div>
              <p>Choose a provider, then review the details below before saving.</p>
            </div>
            <div class="preset-grid">
              <button
                v-for="preset in availablePresets"
                :key="preset.id"
                type="button"
                class="preset-button"
                :class="{ active: preset.id === activePresetId }"
                :aria-pressed="preset.id === activePresetId"
                @click="applyPreset(preset)"
              >
                <strong>{{ preset.name }}</strong>
                <span>{{ preset.sub }}</span>
              </button>
            </div>
            <div class="provider-policy">
              <strong>Operator-permitted endpoints</strong>
              <p v-if="allowedBaseUrls.length">
                Only the endpoints listed below can be saved or tested.
              </p>
              <p v-else>
                No endpoint is currently allowlisted. Ask the deployment
                operator to configure one before changing providers.
              </p>
              <ul v-if="allowedBaseUrls.length">
                <li v-for="url in allowedBaseUrls" :key="url">{{ url }}</li>
              </ul>
              <p>
                Local-service presets appear only when private endpoints are
                explicitly enabled. Every connection test requires a new API key.
              </p>
            </div>
          </section>

          <section class="model-section" aria-labelledby="model-title">
            <div class="section-heading">
              <div>
                <p class="section-number">03 / Models</p>
                <h3 id="model-title">Model connections</h3>
              </div>
              <p>New secrets replace existing ones. Stored secrets are never shown.</p>
            </div>

            <div class="model-grid">
              <fieldset class="model-card">
                <legend>Scenario model</legend>
                <p>Creates profiles and generated conversation actions.</p>
                <label>
                  <span>API key</span>
                  <span class="secret-field">
                    <input
                      v-model="form.LLM_API_KEY"
                      :type="showKeys.primary ? 'text' : 'password'"
                      maxlength="8192"
                      autocomplete="new-password"
                      placeholder="Enter a new key"
                    />
                    <button type="button" @click="showKeys.primary = !showKeys.primary">
                      {{ showKeys.primary ? "Hide" : "Show" }}
                    </button>
                  </span>
                </label>
                <label>
                  <span>API base URL</span>
                  <input
                    v-model="form.LLM_BASE_URL"
                    type="text"
                    maxlength="2048"
                    inputmode="url"
                    placeholder="https://provider.example/v1"
                  />
                </label>
                <label>
                  <span>Model name</span>
                  <input
                    v-model="form.LLM_MODEL_NAME"
                    type="text"
                    maxlength="256"
                    placeholder="Provider model identifier"
                  />
                </label>
              </fieldset>

              <fieldset class="model-card">
                <legend>Report model</legend>
                <p>Optional separate connection for reports; leave blank to use the scenario model.</p>
                <label>
                  <span>API key</span>
                  <span class="secret-field">
                    <input
                      v-model="form.LLM_BOOST_API_KEY"
                      :type="showKeys.boost ? 'text' : 'password'"
                      maxlength="8192"
                      autocomplete="new-password"
                      placeholder="Optional new key"
                    />
                    <button type="button" @click="showKeys.boost = !showKeys.boost">
                      {{ showKeys.boost ? "Hide" : "Show" }}
                    </button>
                  </span>
                </label>
                <label>
                  <span>API base URL</span>
                  <input
                    v-model="form.LLM_BOOST_BASE_URL"
                    type="text"
                    maxlength="2048"
                    inputmode="url"
                    placeholder="Optional separate endpoint"
                  />
                </label>
                <label>
                  <span>Model name</span>
                  <input
                    v-model="form.LLM_BOOST_MODEL_NAME"
                    type="text"
                    maxlength="256"
                    placeholder="Optional separate model"
                  />
                </label>
              </fieldset>
            </div>
          </section>

          <section class="support-section" aria-labelledby="support-title">
            <div class="section-heading">
              <div>
                <p class="section-number">04 / Supporting services</p>
                <h3 id="support-title">Memory and search</h3>
              </div>
              <p>Optional keys used for source-map memory and report research.</p>
            </div>
            <div class="support-grid">
              <label>
                <span>Source-map memory key</span>
                <span class="secret-field">
                  <input
                    v-model="form.ZEP_API_KEY"
                    :type="showKeys.zep ? 'text' : 'password'"
                    maxlength="8192"
                    autocomplete="new-password"
                    placeholder="Enter a new key"
                  />
                  <button type="button" @click="showKeys.zep = !showKeys.zep">
                    {{ showKeys.zep ? "Hide" : "Show" }}
                  </button>
                </span>
              </label>
              <label>
                <span>Research search key</span>
                <span class="secret-field">
                  <input
                    v-model="form.BRAVE_SEARCH_API_KEY"
                    :type="showKeys.brave ? 'text' : 'password'"
                    maxlength="8192"
                    autocomplete="new-password"
                    placeholder="Enter a new key"
                  />
                  <button type="button" @click="showKeys.brave = !showKeys.brave">
                    {{ showKeys.brave ? "Hide" : "Show" }}
                  </button>
                </span>
              </label>
            </div>
          </section>

          <section class="connection-section" aria-labelledby="check-title">
            <div>
              <p class="section-number">05 / Check</p>
              <h3 id="check-title">Test the scenario model</h3>
              <p>This makes one short request with the values currently entered above.</p>
            </div>
            <button
              type="button"
              class="secondary-action"
              :disabled="testing || !canTest"
              @click="runConnectionTest"
            >
              {{ testing ? "Testing…" : "Test connection" }}
            </button>
          </section>

          <p
            v-if="testResult"
            class="feedback"
            :class="testResult.success ? 'is-success' : 'is-error'"
            role="status"
          >
            {{ testResult.message }}
          </p>
        </template>

        <p v-if="saveError" class="feedback is-error" role="alert">{{ saveError }}</p>
      </div>

      <footer class="settings-footer">
        <span v-if="runtimeSettingsEnabled">
          Saving updates the running deployment and may affect new runs.
        </span>
        <span v-else>Nothing on this screen reveals stored credentials.</span>
        <div>
          <button type="button" class="secondary-action" @click="close">Close</button>
          <button
            v-if="runtimeSettingsEnabled"
            type="button"
            class="primary-action"
            :disabled="saving"
            @click="save"
          >
            {{ saving ? "Saving…" : "Save settings" }}
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { getSettings, testConnection, updateSettings } from "../api/settings";
import { clearAccessKey, getAccessKey } from "../composables/useAccessKey.js";

const emit = defineEmits(["close", "saved"]);

const settingsSheet = ref(null);
const closeButton = ref(null);
const loading = ref(true);
const loadError = ref("");
const saveError = ref("");
const testing = ref(false);
const saving = ref(false);
const testResult = ref(null);
const runtimeSettingsEnabled = ref(false);
const activePresetId = ref("");
const allowedBaseUrls = ref([]);
const allowPrivateEndpoints = ref(false);
const hasAccessKey = ref(Boolean(getAccessKey()));
const configured = ref({
  LLM_API_KEY_CONFIGURED: false,
  LLM_BOOST_API_KEY_CONFIGURED: false,
  ZEP_API_KEY_CONFIGURED: false,
  BRAVE_SEARCH_API_KEY_CONFIGURED: false,
});
const showKeys = ref({
  primary: false,
  boost: false,
  zep: false,
  brave: false,
});
const form = ref({
  LLM_API_KEY: "",
  LLM_BASE_URL: "",
  LLM_MODEL_NAME: "",
  ZEP_API_KEY: "",
  BRAVE_SEARCH_API_KEY: "",
  LLM_BOOST_API_KEY: "",
  LLM_BOOST_BASE_URL: "",
  LLM_BOOST_MODEL_NAME: "",
});

const presets = [
  {
    id: "github-models",
    name: "GitHub Models",
    sub: "Hosted API",
    LLM_BASE_URL: "https://models.github.ai/inference",
    LLM_MODEL_NAME: "openai/gpt-4.1-mini",
    LLM_BOOST_BASE_URL: "https://models.github.ai/inference",
    LLM_BOOST_MODEL_NAME: "openai/gpt-4.1",
  },
  {
    id: "nvidia",
    name: "NVIDIA NIM",
    sub: "Hosted API",
    LLM_BASE_URL: "https://integrate.api.nvidia.com/v1",
    LLM_MODEL_NAME: "meta/llama-4-maverick-17b-128e-instruct",
    LLM_BOOST_BASE_URL: "https://integrate.api.nvidia.com/v1",
    LLM_BOOST_MODEL_NAME: "mistralai/mistral-large-3-675b-instruct-2512",
  },
  {
    id: "together",
    name: "Together AI",
    sub: "Hosted API",
    LLM_BASE_URL: "https://api.together.xyz/v1",
    LLM_MODEL_NAME: "moonshotai/Kimi-K2.5",
    LLM_BOOST_BASE_URL: "https://api.together.xyz/v1",
    LLM_BOOST_MODEL_NAME: "moonshotai/Kimi-K2.5",
  },
  {
    id: "openai",
    name: "OpenAI",
    sub: "Hosted API",
    LLM_BASE_URL: "https://api.openai.com/v1",
    LLM_MODEL_NAME: "gpt-4.1-mini",
    LLM_BOOST_BASE_URL: "https://api.openai.com/v1",
    LLM_BOOST_MODEL_NAME: "gpt-4.1",
  },
  {
    id: "ollama",
    name: "Ollama",
    sub: "Local service",
    LLM_BASE_URL: "http://localhost:11434/v1",
    LLM_MODEL_NAME: "llama3",
    LLM_BOOST_BASE_URL: "http://localhost:11434/v1",
    LLM_BOOST_MODEL_NAME: "llama3",
  },
  {
    id: "lm-studio",
    name: "LM Studio",
    sub: "Local service",
    LLM_BASE_URL: "http://localhost:1234/v1",
    LLM_MODEL_NAME: "meta-llama-3-8b-instruct",
    LLM_BOOST_BASE_URL: "http://localhost:1234/v1",
    LLM_BOOST_MODEL_NAME: "meta-llama-3-8b-instruct",
  },
];

const normalizedAllowedBaseUrls = computed(
  () => new Set(allowedBaseUrls.value.map((url) => url.replace(/\/$/, ""))),
);
const availablePresets = computed(() =>
  presets.filter((preset) => {
    const primary = preset.LLM_BASE_URL.replace(/\/$/, "");
    const boost = preset.LLM_BOOST_BASE_URL.replace(/\/$/, "");
    const isPrivate =
      primary.startsWith("http://") || boost.startsWith("http://");
    return (
      normalizedAllowedBaseUrls.value.has(primary) &&
      normalizedAllowedBaseUrls.value.has(boost) &&
      (!isPrivate || allowPrivateEndpoints.value)
    );
  }),
);

const canTest = computed(
  () =>
    form.value.LLM_API_KEY.trim() &&
    form.value.LLM_BASE_URL.trim() &&
    form.value.LLM_MODEL_NAME.trim(),
);

function close() {
  emit("close");
}

function forgetAccessKey() {
  clearAccessKey();
  hasAccessKey.value = false;
  close();
  window.location.reload();
}

function detectPreset() {
  const baseUrl = form.value.LLM_BASE_URL.trim().replace(/\/$/, "");
  const model = form.value.LLM_MODEL_NAME.trim();
  const match = availablePresets.value.find(
    (preset) =>
      baseUrl === preset.LLM_BASE_URL.replace(/\/$/, "") &&
      model === preset.LLM_MODEL_NAME,
  );
  activePresetId.value = match?.id || "";
}

function applyPreset(preset) {
  activePresetId.value = preset.id;
  form.value.LLM_BASE_URL = preset.LLM_BASE_URL;
  form.value.LLM_MODEL_NAME = preset.LLM_MODEL_NAME;
  form.value.LLM_BOOST_BASE_URL = preset.LLM_BOOST_BASE_URL;
  form.value.LLM_BOOST_MODEL_NAME = preset.LLM_BOOST_MODEL_NAME;
}

async function loadSettings() {
  loading.value = true;
  loadError.value = "";
  try {
    const response = await getSettings();
    const data = response?.data || {};
    runtimeSettingsEnabled.value = data.runtime_settings_enabled === true;
    allowedBaseUrls.value = Array.isArray(data.allowed_llm_base_urls)
      ? data.allowed_llm_base_urls.filter((value) => typeof value === "string")
      : [];
    allowPrivateEndpoints.value = data.allow_private_llm_endpoints === true;
    Object.keys(configured.value).forEach((key) => {
      configured.value[key] = data[key] === true;
    });
    if (runtimeSettingsEnabled.value) {
      Object.keys(form.value).forEach((key) => {
        form.value[key] = typeof data[key] === "string" ? data[key] : "";
      });
      detectPreset();
    }
  } catch (error) {
    loadError.value = error?.message || "Check the connection and try again.";
  } finally {
    loading.value = false;
  }
}

async function runConnectionTest() {
  testing.value = true;
  testResult.value = null;
  try {
    const response = await testConnection({
      LLM_API_KEY: form.value.LLM_API_KEY,
      LLM_BASE_URL: form.value.LLM_BASE_URL,
      LLM_MODEL_NAME: form.value.LLM_MODEL_NAME,
    });
    testResult.value = {
      success: true,
      message: response?.message || "Connection succeeded.",
    };
  } catch (error) {
    testResult.value = {
      success: false,
      message: error?.message || "The connection could not be tested.",
    };
  } finally {
    testing.value = false;
  }
}

async function save() {
  saving.value = true;
  saveError.value = "";
  try {
    await updateSettings(form.value);
    emit("saved");
    close();
  } catch (error) {
    saveError.value = error?.message || "Settings could not be saved.";
  } finally {
    saving.value = false;
  }
}

function handleKeydown(event) {
  if (event.key === "Escape") {
    close();
    return;
  }
  if (event.key !== "Tab" || !settingsSheet.value) return;
  const focusable = Array.from(
    settingsSheet.value.querySelectorAll(
      'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href]',
    ),
  ).filter((element) => element.getClientRects().length > 0);
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

let previouslyFocused = null;
let previousBodyOverflow = "";

onMounted(async () => {
  previouslyFocused = document.activeElement;
  previousBodyOverflow = document.body.style.overflow;
  document.body.style.overflow = "hidden";
  document.addEventListener("keydown", handleKeydown);
  loadSettings();
  await nextTick();
  closeButton.value?.focus();
});

onUnmounted(() => {
  document.removeEventListener("keydown", handleKeydown);
  document.body.style.overflow = previousBodyOverflow;
  previouslyFocused?.focus?.();
});
</script>

<style scoped>
.settings-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgba(12, 16, 15, 0.9);
}

.settings-sheet {
  display: flex;
  flex-direction: column;
  width: min(100%, 68rem);
  max-height: min(92dvh, 58rem);
  overflow: hidden;
  border: 1px solid var(--line-light);
  background: var(--paper);
  color: var(--ink);
  box-shadow: 1rem 1rem 0 rgba(0, 0, 0, 0.32);
}

.settings-header {
  display: grid;
  grid-template-columns: 7rem minmax(0, 1fr) auto;
  align-items: stretch;
  min-height: 7rem;
  border-bottom: 1px solid var(--line-dark);
  background: var(--ink);
  color: var(--paper);
}

.settings-index {
  display: grid;
  place-items: center;
  border-right: 4px solid var(--signal);
  background: var(--ink-deep);
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 3.3rem;
  letter-spacing: -0.03em;
}

.settings-header > div:nth-child(2) {
  align-self: center;
  padding: 1.2rem 1.6rem;
}

.settings-header p,
.section-number {
  margin: 0 0 0.25rem;
  font-family: var(--font-mono);
  font-size: 0.66rem;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.settings-header p {
  color: var(--paper-muted);
}

.settings-header h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(2.5rem, 6vw, 4.2rem);
  font-weight: 400;
  line-height: 0.85;
  letter-spacing: -0.015em;
  text-transform: uppercase;
}

.close-button {
  align-self: center;
  margin-right: 1.3rem;
  border-color: var(--line-dark);
  background: transparent;
  color: var(--paper-muted);
  text-transform: uppercase;
}

.settings-body {
  display: grid;
  gap: 1.2rem;
  padding: 1.4rem;
  overflow-y: auto;
}

.access-strip,
.connection-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 1.2rem;
  border: 1px solid var(--line-light);
  background: var(--paper-strong);
}

h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.55rem;
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.015em;
  text-transform: uppercase;
}

.access-strip p:last-child,
.managed-panel > p,
.section-heading > p,
.connection-section p:last-child,
.model-card > p {
  max-width: 44rem;
  margin: 0.38rem 0 0;
  color: var(--ink-muted);
  font-size: 0.78rem;
  line-height: 1.45;
}

.section-number {
  color: var(--signal-deep) !important;
}

.settings-state {
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.85rem;
  min-height: 6rem;
  padding: 1rem;
  border: 1px solid var(--line-light);
}

.settings-state div {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.settings-state span:last-child {
  color: var(--ink-muted);
  font-size: 0.78rem;
}

.state-marker {
  display: grid;
  place-items: center;
  width: 1.65rem;
  height: 1.65rem;
  border: 2px solid var(--signal-deep);
  background: var(--signal);
  color: var(--ink);
  font-family: var(--font-mono);
  font-weight: 700;
}

.settings-state:not(.is-error) .state-marker {
  animation: square-turn 1.2s steps(4, end) infinite;
}

.managed-panel,
.preset-section,
.model-section,
.support-section {
  padding: 1.35rem;
  border: 1px solid var(--line-light);
  background:
    linear-gradient(rgba(17, 21, 19, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(17, 21, 19, 0.035) 1px, transparent 1px),
    var(--paper-strong);
  background-size: 2rem 2rem;
}

.managed-panel h3 {
  font-size: clamp(2.2rem, 5vw, 4rem);
}

.service-status {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 1.4rem 0 1rem;
  border-top: 1px solid var(--ink);
  border-left: 1px solid var(--ink);
}

.service-status > div {
  min-height: 6.2rem;
  padding: 0.85rem;
  border-right: 1px solid var(--ink);
  border-bottom: 1px solid var(--ink);
}

.service-status dt {
  color: var(--ink-muted);
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
}

.service-status dd {
  margin: 1rem 0 0;
  font-family: var(--font-display);
  font-size: 1.2rem;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.service-status dd.ready {
  color: var(--signal-deep);
}

.managed-note {
  padding-left: 0.8rem;
  border-left: 4px solid var(--signal);
  font-weight: 600;
}

.section-heading {
  display: grid;
  grid-template-columns: minmax(13rem, 0.7fr) minmax(0, 1fr);
  gap: 1.5rem;
  align-items: end;
  margin-bottom: 1rem;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  border-top: 1px solid var(--ink);
  border-left: 1px solid var(--ink);
}

.preset-button {
  display: flex;
  min-height: 5rem;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
  padding: 0.8rem;
  border-width: 0 1px 1px 0;
  border-color: var(--ink);
  background: var(--paper);
  color: var(--ink);
  text-align: left;
}

.preset-button span {
  color: var(--ink-muted);
  font-size: 0.68rem;
}

.preset-button.active {
  background: var(--signal);
  color: var(--ink);
}

.preset-button.active span {
  color: var(--ink);
}

.provider-policy {
  margin-top: 1rem;
  padding: 0.9rem 1rem;
  border-left: 4px solid var(--signal);
  background: var(--paper);
}

.provider-policy strong {
  font-family: var(--font-display);
  font-size: 1rem;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.provider-policy p {
  margin: 0.35rem 0 0;
  color: var(--ink-muted);
  font-size: 0.76rem;
  line-height: 1.45;
}

.provider-policy ul {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin: 0.65rem 0 0;
  padding: 0;
  list-style: none;
}

.provider-policy li {
  max-width: 100%;
  padding: 0.28rem 0.4rem;
  border: 1px solid var(--line-light);
  overflow-wrap: anywhere;
  font-size: 0.68rem;
}

.model-grid,
.support-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.model-card {
  min-width: 0;
  margin: 0;
  padding: 1rem;
  border: 1px solid var(--ink);
}

.model-card legend {
  padding: 0 0.45rem;
  font-family: var(--font-display);
  font-size: 1.25rem;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.model-card label,
.support-grid label {
  display: grid;
  gap: 0.35rem;
  margin-top: 0.8rem;
  color: var(--ink-muted);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.model-card input,
.support-grid input {
  width: 100%;
  min-height: 2.65rem;
  padding: 0.65rem 0.75rem;
  border-color: var(--ink);
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  text-transform: none;
}

.secret-field {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
}

.secret-field button {
  border-left: 0;
  border-color: var(--ink);
  background: var(--ink);
  color: var(--paper);
  font-size: 0.7rem;
  text-transform: uppercase;
}

.connection-section h3 {
  font-size: 1.8rem;
}

.feedback {
  margin: 0;
  padding: 0.8rem 1rem;
  border: 1px solid var(--ink);
  background: var(--paper-strong);
  color: var(--ink);
  font-size: 0.78rem;
  font-weight: 600;
}

.feedback.is-success {
  border-left: 0.5rem solid var(--success);
}

.feedback.is-error,
.settings-state.is-error {
  border-left: 0.5rem solid var(--error);
}

.settings-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.4rem;
  border-top: 1px solid var(--line-dark);
  background: var(--ink);
  color: var(--paper-muted);
  font-size: 0.7rem;
}

.settings-footer > div {
  display: flex;
  gap: 0.6rem;
}

.secondary-action,
.primary-action {
  min-height: 2.6rem;
  border-color: var(--ink);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.secondary-action {
  background: transparent;
  color: inherit;
}

.settings-body .secondary-action {
  color: var(--ink);
}

.primary-action {
  background: var(--signal);
  color: var(--ink);
}

@keyframes square-turn {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 760px) {
  .settings-overlay {
    padding: 0;
  }

  .settings-sheet {
    width: 100%;
    max-height: 100dvh;
    min-height: 100dvh;
    border: 0;
    box-shadow: none;
  }

  .settings-header {
    grid-template-columns: 5rem minmax(0, 1fr) auto;
    min-height: 5.5rem;
  }

  .settings-index {
    font-size: 2.2rem;
  }

  .settings-header > div:nth-child(2) {
    padding: 0.8rem;
  }

  .close-button {
    margin-right: 0.6rem;
  }

  .settings-body {
    padding: 0.8rem;
  }

  .access-strip,
  .connection-section,
  .settings-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .service-status,
  .model-grid,
  .support-grid,
  .section-heading {
    grid-template-columns: 1fr;
  }

  .preset-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .settings-footer > div,
  .settings-footer button {
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .settings-state:not(.is-error) .state-marker {
    animation: none;
  }
}
</style>
