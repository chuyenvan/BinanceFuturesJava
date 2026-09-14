#!/usr/bin/env python3
"""
PROBE: feasibility + edge of a SHORT strategy (mirror of top-8 BUY).
OFFLINE ONLY. Reads existing parquet; does NOT touch sim / live / port 242.
Forward returns from featv2 trailing returns by ts-shift:
  fwd_Xh(t)=trailing_ret(t+Xh)  [validated corr 0.991 vs cand_dev.retEnd_72h].
Pred cadence is 15-min; snapped to hour for the 72h/24h/168h fwd join
(snap error << horizon). S1 score: HIGH score = dump candidate (short zone).
SHORT PnL = -(forward price return).  1x leverage (Configs.LEVERAGE_ORDER=1).
"""
import pandas as pd, numpy as np
from sklearn.metrics import roc_auc_score
H=3600000
FEAT="/home/ubuntu/featv2/feat_v2.parquet"
PRED="/home/ubuntu/ledger/pred_s1a2x1.parquet"
PATHL="/home/ubuntu/ledger/path_labels.parquet"
RATE_FEE=0.002; SLIP=0.003; COST=RATE_FEE+2*SLIP   # 0.8% round-trip (Configs)
K=8
print("=== LOAD ===")
f=pd.read_parquet(FEAT, columns=['ts','sym','ret_1d','ret_3d','ret_7d',
    'fund_last','fund_sum_3d','fund_sum_7d','fund_z_30d'])
def fwd(col,h):
    s=f[['ts','sym',col]].copy(); s['ts']=s['ts']-h*H
    return s.rename(columns={col:'f_%d'%h})
fw=f[['ts','sym','fund_last','fund_sum_3d','fund_sum_7d','fund_z_30d']].copy()
fw=fw.merge(fwd('ret_1d',24),on=['ts','sym'],how='left')
fw=fw.merge(fwd('ret_3d',72),on=['ts','sym'],how='left')
fw=fw.merge(fwd('ret_7d',168),on=['ts','sym'],how='left')
p=pd.read_parquet(PRED, columns=['ts','sym','score'])
p['tsh']=(p.ts//H)*H                       # snap decision ts to hour for fwd join
fwh=fw.rename(columns={'ts':'tsh'})
m=p.merge(fwh,on=['tsh','sym'],how='inner').dropna(subset=['score'])
print("merged rows",len(m),"n_ts(15m)",m.ts.nunique(),"n_sym",m.sym.nunique(),
      "ts",m.ts.min(),"->",m.ts.max())
# per-DECISION-ts rank (1=lowest score)
g=m.groupby('ts')['score']
m['rk']=g.rank(method='first'); m['cnt']=g.transform('size')
m['qd']=m.groupby('ts')['score'].transform(
    lambda s: pd.qcut(s.rank(method='first'),10,labels=False,duplicates='drop'))
long8 =m[m.rk<=K]; short8=m[m.rk>m.cnt-K]; mid=m[(m.rk>K)&(m.rk<=m.cnt-K)]
print("\n=== A. PER-TS BUCKET FWD RET (price ret; SHORT pnl=-f). pooled + portfolio ===")
for name,d in [('LONG_top8(low sc)',long8),('MID',mid),
               ('SHORT_bot8(high sc)',short8),('ALL',m)]:
    pf72=d.groupby('ts').f_72.mean().mean()   # equal-weight-per-ts portfolio, 72h
    print("%-20s n=%8d f24=%+.4f f72=%+.4f f168=%+.4f med72=%+.4f | portf72=%+.4f"%(
        name,len(d),d.f_24.mean(),d.f_72.mean(),d.f_168.mean(),d.f_72.median(),pf72))
print("\n=== B. PER-TS DECILE (0=low..9=high score) fwd ret ===")
print(m.groupby('qd')[['f_24','f_72','f_168']].mean().round(4).to_string())
print("\n=== C. RANK IC (per-ts spearman score vs fwd; neg=>high score->down) ===")
for c in ['f_24','f_72','f_168']:
    gg=m.dropna(subset=[c]).groupby('ts').apply(
        lambda x: x['score'].corr(x[c],method='spearman'),include_groups=False)
    print("  rankIC score vs %-6s = %+.4f (n_ts=%d)"%(c,gg.mean(),gg.notna().sum()))
print("\n=== D. AUC (predictor=score) ===")
d=m.dropna(subset=['f_72'])
print("  AUC score->P(f72<0) short=%.4f | P(f72>0) long=%.4f"%(
    roc_auc_score((d.f_72<0).astype(int),d.score),
    roc_auc_score((d.f_72>0).astype(int),d.score)))
for thr in [-0.05,-0.10,-0.20]:
    print("  AUC score->P(f72<%.2f)=%.4f"%(thr,roc_auc_score((d.f_72<thr).astype(int),d.score)))
print("\n=== E. SHORT NET EDGE (bot8, gross=-f) ===")
for h,col in [(24,'f_24'),(72,'f_72'),(168,'f_168')]:
    g=-short8[col].mean(); print("  h%d gross=%+.4f net(-%.3f)=%+.4f"%(h,g,COST,g-COST))
print("\n=== F. FUNDING TAILWIND SHORT (receives when funding>0) ===")
print("  bot8 fund_sum_3d mean=%+.5f (=%.2f bps/day) | fund_last>0=%.3f sum3d>0=%.3f"%(
    short8.fund_sum_3d.mean(),short8.fund_sum_3d.mean()/3*1e4,
    (short8.fund_last>0).mean(),(short8.fund_sum_3d>0).mean()))
print("  ALL fund_sum_3d mean=%+.5f"%m.fund_sum_3d.mean())
print("\n=== G. TAIL RISK SHORT (pump against) ===")
for thr in [0.20,0.50,1.00]:
    print("  %% f72>+%.0f%%=%.3f%%"%(thr*100,(short8.f_72>thr).mean()*100))
pl=pd.read_parquet(PATHL,columns=['ts','sym','maxFav_h'])
pl['tsh']=(pl.ts//H)*H
sj=short8[['tsh','sym']].drop_duplicates().merge(
    pl.rename(columns={'ts':'plt'}),on=['tsh','sym'],how='inner')
print("  intra-path maxFav_h(72h) n=%d mean=%+.4f p95=%+.4f p99=%+.4f max=%+.4f"%(
    len(sj),sj.maxFav_h.mean(),sj.maxFav_h.quantile(.95),sj.maxFav_h.quantile(.99),sj.maxFav_h.max()))
for thr in [0.20,0.50,1.00]:
    print("  %% maxFav_h>+%.0f%%=%.3f%%"%(thr*100,(sj.maxFav_h>thr).mean()*100))
print("\nDONE")
