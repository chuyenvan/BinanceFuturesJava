#!/usr/bin/env python3
"""
LEAK-FREE funding-selector predictions (walk-forward per-fold) -> predict_wf_*.bin (26B >q h 4f).

Thay vi 1 model train<=2024-12 predict ca history (in-sample, ro ri), sinh prediction WALK-FORWARD:
moi block OOS 3 thang [C, C+3m) du doan boi model chi train < C - purge. Ghep -> chuoi leak-free.
Lua chon (Uni duyet 2026-07-02): expanding train, purge=72h, ca 4 horizon, params=ban single,
cutoff theo GMT+7 (khop WFO). RUNBOOK buoc 2.
[2026-08-03 CANONICAL loi A] Fold-0 KHONG con phu vung 2021 IS: moi fold = 1 OOS block disjoint
(block_lo=cutoff, khong con ts_min). Dat CUTOFFS de OOS dau du muon (model >=2 nam train sach).
[2026-08-04 CANONICAL 1m] Uni chot: model live chay theo PHUT -> selector doi tu luoi 15p sang luoi
THAT theo SELECTOR_GRID_MIN (mac dinh giu 15 = tuong thich nguoc; canonical dat =1). PHAI khop
LABEL_STEP_MIN cua ExportFundingLabel (tu-validate qua sidecar LABEL_CSV.meta.json, throw neu lech).
H_STEPS tinh tu phut-that (bat-bien), KHONG con hardcode. CHUNK_YEARS=1 bat che do merge OI theo tung
nam (giam peak RAM: KHONG con materialize toan bo OI+Tool1 thanh DataFrame cung luc — quan trong o
luoi 1p vi Tool1 phinh ~15x va OI phai giu full-native (khong con duoc loc ve 15m nhu truoc)).

Env: TOOL1_GLOB OI_FILE LABEL_CSV MAP_CSV OUT_DIR [CUTOFFS FIRST_CUTOFF OOS_MONTHS TZ_OFFSET_MS
     PURGE_STEPS SMOKE_FOLDS NEST SEED OI_TOL_MS SELECTOR_GRID_MIN CHUNK_YEARS]
"""
import os, gzip, glob, json, logging, struct
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fwf")

PIPELINE_VERSION = "wfo-selector-v2-1m-canonical-20260804"

H_LIST = ["4h", "12h", "24h", "72h"]
# [2026-08-04] H tinh bang PHUT THAT (bat-bien) / GRID_MIN -> so buoc. Khop 1-doi-1 voi H_MINUTES trong
# ExportFundingLabel.java (Java) — 2 nguon PHAI dung cung base-minutes nay, khong tu suy doan lai.
H_BASE_MIN = {"4h": 240, "12h": 720, "24h": 1440, "72h": 4320}
WIN = 0.06
# [2-sided triple-barrier] maxFav DUONG (dinh), maxAdv AM (day=min low/close-1);
# adv_hit khi maxAdv <= -SEL_ADV_PCT. Param qua env, default giu TP=6%.
SEL_FAV_PCT = float(os.environ.get("SEL_FAV_PCT", "0.06"))  # TP
SEL_ADV_PCT = float(os.environ.get("SEL_ADV_PCT", "0.03"))  # SL placeholder
# [nonoverlap] Downsample CHI tap TRAIN ve luoi khong chong lap (giu OOS predict DAY + purge nguyen).
SEL_SAMPLE_MODE = os.environ.get("SEL_SAMPLE_MODE", "grid")   # "grid" (hien tai) | "nonoverlap"
SEL_TIMEOUT_H = int(os.environ.get("SEL_TIMEOUT_H", "4"))     # horizon(h) dat luoi nonoverlap cho TRAIN
GRID_MIN = int(os.environ.get("SELECTOR_GRID_MIN", "15"))
GRID_MS = GRID_MIN * 60 * 1000
for _h, _m in H_BASE_MIN.items():
    assert _m % GRID_MIN == 0, f"SELECTOR_GRID_MIN={GRID_MIN} khong chia het H={_h}({_m}p) -> chon uoc cua 240."
