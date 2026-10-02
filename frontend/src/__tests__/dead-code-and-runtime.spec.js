// @vitest-environment jsdom

/**
 * Dead code and runtime defects found in the workspace-shell redesign.
 *
 * The cleanup this file pins is not cosmetic. The token layer had grown a
 * component language for a route shell that no longer exists, and two panels
 * that can render side by side were both publishing `id="decision-heading"`,
 * so one of the two `aria-labelledby="decision-heading"` references resolved to
 * the wrong heading.
 *
 * Two kinds of assertion live here and they are not interchangeable:
 *
 *   - A mounted component. A rendered attribute is the only thing that can prove
 *     a relationship holds at runtime.
 *   - A source scan, used only where the claim is genuinely about text: that a
 *     stylesheet rule matches nothing, that a token variable survives, that a
 *     dead export is gone, that production code does not log. Each scan carries
 *     an explicit allowlist with a written reason, so a new violation fails
 *     rather than being absorbed.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  routerPush: vi.fn(),
  route: { name: "Home", params: {}, query: {}, fullPath: "/" },
  getTemplates: vi.fn(() => new Promise(() => {})),
  getSimulationHistory: vi.fn(() => new Promise(() => {})),
  fetchSourceUrls: vi.fn(() => new Promise(() => {})),
}));

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: mocks.routerPush, replace: mocks.routerPush }),
  useRoute: () => mocks.route,
}));

vi.mock("../api/graph", async (importOriginal) => ({
  ...(await importOriginal()),
  getTemplates: mocks.getTemplates,
}));
vi.mock("../api/simulation", async (importOriginal) => ({
  ...(await importOriginal()),
  getSimulationHistory: mocks.getSimulationHistory,
  getSimulationOpinions: vi.fn(() => new Promise(() => {})),
}));
vi.mock("../api/sources.js", async (importOriginal) => ({
  ...(await importOriginal()),
  fetchSourceUrls: mocks.fetchSourceUrls,
}));

import Home from "../views/Home.vue";
import NotFoundView from "../views/NotFoundView.vue";
import OpinionMap from "../components/OpinionMap.vue";
import Step3RunWayfinder from "../components/Step3RunWayfinder.vue";
import {
  DEFAULT_LAYOUT_MODE,
  closeAllWindows,
  cycleLayoutMode,
  layoutMode,
  openApp,
  setLayoutMode,
} from "../composables/useDesktop.js";
import { clearState } from "../composables/useWorkspaceState.js";

const SRC = resolve("src");
const TOKENS = resolve("src/assets/design-tokens.css");

// ---------------------------------------------------------------- file walking

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else out.push(full);
  }
  return out;
}

const allFiles = walk(SRC);
const vueFiles = allFiles.filter((f) => f.endsWith(".vue"));
// Test files are excluded from every scan: a class name that only appears in a
// spec is a test fixture, not a consumer.
const productionFiles = allFiles.filter(
  (f) => /\.(vue|js|css)$/.test(f) && !f.includes(`${join("src", "__tests__")}`),
);
const read = (file) => readFileSync(file, "utf8");

/** The SFC with its script and style blocks removed: markup only. */
const markupOf = (source) =>
  source
    .replace(/<script[\s\S]*?<\/script>/g, "")
    .replace(/<style[\s\S]*?<\/style>/g, "");

// ------------------------------------------------------- live class derivation

/**
 * Every class name a template can actually put on an element.
 *
 * Both quoting styles of a dynamic binding count, because both occur:
 * `:class="'foo'"` and `:class="['foo']"`. So does any class named inside a
 * component's own style block, because a rule that is paired with a scoped one
 * is styled work, not residue.
 */
function liveClassNames() {
  const live = new Set();
  for (const file of vueFiles) {
    const source = read(file);
    const markup = markupOf(source);

    for (const match of markup.matchAll(/\bclass\s*=\s*"([^"]*)"/g)) {
      for (const token of match[1].split(/\s+/)) if (token) live.add(token);
    }
    for (const match of markup.matchAll(/\bclass\s*=\s*'([^']*)'/g)) {
      for (const token of match[1].split(/\s+/)) if (token) live.add(token);
    }
    for (const match of markup.matchAll(/(?::|v-bind:)class\s*=\s*"([^"]*)"/g)) {
      for (const token of match[1].split(/[\s'"]+/)) {
        if (token && !/[[\](){}|:]/.test(token)) live.add(token);
      }
    }
    for (const match of markup.matchAll(/(?::|v-bind:)class\s*=\s*'([^']*)'/g)) {
      for (const token of match[1].split(/[\s'"]+/)) {
        if (token && !/[[\](){}|:]/.test(token)) live.add(token);
      }
    }
    for (const match of source.matchAll(/\.(-?[_a-zA-Z][\w-]*)/g)) {
      if (/<style[\s\S]*?<\/style>/.test(source)) live.add(match[1]);
    }
  }
  try {
    for (const match of read(resolve("index.html")).matchAll(/\bclass\s*=\s*"([^"]*)"/g)) {
      for (const token of match[1].split(/\s+/)) if (token) live.add(token);
    }
  } catch {
    // index.html is optional for this suite's claims.
  }
  return live;
}

