<template>
  <section class="interaction-record" aria-labelledby="interaction-record-title">
    <header class="record-header">
      <div class="record-lockup">
        <span class="record-index" aria-hidden="true">04</span>
        <div>
          <p>Run record / generated activity</p>
          <h3 id="interaction-record-title">What happened inside this run</h3>
          <span>
            Read every saved generated record in chronological order. This
            screen records model output; it does not report people’s views.
          </span>
        </div>
      </div>

      <aside
        class="record-truth-boundary"
        data-testid="interaction-truth-boundary"
        aria-label="Interpretation limits for this run record"
      >
        <span>Actions + answers: synthetic</span>
        <span>Human respondents: 0</span>
        <span>Does not measure people</span>
        <span>Not a forecast</span>
        <span>Human validation: outside this run</span>
      </aside>
    </header>

    <div class="record-toolbar">
      <div class="load-label" aria-live="polite">
        <span>{{ recordLoadLabel }}</span>
        <small v-if="lastUpdatedLabel">Checked {{ lastUpdatedLabel }}</small>
      </div>
      <button
        type="button"
        :disabled="initialLoading || refreshingRecord"
        @click="fetchRunRecord({ manual: true })"
      >
        {{ refreshingRecord ? "Checking saved records…" : "Refresh generated records" }}
      </button>
    </div>

    <div
      v-if="initialLoading"
      class="record-state is-loading"
      role="status"
      aria-live="polite"
      data-testid="interaction-run-record-loading"
    >
      <span class="state-code" aria-hidden="true">LOAD</span>
      <div>
        <p>Opening the run record</p>
        <strong>Checking for saved generated activity.</strong>
        <small>
          Nothing is treated as empty until the request completes.
        </small>
      </div>
      <div class="record-skeleton" aria-hidden="true">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>

    <div
      v-else-if="recordError && chronologicalRecords.length === 0"
      class="record-state is-error"
      role="alert"
      data-testid="interaction-run-record-error"
    >
      <span class="state-code" aria-hidden="true">ERR</span>
      <div>
        <p>Run record unavailable</p>
        <strong>The saved run record could not be opened.</strong>
        <small>{{ recordError }}</small>
      </div>
      <button
        type="button"
        :disabled="refreshingRecord"
        @click="fetchRunRecord({ manual: true })"
      >
        {{ refreshingRecord ? "Trying again…" : "Try again" }}
      </button>
    </div>

    <div v-else class="record-content">
      <div
        v-if="recordError"
        class="record-update-error"
        role="alert"
        data-testid="interaction-run-record-disconnected"
      >
        <div>
          <strong>The refresh failed.</strong>
          <span>{{ recordError }} The last loaded run record remains below.</span>
        </div>
        <button
          type="button"
          :disabled="refreshingRecord"
          @click="fetchRunRecord({ manual: true })"
        >
          {{ refreshingRecord ? "Trying again…" : "Retry refresh" }}
        </button>
      </div>

      <div
        v-if="chronologicalRecords.length === 0"
        class="record-state is-empty"
        data-testid="interaction-run-record-empty"
      >
        <span class="state-code" aria-hidden="true">00</span>
        <div>
          <p>Run record empty</p>
          <strong>No generated activity records were saved.</strong>
          <small>
            This is a successful empty response. It says nothing about people
            or outcomes outside this generated run.
          </small>
        </div>
      </div>

      <div
        v-else
        class="run-record-layout"
        data-testid="interaction-run-record-ready"
      >
        <section class="record-ledger" aria-labelledby="record-ledger-heading">
          <header>
            <div>
              <span>Canonical record</span>
              <h4 id="record-ledger-heading">Oldest to newest</h4>
            </div>
            <strong>
              {{ chronologicalRecords.length }}
              {{ chronologicalRecords.length === 1 ? "record" : "records" }}
            </strong>
          </header>

          <ol
            class="interaction-run-record-list"
            data-testid="interaction-run-record-list"
          >
            <li
              v-for="(record, recordIndex) in chronologicalRecords"
              :key="`${recordKey(record)}:${recordIndex}`"
              data-origin="synthetic-generated"
            >
              <span class="record-number" aria-hidden="true">
                {{ String(recordIndex + 1).padStart(2, "0") }}
              </span>
              <article>
                <header>
                  <div>
                    <span>{{ platformLabel(record.platform) }}</span>
                    <strong>{{ profileLabel(record, recordIndex) }}</strong>
                  </div>
                  <time v-if="record.timestamp">
                    {{ formatTimestamp(record.timestamp) }}
                  </time>
                </header>
                <p>Generated profile activity saved inside this run.</p>
                <blockquote v-if="record.text_snippet">
                  {{ cleanSnippet(record.text_snippet) }}
                </blockquote>
                <span v-else class="missing-preview">
                  No text preview was saved for this generated record.
                </span>
                <footer>
                  Origin: synthetic generated · not a human statement
                </footer>
              </article>
            </li>
          </ol>
        </section>

        <aside
          class="latest-record-inspector"
          data-testid="latest-record-inspector"
          aria-labelledby="latest-record-heading"
        >
          <span>Latest saved record</span>
          <h4 id="latest-record-heading">
            {{ profileLabel(latestRecord, chronologicalRecords.length - 1) }}
          </h4>
          <p class="latest-meta">
            {{ platformLabel(latestRecord.platform) }}
            <template v-if="latestRecord.timestamp">
              · {{ formatTimestamp(latestRecord.timestamp) }}
            </template>
          </p>
          <blockquote v-if="latestRecord.text_snippet">
            {{ cleanSnippet(latestRecord.text_snippet) }}
          </blockquote>
          <p v-else class="latest-empty">
            No text preview was saved for the latest generated record.
          </p>
          <strong>This is generated activity, not a human statement.</strong>
          <small>
            “Latest” means most recently saved by timestamp. It does not mean
            most important, most common, or most credible.
          </small>
        </aside>
      </div>
    </div>

    <details class="technical-record">
      <summary>
        <span>
          <strong>Technical record details</strong>
          <small>Run IDs, generated profile IDs, and saved timestamps</small>
        </span>
        <b aria-hidden="true">+</b>
      </summary>
      <div class="technical-record-body">
        <dl>
          <div>
            <dt>Simulation ID</dt>
            <dd>{{ simulationId || "Unavailable" }}</dd>
          </div>
          <div>
            <dt>Records shown</dt>
            <dd>{{ chronologicalRecords.length }}</dd>
          </div>
          <div>
            <dt>Update mode</dt>
            <dd>Initial load plus manual refresh</dd>
          </div>
        </dl>

        <ol v-if="chronologicalRecords.length > 0">
          <li
            v-for="(record, recordIndex) in chronologicalRecords"
            :key="`technical-${recordKey(record)}:${recordIndex}`"
          >
            <span>Record {{ String(recordIndex + 1).padStart(2, "0") }}</span>
            <code>generated_profile_id={{ record.agent_id ?? "unknown" }}</code>
            <span>{{ platformLabel(record.platform) }}</span>
            <time>{{ formatTimestamp(record.timestamp) || "Time unavailable" }}</time>
          </li>
        </ol>
        <p v-else>No generated record identifiers are available.</p>
      </div>
    </details>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { getSimulationOpinions } from "../api/simulation";

