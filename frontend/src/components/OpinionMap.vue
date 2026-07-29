<template>
  <section class="interaction-route" aria-labelledby="interaction-route-title">
    <header class="route-header">
      <div class="route-lockup">
        <span class="route-index" aria-hidden="true">04</span>
        <div>
          <p>Generated interaction route</p>
          <h3 id="interaction-route-title">What happened inside this run</h3>
          <span>
            Each stop is a saved piece of generated activity. Follow the route
            to inspect the record without mistaking generated activity for
            real people’s views.
          </span>
        </div>
      </div>

      <aside class="route-truth" aria-label="Important interpretation limits">
        <span>Scenario records only</span>
        <strong>0 human respondents</strong>
        <b>Not public opinion · not a forecast</b>
      </aside>
    </header>

    <div class="route-toolbar">
      <div class="connection-label" aria-live="polite">
        <span :class="{ connected: !mapError && !initialLoading }">
          {{ connectionLabel }}
        </span>
        <small v-if="lastUpdatedLabel">
          Last checked {{ lastUpdatedLabel }}
        </small>
      </div>
      <button
        type="button"
        :disabled="initialLoading || refreshingMap"
        @click="fetchInteractionRecords({ manual: true })"
      >
        {{ refreshingMap ? "Checking…" : "Refresh generated records" }}
      </button>
    </div>

    <div
      v-if="initialLoading"
      class="route-state is-loading"
      role="status"
      aria-live="polite"
      data-testid="interaction-map-loading"
    >
      <div>
        <p>Loading the generated route</p>
        <strong>Checking both fictional channels for saved activity.</strong>
      </div>
      <div class="route-skeleton" aria-hidden="true">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>

    <div
      v-else-if="mapError && latestRecords.length === 0"
      class="route-state is-error"
      role="alert"
      data-testid="interaction-map-error"
    >
      <span class="state-mark" aria-hidden="true">!</span>
      <div>
        <p>Generated route unavailable</p>
        <strong>The saved interaction records could not be opened.</strong>
        <small>{{ mapError }}</small>
      </div>
      <button
        type="button"
        :disabled="refreshingMap"
        @click="fetchInteractionRecords({ manual: true })"
      >
        {{ refreshingMap ? "Reconnecting…" : "Reconnect the route" }}
      </button>
    </div>

    <div v-else class="route-content">
      <div
        v-if="mapError"
        class="route-connection-error"
        role="alert"
        data-testid="interaction-map-disconnected"
      >
        <div>
          <strong>Record updates disconnected.</strong>
          <span>{{ mapError }} The last loaded route remains below.</span>
        </div>
        <button
          type="button"
          :disabled="refreshingMap"
          @click="fetchInteractionRecords({ manual: true })"
        >
          {{ refreshingMap ? "Reconnecting…" : "Reconnect updates" }}
        </button>
      </div>

      <div v-if="latestRecords.length === 0" class="route-empty">
        <span class="state-mark" aria-hidden="true">00</span>
        <div>
          <p>No generated interaction records yet</p>
          <strong>The route will appear after this run saves activity.</strong>
          <small>
            This is a true empty state—not a failed connection and not evidence
            of public agreement or disagreement.
          </small>
        </div>
      </div>

      <div
        v-else
        class="route-board"
        aria-label="Generated interaction records grouped by fictional channel"
      >
        <section
          v-for="lane in interactionLanes"
          :key="lane.id"
          class="route-lane"
          :class="`lane-${lane.id}`"
          :aria-labelledby="`lane-${lane.id}-heading`"
        >
          <header>
            <span>{{ lane.sequence }}</span>
            <div>
              <h4 :id="`lane-${lane.id}-heading`">{{ lane.label }}</h4>
              <p>{{ lane.description }}</p>
            </div>
            <strong>
              {{ lane.records.length }}
              {{ lane.records.length === 1 ? "generated record" : "generated records" }}
            </strong>
          </header>

          <ol class="lane-stops">
            <li
              v-for="(record, recordIndex) in lane.records"
              :key="recordKey(record)"
            >
              <article class="route-stop">
                <span class="stop-marker" aria-hidden="true">
                  {{ String(recordIndex + 1).padStart(2, "0") }}
                </span>
                <div class="stop-copy">
                  <header>
                    <strong>{{ profileLabel(record, recordIndex) }}</strong>
                    <time v-if="record.timestamp">
                      {{ formatTimestamp(record.timestamp) }}
                    </time>
                  </header>
                  <p>Generated profile activity saved in this run.</p>
                  <blockquote v-if="record.text_snippet">
                    {{ cleanSnippet(record.text_snippet) }}
                  </blockquote>
                  <span v-else>
                    No text preview was saved for this generated record.
                  </span>
                  <footer>
                    Generated record · {{ lane.label }} · not a person’s
                    testimony
                  </footer>
                </div>
              </article>
            </li>
          </ol>
        </section>
      </div>
    </div>

    <details class="technical-record">
      <summary>
        <span>Technical record details</span>
        <small>Run IDs, generated profile IDs, and timestamps · closed by default</small>
      </summary>
      <div class="technical-record-body">
        <dl>
          <div>
            <dt>Simulation ID</dt>
            <dd>{{ simulationId || "Unavailable" }}</dd>
          </div>
          <div>
            <dt>Records shown</dt>
            <dd>{{ latestRecords.length }}</dd>
          </div>
          <div>
            <dt>Refresh cycle</dt>
            <dd>Checks every 5 seconds while this view is open</dd>
          </div>
        </dl>

        <ol v-if="latestRecords.length > 0">
          <li
            v-for="(record, recordIndex) in latestRecords"
            :key="`technical-${recordKey(record)}`"
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
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { getSimulationOpinions } from "../api/simulation";

