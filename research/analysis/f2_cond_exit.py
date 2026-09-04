"""F2 - Do OFFLINE luat conditional exit tren nhan co san (khong dung lai gia).

Luat do: neu tai gio H lenh chua dat lai theta (maxFav_H < theta) thi cat tai gio H;
nguoc lai giu nguyen hanh vi hien tai. Dung nhan /home/ubuntu/label_15m/*.pb
(luoi 15m, horizon 4h/12h/24h/72h) join voi printDone.csv cua mot sim run.

Chay: python3 research/analysis/f2_cond_exit.py [TAG]
"""
import glob
import logging
import sys

import pandas as pd

sys.path.insert(0, "/home/ubuntu/sel1m_code")
from funding_label_pb import read_label  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("f2")

TAG = sys.argv[1] if len(sys.argv) > 1 else "C2b"
HS = ["4h", "12h", "24h", "72h"]
THETAS = [0.005, 0.01, 0.02, 0.03, 0.04, 0.05]
VN = 7 * 3600 * 1000

df = pd.read_csv("/home/ubuntu/java/devrun/%s/storage/printDone.csv" % TAG)
df = df[df.level == "PREDICT_SYMBOL_TRADE"].copy()
log.info("=== %s: %d lenh PREDICT_SYMBOL_TRADE ===", TAG, len(df))
log.info("side: %s", df.side.value_counts().to_dict())
log.info("status: %s", df.status.value_counts().to_dict())
N_LOSER = int((df.status == "STOP_LOSS_DONE").sum())
N_WIN = int((df.status == "STOP_MARKET_DONE").sum())

df["ts"] = pd.to_datetime(df.start, format="%Y%m%d %H:%M").astype("int64") // 10 ** 6 - VN
df["ts"] = (df["ts"] // (15 * 60000)) * (15 * 60000)
df["symbol"] = df.sym + "USDT"
n_all = len(df)

cols = ["tEpochMs", "symbol"] + [f"{k}_{h}" for h in HS for k in ("maxFav", "maxAdv", "retEnd")]
files = sorted(glob.glob("/home/ubuntu/label_15m/funding_label_2022*.pb")
               + glob.glob("/home/ubuntu/label_15m/funding_label_2023*.pb")
               + glob.glob("/home/ubuntu/label_15m/funding_label_20240101*.pb")
               + glob.glob("/home/ubuntu/label_15m/funding_label_20240401*.pb"))
keys = df[["symbol", "ts"]].drop_duplicates()
parts = []
for f in files:
    lab = read_label(f, usecols=cols)
    keep = lab.merge(keys, left_on=["symbol", "tEpochMs"], right_on=["symbol", "ts"], how="inner")
    parts.append(keep)
    log.info("  %-42s rows=%9d matched=%4d", f.split("/")[-1], len(lab), len(keep))
lb = pd.concat(parts).drop(columns=["ts"])
m = df.merge(lb, left_on=["symbol", "ts"], right_on=["symbol", "tEpochMs"], how="inner")

rate = 100.0 * len(m) / n_all
log.info("JOIN: %d/%d = %.2f%%", len(m), n_all, rate)
miss = df.merge(lb, left_on=["symbol", "ts"], right_on=["symbol", "tEpochMs"], how="left")
miss = miss[miss.tEpochMs.isna()]
if len(miss):
    log.info("MISS theo status: %s", miss.status.value_counts().to_dict())
    log.info("MISS top sym: %s", miss.sym.value_counts().head(10).to_dict())
if rate < 95.0:
    log.error("JOIN < 95%% -> DUNG, khong doc tiep luoi.")
    sys.exit(1)

# he so quy doi profit(%) -> pnl (don bay hieu dung + phi + DCA)
sub = m[m.profit.abs() > 1.0]
K = float((sub.pnl / (sub.margin * sub.profit / 100.0)).median())
log.info("he so quy doi K = median(pnl / (margin*profit/100)) = %.4f (n=%d)", K, len(sub))
log.info("mean(profit|STOP_LOSS_DONE)=%.2f%%  mean(profit|STOP_MARKET_DONE)=%.2f%%",
         m.loc[m.status == "STOP_LOSS_DONE", "profit"].mean(),
         m.loc[m.status == "STOP_MARKET_DONE", "profit"].mean())
log.info("maxFav phan bo cua nhom time-stop (STOP_LOSS_DONE):")
for h in HS:
    s = m.loc[m.status == "STOP_LOSS_DONE", "maxFav_%s" % h]
    log.info("  H=%-4s median=%.4f  p25=%.4f  p75=%.4f  %%<3%%=%.1f",
             h, s.median(), s.quantile(.25), s.quantile(.75), 100 * (s < 0.03).mean())

is_loser = m.status == "STOP_LOSS_DONE"
is_win = m.status == "STOP_MARKET_DONE"
rows = []
for h in HS:
    hh = int(h[:-1])
    for th in THETAS:
        cut = (m.time_order > hh) & (m["maxFav_%s" % h] < th)
        cl, cw = cut & is_loser, cut & is_win
        d_l = float((m.loc[cl, "margin"] * K * (m.loc[cl, "retEnd_%s" % h] - m.loc[cl, "profit"] / 100.0)).sum())
        d_w = float((m.loc[cw, "margin"] * K * (m.loc[cw, "retEnd_%s" % h] - m.loc[cw, "profit"] / 100.0)).sum())
        rows.append(dict(H=hh, theta=th, n_cut_loser=int(cl.sum()), pct_loser=100.0 * cl.sum() / N_LOSER,
                         n_cut_winner=int(cw.sum()), pct_winner=100.0 * cw.sum() / N_WIN,
                         ratio=(cl.sum() / cw.sum()) if cw.sum() else float("inf"),
                         pnl_now_cut=float(m.loc[cut, "pnl"].sum()), d_pnl_loser=d_l, d_pnl_winner=d_w,
                         d_pnl_tot=d_l + d_w,
                         GO=bool(100.0 * cl.sum() / N_LOSER >= 40.0 and 100.0 * cw.sum() / N_WIN <= 10.0)))
g = pd.DataFrame(rows)
log.info("\n=== LUOI (H, theta) | mau so: loser=%d winner=%d ===", N_LOSER, N_WIN)
gp = g.assign(theta=g.theta.map(lambda v: "%.3f" % v))
log.info(gp.to_string(index=False, float_format=lambda v: "%.2f" % v))
ok = g[g.GO]
log.info("\nCONG GO/NO-GO (>=40%% loser bi cat VA <=10%% winner bi cat oan): %s", "PASS" if len(ok) else "FAIL")
if len(ok):
    log.info("O thoa cong:\n%s", ok.assign(theta=ok.theta.map(lambda v: "%.3f" % v)).to_string(index=False, float_format=lambda v: "%.2f" % v))
    best = ok.sort_values(["pct_loser", "d_pnl_tot"], ascending=[False, False]).iloc[0]
    log.info("O cat nhieu loser nhat: H=%d theta=%.3f", int(best.H), best.theta)
g.to_csv("/home/ubuntu/java/fsrun/f2_grid_%s.csv" % TAG, index=False)
