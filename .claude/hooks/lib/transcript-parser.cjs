#!/usr/bin/env node
'use strict';

/**
 * Transcript Parser - Extract tool/agent/todo state from session JSONL
 * @module transcript-parser
 */

const fs = require('fs');
const readline = require('readline');

// PHASE_COMPLETE marker: matches spaced "PHASE_COMPLETE: PLAN" AND unspaced
// "PHASE_COMPLETE:PLAN". Token is uppercase, may contain '-' (e.g. PLAN-SUPPLEMENT,
// UPDATE-PROCESS). `m[0]` preserves the original substring as `raw`; `m[1]` is the
// normalized phase token.
const PHASE_COMPLETE_RE = /PHASE_COMPLETE:\s*([A-Z][A-Z-]*)/g;

// Control-token marker: the NON-PHASE_COMPLETE orchestration control tokens the spec
// emits to drive routing (supplement re-validate, BLOCKED skip, cascade hard-stop,
// mid-program plan insertion, phase restructure/renumber, vc-predict deep-research
// handshake, spec-intent block). Curated ALLOWLIST (not a generic `[A-Z_]+:` matcher)
// so ordinary prose never false-positives. `m[1]` is the normalized token; the optional
// `m[2]` captures a trailing STRUCTURED uppercase qualifier (e.g. PHASE_SKIPPED: BLOCKED →
// 'BLOCKED'). The qualifier group is bounded by `(?![a-z])` so it ONLY matches a true
// all-caps tag and never the first uppercase word of a prose message — `SPEC_INTENT_BLOCKED:
// Missing input…` yields qualifier `null`, not `'M'`. Hyphenated tags require an uppercase
// run on each side (`(?:-[A-Z]+)*`), so no terminal dash is captured (`BLOCKED-skipped` →
// 'BLOCKED', never 'BLOCKED-'). `m[0]` preserves the matched substring as `raw`.
const CONTROL_TOKEN_RE =
  /\b(SUPPLEMENT_APPLIED|PHASE_SKIPPED|CASCADE_BLOCKED|MID_PROGRAM_PLAN_CREATED|PHASE_RESTRUCTURE_NOTICE|PHASE_RENUMBERED|VC-PREDICT-DEEP-NEEDED|VC-PREDICT-RESEARCH-COMPLETE|VC-FEASIBILITY-PROBE-NEEDED|VC-FEASIBILITY-VERDICT-READY|SPEC_INTENT_BLOCKED)(?::\s*([A-Z]+(?:-[A-Z]+)*)(?![a-z]))?/g;

/**
 * Extract textual content from a tool_result block. The content may be a plain
 * string or an array of `{ type: 'text', text }` sub-blocks (the parser already
 * tolerates both shapes). Returns the concatenated text (or '' when none).
 * @param {*} content - tool_result block content
 * @returns {string}
 */
function toolResultText(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content
      .map(sub => {
        if (typeof sub === 'string') return sub;
        if (sub && typeof sub === 'object' && typeof sub.text === 'string') return sub.text;
        return '';
      })
      .join('\n');
  }
  return '';
}

// B-3 dual-trigger: INTENT[-_]?CLARIFY or TIER[-_]?0 text markers → phaseCompletes.
// Scanned separately from PHASE_COMPLETE_RE (different format, no "PHASE_COMPLETE:" prefix).
const INTENT_CLARIFY_RE = /INTENT[-_]?CLARIFY|TIER[-_]?0/g;

/**
 * Scan a text blob for PHASE_COMPLETE markers and push each match onto
 * `result.phaseCompletes`, stamping a shared monotonic index.
 * Also scans for INTENT[-_]?CLARIFY and TIER[-_]?0 markers (B-3 dual-trigger text path).
 * @param {string} text - text to scan
 * @param {string} source - source enum: 'assistant' | 'user' | 'tool_result'
 * @param {Object} result - result object carrying `phaseCompletes` + `_signalIndex`
 */
function scanPhaseCompletes(text, source, result) {
  if (!text || typeof text !== 'string') return;
  PHASE_COMPLETE_RE.lastIndex = 0;
  let m;
  while ((m = PHASE_COMPLETE_RE.exec(text)) !== null) {
    result.phaseCompletes.push({
      phase: m[1],
      source,
      raw: m[0],
      index: result._signalIndex++,
      // agentId: null unconditionally — phaseCompletes originate from text-blob scanning
      // (not tool_use blocks), so parent_tool_use_id is not meaningful here (design-correct).
      agentId: null
    });
  }
  // B-3 text path: scan for INTENT[-_]?CLARIFY and TIER[-_]?0 markers.
  // These push to phaseCompletes (NOT controlTokens) so SCN-13 assert sees them.
  INTENT_CLARIFY_RE.lastIndex = 0;
  while ((m = INTENT_CLARIFY_RE.exec(text)) !== null) {
    result.phaseCompletes.push({
      phase: m[0],
      source,
      raw: m[0],
      index: result._signalIndex++,
      agentId: null
    });
  }
}

