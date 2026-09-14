"""DCA-SIGNAL — tra loi truc dien 3 cau hoi cua user (docs/PREREG_DCA_SIGNAL_GATE.md muc 8).

  (i)   so LEG va so CUM (vi the) thay doi bao nhieu % so voi baseline?
  (ii)  ti le lo RAW muc LEG (moi leg tinh rieng) co TANG khong?
  (iii) ti le lo HIEU DUNG muc VI THE (gop cac leg cua cum) so voi baseline ra sao?

Dung lai c3_rates.trades() (cum = (sym, end), leg = cumcount) — khong dinh nghia lai.
Leg-signal nhan dien bang: leg > 0 VA level == PREDICT_SYMBOL_TRADE (leg grid DCA cu mang
level DCA_LEVEL1 / BIG_DOWN nen khong lan). Tren baseline T170 khong co leg nao nhu vay.

Usage: python3 dca_signal_probe.py RG_A_T170 DS_DCA5 DS_DCA8 DS_DCA12
"""
import logging
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def one(tag):
    d = C.trades(tag)
    g = d.groupby(["sym", "end"])
    cl = g.agg(pnl=("pnl", "sum"), margin=("margin", "sum"), legs=("pnl", "size"))
    sig = d[(d.leg > 0) & (d.level == "PREDICT_SYMBOL_TRADE")]
    grid = d[(d.leg > 0) & (d.level != "PREDICT_SYMBOL_TRADE")]
    # cum CO leg-signal
    sig_keys = set(map(tuple, sig[["sym", "end"]].values))
    lead = d[d.leg == 0].set_index(["sym", "end"])
    res = {
        "tag": tag,
        "n_leg": len(d),
        "n_cluster": len(cl),
        "loss_raw_leg": 100.0 * (d.pnl <= 0).mean(),
        "loss_pos": 100.0 * (cl.pnl <= 0).mean(),
        "n_sig": len(sig),
        "n_grid": len(grid),
        "n_cluster_sig": len(sig_keys),
        "pnl_total": float(d.pnl.sum()),
        "pnl_sig": float(sig.pnl.sum()) if len(sig) else 0.0,
        "margin_leg1": float(d[d.leg == 0].margin.mean()),
        "margin_cluster": float(cl.margin.mean()),
    }
    # CUU: cum co leg-signal, leg-1 lo NHUNG tong cum lai duong
    rescue = saved = 0
    for k in sig_keys:
        if k not in cl.index or k not in lead.index:
            continue
        l1 = lead.loc[k]
        p1 = float(l1.pnl) if not hasattr(l1.pnl, "__len__") else float(l1.pnl.iloc[0])
        tot = float(cl.loc[k].pnl)
        if p1 <= 0:
            rescue += 1
            if tot > 0:
                saved += 1
    res["n_sig_leg1_loss"] = rescue
    res["n_sig_rescued"] = saved
    return res


def main():
    tags = sys.argv[1:]
    rows = [one(t) for t in tags]
    base = rows[0]
    log.info("=== (i) SO LENH — leg vs CUM (vi the) ===")
    log.info("%-14s %8s %8s %9s %9s %8s %8s %8s", "tag", "n_leg", "n_cum",
             "dleg%", "dcum%", "n_sig", "n_grid", "cum_sig")
    for r in rows:
        log.info("%-14s %8d %8d %+9.1f %+9.1f %8d %8d %8d", r["tag"], r["n_leg"],
                 r["n_cluster"], 100.0 * (r["n_leg"] / base["n_leg"] - 1),
                 100.0 * (r["n_cluster"] / base["n_cluster"] - 1),
                 r["n_sig"], r["n_grid"], r["n_cluster_sig"])

    log.info("")
    log.info("=== (ii)+(iii) TI LE LO: RAW muc LEG vs HIEU DUNG muc VI THE ===")
    log.info("%-14s %12s %12s %12s %12s", "tag", "loss_leg%", "d_vs_base",
             "loss_pos%", "d_vs_base")
    for r in rows:
        log.info("%-14s %12.2f %+12.2f %12.2f %+12.2f", r["tag"], r["loss_raw_leg"],
                 r["loss_raw_leg"] - base["loss_raw_leg"], r["loss_pos"],
                 r["loss_pos"] - base["loss_pos"])

    log.info("")
    log.info("=== CHAN DOAN leg-signal ===")
    log.info("%-14s %8s %12s %14s %14s %12s %12s", "tag", "n_sig", "pnl_sig",
             "cum_sig_leg1lo", "trong_do_CUU", "mMargin_leg1", "mMargin_cum")
    for r in rows:
        log.info("%-14s %8d %12.0f %14d %14d %12.0f %12.0f", r["tag"], r["n_sig"],
                 r["pnl_sig"], r["n_sig_leg1_loss"], r["n_sig_rescued"],
                 r["margin_leg1"], r["margin_cluster"])


if __name__ == "__main__":
    main()
