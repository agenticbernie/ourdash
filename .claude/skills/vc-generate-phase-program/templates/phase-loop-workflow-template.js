#!/usr/bin/env node
/**
 * phase-loop-workflow-template.js
 *
 * Phase-program INNER-LOOP workflow template (Buildable ID G1 / E2).
 *
 * Given a Context Envelope object, this module expands the canonical 7-step inner loop
 * `R -> I -> P -> PVL -> E -> EVL -> UP` into an ordered array of agent()-delegation step
 * descriptors. The Workflow tool has no direct file access, so every step that touches files
 * is expressed as an `agent()` delegation (see vc-generate-phase-program §G1).
 *
 * Four context slots are threaded into the expanded steps:
 *   - {test-runner}          -> testRunner          (multi-runner `bun test | vitest` -> SEQUENTIAL steps)
 *   - {blast-radius-paths}   -> blastRadiusPaths
 *   - {validate-contract-path} -> validateContractPath
 *   - {infra-context-group}  -> infraContextGroup
 *
 * The `{test-runner}` slot NEVER emits a literal `bun test | vitest` shell pipe. A multi-runner
 * value is split on ` | ` into an ordered runner list, and each runner becomes its own sequential
 * test step.
 *
 * Run `node phase-loop-workflow-template.js --self-test` for the embedded pass/fail assertion.
 */

"use strict";

/**
 * Split a (possibly multi-runner) test-runner DISPLAY value into an ordered list of runners.
 * `"bun test | vitest"` -> `["bun test", "vitest"]`. Never returns the literal pipe string.
 */
function splitTestRunners(testRunner) {
  if (!testRunner || typeof testRunner !== "string") return [];
  return testRunner
    .split(" | ")
    .map((r) => r.trim())
    .filter((r) => r.length > 0);
}

/**
 * Expand the 7-step inner loop into agent-delegation step descriptors.
 *
 * @param {object} envelope
 * @param {string} envelope.testRunner          - e.g. "bun test | vitest" (display) or "vitest"
 * @param {string} [envelope.blastRadiusPaths]  - comma/space separated blast-radius paths
 * @param {string} [envelope.validateContractPath] - path to the phase validate-contract
 * @param {string} [envelope.infraContextGroup] - relevant process/context/ group for infra/runtime
 * @returns {Array<object>} ordered step descriptors
 */
function expandPhaseLoop(envelope = {}) {
  const {
    testRunner = "",
    blastRadiusPaths = "",
    validateContractPath = "",
    infraContextGroup = "",
  } = envelope;

  const runners = splitTestRunners(testRunner);

  const steps = [];

  steps.push({
    step: 1,
    name: "RESEARCH",
    agent: "vc-research-agent",
    action:
      "Read prior phase reports (immediately prior in full; earlier phases' Forward Preview only); " +
      "load context via vc-context-discovery + vc-plan-discovery" +
      (infraContextGroup ? ` (infra context group: ${infraContextGroup})` : "") +
      "; fire Tier-0 intent restatement.",
  });

  steps.push({
    step: 2,
    name: "INNOVATE",
    agent: "vc-innovate-agent",
    action: "Decide approach; write Decision Summary (chosen approach + rejected alternatives).",
  });

  steps.push({
    step: 3,
    name: "PLAN-SUPPLEMENT",
    agent: "vc-plan-agent",
    action:
      "Supplement the existing phase plan with research/innovate findings (or mark 'n/a — clean'); " +
      "write an Inner Loop Refresh Note if sections changed." +
      (blastRadiusPaths ? ` Blast radius: ${blastRadiusPaths}.` : ""),
  });

  steps.push({
    step: 4,
    name: "PVL",
    agent: "vc-validate-agent",
    action:
      "Write the validate-contract (V1–V7)" +
      (validateContractPath ? ` to ${validateContractPath}` : "") +
      ". No new /goal block — umbrella Stable Program Goal stays authoritative.",
  });

  steps.push({
    step: 5,
    name: "EXECUTE",
    agent: "vc-execute-agent",
    action:
      "Implement the approved phase scope" +
      (blastRadiusPaths ? ` within ${blastRadiusPaths}` : "") +
      "; run per-section Level-1 test gates to green.",
  });

  // Step 6 (EVL) expands the {test-runner} slot into SEQUENTIAL runner steps.
  if (runners.length > 0) {
    runners.forEach((runner, idx) => {
      steps.push({
        step: 6,
        substep: `6.${idx + 1}`,
        name: "EVL",
        agent: "vc-tester",
        action: `Run test runner sequentially: ${runner}.`,
        runner,
      });
    });
  } else {
    steps.push({
      step: 6,
      name: "EVL",
      agent: "vc-tester",
      action: "Run the phase test gates (no runner specified in envelope).",
    });
  }

  steps.push({
    step: 7,
    name: "UPDATE PROCESS",
    agent: "vc-update-process-agent",
    action:
      "Write phase report; update umbrella ## Current Execution State; archive when ready; " +
      "update context docs; commit.",
  });

  return steps;
}

/**
 * Render the expanded steps to a single inspectable string (used by --self-test and callers
 * that want a flat textual view of the workflow).
 */
function renderSteps(steps) {
  return steps
    .map((s) => {
      const id = s.substep ? s.substep : String(s.step);
      return `${id}. ${s.name} [${s.agent}] — ${s.action}`;
    })
    .join("\n");
}

function selfTest() {
  const fixture = {
    testRunner: "bun test | vitest",
    blastRadiusPaths: "packages/api, apps/web",
    validateContractPath: "process/features/x/active/x_PLAN_09-06-26.md#validate-contract",
    infraContextGroup: "container",
  };

  const steps = expandPhaseLoop(fixture);
  const rendered = renderSteps(steps);

  // Assert (a): NO literal `bun test | vitest` pipe substring in the expanded output.
  const noLiteralPipe = !rendered.includes("bun test | vitest");

  // Assert (b): `bun test` AND `vitest` appear as separate sequential test steps.
  const evlSteps = steps.filter((s) => s.name === "EVL" && s.runner);
  const hasBunStep = evlSteps.some((s) => s.runner === "bun test");
  const hasVitestStep = evlSteps.some((s) => s.runner === "vitest");
  const sequential =
    hasBunStep &&
    hasVitestStep &&
    evlSteps.length >= 2 &&
    evlSteps[0].runner === "bun test" &&
    evlSteps[1].runner === "vitest";

  const pass = noLiteralPipe && hasBunStep && hasVitestStep && sequential;

  console.log("--- phase-loop-workflow-template --self-test ---");
  console.log(rendered);
  console.log("-----------------------------------------------");
  console.log(`(a) no literal "bun test | vitest" pipe: ${noLiteralPipe ? "PASS" : "FAIL"}`);
  console.log(`(b) sequential "bun test" then "vitest" steps: ${sequential ? "PASS" : "FAIL"}`);
  console.log(pass ? "SELF-TEST: PASS" : "SELF-TEST: FAIL");

  process.exit(pass ? 0 : 1);
}

if (process.argv.includes("--self-test")) {
  selfTest();
}

module.exports = { expandPhaseLoop, splitTestRunners, renderSteps };