const props = defineProps({
  simulationId: String,
});

const records = ref([]);
const initialLoading = ref(true);
const refreshingRecord = ref(false);
const recordError = ref("");
const lastUpdatedAt = ref(null);
let requestInFlight = null;
let requestSequence = 0;

const recordKey = (record) =>
  [
    record?.agent_id ?? "unknown",
    record?.platform || "unknown",
    record?.timestamp || "undated",
    String(record?.text_snippet || "").slice(0, 32),
  ].join(":");

const timestampValue = (record) => {
  const value = Date.parse(record?.timestamp || "");
  return Number.isFinite(value) ? value : Number.POSITIVE_INFINITY;
};

const chronologicalRecords = computed(() =>
  records.value
    .map((record, index) => ({ record, index }))
    .sort((first, second) => {
      const timeDifference =
        timestampValue(first.record) - timestampValue(second.record);
      return timeDifference || first.index - second.index;
    })
    .map(({ record }) => record),
);

const latestRecord = computed(
  () =>
    chronologicalRecords.value[chronologicalRecords.value.length - 1] || {},
);

const platformLabel = (platform) => {
  if (platform === "reddit") return "Topic community";
  if (platform === "twitter") return "Short-post channel";
  return "Other generated channel";
};

const recordLoadLabel = computed(() => {
  if (initialLoading.value) return "Opening saved records";
  if (recordError.value) return "Saved record unavailable";
  if (refreshingRecord.value) return "Checking saved records";
  return "Saved record loaded";
});

