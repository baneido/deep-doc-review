#!/usr/bin/env python3
"""Deep Review helper: validate + merge pass files.
usage: merge_findings.py RUN_DIR                -> RUN/merged.json (IDs F1.., near-duplicate merge)
       merge_findings.py RUN_DIR --groups G.json -> RUN/deduped.json (apply root-cause groups {"groups":[["F1","F7"],...]})
Invalid pass files are reported (re-run that reviewer)."""
import difflib, json, re, sys
from pathlib import Path

SEV = {"critical": 0, "major": 1, "minor": 2, "info": 3}


def load_json(p: Path):
    t = p.read_text(encoding="utf-8").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.S)
        return json.loads(m.group(0)) if m else None


def norm(f, seg, job, n):
    if not isinstance(f, dict) or not str(f.get("issue", "")).strip():
        return None
    sev = str(f.get("severity", "minor")).lower().strip()
    sev = sev if sev in SEV else "minor"

    def _i(v, d):
        try:
            return max(1, min(n, int(str(v).lstrip("Ll"))))
        except Exception:
            return d
    a = _i(f.get("line_start"), 1)
    b = max(a, _i(f.get("line_end"), a))
    try:
        c = max(0.0, min(1.0, float(f.get("confidence", 0.5))))
    except Exception:
        c = 0.5
    return {"severity": sev, "category": str(f.get("category", "other")), "line_start": a, "line_end": b,
            "quote": str(f.get("quote", ""))[:200], "issue": str(f["issue"]).strip(),
            "evidence": str(f.get("evidence", "")).strip(), "suggestion": str(f.get("suggestion", "")).strip(),
            "confidence": c, "segments": [seg], "passes": [job],
            "source": "cross_check" if seg == "GLOBAL" else "segment_review"}


def similar(a, b):
    if a["line_end"] + 2 < b["line_start"] or b["line_end"] + 2 < a["line_start"]:
        return False
    q = difflib.SequenceMatcher(None, a["quote"], b["quote"]).ratio() if a["quote"] and b["quote"] else 0
    t = difflib.SequenceMatcher(None, a["issue"][:200], b["issue"][:200]).ratio()
    return q > 0.6 or t > 0.5 or (a["category"] == b["category"] and (q > 0.35 or t > 0.3))


def absorb(p, m):
    p["segments"] = sorted(set(p["segments"]) | set(m["segments"]))
    p["passes"] = sorted(set(p["passes"]) | set(m["passes"]))
    p["confidence"] = max(p["confidence"], m["confidence"])
    if (m["line_start"], m["line_end"]) != (p["line_start"], p["line_end"]):
        p.setdefault("related_lines", []).append(f"L{m['line_start']}-L{m['line_end']}")
    p.setdefault("alt_descriptions", []).append(m["issue"][:300])
    if m.get("source") == "cross_check":
        p["source"] = p.get("source", "segment_review")
    p["support"] = len(p["passes"])


def main():
    run = Path(sys.argv[1]).expanduser()
    if "--groups" in sys.argv:
        groups = load_json(Path(sys.argv[sys.argv.index("--groups") + 1]))["groups"]
        fs = json.loads((run / "merged.json").read_text(encoding="utf-8"))["findings"]
        by, seen, out = {f["id"]: f for f in fs}, set(), []
        for g in groups:
            mem = sorted([by[i] for i in g if i in by and i not in seen], key=lambda f: (SEV[f["severity"]], -f["confidence"]))
            if not mem:
                continue
            seen.update(m["id"] for m in mem)
            p = dict(mem[0])
            for m in mem[1:]:
                absorb(p, m)
            out.append(p)
        out += [f for f in fs if f["id"] not in seen]
        (run / "deduped.json").write_text(json.dumps({"findings": out}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"deduped: {len(fs)} -> {len(out)}")
        return
    n = sum(1 for _ in (run / "doc.txt").open(encoding="utf-8"))
    raw, bad = [], []
    for p in sorted((run / "passes").glob("*.json")):
        d = load_json(p)
        if d is None:
            bad.append(p.name)
            continue
        items = d.get("findings", []) if isinstance(d, dict) else d if isinstance(d, list) else []
        seg = (d.get("segment") if isinstance(d, dict) else None) or p.stem.split("_")[0]
        job = (d.get("job") if isinstance(d, dict) else None) or p.stem
        raw += [x for x in (norm(f, seg, job, n) for f in items) if x]
    merged = []
    for f in sorted(raw, key=lambda x: (SEV[x["severity"]], -x["confidence"])):
        for m in merged:
            if similar(m, f):
                absorb(m, f)
                break
        else:
            f["support"] = 1
            merged.append(f)
    merged.sort(key=lambda f: (SEV[f["severity"]], f["line_start"]))
    for k, f in enumerate(merged, 1):
        f["id"] = f"F{k}"
    (run / "merged.json").write_text(json.dumps({"findings": merged}, ensure_ascii=False, indent=1), encoding="utf-8")
    brief = "\n".join(f"- {f['id']} [{f['severity']}/{f['category']}] L{f['line_start']}-L{f['line_end']}: "
                      f"{f['issue'][:240]} | evidence: {f['evidence'][:200]}" for f in merged)
    (run / "merged_brief.txt").write_text(brief + "\n", encoding="utf-8")
    print(json.dumps({"pass_files": len(list((run / 'passes').glob('*.json'))), "invalid": bad,
                      "raw": len(raw), "merged": len(merged)}, ensure_ascii=False))
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