// ------------------------------------------------------------- a small CSS scan

/**
 * Selector lists in a stylesheet, with the line each one starts on.
 *
 * Hand-rolled rather than pulled from postcss so the test has no undeclared
 * dependency: postcss is a transitive dep of Vite, not of this package. Brace
 * matching is enough here because the file has no `url()` payload with an
 * unbalanced brace and no string that contains one.
 */

/** Split a selector list on commas that are not inside `:is(...)` / `:not(...)`. */
const splitSelectors = (prelude) => {
  const out = [];
  let depth = 0;
  let current = "";
  for (const char of prelude) {
    if (char === "(") depth += 1;
    else if (char === ")") depth -= 1;
    if (char === "," && depth === 0) {
      out.push(current);
      current = "";
      continue;
    }
    current += char;
  }
  out.push(current);
  return out.map((s) => s.replace(/\s+/g, " ").trim()).filter(Boolean);
};

const cssRules = (css) => {
  const stripped = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const results = [];
  const stack = [];
  let buffer = "";
  let line = 1;
  let startLine = 1;

  for (const char of stripped) {
    if (char === "\n") {
      line += 1;
      continue;
    }
    if (char === "{") {
      stack.push({ prelude: buffer.trim(), startLine });
      buffer = "";
      continue;
    }
    if (char === "}") {
      const closed = stack.pop();
      // A block is a rule when its prelude is a selector list rather than an
      // at-rule parameter or a custom-property name.
      if (
        closed &&
        !closed.prelude.startsWith("@") &&
        !closed.prelude.startsWith("--")
      ) {
        results.push({ selectors: splitSelectors(closed.prelude), line: closed.startLine });
      }
      buffer = "";
      continue;
    }
    if (char === ";") {
      buffer = "";
      continue;
    }
    // Whitespace is kept: `.a .b` and `.a.b` are different selectors, and
    // collapsing it away would merge the descendant pair into one dead class.
    if (/\S/.test(char) && !buffer) startLine = line;
    buffer += char;
  }
  return results;
};

const classNamesIn = (selector) =>
  [...selector.matchAll(/\.(-?[_a-zA-Z][\w-]*)/g)].map((m) => m[1]);

// Rules whose every selector names only classes no template can produce. Each
// one is retained because an existing contract test asserts on its exact text
// (shell-ux-contract.spec.js, "reserves the display face for nouns"). Deleting
// them would break a passing test, and rewriting that test is a design change
// rather than a cleanup. They are listed so a NEW dead rule cannot join them.
const REVIEWED_DEAD_RULE_ALLOWLIST = new Set([
  "eyebrow",
  "label",
  "data-label",
  "step-name",
  "step-label",
  "phase-name",
  "final-action-btn",
  "ask-group-btn",
  "send-btn",
  "app-cta-btn",
  "map-title",
  "setup-title",
  "report-title",
  "workbench-title",
  "btn",
]);


