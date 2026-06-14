---
id: 018
status: TODO
depends_on: [013]
touches_live_process: false
writes_242_data: false
resource: kaggle
checkpoint: false
max_retry: 2
report: docs/reports/018.md
require_review: true
---

# TASK-018: Export feature gate B crowdedness OI/LS-market (B6, B8) — CHỜ 013

- **status:** BLOCKED — chờ **TASK-013** (backfill OI/LS metrics) verify + backfill PASS. KHÔNG bắt đầu trước.
- **owner:** _(điền khi claim — đồng bộ `docs/AGENTS.md`)_ · **updated:** _(điền)_
- **Spec:** `docs/H1_GATE_SPEC.md` §2.2 (B6, B8) + §2.4. **AGGREGATE toàn thị trường = GATE** (KHÁC per-coin = selector ADR-0011).

## Mục tiêu
Code + export 2 nhóm feature crowdedness vĩ mô, align `t` với `gate_return.csv` (sample 15m), validate RIÊNG. Aggregate cross-coin từ OI/LS data của 013.

## Feature (H1_GATE_SPEC §2.2)
- **B6 OI-market:** `oiMarketTotal` = Σ `sum_open_interest_value` toàn universe; `oiDelta24h` = Δ% 24h; `oiPriceDiverge` = OI tăng + giá ngang (đòn bẩy tích tụ → squeeze setup).
- **B8 LS-market:** `lsGlobal` = agg `count_long_short_ratio`; `lsToptrader` = agg top-trader; `takerBuySell` = agg taker ratio. Một phía quá tải → reversal.

## Nguồn
- Set OI/LS từ **TASK-013** (Aerospike 226). Dùng SCHEMA chung 013 chốt (BƯỚC 1.5).
- ⚠️ Aggregate cross-coin phải GỒM coin backfill (KHÔNG lọc DIED — như cảnh báo TASK-015/017).

## Yêu cầu
- Tính tại mỗi `t` (15m) khớp `gate_return.csv`. Granularity OI/LS gốc ~5m → resample/align về mốc 15m, look-ahead: chỉ điểm ≤ t.
- Crowdedness (funding B7 / OI B6 / LS B8) dễ TRÙNG → giữ ít đại diện; H2 corr-check + importance tỉa.

## Validate RIÊNG mỗi feature (§2.4)
range/phân bố; NaN/Inf→0 (coin thiếu OI/LS đoạn đầu → xử như warmup, không 0 giả); recompute ~5 mốc; look-ahead (điểm ≤t); align gate_return; báo #coin tham gia aggregate/năm.

## An toàn / tài nguyên
- Đọc-only 226, ghi `outputs/`. Chạy 226 — không đồng thời job nặng khác (CLAUDE.md). SLF4J.

## Acceptance
- [ ] B6 + B8 export, align gate_return, range data 013 phủ.
- [ ] Validate riêng PASS + #coin aggregate/năm.
- [ ] Aggregate gồm coin backfill; look-ahead sạch (resample 5m→15m ≤t).

## (Code điền)
- **B6 OI-market công thức + validate:** …
- **B8 LS-market + validate:** …
- **#coin aggregate/năm + range:** …
