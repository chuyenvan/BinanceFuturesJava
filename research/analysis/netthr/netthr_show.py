import json, sys
d = json.load(open(sys.argv[1]))
print("overall_means", json.dumps({k: {m: round(v, 5) for m, v in x.items()} for k, x in d["overall_means"].items()}))
print("xs_rank_corr_vs_base", json.dumps(d["overall_xs_rank_corr"]))
print("per-fold xc ORIG vs base", [round(f["orig_vs_" + d["base"] + "_spearman_xs"], 4) for f in d["folds"].values()])
for arm, b in d["boot"].items():
    print("BOOT", arm, "n_ic_pos", b["n_folds_ic_pos"], "n_ic_ci_pos", b["n_folds_ic_ci_pos"])
    for m, o in b["overall"].items():
        print("   ", m, {k: round(v, 5) for k, v in o.items()})
print("GATE", json.dumps(d["gate"]))