H_STEPS = {h: m // GRID_MIN for h, m in H_BASE_MIN.items()}

TOOL1_GLOB = os.environ["TOOL1_GLOB"]
OI_FILE = os.environ["OI_FILE"]
LABEL_CSV = os.environ["LABEL_CSV"]
MAP_CSV = os.environ["MAP_CSV"]
OUT_DIR = os.environ.get("OUT_DIR", ".")
os.makedirs(OUT_DIR, exist_ok=True)
OOS_MONTHS = int(os.environ.get("OOS_MONTHS", "3"))
TZ_OFFSET_MS = int(os.environ.get("TZ_OFFSET_MS", str(7 * 3600 * 1000)))
# [2026-08-04 FIX latent bug] Default purge PHAI luon = 72h WALL-CLOCK bat ke grid, khong duoc de "288"
# hardcode (dung nghia o luoi 15p thoi — o luoi 1p thi 288 buoc = 288 PHUT = 4.8h, AM THAM rut ngan purge
# tu 72h xuong 4.8h -> leak). Default nay tu tinh theo GRID_MIN; override PURGE_STEPS van la SO BUOC (grid-relative).
PURGE_MS = int(os.environ.get("PURGE_STEPS", str(H_STEPS["72h"]))) * GRID_MS
SMOKE_FOLDS = int(os.environ.get("SMOKE_FOLDS", "0"))
NEST = int(os.environ.get("NEST", "400"))
SEED = int(os.environ.get("SEED", "42"))
OI_TOL_MS = int(os.environ.get("OI_TOL_MS", str(2 * 60 * 60 * 1000)))
CHUNK_YEARS = os.environ.get("CHUNK_YEARS", "0") == "1"

log.info("PIPELINE_VERSION=%s | GRID_MIN=%d | H_STEPS=%s | PURGE_MS=%dh | CHUNK_YEARS=%s",
         PIPELINE_VERSION, GRID_MIN, H_STEPS, PURGE_MS // 3_600_000, CHUNK_YEARS)

# [2026-08-07 TASK-251] Tool1 doi sang dinh dang T1C1 (.t1c.gz, columnar+quantize int16, LITTLE-endian)
# -> KHONG con doc bang np.dtype co dinh nua. Doc qua ml/lib/tool1_col.py (read_tool1) — reader do
# doc duoc CA .t1c.gz MOI lan .bin/.bin.gz CU (tu nhan dien theo magic "T1C1"), tra ve structured
# array CUNG TEN TRUONG (ts/sym/f) nen phan code phia sau KHONG doi. TOOL1_DT chi giu lai de tham chieu.
TOOL1_DT = np.dtype([("ts", "<i8"), ("sym", "<i2"), ("f", "<f4", 40)])
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES


def read_bin(path_or_glob, dt, item, grid_filter=False):
    is_glob = any(c in path_or_glob for c in "*?[")
    files = sorted(glob.glob(path_or_glob, recursive=True)) if is_glob else [path_or_glob]
    assert files, f"khong tim thay file: {path_or_glob}"
    parts = []
    for fp in files:
        raw = open(fp, "rb").read()
        if fp.endswith(".gz"):
            raw = gzip.decompress(raw)
        assert len(raw) % item == 0, f"{fp}: {len(raw)} khong chia het {item}"
        a = np.frombuffer(raw, dtype=dt)
        if grid_filter:
            a = a[(a["ts"] % GRID_MS) == 0]
        parts.append(a)
    return np.concatenate(parts) if len(parts) > 1 else parts[0]


def _import_tool1_decoder():
    """[2026-08-07 TASK-251] Import reader Tool1 (ml/lib/tool1_col.py), chay duoc o CA 2 noi:
      - trong repo: ../lib so voi script nay (ml/training/)
      - tren Kaggle: buoc sync_kernel copy tool1_col.py vao CUNG thu muc kernel
    Bao loi RO RANG neu thieu (thay vi ImportError kho hieu tren Kaggle).
    """
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (here, os.path.join(here, "..", "lib")):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        import tool1_col as _m
        return _m
    except ImportError as e:
        raise ImportError(
            "Khong import duoc tool1_col (reader Tool1 T1C1). Da thu: %s. Tren Kaggle: buoc "
            "sync_kernel cua wfo_canonical_1m.json phai copy ml/lib/tool1_col.py vao kernel dir. "
            "Loi goc: %s" % ([here, os.path.join(here, "..", "lib")], e))


def read_tool1_any(path_or_glob, grid_filter=False):
    """Doc Tool1 o CA HAI dinh dang, tu nhan dien theo magic "T1C1" trong noi dung file:

      *.t1c.gz -> T1C1 (MOI): columnar + quantize int16 + byte-split + delta, LITTLE-endian.
                  Do that quy 2024Q2: 105.96 -> 27.97 B/record sau gzip = giam 3.79 lan quota Kaggle.
      *.bin(.gz) -> row-major float32 BIG-endian 170 B/record (CU, van doc duoc de khong phai re-export).

    Tra ve structured array CUNG TEN TRUONG ("ts","sym","f") nhu read_bin cu -> phia goi khong doi.
    """
    return _import_tool1_decoder().read_tool1(path_or_glob, grid_ms=GRID_MS if grid_filter else None)


def build_features():
    if CHUNK_YEARS:
        return build_features_chunked()
    return build_features_full()


def build_features_full():
    # [2026-08-04] grid_filter voi GRID_MS hien tai: neu GRID_MIN=1, day la NO-OP tren ca Tool1 (da 1p tai
    # nguon) va OI (5p la boi so cua 1p) -> KHONG mat du lieu OI (khac truoc: GRID_MIN=15 tung LOC OI ve
    # 15m, boi vi luc do Tool1 cung 15m nen khong mat gi; gio Tool1=1p thi PHAI giu OI full-native, va
    # co che nay tu dong lam dung dieu do — khong can sua them).
    a = read_tool1_any(TOOL1_GLOB, grid_filter=True)
    t = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    F = np.asarray(a["f"], dtype=np.float32)
    for j in range(40):
        t[f"f{j}"] = F[:, j]
    t = t.sort_values("ts").reset_index(drop=True)
    log.info("Tool1: %d rows | %d symId | ts[%s..%s]", len(t), t.symId.nunique(),
             pd.to_datetime(t.ts.min(), unit="ms"), pd.to_datetime(t.ts.max(), unit="ms"))
    ao = read_bin(OI_FILE, OI_DT, 30, grid_filter=True)
    o = pd.DataFrame({"ts": ao["ts"].astype(np.int64), "symId": ao["sym"].astype(np.int32)})
    O = np.asarray(ao["oi"], dtype=np.float32)
    for j, nm in enumerate(OI_NAMES):
        o[nm] = O[:, j]
    o = o.sort_values("ts").reset_index(drop=True)
    m = pd.read_csv(MAP_CSV)
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(m, on="symId", how="left").dropna(subset=["symbol"])
    log.info("Features: %d rows | %d symbol", len(merged), merged.symbol.nunique())
    return merged.sort_values("ts").reset_index(drop=True)


def build_features_chunked(chunk_months=12):
    """[2026-08-04] RAM-bounded cho luoi 1p: Tool1 phinh ~15x + OI phai giu full-native (khong con loc
    duoc ve grid tho nhu 15m) -> merge 1-lan-toan-bo de OOM ngay ca Kaggle 30GB. Doc raw 1 LAN (numpy gon,
    khong doi), roi CAT theo tung chunk_months truoc khi thanh pd.DataFrame + merge_asof (giam peak RAM:
    khong bao gio materialize toan bo OI/Tool1 thanh DataFrame cung luc). Ket qua nong het (concat) —
    VAN giu du lieu full tu ts_min cho train (yeu cau Uni: moi fold train tren FULL history 20210101,
    chunk chi anh huong CACH XAY feat_df, khong cat bot du lieu cuoi cung)."""
    a = read_tool1_any(TOOL1_GLOB, grid_filter=True)
    ao = read_bin(OI_FILE, OI_DT, 30, grid_filter=True)
    m = pd.read_csv(MAP_CSV)
    ts_min, ts_max = int(a["ts"].min()), int(a["ts"].max())
    log.info("CHUNK_YEARS=1: Tool1 raw=%d rec | OI raw=%d rec | chunk=%d thang | ts[%s..%s]",
             len(a), len(ao), chunk_months, pd.to_datetime(ts_min, unit="ms"), pd.to_datetime(ts_max, unit="ms"))
    chunks = []
    c0 = pd.Timestamp(pd.to_datetime(ts_min, unit="ms").strftime("%Y-%m-01"), tz="UTC")
    while int(c0.value // 1_000_000) <= ts_max:
        c1 = c0 + pd.DateOffset(months=chunk_months)
        lo, hi = int(c0.value // 1_000_000), int(c1.value // 1_000_000)
        a_chunk = a[(a["ts"] >= lo) & (a["ts"] < hi)]
        if len(a_chunk) == 0:
            c0 = c1
            continue
        # OI can bien SOM hon lo (tru OI_TOL_MS) de merge_asof backward tim dung gia tri gan-nhat<=t
        # ngay tai mep dau chunk (khong bi hut gia tri vi OI nam ngay truoc bien bi cat mat).
        ao_chunk = ao[(ao["ts"] >= lo - OI_TOL_MS) & (ao["ts"] < hi)]
        t = pd.DataFrame({"ts": a_chunk["ts"].astype(np.int64), "symId": a_chunk["sym"].astype(np.int32)})
        F = np.asarray(a_chunk["f"], dtype=np.float32)
        for j in range(40):
            t[f"f{j}"] = F[:, j]
        o = pd.DataFrame({"ts": ao_chunk["ts"].astype(np.int64), "symId": ao_chunk["sym"].astype(np.int32)})
        O = np.asarray(ao_chunk["oi"], dtype=np.float32)
        for j, nm in enumerate(OI_NAMES):
            o[nm] = O[:, j]
        t = t.sort_values("ts").reset_index(drop=True)
        o = o.sort_values("ts").reset_index(drop=True)
        merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
        merged = merged.merge(m, on="symId", how="left").dropna(subset=["symbol"])
        chunks.append(merged)
        log.info("  chunk [%s..%s): tool1=%d oi=%d -> merged=%d", c0.date(), c1.date(), len(a_chunk), len(ao_chunk), len(merged))
        del t, o, a_chunk, ao_chunk
        c0 = c1
    assert chunks, "CHUNK_YEARS=1 nhung khong chunk nao co du lieu -> kiem ts_min/ts_max/TOOL1_GLOB"
    out = pd.concat(chunks, ignore_index=True).sort_values("ts").reset_index(drop=True)
    log.info("Features (chunked, %d chunk): %d rows | %d symbol", len(chunks), len(out), out.symbol.nunique())
    return out


def _import_pb_decoder():
    """Import decoder protobuf, chay duoc o CA 2 noi:
      - trong repo: file nam o ml/lib/ (script nay o ml/training/)  -> ../lib
      - tren Kaggle: pipeline buoc sync_kernel copy funding_label_pb.py + funding_label_pb2.py
        vao CUNG thu muc voi _gen_funding_wf_predictions.py        -> chinh thu muc do
    Thu ca 2 duong dan, bao loi RO RANG neu thieu (thay vi ImportError kho hieu tren Kaggle).
    """
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (here, os.path.join(here, "..", "lib")):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        import funding_label_pb as _m
        return _m
    except ImportError as e:
        raise ImportError(
            "Khong import duoc funding_label_pb (decoder label protobuf). Da thu: %s. "
            "Tren Kaggle: buoc sync_kernel cua wfo_canonical_1m.json phai copy CA "
            "funding_label_pb.py VA funding_label_pb2.py vao kernel dir. Loi goc: %s"
            % ([here, os.path.join(here, "..", "lib")], e))


def _read_label_any(path, cols):
    """[2026-08-07 TASK-251] Doc label o CA HAI dinh dang, tu nhan dien theo duoi file:

      *.pb  -> protobuf columnar (dinh dang MOI, giam quota Kaggle 3.7x — xem
               src/main/proto/funding_label.proto). Ho tro CA glob nhieu file quy.
      *.csv -> pandas read_csv (dinh dang CU, giu de doc lai dataset cu khong phai re-gen).

    Ho tro glob giai quyet luon viec ton dong tu truoc: label duoc xuat theo TUNG QUY
    (funding_label_1m_YYYYMMDD_to_YYYYMMDD.pb) nen LABEL_CSV giờ co the la pattern
    ".../funding_label_1m_*.pb" -> tu concat het cac quy, khong phai gop tay.
    """
    is_glob = any(ch in path for ch in "*?[")
    files = sorted(glob.glob(path)) if is_glob else [path]
    if is_glob:
        # Loai file partition tam (.partN.pb / .partN.csv) — do la file job export DANG GHI DO,
        # doc vao se loi \"Wire format was corrupt\" (protobuf) hoac thieu dong (CSV).
        files = [f for f in files if ".part" not in os.path.basename(f)]
    assert files, f"khong tim thay file label hoan chinh: {path}"

    if files[0].endswith(".pb"):
        read_label = _import_pb_decoder().read_label
        parts = [read_label(fp, usecols=cols) for fp in files]
        df = pd.concat(parts, ignore_index=True) if len(parts) > 1 else parts[0]
        log.info("Label (protobuf): %d dong tu %d file", len(df), len(files))
        return df

    parts = [pd.read_csv(fp, usecols=cols, on_bad_lines="skip") for fp in files]
    df = pd.concat(parts, ignore_index=True) if len(parts) > 1 else parts[0]
    log.info("Label (CSV): %d dong tu %d file", len(df), len(files))
    return df


def load_labels():
    # [2026-08-04] Validate CHAT: Tool1 grid (GRID_MIN) PHAI khop LABEL_STEP_MIN thuc te sinh LABEL_CSV,
    # neu khong join (symbol,ts) exact se rot ~het du lieu (VD Tool1=1p, label van=15p -> chi 1/15 dong
    # Tool1 co label -> train ngo nhu binh thuong nhung THUC RA rot 14/15 du lieu, SAI IM LANG). Doc sidecar
    # .meta.json (ExportFundingLabel ghi ra) -> throw ngay neu lech, KHONG doan/bo qua.
    # [2026-08-07 TASK-251] Voi dinh dang protobuf, stepMinutes nam NGAY TRONG file (truong step_min cua
    # moi chunk) -> doc thang tu do, dang tin hon sidecar .meta.json (sidecar co the lac/thieu khi label
    # duoc chia nhieu file quy hoac copy le len Kaggle).
    _lbl_files = sorted(glob.glob(LABEL_CSV)) if any(ch in LABEL_CSV for ch in "*?[") else [LABEL_CSV]
    if _lbl_files and _lbl_files[0].endswith(".pb"):
        _m = _import_pb_decoder().meta(_lbl_files[0])
        if int(_m["step_min"]) != GRID_MIN:
            raise AssertionError(
                f"LABEL/TOOL1 GRID MISMATCH: {_lbl_files[0]} step_min={_m['step_min']} != "
                f"SELECTOR_GRID_MIN={GRID_MIN}. Join (symbol,ts) exact se rot phan lon du lieu SAI IM LANG.")
        log.info("Label meta OK (tu file .pb): step_min=%d, scale=%d, horizons=%s, %d file",
                 _m["step_min"], _m["scale"], _m["horizons"], len(_lbl_files))
        return _load_labels_from(_read_label_any(
            LABEL_CSV,
            ["tEpochMs", "symbol"] + [f"maxFav_{h}" for h in H_LIST] + [f"maxAdv_{h}" for h in H_LIST] + [f"tHitFav_{h}" for h in H_LIST] + [f"tHitAdv_{h}" for h in H_LIST] + [f"nBars_{h}" for h in H_LIST]))

    meta_path = LABEL_CSV + ".meta.json"
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as mf:
            meta = json.load(mf)
        label_step = int(meta.get("stepMinutes", -1))
        if label_step != GRID_MIN:
            raise AssertionError(
                f"LABEL/TOOL1 GRID MISMATCH: {meta_path} stepMinutes={label_step} != SELECTOR_GRID_MIN={GRID_MIN}. "
                f"Join (symbol,ts) exact se rot phan lon du lieu SAI IM LANG. Re-gen ExportFundingLabel voi "
                f"LABEL_STEP_MIN={GRID_MIN}, hoac dat SELECTOR_GRID_MIN={label_step} cho khop file label hien co.")
        log.info("Label meta OK: %s stepMinutes=%d khop SELECTOR_GRID_MIN", meta_path, label_step)
    else:
        log.warning("KHONG thay %s (label cu truoc ban co sidecar meta) -> KHONG tu-validate duoc step. "
                     "Neu day la canonical GRID_MIN=%d, PHAI tu xac nhan LABEL_CSV sinh cung step (LABEL_STEP_MIN=%d) "
                     "truoc khi tin ket qua train.", meta_path, GRID_MIN, GRID_MIN)
    cols = ["tEpochMs", "symbol"] + [f"maxFav_{h}" for h in H_LIST] + [f"maxAdv_{h}" for h in H_LIST] + [f"tHitFav_{h}" for h in H_LIST] + [f"tHitAdv_{h}" for h in H_LIST] + [f"nBars_{h}" for h in H_LIST]
    return _load_labels_from(_read_label_any(LABEL_CSV, cols))


def _load_labels_from(df):
    """[2-SIDED triple-barrier] Tach df -> y cho tung horizon (SL vs TP song song), dung chung 2 nhanh.
    fav_hit=maxFav>=SEL_FAV_PCT (TP); adv_hit=maxAdv<=-SEL_ADV_PCT (SL, maxAdv ratio AM).
    y=1: fav_hit & (not adv_hit OR tHitFav<tHitAdv). lose/timeout -> y=0. tHit* cung don vi (phut)."""
    out = {}
    for h in H_LIST:
        need = H_STEPS[h]
        d = df[["tEpochMs", "symbol", f"maxFav_{h}", f"maxAdv_{h}",
                f"tHitFav_{h}", f"tHitAdv_{h}", f"nBars_{h}"]].rename(
            columns={"tEpochMs": "ts", f"maxFav_{h}": "maxFav", f"maxAdv_{h}": "maxAdv",
                     f"tHitFav_{h}": "tHitFav", f"tHitAdv_{h}": "tHitAdv", f"nBars_{h}": "nBars"})
        d = d[(d["nBars"] >= need) & d["maxFav"].notna() & d["maxAdv"].notna()].copy()
        fav_hit = d["maxFav"] >= SEL_FAV_PCT
        adv_hit = d["maxAdv"] <= -SEL_ADV_PCT
        fav_first = d["tHitFav"] < d["tHitAdv"]
        win = fav_hit & (~adv_hit | fav_first)
        d["y"] = win.astype(np.int8)
        out[h] = d[["ts", "symbol", "y"]]
        n = len(d)
        if n:
            lose = float((adv_hit & (~fav_hit | ~fav_first)).mean())
            timeout = float(((~fav_hit) & (~adv_hit)).mean())
            log.info("Label %s [2sided fav=%.3f adv=%.3f]: %d rows | base_new=%.4f (old_1sided=%.4f) | "
                     "lose=%.4f timeout=%.4f", h, SEL_FAV_PCT, SEL_ADV_PCT, n, d["y"].mean(),
                     float(fav_hit.mean()), lose, timeout)
    return out


def gen_cutoffs(ts_min, ts_max):
    env = os.environ.get("CUTOFFS", "").strip()
    if env:
        cs = []
        for x in env.split(","):
            x = x.strip()
            dt = pd.Timestamp(f"{x[0:4]}-{x[4:6]}-{x[6:8]}", tz="UTC")
            cs.append(int(dt.value // 1_000_000) - TZ_OFFSET_MS)
        return sorted(cs)
    # [2026-08-03 CANONICAL] FIRST_CUTOFF=YYYYMMDD ep OOS block DAU (vd 20230101) -> model >=2 nam train sach
    # truoc MOI window (loi A). Neu khong set: giu cu (thang dau data + 12m). Buoc OOS_MONTHS toi ts_max.
    fc = os.environ.get("FIRST_CUTOFF", "").strip()
    if fc:
        c = pd.Timestamp(f"{fc[0:4]}-{fc[4:6]}-{fc[6:8]}", tz="UTC")
    else:
        start = pd.Timestamp(pd.to_datetime(ts_min + TZ_OFFSET_MS, unit="ms").strftime("%Y-%m-01"), tz="UTC")
        c = start + pd.DateOffset(months=12)
    cs = []
    while True:
        c_ms = int(c.value // 1_000_000) - TZ_OFFSET_MS
        oos_end = int((c + pd.DateOffset(months=OOS_MONTHS)).value // 1_000_000) - TZ_OFFSET_MS
        if oos_end > ts_max:
            break
        cs.append(c_ms)
        c = c + pd.DateOffset(months=OOS_MONTHS)
    return cs


def train_predict_fold(feat_df, labels, cutoff_ms, block_lo, block_hi, fidx):
    import xgboost as xgb
    oos = feat_df[(feat_df.ts >= block_lo) & (feat_df.ts < block_hi)]
    if len(oos) == 0:
        log.warning("fold %d: OOS block rong", fidx)
        return None
    key = oos[["ts", "symId"]].reset_index(drop=True)
    preds = {h: np.full(len(oos), np.nan, dtype=np.float32) for h in H_LIST}
    tr_cut = cutoff_ms - PURGE_MS
    tr_feat = feat_df[feat_df.ts < tr_cut]
    nonov_ms = SEL_TIMEOUT_H * 3600 * 1000   # luoi nonoverlap TRAIN (global grid: ts tuyet doi -> moi symbol cach >= SEL_TIMEOUT_H)
    for h in H_LIST:
        tr = tr_feat.merge(labels[h], on=["symbol", "ts"], how="inner")
        if SEL_SAMPLE_MODE == "nonoverlap":
            n0 = len(tr)
            base0 = float(tr.y.mean()) if n0 else float("nan")
            tr = tr[(tr.ts % nonov_ms) == 0]   # CHI train; OOS predict giu day; PURGE_MS khong doi
            base1 = float(tr.y.mean()) if len(tr) else float("nan")
            log.info("fold %d %s [nonoverlap %dh TRAIN]: rows %d -> %d | base y=1 %.4f -> %.4f",
                     fidx, h, SEL_TIMEOUT_H, n0, len(tr), base0, base1)
        if len(tr) < 5000 or tr.y.nunique() < 2:
            log.warning("fold %d %s: train it (%d) -> bo", fidx, h, len(tr))
            continue
        assert tr.ts.max() < cutoff_ms, f"LEAK fold {fidx} {h}"
        pos = tr.y.mean()
        clf = xgb.XGBClassifier(n_estimators=NEST, max_depth=5, learning_rate=0.05,
                                subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                scale_pos_weight=(1 - pos) / max(pos, 1e-6),
                                eval_metric="auc", n_jobs=-1, tree_method="hist", random_state=SEED)
        clf.fit(tr[FEAT], tr.y, verbose=False)
        preds[h] = clf.predict_proba(oos[FEAT])[:, 1].astype(np.float32)
        log.info("fold %d %s: train %d (ts_max=%s<cutoff) pos=%.4f pred %d", fidx, h, len(tr),
                 pd.to_datetime(tr.ts.max(), unit="ms"), pos, len(oos))
    return key, preds


def write_bin(path, key, preds):
    ts = key["ts"].values
    sid = key["symId"].values
    p = [preds[h] for h in H_LIST]
    with open(path, "wb") as fo:
        for i in range(len(key)):
            fo.write(struct.pack(">qh4f", int(ts[i]), int(sid[i]),
                                 float(p[0][i]), float(p[1][i]), float(p[2][i]), float(p[3][i])))
    log.info("ghi %s: %d rec = %d bytes", path, len(key), len(key) * 26)


def main():
    feat_df = build_features()
    labels = load_labels()
    ts_min, ts_max = int(feat_df.ts.min()), int(feat_df.ts.max())
    cutoffs = gen_cutoffs(ts_min, ts_max)
    log.info("CUTOFFS (%d): %s", len(cutoffs),
             [str(pd.to_datetime(c + TZ_OFFSET_MS, unit="ms").date()) for c in cutoffs])
    if SMOKE_FOLDS > 0:
        cutoffs = cutoffs[:SMOKE_FOLDS]
        log.info("SMOKE: %d fold dau", SMOKE_FOLDS)
    for i, c in enumerate(cutoffs):
        # 2026-08-03 CANONICAL leak-free (loi A): fold-0 KHONG con phu ts_min.
        # Cu: block_lo=ts_min cho fold dau -> OOS block phu ca vung IS (ts < cutoff-purge) ma model DA train
        # -> in-sample leak (MILD). Nay moi fold = dung 1 OOS block [c, c+OOS_MONTHS) DISJOINT, range roi nhau
        # -> khop leak-guard buildFundingFromWfFiles (throw on overlap). Danh doi: mat coverage window som (loi A).
        block_lo = c
        cdt = pd.to_datetime(c + TZ_OFFSET_MS, unit="ms").normalize()
        block_hi = int((cdt + pd.DateOffset(months=OOS_MONTHS)).value // 1_000_000) - TZ_OFFSET_MS
        r = train_predict_fold(feat_df, labels, c, block_lo, block_hi, i)
        if r is None:
            continue
        key, preds = r
        cdate = pd.to_datetime(c + TZ_OFFSET_MS, unit="ms").strftime("%Y%m%d")
        write_bin(os.path.join(OUT_DIR, f"predict_wf_{cdate}.bin"), key, preds)
    log.info("DONE -> %s", OUT_DIR)


if __name__ == "__main__":
    main()
