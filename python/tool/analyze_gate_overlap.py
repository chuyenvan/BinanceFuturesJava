# TASK-026b DIAGNOSTIC: do edge cua gate cho DUNG voi label chong lan (overlap-correct).
# Boi canh: ban train (train_gate_production.py) bao rank-IC OOS=0.185 t=8.52 -> NHUNG t do
# PHONG DAI vi label ret_12h chong lan 48x (sampling 15m). Overlap KHONG lam lech diem uoc luong
# IC, chi lam phong dai DO TIN CAY (t). Ngoai ra cach tinh IC theo-ngay (96 bar chong lan/ngay)
# khien ban than IC kho dien giai. Script nay do lai SACH (KHONG retrain de ep pass):
#   1. IC non-overlap: lay moi 48 bar (=12h=1 mau doc lap), lap 48 offset -> IC + p doc lap.
#   2. Block-bootstrap IC (block >= horizon, giu autocorrelation) -> CI95 that.
#   3. Newey-West HAC t (lag 48) tren rank-rank.
#   4. Bang decile OOS (ret, %DOWN, %UP) -> goc dung cho SOFT size-tilt (dung dich cua gate).
# Tin hieu gate = P_up - P_down. Refit dung pipeline train (n_est=56 tu manifest) roi do OOS.
# Chay Kaggle (kernel gate-train-026, input dataset gate_dataset_v1.csv). enable_internet khong can.
import pandas as pd, numpy as np, glob
from scipy.stats import spearmanr
from xgboost import XGBClassifier
from collections import Counter

HORIZON="ret_12h"; SHIFT=48; K=0.7; WIN=2880; MINP=500; OOS_MONTHS=12; N_EST=56; H_BARS=48

_c=glob.glob("/kaggle/input/**/gate_dataset_v1.csv",recursive=True); assert _c,"khong thay v1"
df=pd.read_csv(_c[0]).sort_values("tEpochMs").reset_index(drop=True)
ts=df["tEpochMs"].values; dt=pd.to_datetime(ts,unit="ms")
drop=set(["ret_4h","ret_12h","ret_24h","n_4h","n_12h","n_24h","tEpochMs","tDate","b6_oiPriceDiverge"])
feat=[c for c in df.columns if c not in drop]; X=df[feat].astype(float).values
rr=df[HORIZON].values
sigma=pd.Series(rr).rolling(WIN,min_periods=MINP).std().shift(SHIFT).values
y=np.where(rr>=K*sigma,2,np.where(rr<=-K*sigma,0,1)).astype(float)
valid=(~np.isnan(sigma))&(~np.isnan(rr))
cutoff=dt.max()-pd.DateOffset(months=OOS_MONTHS); is_oos=np.asarray(dt>cutoff)
trm=valid&(~is_oos); oom=valid&is_oos

def sw(yy):
    c=Counter(yy); n=len(yy); k=len(c); w={cl:n/(k*v) for cl,v in c.items()}
    return np.array([w[v] for v in yy])

clf=XGBClassifier(n_estimators=N_EST,max_depth=5,learning_rate=0.05,subsample=0.8,colsample_bytree=0.8,
                  objective="multi:softprob",num_class=3,tree_method="hist",missing=np.nan,n_jobs=4,random_state=42)
clf.fit(X[trm],y[trm].astype(int),sample_weight=sw(y[trm].astype(int)))
P=clf.predict_proba(X[oom]); sig=P[:,2]-P[:,0]; ret=rr[oom].astype(float); yo=y[oom].astype(int)
N=len(sig)
print(f"OOS N={N} (label ret_12h chong lan {H_BARS}x) | cutoff={cutoff}")

# 0. pooled tho (THAM KHAO — t khong dang tin do chong lan)
ic_all=spearmanr(sig,ret).correlation
print(f"[0 tham khao] IC pooled co-chong-lan = {ic_all:.4f}")

# 1. non-overlap: moi 48 bar = 1 mau doc lap (~independent), lap 48 offset
ics=[]; ps=[]
for off in range(H_BARS):
    s=sig[off::H_BARS]; r=ret[off::H_BARS]
    if len(s)<50: continue
    rho=spearmanr(s,r); ics.append(rho.correlation); ps.append(rho.pvalue)
ics=np.array(ics); n_sub=len(sig[::H_BARS])
print(f"[1] IC NON-OVERLAP (moi {H_BARS} bar): mean={ics.mean():.4f} std={ics.std():.4f} "
      f"min={ics.min():.4f} max={ics.max():.4f} | n_mau/offset~{n_sub} | median p={np.median(ps):.3g} "
      f"| %offset p<.05={(np.array(ps)<.05).mean()*100:.0f}%")

# 2. block-bootstrap (block 192 bar ~2 ngay, giu autocorrelation) -> CI95 that
rng=np.random.default_rng(42); L=192; B=1000; idx=np.arange(N); boot=[]
for _ in range(B):
    chunks=[]; tot=0
    while tot<N:
        st=rng.integers(0,max(1,N-L)); chunks.append(idx[st:st+L]); tot+=L
    bi=np.concatenate(chunks)[:N]
    boot.append(spearmanr(sig[bi],ret[bi]).correlation)
boot=np.array(boot); lo,hi=np.percentile(boot,[2.5,97.5])
print(f"[2] block-bootstrap IC: mean={boot.mean():.4f} CI95=[{lo:.4f},{hi:.4f}] "
      f"-> {'KHAC 0 (co y nghia)' if (lo>0 or hi<0) else 'TRUM 0 (KHONG y nghia)'}")

# 3. Newey-West HAC t tren rank-rank
def rnk(a):
    o=np.argsort(np.argsort(a)); return o/len(a)
sx=rnk(sig)-0.5; sy=rnk(ret)-0.5
beta=np.sum(sx*sy)/np.sum(sx*sx); resid=sy-beta*sx
u=sx*resid; s=np.sum(u*u)
for l in range(1,H_BARS+1):
    w=1-l/(H_BARS+1); s+=2*w*np.sum(u[l:]*u[:-l])
se=np.sqrt(s)/np.sum(sx*sx); t_hac=beta/se
print(f"[3] rank-beta={beta:.4f} Newey-West t(lag{H_BARS})={t_hac:.2f} (so voi t=8.52 cua ban train)")

# 4. decile OOS (goc SOFT size-tilt — dung cach gate duoc dung)
d=pd.DataFrame({"sig":sig,"ret":ret,"y":yo})
d["dec"]=pd.qcut(d["sig"].rank(method="first"),10,labels=False)
g=d.groupby("dec").agg(ret=("ret","mean"),DOWN=("y",lambda s:(s==0).mean()),
                       UP=("y",lambda s:(s==2).mean()),n=("y","size"))
print("[4] decile OOS (sig=P_up-P_down tang dan 0..9):")
print(g.round(4).to_string())
print(f"    spread ret dec9-dec0={g.loc[9,'ret']-g.loc[0,'ret']:.4f} | "
      f"DOWN%: dec0={g.loc[0,'DOWN']:.3f} -> dec9={g.loc[9,'DOWN']:.3f} | "
      f"don dieu DOWN giam dan? {(g['DOWN'].is_monotonic_decreasing)}")
print("\n=== KET LUAN can doc: [1]/[2]/[3] co giu IC>0 voi y nghia khi BO chong lan khong? "
      "[4] DOWN% co giam don dieu theo sig khong (goc soft-tilt)? ===")
