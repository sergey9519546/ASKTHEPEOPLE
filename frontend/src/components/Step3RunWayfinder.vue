<template>
  <section
    class="run-wayfinder"
    :data-run-state="recordState"
    aria-labelledby="run-wayfinder-title"
  >
    <header class="run-hero">
      <div class="run-hero-copy">
        <span class="run-kicker">03 / Check the run</span>
        <h2 id="run-wayfinder-title">{{ runHeadline }}</h2>
        <p>{{ runDeck }}</p>
      </div>

      <aside
        class="run-truth-boundary"
        data-testid="run-truth-boundary"
        aria-label="Interpretation limits for this synthetic run"
      >
        <span>Actions + answers: synthetic</span>
        <span>Human respondents: 0</span>
        <span>Not a forecast</span>
        <span>Sources: starting conditions only</span>
        <span>Human validation: outside this run</span>
      </aside>
    </header>

    <section class="decision-band" aria-labelledby="decision-heading">
      <div class="decision-copy">
        <span class="section-index">Decision under rehearsal</span>
        <h3 id="decision-heading">{{ decisionQuestion }}</h3>
      </div>

      <div
        class="run-progress"
        role="progressbar"
        aria-label="Saved simulation round completion"
        :aria-valuemin="0"
        :aria-valuemax="progressMax"
        :aria-valuenow="Math.min(currentRound, progressMax)"
        :aria-valuetext="progressText"
      >
        <div class="progress-heading">
          <span>{{ progressLabel }}</span>
          <strong>{{ progressText }}</strong>
        </div>
        <div class="progress-track" aria-hidden="true">
          <span :style="{ transform: `scaleX(${progressRatio})` }"></span>
        </div>
        <small>
          This tracks saved rounds only. It does not score a path or outcome.
        </small>
      </div>
    </section>

    <section class="run-record" aria-labelledby="run-record-heading">
      <header class="record-heading">
        <div>
          <span class="section-index">Run record / generated activity</span>
          <h3 id="run-record-heading">Generated activity, in recorded order</h3>
          <p>
            Generated activity is the run record. Possible paths are created
            later in the decision brief.
          </p>
        </div>
        <span class="record-status" :class="`is-${statusTone}`" aria-live="polite">
          <b aria-hidden="true">{{ statusCode }}</b>
          {{ statusLabel }}
        </span>
      </header>

      <div
        v-if="hasRunError"
        class="record-state is-error"
        data-testid="run-record-error"
        role="alert"
      >
        <span class="state-code" aria-hidden="true">ERR</span>
        <div>
          <strong>This run stopped before the record was complete.</strong>
          <p>{{ startError || runStatus.error || "The saved run did not finish." }}</p>
        </div>
        <button
          type="button"
          @click="$emit(startError ? 'retry-run' : 'start-over')"
        >
          {{ startError ? "Try this run again" : "Return to assumptions" }}
        </button>
      </div>

      <div
        v-if="recordState === 'loading'"
        class="record-state is-loading"
        data-testid="run-record-loading"
        role="status"
        aria-live="polite"
      >
        <span class="state-code" aria-hidden="true">REC</span>
        <div>
          <strong>No generated action has been saved yet.</strong>
          <p>
            The run is active. This area will show each saved synthetic action
            without making claims about people or outcomes outside this run.
          </p>
        </div>
      </div>

      <div
        v-else-if="recordItems.length === 0 && !hasRunError"
        class="record-state is-empty"
        data-testid="run-record-empty"
      >
        <span class="state-code" aria-hidden="true">00</span>
        <div>
          <strong v-if="hasCompleted">
            The run finished without a saved generated action.
          </strong>
          <strong v-else>No generated actions are recorded.</strong>
          <p v-if="hasCompleted">
            This is an empty synthetic run record, not evidence about people
            or any real-world outcome.
          </p>
          <p v-else>
            Begin the run to create a synthetic activity record under the
            reviewed assumptions.
          </p>
        </div>
      </div>

      <div
        v-else-if="recordItems.length > 0"
        class="record-layout"
        :data-testid="hasCompleted ? 'run-record-complete' : 'run-record-active'"
      >
        <div class="record-ledger">
          <div class="record-list-heading">
            <span>Recorded order</span>
            <strong>Oldest to newest · {{ recordItems.length }} saved</strong>
          </div>
          <ol class="run-record-list" data-testid="run-record-list">
            <li
              v-for="item in recordItems"
              :key="item.id"
              data-origin="synthetic-generated"
            >
              <span class="record-number" aria-hidden="true">{{ item.sequence }}</span>
              <article>
                <header>
                  <span>{{ item.roundLabel }} · {{ item.channel }}</span>
                  <strong>{{ item.actor }}</strong>
                </header>
                <p>{{ item.text }}</p>
                <footer>
                  Synthetic generated action · recorded inside this run
                </footer>
              </article>
            </li>
          </ol>
        </div>

        <aside class="meaning-boundary" aria-labelledby="meaning-boundary-heading">
          <span class="section-index">Do not collapse these stages</span>
          <h4 id="meaning-boundary-heading">Record ≠ path ≠ human finding</h4>
          <dl>
            <div>
              <dt>Generated activity</dt>
              <dd>Model-generated actions recorded inside this run.</dd>
            </div>
            <div>
              <dt>Possible paths</dt>
              <dd>
                Exploratory branches assembled in the decision brief from
                assumptions, tensions, and missing information.
              </dd>
            </div>
            <div>
              <dt>Human validation</dt>
              <dd>External research with real people after this workflow.</dd>
            </div>
          </dl>
          <p>
            Possible paths are exploratory branches, not predictions, rankings,
            or real-world evidence.
          </p>
        </aside>
      </div>
    </section>

    <section class="validation-handoff" aria-labelledby="handoff-heading">
      <span class="handoff-index" aria-hidden="true">→</span>
      <div>
        <span class="section-index">Next boundary</span>
        <h3 id="handoff-heading">Validate with people outside this run</h3>
        <p>
          Open the decision brief to turn recorded synthetic activity into
          possible paths, source gaps, and questions for real conversations.
        </p>
        <div v-if="reportError" class="handoff-error" role="alert">
          <strong>The decision brief was not prepared.</strong>
          <span>{{ reportError }}</span>
        </div>
      </div>
      <button
        class="review-button"
        type="button"
        :disabled="!canReview || isReviewing"
        @click="$emit('review')"
      >
        <span v-if="isReviewing">Preparing the brief…</span>
        <span v-else-if="canReview">Open the decision brief</span>
        <span v-else>Available when the run finishes</span>
      </button>
    </section>

    <div
      v-if="liveUpdateError && isRunning"
      class="live-update-alert"
      role="status"
      aria-live="polite"
    >
      <span>
        <strong>Run updates are disconnected.</strong>
        The server-side run may still be continuing.
      </span>
      <button type="button" @click="$emit('reconnect')">Reconnect updates</button>
    </div>

    <div class="run-capability-note">
      <span>
        Need different conditions? An active run cannot be changed after it begins.
      </span>
      <button type="button" @click="$emit('start-over')">
        Return to assumptions
      </button>
    </div>

    <details class="run-details" @toggle="handleDetailsToggle">
      <summary>
        <span>
          <strong>Technical run details</strong>
          <small>Readiness, synthetic interaction diagnostics, and process notes</small>
        </span>
        <b aria-hidden="true">+</b>
      </summary>

      <div class="details-grid">
        <section class="detail-section" aria-labelledby="readiness-heading">
          <span class="detail-number">01</span>
          <div>
            <h3 id="readiness-heading">Before the run</h3>
            <p>System readiness recorded when this run started.</p>
            <dl class="readiness-list">
              <div>
                <dt>Readiness checks</dt>
                <dd>{{ readinessLabel }}</dd>
              </div>
              <div>
                <dt>Generated profiles</dt>
                <dd>{{ diagnostics?.canonical_agents?.length || "Not available" }}</dd>
              </div>
              <div>
                <dt>Starting relationships</dt>
                <dd>{{ diagnostics?.relationship_bootstrap?.length || "Not available" }}</dd>
              </div>
              <div>
                <dt>Response rules</dt>
                <dd>{{ diagnostics?.model_resolution?.actor ? "Ready" : "Not available" }}</dd>
              </div>
            </dl>
            <p v-if="diagnosticsError" class="detail-error">{{ diagnosticsError }}</p>
          </div>
        </section>

        <section class="detail-section" aria-labelledby="activity-heading">
          <span class="detail-number">02</span>
          <div>
            <h3 id="activity-heading">Record inventory</h3>
            <p>Counts saved synthetic actions only. They are not a sample size.</p>
            <dl class="readiness-list">
              <div>
                <dt>Saved actions</dt>
                <dd>{{ recordItems.length }}</dd>
              </div>
              <div>
                <dt>Last saved round</dt>
                <dd>{{ currentRound || "Not available" }}</dd>
              </div>
            </dl>
          </div>
        </section>

        <section class="detail-section" aria-labelledby="patterns-heading">
          <span class="detail-number">03</span>
          <div>
            <h3 id="patterns-heading">Synthetic interaction diagnostics</h3>
            <p>
              Descriptive values from this generated interaction graph. They
              are not population measures or real-world confidence scores.
            </p>

            <div v-if="metricsLoading" class="detail-loading" role="status">
              <span aria-hidden="true">··</span>
              Reading the saved diagnostic record…
            </div>
            <div v-else-if="metricsError" class="detail-error">
              <p>{{ metricsError }}</p>
              <button type="button" @click="$emit('load-metrics')">Try again</button>
            </div>
            <dl v-else-if="metrics" class="pattern-list">
              <div>
                <dt>Conversation clustering</dt>
                <dd>{{ formatDecimal(metrics.polarization_index) }}</dd>
                <small>Generated network modularity inside this run</small>
              </div>
              <div>
                <dt>Activity concentration</dt>
                <dd>{{ formatDecimal(metrics.engagement_gini) }}</dd>
                <small>Generated action distribution inside this run</small>
              </div>
              <div>
                <dt>Within-group interaction ratio</dt>
                <dd>{{ formatDecimal(metrics.echo_chamber_score) }}</dd>
                <small>Raw 0–1 ratio inside the generated graph</small>
              </div>
            </dl>
            <button
              v-else
              class="load-patterns"
              type="button"
              :disabled="!canReview"
              @click="$emit('load-metrics')"
            >
              {{ canReview ? "Load synthetic diagnostics" : "Available after the run" }}
            </button>
          </div>
        </section>

        <section class="detail-section" aria-labelledby="notes-heading">
          <span class="detail-number">04</span>
          <div>
            <h3 id="notes-heading">Process notes</h3>
            <p>Recent system-authored updates from this run.</p>
            <ul v-if="recentNotes.length" class="process-notes">
              <li v-for="(note, index) in recentNotes" :key="`${index}-${note}`">
                {{ note }}
              </li>
            </ul>
            <p v-else class="detail-empty">No process notes are available.</p>
          </div>
        </section>
      </div>
    </details>
  </section>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  runStatus: {
    type: Object,
    default: () => ({}),
  },
  actions: {
    type: Array,
    default: () => [],
  },
  phase: {
    type: Number,
    default: 0,
  },
  isStarting: Boolean,
  startError: String,
  liveUpdateError: String,
  reportError: String,
  canReview: Boolean,
  isReviewing: Boolean,
  projectData: {
    type: Object,
    default: () => ({}),
  },
  maxRounds: Number,
  preflight: Object,
  diagnostics: Object,
  diagnosticsError: String,
  metrics: Object,
  metricsLoading: Boolean,
  metricsError: String,
  systemLogs: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits([
  "review",
  "load-metrics",
  "retry-run",
  "start-over",
  "reconnect",
]);

