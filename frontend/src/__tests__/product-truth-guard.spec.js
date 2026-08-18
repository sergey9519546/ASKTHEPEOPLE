// @vitest-environment jsdom

import { resolve } from "node:path";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import {
  auditFrontendDirectory,
  auditPrimarySurfaceTruthRails,
  auditVisibleCopy,
} from "../../../tools/lint_frontend_truth.mjs";
import TruthRail from "../components/TruthRail.vue";

const REQUIRED_TRUTH_RAIL_FACTS = [
  "ACTIONS + ANSWERS: GENERATED",
  "HUMAN RESPONDENTS: 0",
  "NOT A FORECAST",
  "SOURCES: STARTING CONDITIONS ONLY",
  "HUMAN VALIDATION: OUTSIDE THIS RUN",
];

describe("frontend product-truth guard", () => {
  it("renders every permanent truth fact in the shared rail", () => {
    const wrapper = mount(TruthRail);

    expect(
      wrapper.findAll(".truth-rail-item").map((item) => item.text()),
    ).toEqual(REQUIRED_TRUTH_RAIL_FACTS);
    expect(wrapper.get(".truth-rail").attributes("aria-label")).toBe(
      REQUIRED_TRUTH_RAIL_FACTS.join(". "),
    );
  });

  it("rejects unsupported outcome language in visible text and accessible labels", () => {
    const textResult = auditVisibleCopy(
      `<p>{{ syntheticScore }}% Consensus</p>`,
      "frontend/src/components/Example.vue",
    );
    const labelResult = auditVisibleCopy(
      `<button aria-label="Prediction confidence">Open</button>`,
      "frontend/src/components/Example.vue",
    );

    expect(textResult.violations).toEqual([
      expect.objectContaining({ term: "consensus", surface: "text" }),
    ]);
    expect(labelResult.violations.map(({ term, surface }) => ({ term, surface }))).toEqual([
      { term: "prediction", surface: "aria-label" },
      { term: "confidence", surface: "aria-label" },
    ]);
  });

  it("requires the approved synthetic descriptor wherever the product name appears", () => {
    const nakedName = auditVisibleCopy(
      `<a aria-label="Ask The People home">ASK THE PEOPLE</a>`,
      "frontend/src/components/Example.vue",
    );
    const approvedLockup = auditVisibleCopy(
      `<p>ASKTHEPEOPLE / Generated Decision Explorer</p>`,
      "frontend/src/components/Example.vue",
    );

    expect(nakedName.violations).toEqual([
      expect.objectContaining({ term: "product-name", surface: "aria-label" }),
      expect.objectContaining({ term: "product-name", surface: "text" }),
    ]);
    expect(approvedLockup.violations).toEqual([]);
  });

  it("allows explicit limitations and the zero-human disclosure", () => {
    const approvedLimitations = [
      "0 human respondents. Not a forecast.",
      "Do not treat them as public opinion.",
      "They are not sampled respondents or digital twins.",
      "The run is not representative, calibrated, or a probability estimate.",
    ];

    for (const copy of approvedLimitations) {
      expect(
        auditVisibleCopy(`<p>${copy}</p>`, "frontend/src/components/Example.vue")
          .violations,
      ).toEqual([]);
    }
  });

  it("blocks new violations while keeping the current audited debt explicit", () => {
    const repositoryRoot = resolve(process.cwd(), "..");
    const result = auditFrontendDirectory(
      resolve(repositoryRoot, "frontend"),
      repositoryRoot,
    );
    const acceptedDebt = [
      // Migration ratchet only: the standalone CLI fails on every item below.
      // Delete each entry as its source is corrected; never add new debt casually.
      {
        path: "frontend/index.html",
        term: "respondents",
        surface: "content",
        snippet: "Zero human respondents",
      },
      {
        path: "frontend/src/components/Step4Report.vue",
        term: "respondents",
        surface: "text",
        snippet: "human respondents",
      },
      ...[
        "frontend/public/mark.svg",
        "frontend/public/social-card.svg",
      ].map((path) => ({
        path,
        term: "product-name",
        surface: "text",
        snippet: "Ask The People",
      })),
      ...[
        ["frontend/src/views/InteractionView.vue", "text", "ASK THE PEOPLE"],
        ["frontend/src/views/MainView.vue", "text", "ASK THE PEOPLE"],
        ["frontend/src/views/NotFoundView.vue", "text", "Ask The People · Route recovery"],
        ["frontend/src/views/ReportView.vue", "text", "ASK THE PEOPLE"],
        ["frontend/src/views/SimulationRunView.vue", "text", "ASK THE PEOPLE"],
        ["frontend/src/views/SimulationView.vue", "text", "ASK THE PEOPLE"],
        ["frontend/src/components/DesktopMasthead.vue", "text", "ASKTHEPEOPLE"],
      ].map(([path, surface, snippet]) => ({
        path,
        term: "product-name",
        surface,
        snippet,
      })),
      {
        path: "frontend/src/views/Home.vue",
        term: "product-name",
        surface: "text",
        snippet: "ASKTHEPEOPLE",
      },
      {
        path: "frontend/src/views/Home.vue",
        term: "product-name",
        surface: "text",
        snippet: "ASK THE PEOPLE",
      },
      {
        path: "frontend/src/views/Home.vue",
        term: "product-name",
        surface: "aria-label",
        snippet: "ASKTHEPEOPLE home",
      },
    ];
    const isAcceptedDebt = (violation) =>
      acceptedDebt.some(
        (accepted) =>
          violation.path === accepted.path &&
          violation.term === accepted.term &&
          violation.surface === accepted.surface &&
          violation.text.includes(accepted.snippet),
      );

    expect(result.violations.filter((violation) => !isAcceptedDebt(violation))).toEqual([]);
    expect(result.violations.filter(isAcceptedDebt)).toHaveLength(acceptedDebt.length);
  });

  it("keeps every primary route behind the permanent five-fact Truth Rail", () => {
    const repositoryRoot = resolve(process.cwd(), "..");
    const result = auditPrimarySurfaceTruthRails(
      resolve(repositoryRoot, "frontend"),
      repositoryRoot,
    );

    // The desktop shell renders the rail once for the whole workspace, so no
    // primary route is a gap.
    expect(result.gaps).toEqual([]);
  });
});
