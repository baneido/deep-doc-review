#!/usr/bin/env python3
"""Deep Review helper: verify RUN/segments.json covers every non-blank line. usage: check_segments.py RUN_DIR
Exit 0 = OK, 1 = gaps/invalid (printed)."""
import json, sys
from pathlib import Path

run = Path(sys.argv[1]).expanduser()
lines = (run / "doc.txt").read_text(encoding="utf-8").split("\n")
if lines and lines[-1] == "":
    lines.pop()
n = len(lines)
segs = json.loads((run / "segments.json").read_text(encoding="utf-8"))
segs = segs.get("segments", segs) if isinstance(segs, dict) else segs
cov = [False] * (n + 2)
problems = []
for s in segs:
    a, b = int(s["start_line"]), int(s["end_line"])
    if a < 1 or b > n or a > b:
        problems.append(f"{s.get('id')}: bad range {a}-{b} (doc has {n} lines)")
    for i in range(max(1, a), min(n, b) + 1):
        cov[i] = True
gaps, i = [], 1
while i <= n:
    if not cov[i] and lines[i - 1].strip():
        j = i
        while j + 1 <= n and not cov[j + 1]:
            j += 1
        gaps.append(f"L{i}-L{j}")
        i = j + 1
    else:
        i += 1
if gaps:
    problems.append("uncovered non-blank lines: " + ", ".join(gaps))
print(json.dumps({"lines": n, "segments": len(segs), "ok": not problems, "problems": problems}, ensure_ascii=False))
sys.exit(1 if problems else 0)
