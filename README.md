# deep-doc-review

English | [日本語](README.ja.md)

**deep-doc-review** is a plugin for [Claude Code](https://docs.claude.com/en/docs/claude-code) and [OpenAI Codex CLI](https://github.com/openai/codex) that carefully checks a technical document for mistakes. Point it at a design doc, specification, proposal, paper, contract or report, and you get back a report listing problems it found, each with the exact location, the reason and a suggested fix.

It is based on the approach described in Google Research's [Deep Review](https://research.google/blog/analyzing-technical-documents-with-deep-review/): instead of reading the document once, it splits it into sections, has several reviewers examine each section in depth at the same time, and then cross-checks and re-verifies what they found.

## What it finds

- Calculation errors: totals, percentages, units and dates are recomputed, not just read
- Contradictions between different parts of the document
- Broken logic and claims without support
- Ambiguous wording that could be read in more than one way

Every finding shows the line numbers, a quote of the passage, the evidence (for example the recalculation or the conflicting passage) and a suggested fix. Serious findings are double-checked by a separate reviewer, which removes false alarms.

It is not meant for code review or for polishing style and grammar.

## Requirements

You need Claude Code or Codex CLI, installed and signed in.

## Installation

### Claude Code

Run these in a Claude Code session:

```text
/plugin marketplace add baneido/deep-doc-review
/plugin install deep-doc-review@deep-doc-review
/reload-plugins
```

### Codex CLI

Run these in your terminal, then start a new Codex session:

```bash
codex plugin marketplace add baneido/deep-doc-review
codex plugin add deep-doc-review@deep-doc-review
```

## Quick start

Open Claude Code or Codex in the folder that contains your document and ask for a review:

```text
Deep-review docs/design.md
```

Or use the command directly:

| Claude Code | Codex CLI |
|---|---|
| `/deep-doc-review:deep-doc-review docs/design.md` | `$deep-doc-review:deep-doc-review docs/design.md` |

Supported files are Markdown, plain text, PDF and Word (`.docx`). A typical design document takes about 10 to 20 minutes; longer documents take longer.

When it finishes, open the report it tells you about. Your original document is never changed.

## Options

Add options after the file name in plain words, for example `/deep-doc-review:deep-doc-review spec.pdf lang=en depth=thorough`.

| Option | What it does | Default |
|---|---|---|
| `lang` | Language of the report: `ja` (Japanese), `en` (English) or `auto` (same as the document) | `ja` |
| `depth` | How thorough the review is: `quick`, `standard` or `thorough`. Deeper reviews take longer | `standard` |
| `focus` | Parts or aspects to concentrate on, for example `focus="numbers in chapters 3-5"` | none |
| `web` | Checks facts such as standards, prices and laws with a web search. Only short search phrases are sent, never your document. Use `web=off` to turn it off | `on` |

Note that the report is written in Japanese unless you add `lang=en` or `lang=auto`.

## Output

Results are saved in a new folder in your working directory, `.deep-doc-review/<document name>-<date and time>/`:

- `report.md`: the review report, with a summary table followed by each finding in detail
- `findings.json`: the same findings in a machine-readable format

## How it works

1. **Prepare**: the document is converted to text and every line gets a number, so each finding can point to exact lines.
2. **Split**: the document is divided into 4 to 12 sections by topic.
3. **Plan**: each section is rated by how difficult and important it is. Harder sections get more reviewers, each looking from a different angle: a general review, a recheck of every number, and a skeptical expert.
4. **Review**: the reviewers work in parallel. Each one reads the whole document but concentrates on its own section.
5. **Combine and verify**: findings are merged, checked for contradictions between sections, and duplicates are removed. Serious findings are then re-checked by a reviewer that did not report them, and anything that does not hold up is dropped.