describe("the token layer carries no rule that matches nothing", () => {
  const css = read(TOKENS);
  const live = liveClassNames();
  const rules = cssRules(css);

  it("finds rules to judge, so the scan is not silently vacuous", () => {
    // A parser that returned nothing would make every assertion below pass.
    expect(rules.length).toBeGreaterThan(60);
  });

  it("has no dead rule outside the reviewed allowlist", () => {
    const dead = [];
    for (const rule of rules) {
      const names = new Set(rule.selectors.flatMap(classNamesIn));
      if (names.size === 0) continue;
      if ([...names].some((name) => live.has(name))) continue;
      dead.push(`L${rule.line} ${rule.selectors.join(" | ")}`);
    }

    const unreviewed = dead.filter((entry) => {
      const names = entry.replace(/^L\d+\s/, "").match(/\.[-a-zA-Z_][\w-]*/g) || [];
      return !names.every((dotted) => REVIEWED_DEAD_RULE_ALLOWLIST.has(dotted.slice(1)));
    });

    expect(unreviewed, unreviewed.join("\n")).toEqual([]);
  });

  it("keeps the accessibility helpers components actually opted into", () => {
    // `.u-target` and `.u-prose` are used; removing them as "unused helpers"
    // would silently drop the WCAG 2.2 SC 2.5.8 hit area and the prose measure.
    expect(live.has("u-target")).toBe(true);
    expect(live.has("u-prose")).toBe(true);
    expect(css).toMatch(/\.u-target::after\s*\{[^}]*var\(--target-min\)/);
    expect(css).toMatch(/\.u-prose\s*\{[^}]*var\(--measure-prose\)/);
  });

  it("no longer ships the helper classes nothing opted into", () => {
    // `.u-stack` and `.u-cluster` were added today and used by no template.
    expect(live.has("u-stack")).toBe(false);
    expect(live.has("u-cluster")).toBe(false);
    expect(css).not.toContain(".u-stack");
    expect(css).not.toContain(".u-cluster");
  });

  it("never dropped a token variable that something still references", () => {
    const declared = new Set(
      [...css.matchAll(/(--[a-z0-9-]+)\s*:/g)].map((m) => m[1]),
    );
    // `var(--x, fallback)` declares the value inline rather than reading a
    // token-layer entry, so only a bare reference is a contract.
    const referenced = new Set();
    for (const file of productionFiles) {
      for (const match of read(file).matchAll(/var\(\s*(--[a-z0-9-]+)\s*[,)]/g)) {
        if (match[0].endsWith(",")) continue;
        referenced.add(match[1]);
      }
    }

    const missing = [...referenced].filter((token) => !declared.has(token)).sort();
    // Token variables are referenced, not class-matched, so a dead-rule sweep
    // must never have touched them.
    expect(missing, missing.join(", ")).toEqual([]);
  });

  it("keeps the reduced-motion, contrast, and forced-colors guards", () => {
    // These blocks mostly target element and token selectors, which is why they
    // are not measured against the template class set.
    for (const guard of [
      "@media (prefers-contrast: more)",
      "@media (forced-colors: active)",
      "@media (prefers-reduced-motion: reduce)",
    ]) {
      expect(css).toContain(guard);
    }
    expect(css).toMatch(/@media \(prefers-contrast: more\)[\s\S]*?--line-dark:\s*var\(--line-structural\)/);
    expect(css).toMatch(/@media \(forced-colors: active\)[\s\S]*?forced-color-adjust:\s*auto/);
  });
});

describe("panels that render side by side never publish the same id", () => {
  let home = null;
  let wayfinder = null;

  beforeEach(() => {
    closeAllWindows();
    clearState();
    document.body.replaceChildren();
  });

  afterEach(() => {
    home?.unmount();
    wayfinder?.unmount();
    home = null;
    wayfinder = null;
    document.body.replaceChildren();
  });

  it("resolves each decision-band to the heading it actually labels", () => {
    // Two panels render at once in the split and free layouts, and DesktopWindow
    // mounts each view component directly, so both of these are in one document
    // at the same time. Before the fix both declared id="decision-heading" and
    // getElementById returned whichever came first in document order.
    home = mount(Home, { attachTo: document.body });
    wayfinder = mount(Step3RunWayfinder, {
      attachTo: document.body,
      props: {
        runStatus: { runner_status: "completed", current_round: 4, total_rounds: 4 },
        actions: [],
        phase: 3,
        canReview: true,
        projectData: { simulation_requirement: "Does the route hold up?" },
      },
    });

    const ids = [...document.querySelectorAll("[id]")].map((el) => el.id);
    const duplicates = ids.filter((id, i) => ids.indexOf(id) !== i);
    expect(duplicates, `duplicate ids: ${duplicates.join(", ")}`).toEqual([]);

    const band = wayfinder.get(".decision-band");
    const labelled = document.getElementById(band.attributes("aria-labelledby"));
    // The heading the band names must be the heading inside that band.
    expect(labelled).not.toBeNull();
    expect(band.element.contains(labelled)).toBe(true);
    expect(labelled.textContent).toBe("Does the route hold up?");
  });

  it("still gives the decision view its own heading for its own section", () => {
    home = mount(Home, { attachTo: document.body });

    const section = home.get("section#decision");
    const labelled = document.getElementById(section.attributes("aria-labelledby"));
    expect(labelled).not.toBeNull();
    expect(section.element.contains(labelled)).toBe(true);
    expect(labelled.textContent).toBe("The decision");
  });
});

