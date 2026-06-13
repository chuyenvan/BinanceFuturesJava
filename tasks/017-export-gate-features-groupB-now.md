# TASK-017: Export feature gate NHÓM B giá/xu-hướng + funding-breadth (B1–B5, B7) — code mới + validate RIÊNG

- **status:** TODO (H1 — feature gate nhóm B, phần LÀM NGAY). Sau khi 015 (nhóm A) PASS.
- **owner:** _(điền khi claim — đồng bộ `docs/AGENTS.md`)_ · **updated:** _(điền)_
- **Spec:** `docs/H1_GATE_SPEC.md` §2.2 (B1–B5, B7) + §2.4. **Code MỚI.** B6/B8 (OI/LS-market) CHỜ 013 → TASK-018 riêng.

## Mục tiêu
Code + export 6 feature mới, align `t` với `gate_return.csv` (sample 15m, 2021→nay), **mỗi feature validate RIÊNG**.

## Feature — công thức đã CHỐT (H1_GATE_SPEC §2.2)
- **B1 price-vs-SMA (BTC):** `close/SMA−1` — 15m-SMA20 + 4h-SMA50 (2 cột, tương đối).
- **B2 alignment:** trendLong=sign(close_4h − SMA50_4h); momShort=sign(ret_15m N nến); `alignment=momShort×trendLong ∈{−1,0,+1}` + cờ `bearRally=(trendLong<0 AND momShort>0)`.
- **B3 regime MA200 (daily):** daily close BTC gom từ 4h; `distMA200=close_daily/MA200−1`; `regime=sign(distMA200)`.
- **B4 ETH momentum:** `ethRet_15m`, `ethRet_4h`.
- **B5 đồng-pha BTC-ETH:** `coDown=(btcRet_4h<0 AND ethRet_4h<0)`; `dispersion=|btcRet_4h − ethRet_4h|`; `rollingCorr`=corr(btcRet,ethRet) cửa sổ 24h/15m.
- **B7 funding-breadth:** `pctFundingHigh`=% coin funding > ngưỡng cao; `fundingDispersion` (độ tản cross-coin). Từ `funding_data`.

## Nguồn
- `kline_15m_btceth`/`kline_4h_btceth` (TASK-009) cho BTC + ETH.
- daily BTC gom từ 4h (6×4h/ngày) cho MA200 (B3).
- `funding_data` (Aerospike 226) cho B7.

## ⚠️ Hai bẫy bắt buộc xử đúng
1. **Look-ahead trong "percentile/ngưỡng" (B7):** `pctFundingHigh` so funding với "ngưỡng cao" — ngưỡng đó phải tính từ dữ liệu **≤ t** (expanding/rolling), **TUYỆT ĐỐI không** dùng percentile full-sample (sẽ rò tương lai vào quá khứ). Ghi rõ cách tính ngưỡng.
2. **Warmup KHÔNG fill 0 giả:** B3 MA200 (200 ngày đầu, ~2021) và B5 rollingCorr (cửa sổ đầu) thiếu dữ liệu → đánh dấu **NaN/loại dòng**, KHÔNG fill 0 (0 = "giá đúng bằng MA200" / "corr=0" là nghĩa SAI, model học nhiễu). Phân biệt rõ thiếu-warmup vs giá-trị-thật.

## Yêu cầu chung
- Mỗi feature tính tại mỗi `t` (15m) khớp `gate_return.csv`. Look-ahead: chỉ nến ĐÓNG ≤ t (4h/daily: chỉ nến hoàn tất).
- B7 aggregate cross-coin phải **GỒM coin backfill** (không lọc DIED hẹp — xem cảnh báo TASK-015); báo #coin/năm.
- Format cột + key `t` khớp loader H2 (thống nhất với 015).

## Validate RIÊNG mỗi feature (§2.4) — PASS mới sang feature kế
(a) range/phân bố; (b) NaN/Inf→0 đúng (xử warmup ở trên); (c) recompute ~5 mốc bằng đường khác; (d) look-ahead (nến/percentile ≤t); (e) align `t` với gate_return.

## An toàn / tài nguyên
- Đọc-only (226), ghi `outputs/`. Chạy **trên 226**, KHÔNG đồng thời job nặng khác trên 226 (CLAUDE.md "Tài nguyên"). SLF4J.

## Acceptance
- [ ] 6 feature (B1–B5, B7), align gate_return, 2021→nay.
- [ ] Mỗi feature validate (a–e) PASS + số liệu.
- [ ] B7 ngưỡng percentile tính expanding ≤t (không leak); báo cách tính.
- [ ] Warmup (MA200, rollingCorr) NaN/loại — không fill 0 giả.
- [ ] B7 aggregate gồm coin backfill (#coin/năm).

## (Code điền)
- **B1–B5 công thức triển khai + validate:** …
- **B7 funding-breadth (ngưỡng expanding) + #coin:** …
- **Xử warmup MA200/rollingCorr:** …
