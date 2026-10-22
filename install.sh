#!/usr/bin/env bash
# Deep Review skill installer for Claude Code and OpenAI Codex CLI (idempotent).
# usage: ./install.sh [--claude-only|--codex-only] [--codex-legacy] [--uninstall]
#   Claude Code: ~/.claude/skills/deep-review + ~/.claude/agents/deep-review-reviewer.md
#   Codex CLI  : ~/.agents/skills/deep-review + ~/.codex/agents/deep_review_reviewer.toml
#   --codex-legacy also copies the skill to ~/.codex/skills/deep-review (older Codex builds)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/skills/deep-review"
DO_CLAUDE=1; DO_CODEX=1; LEGACY=0; UNINSTALL=0
for a in "$@"; do
  case "$a" in
    --claude-only) DO_CODEX=0 ;;
    --codex-only) DO_CLAUDE=0 ;;
    --codex-legacy) LEGACY=1 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done
[ -f "$SRC/SKILL.md" ] || { echo "skills/deep-review/SKILL.md not found next to install.sh" >&2; exit 1; }

put_skill() {  # $1 = target skills dir
  local dst="$1/deep-review"
  if [ "$UNINSTALL" = 1 ]; then rm -rf "$dst"; echo "  removed $dst"; return; fi
  mkdir -p "$1"; rm -rf "$dst"; cp -R "$SRC" "$dst"
  find "$dst" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  chmod +x "$dst"/scripts/*.py 2>/dev/null || true
  echo "  skill  -> $dst"
}
put_file() {  # $1 = src, $2 = dst dir
  if [ "$UNINSTALL" = 1 ]; then rm -f "$2/$(basename "$1")"; echo "  removed $2/$(basename "$1")"; return; fi
  mkdir -p "$2"; cp "$1" "$2/"; echo "  agent  -> $2/$(basename "$1")"
}

if [ "$DO_CLAUDE" = 1 ]; then
  if [ -d "$HOME/.claude" ] || command -v claude >/dev/null 2>&1; then
    echo "Claude Code:"
    put_skill "$HOME/.claude/skills"
    put_file "$HERE/agents/claude/deep-review-reviewer.md" "$HOME/.claude/agents"
  else
    echo "Claude Code: not found (~/.claude missing) - skipped"
  fi
fi
if [ "$DO_CODEX" = 1 ]; then
  if [ -d "$HOME/.codex" ] || command -v codex >/dev/null 2>&1; then
    echo "Codex CLI:"
    put_skill "$HOME/.agents/skills"
    [ "$LEGACY" = 1 ] && put_skill "$HOME/.codex/skills"
    put_file "$HERE/agents/codex/deep_review_reviewer.toml" "$HOME/.codex/agents"
    if [ "$LEGACY" = 0 ] && [ -d "$HOME/.codex/skills/deep-review" ] && [ "$UNINSTALL" = 0 ]; then
      echo "  note: an older copy exists at ~/.codex/skills/deep-review (may appear twice). Remove it or rerun with --codex-legacy to update it."
    fi
  else
    echo "Codex CLI: not found (~/.codex missing) - skipped"
  fi
fi
[ "$UNINSTALL" = 1 ] || echo "Done. Claude Code: /deep-review <doc>   Codex: \$deep-review <doc>"