const failedStatuses = new Set(["failed", "interrupted"]);

const runnerStatus = computed(() => props.runStatus?.runner_status || "idle");
const hasFailed = computed(() => failedStatuses.has(runnerStatus.value));
const hasRunError = computed(() => Boolean(props.startError) || hasFailed.value);
const hasCompleted = computed(() => props.phase === 2 && !hasFailed.value);
const isRunning = computed(
  () =>
    !hasCompleted.value &&
    (props.isStarting ||
      ["starting", "running", "stopping"].includes(runnerStatus.value)),
);

const decisionQuestion = computed(
  () =>
    props.projectData?.simulation_requirement ||
    props.projectData?.simulationRequirement ||
    props.projectData?.question ||
    "What could happen under the conditions in this scenario?",
);

const runHeadline = computed(() => {
  if (hasFailed.value) return "This run stopped before the finish.";
  if (hasCompleted.value) return "See how the run unfolded.";
  if (isRunning.value) return "Follow the activity as it unfolds.";
  return "Prepare the decision rehearsal.";
});

const runDeck = computed(() => {
  if (hasFailed.value) {
    return "Inspect any saved generated actions, then decide whether to revise the assumptions and begin again.";
  }
  if (hasCompleted.value) {
    return "Read the generated activity in chronological order before opening possible paths in the decision brief.";
  }
  if (isRunning.value) {
    return "This screen records model-generated actions under the reviewed assumptions. It does not observe people.";
  }
  return "Review the decision and conditions before the synthetic run begins.";
});

