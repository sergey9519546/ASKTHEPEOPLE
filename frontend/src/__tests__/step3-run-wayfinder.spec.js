import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import Step3RunWayfinder from "../components/Step3RunWayfinder.vue";

const completedRun = {
  runner_status: "completed",
  current_round: 6,
  total_rounds: 6,
  twitter_actions_count: 2,
  reddit_actions_count: 1,
};

const generatedActions = [
  {
    id: "short-1",
    platform: "twitter",
    round_num: 1,
    agent_name: "Weekend rider",
    action_type: "CREATE_POST",
    action_args: {
      content: "Fewer buses could make weekend work shifts harder to reach.",
    },
  },
  {
    id: "short-2",
    platform: "twitter",
    round_num: 3,
    agent_name: "Transit advocate",
    action_type: "REPOST",
    action_args: {
      original_content: "Late service matters for workers without a car.",
    },
  },
  {
    id: "community-1",
    platform: "reddit",
    round_num: 2,
    agent_name: "Small business owner",
    action_type: "CREATE_COMMENT",
    action_args: {
      content: "Reduced access may also reduce weekend foot traffic.",
    },
  },
];

describe("Step3RunWayfinder", () => {
  it("renders recent chronological activity without claiming complete history", async () => {
    const wrapper = mount(Step3RunWayfinder, {
      props: {
        runStatus: completedRun,
        actions: generatedActions,
        phase: 2,
        canReview: true,
        projectData: {
          simulation_requirement:
            "What could happen if weekend bus service is reduced?",
        },
      },
    });

    expect(wrapper.text()).toContain(
      "What could happen if weekend bus service is reduced?",
    );
    const truthBoundary = wrapper.get('[data-testid="run-truth-boundary"]');
    expect(truthBoundary.text()).toContain("Actions + answers: generated");
    expect(truthBoundary.text()).toContain("Human respondents: 0");
    expect(truthBoundary.text()).toContain("Not a forecast");
    expect(truthBoundary.text()).toContain("Human validation: outside this run");

    const record = wrapper.get('[data-testid="run-record-list"]');
    expect(record.element.tagName).toBe("OL");
    expect(record.findAll('li[data-origin="generated"]')).toHaveLength(3);
    expect(record.text().indexOf("Weekend rider")).toBeLessThan(
      record.text().indexOf("Small business owner"),
    );
    expect(record.text().indexOf("Small business owner")).toBeLessThan(
      record.text().indexOf("Transit advocate"),
    );
    expect(wrapper.text()).toContain(
      "This is a bounded view of received records, not complete history.",
    );
    expect(wrapper.text()).toContain(
      "Fewer buses could make weekend work shifts harder to reach.",
    );
    expect(wrapper.text()).toContain(
      "Reduced access may also reduce weekend foot traffic.",
    );
    expect(wrapper.text()).toContain(
      "Possible paths are exploratory branches, not predictions, rankings, or real-world evidence.",
    );
    expect(wrapper.text()).toContain("Validate with people outside this run");
    expect(wrapper.text()).toContain("Open the decision brief");
    expect(wrapper.text()).not.toContain("Review the evidence");
    expect(wrapper.text()).not.toContain("PID");
    expect(wrapper.text()).not.toMatch(/consensus|alignment|telemetry/i);
    expect(wrapper.text()).not.toContain("ATP");

    const progress = wrapper.get('[role="progressbar"]');
    expect(progress.attributes("aria-valuenow")).toBe("6");
    expect(progress.attributes("aria-valuetext")).toBe("Run complete");
    expect(wrapper.get("details").attributes("open")).toBeUndefined();

    await wrapper.get(".review-button").trigger("click");
    expect(wrapper.emitted("review")).toHaveLength(1);
  });

  it("uses numeric timestamp order and display-order numbering", () => {
    const wrapper = mount(Step3RunWayfinder, {
      props: {
        runStatus: { runner_status: "running", current_round: 1, total_rounds: 2 },
        actions: [
          {
            id: "late",
            round_num: 1,
            timestamp: 10,
            _sequence: 1,
            agent_name: "Later generated profile",
            action_type: "CREATE_POST",
            action_args: { content: "Later timestamp" },
          },
          {
            id: "early",
            round_num: 1,
            timestamp: 2,
            _sequence: 2,
            agent_name: "Earlier generated profile",
            action_type: "CREATE_POST",
            action_args: { content: "Earlier timestamp" },
          },
        ],
        phase: 1,
      },
    });

    const rows = wrapper.findAll('[data-testid="run-record-list"] li');
    expect(rows).toHaveLength(2);
    expect(rows[0].text()).toContain("Earlier generated profile");
    expect(rows[0].text()).toContain("01");
    expect(rows[1].text()).toContain("Later generated profile");
    expect(rows[1].text()).toContain("02");
  });

  it("shows a static loading state while the first generated record is pending", () => {
    const wrapper = mount(Step3RunWayfinder, {
      props: {
        runStatus: {
          runner_status: "running",
          current_round: 2,
          total_rounds: 8,
        },
        phase: 1,
        canReview: false,
      },
    });

    expect(wrapper.text()).toContain("Follow the activity as it unfolds.");
    expect(wrapper.text()).toContain("Recording generated activity");
    expect(wrapper.text()).toContain("Round 2 of 8");
    expect(wrapper.get('[data-testid="run-record-loading"]').text()).toContain(
      "No recent activity has been received yet.",
    );
    expect(wrapper.get(".review-button").attributes("disabled")).toBeDefined();
  });

  it("separates true empty, failed, and completed states", () => {
    const empty = mount(Step3RunWayfinder, {
      props: { runStatus: { runner_status: "idle" }, phase: 0 },
    });
    expect(empty.get('[data-testid="run-record-empty"]').text()).toContain(
      "No recent activity is shown.",
    );

    const failed = mount(Step3RunWayfinder, {
      props: {
        runStatus: { runner_status: "failed", error: "Worker stopped." },
        phase: 1,
      },
    });
    expect(failed.get('[data-testid="run-record-error"]').text()).toContain(
      "This run stopped before the record was complete.",
    );

    const complete = mount(Step3RunWayfinder, {
      props: {
        runStatus: completedRun,
        actions: generatedActions,
        phase: 2,
        canReview: true,
      },
    });
    expect(complete.get('[data-testid="run-record-complete"]').text()).toContain(
      "Recorded order",
    );
  });

  it("treats a websocket-completed phase as reviewable presentation state", () => {
    const wrapper = mount(Step3RunWayfinder, {
      props: {
        runStatus: {
          runner_status: "running",
          current_round: 4,
          total_rounds: 4,
        },
        phase: 2,
        canReview: true,
      },
    });

    expect(wrapper.text()).toContain("See how the run unfolded.");
    expect(wrapper.find('[data-testid="run-record-loading"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="run-record-empty"]').text()).toContain(
      "No recent records are shown for this finished run.",
    );
    expect(wrapper.get('[role="progressbar"]').attributes("aria-valuetext")).toBe(
      "Run complete",
    );
  });

  it("shows the declared composition for a mass-population run", () => {
    const wrapper = mount(Step3RunWayfinder, {
      props: {
        runStatus: {
          runner_status: "running",
          current_round: 2,
          total_rounds: 8,
          population_tier: "mass_population",
          declared_population_total: 50000,
          follower_actions_last_round: 2000,
        },
        actions: generatedActions,
        diagnostics: { canonical_agents: new Array(5000).fill(null) },
        phase: 1,
        canReview: false,
      },
    });

    const composition = wrapper.get('[data-testid="run-composition"]');
    expect(composition.text()).toContain("50,000 generated characters");
    expect(composition.text()).toContain("not a measure of real people");
    const crowd = wrapper.get('[data-testid="crowd-actions"]');
    expect(crowd.text()).toContain("2,000");
  });

  it("hides the composition block for runs on the default tier", () => {
    const wrapper = mount(Step3RunWayfinder, {
      props: {
        runStatus: completedRun,
        actions: generatedActions,
        phase: 2,
        canReview: true,
        projectData: {
          simulation_requirement:
            "What could happen if weekend bus service is reduced?",
        },
      },
    });

    expect(wrapper.find('[data-testid="run-composition"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="crowd-actions"]').exists()).toBe(false);
  });

  it("contains no fabricated agreement readout or continuous activity animation", () => {
    const source = readFileSync(
      resolve("src/components/Step3RunWayfinder.vue"),
      "utf8",
    );

    expect(source).not.toMatch(/consensus|perspective alignment|heatmap/i);
    expect(source).not.toMatch(/Math\.round\([^)]*currentRound/i);
    expect(source).not.toMatch(/@keyframes\s+route-pulse/i);
    expect(source).not.toMatch(/animation:\s*[^;]*infinite/i);
  });
});
