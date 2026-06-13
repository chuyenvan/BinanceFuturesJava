# TASK-013: Verify + backfill OI / long-short / taker history từ data.binance.vision/metrics

- **status:** TODO (data — mở khoá chân OI cho funding model). CHẠY ĐƯỢC NGAY (độc lập).
- **owner:** _(điền khi claim — đồng bộ `docs/AGENTS.md`)_ · **updated:** _(điền)_
- **Liên hệ:** ADR-0011 §5.3 (OI/LS/taker — đảo kết luận "không backfill được"). Forward poll cho live = TASK-007 phần C (riêng). Đây là HISTORY cho train.

## Bối cảnh (user phát hiện 2026-06-13)
`https://data.binance.vision/?prefix=data/futures/um/daily/metrics/<SYMBOL>/` — dump daily, mỗi file 1 ngày, granularity ~5m, **CÓ từ 2020** (user kiểm BTC). Cùng host đã dùng backfill ticker (004/005). Header:
```
create_time, symbol, sum_open_interest, sum_open_interest_value,
count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio,
count_long_short_ratio, sum_taker_long_short_vol_ratio
```
→ `sum_open_interest_value` (USDT) = OI để dùng (chuẩn hoá cross-coin); + long/short (top-trader account & vị thế, global) + taker buy/sell. Giải chân thiếu nhất của funding (ADR-0011).

## BƯỚC 1 — VERIFY (GATE, làm TRƯỚC, KHÔNG backfill vội)
Báo cáo 4 điểm cho user/Desktop soát trước khi tải đại trà:
1. **Granularity + format:** tải 1–2 file daily (BTC + 1 alt) → đếm dòng/ngày (288 = 5m?), xác nhận bước thời gian + timezone của `create_time` (UTC?) + có header/đuôi lạ.
2. **Coverage per-coin (PHÂN TÍCH CHI TIẾT — user nhấn):** lập **bảng mọi coin → [firstSeen, lastSeen] metrics + #ngày thiếu (gap)**. Kiểm cụ thể "đủ lịch sử không": vd coin niêm yết **2023-01-04** thì metrics CÓ đủ từ 2023-01-04 hay khuyết đoạn đầu? **Đối chiếu firstSeen-metrics vs firstSeen-ticker** (từ lifecycle 010): coin có ticker mà thiếu metrics (hoặc ngược) → đánh dấu. Alt chỉ có từ ngày list — KHÔNG giả định mọi coin từ 2020. **Xuất bảng coverage ra file** để Desktop/user soát.
3. **Đơn vị khớp forward:** so `sum_open_interest_value` (metrics) vs `openInterestHist.sumOpenInterestValue` (API, dùng ở 007-C) tại vài mốc TRÙNG → cùng định nghĩa/đơn vị? Lệch → phải chuẩn hoá kẻo **bậc thang train/serve**.
4. **Dedup + gap:** mẫu user dán đã có 2 dòng trùng → cần dedup theo `create_time`; đếm ngày thiếu file.

## BƯỚC 1.5 — CHỐT SCHEMA OI CHUNG (thống nhất history + forward — user: "tránh mỗi ông lưu một kiểu")
History (013) và forward poll (007-C) **PHẢI ghi CÙNG** set + key + value. Chốt 1 schema, cả hai đường tuân + feature extractor chỉ thấy MỘT schema (không phân biệt nguồn):
- **Set/bins:** chốt tên set (vd `open_interest` cho OI value; LS + taker lưu bins/set riêng nhưng CÙNG key+granularity). 
- **Granularity 5m** (theo metrics) — forward poll chuẩn hoá về mốc 5m để khớp (không ghi mốc lổn xộn).
- **Value:** Snappy `Map<Long,Float>` per symbol per metric (như funding), đơn vị thống nhất (OI = USDT notional `sum_open_interest_value`).
- ⚠️ Nếu 007-C (đang làm) đã lỡ ghi khác → **đồng bộ về schema này**; ghi rõ để CCD làm 007-C + 013 dùng chung. Đây là phần "tổ chức lại ingest" user yêu cầu.

