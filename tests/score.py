#!/usr/bin/env python3
"""findings.json を planted_errors.json と突き合わせる簡易スコアラ（キーワード規則ベース。最終判断は目視で確認）。
python3 tests/score.py out_dir/findings.json"""
import json, re, sys

RULES = {
    "P1": lambda t: ("4,620" in t or "4620" in t) and ("4,520" in t or "4520" in t),
    "P2": lambda t: ("4,800" in t or "4800" in t) and any(x in t for x in ("4,520", "4520", "4,620", "4620")),
    "P3": lambda t: ("NFR-3" in t or "外部クラウド" in t or "社外" in t) and ("LLM" in t or "米国" in t or "API" in t),
    "P4": lambda t: ("30%" in t or "30 %" in t or "すべて" in t) and any(x in t for x in ("出典", "根拠", "裏付け", "一般化", "引用", "unsupported", "検証")),
    "P5": lambda t: ("4 月 1 日" in t or "4月1日" in t or "2027-04" in t or "4月" in t) and ("6 月 1 日" in t or "6月1日" in t or "6月" in t),
    "P6": lambda t: ("15 分" in t or "15分" in t) and ("1 時間" in t or "1時間" in t or "60 分" in t or "60分" in t),
    "P8b_payback": lambda t: ("1.5 年" in t or "1.5年" in t) and any(x in t for x in ("回収", "payback")),
}
FP_SUSPECT = {
    "7.2億は正しい": lambda t: "7.2" in t and any(x in t for x in ("誤り", "間違", "正しくは")) and "回収" not in t,
    "12TB は十分": lambda t: ("12 TB" in t or "12TB" in t) and any(x in t for x in ("不足", "足りない")),
}

def main(path):
    d = json.load(open(path))
    fs = d["findings"]
    kept = [f for f in fs if f.get("verdict") != "rejected"]
    rej = [f for f in fs if f.get("verdict") == "rejected"]
    hits = {k: [] for k in RULES}
    unmatched = []
    for f in kept:
        t = " ".join(str(f.get(k, "")) for k in ("quote", "issue", "evidence", "suggestion", "category"))
        m = [k for k, r in RULES.items() if r(t)]
        for k in m:
            hits[k].append(f["id"])
        if not m:
            unmatched.append(f)
        for name, r in FP_SUSPECT.items():
            if r(t):
                print(f"  !! FP 疑い ({name}): {f['id']} {f['issue'][:100]}")
    rej_hits = {k: [f["id"] for f in rej if r(" ".join(str(f.get(x, "")) for x in ("quote", "issue", "evidence")))] for k, r in RULES.items()}
    core = [k for k in RULES if k.startswith("P") and k[1].isdigit()]
    caught = [k for k in core if hits[k]]
    print(f"caught {len(caught)}/{len(core)}: " + ", ".join(f"{k}={hits[k] or '-'}" for k in RULES))
    print("missed:", [k for k in core if not hits[k]], " / 棄却された中の正解:", {k: v for k, v in rej_hits.items() if v})
    print(f"kept={len(kept)} rejected={len(rej)} 未対応(要目視: 妥当な追加指摘 or 誤検出)={len(unmatched)}")
    for f in unmatched:
        print(f"  - {f['id']} [{f['severity']}/{f['category']}] L{f['line_start']}: {f['issue'][:160]}")
    s = d["stats"]
    print("wall", s["wall_clock_sec"], "s; stages", s["stage_wall_clock_sec"])
    print("usage", s["usage_total"])

main(sys.argv[1])
