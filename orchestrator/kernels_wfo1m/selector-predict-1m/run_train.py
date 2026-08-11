#!/usr/bin/env python3
"""
selector-predict-1m — Kaggle kernel wrapper cho ml/training/gen_funding_wf_predictions.py
(buoc C cua docs/WFO_DATA_PIPELINE_MASTER.md, canonical luoi 1-phut).

*** KHONG chua logic train. Chi lam 2 viec: ***
  1. Resolve duong dan Kaggle input (glob-fallback, giong short-selector kernel).
  2. Set cac env var BAT BUOC cua gen_funding_wf_predictions.py (TOOL1_GLOB, OI_FILE,
     LABEL_CSV, MAP_CSV, OUT_DIR, SELECTOR_GRID_MIN, FIRST_CUTOFF, CHUNK_YEARS, OOS_MONTHS)
     roi runpy.run_path() file THAT (_gen_funding_wf_predictions.py) nhu __main__.

*** LUU Y QUAN TRONG (dung tu suy doan lai o day) ***
  _gen_funding_wf_predictions.py trong thu muc nay la BAN SAO duoc pipeline CE
  (buoc "sync_kernel" trong orchestrator/pipelines/wfo_canonical_1m.json) tu dong
  cp tu ml/training/gen_funding_wf_predictions.py NGAY TRUOC kaggle_push — KHONG
  duoc sua tay file do o day, sua o ml/training/ roi chay lai pipeline. Neu file
  chua ton tai (chua chay qua sync_kernel/pipeline lan nao) -> FAIL ro rang o duoi,
  KHONG doan/silently skip.

  dataset_sources trong kernel-metadata.json (funding-tool1-features-1m,
  funding-label-full-1m) LA SLUG MOI CHUA TON TAI tren Kaggle luc viet file nay
  (2026-08-04) — Oracle phai export xong (label_export + tool1_export, luoi 1p)
  roi Uni/CDK tu tay `kaggle datasets create`/`version` cac slug do TRUOC khi
  kaggle_push kernel nay lan dau. Chua co CE atom cho buoc upload-dataset nay
  (xem canh bao trong ce-buttons.md / WFO_DATA_PIPELINE_MASTER.md).

Env override (khi can, vd smoke test truoc khi chay full):
  SELECTOR_GRID_MIN (default 1 — canonical, KHAC default "15" cua script goc)
  FIRST_CUTOFF      (default 20230101 — Uni chot 2026-08-03, xac nhan lai 2026-08-05)
  CHUNK_YEARS       (default 1 — RAM-bounded, BAT BUOC o luoi 1p)
  SMOKE_FOLDS       (default 0 — set vd "2" de test nhanh truoc full run)
"""
import os
import glob
import runpy
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("selector-predict-1m")


def find1(pattern):
    m = sorted(glob.glob(pattern, recursive=True))
    assert m, f"KHONG TIM THAY (kiem dataset_sources da mount dung slug chua): {pattern}"
    return m[0]


# ---- Resolve input (Kaggle-path fallback, cho phep override qua env de test cuc bo) ----
# Chi glob-tim khi env CHUA duoc set san (tranh goi find1() thua/gay loi khi da co gia tri).
# [2026-08-07 TASK-251] Tool1 doi sang dinh dang T1C1 (.t1c.gz — columnar + quantize int16 +
# byte-split + delta; do that quy 2024Q2: 105.96 -> 27.97 B/record sau gzip = giam 3.79 lan quota
# Kaggle). Uu tien glob file MOI; neu dataset mount van la ban .bin cu thi fallback -> khong vo
# pipeline (reader ml/lib/tool1_col.py doc duoc CA HAI, tu nhan dien theo magic "T1C1").
if "TOOL1_GLOB" not in os.environ:
    _t1c = sorted(glob.glob("/kaggle/input/**/ff_*.t1c.gz", recursive=True))
    if _t1c:
        os.environ["TOOL1_GLOB"] = os.path.join(os.path.dirname(_t1c[0]), "ff_*.t1c.gz")
        log.info("Tool1: tim thay %d file .t1c.gz (T1C1) -> dung pattern %s",
                 len(_t1c), os.environ["TOOL1_GLOB"])
    else:
        os.environ["TOOL1_GLOB"] = "/kaggle/input/**/ff_*.bin"
        log.warning("KHONG thay file .t1c.gz nao -> fallback ve dinh dang cu: %s",
                    os.environ["TOOL1_GLOB"])
