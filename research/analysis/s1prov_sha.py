"""Ghim sha256 input cua pipeline S1 (DEV only). Xuat JSON + digest.
Khong doc VALIDATION: chi hash label DEV (<= 20240401_to_20240701) va ghi ro."""
import hashlib, json, glob, os, logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger(__name__)
OUT = "/home/ubuntu/feataudit/s1prov_inputs_sha.json"
# OI file 4.2GB: dung lai sha da xac nhan tu G015_PROVENANCE (da doi chieu prefix e3887f63)
OI_SHA = "e3887f63097299655213f8382ca7e473e126ee4d7ddf69a39658942651b305ec"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


items = {}
single = [
    ("feat_v2.parquet", "/home/ubuntu/featv2/feat_v2.parquet"),
    ("feat_v2.meta.json", "/home/ubuntu/featv2/feat_v2.meta.json"),
    ("cand_dev.parquet", "/home/ubuntu/ledger/cand_dev.parquet"),
    ("wfo_gate_pred.csv", "/home/ubuntu/claudedata/wfo_gate_pred.csv"),
    ("symbol_map_selpred.csv", "/home/ubuntu/selector_pred_out/symbol_map.csv"),
    ("symbol_map_oi.csv", "/home/ubuntu/claudedata/oi/symbol_map.csv"),
]
for name, p in single:
    items[name] = {"path": p, "sha256": sha(p), "bytes": os.path.getsize(p)}
    LOG.info("%s %s %d", name, items[name]["sha256"][:16], items[name]["bytes"])
items["oi_percoin_full.bin"] = {"path": "/home/ubuntu/claudedata/oi/oi_percoin_full.bin",
                                "sha256": OI_SHA, "bytes": os.path.getsize("/home/ubuntu/claudedata/oi/oi_percoin_full.bin"),
                                "note": "SACH, KHONG rebuild; sha dung lai tu G015_PROVENANCE (da doi chieu prefix)"}
LOG.info("oi %s %d", OI_SHA[:16], items["oi_percoin_full.bin"]["bytes"])
# G015 source bins (build_map doc de tai phan phoi p) — 10 fold DEV
DEVF = ("20220101","20220401","20220701","20221001","20230101","20230401","20230701","20231001","20240101","20240401")
g = [x for x in sorted(glob.glob("/home/ubuntu/claudedata/predwf_G015x26/predict_wf_*.bin")) if os.path.basename(x)[11:19] in DEVF]
items["predwf_G015x26"] = {f"predict_wf_{os.path.basename(x)[11:19]}": {"sha256": sha(x), "bytes": os.path.getsize(x)} for x in g}
LOG.info("G015 source bins DEV: %d file (VAL-period KHONG hash)", len(g))
# label DEV: ledger.py doc glob 202[1-4]* nhung LOC theo T1=2024-07-01. Ghi ro file DEV thuc dung.
lab = sorted(glob.glob("/home/ubuntu/label_15m/funding_label_202[1-4]*.pb"))
lab = [x for x in lab if os.path.basename(x) <= "funding_label_20240701"]  # <= file bat dau 2024-07-01
items["label_15m_DEV"] = {os.path.basename(x): {"sha256": sha(x), "bytes": os.path.getsize(x)} for x in lab}
LOG.info("label DEV file: %d (den 20240401_to_20240701; VAL >= 20240701 KHONG hash)", len(lab))
blob = json.dumps(items, sort_keys=True, indent=1)
open(OUT, "w").write(blob)
digest = hashlib.sha256(blob.encode()).hexdigest()
LOG.info("MANIFEST_DIGEST sha256(inputs_sha.json)=%s", digest)
LOG.info("wrote %s", OUT)