const totalRounds = computed(() =>
  Math.max(Number(props.runStatus?.total_rounds || props.maxRounds || 0), 0),
);
const currentRound = computed(() =>
  Math.max(
    Number(props.runStatus?.current_round || 0),
    Number(props.runStatus?.twitter_current_round || 0),
    Number(props.runStatus?.reddit_current_round || 0),
  ),
);
const progressMax = computed(() =>
  Math.max(totalRounds.value, currentRound.value, 1),
);
const progressRatio = computed(() => {
  if (hasCompleted.value) return 1;
  return Math.max(0, Math.min(1, currentRound.value / progressMax.value));
});
const progressText = computed(() => {
  if (hasCompleted.value) return "Run complete";
  if (!totalRounds.value) return "Waiting to begin";
  return `Round ${currentRound.value} of ${totalRounds.value}`;
});
const progressLabel = computed(() => {
  if (hasFailed.value) return "Run stopped";
  if (hasCompleted.value) return "Rounds recorded";
  if (isRunning.value) return "Saved round progress";
  return "Run not started";
});

const statusLabel = computed(() => {
  if (hasRunError.value) return "Run stopped";
  if (hasCompleted.value) return "Record complete";
  if (isRunning.value) return "Recording generated activity";
  return "Not started";
});
const statusTone = computed(() => {
  if (hasRunError.value) return "error";
  if (hasCompleted.value) return "complete";
  if (isRunning.value) return "running";
  return "waiting";
});
const statusCode = computed(() => ({
  error: "ERR",
  complete: "END",
  running: "REC",
  waiting: "WAIT",
})[statusTone.value]);