if "OI_FILE" not in os.environ:
    os.environ["OI_FILE"] = find1("/kaggle/input/**/oi_percoin_full.bin")
if "LABEL_CSV" not in os.environ:
    # [2026-08-07 TASK-251] Label doi tu CSV sang PROTOBUF columnar (giam quota Kaggle 3.7x) va duoc
    # chia theo TUNG QUY -> khong con 1 file "funding_label.csv" duy nhat. Truyen thang PATTERN glob
    # cho gen_funding_wf_predictions.py (ham _read_label_any() cua no tu glob + concat cac quy, va tu
    # nhan dien .pb vs .csv theo duoi file). Van giu TEN env LABEL_CSV de khong phai doi 2 dau.
    # Uu tien .pb (dinh dang moi); neu dataset mount van la ban CSV cu thi fallback -> khong vo pipeline.
    _pb = sorted(glob.glob("/kaggle/input/**/funding_label_1m_*.pb", recursive=True))
    if _pb:
        os.environ["LABEL_CSV"] = os.path.join(os.path.dirname(_pb[0]), "funding_label_1m_*.pb")
        log.info("Label: tim thay %d file .pb (protobuf) -> dung pattern %s",
                 len(_pb), os.environ["LABEL_CSV"])
    else:
        os.environ["LABEL_CSV"] = find1("/kaggle/input/**/funding_label*.csv")
        log.warning("KHONG thay file .pb nao -> fallback ve CSV cu: %s", os.environ["LABEL_CSV"])
if "MAP_CSV" not in os.environ:
    os.environ["MAP_CSV"] = find1("/kaggle/input/**/symbol_map.csv")
os.environ.setdefault("OUT_DIR", "/kaggle/working")

# ---- Canonical 1-phut (Uni chot 2026-08-04) — KHAC default cua script goc (15) ----
os.environ.setdefault("SELECTOR_GRID_MIN", "1")
# [2026-08-05] Uni xac nhan lai: FIRST_CUTOFF=20230101 (loi A) la DUNG, giu nguyen. Y "gen tu
# 20210101" la pham vi EXPORT label/feature/ticker (de fold dau - cutoff 20230101 - co du train
# tu 20210101 toi 20230101-72h purge), KHONG phai doi diem cutoff cua fold dau. Sua nham
# 2026-08-05 sang 20210101 roi REVERT lai ngay trong phien nay - xem TASK-251.
os.environ.setdefault("FIRST_CUTOFF", "20230101")
os.environ.setdefault("CHUNK_YEARS", "1")
os.environ.setdefault("OOS_MONTHS", "3")

GEN_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "_gen_funding_wf_predictions.py")
if not os.path.exists(GEN_SCRIPT):
    raise SystemExit(
        f"KHONG THAY {GEN_SCRIPT}. File nay phai duoc pipeline CE (buoc sync_kernel trong "
        f"wfo_canonical_1m.json) copy tu ml/training/gen_funding_wf_predictions.py TRUOC "
        f"khi kaggle_push. Chay lai pipeline tu buoc sync_kernel, KHONG tao file nay bang tay.")

log.info("selector-predict-1m: TOOL1_GLOB=%s OI_FILE=%s LABEL_CSV=%s MAP_CSV=%s "
        "SELECTOR_GRID_MIN=%s FIRST_CUTOFF=%s CHUNK_YEARS=%s",
        os.environ["TOOL1_GLOB"], os.environ["OI_FILE"], os.environ["LABEL_CSV"],
        os.environ["MAP_CSV"], os.environ["SELECTOR_GRID_MIN"], os.environ["FIRST_CUTOFF"],
        os.environ["CHUNK_YEARS"])

runpy.run_path(GEN_SCRIPT, run_name="__main__")
