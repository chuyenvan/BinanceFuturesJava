# RESULT — TREND/VOL RANK-IC SCREENING (STANDALONE, CRYPTO DEV)

**Ngay:** 2026-09-17
**Pre-reg:** `docs/prereg/PREREG_TREND_RANK_IC.md` (commit `e26e3c3`)
**Script:** `research/analysis/trend_rank_ic.py` + `research/analysis/trend_rank_ic_common.py`
**Trang thai:** DESCRIPTIVE SCREENING (khong phai bang chung alpha). Chay MOT lan, khong tune.

---

## 1. Nguon du lieu per-coin (da xac minh)

- `/home/ubuntu/java/fsrun/CLOSES_1H.bin` — binary big-endian
  `[ts>i8, sym>i2, c>f4]` = close 1h per coin (ts = Binance open_time, c = close tai
  close_time = ts+1h). 10.322.386 dong, 627 symbol-id, 2021-01-01 -> 2026-01-01 (UTC).
- Map id->ten: `/home/ubuntu/selector_pred_out/symbol_map.csv`.
- Doi chung S1: `/home/ubuntu/ledger/pred_s1a2x1.parquet` (ts,sym,score; score thap=tot;
  2021-12-31 -> 2025-12-31; 620 symbol; moi ~15 phut).
- DEV = 2021-01-01 .. 2025-12-31. Nam 2026 (590 dong seal) LOAI. Snapshot 1h co dinh.

## 2. Bang rank-IC (Spearman cross-section) — full cua so DEV

Feature: `trend` = mean over {SMA50,SMA100,SMA200} cua I[close>SMA_k] (warmup 200 bar);
`mom` = trailing return 168h; `vol` = std(1h return) 168h. Target = forward return 1h/4h/24h.
CI = block-72h bootstrap, 2000 rep, seed 20260905, inflate x1.21. ~187 coin/snapshot.

| h | feat | rankIC mean | CI95 (x1.21) | pearson | n_snap |
|---|---|---|---|---|---|
| 1h | trend | **-0.0241** | [-0.0260, -0.0221] | -0.0027 | 43411 |
| 1h | mom | -0.0234 | [-0.0255, -0.0212] | -0.0017 | 43630 |
| 1h | vol | -0.0334 | [-0.0355, -0.0312] | -0.0060 | 43630 |
| 1h | S1 | -0.0247 | [-0.0264, -0.0229] | -0.0004 | 35046 |
| 4h | trend | -0.0300 | [-0.0335, -0.0267] | -0.0026 | 43410 |
| 4h | mom | -0.0338 | [-0.0376, -0.0299] | -0.0025 | 43631 |
| 4h | vol | -0.0524 | [-0.0568, -0.0481] | -0.0115 | 43631 |
| 4h | S1 | -0.0407 | [-0.0440, -0.0370] | -0.0040 | 35047 |
| 24h | trend | -0.0363 | [-0.0429, -0.0297] | -0.0051 | 43413 |
| 24h | mom | -0.0490 | [-0.0575, -0.0406] | -0.0060 | 43631 |
| 24h | vol | **-0.0905** | [-0.1017, -0.0799] | -0.0229 | 43631 |
| 24h | S1 | -0.0693 | [-0.0770, -0.0613] | -0.0100 | 35047 |

## 3. So sanh "cung moc" (chi snapshot co S1, n=35047, 2022-2025)

| h | trend | mom | vol | S1 |
|---|---|---|---|---|
| 1h | -0.0219 | -0.0208 | -0.0320 | -0.0247 |
| 4h | -0.0286 | -0.0308 | -0.0505 | -0.0407 |
| 24h | -0.0367 | -0.0446 | -0.0876 | -0.0693 |

## 4. KET LUAN

**KHONG CO TIN HIEU TREND-FOLLOWING. Ghi NULL. DUNG huong "trend/vol lam ranking"
cho T170, khong ton sim nao.**

Giai thich (chinh xac, khong bien ho):

1. **Tat ca rank-IC deu AM** — nguoc dau voi gia thuyet trend-following (gia thuyet can
   IC DUONG: coin trend manh -> forward return cao). Thuc te: coin dang uptrend manh
   (trend cao) lai co forward return THAP hon, dac biet horizon dai. Day la
   **mean-reversion / reversal ngan han**, khong phai trend continuation.
2. **trend + mom YEU HON S1** o ca 3 horizon (bang muc 3). Theo pre-reg
   ("neu trend khong hon duoc S1 => khong them gia tri"): trend KHONG them gia tri.
3. **vol la feature manh nhat, va no AM** (rank-IC -0.09 o 24h, manh hon S1 -0.069).
   Day la **low-vol premium / de-risking**: coin vol cao -> forward return thap.
   No KHONG phai "trend alpha"; no cung huong voi ket qua ablation cua holdout
   (chi vol-targeting co tin hieu, trend khong co; p=0.109). La hieu ung de-risking
   da biet, khong phai cai ma ke hoach T170 huong toi ("xep hang coin de vao lenh").
4. **Do lon rat nho**: |rank-IC| <= 0.09 o moi noi. Muc nay gan nhu chac chan vo dung
   sau phi/slippage/exit (pre-reg da ghi: "IC nho van co the vo dung sau phi/exit").

=> Huy bo gia thuyet "tap dac trung trend/vol xep hang coin de vao lenh trend" tren
crypto DEV. Ket qua nay CUNG CO chu khong mau thuan voi holdout: thanh phan trend
khong mang tin hieu (o day con AM nhe); chi con lai tin hieu vol (am, de-risking).

## 5. Ghi chu (khong phai buoc tich hop)

- Tin hieu **vol (low-vol)** la co that va on dinh nhung AM, ban chat la de-risking
  (cung phia voi vol-targeting cua holdout). Neu muon theo huong nay, phai pre-reg
  RIENG cho "low-vol ranking / de-risking", khong phai "trend ranking", va khong duoc
  tron vao ket luan trend. KHONG tu tien tich hop.
- `contains_zero=False` cho moi o (CI deu nam am, ngoai 0) chi la ket qua cua mau rat
  lon (43k snapshot -> SE cua mean rat nho). Dieu do KHONG dong nghia co alpha; dau am
  + do lon nho + yeu hon S1 moi la noi dung quyet dinh.
