# Platform notes

## Claude Code
- Install location: `~/.claude/skills/deep-review/` (personal) or `<repo>/.claude/skills/deep-review/` (project).
  Invoke with `/deep-review <path> [options]` or just ask ("この設計書をディープレビューして").
- `${CLAUDE_SKILL_DIR}` expands to the skill folder — use it for `scripts/` paths.
- Subagents: the **Agent** tool (formerly Task). Prefer `subagent_type: "deep-review-reviewer"` (installed to
  `~/.claude/agents/deep-review-reviewer.md` by install.sh); fall back to `general-purpose`.
  Spawn a whole wave in ONE assistant message with multiple Agent calls so they run concurrently.
  Default concurrent limit is 20 (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`); keep waves ≤ 8.
- Subagents may start in the background; wait until every subagent of the wave has reported (completion
  notifications) before merging. In `claude -p` (non-interactive) the orchestrator can wait directly.
- Effort: for difficulty-5 segments pass `effort: "high"`/`"max"` on the Agent call if supported, or add
  "ultrathink" to the prompt.
- Permissions: reviewers need Read + Write (their own output file). In non-interactive runs use e.g.
  `claude -p "/deep-review doc.md" --permission-mode acceptEdits --allowedTools "Bash(python3:*)" ...`.
- If the Agent tool is denied/unavailable → sequential fallback (SKILL.md Stage 3).

## OpenAI Codex CLI
- Skill locations scanned by Codex: `$HOME/.agents/skills/<name>/SKILL.md` (user), `<repo>/.agents/skills/` (repo),
  `/etc/codex/skills` (admin). install.sh uses `~/.agents/skills/deep-review/` (and, with `--codex-legacy`, also
  `~/.codex/skills/` for older builds). Invoke with `$deep-review <path>` or via `/skills`, or just ask.
- `SKILL_DIR`: Codex lists each skill's file path; use the directory of that SKILL.md for `scripts/`.
- Subagents: current Codex releases spawn subagents when a skill instruction asks for it. Ask explicitly:
  "Spawn one subagent per job below, wait for all of them, then continue." Use the custom agent
  `deep_review_reviewer` (installed to `~/.codex/agents/deep_review_reviewer.toml`) if present.
  Concurrency is capped by `[agents] max_concurrent_threads_per_session` in `~/.codex/config.toml`.
  `/subagents` in the TUI shows the threads.
- Subagents inherit the parent's sandbox/approvals. Writing `RUN/` files needs `workspace-write`
  (e.g. `codex exec --sandbox workspace-write "..."` or `--full-auto`). In `codex exec`, an action that needs a fresh
  approval fails — make sure RUN/ is inside the writable workspace.
- If subagents are disabled (`[agents] enabled = false`) → sequential fallback.

## Other agents supporting the Agent Skills standard
The skill body is tool-agnostic: any agent that can read files, write files and (optionally) spawn subagents can run it.
