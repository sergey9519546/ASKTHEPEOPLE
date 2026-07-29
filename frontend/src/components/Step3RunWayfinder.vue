<template>
  <section class="run-wayfinder" aria-labelledby="run-wayfinder-title">
    <header class="run-hero">
      <div class="run-hero-copy">
        <span class="run-kicker">03 / Map the scenarios</span>
        <h2 id="run-wayfinder-title">{{ runHeadline }}</h2>
        <p>{{ runDeck }}</p>
      </div>

      <div
        class="truth-stamp"
        aria-label="0 human respondents. Synthetic observations. Not a forecast."
      >
        <span class="truth-number">0</span>
        <span>
          <strong>human respondents</strong>
          <small>Synthetic observations · not a forecast</small>
        </span>
      </div>
    </header>

    <section class="decision-band" aria-labelledby="decision-heading">
      <div class="decision-copy">
        <span class="section-index">The decision</span>
        <h3 id="decision-heading">{{ decisionQuestion }}</h3>
      </div>

      <div
        class="route-progress"
        role="progressbar"
        aria-label="Scenario run progress"
        :aria-valuemin="0"
        :aria-valuemax="totalRounds || 1"
        :aria-valuenow="currentRound"
        :aria-valuetext="progressText"
      >
        <div class="progress-heading">
          <span>{{ progressLabel }}</span>
          <strong>{{ progressText }}</strong>
        </div>
        <div class="progress-track" aria-hidden="true">
          <span :style="{ transform: `scaleX(${progressRatio})` }"></span>
        </div>
      </div>
    </section>

    <div
      v-if="startError || hasFailed"
      class="run-alert"
      role="alert"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 3 2.8 20h18.4L12 3Z" />
        <path d="M12 9v5M12 17.2v.1" />
      </svg>
      <div>
        <strong>This run needs attention.</strong>
        <p>{{ startError || runStatus.error || "The saved run did not finish." }}</p>
        <button
          type="button"
          @click="$emit(startError ? 'retry-run' : 'start-over')"
        >
          {{ startError ? "Try again" : "Return to assumptions" }}
        </button>
      </div>
    </div>

    <section class="route-board" aria-labelledby="routes-heading">
      <div class="route-board-heading">
        <div>
          <span class="section-index">Activity in this run</span>
          <h3 id="routes-heading">{{ routesHeading }}</h3>
          <p>
            These are model-generated channel streams under the chosen
            assumptions. They show activity inside this run, not causal paths
            or what people will do.
          </p>
        </div>

        <span class="plain-status" :class="`is-${statusTone}`" aria-live="polite">
          <i aria-hidden="true"></i>
          {{ statusLabel }}
        </span>
      </div>

      <div class="route-map">
        <div class="route-origin" aria-hidden="true">
          <span></span>
        </div>

        <div class="route-lanes">
          <article
            v-for="(lane, laneIndex) in routeLanes"
            :key="lane.id"
            class="route-lane"
            :class="[`route-${lane.id}`, { 'is-waiting': lane.isWaiting }]"
          >
            <header>
              <span>Generated channel {{ String(laneIndex + 1).padStart(2, "0") }}</span>
              <h4>{{ lane.title }}</h4>
              <p>{{ lane.summary }}</p>
            </header>

            <div
              class="route-line"
              :style="{ '--route-step-count': lane.steps.length }"
              aria-hidden="true"
            >
              <span class="route-stroke"></span>
              <i
                v-for="step in lane.steps"
                :key="step.id"
                class="route-node"
              ></i>
            </div>

            <ol
              class="route-steps"
              :style="{ '--route-step-count': lane.steps.length }"
            >
              <li v-for="step in lane.steps" :key="step.id">
                <span>{{ step.label }}</span>
                <p>{{ step.text }}</p>
              </li>
            </ol>
          </article>
        </div>

        <aside class="validation-destination">
          <svg viewBox="0 0 48 48" aria-hidden="true">
            <circle cx="16" cy="17" r="6" />
            <circle cx="32" cy="17" r="6" />
            <path d="M5 39c1.2-8 7-12 13-12s11.8 4 13 12M22 39c1-6.4 5.6-10 11-10 5.3 0 9.8 3.6 10 10" />
          </svg>
          <span>Next stop</span>
          <strong>Validate with people</strong>
          <p>Turn the strongest assumptions and tensions into questions for real conversations.</p>
        </aside>
      </div>

      <div v-if="isWaitingForSignals" class="route-waiting" aria-live="polite">
        <span class="route-waiting-mark" aria-hidden="true"></span>
        <p>
          <strong>The first activity stream is being recorded.</strong>
          Generated observations will appear here as the run moves forward.
        </p>
      </div>
    </section>

    <section class="validation-handoff" aria-labelledby="handoff-heading">
      <svg class="handoff-arrow" viewBox="0 0 56 56" aria-hidden="true">
        <path d="M5 28h39M31 14l14 14-14 14" />
      </svg>
      <div>
        <span class="section-index">Make the next move human</span>
        <h3 id="handoff-heading">Review the activity. Challenge the assumptions.</h3>
        <p>
          The decision brief turns this synthetic activity into possible paths,
          questions, and source gaps to test with affected people.
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
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M5 12h13M13 6l6 6-6 6" />
        </svg>
      </button>
    </section>

    <div
      v-if="liveUpdateError && isRunning"
      class="live-update-alert"
      role="status"
      aria-live="polite"
    >
      <span>
        <strong>Live updates are disconnected.</strong>
        The run may still be continuing.
      </span>
      <button type="button" @click="$emit('reconnect')">Reconnect</button>
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
          <strong>Run details</strong>
          <small>Readiness, generated activity, and interaction summary</small>
        </span>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="m6 9 6 6 6-6" />
        </svg>
      </summary>

      <div class="details-grid">
        <section class="detail-section" aria-labelledby="readiness-heading">
          <span class="detail-number">01</span>
          <div>
            <h3 id="readiness-heading">Before the run</h3>
            <p>What was ready when this scenario started.</p>
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
            <h3 id="activity-heading">Generated activity</h3>
            <p>
              A plain-language record of model-generated actions. No human
              behavior was observed.
            </p>
            <ol v-if="detailActions.length" class="detail-activity">
              <li v-for="item in detailActions" :key="item.id">
                <span>{{ item.channel }}</span>
                <p>{{ item.text }}</p>
              </li>
            </ol>
            <p v-else class="detail-empty">No generated activity is available yet.</p>
          </div>
        </section>

        <section class="detail-section" aria-labelledby="patterns-heading">
          <span class="detail-number">03</span>
          <div>
            <h3 id="patterns-heading">Interaction summary</h3>
            <p>
              Descriptive patterns inside this synthetic run. They are not
              population measurements.
            </p>

            <div v-if="metricsLoading" class="detail-loading" aria-live="polite">
              <span></span>
              Reading the generated interaction record…
            </div>
            <div v-else-if="metricsError" class="detail-error">
              <p>{{ metricsError }}</p>
              <button type="button" @click="$emit('load-metrics')">Try again</button>
            </div>
            <dl v-else-if="metrics" class="pattern-list">
              <div>
                <dt>Conversation clustering</dt>
                <dd>{{ formatDecimal(metrics.polarization_index) }}</dd>
                <small>Network modularity inside this run</small>
              </div>
              <div>
                <dt>Activity concentration</dt>
                <dd>{{ formatDecimal(metrics.engagement_gini) }}</dd>
                <small>0 is even; 1 is concentrated</small>
              </div>
              <div>
                <dt>Within-group interaction</dt>
                <dd>{{ formatPercent(metrics.echo_chamber_score) }}</dd>
                <small>Share of generated interactions</small>
              </div>
            </dl>
            <button
              v-else
              class="load-patterns"
              type="button"
              :disabled="!canReview"
              @click="$emit('load-metrics')"
            >
              {{ canReview ? "Load interaction summary" : "Available after the run" }}
            </button>
          </div>
        </section>

        <section class="detail-section" aria-labelledby="notes-heading">
          <span class="detail-number">04</span>
          <div>
            <h3 id="notes-heading">Process notes</h3>
            <p>Recent plain-language updates from this run.</p>
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
const hasCompleted = computed(
  () => props.phase === 2 && !hasFailed.value,
);
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
  return "Preparing the activity map.";
});