const actionText = (action) => {
  const args = action?.action_args || {};
  return (
    args.content ||
    args.quote_content ||
    args.original_content ||
    args.post_content ||
    args.comment_content ||
    args.query ||
    args.keyword ||
    ""
  );
};

const cleanText = (value, limit = 180) => {
  const normalized = String(value || "").replace(/\s+/g, " ").trim();
  if (!normalized) return "";
  return normalized.length > limit
    ? `${normalized.slice(0, limit - 1).trim()}…`
    : normalized;
};

const channelLabel = (platform) => {
  if (platform === "twitter") return "Short-post channel";
  if (platform === "reddit") return "Topic-community channel";
  return "Generated channel";
};

const describeAction = (action) => {
  const actor = cleanText(action?.agent_name, 48) || "Generated profile";
  const text = cleanText(actionText(action));
  const target =
    cleanText(action?.action_args?.target_user_name, 48) ||
    cleanText(action?.action_args?.post_author_name, 48);

  switch (action?.action_type) {
    case "CREATE_POST":
      return text ? `${actor} introduces “${text}”` : `${actor} creates a post.`;
    case "CREATE_COMMENT":
      return text ? `${actor} responds with “${text}”` : `${actor} adds a reply.`;
    case "QUOTE_POST":
      return text
        ? `${actor} reframes a prior post with “${text}”`
        : `${actor} reframes a prior post.`;
    case "REPOST":
      return text
        ? `${actor} carries forward “${text}”`
        : `${actor} carries a prior post forward.`;
    case "LIKE_POST":
    case "LIKE_COMMENT":
    case "UPVOTE_POST":
      return `${actor} applies a positive reaction to another generated contribution.`;
    case "DISLIKE_POST":
    case "DISLIKE_COMMENT":
    case "DOWNVOTE_POST":
      return `${actor} applies a negative reaction to another generated contribution.`;
    case "FOLLOW":
      return target
        ? `${actor} follows ${target} inside the generated network.`
        : `${actor} follows another generated profile inside the run.`;
    case "SEARCH_POSTS":
    case "SEARCH_USER":
      return text
        ? `${actor} searches the generated channel for “${text}”`
        : `${actor} searches for more information inside the run.`;
    case "DO_NOTHING":
      return `${actor} records no action during this round.`;
    default:
      return text
        ? `${actor} adds “${text}”`
        : `${actor} records a generated action.`;
  }
};

