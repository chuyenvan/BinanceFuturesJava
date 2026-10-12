#!/usr/bin/env python3
"""BCAST: gom ket qua dung kho -> docs/result/bcast/BCAST_BUILD.json (chi md5/dem/NaN/khoang ts/khoa ky thuat; khong PnL).
Usage: bcast_build_json.py <out.json>"""
import json, logging, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("bcast_bj")
W = "/home/ubuntu/claude_master/1012/bcast"
J = lambda p: json.load(open(W + "/" + p))  # noqa: E731
ch = J("kaggle/out/bcast-ch20-a/result.json")
xa = J("x_bcast-x20-a.json")
xr = J("kaggle/out/bcast-x20-a/result.json")
out = dict(prereg="596c1ef8", exporter=dict(xa, outputs=None, jar_sha256=xr.get("jar_sha256"), funding_F_dev_pts=xr["steps"]["funding_F"]["dev_pts"],
                                             task_secs={t["name"]: t["secs"] for t in xr["tasks"]}),
           chain=dict(ok=ch.get("ok"), secs=ch.get("secs"), steps=ch["steps"], dup_ids=ch.get("dup_ids"), manifest=ch["manifest"]),
           p3det_exporter=J("det_bcast-x20-a_bcast-x20-b.json"), p3det_chain=J("det_bcast-ch20-a_bcast-ch20-b.json"),
           arts=dict(J("arts.json"), tk_md5="(369 entries, xem dataset ticker_raw_md5.json)"),
           tech=J("bcast_tech_check.json"), dataset=dict(id="chuyendinh/bcast-2020-2021h1-p1", private=True,
                                                          manifest=J("MANIFEST_bcast.json"), raw_md5_nonticker=J("raw_md5_nonticker.json"),
                                                          note="Kaggle tu giai nen .gz: ticker kiem bang ticker_raw_md5.json, gate/t1 bang raw_md5_nonticker"),
           excluded=dict(not_in_mapper=["LENDUSDT", "BTCSTUSDT"], no_funding_vision=ch["steps"]["excl_no_funding"]["symbols"],
                         settle_tail=ch["steps"]["excl_no_funding"]["settle_tail"], dup_id_843_850="khong co symbol 2020"))
json.dump(out, open(sys.argv[1], "w"), indent=1, sort_keys=True, default=str)
log.info("ghi %s", sys.argv[1])