const runDeck = computed(() => {
  if (hasFailed.value) {
    return "Keep the partial observations, inspect what stopped, and decide whether to begin a new run.";
  }
  if (hasCompleted.value) {
    return "Compare the generated channel activity, then decide which possible paths and assumptions need real-world validation.";
  }
  return "Follow two synthetic conversation spaces as they respond to the same conditions.";
});

const totalRounds = computed(
  () => Number(props.runStatus?.total_rounds || props.maxRounds || 0),
);
const currentRound = computed(() =>
  Math.max(
    Number(props.runStatus?.current_round || 0),
    Number(props.runStatus?.twitter_current_round || 0),
    Number(props.runStatus?.reddit_current_round || 0),
  ),
);
const progressRatio = computed(() => {
  if (hasCompleted.value) return 1;
  if (!totalRounds.value) return 0;
  return Math.max(0, Math.min(1, currentRound.value / totalRounds.value));
});
const progressText = computed(() => {
  if (hasCompleted.value) return "Run complete";
  if (!totalRounds.value) return "Waiting to begin";
  return `Round ${currentRound.value} of ${totalRounds.value}`;
});
const progressLabel = computed(() => {
  if (hasFailed.value) return "Run stopped";
  if (hasCompleted.value) return "Activity recorded";
  if (isRunning.value) return "Run in progress";
  return "Getting ready";
});