const props = defineProps({
  simulationId: String,
});

const RECORD_POLL_INTERVAL_MS = 5000;

const records = ref([]);
const initialLoading = ref(true);
const refreshingMap = ref(false);
const mapError = ref("");
const lastUpdatedAt = ref(null);
let pollTimer = null;
let requestInFlight = null;
let requestSequence = 0;

const recordKey = (record) =>
  [
    record.agent_id ?? "unknown",
    record.platform || "unknown",
    record.timestamp || "undated",
  ].join(":");

const latestRecords = computed(() => {
  const latestByProfileAndChannel = new Map();
  const sorted = [...records.value].sort((first, second) =>
    String(first?.timestamp || "").localeCompare(
      String(second?.timestamp || ""),
    ),
  );

  sorted.forEach((record) => {
    const key = `${record?.agent_id ?? "unknown"}:${record?.platform || "unknown"}`;
    latestByProfileAndChannel.set(key, record);
  });

  return Array.from(latestByProfileAndChannel.values()).sort((first, second) =>
    String(second?.timestamp || "").localeCompare(
      String(first?.timestamp || ""),
    ),
  );
});

const platformLabel = (platform) => {
  if (platform === "reddit") return "Topic community";
  if (platform === "twitter") return "Short-post channel";
  return "Other generated channel";
};

const laneDescription = (platform) => {
  if (platform === "reddit") {
    return "Longer generated posts and replies saved in the fictional topic space.";
  }
  if (platform === "twitter") {
    return "Short generated posts and reactions saved in the fictional feed.";
  }
  return "Generated activity saved outside the two primary fictional channels.";
};

const interactionLanes = computed(() => {
  const laneOrder = ["reddit", "twitter", "other"];
  const grouped = new Map(
    laneOrder.map((platform) => [platform, []]),
  );

  latestRecords.value.forEach((record) => {
    const platform =
      record?.platform === "reddit" || record?.platform === "twitter"
        ? record.platform
        : "other";
    grouped.get(platform).push(record);
  });

  return laneOrder
    .filter((platform) => grouped.get(platform).length > 0)
    .map((platform, index) => ({
      id: platform,
      sequence: String(index + 1).padStart(2, "0"),
      label: platformLabel(platform),
      description: laneDescription(platform),
      records: grouped.get(platform),
    }));
});

