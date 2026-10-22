# deep-doc-review — Deep Review plugin for Claude Code and Codex CLI

English | [日本語](README.ja.md)

A plugin that makes **Claude Code** and **OpenAI Codex CLI** run a **deep, multi-agent review** of technical documents (design docs, specs, proposals, papers, contracts, reports, and more).
It follows the approach of Google Research's [Deep Review](https://research.google/blog/analyzing-technical-documents-with-deep-review/) (segmentation → adaptive budgeting → parallel per-segment verification → global synthesis and re-verification).

- Detects broken logic, calculation errors (re-computing totals, percentages, units and dates), contradictions across sections, unsupported claims and ambiguity
- Every finding comes with line numbers (`L0042`), a quote, evidence (a recalculation or the conflicting passage) and a suggested fix
- Critical findings are **independently re-verified by a separate subagent**, which can reject false positives
- Output: `report.md` (Japanese by default) and `findings.json` (machine-readable)
- Not intended for code review or copy editing

## Installation

> **Private repository:** you need read access to `baneido/deep-doc-review` on GitHub, and git on your machine must already be able to clone it without a prompt (for example `gh auth login` followed by `gh auth setup-git`, or an SSH key registered with GitHub). Neither CLI asks for a password.

### Claude Code

In a Claude Code session:

```text
/plugin marketplace add baneido/deep-doc-review
/plugin install deep-review@deep-doc-review
/reload-plugins
```

Or from your shell:

```bash
claude plugin marketplace add baneido/deep-doc-review
claude plugin install deep-review@deep-doc-review      # user scope; add --scope project to share via .claude/settings.json
```

Check it with `claude plugin list` or `claude plugin details deep-review@deep-doc-review`.

### Codex CLI

```bash
codex plugin marketplace add baneido/deep-doc-review   # or: git@github.com:baneido/deep-doc-review.git
codex plugin add deep-review@deep-doc-review
codex plugin list --marketplace deep-doc-review        # should show "installed, enabled"
```

In the TUI you can also open `/plugins`, choose the `deep-doc-review` marketplace and install **deep-review** there. Start a new session after installing.

## Update

```bash
# Claude Code
claude plugin marketplace update deep-doc-review
claude plugin update deep-review@deep-doc-review       # or /plugin → Installed → deep-review → Update now

# Codex CLI
codex plugin marketplace upgrade deep-doc-review       # refreshes the marketplace and the installed plugin
```

## Uninstall

```bash
# Claude Code
claude plugin uninstall deep-review@deep-doc-review
claude plugin marketplace remove deep-doc-review       # optional: also forget the marketplace

# Codex CLI
codex plugin remove deep-review@deep-doc-review
codex plugin marketplace remove deep-doc-review        # optional
```

## Usage

### Claude Code

Plugin skills are namespaced, so the command is `/deep-review:deep-review`:

```text
/deep-review:deep-review docs/design.pdf
/deep-review:deep-review docs/proposal.md lang=en depth=thorough
/deep-review:deep-review spec.md focus="numbers in chapters 3-5" web=on
```

You can also skip the slash command and just ask, e.g. "Deep-review this design doc: docs/design.md".
Non-interactive example:

```bash
claude -p "/deep-review:deep-review docs/design.md" --permission-mode acceptEdits \
  --allowedTools "Read,Write,Edit,Glob,Grep,Agent,Bash(python3:*),Bash(mkdir:*),Bash(date:*)"
```

### Codex CLI

The skill is listed as `deep-review:deep-review`:

```text
$deep-review:deep-review docs/design.pdf
$deep-review:deep-review docs/proposal.md depth=thorough — verify each segment in parallel with subagents
```

You can also pick it from `/skills` or just ask. Non-interactive example: `codex exec --sandbox workspace-write '$deep-review:deep-review docs/design.md'`
(workspace-write or higher is required because the skill writes result files).

### Options (free-form)

| Option | Values | Default |
|---|---|---|
| `lang` | `ja` / `en` / `auto` (language of the document) | `ja` |
| `depth` | `quick` / `standard` / `thorough` | `standard` |
| `focus` | Scope or angle to emphasize (e.g. "numbers only", "chapters 3-5") | none |
| `web` | `on` to fact-check against external sources (sends only short search queries, never the document text) | off |

Results are written to `.deep-review/<doc>-<timestamp>/` in the working directory (`report.md`, `findings.json` and intermediate files). The original document is never modified.

## How it works

1. **Preparation (Stage 0)**: Convert the document to text and create a line-numbered copy in `L0001| …` format. Very long documents get a narrower scope.
2. **Segmentation (Stage 1)**: Split into 4–12 meaningful segments (tables stay with the text that interprets them) and check that every line is covered.
3. **Adaptive budgeting (Stage 2)**: Rate each segment's difficulty 1–5, which sets the number of passes (1–3) and reasoning depth.
   Pass angles: A = general review, B = recompute every number and cross-check it against other passages, C = skeptical domain expert.
4. **Deep parallel verification (Stage 3)**: Launch a fresh subagent for each segment × pass (waves of up to 8 in parallel).
   Each reviewer **reads the whole document but focuses on its segment**, and writes findings to a file as strict JSON.
   Where subagents are unavailable, the same steps run one after another.
5. **Global synthesis (Stage 4)**: Merge findings → cross-section consistency check (dedicated subagent) → dedupe by root cause →
   **independent re-verification** of critical/major findings by a subagent that did not write them (confirmed / rejected / uncertain) →
   (optional) web fact-checking → write `findings.json` and `report.md`.
