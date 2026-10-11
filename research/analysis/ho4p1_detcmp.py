#!/usr/bin/env python3
"""HO4-P1 cong P3-DET (ADDENDUM-6 §6.3): so md5 MANIFEST 2 lan chay doc lap (chi tai MANIFEST/result.json, nho).
Usage: ho4p1_detcmp.py <slugA> <slugB> <kind exp|oi|chain> [out.json]"""
import json, logging, os, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("detcmp")
A = "/home/ubuntu/src/BinanceFuturesJava/research/analysis"
sys.path.insert(0, A)
import ho4p1_exp_kernel as E  # noqa: E402
OD = "/home/ubuntu/claude_master/1011/ho4p1/kaggle/out/"


def get(slug):
    E.fetch(slug, r"(^|/)(MANIFEST\.json|result\.json)$")
    d = OD + slug
    res = json.load(open(d + "/result.json")) if os.path.exists(d + "/result.json") else {}
    mp = [os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs if f == "MANIFEST.json"]
    man = json.load(open(mp[0])) if mp else None
    return res, man


def main():
    a, b, kind = sys.argv[1:4]
    ra, ma = get(a)
    rb, mb = get(b)
    r = dict(a=a, b=b, kind=kind)
    if kind == "oi":
        r.update(md5_raw=[ra.get("md5_raw"), rb.get("md5_raw")], md5_gz=[ra.get("md5_gz"), rb.get("md5_gz")],
                 rows=[ra.get("rebuilt_rows"), rb.get("rebuilt_rows")])
        r["pass"] = bool(ra.get("md5_raw") and ra.get("md5_raw") == rb.get("md5_raw") and ra.get("md5_gz") == rb.get("md5_gz"))
    else:
        if kind == "exp":
            r["rc"] = [[t["name"], t["rc"]] for t in ra.get("tasks", [])] + [[t["name"], t["rc"]] for t in rb.get("tasks", [])]
            r["ok"] = [ra.get("ok"), rb.get("ok")]
        else:
            r["ok"] = [bool(ra.get("manifest")), bool(rb.get("manifest"))]
        ka, kb = set(ma or {}), set(mb or {})
        r["n_files"] = [len(ka), len(kb)]
        r["only_a"], r["only_b"] = sorted(ka - kb), sorted(kb - ka)
        diff = sorted(k for k in ka & kb if ma[k]["md5"] != mb[k]["md5"])
        r["n_equal"] = len(ka & kb) - len(diff)
        r["diff"] = diff
        r["groups"] = {}
        for k in sorted(ka | kb):
            g = k.split("/")[0] if "/" in k else k
            g = "ticker/*" if k.startswith("ticker/") else g
            e = r["groups"].setdefault(g, [0, 0])
            e[0] += 1
            e[1] += int(k in ka and k in kb and ma[k]["md5"] == mb[k]["md5"])
        r["pass"] = bool(ma and mb and all(r["ok"]) and not r["only_a"] and not r["only_b"] and not diff
                         and (kind != "exp" or all(x[1] == 0 for x in r["rc"])))
    out = sys.argv[4] if len(sys.argv) > 4 else OD + "detcmp_%s_%s.json" % (a, b)
    json.dump(r, open(out, "w"), indent=1)
    log.info("P3-DET %s %s vs %s: pass=%s %s", kind, a, b, r["pass"],
             json.dumps({k: v for k, v in r.items() if k in ("n_files", "n_equal", "diff", "only_a", "only_b", "md5_raw", "md5_gz", "groups")})[:1500])


if __name__ == "__main__":
    main()