const connectionLabel = computed(() => {
  if (initialLoading.value) return "Connecting to generated records";
  if (mapError.value) return "Updates disconnected";
  if (refreshingMap.value) return "Checking for newer generated records";
  return "Generated records connected";
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
  `Fictional profile ${Number(index) + 1}`;

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

const fetchInteractionRecords = async ({ manual = false } = {}) => {
  if (requestInFlight) return requestInFlight;
  if (!props.simulationId) {
    initialLoading.value = false;
    mapError.value =
      "This route is missing the simulation ID needed to load generated records.";
    return false;
  }

  const sequence = ++requestSequence;
  if (manual || !initialLoading.value) refreshingMap.value = true;

  let currentRequest;
  currentRequest = (async () => {
    try {
      const response = await getSimulationOpinions(props.simulationId);
      if (!response?.success || !Array.isArray(response.data?.opinions)) {
        throw new Error("generated_records_unavailable");
      }
      if (sequence !== requestSequence) return false;

      records.value = response.data.opinions;
      mapError.value = "";
      lastUpdatedAt.value = new Date();
      return true;
    } catch {
      if (sequence !== requestSequence) return false;
      mapError.value =
        "The app could not reach the saved generated records. Check the connection and try again.";
      return false;
    } finally {
      if (sequence === requestSequence) {
        initialLoading.value = false;
        refreshingMap.value = false;
      }
      if (requestInFlight === currentRequest) requestInFlight = null;
    }
  })();
  requestInFlight = currentRequest;

  return requestInFlight;
};

onMounted(() => {
  fetchInteractionRecords();
  pollTimer = window.setInterval(
    () => fetchInteractionRecords(),
    RECORD_POLL_INTERVAL_MS,
  );
});

onUnmounted(() => {
  requestSequence += 1;
  if (pollTimer) window.clearInterval(pollTimer);
});

watch(
  () => props.simulationId,
  (nextSimulationId, previousSimulationId) => {
    if (nextSimulationId === previousSimulationId) return;
    requestSequence += 1;
    requestInFlight = null;
    records.value = [];
    mapError.value = "";
    lastUpdatedAt.value = null;
    initialLoading.value = true;
    fetchInteractionRecords();
  },
);
</script>

<style scoped>
.interaction-route {
  min-width: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-sans);
}

.route-header {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(18rem, 0.65fr);
  border-bottom: 3px solid var(--ink);
  background: var(--ink-deep);
  color: var(--paper);
}

.route-lockup {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: clamp(1rem, 2vw, 2rem);
  align-items: start;
  padding: clamp(1.25rem, 3vw, 2.25rem);
}

.route-index,
.state-mark {
  display: grid;
  width: 3.4rem;
  height: 3.4rem;
  place-items: center;
  border: 2px solid var(--signal);
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 1.55rem;
}

.route-lockup p,
.route-state p,
.route-empty p {
  margin: 0 0 0.45rem;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.78rem;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.route-lockup h3 {
  max-width: 18ch;
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(2.1rem, 4vw, 3.8rem);
  font-weight: 400;
  line-height: 0.92;
  text-transform: uppercase;
}

.route-lockup > div > span {
  display: block;
  max-width: 57rem;
  margin-top: 0.85rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--line-dark);
  color: var(--paper-muted);
  font-size: 0.82rem;
  line-height: 1.5;
}

.route-truth {
  display: grid;
  align-content: center;
  padding: clamp(1.25rem, 3vw, 2.25rem);
  border-left: 3px solid var(--ink);
  background: var(--signal);
  color: var(--ink);
}

.route-truth span,
.route-truth b {
  font-family: var(--font-display);
  font-size: 0.82rem;
  font-weight: 400;
  letter-spacing: 0.055em;
  text-transform: uppercase;
}

.route-truth strong {
  max-width: 8ch;
  margin: 0.65rem 0 0.35rem;
  font-family: var(--font-display);
  font-size: clamp(2.4rem, 4vw, 3.7rem);
  font-weight: 400;
  line-height: 0.82;
  text-transform: uppercase;
}

.route-toolbar {
  display: flex;
  min-height: 4rem;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.7rem clamp(1rem, 3vw, 2rem);
  border-bottom: 2px solid var(--ink);
  background: var(--paper-strong);
}

.connection-label {
  display: grid;
  gap: 0.15rem;
}

.connection-label > span {
  position: relative;
  padding-left: 1.1rem;
  color: var(--error-text);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.connection-label > span::before {
  position: absolute;
  top: 0.25rem;
  left: 0;
  width: 0.55rem;
  height: 0.55rem;
  background: var(--error);
  content: "";
}

.connection-label > span.connected {
  color: var(--ink);
}

.connection-label > span.connected::before {
  background: var(--success);
}

.connection-label small {
  color: var(--ink-muted);
  font-size: 0.68rem;
}

.route-toolbar button,
.route-state button,
.route-connection-error button {
  min-height: 2.7rem;
  padding: 0.6rem 0.9rem;
  border: 2px solid var(--ink);
  border-radius: 0;
  background: var(--signal);
  color: var(--ink);
  font-size: 0.7rem;
  font-weight: 800;
  text-transform: uppercase;
}

.route-toolbar button:active:not(:disabled),
.route-state button:active:not(:disabled),
.route-connection-error button:active:not(:disabled) {
  transform: translateY(1px);
}

.route-state,
.route-empty {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 1rem 1.5rem;
  align-items: center;
  min-height: 17rem;
  padding: clamp(1.5rem, 4vw, 3rem);
  border-bottom: 3px solid var(--ink);
}

.route-state.is-loading {
  grid-template-columns: minmax(0, 1fr) minmax(14rem, 0.65fr);
  background: var(--ink);
  color: var(--paper);
}

.route-state strong,
.route-empty strong {
  display: block;
  max-width: 38rem;
  font-family: var(--font-display);
  font-size: clamp(1.55rem, 3vw, 2.4rem);
  font-weight: 400;
  line-height: 1;
  text-transform: uppercase;
}

.route-state small,
.route-empty small {
  display: block;
  max-width: 48rem;
  margin-top: 0.5rem;
  color: var(--ink-muted);
  font-size: 0.78rem;
  line-height: 1.45;
}

.route-state.is-loading small {
  color: var(--paper-muted);
}

.route-state.is-error {
  border-top: 0.55rem solid var(--error);
  background: var(--paper);
}

.route-state.is-error .state-mark {
  border-color: var(--error);
  background: var(--error);
  color: var(--paper);
}

.route-skeleton {
  display: grid;
  gap: 0.8rem;
}

.route-skeleton span {
  height: 1rem;
  transform-origin: left;
  background: var(--line-dark);
  animation: route-pulse 1.2s var(--ease-out) infinite alternate;
}

.route-skeleton span:nth-child(2) {
  width: 76%;
  animation-delay: 120ms;
}

.route-skeleton span:nth-child(3) {
  width: 52%;
  animation-delay: 240ms;
}

.route-connection-error {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1rem;
  align-items: center;
  padding: 0.85rem clamp(1rem, 3vw, 2rem);
  border-bottom: 3px solid var(--error);
  background: var(--ink);
  color: var(--paper);
}

.route-connection-error div {
  display: grid;
  gap: 0.25rem;
}

.route-connection-error strong {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 400;
  letter-spacing: 0.045em;
  text-transform: uppercase;
}

.route-connection-error span {
  color: var(--paper-muted);
  font-size: 0.76rem;
}

.route-empty {
  grid-template-columns: auto minmax(0, 1fr);
  background:
    linear-gradient(var(--line-light) 1px, transparent 1px),
    linear-gradient(90deg, var(--line-light) 1px, transparent 1px),
    var(--paper);
  background-size: 2.2rem 2.2rem;
}

.route-empty .state-mark {
  border-color: var(--ink);
  background: var(--signal);
  color: var(--ink);
}

.route-board {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(20rem, 0.85fr);
  border-bottom: 3px solid var(--ink);
  background: var(--paper);
}

.route-lane + .route-lane {
  border-left: 3px solid var(--ink);
}

.route-lane > header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.7rem 1rem;
  align-items: center;
  min-height: 7rem;
  padding: 1rem 1.25rem;
  border-bottom: 3px solid var(--ink);
  background: var(--ink);
  color: var(--paper);
}

.route-lane > header > span {
  grid-row: 1 / span 2;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 2rem;
}

.route-lane > header h4 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 400;
  letter-spacing: 0.035em;
  line-height: 1;
  text-transform: uppercase;
}

