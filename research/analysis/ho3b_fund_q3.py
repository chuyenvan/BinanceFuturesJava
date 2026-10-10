#!/usr/bin/env python3
"""HO3b (ADDENDUM-4 quyet dinh 2): funding_data cho exporter Q3 = ban sao store local (CHI DOC, tu asdata_local.pkl)
HOP voi Vision fundingRate monthly 2026-06..2026-09 (gia tri Vision ghi de khi trung ms; key = calc_time ms).
37 symbol khong co tren Vision giu nguyen ban local (khong them gi). Ghi pickle {"funding_data": [(sym, {"f_data": snappy(json)})]}.
Chi dem; KHONG in gia tri. Usage: ho3b_fund_q3.py <out.pkl>"""
import io, json, logging, pickle, re, sys, urllib.parse, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
import cramjam
import numpy as np
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho3b_fq3")
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
PREF = "data/futures/um/monthly/fundingRate/"
VURL = "https://data.binance.vision/data/futures/um/monthly/fundingRate/{s}/{s}-fundingRate-{m}.zip"
MONTHS = ["2026-06", "2026-07", "2026-08", "2026-09"]


def http(u):
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "ho3b"}), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:  # noqa: BLE001
            pass
    raise IOError(u)


def list_syms():
    out, marker = set(), ""
    while True:
        x = http(S3 + "?delimiter=/&prefix=" + PREF + ("&marker=" + urllib.parse.quote(marker) if marker else "")).decode()
        ps = re.findall(r"<Prefix>(.*?)</Prefix>", x)
        for p in ps:
            s = p[len(PREF):].strip("/")
            if s:
                out.add(urllib.parse.unquote(s))
        if "<IsTruncated>true</IsTruncated>" not in x:
            break
        m = re.search(r"<NextMarker>(.*?)</NextMarker>", x)
        marker = m.group(1) if m else ps[-1]
    return sorted(out)


def vision(sym):
    out, miss = {}, 0
    q = urllib.parse.quote(sym)
    for m in MONTHS:
        b = http(VURL.format(s=q, m=m))
        if b is None:
            miss += 1
            continue
        z = zipfile.ZipFile(io.BytesIO(b))
        for ln in z.read(z.namelist()[0]).decode().splitlines():
            p = ln.split(",")
            if len(p) < 3 or not p[0].strip().isdigit():
                continue
            out[int(p[0])] = float(np.float32(float(p[2])))
    return out, miss


def main():
    d = pickle.load(open("/home/ubuntu/claude_master/1003/ho3b/ds_asdata/asdata_local.pkl", "rb"))
    loc = {}
    for k, b in d["funding_data"]:
        m = json.loads(bytes(cramjam.snappy.decompress_raw(bytes(b["f_data"])))) if b.get("f_data") else {}
        loc[k] = {int(t): float(v) for t, v in m.items()}
    vs = list_syms()
    log.info("local %d symbol, vision listing %d symbol", len(loc), len(vs))
    with ThreadPoolExecutor(12) as ex:
        V = dict(zip(vs, ex.map(vision, vs)))
    rows, st = [], dict(local_only=0, vision_only=0, both=0, add_pts=0, over_pts=0)
    for s in sorted(set(loc) | set(k for k, (v, _) in V.items() if v)):
        base = dict(loc.get(s, {}))
        v = V.get(s, ({}, 0))[0]
        if s in loc and v:
            st["both"] += 1
        elif v:
            st["vision_only"] += 1
        else:
            st["local_only"] += 1
        for t, x in v.items():
            if t in base:
                st["over_pts"] += 1
            else:
                st["add_pts"] += 1
            base[t] = x
        js = json.dumps({str(t): base[t] for t in sorted(base)}, separators=(",", ":")).encode()
        rows.append((s, {"f_data": bytes(cramjam.snappy.compress_raw(js))}))
    pickle.dump({"funding_data": rows}, open(sys.argv[1], "wb"), protocol=4)
    st["n_records"] = len(rows)
    st["no_vision_but_local"] = sorted(s for s in loc if not V.get(s, ({}, 0))[0])[:80]
    json.dump(st, open(sys.argv[1] + ".json", "w"), indent=1)
    log.info("XONG %s", {k: v for k, v in st.items() if k != "no_vision_but_local"})


if __name__ == "__main__":
    main()
