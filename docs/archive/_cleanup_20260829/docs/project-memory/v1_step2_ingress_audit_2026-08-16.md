# Step 2 — Rà ingress (đủ dữ liệu) 2026-08-16

Box 242 (103.157.218.242:2222, root), `/home/chuyennd/java/collectData` = `BinanceDataIngestor`, ghi Aerospike ns=`ticker` port 3222.

## Đang thu gì (live, chạy từ 05/04/2026)
- **1m klines**: 687 symbol, `TickerIngestor2AerospikeNew` V8.1, chốt nến mỗi phút. Có monitor lệch giá (2/687 >0.2%). ✅
- **OI / long-short / taker-buy**: `OpenInterestIngestor2AerospikeNew` — nguồn 5 OI feature (oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy). Ghi theo month-chunk. ✅ (có bug, xem dưới)
- **15m roll**: `Kline15m4hForwardRoller` (BTC/ETH + forward roll). Funding: config có (`NUMBER_HOUR_FUNDING_CAL=30`, FUNDING_MAX/MIN_TRADE).
- Aerospike 242 ns=ticker + mirror 226.

## VẤN ĐỀ 1 — OI Infinity (bounded, cần fix, severity thấp)
- **16,227 lỗi ghi** vs 2,914 OK (log 4 tháng), nhưng chỉ **~3 symbol** (NFPUSDT, AERGOUSDT, +1) — coin thanh khoản thấp, short=0 → long/short ratio = **Infinity** → Aerospike từ chối `Infinity is not a valid double` → `writeMonthChunk` fail, retry mỗi cycle.
- Sets fail: `oi_ls_toptrader_acc/pos`, `oi_ls_global_acc`; tháng 202607/08.
- Hệ quả: 3 coin đó thiếu OI feature (stale). 3/687 → nhỏ, nhưng là data-integrity bug thật.
- **Fix**: guard Infinity/NaN trong `OpenInterestIngestor2AerospikeNew` trước khi ghi (clamp về cap hợp lý, hoặc skip sạch + log 1 lần thay vì spam retry). Đồng thời divergence backtest↔live: backtest OI từ `oi_percoin_full.bin` (sạch, offline), live có bug 3-symbol này.

## VẤN ĐỀ 2 — KHÔNG có tính Tool1 feature live (gap lớn nhất cho v1)
- collectData là **pure ingest** (klines + OI thô) — KHÔNG tính 40 Tool1 feature. Log không có Tool1/feature/convertFeatures.
- Selector WFO mới cần **45 feature (40 Tool1 + 5 OI)** tính realtime. Hiện live trader (v_t_m) đọc model CŨ `ai_models_reg_v3` (input khác), nên chưa cần Tool1.
- → v1 cần **service tính feature live**: từ klines Aerospike → 40 Tool1 feature + join 5 OI → feed selector. Đây là hạng mục ingress lớn nhất của v1 (khớp với "pipeline inference liên tục" đã note ở roadmap Gate 1).

## Kết luận step 2
Hạ tầng ingest raw (klines+OI+funding) **đã chạy tốt cho 684/687 symbol**. Hai việc cho v1:
1. **Fix OI Infinity guard** (nhỏ, làm ngay được) — chống gap 3 symbol + hết spam 16k error.
2. **Dựng live feature-computation** (40 Tool1 + join OI) — hạng mục lớn, là cầu nối để selector WFO chạy live. Đây thực chất là phần "sửa code live" (step 3) giao với ingress.

Chưa đối chiếu chi tiết giá klines live vs backtest (để step 4). Chưa kiểm coverage OI lịch sử đầy đủ mọi symbol (chỉ thấy 3 symbol fail gần đây).
