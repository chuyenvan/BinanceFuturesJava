#!/usr/bin/env python3
"""MAPAUD: gom ket qua (dump/hist/settle/hashorder + so lieu log live doc tay) -> docs/audit/MAPPER_AUDIT_20261011.json.
Usage: mapaud_report.py <mapaud_dir> <out_json>"""
import json, sys
D, OUT = sys.argv[1], sys.argv[2]
L = lambda f: json.load(open(f"{D}/{f}"))
hist = L("mapaud_hist.json")
settle = L("mapaud_settle.json")
# Log 242 v_t_m (full.log tu 2026-08-12, logt9 09-01..09-10, nohup.out.bak 09-14..09-28, nohup.out) — dem dong, CHI DOC.
LIVE = {"MUUUSDT": [1, 1, 2], "XBIUSDT": [1, 1, 2], "BNCUSDT": [125, 16, 13], "SOXSUSDT": [79, 0, 0], "FWDIUSDT": [10, 4, 6],
        "TZAUSDT": [0, 0, 0], "MINIMAXUSDT": [49, 4, 8], "VRTUSDT": [1, 1, 2], "SNOWUSDT": [25, 1, 2], "ZHIPUUSDT": [3, 3, 4],
        "APPUSDT": [0, 0, 0], "SHAZUSDT": [22, 1, 2], "GEVUSDT": [2, 2, 4], "SOFIUSDT": [4, 4, 6], "PANWUSDT": [2, 0, 0],
        "SKHYUSDT": [0, 0, 0]}
out = dict(
    audit="MAPAUD 2026-10-11",
    mapper_live_242=dict(L("mapaud_dump_summary.json")["242"], host="103.157.218.242:3222", ns="ticker", set="symbol_mapper",
                         key="global_id_map", sha_def="sha256 cua chuoi 'symbol,id\\n' sap theo symbol"),
    snapshots={k: {x: v[x] for x in ("n", "max_id", "n_ids", "sha", "dups", "missing", "only_here", "diff_vs_live") if x in v}
               for k, v in hist.items()},
    live_log_counts_pass_push_buyLines=LIVE,
    live_log_note="buyLines = so dong 'Create order market BUY'/'Create Order market .. BUY' (moi lenh ~2 dong); pass = 'AI PASS'",
    hashmap_victim_estimate=L("mapaud_hashorder.json"),
    settle=dict(counts=settle["counts"], rule=settle["rule"], n_rec_242=settle["n_rec_242"], universe_n=settle.get("universe_n"),
                universe_qv_by_month=settle.get("universe_qv_by_month"), nham_cut_share_by_month=settle.get("nham_cut_share_by_month"),
                syms={s: {k: r[k] for k in ("cls", "from_day", "vision_last_row", "vision_last_nonzero", "vision_days_vol_after",
                                             "cut_qv_2026q1q3", "a242_last_present", "a242_last_nonzero", "a242_days_vol_after",
                                             "pin_status")} for s, r in settle["syms"].items()}),
    mvn_test=dict(before=dict(tests=264, classes=45, fail=0), after=dict(tests=273, classes=46, fail=0)))
json.dump(out, open(OUT, "w"), indent=1, sort_keys=True)
print("ok", OUT)