const lastUpdatedLabel = computed(() => {
  if (!lastUpdatedAt.value) return "";
  return lastUpdatedAt.value.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
});

const profileLabel = (record, index) =>
  record?.agent_name ||
  record?.username ||
  `Generated profile ${Math.max(Number(index) + 1, 1)}`;

const formatTimestamp = (timestamp) => {
  if (!timestamp) return "";
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) return "Time unavailable";
  return parsed.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const cleanSnippet = (value) => {
  const text = String(value || "").trim().replace(/\s+/g, " ");
  if (text.length <= 220) return text;
  return `${text.slice(0, 217)}…`;
};

const fetchRunRecord = async ({ manual = false } = {}) => {
  if (requestInFlight) return requestInFlight;
  if (!props.simulationId) {
    initialLoading.value = false;
    recordError.value =
      "This view is missing the simulation ID required to load the run record.";
    return false;
  }

  const sequence = ++requestSequence;
  if (manual || !initialLoading.value) {
    refreshingRecord.value = true;
    recordError.value = "";
  }

  let currentRequest;
  currentRequest = (async () => {
    try {
      const response = await getSimulationOpinions(props.simulationId);
      if (!response?.success || !Array.isArray(response.data?.opinions)) {
        throw new Error("generated_records_unavailable");
      }
      if (sequence !== requestSequence) return false;

      records.value = response.data.opinions;
      recordError.value = "";
      lastUpdatedAt.value = new Date();
      return true;
    } catch {
      if (sequence !== requestSequence) return false;
      recordError.value =
        "The app could not reach the saved generated records. Check the connection and try again.";
      return false;
    } finally {
      if (sequence === requestSequence) {
        initialLoading.value = false;
        refreshingRecord.value = false;
      }
      if (requestInFlight === currentRequest) requestInFlight = null;
    }
  })();
  requestInFlight = currentRequest;

  return requestInFlight;
};

onMounted(() => {
  fetchRunRecord();
});

watch(
  () => props.simulationId,
  (nextSimulationId, previousSimulationId) => {
    if (nextSimulationId === previousSimulationId) return;
    requestSequence += 1;
    requestInFlight = null;
    records.value = [];
    recordError.value = "";
    lastUpdatedAt.value = null;
    initialLoading.value = true;
    fetchRunRecord();
  },
);
</script>

<style scoped>
.interaction-record {
  min-width: 0;
  background: var(--ink-soft);
  color: var(--paper);
  font-family: var(--font-sans);
}

