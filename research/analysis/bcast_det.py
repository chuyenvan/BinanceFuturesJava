#!/usr/bin/env python3
"""BCAST (PREREG_BACKCAST_RESERVOIR 596c1ef8 §5): P3-DET (MANIFEST md5 2 lan chay) + kiem B1 + arts cho sim ky thuat.
Chi dem/md5/NaN/khoang ts — khong PnL. Usage: bcast_det.py cmp <tag_a> <tag_b> | x <tag> | ch <tag> | arts <x_tag> <ch_tag>"""
import json, logging, os, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("bcast_det")
W = "/home/ubuntu/claude_master/1012/bcast"
O = W + "/kaggle/out/%s/"


def man(tag):
    for p in (O % tag + "out/MANIFEST.json", O % tag + "MANIFEST.json"):
        if os.path.exists(p):
            return json.load(open(p))
    raise FileNotFoundError(tag)


def cmp(a, b):
    A, B = man(a), man(b)
    keys = sorted(set(A) | set(B))
    diff = [k for k in keys if A.get(k, {}).get("md5") != B.get(k, {}).get("md5")]
    r = dict(a=a, b=b, n_a=len(A), n_b=len(B), n_equal=len(keys) - len(diff), diff=diff[:50], pass_=(not diff and len(A) == len(B) > 0))
    json.dump(r, open(W + "/det_%s_%s.json" % (a, b), "w"), indent=1)
    log.info("P3-DET %s vs %s: n=%d/%d equal=%d diff=%d pass=%s %s", a, b, len(A), len(B), r["n_equal"], len(diff), r["pass_"], diff[:5])


def x(tag):
    rj = json.load(open(O % tag + "result.json"))
    st = rj["steps"]
    tk = json.load(open(O % tag + "out/ticker_raw_md5.json"))
    days = st["klines"]["days"]
    r = dict(ok=rj.get("ok"), tasks={t["name"]: t["rc"] for t in rj["tasks"]}, manifest_n=rj.get("manifest_n"), n_ticker=len(tk),
             n_min_lt1440=sorted(d for d, v in days.items() if v["n_min"] < 1440), syms_by_day_min=min(v["n_sym"] for v in days.values()),
             syms_by_day_max=max(v["n_sym"] for v in days.values()), uni_month=st["klines"]["uni_month"],
             settle_tail=sorted(st.get("settle_tail", {})), no_funding=st.get("no_funding_vision"), funding_F=st.get("funding_F", {}).get("dev_pts"),
             closes1h=st.get("closes1h"), lifecycle=st.get("lifecycle"), ingest_rc=st["ingest"]["rc"],
             outputs={t["name"]: t.get("outputs") for t in rj["tasks"]})
    json.dump(r, open(W + "/x_%s.json" % tag, "w"), indent=1)
    log.info("X %s ok=%s tasks=%s n_ticker=%d days<1440=%d sym/day %d..%d settle=%s nofund=%s manifest=%s", tag, r["ok"], r["tasks"],
             r["n_ticker"], len(r["n_min_lt1440"]), r["syms_by_day_min"], r["syms_by_day_max"], r["settle_tail"], r["no_funding"], r["manifest_n"])


def ch(tag):
    rj = json.load(open(O % tag + "result.json"))
    s = rj["steps"]
    log.info("CH %s ok=%s secs=%s oi=%s gate=%s", tag, rj.get("ok"), rj.get("secs"), {k: v for k, v in s["oi"].items() if k != "syms"},
             {k: v for k, v in s["gate"].items() if k not in ("rows_by_month",)})
    log.info("CH pred=%s market=%s", {k: (v["md5"][:8], v["n"], v["nan"]) for k, v in s["pred"].items()},
             {k: v for k, v in s["market"].items()})
    log.info("CH net015=%s", {k: (v["n_rows"], v["nan"], v["oi_nan_rows"], v["md5"][:8]) for k, v in s["net015"].items()})
    log.info("CH featv2=%s s1=%s not781=%s", s["featv2"], s["s1"], s["closes_syms_not_in_781"])
    log.info("CH bins=%s excl=%s cov=%s", s["bins"], s["excl_no_funding"], s["bins_syms_by_month"])


def arts(xt, ct):
    tk = json.load(open(O % xt + "out/ticker_raw_md5.json"))
    rj = json.load(open(O % ct + "result.json"))
    bm = {k: v["md5"] for k, v in rj["manifest"].items() if k.startswith("bins/")}
    A = dict(x_slug=xt, chain_slug=ct, tk_md5=tk, pred_s42=rj["steps"]["pred"]["42"]["md5"],
             bins_md5={os.path.basename(k): v for k, v in bm.items()})
    json.dump(A, open(W + "/arts.json", "w"), indent=1)
    log.info("ARTS tk=%d bins=%s pred42=%s", len(tk), A["bins_md5"], A["pred_s42"])


if __name__ == "__main__":
    f = {"cmp": cmp, "x": x, "ch": ch, "arts": arts}[sys.argv[1]]
    f(*sys.argv[2:])