const chronologicalActions = computed(() =>
  props.actions
    .map((action, index) => ({ action, index }))
    .sort((left, right) => {
      const roundDifference =
        Number(left.action?.round_num || 0) -
        Number(right.action?.round_num || 0);
      if (roundDifference) return roundDifference;

      const timeDifference = String(left.action?.timestamp || "").localeCompare(
        String(right.action?.timestamp || ""),
      );
      return timeDifference || left.index - right.index;
    }),
);

const recordItems = computed(() =>
  chronologicalActions.value.map(({ action, index }, recordIndex) => ({
    id:
      action?._uniqueId ||
      action?.id ||
      `record-${action?.platform || "mixed"}-${action?.round_num || 0}-${index}`,
    sequence: String(recordIndex + 1).padStart(2, "0"),
    roundLabel: action?.round_num ? `Round ${action.round_num}` : "Round unavailable",
    channel: channelLabel(action?.platform),
    actor: cleanText(action?.agent_name, 48) || "Generated profile",
    text: describeAction(action),
  })),
);

const recordState = computed(() => {
  if (hasRunError.value) return "error";
  if (hasCompleted.value) return "complete";
  if (isRunning.value && recordItems.value.length === 0) return "loading";
  if (recordItems.value.length > 0) return "active";
  return "empty";
});

const recentNotes = computed(() =>
  props.systemLogs
    .slice(-8)
    .map((note) => cleanText(note?.msg || note, 180))
    .filter(Boolean)
    .reverse(),
);

const readinessLabel = computed(() => {
  if (!props.preflight) return "Not available";
  if (props.preflight.status === "failed") {
    const count = props.preflight.failed_checks?.length || 0;
    return count ? `${count} checks need attention` : "Needs attention";
  }
  return "Ready";
});

const formatDecimal = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(2) : "Not available";
};

const handleDetailsToggle = (event) => {
  if (
    event.currentTarget.open &&
    props.canReview &&
    !props.metrics &&
    !props.metricsLoading
  ) {
    emit("load-metrics");
  }
};
</script>

<style scoped>
.run-wayfinder {
  min-width: 0;
  min-height: 100%;
  overflow-x: clip;
  background: var(--ink-deep);
  color: var(--paper);
  font-family: var(--font-sans);
}

.run-hero {
  padding: 1.5rem 1rem 0;
  border-bottom: 1px solid var(--line-dark);
}

.run-kicker,
.section-index {
  display: block;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.78rem;
  letter-spacing: 0.075em;
  line-height: 1;
  text-transform: uppercase;
}

.run-hero h2,
.decision-band h3,
.record-heading h3,
.validation-handoff h3 {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 400;
  letter-spacing: 0.005em;
}

.run-hero h2 {
  max-width: 15ch;
  margin-top: 0.6rem;
  font-size: clamp(3rem, 16vw, 4.8rem);
  line-height: 0.88;
}

.run-hero-copy > p {
  max-width: 60ch;
  margin: 0.9rem 0 1.5rem;
  color: var(--paper-muted);
  font-size: 0.9rem;
  line-height: 1.5;
}

.run-truth-boundary {
  display: grid;
  margin: 0 -1rem;
  border-top: 1px solid var(--line-dark);
  background: var(--ink-soft);
}

