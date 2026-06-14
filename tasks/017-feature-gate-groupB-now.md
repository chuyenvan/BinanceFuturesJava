# TASK-017: Feature gate nhóm B-now (B1–B5 + B7) — code mới [CCD1]

- **status:** TODO. Giao CCD1 (rảnh sau 034). Code MỚI; làm song song 015 (khác feature, không đụng nhau). Ghép cần A+B nhưng code/validate riêng được ngay.
- **owner:** CCD #1 · **status:** DOING · **updated:** 2026-06-14
- **Spec gốc:** `docs/H1_GATE_SPEC.md` §2.2 (B-giá/xu-hướng B1–B5 + B-crowdedness B7). B6/B8 (OI/LS) = TASK-018 (chờ 013).

## Nguồn data + nơi chạy
- `kline_15m_btceth` + `kline_4h_btceth` (TASK-009) + daily BTC gom từ 4h (B3) + `funding_data` (B7).
- Đọc **226** (đã có 15m/4h từ 009; funding_data 754 từ 034 backup) — `IS_KAGGLE_MODE=true` như 015. Chạy Kaggle hoặc 226. ĐỌC-ONLY, KHÔNG ghi 242.

## Feature (mỗi cái 1 đại diện — §2.2)
- **B1 price-vs-SMA (BTC):** `close/SMA_n − 1` (tương đối). 2 cột: 15m-SMA20, 4h-SMA50.
- **B2 alignment ngắn-dài:** `trendLong=sign(close_4h − SMA50_4h)`, `momShort=sign(ret_15m N nến)`; `alignment=momShort×trendLong ∈{−1,0,+1}` + cờ `bearRally=(trendLong<0 AND momShort>0)`.
- **B3 regime MA200 (daily):** daily close BTC gom từ 4h; `distMA200=close_daily/MA200−1`; `regime=sign(distMA200)`. Warmup 200 ngày.
- **B4 ETH momentum:** `ethRet_15m`, `ethRet_4h`.
- **B5 đồng-pha BTC–ETH:** `coDown=(btcRet_4h<0 AND ethRet_4h<0)`; `dispersion=|btcRet_4h−ethRet_4h|`; `rollingCorr` = corr(btcRet,ethRet) cửa sổ 24h trên 15m.
- **B7 funding-breadth:** từ `funding_data` (KHÔNG chỉ basket-avg): `pctFundingHigh` = % coin funding > ngưỡng cao (percentile lịch sử); `fundingDispersion` (độ tản cross-coin). **Aggregate GỒM coin backfill — KHÔNG lọc `diedSymbol`** (như cảnh báo 015).

## Look-ahead clean
- Feature chỉ dùng `[.., t]`: nến 15m/4h ĐÓNG ≤ t; daily MA200 dùng ngày ≤ ngày(t); funding ≤ t. Align `t` lưới 15m.

## Output + validate RIÊNG (§2.4 — PASS mới ghép 025)
- `outputs/gate_features_groupB_now.csv`, key `tEpochMs`(+tDate), align `gate_return.csv` (012).
- Validate mỗi feature: (a) range/percentile; (b) NaN/Inf→0 (phân biệt 0-thật); (c) recompute ~5 mốc đường khác; (d) look-ahead (nến đóng ≤t); (e) align gate_return (cùng tập t).

## An toàn / quy tắc
- ĐỌC-ONLY 226; ghi `outputs/`. SLF4J (KHÔNG System.out).
- **`System.exit(0)` cuối main** (CLAUDE.md #6 — tránh treo như 015).
- Nếu chạy Kaggle: ghi mục Job-đang-chạy bàn giao (#4) + checkpoint nếu lâu (#5). B-now nhẹ hơn 015 (chỉ BTC/ETH 15m/4h + funding, không quét 1m toàn coin 5 năm) → nhanh.

## Acceptance
- [ ] CSV B1–B5 + B7, align gate_return, 2021→nay.
- [ ] Validate (a–e) PASS mỗi feature, kèm số.
- [ ] Look-ahead clean; B7 survivorship (không lọc DIED).
- [ ] Exit sạch (System.exit).

## (Code điền)
- **Class + commit:** … · **Validate số:** … · **Job Kaggle (nếu có):** …