## BƯỚC 2 — BACKFILL (chỉ sau VERIFY PASS + user OK)
- Tải metrics 2020→nay cho universe USDT-perp (ưu tiên coin trong scope train).
- Lưu Aerospike: set mới cho OI value (+ set/bins cho LS + taker). Snappy `Map<Long,Float>` per symbol per metric, **bắt chước `writeFundingMap`** (guard chống mất lịch sử). Ghi 226 (train) + 242 (live) — chốt với read-client H1.
- Dedup theo key 5m; skip+log gap.
- **Validate:** recompute-compare vài mốc; cross-check OI quanh cú sập (OI tụt mạnh khi sập?); coverage per-coin khớp firstSeen (BƯỚC 1).

## An toàn
- Đọc `data.binance.vision` (cơ chế như 004/005). Chỉ THÊM set OI/LS/taker, đọc-only. KHÔNG đụng ticker/funding/live/config. SLF4J. Throttle tải (nhiều file).

## Acceptance
- [x] BƯỚC 1: báo cáo 4 điểm verify (xem (Code điền); coverage.csv 896 symbol). **GATE — chờ user OK.**
- [ ] BƯỚC 2 (sau OK): set OI/LS/taker 2020→nay, dedup, validate recompute + cross-check sập + coverage per-coin.
- [x] Đơn vị khớp forward (007-C) — diff 0.000%, KHÔNG bậc thang train/serve.

## (Code điền)

### BƯỚC 1 — VERIFY (DONE 2026-06-13, GATE — chờ user OK trước BƯỚC 2)
> Tool: `C:\Users\pc\oi-verify\verify_oi_metrics.py` (đọc-only data.binance.vision + fapi). Output: `coverage.csv` (896 dòng) + `verify.log`.

**B1 — granularity + format + tz:**
- Path: `data/futures/um/daily/metrics/<SYMBOL>/<SYMBOL>-metrics-YYYY-MM-DD.zip` (+ `.CHECKSUM`). Header đúng 8 cột như task.
- **Granularity 5m**: file gần đây (BTC 2026-06-10) = **288 dòng/ngày**, step 300s, nhãn theo CUỐI nến (00:05 → 24:00 hôm sau), 0 trùng.
- **TZ = UTC** (xác nhận ở B1-đơn-vị: đọc `create_time` thẳng dạng UTC khớp ms API diff 0%).
- ⚠️ **File CŨ bị NHÂN ĐÔI**: BTC 2020-09-01 = **576 dòng = mỗi create_time lặp 2 lần** (288 trùng), boundary khác (00:00→23:55). ⇒ **BẮT BUỘC dedup theo create_time** + chuẩn hoá mốc 5m khi backfill.

