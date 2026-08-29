# REPORT — Trailing WFO (baseline) vs oi_z-veto × trailing (2026-07-27)

> Single-window WFO (VerifyOneWindow, jobstore-free) trên path 1m thật. DCA off, funding on, exit=trailing (default engine).
> Mục đích: kiểm tra giả thuyết sống duy nhất sau khi hard-SL/short/endpoint đều chết — trailing có monetize maxFav-spike không.
> Chạy qua `ce bg_run` detached (né cap 180s). Verdict PnL thuộc Uni; report chỉ ghi số.

## 1. Trailing baseline — dataset `wfo_ds_ret2wf_4h_ff` (selector, DCA off, funding on)

| window | oosPnl | wfe | oosTrades | note |
|---|---|---|---|---|
| 8 (2024Q1) | **+797.32** | 1.357 | 169 | SUCCESS, oosMaxDD ddPct 2.28% |
| 10 (2024Q3) | **+411.53** | 0.293 | 240 | SUCCESS, ddPct 3.69% |
| 12 (2025Q1) | — | — | — | FAIL: wrapper hard-timeout 1800s (TICKER_SOURCE=aerospike chậm; lỗi hạ tầng, không phải chiến lược) |

**Đây là exit ĐẦU TIÊN cho OOS dương** trên path 1m thật — tương phản gắt với hard-SL first-touch (âm hết, `track-a-lite`) và endpoint (~0, `reprobe`). Frequency sống (169/240 lệnh), DD thấp (2–4%).

**Chưa phải verdict:** chỉ 2 window; w10 wfe 0.29 (OOS≪IS, mùi overfit); HPO reject 18–23/30 (config chưa sạch); w12 mất do timeout. Cần WFO full slice sạch.

## 2. oi_z-veto × trailing — dataset `wfo_ds_oiz75` (veto chồng lên pipeline)

| window | oosPnl | oosTrades | note |
|---|---|---|---|
| 8 | 0 | 0 | ZERO_TRADES |
| 10 | +77.8 | 29 | TOO_FEW_TRADES |
| 12 | +1729 | 84 | TOO_MUCH_CAPITAL_LOCK (bị phạt oosFit −100003; không phải win sạch) |

Cả 3 reject 30/30 IS → HPO suy biến; frequency sụp. **oi_z-veto CHỒNG lên pipeline có sẵn = frequency wall** (trái ngược screen Kaggle `oiz-gate-probe` nơi veto GIỮ 2971 event vì nó THAY selection, không có gate thị trường chồng lên). → oi_z chỉ đáng test dạng **THAY gate MOM15**, không phải chồng thêm veto.

## 3. Kết luận đo được + next
- **Trailing = hướng thắng** (2/2 window dương). Hard-SL/short/endpoint/oiz-chồng: loại.
- Next: **WFO trailing FULL slice sạch 2023+**, `TICKER_SOURCE=file` (dataset có market.bin → nhanh, né timeout 1800s đã giết w12), DCA off, funding on; tính %OOS-dương / WFE median / worst maxDD vs ngưỡng pre-register (WFE med≥0.5, %OOS≥70%, maxDD≤50%).
- oi_z: chỉ test lại dạng gate-REPLACEMENT (bỏ MIN_MOMENTUM_15M), việc riêng.
- Task 156 (coverage 2022) nên vá để window 2021–2022 công bằng.

## 4. SỪA QUAN TRỌNG (2026-07-27) — ticker 1m CÓ trên Kaggle
Claim trước đó ("path/ticker không có trên Kaggle → trailing bắt buộc Oracle") = **SAI**. `chuyendinh/hpo-ticker-daily` = ticker **1-phút intraday** shard theo ngày (1826 file `ticker_YYYYMMDD.bin`, ~662 symbol × 1440 phút/ngày). Java engine đọc nó (TICKER_SOURCE=file) → **trailing WFO chạy được trên Kaggle fleet 5 kernel song song** (thiết kế fanout, xem `KAGGLE_FANOUT_PHASE1.md` / `NEXT_SESSION_TODO_20260714.md`). Bộ ba Kaggle đủ: `java-run-lc` + `wfo-ds-ret2-4h-ff` + `hpo-ticker-daily`. → không bó buộc 1 box Oracle; cách scalable = `ce wfo_fanout` (2 Oracle + 5 Kaggle). Lưu ý provenance: hpo-ticker-daily bản cũ 07-04 stale (trước ghost-clean); v6 07-13 là bản regen — xác nhận trước khi tin verdict.

=== RESULT ===
STATUS: REVIEW — trailing baseline 2/2 window OOS dương (+797/+411); oiz-veto-chồng dính frequency wall.
NEXT: WFO trailing full clean-slice 2023+ (TICKER_SOURCE=file, DCA off) → verdict %OOS/WFE/maxDD.
=== END ===
