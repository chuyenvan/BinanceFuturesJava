# DATA CADENCE — nhịp cập nhật dữ liệu ingest (base cho thiết kế feature)

> Mục đích: bản đồ "dữ liệu nào, nguồn nào, tươi tới đâu" để KHÔNG phải đọc lại code mỗi lần.
> Dùng làm BASE khi thiết kế feature cho 2 model (gate ADR-0010 / funding selector ADR-0011).
> Cập nhật: 2026-06-15. Nguồn: đọc trực tiếp BinanceDataIngestor + các ingestor.

## Bảng tổng hợp

| Dữ liệu (set) | Nguồn & cơ chế | Toàn-sàn? | Chu kỳ hiện tại | Granularity gốc | Dùng cho feature | Chu kỳ NÊN |
|---|---|---|---|---|---|---|
| Giá realtime (`price_realtime`) | `ticker/price` REST | Có (1 call) | 3 giây | tick | Không (giá execution cho bot) | giữ 3s |
| Kline 1m (`kline_1m_opt`) | nặn nến từ giá 3s + chốt chuẩn `klines 1m` per-symbol | Không (per-symbol ~554) | mỗi phút (burst giây 2-10) | 1 phút | Nền MỌI feature giá/volume/momentum/breadth/volatility (gate + funding) | giữ 1' |
| Kline 15m/4h BTC-ETH (`kline_15m_btceth`, `kline_4h_btceth`) | gom từ kline 1m (không gọi sàn) | n/a (chỉ BTC/ETH) | kiểm mỗi phút, ghi khi khung đóng | 15m / 4h | BTC/ETH momentum khung lớn + regime (gate) | giữ (theo khung đóng) |
| Funding rate (`funding_data`) | `premiumIndex` REST | Có (1 call, weight 1) | 30 giây poll, ghi theo kỳ settle | kỳ settle (1h/4h/8h) | Funding features (gate + funding) | giữ 30s |
| Open Interest (`open_interest`) | `openInterestHist` REST | Không (per-symbol) | 5' (đang 1-record; TASK-035 đổi chunk-tháng) | 5 phút | OI level/Δ/divergence, crowdedness (funding selector) | **30'** (sau 035) |
| LS top-acc/pos, global, taker (`oi_ls_toptrader_acc`, `oi_ls_toptrader_pos`, `oi_ls_global_acc`, `oi_taker_vol`) | 4 endpoint `/futures/data/*` REST | Không (per-symbol) | CHƯA có forward (chỉ backfill batch 013) | 5 phút | Squeeze/crowdedness (funding selector) | **30'** (TASK-035) |

## Vì sao có sự chênh lệch nhịp (phân tích)

**Hai tầng, quyết định bởi API Binance — không phải lựa chọn tuỳ ý:**
- Tầng tươi/rẻ (toàn-sàn 1 call): giá (3s) + funding (30s). Lấy cả sàn một phát nên tươi.
- Tầng chậm/đắt (per-symbol): kline 1m, OI, LS, taker. Mỗi coin một REST call. 3 metric OI/LS/taker KHÔNG có WebSocket và KHÔNG có endpoint all-symbol → buộc per-symbol.

**Trong tầng per-symbol còn phân bậc ưu tiên:**
- Kline 1m là nền của mọi feature → ưu tiên chốt mỗi phút (burst ~554 call giây 2-10).
- OI/LS/taker là feature phụ, khung chậm → đẩy xuống 30' và né ra giây ~30-50 (tránh đụng kline-burst + entry/DCA chạy giây 5-10).

## NGUYÊN TẮC THIẾT KẾ FEATURE (rút ra từ nhịp này)

1. **OI/LS/taker: chỉ dùng feature khung chậm.** Granularity gốc 5m nhưng điểm mới nhất có thể trễ tới ~30' (do poll 30'). ⇒ dùng ở dạng level / ΔOI khung >=30'-1h / OI-price divergence / cross-sectional rank giữa các coin cùng mốc. TRÁNH feature kiểu "ΔOI 5m sát thời điểm entry" — dữ liệu không tươi tới mức đó, sẽ lệch train-vs-live.
2. **Funding rate tươi (30s)** → feature funding có thể nhạy hơn OI/LS/taker.
3. **Kline 1m + giá 3s tươi** → mọi feature giá/momentum/volume realtime dựa vào đây.
4. **Train phải khớp serve:** history (013) granularity 5m; forward (035) cũng 5m, poll 30'. Khi tính feature lúc train, mô phỏng đúng độ trễ serve (không dùng giá trị "tương lai gần" mà live không có kịp).
5. **Lối thoát nếu cần OI tươi cho entry:** thu hẹp phạm vi — poll dày riêng cho nhóm coin đang có lệnh/watchlist (vài chục coin, sweep nhanh), tách khỏi vòng 30' toàn bộ ~554. Chưa làm, để dành.

## Liên quan
- Cơ chế ingest OI/LS/taker forward: `tasks/035-forward-oi-chunk-month-ls-taker.md`.
- Thiết kế feature 2 model: `docs/decisions/0010-market-model-gate-design.md`, `docs/decisions/0011-funding-model-selector.md`.
- Schema chunk-tháng + backfill history: `tasks/013-backfill-oi-metrics-history.md`, `docs/reports/013.md`.
