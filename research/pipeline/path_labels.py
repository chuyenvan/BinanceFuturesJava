"""LABEL v4 tu PATH GIA (y Uni: thay 'maxFav>=6%' bang RANK / hoac dem SO NEN co max > 6%).
Nguon: CLOSES_1H.bin (close theo GIO, symId cung khong gian voi symbol_map). Tu-nhat-quan: entry = close cua GIO chua tick t;
path = 72 close gio ke tiep. KHONG doc >= 2026 (holdout).
Tinh cho moi (ts,sym) trong pool ledger v3 (da lay mau):
  maxFav_h, retEnd_h            : de doi chieu voi label pb (kiem tra nguon)
  nH_above_6 / nH_above_3       : SO GIO nam tren +6% / +3% (do BEN, y Uni — 1 nen vot roi sap != nam tren nhieu nen)
  frac_above_6                  : nH_above_6 / 72
  g1_replay                     : MO PHONG DUNG LUAT EXIT G1 tren path gio — arm khi ROI>=5%, SL = peak - min(0.5*peak, 8%),
                                  ratchet lien tuc, chua arm thi khong stop; het 72h chua thoat -> MTM close cuoi. Day la
                                  ban 'tan cung' cua label: chinh la thu sim kiem tien.
Output: /home/ubuntu/ledger/path_labels.parquet"""

# --- LUAT LOG CUA REPO: dung module `logging`, KHONG dung ham in san co.
#     Ghi ra STDOUT (khong phai stderr) de giu nguyen hanh vi cac script goi,
#     vi du: `python3 build_map.py s1a2 $P | tail -2`.
#     format="%(message)s" => output giong ban da chay sinh ra bins (xem BINS_MANIFEST.md).
import logging as _logging
import sys as _sys
_logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys.stdout)
LOG = _logging.getLogger(__name__)


def _p(*a):
    """Gop cac doi so bang dau cach roi day qua logging (thay cho ham in san co)."""
    LOG.info(" ".join(str(x) for x in a))

import numpy as np, pandas as pd, time
def log(*a): _p(time.strftime("%H:%M:%S"),*a)
H=3600000; LED="/home/ubuntu/ledger"; NH=72; ARM=0.05; GB=0.5; CAP=0.08
DT=np.dtype([("ts",">i8"),("sym",">i2"),("c",">f4")])
C=np.fromfile("/home/ubuntu/java/fsrun/CLOSES_1H.bin",dtype=DT)
ts=C["ts"].astype(np.int64); sy=C["sym"].astype(np.int32); cl=C["c"].astype(np.float32)
CUT=int(pd.Timestamp("2025-01-01").value//1e6); m=(ts<CUT)&(cl>0); ts,sy,cl=ts[m],sy[m],cl[m]
h0=ts.min()//H; hi=(ts.max()//H); NS=int(sy.max())+1; NHR=int(hi-h0)+1
log("CLOSES rows",len(ts),"hours",NHR,"syms",NS,pd.to_datetime(int(ts.min()),unit="ms"),"->",pd.to_datetime(int(ts.max()),unit="ms"))
M=np.full((NHR,NS),np.nan,dtype=np.float32); M[(ts//H-h0).astype(np.int64),sy]=cl
log("matrix",M.shape,"phu",round(float(np.isfinite(M).mean()),3))
D=pd.read_parquet(f"{LED}/cand_dev3.parquet",columns=["ts","sym","p15","g1lite","maxFav_72h","retEnd_72h"])
D=D[D.g1lite.notna()]
tk=D.groupby("ts").p15.first(); hiT=tk[tk>=0.006].index; loT=tk[tk<0.006].index
rng=np.random.default_rng(0); keep=set(hiT)|set(rng.choice(loT,size=int(0.25*len(loT)),replace=False))
D=D[D.ts.isin(keep)].reset_index(drop=True); log("pool",len(D),"ticks",D.ts.nunique())
hidx=(D.ts.values//H-h0).astype(np.int64); sidx=D.sym.values.astype(np.int64)
ok=(hidx>=0)&(hidx+NH<NHR)&(sidx<NS); log("trong pham vi",int(ok.sum()),f"({ok.mean():.3f})")
hidx,sidx=hidx[ok],sidx[ok]; Dk=D[ok].reset_index(drop=True)
entry=M[hidx,sidx]
n=len(entry); mx=np.full(n,-9.0,np.float32); last=np.full(n,np.nan,np.float32)
cnt6=np.zeros(n,np.int16); cnt3=np.zeros(n,np.int16)
peak=np.zeros(n,np.float32); armed=np.zeros(n,bool); sl=np.full(n,-9.0,np.float32); out=np.full(n,np.nan,np.float32); done=np.zeros(n,bool)
for k in range(1,NH+1):
    px=M[hidx+k,sidx]; r=px/entry-1.0
    good=np.isfinite(r)
    mx=np.where(good,np.maximum(mx,r),mx); last=np.where(good,r,last)
    cnt6+=(good&(r>=0.06)); cnt3+=(good&(r>=0.03))
    act=good&~done
    # exit G1: neu da arm va r <= sl -> thoat tai sl (xap xi fill tai muc SL)
    hit=act&armed&(r<=sl)
    out=np.where(hit,sl,out); done|=hit
    act=good&~done
    peak=np.where(act,np.maximum(peak,r),peak)
    newarm=act&~armed&(peak>=ARM); armed|=newarm
    nsl=peak-np.minimum(GB*peak,CAP)
    sl=np.where(act&armed,np.maximum(sl,nsl),sl)
out=np.where(done,out,last)   # chua thoat trong 72h -> MTM close cuoi
Dk["maxFav_h"]=np.where(mx>-9,mx,np.nan); Dk["retEnd_h"]=last; Dk["nH_above_6"]=cnt6; Dk["nH_above_3"]=cnt3
Dk["frac_above_6"]=cnt6/NH; Dk["g1_replay"]=out
v=Dk.dropna(subset=["maxFav_h","maxFav_72h"])
log("KIEM NGUON: corr(maxFav_h, maxFav_72h pb) spearman",round(v.maxFav_h.corr(v.maxFav_72h,method="spearman"),4),
    "| corr(retEnd_h, retEnd_72h)",round(v.retEnd_h.corr(v.retEnd_72h,method="spearman"),4))
_p(Dk[["maxFav_h","retEnd_h","nH_above_6","nH_above_3","g1_replay","g1lite"]].describe().round(4).to_string())
_p("\nphan bo nH_above_6 (chi lenh co maxFav_h>=6%):"); s=Dk[Dk.maxFav_h>=0.06].nH_above_6
_p(s.describe().round(2).to_dict(), "| %chi 1-2 gio:",round((s<=2).mean(),3), "| %>=12 gio:",round((s>=12).mean(),3))
_p("\ng1_replay theo nH_above_6 bucket:"); _p(Dk.assign(b=pd.cut(Dk.nH_above_6,[0,1,3,6,12,24,73],right=False)).groupby("b",observed=True).agg(n=("g1_replay","size"),g1_replay=("g1_replay","mean"),maxFav=("maxFav_h","mean"),retEnd=("retEnd_h","mean")).round(4).to_string())
Dk[["ts","sym","maxFav_h","retEnd_h","nH_above_6","nH_above_3","frac_above_6","g1_replay"]].to_parquet(f"{LED}/path_labels.parquet")
log("saved path_labels.parquet",Dk.shape)
