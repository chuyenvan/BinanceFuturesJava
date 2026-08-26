#!/usr/bin/env python3
# Phan tich sau results CPCV v1 (1600 cell) -> analysis_v1.json + in tom tat.
import json, statistics as st, sys, collections

RES = "/home/ubuntu/cpcv/wf_full/results_jobstore.jsonl"
rows = [json.loads(l) for l in open(RES) if l.strip()]
BLOCKS = sorted({r["block"] for r in rows})
CONFIGS = sorted({r["seq"] for r in rows})
GENES = sorted(rows[0]["knobs"].keys())

def cal(r): return r["metrics"]["calmar"]
def note(r): return r["metrics"].get("note", "?")

# ---- per-block ----
block_stats = {}
for b in BLOCKS:
    cs = [cal(r) for r in rows if r["block"] == b]
    ns = [note(r) for r in rows if r["block"] == b]
    block_stats[b] = {
        "n": len(cs), "median": round(st.median(cs), 4), "mean": round(st.mean(cs), 4),
        "pct_pos": round(sum(c > 0 for c in cs) / len(cs), 3),
        "pct_success": round(ns.count("SUCCESS") / len(ns), 3),
        "pct_burn": round(ns.count("BURN_ACCOUNT") / len(ns), 3),
    }

# ---- per-config (median calmar qua 8 block, on dinh) ----
cfg = {}
for s in CONFIGS:
    rs = [r for r in rows if r["seq"] == s]
    cs = [cal(r) for r in rs]
    cfg[s] = {
        "median": st.median(cs), "mean": st.mean(cs),
        "std": st.pstdev(cs) if len(cs) > 1 else 0.0,
        "pct_block_pos": sum(c > 0 for c in cs) / len(cs),
        "n_burn": sum(note(r) == "BURN_ACCOUNT" for r in rs),
        "knobs": rs[0]["knobs"],
        "objective": st.median(cs) - 0.5 * (st.pstdev(cs) if len(cs) > 1 else 0.0),
    }
ranked = sorted(CONFIGS, key=lambda s: cfg[s]["objective"], reverse=True)
top = [{"seq": s, "obj": round(cfg[s]["objective"], 4), "median": round(cfg[s]["median"], 4),
        "std": round(cfg[s]["std"], 4), "pct_block_pos": round(cfg[s]["pct_block_pos"], 3),
        "n_burn": cfg[s]["n_burn"]} for s in ranked[:12]]
bottom = [{"seq": s, "obj": round(cfg[s]["objective"], 4), "median": round(cfg[s]["median"], 4),
           "n_burn": cfg[s]["n_burn"]} for s in ranked[-8:]]

# ---- gene correlation (gia tri gene per config vs objective config) ----
def pearson(xs, ys):
    n = len(xs); mx = sum(xs)/n; my = sum(ys)/n
    num = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
    dx = (sum((x-mx)**2 for x in xs))**0.5; dy = (sum((y-my)**2 for y in ys))**0.5
    return round(num/(dx*dy), 3) if dx > 0 and dy > 0 else 0.0
objs = [cfg[s]["objective"] for s in CONFIGS]
gene_corr = {}
for g in GENES:
    gv = [cfg[s]["knobs"][g] for s in CONFIGS]
    gene_corr[g] = pearson(gv, objs)
gene_corr = dict(sorted(gene_corr.items(), key=lambda kv: -abs(kv[1])))

# ---- overall ----
allc = [cal(r) for r in rows]
alln = [note(r) for r in rows]
overall = {
    "n_cells": len(rows), "n_configs": len(CONFIGS), "n_blocks": len(BLOCKS),
    "calmar_median": round(st.median(allc), 4), "calmar_mean": round(st.mean(allc), 4),
    "pct_cell_pos": round(sum(c > 0 for c in allc)/len(allc), 3),
    "note_dist": dict(collections.Counter(alln)),
    "n_config_median_pos": sum(cfg[s]["median"] > 0 for s in CONFIGS),
    "n_config_allblock_pos": sum(cfg[s]["pct_block_pos"] == 1.0 for s in CONFIGS),
}
out = {"overall": overall, "block_stats": block_stats, "gene_corr": gene_corr,
       "top_configs": top, "bottom_configs": bottom}
json.dump(out, open("/home/ubuntu/cpcv/analysis_v1.json", "w"), indent=2)
print(json.dumps(out, indent=2))
