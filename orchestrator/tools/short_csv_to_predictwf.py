#!/usr/bin/env python3
# Convert short_preds.csv.gz (win,ts,symbol,ps,oi_z,oi_delta24h) -> predict_wf_<win>.bin (26B big-endian:
#   long ts, short symId, float p4,p12,p24,p72). Nhan bF ev2_csv_to_predictwf.py NHUNG doc cot `ps`
#   (=P(HIT_short)) thay `p6`. Cam ps vao CA 4 horizon slot -> WFO_SEL_HORIZON_IDX nao cung ra P(HIT_short).
#   buildFundingFromWfFiles se DAO DAU score=1-ps, forward-fill 15m->phut, engine chon score THAP (ps CAO).
#
# ⚠️ KHONG loc ps (nhu ban ev2 goc) — vi buildFundingFromWfFiles forward-fill 15m->phut: bo bot row
#   ps thap se lam gia tri ps CAO truoc do "song" LAU hon dang le (dai qua moc 15m ke tiep) -> SINH
#   entry gia. Giu DU moi row de forward-fill trung khop long pipeline. File ~78MB (3M row) — chap nhan.
# symId LAY TU symbol_map.csv (symId,symbol) — PHAI la map SIM dung (khop predict_wf cu). Verify:
#   so symId trung + range khop predict_wf cu truoc khi tin (gate-check symId alignment).
# Dung: python short_csv_to_predictwf.py <short_preds.csv.gz> <symbol_map.csv> <out_dir>
import sys, struct, os
import pandas as pd

def main():
    preds_csv, map_csv, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out_dir, exist_ok=True)
    mp = pd.read_csv(map_csv)                       # cols: symId, symbol
    sym2id = dict(zip(mp["symbol"], mp["symId"].astype(int)))
    df = pd.read_csv(preds_csv)
    if "ps" not in df.columns:
        raise SystemExit("FATAL: cot ps khong co trong " + preds_csv + " (columns=" + ",".join(df.columns) + ")")
    miss = sorted(set(df["symbol"]) - set(sym2id))
    if miss:
        print("WARN symbol khong co trong map (bo):", len(miss), miss[:10])
        df = df[df["symbol"].isin(sym2id)].copy()
    df["symId"] = df["symbol"].map(sym2id).astype(int)
    total = 0
    for win, g in df.groupby("win"):
        fp = os.path.join(out_dir, f"predict_wf_{int(win):02d}.bin")
        with open(fp, "wb") as f:
            for ts, symId, ps in zip(g["ts"].astype("int64"), g["symId"], g["ps"].astype("float32")):
                f.write(struct.pack(">qh4f", int(ts), int(symId), ps, ps, ps, ps))
        total += len(g)
        print(f"  win {int(win):02d}: {len(g)} rec -> {os.path.basename(fp)}")
    print(f"XONG: {total} rec, {df['win'].nunique()} window, {df['symId'].nunique()} symId -> {out_dir}")

if __name__ == "__main__":
    main()
