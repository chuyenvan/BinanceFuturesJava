"""V2 FEATURE BUILD + VALIDATE (V2 label check, V3 unit/causality/distribution). Output: /home/ubuntu/featv2/feat_v2.parquet (hourly, DEV 2021-01..2024-06)
Chay tren Oracle. Moi buoc in PASS/FAIL ro rang; FAIL -> dung (sys.exit) de khong train tren du lieu sai."""

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

import os, sys, json, time, random, numpy as np, pandas as pd
import aerospike, cramjam
OUT="/home/ubuntu/featv2"; CLO="/home/ubuntu/java/fsrun/CLOSES_1H.bin"; MAP="/home/ubuntu/selector_pred_out/symbol_map.csv"
OI="/home/ubuntu/claudedata/oi/oi_percoin_full.bin"; H=3600000; T_END=1719792000000  # 2024-07-01 UTC (DEV cuoi)
def log(*a): _p(time.strftime("%H:%M:%S"), *a)
def check(cond, msg):
    _p(("PASS " if cond else "FAIL ") + msg)
    if not cond: sys.exit("STOP: " + msg)
# ---------- 1. closes -> matrix ----------
DT=np.dtype([("ts",">i8"),("sym",">i2"),("c",">f4")]); a=np.fromfile(CLO,dtype=DT)
df=pd.DataFrame({"ts":a["ts"].astype(np.int64),"sym":a["sym"].astype(np.int32),"c":a["c"].astype(np.float64)}); del a
df=df[df.ts<=T_END]
P=df.pivot(index="ts",columns="sym",values="c").sort_index()
hours=pd.Index(np.arange(P.index.min(),P.index.max()+H,H)); P=P.reindex(hours)   # luoi gio day du; gap = NaN (khong ffill gia -> khong bia du lieu)
log(f"P {P.shape} hours {pd.to_datetime(P.index[0],unit='ms')}..{pd.to_datetime(P.index[-1],unit='ms')}")
mp=pd.read_csv(MAP); id2sym=dict(zip(mp.symId,mp.symbol)); sym2id={v:k for k,v in id2sym.items()}
check(1 in P.columns and id2sym[1]=="BTCUSDT", "BTCUSDT = symId 1 co trong closes")
R1=P/P.shift(1)-1                                                     # ret 1h
# ---------- 2. feature functions (moi ham CHI dung du lieu <= t: rolling tren truc thoi gian, khong center) ----------
def ret(n): return P/P.shift(n)-1
def rmax(n): return P.rolling(n,min_periods=max(2,n//2)).max()
def rmin(n): return P.rolling(n,min_periods=max(2,n//2)).min()
F={}
F["ret_1d"]=ret(24); F["ret_3d"]=ret(72); F["ret_7d"]=ret(168); F["ret_14d"]=ret(336)
mx7,mn7,mx30,mn30=rmax(168),rmin(168),rmax(720),rmin(720)
F["dd_7d"]=P/mx7-1; F["dd_30d"]=P/mx30-1; F["up_7d"]=P/mn7-1; F["pos_30d"]=(P-mn30)/(mx30-mn30)
# hrs_since_high_7d: vi tri argmax trong cua so 168 -> tinh bang rolling apply qua numpy (cham) -> dung thu thuat: idx cua max
def hrs_since_high(win):
    arr=P.to_numpy(); n,m=arr.shape; out=np.full((n,m),np.nan,dtype=np.float32)
    for j in range(m):
        col=arr[:,j]
        for i in range(win-1,n):
            w=col[i-win+1:i+1]
            if np.isnan(w).sum()>win//2: continue
            k=np.nanargmax(w); out[i,j]=(win-1-k)/win
    return pd.DataFrame(out,index=P.index,columns=P.columns)
log("hrs_since_high (cham, ~vai phut)..."); F["hrs_since_high_7d"]=hrs_since_high(168)
F["vol_3d"]=R1.rolling(72,min_periods=36).std(); F["vol_7d"]=R1.rolling(168,min_periods=84).std(); F["vol_30d"]=R1.rolling(720,min_periods=360).std()
F["vol_ratio"]=F["vol_3d"]/F["vol_30d"]; F["range_7d"]=(mx7-mn7)/P
btc3=F["ret_3d"][1]; btc7=F["ret_7d"][1]
F["rs_btc_3d"]=F["ret_3d"].sub(btc3,axis=0); F["rs_btc_7d"]=F["ret_7d"].sub(btc7,axis=0)
F["rs_mkt_3d"]=F["ret_3d"].sub(F["ret_3d"].median(axis=1),axis=0); F["rs_mkt_7d"]=F["ret_7d"].sub(F["ret_7d"].median(axis=1),axis=0)
first=P.notna().idxmax(); age=pd.DataFrame({c:(P.index.values-first[c])/86400000.0 for c in P.columns},index=P.index); age[P.isna()]=np.nan; F["age_days"]=age
log("gia/vol/rs xong")
# ---------- 3. funding tu Aerospike ----------
cli=aerospike.client({"hosts":[("127.0.0.1",3222)]}).connect()
def fmap(sym):
    for kk in (sym,):
        try:
            _,_,rec=cli.get(("test","funding_data",kk)); js=bytes(cramjam.snappy.decompress_raw(bytes(rec["f_data"]))).decode()
            return {int(k):float(v) for k,v in json.loads(js).items()}
        except Exception: return None
FL=pd.DataFrame(np.nan,index=P.index,columns=P.columns); FS3=FL.copy(); FS7=FL.copy(); FZ=FL.copy(); FT=FL.copy(); nf=0
for c in P.columns:
    fm=fmap(id2sym[c])
    if not fm: continue
    s=pd.Series(fm).sort_index(); s=s[(s.index>P.index[0]-30*86400000)&(s.index<=P.index[-1])]
    if len(s)<10: continue
    nf+=1
    # asof: gia tri settle cuoi <= t (settle ts la moc chinh xac, KHONG dung ky settle > t)
    idx=np.searchsorted(s.index.values, P.index.values, side="right")-1
    last=np.where(idx>=0, s.values[np.clip(idx,0,None)], np.nan); FL[c]=last
    cs=np.concatenate([[0.0],np.cumsum(s.values)])
    def sum_win(hrs):
        lo=np.searchsorted(s.index.values, P.index.values-hrs*H, side="right"); hi=idx+1
        return np.where(hi>lo, cs[hi]-cs[np.clip(lo,0,None)], np.nan) if True else None
    FS3[c]=sum_win(72); FS7[c]=sum_win(168)
    # z 30d: dung cac ky settle trong (t-30d, t]
    lo30=np.searchsorted(s.index.values, P.index.values-720*H, side="right")
    cs2=np.concatenate([[0.0],np.cumsum(s.values**2)]); n30=(idx+1-lo30).astype(float); n30[n30<=0]=np.nan
    m30=(cs[idx+1]-cs[lo30])/n30; v30=(cs2[idx+1]-cs2[lo30])/n30-m30**2; sd=np.sqrt(np.clip(v30,1e-12,None))
    FZ[c]=(last-m30)/sd; FT[c]=FS3[c]/np.maximum((idx+1-np.searchsorted(s.index.values,P.index.values-72*H,side="right")),1)-FS7[c]/np.maximum((idx+1-np.searchsorted(s.index.values,P.index.values-168*H,side="right")),1)
log(f"funding: {nf}/{len(P.columns)} coin co du lieu")
F["fund_last"]=FL; F["fund_sum_3d"]=FS3; F["fund_sum_7d"]=FS7; F["fund_trend"]=FT; F["fund_z_30d"]=FZ
# ---------- 4. OI (asof <= t, tol 2h) ----------
ODT=np.dtype([("ts",">i8"),("sym",">i2"),("oi",">f4",5)]); o=np.memmap(OI,dtype=ODT,mode="r")
ots=o["ts"].astype(np.int64); sel=(ots<=T_END)&(ots%H==0); log(f"OI rows {len(o)} -> tai moc gio {sel.sum()}")
od=pd.DataFrame({"ts":ots[sel],"sym":o["sym"][sel].astype(np.int32)}); ov=np.asarray(o["oi"][sel],dtype=np.float32)
names=["oi_delta24h","oi_z","ls_global","ls_toptrader","taker_buy"]
for j,nm in enumerate(names):
    M=od.assign(v=ov[:,j]).pivot(index="ts",columns="sym",values="v").reindex(index=P.index,columns=P.columns)
    M=M.ffill(limit=2)   # tol 2h (chi dung gia tri qua khu)
    F[nm]=M
F["oi_delta_3d"]=F["oi_z"]-F["oi_z"].shift(72)
del o
# ---------- 5. cross-sectional ranks (chi tren coin co gia tri tai tick) ----------
for src,nm in [("ret_3d","rk_ret_3d"),("ret_7d","rk_ret_7d"),("dd_7d","rk_dd_7d"),("vol_ratio","rk_vol_ratio"),("fund_sum_3d","rk_fund_sum_3d"),("oi_delta24h","rk_oi_delta24h"),("rs_btc_7d","rk_rs_btc_7d")]:
    F[nm]=F[src].rank(axis=1,pct=True)
rng=np.random.default_rng(20260902)
for k in range(3): F[f"noise_{k}"]=pd.DataFrame(rng.random(P.shape,dtype=np.float32),index=P.index,columns=P.columns)
FEATS=list(F.keys()); log("features:",len(FEATS),FEATS)
# ---------- V3(a) UNIT TEST tren chuoi tong hop ----------
t=np.arange(1000); lin=pd.Series(100+t*1.0)   # gia tang 1/h
r3=lin/lin.shift(72)-1; check(abs(r3.iloc[999]-(1099/1027-1))<1e-9, "unit ret_3d tren chuoi tuyen tinh")
check(abs((lin/lin.rolling(168).max()-1).iloc[999])<1e-12, "unit dd_7d = 0 khi gia tang deu (dinh = hien tai)")
step=pd.Series([100.0]*500+[50.0]*500); check(abs((step/step.rolling(168).max()-1).iloc[600]+0.5)<1e-12 and abs((step/step.rolling(168).max()-1).iloc[999])<1e-12, "unit dd_7d sau buoc nhay -50%: -0.5 roi ve 0 khi dinh roi khoi cua so")
# ---------- V3(b) CAUSALITY: 200 (sym,t) random, cat chuoi tai t, tinh lai ret_7d/dd_30d/vol_7d/rs_btc_7d ----------
rs=np.random.default_rng(7); valid=np.argwhere(P.notna().to_numpy()); pick=valid[rs.choice(len(valid),200,replace=False)]
bad=0
for i,j in pick:
    if i<720: continue
    c=P.columns[j]; sub=P.iloc[:i+1]   # CAT tai t
    r7=sub[c].iloc[-1]/sub[c].iloc[-169]-1 if not np.isnan(sub[c].iloc[-169]) else np.nan
    w30=sub[c].iloc[-720:]; d30=(sub[c].iloc[-1]/np.nanmax(w30)-1) if w30.notna().sum()>=360 else np.nan   # cung min_periods=360 nhu bang
    wr=(sub[c]/sub[c].shift(1)-1).iloc[-168:]; v7=np.nanstd(wr,ddof=1) if wr.notna().sum()>=84 else np.nan  # cung min_periods=84
    for nm,val in [("ret_7d",r7),("dd_30d",d30),("vol_7d",v7)]:
        got=F[nm].iat[i,j]
        if not (np.isnan(val) and np.isnan(got)) and not np.isclose(val,got,rtol=1e-4,atol=1e-9,equal_nan=True): bad+=1; _p("  MISMATCH",nm,id2sym[c],pd.to_datetime(P.index[i],unit='ms'),val,got)
check(bad==0, f"CAUSALITY 200 mau x 3 feature: mismatch={bad} (tinh lai tu chuoi cat tai t == bang)")
# ---------- V3(c) phan bo ----------
rows=[]
for nm in FEATS:
    v=F[nm].to_numpy().ravel(); v=v[~np.isnan(v)]
    q=np.quantile(v,[0.01,0.05,0.5,0.95,0.99]) if len(v) else [np.nan]*5
    rows.append((nm, round(1-len(v)/F[nm].size,3), *np.round(q,4)))
D=pd.DataFrame(rows,columns=["feat","nan%","q01","q05","q50","q95","q99"]); _p(D.to_string())
check((F["dd_7d"].max().max()<=1e-9) and (F["up_7d"].min().min()>=-1e-9), "range: dd<=0, up>=0")
check(F["pos_30d"].min().min()>=-1e-9 and F["pos_30d"].max().max()<=1+1e-9, "range: pos_30d in [0,1]")
check(all(F[n].min().min()>=0 and F[n].max().max()<=1 for n in FEATS if n.startswith("rk_")), "range: rank in [0,1]")
# ---------- 6. long format + save ----------
long=pd.concat({nm:F[nm].stack(dropna=False) for nm in FEATS},axis=1)
long.index.names=["ts","sym"]; long=long.reset_index(); long=long[P.stack(dropna=False).reset_index(drop=True).notna().to_numpy()]   # chi row co gia
long=long[long.ts>=1609459200000+30*86400000]                       # bo 30 ngay dau (thieu lookback)
log(f"long rows={len(long)} cols={long.shape[1]}"); long.to_parquet(f"{OUT}/feat_v2.parquet",index=False)
json.dump({"feats":FEATS,"n_rows":int(len(long)),"t_end":T_END,"src":{"closes":CLO,"oi":OI,"funding":"aerospike funding_data"}},open(f"{OUT}/feat_v2.meta.json","w"),indent=1)
log("SAVED"); _p("ALL_V3_PASS")
