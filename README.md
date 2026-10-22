# deep-doc-review — Deep Review skill for Claude Code and Codex CLI

English | [日本語](README.ja.md)

An Agent Skill that makes **Claude Code** and **OpenAI Codex CLI** run a **deep, multi-agent review** of technical documents (design docs, specs, proposals, papers, contracts, reports, and more).
It follows the approach of Google Research's [Deep Review](https://research.google/blog/analyzing-technical-documents-with-deep-review/) (segmentation → adaptive budgeting → parallel per-segment verification → global synthesis and re-verification), executed **with the agent's own subagents**, without any external API.

- Detects broken logic, calculation errors (re-computing totals, percentages, units and dates), contradictions across sections, unsupported claims and ambiguity
- Every finding comes with line numbers (`L0042`), a quote, evidence (a recalculation or the conflicting passage) and a suggested fix
- Critical findings are **independently re-verified by a separate subagent**, which can reject false positives
- Output: `report.md` (Japanese by default) and `findings.json` (machine-readable)
- Not intended for code review or copy editing

## Layout

```
.
├── install.sh                         # Install into Claude Code / Codex (idempotent)
├── skills/deep-review/                # The skill itself (shared by both platforms)
│   ├── SKILL.md                       # Orchestration procedure (Stages 0–4)
│   ├── agents/openai.yaml             # UI metadata for Codex (ignored by Claude Code)
│   ├── references/
│   │   ├── prompts.md                 # Subagent prompts (review / cross-check / re-verification)
│   │   ├── findings-schema.json       # JSON schema for findings
│   │   ├── report-template.md         # Report template
│   │   └── platform-notes.md          # Claude Code vs Codex (invocation, concurrency, permissions)
│   └── scripts/                       # Optional helpers (Python 3 standard library only)
│       ├── prepare_doc.py             # PDF/DOCX/MD → line-numbered text
│       ├── check_segments.py          # Checks that segments cover every line
│       ├── merge_findings.py          # Validates, merges and IDs findings; applies root-cause groups
│       └── finalize.py                # Applies re-verification results and writes findings.json
├── agents/
│   ├── claude/deep-review-reviewer.md # Subagent definition for Claude Code
│   └── codex/deep_review_reviewer.toml# Custom agent definition for Codex
└── tests/                             # Synthetic document with planted errors, answer key, scorer
```

## Installation

### install.sh (recommended)

```bash
git clone git@github.com:baneido/deep-doc-review.git
cd deep-doc-review
./install.sh                # Install into whichever of Claude Code / Codex is found
./install.sh --claude-only  # Claude Code only
./install.sh --codex-only   # Codex only
./install.sh --codex-legacy # Also copy to ~/.codex/skills for older Codex versions
./install.sh --uninstall    # Remove
```

| Target | Skill | Subagent definition |
|---|---|---|
| Claude Code | `~/.claude/skills/deep-review/` | `~/.claude/agents/deep-review-reviewer.md` |
| Codex CLI | `~/.agents/skills/deep-review/` | `~/.codex/agents/deep_review_reviewer.toml` |

To update, just run `git pull && ./install.sh` again (files are overwritten).

### Manual copy

```bash
# Claude Code (personal)
mkdir -p ~/.claude/skills ~/.claude/agents
cp -R skills/deep-review ~/.claude/skills/
cp agents/claude/deep-review-reviewer.md ~/.claude/agents/

# Codex CLI (personal)
mkdir -p ~/.agents/skills ~/.codex/agents
cp -R skills/deep-review ~/.agents/skills/
cp agents/codex/deep_review_reviewer.toml ~/.codex/agents/
```

To share it within a project, place it at `.claude/skills/deep-review/` (Claude Code) or `.agents/skills/deep-review/` (Codex) inside the repository.
The subagent definitions are optional. Without them, Claude Code uses `general-purpose` and Codex uses its default subagent.

## Usage

### Claude Code

```text
/deep-review docs/design.pdf
/deep-review docs/proposal.md lang=en depth=thorough
/deep-review spec.md focus="numbers in chapters 3-5" web=on
```

You can also skip the slash command and just ask, e.g. "Deep-review this design doc: docs/design.md".
Non-interactive example:

```bash
claude -p "/deep-review docs/design.md" --permission-mode acceptEdits \
  --allowedTools "Read,Write,Edit,Glob,Grep,Agent,Bash(python3:*),Bash(mkdir:*),Bash(date:*)"
```

### Codex CLI

```text
$deep-review docs/design.pdf
$deep-review docs/proposal.md depth=thorough — verify each segment in parallel with subagents
```

You can also pick it from `/skills`. Non-interactive example: `codex exec --sandbox workspace-write '$deep-review docs/design.md'`
(workspace-write or higher is required because the skill writes result files).

### Options (free-form)

| Option | Values | Default |
|---|---|---|
| `lang` | `ja` / `en` / `auto` (language of the document) | `ja` |
| `depth` | `quick` / `standard` / `thorough` | `standard` |
| `focus` | Scope or angle to emphasize (e.g. "numbers only", "chapters 3-5") | none |
| `web` | `on` to fact-check against external sources (sends only short search queries, never the document text) | off |

Results are written to `.deep-review/<doc>-<timestamp>/` in the working directory (`report.md`, `findings.json` and intermediate files). The original document is never modified.

## Pipeline

1. **Preparation (Stage 0)**: Convert the document to text and create a line-numbered copy in `L0001| …` format. Very long documents get a narrower scope.
2. **Segmentation (Stage 1)**: Split into 4–12 meaningful segments (tables stay with the text that interprets them) and check that every line is covered.
3. **Adaptive budgeting (Stage 2)**: Rate each segment's difficulty 1–5, which sets the number of passes (1–3) and reasoning depth.
   Pass angles: A = general review, B = recompute every number and cross-check it against other passages, C = skeptical domain expert.
4. **Deep parallel verification (Stage 3)**: Launch a fresh subagent for each segment × pass (waves of up to 8 in parallel).
   Each reviewer **reads the whole document but focuses on its segment**, and writes findings to a file as strict JSON.
   Where subagents are unavailable, the orchestrator runs the same steps sequentially.
5. **Global synthesis (Stage 4)**: Merge findings → cross-section consistency check (dedicated subagent) → dedupe by root cause →
   **independent re-verification** of critical/major findings by a subagent that did not write them (confirmed / rejected / uncertain) →
   (optional) web fact-checking → write `findings.json` and `report.md`.

## Testing

`tests/planted_design_doc.md` is a synthetic design document with 6 planted errors (plus 1 bonus), and `tests/planted_errors.json` is the answer key.
It also contains correct calculations, so you can check for false positives.

```bash
cd tests
claude -p "/deep-review planted_design_doc.md" --permission-mode acceptEdits \
  --allowedTools "Read,Write,Edit,Glob,Grep,Agent,Bash(python3:*),Bash(mkdir:*),Bash(date:*)"
python3 score.py .deep-review/planted_design_doc-*/findings.json
```

## Notes

- The helper scripts are optional. SKILL.md describes how the agent can do the same work by hand where Python isn't available.
- If you want batch runs over external APIs, mixed models or cost tracking, you can use a separate standalone Python tool instead (this skill defaults to agent-native execution).
