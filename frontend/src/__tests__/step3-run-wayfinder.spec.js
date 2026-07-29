import { mount } from "@vue/test-utils";
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
  it("makes the completed run understandable without overstating its evidence", async () => {
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
    expect(wrapper.get(".truth-stamp").attributes("aria-label")).toBe(
      "0 human respondents. Synthetic observations. Not a forecast.",
    );
    expect(wrapper.text()).toContain("Synthetic observations · not a forecast");
    expect(wrapper.text()).toContain("Generated channel 01");
    expect(wrapper.text()).toContain("Generated channel 02");
    expect(wrapper.text()).toContain("Short-post activity");
    expect(wrapper.text()).toContain("Topic-community activity");
    expect(wrapper.text()).toContain(
      "They show activity inside this run, not causal paths or what people will do.",
    );
    expect(wrapper.text()).toContain(
      "Fewer buses could make weekend work shifts harder to reach.",
    );
    expect(wrapper.text()).toContain(
      "Reduced access may also reduce weekend foot traffic.",
    );
    expect(wrapper.text()).toContain("Validate with people");
    expect(wrapper.text()).toContain("Open the decision brief");
    expect(wrapper.text()).not.toContain("Review the evidence");
    expect(wrapper.text()).not.toContain("PID");
    expect(wrapper.text()).not.toContain("telemetry");
    expect(wrapper.text()).not.toContain("ATP");

    const progress = wrapper.get('[role="progressbar"]');
    expect(progress.attributes("aria-valuenow")).toBe("6");
    expect(progress.attributes("aria-valuetext")).toBe("Run complete");
    expect(wrapper.get("details").attributes("open")).toBeUndefined();

    await wrapper.get(".review-button").trigger("click");
    expect(wrapper.emitted("review")).toHaveLength(1);
  });

  it("shows honest waiting states while routes are still unfolding", () => {
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
    expect(wrapper.text()).toContain("Activity unfolding");
    expect(wrapper.text()).toContain("Round 2 of 8");
    expect(wrapper.text()).toContain(
      "The first activity stream is being recorded.",
    );
    expect(wrapper.text()).toContain(
      "No generated action has occurred in this channel yet.",
    );
    expect(wrapper.get(".review-button").attributes("disabled")).toBeDefined();
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
    expect(wrapper.text()).not.toContain(
      "The first activity stream is being recorded.",
    );
    expect(wrapper.get('[role="progressbar"]').attributes("aria-valuetext")).toBe(
      "Run complete",
    );
  });
});