.record-header {
  border-bottom: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.record-lockup {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 1rem;
  padding: 1.25rem 1rem;
}

.record-index {
  display: grid;
  width: 3.2rem;
  height: 3.2rem;
  place-items: center;
  border: 1px solid var(--signal);
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 1.45rem;
}

.record-lockup p,
.record-ledger > header span,
.latest-record-inspector > span {
  margin: 0;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.065em;
  text-transform: uppercase;
}

.record-lockup h3 {
  max-width: 18ch;
  margin: 0.35rem 0 0;
  font-family: var(--font-display);
  font-size: clamp(2.25rem, 11vw, 4.2rem);
  font-weight: 400;
  line-height: 0.9;
}

.record-lockup div > span {
  display: block;
  max-width: 62ch;
  margin-top: 0.75rem;
  color: var(--paper-muted);
  font-size: 0.78rem;
  line-height: 1.5;
}

.record-truth-boundary {
  display: grid;
  border-top: 1px solid var(--line-dark);
}

.record-truth-boundary span {
  padding: 0.72rem 1rem;
  border-bottom: 1px solid var(--line-dark);
  color: var(--paper);
  font-family: var(--font-mono);
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.record-truth-boundary span:nth-child(4) {
  background: var(--signal);
  color: var(--ink-deep);
}

.record-toolbar {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.8rem 1rem;
  border-bottom: 1px solid var(--line-dark);
  background: var(--ink-raised);
}

.load-label {
  display: grid;
  gap: 0.15rem;
}

.load-label span {
  color: var(--paper);
  font-size: 0.72rem;
  font-weight: 800;
}

.load-label small {
  color: var(--paper-dim);
  font-family: var(--font-mono);
  font-size: 0.62rem;
}

.record-toolbar button,
.record-state button,
.record-update-error button {
  min-height: 2.75rem;
  padding: 0.62rem 0.82rem;
  border: 1px solid var(--signal);
  border-radius: 0;
  background: var(--signal);
  color: var(--ink-deep);
  font: inherit;
  font-size: 0.7rem;
  font-weight: 800;
}

.record-toolbar button:disabled,
.record-state button:disabled,
.record-update-error button:disabled {
  opacity: 0.55;
}

.record-state {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 1rem;
  align-items: start;
  min-height: 13rem;
  padding: 1.5rem 1rem;
  border-bottom: 1px solid var(--line-dark);
  background: var(--ink-soft);
}

.record-state.is-error {
  border-top: 0.45rem solid var(--error);
}

.state-code {
  display: grid;
  min-width: 3.4rem;
  min-height: 3.4rem;
  place-items: center;
  background: var(--signal);
  color: var(--ink-deep);
  font-family: var(--font-display);
  font-size: 0.9rem;
}

.record-state.is-error .state-code {
  background: var(--error);
  color: var(--paper);
}

.record-state p {
  margin: 0;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.055em;
  text-transform: uppercase;
}

.record-state strong {
  display: block;
  max-width: 34ch;
  margin-top: 0.35rem;
  font-family: var(--font-display);
  font-size: clamp(1.65rem, 7vw, 2.5rem);
  font-weight: 400;
  line-height: 0.96;
}

.record-state small {
  display: block;
  max-width: 58ch;
  margin-top: 0.6rem;
  color: var(--paper-muted);
  font-size: 0.74rem;
  line-height: 1.48;
}

.record-state button {
  grid-column: 2;
  justify-self: start;
}

.record-skeleton {
  grid-column: 1 / -1;
  display: grid;
  gap: 0.5rem;
}

.record-skeleton span {
  display: block;
  height: 0.8rem;
  background:
    repeating-linear-gradient(
      -45deg,
      var(--ink-raised) 0 0.5rem,
      var(--line-dark) 0.5rem 1rem
    );
}

.record-skeleton span:nth-child(2) {
  width: 78%;
}

.record-skeleton span:nth-child(3) {
  width: 56%;
}

.record-update-error {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border-bottom: 0.25rem solid var(--error);
  background: var(--ink-deep);
  color: var(--paper-muted);
  font-size: 0.72rem;
}

.record-update-error strong,
.record-update-error span {
  display: block;
}

.record-update-error strong {
  color: #e7aaa0;
}

.run-record-layout {
  display: grid;
  gap: 1.25rem;
  padding: 1rem;
  border-bottom: 1px solid var(--line-dark);
}

.record-ledger {
  min-width: 0;
  border: 1px solid var(--paper);
}

.record-ledger > header {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem 1rem;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--ink-deep);
  background: var(--paper);
  color: var(--ink-deep);
}

.record-ledger > header span {
  color: var(--ink-muted);
}

.record-ledger > header h4 {
  margin: 0.1rem 0 0;
  font-family: var(--font-display);
  font-size: 1.45rem;
  font-weight: 400;
  line-height: 1;
  text-transform: uppercase;
}

.record-ledger > header > strong {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  text-transform: uppercase;
}

.interaction-run-record-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.interaction-run-record-list > li {
  display: grid;
  grid-template-columns: 3.4rem minmax(0, 1fr);
  border-bottom: 1px solid var(--line-dark);
}

.interaction-run-record-list > li:last-child {
  border-bottom: 0;
}

.record-number {
  display: grid;
  place-items: start center;
  padding-top: 1rem;
  border-right: 1px solid var(--line-dark);
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 1rem;
}

.interaction-run-record-list article {
  min-width: 0;
  padding: 1rem;
}

.interaction-run-record-list article > header {
  display: grid;
  gap: 0.4rem;
}

.interaction-run-record-list header div {
  display: grid;
  gap: 0.2rem;
}

.interaction-run-record-list header span,
.interaction-run-record-list footer {
  color: var(--signal);
  font-family: var(--font-mono);
  font-size: 0.62rem;
  letter-spacing: 0.025em;
  text-transform: uppercase;
}

.interaction-run-record-list header strong {
  font-size: 0.82rem;
}

.interaction-run-record-list time {
  color: var(--paper-dim);
  font-family: var(--font-mono);
  font-size: 0.61rem;
}

.interaction-run-record-list article > p {
  margin: 0.7rem 0 0.55rem;
  color: var(--paper-muted);
  font-size: 0.7rem;
  font-weight: 700;
}

.interaction-run-record-list blockquote,
.latest-record-inspector blockquote {
  margin: 0;
  padding: 0.85rem;
  border-left: 0.35rem solid var(--signal);
  background: var(--ink-raised);
  color: var(--paper);
  font-size: 0.78rem;
  line-height: 1.5;
}

.missing-preview {
  display: block;
  padding: 0.75rem;
  border-left: 0.35rem solid var(--line-dark);
  color: var(--paper-muted);
  font-size: 0.75rem;
}

.interaction-run-record-list footer {
  margin-top: 0.75rem;
  color: var(--paper-dim);
}

.latest-record-inspector {
  align-self: start;
  padding: 1.2rem;
  border: 1px solid var(--signal);
  background: var(--ink-deep);
}

.latest-record-inspector h4 {
  margin: 0.45rem 0 0;
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 400;
  line-height: 0.94;
}

.latest-meta {
  margin: 0.45rem 0 0.9rem;
  color: var(--paper-dim);
  font-family: var(--font-mono);
  font-size: 0.64rem;
}

.latest-record-inspector > strong {
  display: block;
  margin: 1rem -1.2rem 0;
  padding: 0.8rem 1.2rem;
  background: var(--signal);
  color: var(--ink-deep);
  font-size: 0.72rem;
  line-height: 1.4;
}

.latest-record-inspector > small {
  display: block;
  margin-top: 0.85rem;
  color: var(--paper-muted);
  font-size: 0.68rem;
  line-height: 1.45;
}

.latest-empty {
  color: var(--paper-muted);
  font-size: 0.75rem;
}

.technical-record {
  border-top: 1px solid var(--line-dark);
  background: var(--ink-raised);
}

.technical-record > summary {
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  min-height: 3.5rem;
  padding: 0.8rem 1rem;
  border-bottom: 1px solid var(--line-dark);
  cursor: pointer;
  list-style: none;
}

.technical-record > summary::-webkit-details-marker {
  display: none;
}

.technical-record > summary span,
.technical-record > summary strong,
.technical-record > summary small {
  display: block;
}

.technical-record > summary strong {
  font-family: var(--font-display);
  font-size: 1.05rem;
  font-weight: 400;
  text-transform: uppercase;
}

.technical-record > summary small {
  margin-top: 0.18rem;
  color: var(--paper-dim);
  font-size: 0.65rem;
}

.technical-record > summary > b {
  display: grid;
  width: 2.2rem;
  height: 2.2rem;
  place-items: center;
  background: var(--signal);
  color: var(--ink-deep);
  font-family: var(--font-display);
  font-size: 1.45rem;
  transition: transform 160ms var(--ease-out);
}

.technical-record[open] > summary > b {
  transform: rotate(45deg);
}

.technical-record-body {
  display: grid;
  gap: 1.25rem;
  padding: 1rem;
  border-bottom: 1px solid var(--line-dark);
}

.technical-record-body dl {
  margin: 0;
}

.technical-record-body dl > div {
  display: grid;
  gap: 0.2rem;
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--line-dark);
}

