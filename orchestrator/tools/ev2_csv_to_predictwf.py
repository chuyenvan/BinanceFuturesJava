#!/usr/bin/env python3
# Convert ev2_preds_n6.csv.gz (win,ts,symbol,p6,p9) -> predict_wf_<win>.bin (26B big-endian:
#   long ts, short symId, float p4,p12,p24,p72). Cam p6 vao CA 4 horizon slot -> WFO_SEL_HORIZON_IDX
#   nao cung ra cung P(win)=p6. buildFundingFromWfFiles se DAO DAU score=1-p6, forward-fill 15m->phut.
# symId LAY TU symbol_map.csv (symId,symbol) — PHAI la map SIM dung (khop predict_wf cu). Verify:
#   so symId trung + range khop predict_wf cu truoc khi tin (gate-check symId alignment).
# Dung: python ev2_csv_to_predictwf.py <ev2_preds.csv.gz> <symbol_map.csv> <out_dir>
import sys, struct, os
import pandas as pd

def main():
    preds_csv, map_csv, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out_dir, exist_ok=True)
    mp = pd.read_csv(map_csv)                       # cols: symId, symbol
    sym2id = dict(zip(mp["symbol"], mp["symId"].astype(int)))
    df = pd.read_csv(preds_csv)
    miss = sorted(set(df["symbol"]) - set(sym2id))
    if miss:
        print("WARN symbol khong co trong map (bo):", len(miss), miss[:10])
        df = df[df["symbol"].isin(sym2id)].copy()
    df["symId"] = df["symbol"].map(sym2id).astype(int)
    total = 0
    for win, g in df.groupby("win"):
        fp = os.path.join(out_dir, f"predict_wf_{int(win):02d}.bin")
        with open(fp, "wb") as f:
            for ts, symId, p6 in zip(g["ts"].astype("int64"), g["symId"], g["p6"].astype("float32")):
                f.write(struct.pack(">qh4f", int(ts), int(symId), p6, p6, p6, p6))
        total += len(g)
        print(f"  win {int(win):02d}: {len(g)} rec -> {os.path.basename(fp)}")
    print(f"XONG: {total} rec, {df['win'].nunique()} window, {df['symId'].nunique()} symId -> {out_dir}")

if __name__ == "__main__":
    main()