const statusLabel = computed(() => {
  if (hasFailed.value) return "Needs attention";
  if (hasCompleted.value) return "Ready to review";
  if (isRunning.value) return "Activity unfolding";
  return "Waiting to start";
});
const statusTone = computed(() => {
  if (hasFailed.value) return "error";
  if (hasCompleted.value) return "complete";
  if (isRunning.value) return "running";
  return "waiting";
});

const routesHeading = computed(() =>
  hasCompleted.value
    ? "What happened inside the generated channels"
    : "What is happening inside the generated channels",
);

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

const cleanText = (value, limit = 150) => {
  const normalized = String(value || "").replace(/\s+/g, " ").trim();
  if (!normalized) return "";
  return normalized.length > limit
    ? `${normalized.slice(0, limit - 1).trim()}…`
    : normalized;
};

const describeAction = (action) => {
  const actor = cleanText(action?.agent_name, 48) || "A generated profile";
  const text = cleanText(actionText(action));
  const target =
    cleanText(action?.action_args?.target_user_name, 48) ||
    cleanText(action?.action_args?.post_author_name, 48);

  switch (action?.action_type) {
    case "CREATE_POST":
      return text ? `${actor} introduces “${text}”` : `${actor} introduces a new post.`;
    case "CREATE_COMMENT":
      return text ? `${actor} responds with “${text}”` : `${actor} joins a discussion.`;
    case "QUOTE_POST":
      return text ? `${actor} reframes the discussion with “${text}”` : `${actor} reframes an earlier post.`;
    case "REPOST":
      return text ? `${actor} carries forward “${text}”` : `${actor} carries an earlier post forward.`;
    case "LIKE_POST":
    case "LIKE_COMMENT":
    case "UPVOTE_POST":
      return `${actor} signals support for another generated contribution.`;
    case "DISLIKE_POST":
    case "DISLIKE_COMMENT":
    case "DOWNVOTE_POST":
      return `${actor} signals disagreement with another generated contribution.`;
    case "FOLLOW":
      return target
        ? `${actor} follows ${target} inside the synthetic network.`
        : `${actor} follows another generated profile.`;
    case "SEARCH_POSTS":
    case "SEARCH_USER":
      return text
        ? `${actor} looks for “${text}”`
        : `${actor} looks for more information inside the run.`;
    case "DO_NOTHING":
      return `${actor} does not act during this round.`;
    default:
      return text
        ? `${actor} adds “${text}”`
        : `${actor} takes a generated action in this channel.`;
  }
};

const routeDefinitions = [
  {
    id: "short",
    platform: "twitter",
    title: "Short-post activity",
    empty: "Waiting for the first short-post signal.",
  },
  {
    id: "community",
    platform: "reddit",
    title: "Topic-community activity",
    empty: "Waiting for the first community signal.",
  },
];