.route-lane > header p {
  margin: 0.25rem 0 0;
  color: var(--paper-muted);
  font-size: 0.7rem;
  line-height: 1.35;
}

.route-lane > header > strong {
  grid-column: 2;
  color: var(--signal);
  font-size: 0.65rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.lane-stops {
  position: relative;
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0 0 0 1.15rem;
  list-style: none;
}

.lane-stops::before {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 2.8rem;
  width: 0.35rem;
  background: var(--signal);
  content: "";
}

.lane-stops > li {
  position: relative;
  border-bottom: 2px solid var(--ink);
}

.lane-stops > li:last-child {
  border-bottom: 0;
}

.route-stop {
  position: relative;
  display: grid;
  grid-template-columns: 3.4rem minmax(0, 1fr);
  gap: 1rem;
  min-height: 10rem;
  padding: 1.25rem 1.25rem 1.25rem 0;
  background: var(--paper);
}

.stop-marker {
  z-index: 1;
  display: grid;
  width: 3.4rem;
  height: 3.4rem;
  place-items: center;
  border: 3px solid var(--ink);
  background: var(--signal);
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1.2rem;
}

.stop-copy {
  min-width: 0;
}

.stop-copy > header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 0.55rem;
  border-bottom: 1px solid var(--line-light);
}