.technical-record-body dt {
  color: var(--paper-dim);
  font-size: 0.62rem;
  font-weight: 800;
  text-transform: uppercase;
}

.technical-record-body dd {
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--paper);
  font-family: var(--font-mono);
  font-size: 0.72rem;
}

.technical-record-body ol {
  max-height: 16rem;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.technical-record-body li {
  display: grid;
  gap: 0.3rem;
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--line-dark);
  color: var(--paper-muted);
  font-family: var(--font-mono);
  font-size: 0.65rem;
}

.technical-record-body code,
.technical-record-body p {
  overflow-wrap: anywhere;
  color: var(--paper-muted);
}

button:focus-visible,
summary:focus-visible {
  outline: 3px solid var(--signal);
  outline-offset: 3px;
}

button:active:not(:disabled) {
  transform: translateY(1px);
}

@media (min-width: 48rem) {
  .record-lockup {
    gap: clamp(1rem, 2vw, 2rem);
    padding: clamp(1.5rem, 3vw, 2.4rem);
  }

  .record-lockup h3 {
    font-size: clamp(3.5rem, 6vw, 5.8rem);
  }

  .record-truth-boundary {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .record-truth-boundary span {
    display: grid;
    min-height: 3.5rem;
    align-items: center;
    border-right: 1px solid var(--line-dark);
    border-bottom: 0;
  }

  .record-toolbar,
  .record-update-error {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    padding-right: clamp(1.5rem, 3vw, 2.5rem);
    padding-left: clamp(1.5rem, 3vw, 2.5rem);
  }

  .record-state {
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    padding: clamp(1.5rem, 4vw, 3rem) clamp(1.5rem, 3vw, 2.5rem);
  }

  .record-state button {
    grid-column: auto;
  }

  .record-skeleton {
    grid-column: 2 / -1;
  }

  .run-record-layout {
    grid-template-columns: minmax(0, 1.55fr) minmax(18rem, 0.65fr);
    align-items: start;
    gap: clamp(1.25rem, 3vw, 2.5rem);
    padding: clamp(1.25rem, 3vw, 2.5rem);
  }

  .interaction-run-record-list article > header {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
  }

  .latest-record-inspector {
    position: sticky;
    top: 1rem;
  }

  .technical-record > summary,
  .technical-record-body {
    padding-right: clamp(1.5rem, 3vw, 2.5rem);
    padding-left: clamp(1.5rem, 3vw, 2.5rem);
  }

  .technical-record-body {
    grid-template-columns: minmax(15rem, 0.4fr) minmax(0, 1fr);
    gap: 2rem;
  }
}

@media (min-width: 64rem) {
  .record-header {
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(18rem, 0.65fr);
  }

  .record-truth-boundary {
    grid-template-columns: 1fr;
    border-top: 0;
    border-left: 1px solid var(--line-dark);
  }

  .record-truth-boundary span {
    min-height: 0;
    border-right: 0;
    border-bottom: 1px solid var(--line-dark);
  }
}

@media (prefers-reduced-motion: reduce) {
  .technical-record > summary > b {
    transition: none;
  }
}

@media (forced-colors: active) {
  .record-truth-boundary span:nth-child(4),
  .state-code,
  .latest-record-inspector > strong {
    border: 1px solid CanvasText;
  }
}
</style>