const routeLanes = computed(() =>
  routeDefinitions.map((definition) => {
    const laneActions = props.actions.filter(
      (action) => action?.platform === definition.platform,
    );
    const meaningful = laneActions
      .filter((action) => action?.action_type !== "DO_NOTHING" || laneActions.length < 3)
      .slice(-3);
    const steps = meaningful.length
      ? meaningful.map((action, index) => ({
          id:
            action._uniqueId ||
            action.id ||
            `${definition.id}-${action.round_num || 0}-${index}`,
          label: action.round_num ? `Round ${action.round_num}` : `Signal ${index + 1}`,
          text: describeAction(action),
        }))
      : [
          {
            id: `${definition.id}-waiting`,
            label: isRunning.value ? "Tracing" : "No signal yet",
            text: definition.empty,
          },
        ];

    return {
      ...definition,
      steps,
      isWaiting: meaningful.length === 0,
      summary: laneActions.length
        ? `${laneActions.length} generated ${laneActions.length === 1 ? "action occurred" : "actions occurred"} in this channel.`
        : "No generated action has occurred in this channel yet.",
    };
  }),
);

const isWaitingForSignals = computed(
  () => isRunning.value && props.actions.length === 0,
);

const detailActions = computed(() =>
  props.actions.slice(-12).reverse().map((action, index) => ({
    id:
      action._uniqueId ||
      action.id ||
      `detail-${action.platform || "mixed"}-${action.round_num || 0}-${index}`,
    channel:
      action.platform === "twitter"
        ? "Short-post activity"
        : action.platform === "reddit"
          ? "Topic-community activity"
          : "Generated activity",
    text: describeAction(action),
  })),
);

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

