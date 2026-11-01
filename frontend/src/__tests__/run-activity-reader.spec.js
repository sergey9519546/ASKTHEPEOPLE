import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { defineComponent, nextTick } from "vue";
import Step3RunWayfinder from "../components/Step3RunWayfinder.vue";
import RunActivityInspector from "../components/RunActivityInspector.vue";
import { useRunActivity } from "../composables/useRunActivity";

const action = (id, text = `Public action ${id}`) => ({
  id, platform: "reddit", round_num: id, agent_id: 0,
  agent_name: "Generated operator", action_type: "CREATE_POST",
  timestamp: `2026-11-01T10:00:${String(id).padStart(2, "0")}`,
  action_args: { content: text, post_id: id },
});
let wrapper;
afterEach(() => { wrapper?.unmount(); document.body.innerHTML = ""; });

function mountReader() {
  let activity;
  const Harness = defineComponent({
    components: { Step3RunWayfinder },
    setup() {
      activity = useRunActivity({ limit: 2 });
      activity.mergeActions([action(1), action(2)]);
      return { ...activity };
    },
    template: `<Step3RunWayfinder :actions="displayedRecords" :activity-held="held"
      :pending-count="pendingCount" :pending-overflow="pendingOverflow" :activity-evicted="hasEvicted"
      :activity-limit="2" :selected-record="selectedRecord" :run-status="{runner_status:'running',current_round:2,total_rounds:8}"
      :phase="1" @hold-view="holdView" @show-latest="showLatest" @inspect-record="selectRecord" @close-inspector="clearSelection" />`,
  });
  wrapper = mount(Harness, { attachTo: document.body });
  return activity;
}

describe("recent activity reading controls", () => {
  it("uses a singular status label for one received record", async () => {
    const activity = mountReader();
    await wrapper.get('[data-testid="activity-toolbar"] button').trigger("click");
    activity.mergeActions([action(3)]);
    await nextTick();
    expect(wrapper.get('[data-testid="activity-held-status"]').text()).toContain(
      "1 newer entry received.",
    );
  });

  it("holds the displayed rows while bounded updates continue", async () => {
    const activity = mountReader();
    await wrapper.get('[data-testid="activity-toolbar"] button').trigger("click");
    activity.mergeActions([action(3), action(4), action(5)]);
    await nextTick();
    const list = wrapper.get('[data-testid="run-record-list"]');
    expect(list.text()).toContain("Public action 1");
    expect(list.text()).not.toContain("Public action 5");
    expect(wrapper.get('[data-testid="activity-held-status"]').text()).toContain("2+");
    expect(wrapper.get('[data-testid="activity-overflow"]').text()).toContain("not every intervening action");
    expect(wrapper.text()).toContain("Holding this view does not pause the run.");
    await wrapper.get('[data-testid="activity-toolbar"] button').trigger("click");
    expect(list.text()).toContain("Public action 5");
    expect(list.text()).not.toContain("Public action 1");
  });

  it("keeps a selected public copy and returns focus to its row", async () => {
    const activity = mountReader();
    const button = wrapper.get('button[aria-label="Inspect recorded activity 01"]');
    await button.trigger("click");
    await nextTick();
    expect(document.activeElement.textContent).toBe("Inspect recorded activity");
    activity.mergeActions([action(2, "Changed snapshot")]);
    await nextTick();
    expect(wrapper.get('[data-testid="inspected-public-text"]').text()).toBe("Public action 1");
    await wrapper.get('[data-testid="activity-inspector"] button').trigger("click");
    await nextTick();
    expect(document.activeElement).toBe(button.element);
    expect(wrapper.find('[data-testid="activity-inspector"]').exists()).toBe(false);
  });

  it("keeps inspection across eviction and returns focus to the toolbar", async () => {
    const activity = mountReader();
    await wrapper.get('button[aria-label="Inspect recorded activity 01"]').trigger("click");
    activity.mergeActions([action(3), action(4)]);
    await nextTick();
    expect(wrapper.get('[data-testid="inspected-public-text"]').text()).toBe("Public action 1");
    await wrapper.get('[data-testid="activity-inspector"] button').trigger("click");
    await nextTick();
    expect(document.activeElement).toBe(wrapper.get('[data-testid="activity-toolbar"] button').element);
  });

  it("preserves recorded rows and inspection when the run fails", async () => {
    wrapper = mount(Step3RunWayfinder, {
      props: { actions: [action(1)], selectedRecord: { ...action(1), _uniqueId: "activity-1", _identitySource: "server" },
        runStatus: { runner_status: "failed", error: "Worker stopped" }, phase: 2 },
    });
    expect(wrapper.get('[data-testid="run-record-error"]').text()).toContain("Worker stopped");
    expect(wrapper.get('[data-testid="run-record-list"]').text()).toContain("Public action 1");
    expect(wrapper.get('[data-testid="inspected-public-text"]').text()).toBe("Public action 1");
  });

  it("does not describe unavailable history as an empty run", () => {
    wrapper = mount(Step3RunWayfinder, { props: { phase: 2, runStatus: { runner_status: "completed" },
      historyError: "Recent activity history is unavailable. Displayed records may be incomplete." } });
    expect(wrapper.get('[data-testid="run-record-empty"]').text()).toContain("cannot establish that the run had no actions");
    expect(wrapper.get('[data-testid="activity-history-error"]').text()).toContain("unavailable");
  });
});

describe("public record inspection", () => {
  it("shows text literally and omits private and unrecognized payload fields", () => {
    wrapper = mount(RunActivityInspector, { props: { record: {
      ...action(1, "<script>untrusted text</script>"), _uniqueId: "activity-1", _identitySource: "local",
      reasoning: "PRIVATE_REASONS", action_args: { content: "<script>untrusted text</script>", reasoning: "PRIVATE_ARGS", tweet_id: 0 },
    } } });
    expect(wrapper.find("script").exists()).toBe(false);
    expect(wrapper.text()).toContain("<script>untrusted text</script>");
    expect(wrapper.text()).not.toContain("PRIVATE_");
    expect(wrapper.text()).toContain("Local display reference (not a server ID)");
    expect(wrapper.text()).toContain("tweet id");
    expect(wrapper.text()).not.toContain("undefined");
  });
});