**B1 — coverage per-coin (file `coverage.csv`, 896 symbol; 0 symbol thiếu data):**
- 896 symbol có metrics: **774 USDT**, 39 USDC, ~83 khác (BUSD…). Nhiều hơn ~554 ticker sống ⇒ gồm coin DELIST (giá trị survivorship!).
- **firstSeen theo năm (USDT):** 2020:1(chỉ BTC), 2021:137, 2022:26, 2023:99, 2024:131, 2025:242, 2026:138.
- **PHÁT HIỆN CHỐT — nền metrics bắt đầu ~2021-12-01, KHÔNG phải 2020:** coin list TRƯỚC 2021-12 chỉ có metrics TỪ 2021-12-01 (ETH list 2019→metrics 2021-12-01; LUNA/BTCST tương tự). Coin list 2022+ thì metrics = đúng ngày list. ⇒ cụm "2021:137" thực chất là đống dồn về mốc sàn 2021-12-01. **Chỉ BTC có 2020-09.** Tiêu đề "2020+" chỉ đúng cho BTC.
- Cross-check firstSeen-metrics vs firstSeen-ticker(klines) — mẫu:

  | symbol | ticker_first | metrics_first | metrics_last | mDays | gap | nhận xét |
  |---|---|---|---|---|---|---|
  | APTUSDT | 2022-10-19 | 2022-10-19 | 2026-06-12 | 1333 | 0 | khớp ngày list |
  | SUIUSDT | 2023-05-03 | 2023-05-03 | 2026-06-12 | 1136 | 1 | khớp ngày list |
  | ARBUSDT | 2023-03-23 | 2023-03-23 | 2026-06-12 | 1178 | 0 | khớp |
  | WIFUSDT | 2024-01-18 | 2024-01-18 | 2026-06-12 | 877 | 0 | khớp |
  | 1000BONKUSDT | 2023-11-22 | 2023-11-22 | 2026-06-12 | 934 | 0 | khớp |
  | ETHUSDT | 2019-12-31 | **2021-12-01** | 2026-06-12 | 1655 | 0 | metrics MUỘN hơn list (floor sàn) |
  | LUNAUSDT | 2021-01-28 | **2021-12-01** | 2024-06-20 | 195 | 738 | delist, data THƯA |
  | BTCSTUSDT | 2021-03-04 | **2021-12-01** | 2024-07-15 | 85 | 873 | delist, gần như không có data |
- **Gap:** 101/774 USDT có gap>0. Gap lớn dồn vào coin CŨ/DELIST data thưa (BTCST 873, CVC 863, LUNA 738…). Coin sống gần đây gap 0–1.
- **Delist:** 94 USDT lastSeen < 2026-05 (ngừng cập nhật ⇒ nghi delist) — chính là tập survivorship cần cho train.
- **Khối lượng BƯỚC 2:** tổng ~**545,779 file-ngày** (mọi symbol). LS+taker NẰM CHUNG file metrics ⇒ 1 lần tải đủ 4 metric. ~12KB/file ⇒ ~6.5GB zip; cần throttle + resume.

**B1 — đơn vị metrics vs openInterestHist (007-C):** ✅ **diff = 0.000% tại offset=same** cả 6 mốc (BTC 2026-06-10). `sum_open_interest_value` (metrics) **== `sumOpenInterestValue`** (API), cùng đơn vị USDT-notional, create_time = UTC đọc thẳng, KHÔNG lệch nhãn. ⇒ history (013) + forward (007-C) khớp tuyệt đối, **không bậc thang train/serve**.

### BƯỚC 1.5 — đề xuất SCHEMA CHUNG (chờ user chốt trước BƯỚC 2)
Granularity 5m UTC; mỗi metric 1 set, Snappy `Map<Long,Float>` per symbol (như funding), key = symbol UPPER, dedup theo ts. 007-C forward đã dùng `open_interest`/bin `oi_data` cho OI value ⇒ history ghi CÙNG set đó. Đề xuất 4 set còn lại:
| metric (cột CSV) | set đề xuất | ý nghĩa |
|---|---|---|
| sum_open_interest_value | `open_interest` (đã có ở 007-C) | OI notional USDT |
| count_toptrader_long_short_ratio | `oi_ls_toptrader_acc` | L/S top-trader theo tài khoản |
| sum_toptrader_long_short_ratio | `oi_ls_toptrader_pos` | L/S top-trader theo vị thế |
| count_long_short_ratio | `oi_ls_global_acc` | L/S toàn cầu theo tài khoản |
| sum_taker_long_short_vol_ratio | `oi_taker_vol` | taker buy/sell vol ratio |
⚠️ 007-C forward hiện CHỈ ghi OI value (chưa LS/taker). Nếu chốt schema này → 007-C cần mở rộng forward ghi đủ 4 metric kia (cùng set/key) để history+forward đồng bộ.

**B2 backfill (set, #record, range, validate):** _(CHƯA làm — chờ user OK GATE + chốt schema 1.5)_
