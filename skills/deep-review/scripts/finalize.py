#!/usr/bin/env python3
"""Deep Review helper: apply verifier verdicts and write RUN/findings.json.
usage: finalize.py RUN_DIR
reads deduped.json (or merged.json), verdicts_*.json, segments.json, plan.json, meta.json, summary.json (optional).
Output shape matches the deep_review.py tool (summary/findings/segments/stats)."""
import json, sys, time
from pathlib import Path

SEV = {"critical": 0, "major": 1, "minor": 2, "info": 3}
run = Path(sys.argv[1]).expanduser()
rd = lambda name, d=None: json.loads((run / name).read_text(encoding="utf-8")) if (run / name).exists() else d
src = rd("deduped.json") or rd("merged.json")
fs = src["findings"]
verd = {}
for p in sorted(run.glob("verdicts*.json")):
    for v in (json.loads(p.read_text(encoding="utf-8")).get("verdicts") or []):
        verd[str(v.get("id"))] = v
for f in fs:
    v = verd.get(f["id"])
    if not v:
        f.setdefault("verdict", "unverified")
        continue
    vv = str(v.get("verdict", "uncertain")).lower()
    f["verdict"] = vv if vv in ("confirmed", "rejected", "uncertain") else "uncertain"
    f["verify_note"] = str(v.get("note", ""))
    s = str(v.get("severity", f["severity"])).lower()
    if f["verdict"] == "confirmed" and s in SEV and s != f["severity"]:
        f["original_severity"], f["severity"] = f["severity"], s
fs.sort(key=lambda f: (f["verdict"] == "rejected", SEV[f["severity"]], f["line_start"]))
meta = rd("meta.json", {})
segs = rd("segments.json", {}).get("segments", [])
plan = rd("plan.json", {}) or {}
for s in segs:
    b = next((x for x in plan.get("segments", []) if x.get("id") == s.get("id")), None)
    if b:
        s.update({k: b[k] for k in ("difficulty", "passes", "rationale") if k in b})
now = time.time()
kept = [f for f in fs if f["verdict"] != "rejected"]
stats = {"engine": "agent-native skill", "input_lines": meta.get("lines"), "segments": len(segs),
         "review_jobs": len(list((run / "passes").glob("*.json"))),
         "findings_kept": len(kept), "findings_rejected": len(fs) - len(kept),
         "by_severity": {k: sum(1 for f in kept if f["severity"] == k) for k in SEV},
         "wall_clock_sec": round(now - float(meta.get("started_at", now)), 1),
         "stage_wall_clock_sec": meta.get("stage_times", {}), "usage_total": "n/a (agent session)"}
summary = rd("summary.json") or (rd("findings.json", {}) or {}).get("summary") or \
    {"overall_assessment": "", "top_priorities": [], "strengths": [], "verdict": "n/a"}
(run / "findings.json").write_text(json.dumps({"summary": summary, "findings": fs, "segments": segs, "stats": stats},
                                              ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(stats, ensure_ascii=False))
