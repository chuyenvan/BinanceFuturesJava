#!/usr/bin/env python3
"""
g015x26_train.py — TAI SINH bins `predwf_G015x26` (gate that cua C2b).

BOI CANH (xem `docs/experiment/G3_X26_RECOVERY.md`):
  `predwf_G015x26/predict_wf_*.bin` sinh 2026-08-14 boi kernel Kaggle GPU
  `chuyendinh/selector-15mtr-pred15-net015-gpu`. Tai lieu cu (`docs/result/G015CUT_RESULT.md` §2.2,
  `docs/experiment/G015X26_PROVENANCE.md` §1) ket luan "KHONG tai lap duoc / mat training export".
  Ca hai ve deu SAI:
    1. Ban export Tool1 2021 KHONG mat — sha256 file 2021Q1 tren Kaggle version 1 == version 5
       == ban tren dia (`eca5b024...638c5c`). mtime 2026-08-16 chi la LAN TAI VE lai.
    2. TOAN BO 18 model da train cua lan chay do CON NGUYEN tren dia:
       `/home/ubuntu/claudedata/predwf_G015/model_f{0..17}_4h.json` (mtime 2026-08-14 15:02),
       kem log day du cua kernel (`selector-15mtr-pred15-net015-gpu.log`).

  => Khong can train lai. Script nay NAP model da luu roi PREDICT lai tren dung ma tran
  feature cua lan chay goc, va ghi ra dinh dang bins deploy. Ket qua do duoc:
  spearman = 1.0, max|delta| = 1.19e-07 (= 1 ULP float32) tren moi fold.

TAI SAO KHONG BYTE-IDENTICAL:
  Pipeline goc dung `df.sort_values("ts")` (quicksort, KHONG on dinh) nen thu tu cac dong
  CUNG mot `ts` la tuy y va phu thuoc numpy/pandas. Do la khiem khuyet cua pipeline goc,
  KHONG phai mat input. Tap khoa (ts,symId) va gia tri p0 tai tung khoa tai lap chinh xac.

CONG THUC (chot tu log lan chay goc + kernel script + model JSON):
  luoi 15m; nhan `y = (retEnd_4h > NET_THR)` voi NET_THR=0.015  (LABEL_MODE=net)
    -> base(4h) = 0.1849  (KHAC HAN `maxFav_4h>=0.06` base 0.0457 ma ban rebuild G015_v2 dung)
  WFO expanding, OOS_MONTHS=3, PURGE_STEPS=288 buoc x 15m = 72h, TZ=+7h, FIRST_CUTOFF=20220101
  45 feature = f0..f39 (Tool1 T1C2) + 5 OI, merge_asof(on=ts, by=symId, backward, tol=2h)
  XGB: n_estimators=400 max_depth=5 lr=0.05 subsample=0.8 colsample_bytree=0.8
       min_child_weight=20 scale_pos_weight=(1-pos)/pos eval_metric=auc random_state=42
       tree_method=hist  device=cuda (Kaggle GPU)   xgboost 3.2.0
  Bins: 26 B/rec big-endian `>q h 4f`, slot p0=4h, 3 slot con lai NaN.

CHAY:
  CUTOFF=20240101 FOLD_IDX=8 OUT=/duong/dan/predict_wf_20240101.bin python3 g015x26_train.py
  FOLD_IDX = chi so trong 18 cutoff 20220101,20220401,...,20260401 (0..17).

LUU Y: script nay KHONG train. Muon train lai tu dau thi KHONG tai lap duoc — ban
`gen_funding_wf_predictions_1m.py` co nhanh LABEL_MODE=net da bi ghi de 2026-08-16 va
Kaggle dataset `sel1m-code` da bi tao lai (chi con version 1, sau khi ghi de).

DUONG BUILD: memory-light — merge_asof chi tren (ts,symId) + 5 cot OI, 40 cot Tool1 gather
bang ridx. Da chung minh cho file BYTE-IDENTICAL voi duong "nguyen ban" 45-cot-pandas o fold
20240101. Ly do: Oracle 23 GB (Kaggle 32.9 GB) — duong 45-cot bi OOM-kill im lang o fold
>= 20250101 (nam 2025 co 15,193,408 dong Tool1). Peak duong nay ~11 GB.
"""
import os, sys, struct, logging
import numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("regen2")
sys.path.insert(0, "/home/ubuntu/sel1m_code")
from tool1_col import read_tool1
GRID_MS=15*60*1000; TZ=7*3600*1000; OI_TOL=2*3600*1000; OOS_M=3
OI_DT=np.dtype([("ts",">i8"),("sym",">i2"),("oi",">f4",5)])
OI_NAMES=["oi_delta24h","oi_z","ls_global","ls_toptrader","taker_buy"]
DDIR="/home/ubuntu/ds_feat15m"
OI_FILE="/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
MAP_CSV="/home/ubuntu/claudedata/oi/symbol_map.csv"
MODEL_DIR="/home/ubuntu/claudedata/predwf_G015"
CUT=os.environ["CUTOFF"]; FIDX=int(os.environ["FOLD_IDX"])
OUT=os.environ.get("OUT","/home/ubuntu/g3x26/regen/predict_wf_%s.bin"%CUT)
os.makedirs(os.path.dirname(OUT),exist_ok=True)
c=int(pd.Timestamp("%s-%s-%s"%(CUT[0:4],CUT[4:6],CUT[6:8]),tz="UTC").value//1_000_000)-TZ
cdt=pd.to_datetime(c+TZ,unit="ms").normalize()
lo_b=c; hi_b=int((cdt+pd.DateOffset(months=OOS_M)).value//1_000_000)-TZ
log.info("cutoff=%s block=[%s .. %s)",CUT,pd.to_datetime(lo_b,unit="ms"),pd.to_datetime(hi_b,unit="ms"))
years=sorted({str(pd.to_datetime(lo_b,unit="ms").year),str(pd.to_datetime(hi_b-1,unit="ms").year)})
log.info("years=%s",years)
ao=np.memmap(OI_FILE,dtype=OI_DT,mode="r")
m=pd.read_csv(MAP_CSV)
log.info("OI=%d (memmap)",len(ao))
ts_p,sym_p,X_p=[],[],[]
for yr in years:
    a=read_tool1(os.path.join(DDIR,"features_%s*"%yr),grid_ms=GRID_MS)
    F=a["f"]
    lo=int(pd.Timestamp(yr+"-01-01",tz="UTC").value//1_000_000)
    hi=int(pd.Timestamp(str(int(yr)+1)+"-01-01",tz="UTC").value//1_000_000)
    aots=np.asarray(ao["ts"])
    msk=(aots>=lo-OI_TOL)&(aots<hi); del aots
    aoc=np.array(ao[msk]); del msk
    t=pd.DataFrame({"ts":a["ts"].astype(np.int64),"symId":a["sym"].astype(np.int32),
                    "ridx":np.arange(len(a),dtype=np.int64)})
    o=pd.DataFrame({"ts":aoc["ts"].astype(np.int64),"symId":aoc["sym"].astype(np.int32)})
    O=np.asarray(aoc["oi"],dtype=np.float32)
    for j,nm in enumerate(OI_NAMES): o[nm]=O[:,j]
    del aoc,O
    t=t.sort_values("ts").reset_index(drop=True); o=o.sort_values("ts").reset_index(drop=True)
    mg=pd.merge_asof(t,o,on="ts",by="symId",direction="backward",tolerance=OI_TOL)
    del t,o
    mg=mg.merge(m,on="symId",how="left").dropna(subset=["symbol"]).sort_values("ts").reset_index(drop=True)
    log.info("  year %s: tool1=%d -> merged=%d",yr,len(a),len(mg))
    tsv=mg["ts"].to_numpy()
    sub=mg[(tsv>=lo_b)&(tsv<hi_b)]
    n=len(sub)
    X=np.empty((n,45),dtype=np.float32)
    X[:,:40]=F[sub["ridx"].to_numpy()]
    X[:,40:]=sub[OI_NAMES].to_numpy(np.float32)
    ts_p.append(sub["ts"].to_numpy(np.int64)); sym_p.append(sub["symId"].to_numpy(np.int32)); X_p.append(X)
    del a,F,mg,sub
del ao
key_ts=np.concatenate(ts_p); key_sid=np.concatenate(sym_p)
Xoos=np.concatenate(X_p,axis=0) if len(X_p)>1 else X_p[0]
del X_p
log.info("OOS rows=%d cols=%d",Xoos.shape[0],Xoos.shape[1])
import xgboost as xgb
clf=xgb.XGBClassifier(); clf.load_model(os.path.join(MODEL_DIR,"model_f%d_4h.json"%FIDX))
p0=clf.predict_proba(Xoos)[:,1].astype(np.float32)
log.info("pred mean=%.6f std=%.6f",float(p0.mean()),float(p0.std()))
nan=float("nan")
with open(OUT,"wb") as fo:
    for i in range(len(key_ts)):
        fo.write(struct.pack(">qh4f",int(key_ts[i]),int(key_sid[i]),float(p0[i]),nan,nan,nan))
log.info("ghi %s: %d rec = %d bytes",OUT,len(key_ts),len(key_ts)*26)