.run-truth-boundary span {
  padding: 0.72rem 1rem;
  border-bottom: 1px solid var(--line-dark);
  color: var(--paper);
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.run-truth-boundary span:nth-child(3) {
  background: var(--signal);
  color: var(--ink-deep);
}

.decision-band {
  display: grid;
  gap: 1.5rem;
  margin: 1rem;
  padding: 1.2rem;
  border: 1px solid var(--paper);
  background: var(--ink-soft);
  box-shadow: 0.42rem 0.42rem 0 var(--signal-deep);
}

.decision-band h3 {
  max-width: 28ch;
  margin-top: 0.55rem;
  font-size: clamp(2rem, 10vw, 3.6rem);
  line-height: 0.95;
}

.run-progress {
  min-width: 0;
  padding-top: 1rem;
  border-top: 1px solid var(--line-light);
}

.progress-heading {
  display: flex;
  gap: 1rem;
  align-items: baseline;
  justify-content: space-between;
  font-size: 0.74rem;
}

.progress-heading span,
.run-progress small {
  color: var(--paper-muted);
}

.progress-heading strong {
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 400;
}

.progress-track {
  height: 0.5rem;
  margin-top: 0.75rem;
  overflow: hidden;
  border: 1px solid var(--line-dark);
  background: var(--ink-raised);
}

.progress-track span {
  display: block;
  width: 100%;
  height: 100%;
  transform: scaleX(0);
  transform-origin: left;
  background: var(--signal);
  transition: transform 180ms var(--ease-out);
}

.run-progress small {
  display: block;
  margin-top: 0.5rem;
  font-size: 0.66rem;
  line-height: 1.45;
}

.run-record {
  padding: 2rem 1rem;
}

.record-heading {
  display: grid;
  gap: 1.2rem;
  margin-bottom: 1.5rem;
}

.record-heading h3 {
  max-width: 17ch;
  margin-top: 0.5rem;
  font-size: clamp(2.35rem, 12vw, 4.5rem);
  line-height: 0.9;
}

.record-heading p {
  max-width: 64ch;
  margin: 0.8rem 0 0;
  color: var(--paper-muted);
  font-size: 0.84rem;
  line-height: 1.55;
}

.record-status {
  display: inline-grid;
  grid-template-columns: auto 1fr;
  gap: 0.55rem;
  align-items: center;
  justify-self: start;
  min-height: 2.75rem;
  padding: 0.45rem 0.7rem 0.45rem 0.45rem;
  border: 1px solid var(--line-dark);
  color: var(--paper-muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.record-status b {
  display: grid;
  min-width: 2.5rem;
  min-height: 1.8rem;
  place-items: center;
  background: var(--ink-raised);
  color: var(--signal);
  font-family: var(--font-mono);
  font-size: 0.65rem;
}

.record-status.is-error {
  border-color: var(--error);
  color: #e7aaa0;
}

.record-status.is-complete {
  border-color: var(--paper-muted);
  color: var(--paper);
}

.record-status.is-running {
  border-color: var(--signal);
  color: var(--signal);
}

.record-state {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 1rem;
  align-items: start;
  padding: 1.25rem;
  border: 1px solid var(--paper);
  background: var(--ink-soft);
}

.record-state.is-error {
  border-color: var(--error);
}

.state-code {
  display: grid;
  min-width: 3.2rem;
  min-height: 3.2rem;
  place-items: center;
  background: var(--signal);
  color: var(--ink-deep);
  font-family: var(--font-display);
  font-size: 1.1rem;
}

.record-state.is-error .state-code {
  background: var(--error);
  color: var(--paper);
}

.record-state strong {
  font-family: var(--font-display);
  font-size: 1.55rem;
  font-weight: 400;
  line-height: 1;
}

.record-state p {
  max-width: 62ch;
  margin: 0.5rem 0 0;
  color: var(--paper-muted);
  font-size: 0.78rem;
  line-height: 1.5;
}

.record-state button,
.review-button,
.live-update-alert button,
.run-capability-note button,
.load-patterns,
.detail-error button {
  min-height: 2.75rem;
  padding: 0.65rem 0.85rem;
  border: 1px solid currentColor;
  border-radius: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-weight: 800;
}

.record-state button {
  grid-column: 2;
  justify-self: start;
}

.record-layout {
  display: grid;
  gap: 1.5rem;
}

.record-ledger {
  min-width: 0;
  border: 1px solid var(--paper);
}

.record-list-heading {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  align-items: baseline;
  justify-content: space-between;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--paper);
  background: var(--paper);
  color: var(--ink-deep);
}

.record-list-heading span {
  font-family: var(--font-display);
  font-size: 1.2rem;
  text-transform: uppercase;
}

.record-list-heading strong {
  font-family: var(--font-mono);
  font-size: 0.64rem;
  text-transform: uppercase;
}

.run-record-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.run-record-list > li {
  display: grid;
  grid-template-columns: 3.3rem minmax(0, 1fr);
  border-bottom: 1px solid var(--line-dark);
}

.run-record-list > li:last-child {
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

.run-record-list article {
  min-width: 0;
  padding: 1rem;
}

.run-record-list header {
  display: grid;
  gap: 0.22rem;
}

.run-record-list header span,
.run-record-list footer {
  color: var(--paper-dim);
  font-family: var(--font-mono);
  font-size: 0.62rem;
  letter-spacing: 0.025em;
  text-transform: uppercase;
}

.run-record-list header strong {
  font-size: 0.82rem;
}

.run-record-list p {
  margin: 0.7rem 0;
  color: var(--paper);
  font-size: 0.82rem;
  line-height: 1.52;
}

.meaning-boundary {
  align-self: start;
  padding: 1.25rem;
  border: 1px solid var(--signal);
  background: var(--ink-soft);
}

.meaning-boundary h4 {
  margin: 0.55rem 0 1rem;
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 400;
  line-height: 0.92;
}

.meaning-boundary dl {
  margin: 0;
}

.meaning-boundary dl > div {
  padding: 0.85rem 0;
  border-top: 1px solid var(--line-dark);
}

.meaning-boundary dt {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.9rem;
  text-transform: uppercase;
}

.meaning-boundary dd {
  margin: 0.3rem 0 0;
  color: var(--paper-muted);
  font-size: 0.75rem;
  line-height: 1.45;
}

.meaning-boundary > p {
  margin: 1rem -1.25rem -1.25rem;
  padding: 0.85rem 1.25rem;
  background: var(--signal);
  color: var(--ink-deep);
  font-size: 0.72rem;
  font-weight: 800;
  line-height: 1.45;
}

.validation-handoff {
  display: grid;
  gap: 1rem;
  padding: 1.5rem 1rem;
  background: var(--signal);
  color: var(--ink-deep);
}

.validation-handoff .section-index {
  color: var(--ink-deep);
}

.handoff-index {
  font-family: var(--font-display);
  font-size: 3.5rem;
  line-height: 0.8;
}

.validation-handoff h3 {
  margin-top: 0.35rem;
  font-size: clamp(2rem, 10vw, 3.5rem);
  line-height: 0.92;
}

.validation-handoff p {
  max-width: 58ch;
  margin: 0.65rem 0 0;
  font-size: 0.8rem;
  line-height: 1.5;
}

.review-button {
  width: 100%;
  border-color: var(--ink-deep);
  background: var(--ink-deep);
  color: var(--paper);
}

.review-button:disabled {
  opacity: 0.55;
}

.handoff-error {
  display: grid;
  gap: 0.2rem;
  margin-top: 0.8rem;
  padding: 0.75rem;
  border-left: 0.35rem solid var(--error);
  background: var(--paper);
  color: #612b26;
  font-size: 0.76rem;
}

.live-update-alert,
.run-capability-note {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: stretch;
  margin: 1rem;
  padding: 0.8rem;
  border: 1px solid var(--line-dark);
  color: var(--paper-muted);
  font-size: 0.74rem;
}

.live-update-alert strong {
  color: var(--signal);
}

.run-details {
  margin: 1.5rem 1rem 0;
  border-top: 1px solid var(--line-dark);
}

.run-details summary {
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  min-height: 3.5rem;
  padding: 0.8rem 0;
  cursor: pointer;
  list-style: none;
}

.run-details summary::-webkit-details-marker {
  display: none;
}

.run-details summary span,
.run-details summary strong,
.run-details summary small {
  display: block;
}

.run-details summary strong {
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 400;
}

.run-details summary small {
  margin-top: 0.2rem;
  color: var(--paper-dim);
  font-size: 0.66rem;
}

.run-details summary > b {
  display: grid;
  width: 2.25rem;
  height: 2.25rem;
  place-items: center;
  background: var(--signal);
  color: var(--ink-deep);
  font-family: var(--font-display);
  font-size: 1.5rem;
  transition: transform 160ms var(--ease-out);
}

.run-details[open] summary > b {
  transform: rotate(45deg);
}

.details-grid {
  display: grid;
  border-top: 1px solid var(--line-dark);
}

.detail-section {
  display: grid;
  grid-template-columns: 2.1rem minmax(0, 1fr);
  gap: 0.9rem;
  min-width: 0;
  padding: 1.2rem 0;
  border-bottom: 1px solid var(--line-dark);
}

.detail-number {
  color: var(--signal);
  font-family: var(--font-display);
}

.detail-section h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 400;
}

.detail-section > div > p {
  max-width: 52ch;
  margin: 0.4rem 0 1rem;
  color: var(--paper-muted);
  font-size: 0.74rem;
  line-height: 1.45;
}

.readiness-list,
.pattern-list {
  margin: 0;
}

.readiness-list > div,
.pattern-list > div {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.3rem 1rem;
  align-items: baseline;
  padding: 0.7rem 0;
  border-top: 1px solid var(--line-dark);
}

.readiness-list dt,
.pattern-list dt {
  color: var(--paper-muted);
  font-size: 0.72rem;
}

.readiness-list dd,
.pattern-list dd {
  margin: 0;
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 1.1rem;
}

.pattern-list small {
  grid-column: 1 / -1;
  color: var(--paper-dim);
  font-size: 0.64rem;
}

.process-notes {
  max-height: 18rem;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.process-notes li {
  padding: 0.7rem 0;
  border-top: 1px solid var(--line-dark);
  color: var(--paper-muted);
  font-size: 0.72rem;
  line-height: 1.45;
}

.detail-empty,
.detail-error,
.detail-loading {
  padding: 0.8rem;
  border-left: 0.25rem solid var(--line-dark);
  background: var(--ink-soft);
  color: var(--paper-muted);
  font-size: 0.72rem;
}

.detail-error {
  border-left-color: var(--error);
  color: #e7aaa0;
}

.detail-error p {
  margin: 0;
}

.detail-loading {
  display: flex;
  gap: 0.6rem;
  align-items: center;
}

.detail-loading span {
  color: var(--signal);
  font-family: var(--font-mono);
}

.load-patterns,
.detail-error button {
  background: transparent;
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
  .run-hero {
    padding: clamp(2rem, 5vw, 4rem) clamp(1.5rem, 4vw, 4rem) 0;
  }

  .run-hero h2 {
    font-size: clamp(4rem, 7vw, 6.6rem);
  }

  .run-truth-boundary {
    grid-template-columns: repeat(5, minmax(0, 1fr));
    margin: 0 calc(clamp(1.5rem, 4vw, 4rem) * -1);
  }

  .run-truth-boundary span {
    display: grid;
    min-height: 3.6rem;
    align-items: center;
    border-right: 1px solid var(--line-dark);
    border-bottom: 0;
  }

  .decision-band {
    grid-template-columns: minmax(0, 1.6fr) minmax(16rem, 0.7fr);
    gap: clamp(2rem, 5vw, 5rem);
    align-items: center;
    margin: clamp(1.5rem, 3vw, 2.5rem);
    padding: clamp(1.5rem, 3vw, 2.4rem);
  }

  .run-progress {
    align-self: stretch;
    display: grid;
    align-content: center;
    padding: 0 0 0 clamp(1.25rem, 3vw, 2.5rem);
    border-top: 0;
    border-left: 1px solid var(--line-light);
  }

  .run-record {
    padding: clamp(2rem, 4vw, 4rem) clamp(1.5rem, 3vw, 2.5rem);
  }

  .record-heading {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 2rem;
    align-items: end;
  }

  .record-layout {
    grid-template-columns: minmax(0, 1.55fr) minmax(18rem, 0.65fr);
    align-items: start;
  }

  .meaning-boundary {
    position: sticky;
    top: 1rem;
  }

  .validation-handoff {
    grid-template-columns: 3.5rem minmax(0, 1fr) auto;
    gap: 1.5rem;
    align-items: center;
    width: min(96%, 82rem);
    padding: 1.6rem clamp(1.5rem, 3vw, 2.8rem);
    clip-path: polygon(0 0, 97% 0, 100% 100%, 0 100%);
  }

  .review-button {
    width: auto;
    min-width: 12rem;
  }

  .live-update-alert,
  .run-capability-note {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    margin-right: clamp(1.5rem, 3vw, 2.5rem);
    margin-left: clamp(1.5rem, 3vw, 2.5rem);
  }

  .run-details {
    margin: clamp(1.5rem, 3vw, 2.75rem) clamp(1.5rem, 3vw, 2.5rem) 0;
  }

  .details-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .detail-section {
    padding: 1.5rem;
    border-right: 1px solid var(--line-dark);
  }

  .detail-section:nth-child(even) {
    border-right: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .progress-track span,
  .run-details summary > b {
    transition: none;
  }
}

@media (forced-colors: active) {
  .run-truth-boundary span:nth-child(3),
  .state-code,
  .meaning-boundary > p,
  .validation-handoff {
    border: 1px solid CanvasText;
  }
}
</style>