.stop-copy > header strong {
  overflow: hidden;
  font-size: 0.86rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stop-copy time {
  flex: 0 0 auto;
  color: var(--ink-muted);
  font-size: 0.62rem;
}

.stop-copy > p {
  margin: 0.75rem 0 0.5rem;
  color: var(--ink-muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.stop-copy blockquote {
  margin: 0;
  padding: 0.8rem;
  border-left: 0.4rem solid var(--signal);
  background: var(--paper-strong);
  font-size: 0.78rem;
  line-height: 1.5;
}

.stop-copy > span {
  display: block;
  margin-top: 0.6rem;
  color: var(--ink-muted);
  font-size: 0.74rem;
}

.stop-copy footer {
  margin-top: 0.75rem;
  color: var(--ink-muted);
  font-size: 0.62rem;
  font-weight: 800;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.technical-record {
  background: var(--paper-strong);
}

.technical-record > summary {
  display: flex;
  min-height: 4rem;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.85rem clamp(1rem, 3vw, 2rem);
  border-bottom: 2px solid var(--ink);
  cursor: pointer;
  list-style: none;
}

.technical-record > summary::-webkit-details-marker {
  display: none;
}

.technical-record > summary::before {
  display: grid;
  width: 2rem;
  height: 2rem;
  flex: 0 0 2rem;
  place-items: center;
  background: var(--ink);
  color: var(--signal);
  content: "+";
  font-family: var(--font-display);
  font-size: 1.25rem;
}

.technical-record[open] > summary::before {
  content: "−";
}

.technical-record > summary span {
  margin-right: auto;
  font-family: var(--font-display);
  font-size: 1rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.technical-record > summary small {
  color: var(--ink-muted);
  font-size: 0.68rem;
}

.technical-record-body {
  display: grid;
  grid-template-columns: minmax(15rem, 0.35fr) minmax(0, 1fr);
  gap: 2rem;
  padding: 1.5rem clamp(1rem, 3vw, 2rem);
  border-bottom: 3px solid var(--ink);
}

.technical-record-body dl {
  margin: 0;
}

.technical-record-body dl > div {
  padding: 0.75rem 0;
  border-top: 1px solid var(--line-light);
}

.technical-record-body dt {
  color: var(--ink-muted);
  font-size: 0.62rem;
  font-weight: 800;
  text-transform: uppercase;
}

.technical-record-body dd {
  margin: 0.25rem 0 0;
  overflow-wrap: anywhere;
  font-family: var(--font-mono);
  font-size: 0.72rem;
}

.technical-record-body ol {
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}

.technical-record-body li {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  gap: 0.75rem;
  align-items: center;
  padding: 0.65rem 0;
  border-top: 1px solid var(--line-light);
  font-size: 0.68rem;
}

.technical-record-body code {
  overflow-wrap: anywhere;
  color: var(--ink-muted);
}

.technical-record-body p {
  color: var(--ink-muted);
  font-size: 0.76rem;
}

@keyframes route-pulse {
  from {
    opacity: 0.35;
    transform: scaleX(0.74);
  }

  to {
    opacity: 1;
    transform: scaleX(1);
  }
}

@media (max-width: 900px) {
  .route-header,
  .route-board,
  .technical-record-body {
    grid-template-columns: 1fr;
  }

  .route-truth,
  .route-lane + .route-lane {
    border-left: 0;
  }

  .route-truth {
    border-top: 3px solid var(--ink);
  }

  .route-lane + .route-lane {
    border-top: 3px solid var(--ink);
  }
}

@media (max-width: 600px) {
  .route-lockup {
    grid-template-columns: 2.6rem minmax(0, 1fr);
    gap: 0.75rem;
    padding: 1rem;
  }

  .route-index,
  .state-mark {
    width: 2.6rem;
    height: 2.6rem;
    font-size: 1.1rem;
  }

  .route-lockup h3 {
    font-size: 2.2rem;
  }

  .route-lockup > div > span {
    font-size: 0.75rem;
  }

  .route-truth {
    padding: 1rem;
  }

  .route-truth strong {
    max-width: none;
    font-size: 2.25rem;
  }

  .route-toolbar,
  .route-connection-error,
  .route-state {
    align-items: stretch;
    flex-direction: column;
    grid-template-columns: 1fr;
  }

  .route-toolbar {
    display: flex;
  }

  .route-toolbar button,
  .route-connection-error button,
  .route-state button {
    width: 100%;
  }

  .route-state,
  .route-state.is-loading,
  .route-empty {
    grid-template-columns: 1fr;
    min-height: 15rem;
    padding: 1.25rem 1rem;
  }

  .route-lane > header {
    min-height: 0;
    padding: 0.9rem 1rem;
  }

  .lane-stops {
    padding-left: 0.75rem;
  }

  .lane-stops::before {
    left: 2.15rem;
  }

  .route-stop {
    grid-template-columns: 2.8rem minmax(0, 1fr);
    gap: 0.75rem;
    min-height: 0;
    padding: 1rem 0.75rem 1rem 0;
  }

  .stop-marker {
    width: 2.8rem;
    height: 2.8rem;
    font-size: 1rem;
  }

  .stop-copy > header {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.25rem;
  }

  .technical-record > summary {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .technical-record > summary small {
    width: 100%;
    padding-left: 3rem;
  }

  .technical-record-body li {
    grid-template-columns: 1fr;
    gap: 0.25rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .route-skeleton span {
    animation: none;
  }
}
</style>
