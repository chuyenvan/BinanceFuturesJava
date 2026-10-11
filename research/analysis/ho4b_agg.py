#!/usr/bin/env python3
"""HO4-P0b: gom ket qua chan doan (detcmp, detcmp_lab, t1xcmp, portcmp, tkas, q3, gitlog) vao HO4_P0b.json.
Chi doc file JSON/log nho trong thu muc lam viec; khong mo so 2026 (Q3 chi ti le khop/sha)."""
import ast
import json
import logging
import os
import re
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("ho4b_agg")


def jload(path):
    if not os.path.exists(path):
        LOG.warning("thieu %s", path)
        return None
    with open(path) as f:
        return json.load(f)


def q3_gate(path):
    out = {}
    if not os.path.exists(path):
        return out
    pat = re.compile(r"(gate s\d+|retrain s42) (\{.*\})\s*$")
    with open(path) as f:
        for line in f:
            m = pat.search(line)
            if m:
                d = ast.literal_eval(m.group(2))
                d.pop("pred_md5", None)
                out[m.group(1)] = d
    return out


def main():
    wd, dst = sys.argv[1], sys.argv[2]
    res = {
        "phase": "HO4-P0b",
        "addendum_ref": "31e3c9e7",
        "windows": {"gate": "2025-09-30..2025-10-16 +07", "tool1": "2025-10-01..2025-10-16 UTC",
                    "labels": "2025-10-01..2025-10-09 UTC"},
        "tolerance": "|d| <= 1e-6*max(1,|ref|), NaN==NaN",
        "detcmp": jload(os.path.join(wd, "detcmp.json")),
        "labels_full_lookahead": jload(os.path.join(wd, "detcmp_lab.json")),
        "t1xcmp": jload(os.path.join(wd, "t1xcmp.json")),
        "tool1_quantization_check": jload(os.path.join(wd, "t1q.json")),
        "tool1_start_by_day": jload(os.path.join(wd, "t1path.json")),
        "port_python": {"20250715": jload(os.path.join(wd, "portcmp_0715.json")),
                        "20251010": jload(os.path.join(wd, "portcmp_1010.json"))},
        "ticker_file_vs_aerospike": jload(os.path.join(wd, "tkas.json")),
        "q3": {"gate": q3_gate(os.path.join(wd, "q3_gate.log")), "net015_s1": (jload(os.path.join(wd, "q3.json")) or {}).get("net015_s1")},
    }
    with open(os.path.join(wd, "gitlog.txt")) as f:
        res["gitlog_since_20250725"] = f.read().splitlines()
    with open(dst, "w") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    LOG.info("ghi %s (%d khoa)", dst, len(res))


if __name__ == "__main__":
    main()
