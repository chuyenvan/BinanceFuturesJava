import json
R = json.load(open("/home/ubuntu/claude_master/tsx_v2/out/phaseB.json"))
V = R["variants"]
print("CHECKS", json.dumps({k: v for k, v in R["checks"].items() if k != "K6_on_days"}))
print("| Ô | ngày ON | Δ/seed vs X14 | seed > 0 | cụm ảnh hưởng/seed | LOO min (đợt) | CI95 theo đợt (n đợt) | LUNA | 06/2024 | Δ vs P0 (seed>0) | (i)(ii)(iii)(iv)(v) |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for k, v in V.items():
    ru = v.get("rule")
    rs = "".join("✔" if ru[x] else "✘" for x in ("i", "ii", "iii", "iv", "v")) if ru else "–"
    print("| %s | %d | %+.0f | %d/8 | %.1f | %+.0f (%s) | [%+.0f; %+.0f] (%d) | %+.0f | %+.0f | %+.0f (%d/8) | %s |" % (
        k, v["on_days"], v["delta_mean"], v["n_pos_seed"], v["n_aff_seed"], v["loo_min"], v["loo_min_ep"], v["ci95"][0], v["ci95"][1],
        v["n_ep"], v["d_luna"], v["d_0624"], v["dP0_mean"], v["dP0_npos"], rs))
print()
print("SEEDS")
for k, v in V.items():
    print(k, {s: round(x) for s, x in v["delta_seed"].items()})
print()
print("EP")
eps = sorted({e for v in V.values() for e in v["delta_ep"]})
print("| Ô | " + " | ".join(e[:7] + "…" + e[-5:] for e in eps) + " |")
for k, v in V.items():
    if k == "BASE":
        continue
    print("| %s | " % k + " | ".join(("%+.0f" % v["delta_ep"][e]) if e in v["delta_ep"] else "·" for e in eps) + " |")
print()
print("B4 grid d / dP0")
for thr in ("-0.25", "-0.30", "-0.35"):
    print(thr, [(L, round(R["B4_grid"]["%s/%d" % (thr, L)]["d"]), round(R["B4_grid"]["%s/%d" % (thr, L)]["dP0"]), R["B4_grid"]["%s/%d" % (thr, L)]["dP0_npos"], R["B4_grid"]["%s/%d" % (thr, L)]["on"]) for L in (20, 30, 45)])
print("plateau", R["B4_plateau_ok"], "cands", R["candidates"], "pick", R["pick"])
