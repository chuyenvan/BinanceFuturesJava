"""Sinh ofi_train_eval_v3.py tu ofi_train_eval_v2.py bang cac thay the CO HOC (in diff so dong)."""
import logging
import re

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("gen")
SRC = r"E:\educa\source\github\20260415\BinanceFuturesJava\research\pipeline\x1\kaggle_ofi\ofi_train_eval_v2.py"
DST = r"D:\claudedata\ofi_v3\stage\research\pipeline\x1\kaggle_ofi_v3\ofi_train_eval_v3.py"
s = open(SRC, encoding="utf-8").read()
n0 = s.count("\n")

HEADER_OLD = s[:s.index("import glob")]
HEADER_NEW = (
    "# OFI V3 UNIVERSE -- train/eval CONFIRM cho OFI build tren TOAN BO universe (docs/prereg/PREREG_S1_FREE_OFI_V3_UNIVERSE.md).\n"
    "# Sinh CO HOC tu ofi_train_eval_v2.py (gen_train_v3.py): harness/model/CI/noise-mask Y HET v2. Khac biet DUY NHAT:\n"
    "# (1) doc + ghep TAT CA ofi_feat_x1.parquet cua cac kernel shard (bo symbol chua hoan tat cua shard bi cat, dedupe dong trung y het, assert khong xung dot),\n"
    "# (2) log mo ta coverage theo nam (KHONG tinh edge5 them), (3) logging thay print, (4) output ofi_result_v3.json.\n"
)
s = s.replace(HEADER_OLD, HEADER_NEW, 1)

OLD_OFI_PATH = 'OFI_PATH = find1("/kaggle/input/**/ofi_feat_x1.parquet")\n'
assert OLD_OFI_PATH in s
s = s.replace(OLD_OFI_PATH,
              'OFI_PATHS = sorted(glob.glob("/kaggle/input/**/ofi_feat_x1.parquet", recursive=True))\n'
              'assert OFI_PATHS, "not found: ofi_feat_x1.parquet"\n'
              'OFI_PATH = ";".join(OFI_PATHS)\n', 1)

OLD_OFI_READ = 'OFI = pd.read_parquet(OFI_PATH, columns=["ts", "sym", "ofi_1h", "aggr_buy_ratio_1h"])\n'
assert OLD_OFI_READ in s
s = s.replace(OLD_OFI_READ,
              'def _read_shard(p):\n'
              '    x = pd.read_parquet(p, columns=["ts", "sym", "ofi_1h", "aggr_buy_ratio_1h"])\n'
              '    sp = os.path.join(os.path.dirname(p), "ofi_build_summary.json")\n'
              '    if os.path.exists(sp):\n'
              '        sm = json.load(open(sp))\n'
              '        bad = set(sm.get("symids_not_completed", []))\n'
              '        if bad:\n'
              '            print("shard", sm.get("shard"), "bo symbol chua hoan tat:", sorted(bad), flush=True)\n'
              '            x = x[~x.sym.isin(bad)]\n'
              '    return x\n\n\n'
              'OFI = pd.concat([_read_shard(p) for p in OFI_PATHS], ignore_index=True)\n'
              'n_ofi_raw = len(OFI)\n'
              'OFI = OFI.drop_duplicates()\n'
              'assert not OFI.duplicated(["ts", "sym"]).any(), "OFI: (ts,sym) trung voi gia tri KHAC nhau"\n'
              'print("OFI files", len(OFI_PATHS), "rows raw", n_ofi_raw, "after exact-dedupe", len(OFI),\n'
              '      "n_sym", OFI.sym.nunique(), flush=True)\n', 1)

OLD_COV = 'D["yr"] = pd.to_datetime(D.ts, unit="ms").dt.year\n'
assert OLD_COV in s
s = s.replace(OLD_COV, OLD_COV +
              'cov_by_year = D.groupby("yr").ofi_1h.apply(lambda x: float(x.notna().mean())).to_dict()\n'
              'sym_any_ofi = D.groupby("sym").ofi_1h.apply(lambda x: bool(x.notna().any()))\n'
              'print("coverage ofi_1h theo nam:", cov_by_year, flush=True)\n'
              'print("pool n_sym", int(sym_any_ofi.size), "n_sym co >=1 dong OFI", int(sym_any_ofi.sum()), flush=True)\n', 1)

OLD_RES = '    ofi_coverage_frac=float(ofi_cov),\n'
assert OLD_RES in s
s = s.replace(OLD_RES, OLD_RES +
              '    ofi_n_files=len(OFI_PATHS), ofi_n_rows=int(len(OFI)), ofi_n_sym=int(OFI.sym.nunique()),\n'
              '    ofi_coverage_by_year={str(k): v for k, v in cov_by_year.items()},\n'
              '    pool_n_sym=int(sym_any_ofi.size), pool_n_sym_with_ofi=int(sym_any_ofi.sum()),\n', 1)
assert s.count("ofi_result_v2.json") == 1
s = s.replace("ofi_result_v2.json", "ofi_result_v3.json")
s = s.replace("=== FINAL v2 ===", "=== FINAL v3 ===")

# print -> logging (co hoc)
imp = "import time\n"
assert imp in s
s = s.replace(imp, imp + "import logging\n", 1)
anchor = 'WORK = "/kaggle/working"\n'
s = s.replace(anchor,
              'logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)\n'
              '_log = logging.getLogger("ofi_v3_eval")\n\n\n'
              'def _p(*a, flush=True):\n'
              '    _log.info(" ".join(str(x) for x in a))\n\n\n' + anchor, 1)
s = re.sub(r"\bprint\(", "_p(", s)
open(DST, "w", encoding="utf-8", newline="\n").write(s)
log.info("v2 lines=%d -> v3 lines=%d", n0, s.count("\n"))
