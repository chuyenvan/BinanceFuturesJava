#!/usr/bin/env python3
# Convert ev2_preds_n6.csv.gz (win,ts,symbol,p6,p9,oi_z,...) -> predict_wf_<win>.bin (26B big-endian:
#   long ts, short symId, float p4,p12,p24,p72) VOI OI_Z VETO (long).
#
# KHAC ev2_csv_to_predictwf.py: THEM buoc LOC entry theo oi_z (tang DU LIEU, KHONG dung sim code):
#   1. mask70 = rows co p6 >= P6_MIN (mac dinh 0.7) = tap "tradable" (candidate long).
#   2. oiz_q = quantile(OIZ_Q) cua oi_z TREN tap mask70 (mac dinh Q=0.75 — NOI HON Q0.5 de khoi phuc tan suat).
#   3. CHI GIU rows: p6>=P6_MIN AND oi_z<=oiz_q (giu OIZ_Q% oi_z THAP nhat -> edge_spread am proxy).
#   LICH SU: Q0.5 cho WFE1.49/BURN2 nhung 9/16 window doi lenh -> FAIL %OOS; Q0.75 giu nhieu entry hon.
#   NaN oi_z bi loai (oi_z<=q50 False cho NaN). Cam p6 vao CA 4 horizon slot nhu cu ->
#   buildFundingFromWfFiles DAO DAU score=1-p6, forward-fill 15m->phut, engine chon score thap.
# symId LAY TU symbol_map.csv (symId,symbol) — PHAI la map SIM dung (khop predict_wf cu).
# Dung: python ev2_csv_to_predictwf_oiz.py <ev2_preds.csv.gz> <symbol_map.csv> <out_dir> [P6_MIN] [OIZ_Q]
import sys, struct, os
import pandas as pd

def main():
    preds_csv, map_csv, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    # P6_MIN: ENV P6_MIN > positional argv[4] > default 0.7. ENV thang de nut CE pred_convert
    #   (ep positional 0.7) van ha duoc nguong xuong 0.5 ma KHONG sua button: `P6_MIN=0.5 pred_convert ...`.
    #   Default 0.7 giu HANH VI CU byte-identical khi khong set env va button truyen 0.7.
    _p6_env = os.environ.get("P6_MIN")
    if _p6_env is not None and _p6_env.strip() != "":
        p6_min = float(_p6_env)
    elif len(sys.argv) > 4:
        p6_min = float(sys.argv[4])
    else:
        p6_min = 0.7
    oiz_q  = float(sys.argv[5]) if len(sys.argv) > 5 else 0.75
    os.makedirs(out_dir, exist_ok=True)
    mp = pd.read_csv(map_csv)                       # cols: symId, symbol
    sym2id = dict(zip(mp["symbol"], mp["symId"].astype(int)))
    df = pd.read_csv(preds_csv)
    n_all = len(df)
    if "oi_z" not in df.columns:
        raise SystemExit("FATAL: cot oi_z khong co trong " + preds_csv + " (columns=" + ",".join(df.columns) + ")")
    miss = sorted(set(df["symbol"]) - set(sym2id))
    if miss:
        print("WARN symbol khong co trong map (bo):", len(miss), miss[:10])
        df = df[df["symbol"].isin(sym2id)].copy()
    df["symId"] = df["symbol"].map(sym2id).astype(int)

    # ---- OI_Z VETO ----
    mask70 = df["p6"] >= p6_min
    n70 = int(mask70.sum())
    if n70 == 0:
        raise SystemExit("FATAL: 0 rows co p6>=%.3f — khong the tinh nguong oi_z" % p6_min)
    oiz_q50 = float(df.loc[mask70, "oi_z"].quantile(oiz_q))
    keep = mask70 & (df["oi_z"] <= oiz_q50)
    kept = df[keep].copy()
    n_kept = len(kept)
    n_nan_oiz70 = int(df.loc[mask70, "oi_z"].isna().sum())
    print("=== OI_Z VETO ===")
    print(f"  rows tong        : {n_all}")
    print(f"  rows p6>={p6_min:.2f}     : {n70}  (NaN oi_z trong tap nay: {n_nan_oiz70})")
    print(f"  oiz_q{int(oiz_q*100):02d} nguong    : {oiz_q50:.6f}")
    print(f"  rows GIU (veto)  : {n_kept}  ({100.0*n_kept/max(n70,1):.1f}% cua tap p6>={p6_min:.2f})")

    total = 0
    for win, g in kept.groupby("win"):
        fp = os.path.join(out_dir, f"predict_wf_{int(win):02d}.bin")
        with open(fp, "wb") as f:
            for ts, symId, p6 in zip(g["ts"].astype("int64"), g["symId"], g["p6"].astype("float32")):
                f.write(struct.pack(">qh4f", int(ts), int(symId), p6, p6, p6, p6))
        total += len(g)
        print(f"  win {int(win):02d}: {len(g)} rec -> {os.path.basename(fp)}")
    print(f"XONG: {total} rec, {kept['win'].nunique()} window, {kept['symId'].nunique()} symId -> {out_dir}")

if __name__ == "__main__":
    main()
