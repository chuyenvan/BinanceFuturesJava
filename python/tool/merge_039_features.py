# TASK-039 (chuẩn bị) — MERGE 45 feature: 40 cột Tool1 (.bin.gz) + 5 cột OI Tool2.
# CHỈ phần merge feature. Phần ghép label triple-barrier (024) + train để SAU
# (đã chốt target +6% — xem TODO cuối file).
#
# Layout nhị phân (đọc từ Java, big-endian — DataOutputStream mặc định):
#   Tool1 ExportFeaturesForPythonTool: long time(8B) + short symId(2B) + 40×float(160B) = 170B/record
#   Tool2 ExportFundingOiPerCoin:      long ts(8B)   + short symId(2B) + 5×float(20B)   = 30B/record
# Tên cột lấy từ FundingMarketFeatures.java (#1-#45).
#
# Chạy ví dụ:
#   python3 merge_039_features.py \
#     --feature-glob "/d/claudedata/ff40/*.bin.gz" \
#     --oi-glob      "/d/claudedata/oi/*.bin.gz" \
#     --out /d/claudedata/dataset_039_features.parquet

import argparse, glob, gzip, struct
import numpy as np
import pandas as pd

# 40 cột Tool1 — KHỚP CHÍNH XÁC convertFeaturesToArray() trong ExportFeaturesForPythonTool (dòng ~228).
# CHÚ Ý: mảng feature KHÔNG có rateDownAvg (#6 thật là rateDown15MAvg) — field đó khai báo nhưng không xuất.
F40 = [
    "btcMomentum1H","btcMomentum4H","btcMomentum24H","btcDominance","marketBreadthStrength",   # 1-5
    "rateDown15MAvg","momentum1H","momentum4H","momentum24H","rsi1H","distFromLow24H","volatilityShock",  # 6-12
    "basketMomentum15M","basketMomentum1H","basketMomentum24H","basketRsi14","basketVolSpike",  # 13-17
    "coinFundingRate","basketFundingAvg","fundingRateAvg24H","fundingRateTrend",                # 18-21
    "fundingPercentileCoin","fundingZCoin","fundingPersistence","fundingSum24h","fundingAbs",   # 22-26
    "volumeZCoin","volumeTrend",                                                                # 27-28
    "distFromHigh24H","rangePosition24H","atrSqueeze","relStrengthBtc24H",                       # 29-32
    "fundingRankCS","volumeZRankCS","momentumRankCS",                                           # 33-35
    "ret15m","rvol15m","volumeZ5m","closePosRange15m","wickRatio15m",                            # 36-40
]
# 5 cột Tool2 OI (#41-45) — thứ tự dos.writeFloat trong ExportFundingOiPerCoin.writeCoin
OI5 = ["oiDelta24hCoin","oiZCoin","lsGlobalCoin","lsToptraderCoin","takerBuyRatioCoin"]

# ⚠️ CHÚ Ý CẦN XÁC NHẬN KHI CHẠY THẬT:
# F40 phải KHỚP CHÍNH XÁC số float mà Tool1 ghi (=40). Nếu len(F40)!=40 -> dừng.
# Thứ tự #19-21 (coinFundingRate/basketFundingAvg/fundingRateAvg24H/fundingRateTrend) là 4 field
# nhưng đánh số tới 21 -> cần soi lại extractFeatures xem có gộp/bỏ field nào không.
# Script tự kiểm: nếu record_size/4 sau khi trừ 10 byte (ts+symId) != len(F40) -> báo lỗi rõ.

REC1 = 8 + 2 + 40 * 4   # 170
REC2 = 8 + 2 + 5 * 4    # 30


def read_bin(path, n_float, names, rec_size):
    """Đọc 1 file .bin.gz -> DataFrame [ts, symId, *names]. Big-endian."""
    with gzip.open(path, "rb") as fh:
        raw = fh.read()
    if len(raw) % rec_size != 0:
        raise ValueError(f"{path}: size {len(raw)} không chia hết {rec_size} — sai layout?")
    n = len(raw) // rec_size
    # numpy structured dtype, big-endian: >i8 ts, >i2 symId, >f4 × n_float
    dt = np.dtype([(">ts", ">i8"), (">sym", ">i2")] + [(nm, ">f4") for nm in names])
    arr = np.frombuffer(raw, dtype=dt, count=n)
    df = pd.DataFrame({"ts": arr[">ts"], "symId": arr[">sym"].astype(np.int32)})
    for nm in names:
        df[nm] = arr[nm].astype(np.float32)
    return df


def read_glob(pattern, n_float, names, rec_size, tag):
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"[{tag}] KHÔNG tìm thấy file khớp: {pattern}")
    parts = []
    for f in files:
        d = read_bin(f, n_float, names, rec_size)
        print(f"[{tag}] {f}: {len(d):,} record")
        parts.append(d)
    out = pd.concat(parts, ignore_index=True)
    print(f"[{tag}] TỔNG: {len(out):,} record, {len(files)} file")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feature-glob", required=True, help="glob .bin.gz Tool1 (40 cột)")
    ap.add_argument("--oi-glob", required=True, help="glob .bin.gz Tool2 (5 cột OI)")
    ap.add_argument("--out", required=True, help="đường dẫn parquet output")
    args = ap.parse_args()

    assert len(F40) == 40, f"F40 phải đúng 40 tên, đang có {len(F40)} — soi lại extractFeatures!"
    assert len(OI5) == 5, f"OI5 phải đúng 5 tên, đang có {len(OI5)}"

    feat = read_glob(args.feature_glob, 40, F40, REC1, "Tool1")
    oi = read_glob(args.oi_glob, 5, OI5, REC2, "Tool2-OI")

    # merge_asof theo symId (by) + ts (on), backward — KHÔNG nhìn tương lai
    feat = feat.sort_values(["symId", "ts"]).reset_index(drop=True)
    oi = oi.sort_values(["symId", "ts"]).reset_index(drop=True)
    merged = pd.merge_asof(feat, oi, on="ts", by="symId", direction="backward")

    n_oi_null = merged[OI5[0]].isna().sum()
    print(f"=== MERGE: {len(merged):,} record | OI null {n_oi_null:,} ({n_oi_null/len(merged)*100:.1f}%) ===")
    print(f"=== cột ({merged.shape[1]}): {list(merged.columns)} ===")

    merged.to_parquet(args.out, index=False)
    print(f"=== WROTE {args.out} shape {merged.shape} ===")

    # ============================================================
    # TODO — BƯỚC SAU (sau khi 037/038 export xong + chạy merge này):
    #   1. Ghép label triple-barrier 024: target +6% (ĐÃ CHỐT 2026-06-18).
    #      label6 = calculateLabelType(+6%) — 5 lớp 0=Fail/1=72H/2=24H/3=4H/4=15M.
    #      Selector target: P(fail) = pred[0] (KHÓA thứ tự lớp — ADR-0011 §6).
    #   2. Align label theo (symId, ts), de-overlap per-symbol theo horizon, purge.
    #   3. Train XGBoost (như train_fundingfee_xgboost_optuna): split thời gian KHÔNG shuffle,
    #      KHÔNG scale, purge horizon, holdout 12 tháng OOS.
    #   4. Gate: LIFT≥1.20, N≥100, z≥2, |t-IC|≥2 + BEAT rule baseline (không beat -> bỏ ML).
    # ============================================================


if __name__ == "__main__":
    main()
