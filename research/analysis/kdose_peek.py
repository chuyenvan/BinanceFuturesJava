import json, sys
a = json.load(open("/home/ubuntu/claude_master/1010/kdose/kdose_post.json"))
print("D", a["D"]["sum"], a["den"], a["entry_check"])
for k, v in a["agg"].items():
    out = {x: (round(v[x]["mean"], 3), round(v[x]["lo"], 3), round(v[x]["hi"], 3)) for x in
           ("G0_flip_pass_pct", "G1_42_flip_pass_pct", "G2_flip_pass_pct", "dpnl_pct", "dpnl_usd", "entry_frac_aff",
            "entry_mean_bps_all", "entry_mean_bps_aff", "entry_mean_abs_bps_aff", "s1_K24_top_changed_pct",
            "s1_K24_bot_changed_pct", "s1_K16_top_changed_pct", "s1_K24_top_jac", "G1_8seed_flip_pass_pct",
            "G1_42_min_any_pct", "G1_42_dq_p99", "dp15_p50", "dp15_p99")}
    print(k, v["n"], v["econ_add_rem"], json.dumps(out))
