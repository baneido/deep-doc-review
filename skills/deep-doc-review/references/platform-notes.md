# Platform notes

## Claude Code
- Installed as the plugin `deep-doc-review` from the marketplace `deep-doc-review`
  (`claude plugin install deep-doc-review@deep-doc-review`). Plugin skills are namespaced: invoke with
  `/deep-doc-review:deep-doc-review <path> [options]` or just ask ("この設計書をディープレビューして").
- `${CLAUDE_SKILL_DIR}` expands to the skill folder inside the plugin cache — use it for `scripts/` paths.
- Subagents: the **Agent** tool (formerly Task). Prefer `subagent_type: "deep-doc-review:reviewer"` (bundled in the
  plugin's `agents/reviewer.md`); fall back to `general-purpose`.
  Spawn a whole wave in ONE assistant message with multiple Agent calls so they run concurrently.
  Default concurrent limit is 20; keep waves ≤ 8.
- Subagents may start in the background; wait until every subagent of the wave has reported (completion
  notifications) before merging. In `claude -p` (non-interactive) the orchestrator can wait directly.
- Effort: for difficulty-5 segments pass a higher `effort` on the Agent call if supported, or add "ultrathink".
- Permissions: reviewers need Read + Write (their own output file). In non-interactive runs use e.g.
  `claude -p "/deep-doc-review:deep-doc-review doc.md" --permission-mode acceptEdits --allowedTools "Agent,Read,Write,Bash(python3:*)"`.
- If the Agent tool is denied/unavailable → sequential fallback (SKILL.md Stage 3).

## OpenAI Codex CLI
- Installed as the plugin `deep-doc-review@deep-doc-review` (`codex plugin add deep-doc-review@deep-doc-review`).
  The skill is listed as `deep-doc-review:deep-doc-review`: invoke with `$deep-doc-review:deep-doc-review <path>`, pick it from
  `/skills`, or just ask.
- `SKILL_DIR`: Codex lists each skill's file path (inside `~/.codex/plugins/cache/...`); use the directory of that
  SKILL.md for `scripts/`.
- Subagents: current Codex releases spawn subagents when a skill instruction asks for it. Ask explicitly:
  "Spawn one subagent per job below, wait for all of them, then continue." Codex plugins do not ship custom agent
  definitions, so use the default subagent; every prompt in `prompts.md` carries the full reviewer rules.
  Concurrency is capped by `[agents] max_concurrent_threads_per_session` in `~/.codex/config.toml`.
- Subagents inherit the parent's sandbox/approvals. Writing `RUN/` files needs `workspace-write`
  (e.g. `codex exec --sandbox workspace-write '$deep-doc-review:deep-doc-review doc.md'`).
- If subagents are disabled → sequential fallback.

## Other agents supporting the Agent Skills standard
The skill body is tool-agnostic: any agent that can read files, write files and (optionally) spawn subagents can run it.
