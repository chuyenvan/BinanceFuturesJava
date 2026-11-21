#!/usr/bin/env python3
"""rt_lchk.py <lane p|s|m> <seed> (fork rt_nchk.py, U4a PREREG_RETRAIN_DIAG 436977c1; HOLDOUT_UNSEAL_2026_1121 (U4a)) - ADD3 A3-4(4): kiem chung KHONG lo PnL Q3 cho Lane N (HOLDOUT_UNSEAL_2026_1121 e9095a02, U2).
CHI in so dem / True-False / hash dau vao. KHONG doc gia tri dong printDone co end >= 2026-07-01 00:00 +07 (chi kiem NaN dang bool),
KHONG in b_final / n_trades / equity / md5_printdone."""
import csv, datetime as dt, gzip, json, math, os, re, sys
ln, s = sys.argv[1].lower(), sys.argv[2].lower()
N = "/home/ubuntu/claude_master/w3/retrain/out/lane/sim/rt-%s-l26-%s" % (ln, s)
L = "/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-%s" % s
CUTS = "20260701 00:00"
WANT = {"jar": "cc0f9d11ef6b865e9070e79b3111f6786ca7008a8c4a3a28571f54322e1b1dfe",
        "bins": json.load(open("/home/ubuntu/claude_master/w3/retrain/out/lane/DATA26_%s.json" % ln.upper()))["bins26_sha"],
        "fsnap": "fb024c404c840a786742bacb3e6b46075ed8c057db9a425ac8550b62aff8491c", "fovl": "207e7c60388dca1f48cfd578c97c50eaec311c6c49e0a92581a948c89a39f300",
        "msnap": "5c436e65a1314118ba9e19e79185f9f22e11d1d76e3f8bf1ebf898d782de665d", "movl": "6143fa754a1f595ed1c4810289ed4882d7f8e17d1ea3ce01854ea2c2d347a96b"}
UPD = re.compile(r"Update (\d{8}) 07:00 => ")
def upd(d):
    p = [c for c in (d + "/logs/sim.out.gz", d + "/logs/sim.out") if os.path.exists(c)][0]
    op = gzip.open if p.endswith(".gz") else open
    out = {}
    with op(p, "rt", errors="replace") as f:
        for ln in f:
            m = UPD.search(ln)
            if m:
                out[m.group(1)] = ln[ln.index("Update"):].rstrip("\n")
    return out
rn, rl = json.load(open(N + "/result.json")), json.load(open(L + "/result.json"))
h, hl = rn.get("ho5", {}), rl.get("ho5", {})
c = {"seed": s, "ok": rn.get("ok") is True, "java_rc": rn.get("java_rc"), "date_last_ge_20260929": str(rn.get("date_last", "")) >= "20260929",
     "jar": rn.get("jar_sha256") == WANT["jar"], "mapper": rn.get("ho5_mapper", {}).get("snap_sha256") == WANT["msnap"] and rn.get("ho5_mapper", {}).get("overlay_sha256") == WANT["movl"],
     "fund_snap": rn.get("ho5_funding", {}).get("snap_sha256") == WANT["fsnap"] and rn.get("ho5_funding", {}).get("overlay_sha256") == WANT["fovl"],
     "bins26": h.get("bins26_sha") == WANT["bins"], "unseal_ref_U4a": "U4a" in str(h.get("unseal_ref")),
     "pred_n2026": h.get("pred", {}).get("n_2026"), "pred_nan2026": h.get("pred", {}).get("nan_2026"),
     "pred_src_eq_L": h.get("pred", {}).get("src_md5") == hl.get("pred", {}).get("src_md5"),
     "pred_ndev_eq_L": h.get("pred", {}).get("n_dev") == hl.get("pred", {}).get("n_dev"),
     "market_eq_L": h.get("market") == hl.get("market"),
     "funding_pre_eq_dev": h.get("funding", {}).get("pre_md5_new") == h.get("funding", {}).get("pre_md5_dev") == hl.get("funding", {}).get("pre_md5_new"),
     "profile_hash_eq_L": rn.get("profile_hash") == rl.get("profile_hash"), "overrides_eq_L": rn.get("overrides") == rl.get("overrides"),
     "r1a3_bins_eq_L": rn.get("r1_a3", {}).get("bins_sha256") == rl.get("r1_a3", {}).get("bins_sha256")}
F = lambda x: dt.datetime.strptime(x.strip(), "%Y%m%d %H:%M")
cut = F(CUTS)
hdr_n = open(N + "/storage/printDone.csv").readline(); hdr_l = open(L + "/storage/printDone.csv").readline()
pn = list(csv.DictReader(open(N + "/storage/printDone.csv"))); pl = list(csv.DictReader(open(L + "/storage/printDone.csv")))
bn = [r for r in pn if F(r["end"]) < cut]; bl = [r for r in pl if F(r["end"]) < cut]
c["printdone_header_eq"] = hdr_n == hdr_l
c["n_rows_end_lt_0701_N"], c["n_rows_end_lt_0701_L"] = len(bn), len(bl)
c["rows_end_lt_0701_identical_ordered"] = bn == bl
def bad(v):
    try:
        return math.isnan(float(v))
    except Exception:
        return True
c["no_nan_pnl_start_end_all_rows"] = not any(bad(r["pnl"]) or not r["start"].strip() or not r["end"].strip() for r in pn)
un, ul = upd(N), upd(L)
c["n_update_2026"] = sum(1 for k in un if k >= "20260101"); c["n_update_2026_L"] = sum(1 for k in ul if k >= "20260101")
c["update_le_20260630_identical"] = {k: v for k, v in un.items() if k <= "20260630"} == {k: v for k, v in ul.items() if k <= "20260630"}
c["update_dates_eq_L"] = sorted(un) == sorted(ul)
must = ["ok", "unseal_ref_U4a", "date_last_ge_20260929", "jar", "mapper", "fund_snap", "bins26", "pred_src_eq_L", "pred_ndev_eq_L", "market_eq_L", "funding_pre_eq_dev",
        "profile_hash_eq_L", "overrides_eq_L", "r1a3_bins_eq_L", "printdone_header_eq", "rows_end_lt_0701_identical_ordered", "no_nan_pnl_start_end_all_rows",
        "update_le_20260630_identical", "update_dates_eq_L"]
c["PASS"] = all(c[k] is True for k in must) and c["pred_n2026"] == 393120 and c["pred_nan2026"] == 0 and c["n_update_2026"] == c["n_update_2026_L"]
c["lane"] = ln
json.dump(c, open(N + "/check_lane.json", "w"), indent=1)
print(json.dumps(c))