const formatPercent = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(0)}%` : "Not available";
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
  width: 100%;
  min-height: 100%;
  overflow-x: clip;
  background: var(--ink-deep);
  color: var(--paper);
  font-family: var(--font-sans);
}

.run-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(14rem, 0.55fr);
  gap: clamp(2rem, 7vw, 6rem);
  align-items: end;
  padding: clamp(2rem, 5vw, 4.5rem) clamp(1.25rem, 4.5vw, 4.5rem) 2rem;
  border-bottom: 1px solid var(--line-dark);
  background:
    linear-gradient(115deg, rgba(229, 194, 29, 0.05), transparent 42%),
    var(--ink-deep);
}

.run-kicker,
.section-index,
.validation-destination > span,
.route-lane > header > span {
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
.route-board-heading h3,
.validation-handoff h3 {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 400;
  letter-spacing: 0.005em;
}

.run-hero h2 {
  max-width: 15ch;
  margin-top: 0.65rem;
  font-size: clamp(3.15rem, 7vw, 6.7rem);
  line-height: 0.88;
}

.run-hero-copy > p {
  max-width: 58ch;
  margin: 1rem 0 0;
  color: var(--paper-muted);
  font-size: clamp(1rem, 1.4vw, 1.2rem);
  line-height: 1.55;
}

.truth-stamp {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.8rem;
  align-items: center;
  padding: 1rem 0;
  border-top: 1px solid var(--paper-muted);
  border-bottom: 1px solid var(--paper-muted);
}

.truth-number {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 4.25rem;
  line-height: 0.8;
}

.truth-stamp strong,
.truth-stamp small {
  display: block;
}

.truth-stamp strong {
  font-size: 0.9rem;
  font-weight: 700;
}

.truth-stamp small {
  margin-top: 0.22rem;
  color: var(--paper-muted);
  font-size: 0.72rem;
  line-height: 1.35;
}

.decision-band {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(16rem, 0.75fr);
  gap: clamp(2rem, 5vw, 5rem);
  align-items: center;
  margin: clamp(1.25rem, 3vw, 2.5rem);
  padding: clamp(1.4rem, 3vw, 2.35rem);
  background: var(--paper);
  color: var(--ink);
  box-shadow: 0.65rem 0.65rem 0 var(--signal-deep);
}

.decision-band .section-index {
  color: var(--signal-deep);
}

.decision-band h3 {
  max-width: 26ch;
  margin-top: 0.55rem;
  font-size: clamp(2rem, 4vw, 4.1rem);
  line-height: 0.97;
}

.route-progress {
  align-self: stretch;
  display: grid;
  align-content: center;
  padding-left: clamp(1.25rem, 3vw, 2.5rem);
  border-left: 1px solid var(--line-light);
}

.progress-heading {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: baseline;
  font-size: 0.76rem;
}

.progress-heading span {
  color: var(--ink-muted);
  font-weight: 600;
}

.progress-heading strong {
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 400;
}

.progress-track {
  height: 0.55rem;
  margin-top: 0.75rem;
  overflow: hidden;
  border: 1px solid var(--ink);
  background: var(--paper-strong);
}

.progress-track span {
  display: block;
  width: 100%;
  height: 100%;
  transform: scaleX(0);
  transform-origin: left;
  background: var(--signal);
  transition: transform 700ms var(--ease-out);
}

.run-alert {
  display: grid;
  grid-template-columns: 2rem 1fr;
  gap: 1rem;
  margin: 0 clamp(1.25rem, 3vw, 2.5rem) 1.5rem;
  padding: 1rem 1.2rem;
  border-left: 0.45rem solid var(--error);
  background: #ead5cf;
  color: #612b26;
}

.run-alert svg {
  width: 1.7rem;
  fill: none;
  stroke: currentColor;
  stroke-linecap: square;
  stroke-linejoin: miter;
  stroke-width: 1.8;
}

.run-alert strong {
  font-weight: 700;
}

.run-alert p {
  margin: 0.25rem 0 0;
  font-size: 0.85rem;
}

.run-alert button,
.live-update-alert button,
.run-capability-note button {
  min-height: 2.25rem;
  margin-top: 0.7rem;
  padding: 0.42rem 0.72rem;
  border: 1px solid currentColor;
  border-radius: 0;
  background: transparent;
  color: inherit;
  font-weight: 700;
}

.run-alert button:hover,
.live-update-alert button:hover,
.run-capability-note button:hover {
  background: currentColor;
  color: var(--paper);
}

.route-board {
  padding: clamp(1.5rem, 3vw, 2.75rem) clamp(1.25rem, 3vw, 2.5rem) clamp(2rem, 4vw, 4rem);
}

.route-board-heading {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 2rem;
  align-items: end;
  margin-bottom: clamp(2rem, 4vw, 3.5rem);
}

.route-board-heading h3 {
  margin-top: 0.5rem;
  font-size: clamp(2.25rem, 4.5vw, 4.6rem);
  line-height: 0.95;
}

.route-board-heading p {
  max-width: 64ch;
  margin: 0.75rem 0 0;
  color: var(--paper-muted);
  font-size: 0.88rem;
  line-height: 1.55;
}

.plain-status {
  display: inline-flex;
  gap: 0.55rem;
  align-items: center;
  min-height: 2.4rem;
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--line-dark);
  color: var(--paper-muted);
  font-size: 0.76rem;
  font-weight: 650;
}

.plain-status i {
  width: 0.62rem;
  height: 0.62rem;
  border: 1px solid currentColor;
  border-radius: 50%;
  background: currentColor;
}

.plain-status.is-running {
  border-color: var(--signal);
  color: var(--signal);
}

.plain-status.is-running i {
  animation: route-pulse 1.7s var(--ease-out) infinite;
}

.plain-status.is-complete {
  border-color: var(--paper-muted);
  color: var(--paper);
}

.plain-status.is-error {
  border-color: var(--error);
  color: #e09b91;
}

.route-map {
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr) minmax(11rem, 0.25fr);
  gap: 1.25rem;
  align-items: stretch;
}

.route-origin {
  display: grid;
  place-items: center;
  position: relative;
}

.route-origin::before {
  content: "";
  position: absolute;
  top: 25%;
  bottom: 25%;
  width: 0.22rem;
  background: var(--paper);
}

.route-origin span {
  position: relative;
  width: 1.6rem;
  height: 1.6rem;
  border: 0.28rem solid var(--paper);
  border-radius: 50%;
  background: var(--ink-deep);
}

.route-lanes {
  display: grid;
  gap: clamp(2.25rem, 5vw, 4.5rem);
  padding: 0.8rem 0 1rem;
}

.route-lane {
  min-width: 0;
}

.route-lane header {
  display: grid;
  grid-template-columns: minmax(11rem, 0.55fr) minmax(0, 1fr);
  column-gap: 1.25rem;
  align-items: baseline;
}

.route-lane header > span {
  grid-column: 1;
  color: var(--signal);
}

.route-lane h4 {
  grid-column: 1;
  margin: 0.28rem 0 0;
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 400;
  line-height: 1;
}

.route-lane header > p {
  grid-column: 2;
  grid-row: 1 / span 2;
  align-self: center;
  margin: 0;
  color: var(--paper-muted);
  font-size: 0.76rem;
}

.route-line {
  position: relative;
  display: grid;
  grid-template-columns: repeat(var(--route-step-count), minmax(0, 1fr));
  height: 2rem;
  margin-top: 0.65rem;
  align-items: center;
}

.route-stroke {
  position: absolute;
  inset: calc(50% - 0.18rem) 0 auto;
  height: 0.36rem;
  transform: scaleX(1);
  transform-origin: left;
  background: var(--signal);
  animation: trace-route 760ms var(--ease-out) both;
}

.route-community .route-stroke {
  height: 0.2rem;
  background:
    repeating-linear-gradient(
      90deg,
      var(--signal) 0 1.4rem,
      transparent 1.4rem 2rem
    );
}

.route-lane.is-waiting .route-stroke {
  opacity: 0.35;
}

.route-node {
  z-index: 1;
  justify-self: center;
  width: 1.35rem;
  height: 1.35rem;
  border: 0.27rem solid var(--signal);
  border-radius: 50%;
  background: var(--ink-deep);
}

.route-node:first-of-type {
  justify-self: start;
}

.route-node:last-of-type {
  justify-self: end;
}

.route-steps {
  display: grid;
  grid-template-columns: repeat(var(--route-step-count), minmax(0, 1fr));
  gap: clamp(0.8rem, 2vw, 2rem);
  margin: 0;
  padding: 0;
  list-style: none;
}

.route-steps li {
  min-width: 0;
}

.route-steps li:not(:first-child):not(:last-child) {
  text-align: center;
}

.route-steps li:last-child:not(:only-child) {
  text-align: right;
}

.route-steps span {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.route-steps p {
  margin: 0.35rem 0 0;
  color: var(--paper);
  font-size: clamp(0.78rem, 1.1vw, 0.9rem);
  line-height: 1.42;
}

.validation-destination {
  align-self: stretch;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  padding: 1.25rem;
  border: 1px solid var(--paper);
  background: var(--paper);
  color: var(--ink);
  box-shadow: 0.45rem 0.45rem 0 var(--signal-deep);
}

.validation-destination svg {
  width: 3rem;
  fill: none;
  stroke: var(--ink);
  stroke-linecap: square;
  stroke-linejoin: miter;
  stroke-width: 2;
}

.validation-destination > span {
  margin-top: 1rem;
  color: var(--signal-deep);
}

.validation-destination strong {
  margin-top: 0.35rem;
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 400;
  line-height: 0.95;
}

.validation-destination p {
  margin: 0.7rem 0 0;
  color: var(--ink-muted);
  font-size: 0.76rem;
  line-height: 1.45;
}

.route-waiting {
  display: flex;
  gap: 0.85rem;
  align-items: center;
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--line-dark);
}

.route-waiting-mark {
  flex: 0 0 auto;
  width: 1rem;
  height: 1rem;
  border: 0.18rem solid var(--signal);
  border-radius: 50%;
  animation: route-pulse 1.7s var(--ease-out) infinite;
}

.route-waiting p {
  margin: 0;
  color: var(--paper-muted);
  font-size: 0.8rem;
}

.route-waiting strong {
  color: var(--paper);
}

.validation-handoff {
  display: grid;
  grid-template-columns: 3.5rem minmax(0, 1fr) auto;
  gap: clamp(1.2rem, 3vw, 2.5rem);
  align-items: center;
  width: min(94%, 78rem);
  padding: clamp(1.4rem, 3vw, 2.2rem) clamp(1.2rem, 3vw, 2.8rem);
  background: var(--signal);
  color: var(--ink);
  clip-path: polygon(0 0, 96% 0, 100% 100%, 0 100%);
}

.handoff-arrow {
  width: 3.25rem;
  fill: none;
  stroke: var(--ink);
  stroke-linecap: square;
  stroke-linejoin: miter;
  stroke-width: 4;
}

.validation-handoff .section-index {
  color: var(--ink-muted);
}

.validation-handoff h3 {
  margin-top: 0.38rem;
  font-size: clamp(1.8rem, 3.2vw, 3.25rem);
  line-height: 0.98;
}

.validation-handoff p {
  max-width: 58ch;
  margin: 0.55rem 0 0;
  font-size: 0.82rem;
  line-height: 1.45;
}

.handoff-error {
  display: grid;
  gap: 0.18rem;
  margin-top: 0.75rem;
  padding: 0.65rem 0.75rem;
  border-left: 0.35rem solid var(--error);
  background: rgba(255, 255, 255, 0.58);
  color: #612b26;
  font-size: 0.78rem;
}

.handoff-error strong,
.handoff-error span {
  display: block;
}

.review-button {
  min-width: 12rem;
  min-height: 3.25rem;
  padding: 0.8rem 1rem;
  border-color: var(--ink);
  background: var(--ink);
  color: var(--paper);
  font-weight: 700;
}

.review-button:hover:not(:disabled) {
  border-color: var(--ink);
  background: var(--paper);
  color: var(--ink);
}

.review-button svg {
  width: 1.15rem;
  fill: none;
  stroke: currentColor;
  stroke-linecap: square;
  stroke-linejoin: miter;
  stroke-width: 2;
}

.run-capability-note {
  display: flex;
  gap: 0.8rem;
  align-items: center;
  justify-content: space-between;
  margin: 1rem clamp(1.25rem, 3vw, 2.5rem) 0;
  color: var(--paper-dim);
  font-size: 0.72rem;
}

.run-capability-note button {
  flex: 0 0 auto;
  margin-top: 0;
}

.live-update-alert {
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  margin: 1rem clamp(1.25rem, 3vw, 2.5rem) 0;
  padding: 0.75rem 0.9rem;
  border: 1px solid var(--signal);
  color: var(--paper);
  font-size: 0.78rem;
}

.live-update-alert strong {
  color: var(--signal);
}

.live-update-alert button {
  flex: 0 0 auto;
  margin-top: 0;
  color: var(--signal);
}

.run-details {
  margin: clamp(1.5rem, 3vw, 2.75rem) clamp(1.25rem, 3vw, 2.5rem) 0;
  border-top: 1px solid var(--line-dark);
}

.run-details summary {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 1rem 0;
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
  letter-spacing: 0.035em;
}

.run-details summary small {
  margin-top: 0.2rem;
  color: var(--paper-dim);
  font-size: 0.68rem;
}

.run-details summary svg {
  width: 1.25rem;
  fill: none;
  stroke: var(--signal);
  stroke-linecap: square;
  stroke-width: 2;
  transition: transform 240ms var(--ease-out);
}

.run-details[open] summary svg {
  transform: rotate(180deg);
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-top: 1px solid var(--line-dark);
}

.detail-section {
  display: grid;
  grid-template-columns: 2.2rem minmax(0, 1fr);
  gap: 1rem;
  min-width: 0;
  padding: clamp(1.25rem, 3vw, 2rem);
  border-right: 1px solid var(--line-dark);
  border-bottom: 1px solid var(--line-dark);
}

.detail-section:nth-child(even) {
  border-right: 0;
}

.detail-number {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 1rem;
}

.detail-section h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.55rem;
  font-weight: 400;
}

.detail-section > div > p {
  max-width: 52ch;
  margin: 0.4rem 0 1rem;
  color: var(--paper-muted);
  font-size: 0.76rem;
  line-height: 1.45;
}

.readiness-list,
.pattern-list {
  display: grid;
  margin: 0;
}

.readiness-list > div,
.pattern-list > div {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.35rem 1rem;
  align-items: baseline;
  padding: 0.7rem 0;
  border-top: 1px solid var(--line-dark);
}

.readiness-list dt,
.pattern-list dt {
  color: var(--paper-muted);
  font-size: 0.73rem;
}

.readiness-list dd,
.pattern-list dd {
  margin: 0;
  color: var(--paper);
  font-family: var(--font-display);
  font-size: 1.15rem;
}

.pattern-list small {
  grid-column: 1 / -1;
  color: var(--paper-dim);
  font-size: 0.66rem;
}

.detail-activity,
.process-notes {
  display: grid;
  gap: 0;
  max-height: 18rem;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.detail-activity li,
.process-notes li {
  padding: 0.7rem 0;
  border-top: 1px solid var(--line-dark);
}

.detail-activity span {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.detail-activity p,
.process-notes li {
  margin: 0.25rem 0 0;
  color: var(--paper-muted);
  font-size: 0.73rem;
  line-height: 1.45;
}

.detail-empty,
.detail-error,
.detail-loading {
  padding: 0.8rem;
  border-left: 0.25rem solid var(--line-dark);
  background: var(--ink-soft);
  color: var(--paper-muted);
  font-size: 0.73rem;
}

.detail-error {
  border-left-color: var(--error);
  color: #e09b91;
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
  width: 0.8rem;
  height: 0.8rem;
  border: 0.15rem solid var(--signal);
  border-radius: 50%;
  animation: route-pulse 1.7s var(--ease-out) infinite;
}

.load-patterns,
.detail-error button {
  background: transparent;
}

@keyframes trace-route {
  from {
    opacity: 0;
    transform: scaleX(0);
  }
  to {
    opacity: 1;
    transform: scaleX(1);
  }
}

@keyframes route-pulse {
  0%,
  100% {
    opacity: 0.5;
    transform: scale(0.85);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

@media (max-width: 860px) {
  .run-hero,
  .decision-band,
  .route-board-heading,
  .validation-handoff {
    grid-template-columns: 1fr;
  }

  .run-hero {
    gap: 1.5rem;
  }

  .truth-stamp {
    max-width: 24rem;
  }

  .decision-band {
    gap: 1.5rem;
  }

  .route-progress {
    padding: 1.2rem 0 0;
    border-top: 1px solid var(--line-light);
    border-left: 0;
  }

  .plain-status {
    justify-self: start;
  }

  .route-map {
    grid-template-columns: minmax(0, 1fr);
  }

  .route-origin {
    display: none;
  }

  .validation-destination {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    column-gap: 1rem;
    align-items: center;
  }

  .validation-destination svg {
    grid-row: 1 / span 3;
  }

  .validation-destination > span,
  .validation-destination strong,
  .validation-destination p {
    grid-column: 2;
    margin-top: 0;
  }

  .validation-handoff {
    width: 100%;
    clip-path: none;
  }

  .review-button {
    justify-self: start;
  }
}

@media (max-width: 620px) {
  .run-hero {
    padding: 1.5rem 1rem;
  }

  .run-hero h2 {
    font-size: clamp(3rem, 17vw, 4.7rem);
  }

  .decision-band {
    margin: 1rem;
    padding: 1.2rem;
    box-shadow: 0.38rem 0.38rem 0 var(--signal-deep);
  }

  .route-board {
    padding: 1.8rem 1rem;
  }

  .route-lane header {
    grid-template-columns: 1fr;
  }

  .route-lane header > p {
    grid-column: 1;
    grid-row: auto;
    margin-top: 0.4rem;
  }

  .route-line {
    display: none;
  }

  .route-steps {
    grid-template-columns: 1fr;
    margin-top: 1rem;
    padding-left: 1rem;
    border-left: 0.3rem solid var(--signal);
  }

  .route-steps li,
  .route-steps li:nth-child(2),
  .route-steps li:nth-child(3) {
    padding: 0.1rem 0 0.9rem;
    text-align: left !important;
  }

  .validation-handoff {
    padding: 1.5rem 1rem;
  }

  .handoff-arrow {
    width: 2.5rem;
  }

  .review-button {
    width: 100%;
  }

  .run-capability-note,
  .run-details {
    margin-right: 1rem;
    margin-left: 1rem;
  }

  .run-capability-note,
  .live-update-alert {
    align-items: stretch;
    flex-direction: column;
  }

  .run-capability-note button,
  .live-update-alert button {
    width: 100%;
  }

  .details-grid {
    grid-template-columns: 1fr;
  }

  .detail-section,
  .detail-section:nth-child(even) {
    border-right: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .route-stroke,
  .plain-status i,
  .route-waiting-mark,
  .detail-loading span {
    animation: none;
  }

  .progress-track span,
  .run-details summary svg {
    transition: none;
  }
}
</style>
