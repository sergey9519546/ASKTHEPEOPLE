<template>
  <section class="activity-inspector" aria-label="Selected generated record" data-testid="activity-inspector">
    <header>
      <div>
        <span class="section-index">Selected record / generated</span>
        <h4 ref="heading" tabindex="-1">Inspect recorded activity</h4>
      </div>
      <button type="button" @click="$emit('close')">Close inspection</button>
    </header>
    <p>This copy stays fixed while new activity arrives. It is not a human finding.</p>
    <dl>
      <div v-for="field in fields" :key="field.label">
        <dt>{{ field.label }}</dt>
        <dd>{{ field.value }}</dd>
      </div>
    </dl>
    <h5>Recorded public text</h5>
    <p class="public-text" data-testid="inspected-public-text">{{ publicText }}</p>
    <h5>Explicit references</h5>
    <dl v-if="references.length">
      <div v-for="reference in references" :key="reference.label">
        <dt>{{ reference.label }}</dt>
        <dd>{{ reference.value }}</dd>
      </div>
    </dl>
    <p v-else>Not recorded.</p>
    <p class="inspection-boundary">References identify recorded targets only; they do not establish causation or source support.</p>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";

const props = defineProps({ record: { type: Object, required: true } });
defineEmits(["close"]);
const heading = ref(null);
const scalar = (value) =>
  (typeof value === "string" && value.trim()) ||
  (typeof value === "number" && Number.isFinite(value))
    ? String(value)
    : "Not recorded";
const fields = computed(() => [
  { label: "Actor", value: scalar(props.record.agent_name) },
  { label: "Actor reference", value: scalar(props.record.agent_id) },
  { label: "Channel", value: scalar(props.record.platform) },
  { label: "Round", value: scalar(props.record.round_num) },
  { label: "Recorded timestamp", value: scalar(props.record.timestamp) },
  { label: "Action", value: scalar(props.record.action_type) },
  {
    label: props.record._identitySource === "server" ? "Server record reference" : "Local display reference (not a server ID)",
    value: scalar(props.record._identitySource === "server" ? props.record.id : props.record._uniqueId),
  },
]);
const publicText = computed(() => {
  const args = props.record.action_args || {};
  return ["content", "quote_content", "original_content", "post_content", "comment_content", "text"]
    .map((key) => args[key])
    .find((value) => typeof value === "string" && value.trim()) || "Not recorded.";
});
const references = computed(() => {
  const args = props.record.action_args || {};
  return ["post_id", "tweet_id", "comment_id", "target_user_id", "target_agent_id", "parent_id"]
    .filter((key) => scalar(args[key]) !== "Not recorded")
    .map((key) => ({ label: key.replaceAll("_", " "), value: scalar(args[key]) }));
});
watch(() => props.record._uniqueId, async () => {
  await nextTick();
  heading.value?.focus({ preventScroll: true });
}, { immediate: true });
</script>

<style scoped>
.activity-inspector {
  min-width: 0;
  padding: 1.25rem;
  border: 1px solid var(--line-structural);
  border-top: 3px solid var(--signal);
  background: var(--ink-raised);
  color: var(--paper);
  overflow-wrap: anywhere;
}
header { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 1rem; }
h4 { margin: 0.4rem 0; font-family: var(--font-display); font-size: 1.6rem; }
h5 { margin: 1.25rem 0 0.5rem; font-size: 1rem; }
p, dd { line-height: 1.6; }
dl { display: grid; gap: 0.75rem; margin: 1rem 0; }
dl > div { min-width: 0; border-bottom: 1px solid var(--line-dark); padding-bottom: 0.5rem; }
dt { font-size: 0.8rem; color: var(--paper-muted); }
dd { margin: 0.25rem 0 0; }
.public-text { white-space: pre-wrap; }
button { min-height: 44px; padding: 0.6rem 0.85rem; border: 1px solid var(--line-structural); background: var(--ink); color: var(--paper); cursor: pointer; }
button:focus-visible, h4:focus-visible { outline: 3px solid var(--attention); outline-offset: 3px; }
.inspection-boundary { border-top: 1px solid var(--line-structural); padding-top: 1rem; }
@media (forced-colors: active) {
  .activity-inspector, button, .inspection-boundary { border-color: CanvasText; }
  button:focus-visible, h4:focus-visible { outline-color: Highlight; }
}
</style>