/**
 * Scan a text blob for NON-PHASE_COMPLETE control tokens and push each match onto
 * `result.controlTokens`, stamping the same shared monotonic index used by
 * phaseCompletes (so control-token order is comparable to phase order).
 * @param {string} text - text to scan
 * @param {string} source - source enum: 'assistant' | 'user' | 'tool_result'
 * @param {Object} result - result object carrying `controlTokens` + `_signalIndex`
 */
function scanControlTokens(text, source, result) {
  if (!text || typeof text !== 'string') return;
  CONTROL_TOKEN_RE.lastIndex = 0;
  let m;
  while ((m = CONTROL_TOKEN_RE.exec(text)) !== null) {
    result.controlTokens.push({
      token: m[1],
      qualifier: m[2] ?? null,
      raw: m[0],
      source,
      index: result._signalIndex++,
      // agentId: null unconditionally — controlTokens originate from text-blob scanning
      // (not tool_use blocks), so parent_tool_use_id is not meaningful here (design-correct).
      agentId: null
    });
  }
}

/**
 * Capture a text block from the JSONL stream into `result.chatMessages`. One entry
 * per non-empty text block — asserts do substring/regex matching against the full text.
 * Does NOT re-scan for PHASE_COMPLETE or control tokens; those are handled by their
 * own scan functions. This is additive: it runs on the same text but records the whole
 * block, not just matched tokens.
 * @param {string} text - full text block content
 * @param {string} source - source enum: 'assistant' | 'user' | 'tool_result'
 * @param {Object} result - result object carrying `chatMessages` + `_signalIndex`
 */
function scanChatMessages(text, source, result) {
  if (!text || typeof text !== 'string' || !text.trim().length) return;
  result.chatMessages.push({
    text,
    source,
    index: result._signalIndex++
  });
}

function isNativeTaskTodo(todo) {
  return Boolean(todo && todo._source === 'native_task');
}

function normalizeTodo(todo) {
  if (!todo || typeof todo !== 'object') return null;
  const normalized = {
    content: todo.content ?? '',
    status: todo.status ?? 'pending',
    activeForm: todo.activeForm ?? null
  };
  if (todo.id != null) normalized.id = todo.id;
  return normalized;
}

