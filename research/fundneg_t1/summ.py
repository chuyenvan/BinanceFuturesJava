import json
r = json.load(open("/home/ubuntu/claude_master/fundneg_t1_wk/out/results.json"))
print(json.dumps(r["meta"]))
for nm, v in r["variants"].items():
    print("=" * 20, nm, v["criteria"])
    print({k: v[k] for k in ["raw_counts", "n_beyond_data", "n_no_entry", "n_no_exit", "n_dropped_onepos", "n_trades_all", "n_pool_whole_universe", "pool_size_med"]})
    for k in ["NON_DISC", "NON_TEST", "ALL_DISC", "ALL_TEST"]:
        s = v[k]
        print(k, "n=%d yrs=%s mean=%.5f med=%.5f hit=%.3f net2=%.5f gross=%.5f fund=%.5f nset=%.2f CI=[%.5f,%.5f] ndays=%d ctrl50=%.5f ctrl95=%.5f mfe=%.4f mae=%.4f" % (
            s["n"], s["n_by_year"], s["mean_net"], s["median_net"], s["hit"], s["mean_net2"], s["mean_gross"], s["mean_fund"], s["mean_nset"],
            s["ci95_day"][0], s["ci95_day"][1], s["n_days"], s["ctrl_mean_p50"], s["ctrl_mean_p95"], s["mfe_med"], s["mae_med"]))
        print("   byyear", {y: round(m, 5) for y, m in s["mean_by_year"].items()}, "nsym", s["n_sym"], "top5", s["top5_sym"], "top5n %.3f top5sum %.3f exTop5 %.5f" % (s["top5_share_n"], s["top5_share_sumnet"], s["mean_net_ex_top5"]))
        print("   btc7 p=%.3f s=%.3f hold p=%.3f share7neg=%.3f m7neg=%.5f m7pos=%.5f after_x14=%d delist=%d gap=%d ctrlnan=%d" % (
            s["corr_btc7_pearson"], s["corr_btc7_spearman"], s["corr_btchold_pearson"], s["share_btc7_neg"], s["mean_net_btc7_neg"], s["mean_net_btc7_pos"], s["n_after_x14_stop"], s["n_delist"], s["n_gap"], s["ctrl_nan_events"]))
        print("   sleeve", s["sleeve"])
