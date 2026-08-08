#!/usr/bin/env node

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const VISIBLE_ATTRIBUTE_PATTERN =
  /\b(aria-label|title|placeholder|alt|content)\s*=\s*(["'])([\s\S]*?)\2/g;

export const REQUIRED_TRUTH_RAIL_FACTS = [
  "ACTIONS + ANSWERS: SYNTHETIC",
  "HUMAN RESPONDENTS: 0",
  "NOT A FORECAST",
  "SOURCES: STARTING CONDITIONS ONLY",
  "HUMAN VALIDATION: OUTSIDE THIS RUN",
];

const PRODUCT_NAME_PATTERN = /\bask\s*the\s*people\b/i;
const APPROVED_PRODUCT_DESCRIPTOR_PATTERN =
  /\b(?:synthetic decision explorer|synthetic scenario exploration|research-planning handoff)\b/i;

const TERM_PATTERNS = [
  /\bpredict(?:s|ed|ing|ion|ions|ive)?\b/gi,
  /\bforecast(?:s|ed|ing)?\b/gi,
  /\bconsensus\b/gi,
  /\bprobabilit(?:y|ies)\b/gi,
  /\bconfidence\b/gi,
  /\bcertainty\b/gi,
  /\blikelihood\b/gi,
  /\bcalibrat(?:e|es|ed|ing|ion|ions)\b/gi,
  /\brepresentative\b/gi,
  /\bpublic[ -]opinion\b/gi,
  /\bdigital twins?\b/gi,
  /\bmajorit(?:y|ies)\b/gi,
  /\bminorit(?:y|ies)\b/gi,
  /\bpopularity\b/gi,
  /\bperspective alignment\b/gi,
  /\bprevalence\b/gi,
  /\bpopulation (?:estimate|measure|measurement|share)\b/gi,
  /\b(?:public|population|path) support\b/gi,
  /\bsupport (?:score|rate|share)\b/gi,
  /\bvotes?\b/gi,
  /\brespondents?\b/gi,
  /\bparticipants?\b/gi,
  /\bsampl(?:e|es|ed|ing)\b/gi,
  /\bsurvey(?:s|ed|ing)?\b/gi,
  /\bpolls?\b/gi,
  /\bevidence from (?:the )?graph\b/gi,
  /\bverified lineage\b/gi,
  /\bcorroborated claim\b/gi,
  /\brealistic humans?\b/gi,
  /\bhuman parity\b/gi,
  /\bhuman[- ]level accuracy\b/gi,
  /\bbias[- ]free personas?\b/gi,
  /\bscientifically proven (?:people )?simulation\b/gi,
];

function maskPreservingLines(value) {
  return value.replace(/[^\n]/g, " ");
}

function maskComments(source) {
  return source
    .replace(/<!--[\s\S]*?-->/g, maskPreservingLines)
    .replace(/\/\*[\s\S]*?\*\//g, maskPreservingLines)
    .replace(/^\s*\/\/.*$/gm, maskPreservingLines);
}

function lineNumberAt(source, offset) {
  return source.slice(0, offset).split("\n").length;
}

function normalizeCopy(value) {
  return value
    .replace(/\{\{[\s\S]*?\}\}/g, "")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/\s+/g, " ")
    .trim();
}

function nearbyVisibleText(source, offset) {
  return normalizeCopy(
    source
      .slice(Math.max(0, offset - 240), Math.min(source.length, offset + 240))
      .replace(/<[^>]*>/g, " "),
  );
}

function isZeroHumanDisclosure(text, match, source, offset) {
  if (!/^respondents?$/i.test(match)) return false;
  const nearbyText = nearbyVisibleText(source, offset);
  return (
    /\b0\s+human\s+respondents?\b/i.test(text) ||
    /\bhuman\s+respondents?\s*:\s*0\b/i.test(text) ||
    /\b0\s+human\s+respondents?\b/i.test(nearbyText) ||
    /\bhuman\s+respondents?\s*:\s*0\b/i.test(nearbyText)
  );
}

function isExplicitLimitation(text, index) {
  const sentenceStart = Math.max(
    text.lastIndexOf(".", index - 1),
    text.lastIndexOf("!", index - 1),
    text.lastIndexOf("?", index - 1),
    text.lastIndexOf(";", index - 1),
    text.lastIndexOf("\n", index - 1),
  );
  const before = text.slice(Math.max(sentenceStart + 1, index - 120), index);
  return /(?:\bno\b|\bnot\b|\bnever\b|\bwithout\b|\bcannot\b|\bcan['’]t\b|\bdoes\s+not\b|\bdo\s+not\b|\bnon[- ])/i.test(
    before,
  );
}

function violationsForCandidate(candidate, path, source) {
  const violations = [];
  const productNameMatch = PRODUCT_NAME_PATTERN.exec(candidate.text);
  if (productNameMatch) {
    const nearbyText = nearbyVisibleText(source, candidate.offset);
    if (
      !APPROVED_PRODUCT_DESCRIPTOR_PATTERN.test(candidate.text) &&
      !APPROVED_PRODUCT_DESCRIPTOR_PATTERN.test(nearbyText)
    ) {
      violations.push({
        path,
        line: lineNumberAt(source, candidate.offset + (productNameMatch.index ?? 0)),
        surface: candidate.surface,
        term: "product-name",
        text: candidate.text,
      });
    }
  }
  for (const pattern of TERM_PATTERNS) {
    pattern.lastIndex = 0;
    for (const match of candidate.text.matchAll(pattern)) {
      const matchedTerm = match[0].toLowerCase();
      if (
        isZeroHumanDisclosure(
          candidate.text,
          match[0],
          source,
          candidate.offset + (match.index ?? 0),
        ) ||
        isExplicitLimitation(candidate.text, match.index ?? 0)
      ) {
        continue;
      }
      violations.push({
        path,
        line: lineNumberAt(source, candidate.offset + (match.index ?? 0)),
        surface: candidate.surface,
        term: matchedTerm,
        text: candidate.text,
      });
    }
  }
  return violations;
}

function extractTemplateCandidates(source) {
  const candidates = [];
  const openingTemplate = /<template\b[^>]*>/i.exec(source);
  const scriptOffset = source.search(/<script\b/i);
  const closingTemplate = openingTemplate
    ? source.lastIndexOf(
        "</template>",
        scriptOffset === -1 ? source.length : scriptOffset,
      )
    : -1;
  const hasVueTemplate =
    Boolean(openingTemplate) && closingTemplate > (openingTemplate?.index ?? 0);
  const templateOffset = hasVueTemplate
    ? (openingTemplate?.index ?? 0) + openingTemplate[0].length
    : 0;
  const templateSource = maskComments(
    hasVueTemplate ? source.slice(templateOffset, closingTemplate) : source,
  );

  for (const match of templateSource.matchAll(VISIBLE_ATTRIBUTE_PATTERN)) {
    const text = normalizeCopy(match[3]);
    if (!text) continue;
    candidates.push({
      offset: templateOffset + (match.index ?? 0),
      surface: match[1].toLowerCase(),
      text,
    });
  }

  for (const match of templateSource.matchAll(/>([^<]+)(?=<)/g)) {
    const text = normalizeCopy(match[1]);
    if (!text) continue;
    candidates.push({
      offset: templateOffset + (match.index ?? 0) + 1,
      surface: "text",
      text,
    });
  }
  return candidates;
}

function extractScriptCandidates(source) {
  const candidates = [];
  const scriptMatch = /<script\b[^>]*>([\s\S]*?)<\/script>/i.exec(source);
  if (!scriptMatch) return candidates;

  const scriptSource = maskComments(scriptMatch[1]);
  const scriptOffset = (scriptMatch.index ?? 0) + scriptMatch[0].indexOf(scriptMatch[1]);
  const stringPattern = /(["'])(?:\\.|(?!\1)[^\\\r\n])*\1|`(?:\\.|[^`\\])*`/g;
  for (const match of scriptSource.matchAll(stringPattern)) {
    const text = normalizeCopy(match[0].slice(1, -1));
    if (!text) continue;
    candidates.push({
      offset: scriptOffset + (match.index ?? 0) + 1,
      surface: "script-string",
      text,
    });
  }
  return candidates;
}

export function auditVisibleCopy(source, path = "unknown.vue") {
  const candidates = [
    ...extractTemplateCandidates(source),
    ...extractScriptCandidates(source),
  ];
  const seen = new Set();
  const violations = [];
  for (const candidate of candidates) {
    for (const violation of violationsForCandidate(candidate, path, source)) {
      const key = [
        violation.path,
        violation.line,
        violation.surface,
        violation.term,
        violation.text,
      ].join("|");
      if (seen.has(key)) continue;
      seen.add(key);
      violations.push(violation);
    }
  }
  return { candidates, violations };
}

const SKIPPED_DIRECTORIES = new Set([
  "__tests__",
  "coverage",
  "dist",
  "node_modules",
]);

function frontendFiles(directory) {
  const files = [];
  const entries = readdirSync(directory, { withFileTypes: true }).sort((a, b) =>
    a.name.localeCompare(b.name),
  );
  for (const entry of entries) {
    const fullPath = resolve(directory, entry.name);
    if (entry.isDirectory()) {
      if (SKIPPED_DIRECTORIES.has(entry.name)) continue;
      files.push(...frontendFiles(fullPath));
    } else if (
      entry.isFile() &&
      (entry.name.endsWith(".vue") ||
        entry.name.endsWith(".svg") ||
        entry.name === "index.html")
    ) {
      files.push(fullPath);
    }
  }
  return files;
}

export function auditFrontendDirectory(
  directory,
  repositoryRoot = resolve(frontendSourceRoot(directory), "../.."),
) {
  const violations = [];
  let candidateCount = 0;
  const files = frontendFiles(directory);
  for (const file of files) {
    const path = relative(repositoryRoot, file).replaceAll("\\", "/");
    const result = auditVisibleCopy(readFileSync(file, "utf8"), path);
    candidateCount += result.candidates.length;
    violations.push(...result.violations);
  }
  return { candidateCount, filesScanned: files.length, violations };
}

function frontendSourceRoot(frontendDirectory) {
  const directRouter = resolve(frontendDirectory, "router/index.js");
  if (existsSync(directRouter)) return frontendDirectory;
  return resolve(frontendDirectory, "src");
}

export function auditPrimarySurfaceTruthRails(
  frontendDirectory,
  repositoryRoot = resolve(frontendSourceRoot(frontendDirectory), "../.."),
) {
  const sourceRoot = frontendSourceRoot(frontendDirectory);
  const routerPath = resolve(sourceRoot, "router/index.js");
  const routerSource = readFileSync(routerPath, "utf8");
  const imports = new Map();

  for (const match of routerSource.matchAll(
    /import\s+(\w+)\s+from\s+(["'])([^"']+\.vue)\2/g,
  )) {
    imports.set(match[1], resolve(dirname(routerPath), match[3]));
  }

  const gaps = [];
  let routesChecked = 0;
  for (const match of routerSource.matchAll(
    /path:\s*(["'])(.*?)\1[\s\S]*?component:\s*(\w+)/g,
  )) {
    const route = match[2];
    const componentName = match[3];
    if (route.includes("pathMatch")) continue;

    const viewPath = imports.get(componentName);
    if (!viewPath || !existsSync(viewPath)) continue;
    routesChecked += 1;

    const source = readFileSync(viewPath, "utf8");
    const railTag = /<TruthRail\b([^>]*)\/?\s*>/.exec(source);
    const usesSharedRail =
      Boolean(railTag) &&
      !/\bv-(?:if|show)\b/.test(railTag?.[1] ?? "") &&
      /import\s+TruthRail\s+from\s+["'][^"']+TruthRail\.vue["']/.test(source);
    const visibleCopy = auditVisibleCopy(source).candidates
      .filter((candidate) => candidate.surface !== "script-string")
      .map((candidate) => candidate.text)
      .join(" ");
    const exposesInlineRail = REQUIRED_TRUTH_RAIL_FACTS.every((fact) =>
      visibleCopy.includes(fact),
    );
    if (usesSharedRail || exposesInlineRail) continue;

    gaps.push({
      path: relative(repositoryRoot, viewPath).replaceAll("\\", "/"),
      line: 1,
      route,
      surface: "primary-surface",
      term: "truth-rail",
      text: "Missing persistent five-fact Truth Rail",
    });
  }

  return { gaps, routesChecked };
}

function runCli() {
  const repositoryRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
  const frontendRoot = resolve(repositoryRoot, process.argv[2] || "frontend");
  const result = auditFrontendDirectory(frontendRoot, repositoryRoot);
  const railResult = auditPrimarySurfaceTruthRails(frontendRoot, repositoryRoot);

  if (result.violations.length === 0 && railResult.gaps.length === 0) {
    console.log(
      `Frontend truth check passed: ${result.filesScanned} surfaces, ${result.candidateCount} visible-copy candidates, ${railResult.routesChecked} primary routes.`,
    );
    return;
  }

  console.error(
    `Frontend truth check failed: ${result.violations.length} copy violation(s), ${railResult.gaps.length} Truth Rail gap(s).`,
  );
  for (const violation of result.violations) {
    console.error(
      `${violation.path}:${violation.line} [${violation.surface}] unsupported “${violation.term}”: ${violation.text}`,
    );
  }
  for (const gap of railResult.gaps) {
    console.error(
      `${gap.path}:${gap.line} [${gap.surface}] ${gap.text} on route ${gap.route}`,
    );
  }
  process.exitCode = 1;
}

const invokedPath = process.argv[1] ? resolve(process.argv[1]) : "";
const normalizedInvokedPath = invokedPath.replaceAll("\\", "/").toLowerCase();
const normalizedModulePath = fileURLToPath(import.meta.url)
  .replaceAll("\\", "/")
  .toLowerCase();
if (normalizedInvokedPath && normalizedModulePath === normalizedInvokedPath) runCli();