function extractTaskIdFromString(text) {
  if (!text || typeof text !== 'string') return null;
  const trimmed = text.trim();
  if (!trimmed) return null;

  try {
    const parsed = JSON.parse(trimmed);
    return extractTaskIdFromValue(parsed);
  } catch {
    // Not JSON, continue with regex extraction.
  }

  const match = trimmed.match(/["']?task[_-]?id["']?\s*[:=]\s*["']([^"']+)["']/i);
  if (match && match[1]) return match[1];
  return null;
}

function extractTaskIdFromValue(value) {
  if (value == null) return null;

  if (typeof value === 'string') {
    return extractTaskIdFromString(value);
  }

  if (typeof value !== 'object') return null;

  if (typeof value.taskId === 'string' || typeof value.taskId === 'number') {
    return String(value.taskId);
  }
  if (typeof value.task_id === 'string' || typeof value.task_id === 'number') {
    return String(value.task_id);
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const taskId = extractTaskIdFromValue(item);
      if (taskId) return taskId;
    }
    return null;
  }

  for (const fieldValue of Object.values(value)) {
    const taskId = extractTaskIdFromValue(fieldValue);
    if (taskId) return taskId;
  }
  return null;
}

/**
 * Parse transcript JSONL file
 * @param {string} transcriptPath - Path to transcript file
 * @returns {Promise<TranscriptData>}
 */
async function parseTranscript(transcriptPath) {
  const result = {
    tools: [],
    agents: [],
    todos: [],
    sessionStart: null,
    statuslineActivityCount: 0,
    invalidLineCount: 0,
    lastValidEntryAt: null,
    lastActivityAt: null,
    // Phase 2 additive signal arrays (umbrella §2). Returned in FULL (not sliced)
    // so downstream phases can assert presence + cross-signal ordering.
    phaseCompletes: [],
    agentSpawns: [],
    teamCreates: [],
    taskCreates: [],
    sendMessages: [],
    writes: [],
    // Additive: in-thread Skill-tool invocations (Tier-0 skills like vc-context-discovery,
    // vc-intent-clarify, vc-agent-strategy-compare). These never produce a Task/Write signal,
    // so without this they are invisible. Ordered + indexed like the other signal arrays.
    skillInvoked: [],
    // Additive: Bash-tool invocations capturing the command string. The regression-gate
    // validators, the 13 VC-system behavior validators, the Tier-1 audit scripts, and the
    // Routing Step-0 discover-skills.mjs all run as Bash — without this they are invisible
    // to the signal set. Ordered + indexed like the other signal arrays.
    bashCommands: [],
    // Additive: NON-PHASE_COMPLETE orchestration control tokens (SUPPLEMENT_APPLIED,
    // PHASE_SKIPPED: BLOCKED, CASCADE_BLOCKED, MID_PROGRAM_PLAN_CREATED,
    // PHASE_RESTRUCTURE_NOTICE, PHASE_RENUMBERED, VC-PREDICT-DEEP-NEEDED,
    // VC-PREDICT-RESEARCH-COMPLETE, SPEC_INTENT_BLOCKED). These drive routing but never
    // produce a Task/Write/Skill signal, so without this they are invisible. Scanned from
    // the same text + tool_result blocks as phaseCompletes; ordered + indexed identically.
    controlTokens: [],
    // Additive 10th signal: chat text blocks from the JSONL stream. Captures the full text
    // of each non-empty text block — asserts do substring/regex matching against the full text.
    // Ordered + indexed like the other signal arrays via the shared _signalIndex counter.
    chatMessages: [],
    // Private monotonic counter shared across all signal types; deleted before return.
    _signalIndex: 0
  };

  if (!transcriptPath || !fs.existsSync(transcriptPath)) {
    delete result._signalIndex;
    return result;
  }

  const toolMap = new Map();
  const agentMap = new Map();
  let latestTodos = [];

  try {
    const fileStream = fs.createReadStream(transcriptPath);
    const rl = readline.createInterface({
      input: fileStream,
      crlfDelay: Infinity
    });

    for await (const line of rl) {
      if (!line.trim()) continue;

      try {
        const entry = JSON.parse(line);
        processEntry(entry, toolMap, agentMap, latestTodos, result);
      } catch {
        result.invalidLineCount += 1;
      }
    }
  } catch {
    // Return partial results on error
  }

  result.tools = Array.from(toolMap.values()).slice(-20);
  result.agents = Array.from(agentMap.values()).slice(-10);
  result.todos = latestTodos
    .map(normalizeTodo)
    .filter(Boolean);

  // C3: the private scratch counter must NOT leak into the public interface.
  delete result._signalIndex;

  return result;
}

/**
 * Process single JSONL entry
 * @param {Object} entry - Parsed JSON line
 * @param {Map} toolMap - Tool tracking map
 * @param {Map} agentMap - Agent tracking map
 * @param {Array} latestTodos - Latest todo array reference
 * @param {Object} result - Result object
 */
function processEntry(entry, toolMap, agentMap, latestTodos, result) {
  // A0 (PVL C-1): Defensive lazy-init for direct callers (e.g. statusline.test.cjs
  // calls processEntry with a bare `result = { sessionStart: null }`). Without this,
  // `result._signalIndex++` would yield NaN and pushes to undefined arrays would throw.
  if (result._signalIndex == null) result._signalIndex = 0;
  result.phaseCompletes ??= [];
  result.agentSpawns ??= [];
  result.teamCreates ??= [];
  result.taskCreates ??= [];
  result.sendMessages ??= [];
  result.writes ??= [];
  result.skillInvoked ??= [];
  result.bashCommands ??= [];
  result.controlTokens ??= [];
  result.chatMessages ??= [];

  // Phase 5 — per-agent attribution. Read parent_tool_use_id as a TOP-LEVEL field on the
  // JSONL entry object (NOT inside entry.message.content). When this session was spawned as
  // a subagent via the Agent tool, every entry carries the parent Agent block.id here.
  // agentMap maps block.id → { type, model, ... } (populated from Agent tool_use blocks).
  // Read ONCE at the top of processEntry, before the content loop.
  const parentToolUseId = entry.parent_tool_use_id ?? null;
  const parentAgentId = agentMap.get(parentToolUseId)?.type ?? null;

  const parsedTimestamp = entry.timestamp ? new Date(entry.timestamp) : new Date();
  const timestamp = Number.isNaN(parsedTimestamp.getTime()) ? new Date() : parsedTimestamp;
  const timestampIso = timestamp.toISOString();
  let hadActivity = false;

  result.lastValidEntryAt = timestampIso;

  // Track session start
  if (!result.sessionStart && entry.timestamp) {
    result.sessionStart = timestamp;
  }

  const content = entry.message?.content;
  if (!content || !Array.isArray(content)) return;

  // Role-derived source for phaseCompletes text blocks (A2). Defaults to
  // 'assistant' when the role is absent on a text block.
  const role = entry.message?.role;
  const textSource = role === 'user' ? 'user' : 'assistant';

  for (const block of content) {
    // A1/A2: phaseCompletes from text blocks (assistant + user messages).
    if (block.type === 'text') {
      scanPhaseCompletes(block.text, textSource, result);
      scanControlTokens(block.text, textSource, result);
      scanChatMessages(block.text, textSource, result);
    }

    // A3 (PVL C-2): phaseCompletes from tool_result content — UNGATED by
    // `block.tool_use_id` (the structured tool_result branch below IS gated), so a
    // marker-carrying tool_result without a tool_use_id is still scanned.
    if (block.type === 'tool_result') {
      const trText = toolResultText(block.content);
      scanPhaseCompletes(trText, 'tool_result', result);
      scanControlTokens(trText, 'tool_result', result);
    }

    // Handle tool_use blocks
    if (block.type === 'tool_use' && block.id && block.name) {
      // Subagent spawn tool name differs by CLI generation: older Claude Code emitted
      // spawns as `Task`; current Claude Code (v2.x, e.g. 2.1.156) emits them as `Agent`
      // (TaskCreate/TaskUpdate are now the separate task-list tools, handled below).
      // Match BOTH so live transcripts — which use `Agent` — are observable, while the
      // deterministic suite's `Task` fixtures keep matching. Additive, back-compatible.
      // (Discovered by the live-assert pilot: a real `Agent` spawn was invisible under the
      // Task-only match — see ITERATION-NOTES Loop-18.)
      if (block.name === 'Task' || block.name === 'Agent') {
        result.statuslineActivityCount += 1;
        hadActivity = true;
        // Agent spawn
        agentMap.set(block.id, {
          id: block.id,
          type: block.input?.subagent_type ?? 'unknown',
          model: block.input?.model ?? null,
          description: block.input?.description ?? null,
          status: 'running',
          startTime: timestamp,
          endTime: null
        });
        // C2: ordered normalized agentSpawns view (legacy agents[] map unchanged).
        // `model` is additive (default null) so model-policy asserts (EXECUTE=opus, every
        // other phase=sonnet) can read the per-spawn model without touching agents[].
        result.agentSpawns.push({
          subagent_type: block.input?.subagent_type ?? 'unknown',
          model: block.input?.model ?? null,
          id: block.id,
          index: result._signalIndex++,
          agentId: parentAgentId
        });
      } else if (block.name === 'TeamCreate') {
        // B1: team-create presence signal (distinguishes team path from parallel).
        result.statuslineActivityCount += 1;
        hadActivity = true;
        result.teamCreates.push({
          team_name: block.input?.team_name ?? null,
          id: block.id,
          index: result._signalIndex++,
          agentId: parentAgentId
        });
      } else if (block.name === 'SendMessage') {
        // B2: inter-teammate message presence signal (proves coordination).
        result.statuslineActivityCount += 1;
        hadActivity = true;
        result.sendMessages.push({
          to: block.input?.to ?? null,
          summary: block.input?.summary ?? null,
          id: block.id,
          index: result._signalIndex++,
          agentId: parentAgentId
        });
      } else if (block.name === 'TodoWrite') {
        result.statuslineActivityCount += 1;
        hadActivity = true;
        // Legacy: Replace todo array (deprecated, kept for backwards compatibility)
        if (block.input?.todos && Array.isArray(block.input.todos)) {
          latestTodos.length = 0;
          latestTodos.push(
            ...block.input.todos.map(todo => ({
              ...todo,
              _source: 'legacy_todowrite'
            }))
          );
        }
      } else if (block.name === 'TaskCreate') {
        result.statuslineActivityCount += 1;
        hadActivity = true;
        // Native Task API: add new task.
        // Track by tool_use id first; hydrate real task id from matching tool_result when present.
        if (block.input?.subject) {
          latestTodos.push({
            id: block.id,
            content: block.input.subject,
            status: 'pending',
            activeForm: block.input.activeForm || null,
            _source: 'native_task',
            _toolUseId: block.id
          });
        }
        // B1b: ADDITIVE first-class task-presence signal (AC-4 triad). Legacy
        // todos[] handling above is untouched.
        result.taskCreates.push({
          id: block.id,
          index: result._signalIndex++,
          agentId: parentAgentId
        });
      } else if (block.name === 'TaskUpdate') {
        result.statuslineActivityCount += 1;
        hadActivity = true;
        // Native Task API: Update existing task status
        // Match by taskId against native-task ids first.
        // Numeric fallback maps to native-task creation order only (not legacy TodoWrite items).
        if (block.input?.taskId && block.input?.status) {
          const taskId = String(block.input.taskId);
          const nativeTodos = latestTodos.filter(isNativeTaskTodo);
          let task = nativeTodos.find(t => String(t.id) === taskId);
          if (!task && /^\d+$/.test(taskId)) {
            const idx = Number(taskId) - 1;
            if (idx >= 0 && idx < nativeTodos.length) task = nativeTodos[idx];
          }

          if (task) {
            task.status = block.input.status;
            if (Object.prototype.hasOwnProperty.call(block.input, 'activeForm')) {
              task.activeForm = block.input.activeForm || null;
            }
          }
        }
      } else if (block.name === 'Skill') {
        // Additive: in-thread Tier-0 / helper skill invocation. `skill` is the skill name
        // (e.g. 'vc-intent-clarify'); kept ordered so asserts can prove a required skill
        // ran (and, via assert-absent, that a removed/not-built skill never ran).
        result.statuslineActivityCount += 1;
        hadActivity = true;
        result.skillInvoked.push({
          skill: block.input?.skill ?? null,
          id: block.id,
          index: result._signalIndex++,
          agentId: parentAgentId
        });
      } else if (block.name === 'AskUserQuestion') {
        // B-3 tool_use path: intent-clarify question emission → phaseCompletes (NOT controlTokens).
        // SCN-13 assert reads signals.phaseCompletes.filter(/INTENT[-_]?CLARIFY|TIER[-_]?0/).
        result.statuslineActivityCount += 1;
        hadActivity = true;
        result.phaseCompletes.push({
          phase: 'INTENT-CLARIFY',
          source: textSource,
          raw: block.name,
          index: result._signalIndex++,
          agentId: parentAgentId
        });
      } else {
        // Regular tool
        toolMap.set(block.id, {
          id: block.id,
          name: block.name,
          target: extractTarget(block.name, block.input),
          status: 'running',
          startTime: timestamp,
          endTime: null
        });
        // C1: additive normalized writes[] view, reusing extractTarget for the
        // path. Write still registers in toolMap above so .tools is unchanged.
        if (block.name === 'Write') {
          result.writes.push({
            file_path: extractTarget('Write', block.input),
            id: block.id,
            index: result._signalIndex++,
            agentId: parentAgentId
          });
        }
        // Additive: capture the Bash command string so validator/audit/regression-gate
        // runs (all Bash) become assertable. Stays in toolMap above; .tools unchanged.
        if (block.name === 'Bash') {
          result.bashCommands.push({
            command: block.input?.command ?? null,
            id: block.id,
            index: result._signalIndex++,
            agentId: parentAgentId
          });
        }
      }
    }

    // Handle tool_result blocks
    if (block.type === 'tool_result' && block.tool_use_id) {
      const tool = toolMap.get(block.tool_use_id);
      if (tool) {
        tool.status = block.is_error ? 'error' : 'completed';
        tool.endTime = timestamp;
      }

      const agent = agentMap.get(block.tool_use_id);
      if (agent) {
        result.statuslineActivityCount += 1;
        hadActivity = true;
        agent.status = 'completed';
        agent.endTime = timestamp;
      }

      const createdTask = latestTodos.find(
        todo => isNativeTaskTodo(todo) && todo._toolUseId === block.tool_use_id
      );
      if (createdTask) {
        const hydratedId = extractTaskIdFromValue(block.content);
        if (hydratedId) {
          createdTask.id = hydratedId;
        }
      }
    }
  }

  if (hadActivity) {
    result.lastActivityAt = timestampIso;
  }
}

/**
 * Extract target from tool input
 * @param {string} toolName - Tool name
 * @param {Object} input - Tool input object
 * @returns {string|null} - Extracted target
 */
function extractTarget(toolName, input) {
  if (!input) return null;

  switch (toolName) {
    case 'Read':
    case 'Write':
    case 'Edit':
      return input.file_path ?? input.path ?? null;

    case 'Glob':
    case 'Grep':
      return input.pattern ?? null;

    case 'Bash':
      const cmd = input.command;
      if (!cmd) return null;
      return cmd.length > 30 ? cmd.slice(0, 30) + '...' : cmd;

    default:
      return null;
  }
}

module.exports = {
  parseTranscript,
  // Export for testing
  processEntry,
  extractTarget
};