describe("a nested component does not add a second route into the same landmark", () => {
  it("renders the run record without its own skip link", () => {
    const wrapper = mount(OpinionMap, {
      attachTo: document.body,
      props: { simulationId: "sim-1" },
    });

    // OpinionMap renders inside InteractionView's <main id="main-content">, and
    // App.vue already provides a skip link to that id at the top of the
    // document. A second one, mid-page, pointing at an ancestor it is already
    // inside of, bypasses nothing and announces twice.
    expect(wrapper.find("a.skip-link").exists()).toBe(false);
    // The section keeps the heading that names it.
    const section = wrapper.get("section.interaction-record");
    const heading = document.getElementById(section.attributes("aria-labelledby"));
    expect(heading?.tagName).toBe("H2");
    wrapper.unmount();
  });
});

describe("the route-recovery page needs no router", () => {
  it("renders its way home without importing vue-router", () => {
    const wrapper = mount(NotFoundView);

    expect(wrapper.get("#not-found-heading").text()).toBe("This path does not exist.");
    // A plain href, so the 404 screen still works in the shell's no-router
    // fallback, a static export, and a bare test mount alike.
    expect(wrapper.get("a.nav-home-link").attributes("href")).toBe("/");
    wrapper.unmount();
  });

  it("does not reach for useRouter", () => {
    const source = read(resolve("src/views/NotFoundView.vue"));
    // A source claim, because the claim is about a dependency rather than a
    // rendered attribute: an unused useRouter() is the only thing in this file
    // that would make the view depend on being mounted inside a router host.
    expect(source).not.toMatch(/vue-router/);
    expect(source).not.toMatch(/\buseRouter\b/);
  });
});

describe("the desktop store publishes no dead surface", () => {
  afterEach(() => {
    closeAllWindows();
    layoutMode.value = DEFAULT_LAYOUT_MODE;
  });

  it("still cycles and sets every layout mode after the dead members went", () => {
    // `LAYOUT_MODES` stopped being exported and `untileWindows` was deleted; the
    // behaviour they backed has to be unchanged.
    expect(DEFAULT_LAYOUT_MODE).toBe("focus");
    const seen = [layoutMode.value];
    for (let i = 0; i < 3; i += 1) seen.push(cycleLayoutMode());
    expect(seen).toEqual(["focus", "split", "free", "focus"]);

    setLayoutMode("split");
    expect(layoutMode.value).toBe("split");
    setLayoutMode("free");
    expect(layoutMode.value).toBe("free");
    // An unsupported mode is refused rather than stored.
    setLayoutMode("tiled");
    expect(layoutMode.value).toBe("free");
  });

  it("opens and focuses a panel, so the store is still the live one", () => {
    const win = openApp("decision", { name: "Home" });
    expect(win.key).toBe("decision");
    expect(openApp("brief", { name: "Report", params: { reportId: "r-1" } })).not.toBeNull();
    expect(openApp("nope")).toBeNull();
  });

  it("no longer exports the members nothing imported", () => {
    const source = read(resolve("src/composables/useDesktop.js"));
    // A source claim: these four were reachable only from the `useDesktop()`
    // barrel, which nothing called. `activeRoute` duplicated logic
    // DesktopShell.vue re-implements inline, and `untileWindows` was
    // `setLayoutMode("free")` with the validation dropped.
    for (const name of ["activeRoute", "untileWindows", "useDesktop", "LAYOUT_MODES"]) {
      expect(source, name).not.toMatch(new RegExp(`export\\s+(const|function)\\s+${name}\\b`));
    }
    // The behaviour those members backed is still present under its real name.
    expect(source).toMatch(/export\s+function\s+setLayoutMode\b/);
    expect(source).toMatch(/const\s+LAYOUT_MODES\s*=/);
  });
});

describe("production modules do not log", () => {
  it("carries no console.log, console.debug, console.info, or console.trace", () => {
    // console.warn and console.error are the deliberate report paths: an
    // operator needs to know a request failed or a session could not persist.
    // A log/debug/info/trace in the same layer is residue from development and
    // says nothing at runtime, so it has no allowlist entry.
    const offenders = [];
    for (const file of productionFiles) {
      if (!/\.(vue|js)$/.test(file)) continue;
      const rel = file.replace(/\\/g, "/").split("/src/")[1];
      read(file)
        .split(/\r?\n/)
        .forEach((line, index) => {
          if (/console\s*\.\s*(log|debug|info|trace)\s*\(/.test(line)) {
            offenders.push(`${rel}:${index + 1} ${line.trim()}`);
          }
        });
    }
    expect(offenders, offenders.join("\n")).toEqual([]);
  });
});