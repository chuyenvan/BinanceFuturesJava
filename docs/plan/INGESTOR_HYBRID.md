# INGESTOR_HYBRID — ingest lai WS chính + REST bổ trợ cho collectData 242 (giai đoạn 1: điều tra + thiết kế, CHƯA code)

Ngày: 2026-10-30 · Tác giả: agent ING (Opus) theo MASTER · Phạm vi: process `collectData` (`websocket/BinanceDataIngestor`) trên 242.
Prereg nghiệm thu: `docs/prereg/PREREG_INGEST_HYBRID.md` (viết TRƯỚC code). Không thay đổi gì trên 242 trong giai đoạn này.

## 0. Tóm tắt rủi ro (đọc trước)
1. **Watchdog lệch giá tự restart JVM đúng lúc thị trường sập** (`BinanceDataIngestor.java:39-42`, ngưỡng cứng 50 symbol lệch >0,2 %).
   Mỗi restart = burst ~1 500 weight klines trên **IP dùng chung với LEGACY tiền thật** ⇒ 10-30 03:47:59 IP 242 bị **-1003 ban tới 03:48:17**
   (đúng đáy đợt sập). Trong 18 s đó mọi REST của IP (kể cả LEGACY ký) bị chặn và `price_realtime` (LEGACY dùng làm mark price) đứng.
2. **Ingestor (không phải LEGACY) là người tiêu ~70–95 % weight IP 242**: pass settle REST gọi `klines` cho **mọi 752 symbol mỗi phút**
   dù WS đã có 752 nến final — 10-30 cả ngày `rewritten_diff=0` (REST không sửa một ô nào) ⇒ ~750 weight/phút thuần kiểm tra.
3. Ingestor giữ API key giao dịch và gọi `changeInitialLeverage` (ký, tài khoản chính) cho mọi symbol mới (`TickerIngestor2AerospikeNew.java:583-589`) — tác dụng phụ lên tài khoản thật từ process thu dữ liệu.
4. Không có số đo weight thật (không log `X-MBX-USED-WEIGHT-1M`) ⇒ ngân sách hiện là ước lượng; bản mới phải tự đếm + đọc header.

## 1. Nguyên nhân 15 restart ngày 10-30 (bằng chứng)
- Đường code: `ThreadAutoRestartProgram` mỗi 60 s gọi `DataManagerAerospikeFloatSim.checkAndComparePriceDiff()` (`DataManagerAerospikeFloatSim.java:1788-1856`):
  REST `GET /fapi/v1/ticker/24hr` (không symbol, **weight 40**) lấy `lastPrice`, quét set `price_realtime` (giá do `Rest-Price-Loop` ghi mỗi ~3 s từ
  `ticker/price`), đếm symbol `|Δ| > 0,2 %`; **> 50 ⇒ `Utils.reset` (re-exec JVM)**. Không đếm lỗi REST/Aerospike/parse/429 — chỉ đếm độ lệch giá.
- Đây là **bộ đo biến động, không phải bộ đo lỗi**: hai giá chụp cách nhau 3–6 s; phút sập nhiều alt đi >0,2 % trong vài giây.
  Chuỗi đếm 10-30: 03:38 16 · 03:39 17 · 03:41 28 · **03:42 116** · 03:45 27 · 03:46 33 · **03:47 410/751** · **03:48 51** · 03:49 2.
  Ngày thường 2–10/751. `Rest-Price-Loop` 10-30 **0 lỗi** (chỉ 2 WARN cả ngày, đều là ban 03:47:59) ⇒ dữ liệu giá không hỏng.
- 15 lần 10-30: 00:41(67) 03:02(106) 03:08(101) 03:42(116) 03:47(410) 03:48(51) 04:15(78) 07:22(84) 07:24(79) 07:26(57) 07:30(148)
  07:31(62) 08:59(71) 20:40(53) — khớp 2 đợt sập (03:30–04:00, 06:00–09:10). Không phải lỗi mới: 10-15 (5), 10-18 (2), 10-22, 10-24 (3, có 353),
  10-26, 10-27, 10-29 (2). 10-28/29 "chỉ 2 lần" là restart lịch 12h (`counterMinutes > 720`).
- **XUSDT/MAPPER-DUP là HỆ QUẢ, không phải nguyên nhân**: dòng `[MAPPER-DUP] {1=[BTCUSDT, XUSDT]}` xuất hiện ~5–6′ sau mỗi restart, khi
  `OI-Feat-Compute-Loop` khởi tạo lại `SimpleSymbolMapper`. Gốc bản ghi XUSDT vẫn mở (parity_v11_window).
- Hậu quả dữ liệu: **kline 1m không hở, không sai**. (a) Bộ đếm ingest 10-30: `failed=0 rewritten_diff=0 filled_missing=0 early_failed=0`,
  `same=2 080 032`. (b) Đối soát độc lập từ Oracle (`~/claude_master/ing1030/kchk.json`): 7 cửa sổ quanh mọi restart (74 phút), mọi phút
  record đủ **752 symbol**, 30 symbol × phút = **2 220 ô O/H/L/C/QV so REST final: 0 lệch, 0 thiếu** (210 call weight 1, tuần tự).
  (c) Cron `kline_rest_check_242` 22/22 giờ OK. Hở thật: `price_realtime` + funding poll dừng ~1–2 s mỗi restart và **~20 s lúc ban**;
  OI forward sweep + OI-feat compute (812 s) chạy lại từ đầu mỗi restart (07:22–07:31 restart 5 lần/9′ ⇒ oi_feat không tính được ~40′; chưa chạm OI-GUARD 120′).
- Phụ: sau restart, `Kline-Finalizer` ghi phút trước bằng REST sớm cho cả 752 symbol (`rest_som=752`) + pass settle startup limit=30 ⇒ ~1 500 call/phút; đó là burst gây -1003.

## 2. Quota thật (ước lượng code × log; chưa có header)
| Nguồn (collectData) | Tần suất | Weight/phút |
|---|---|---|
| REST settle `klines limit=3` mọi symbol (`KLINE_SETTLE_SEC=30`) | 752/phút | ~752 (10-30: `fetched` 958 800/ngày) |
| REST sớm cho symbol thiếu WS lúc +4 s | 132 958/ngày | ~92 TB, burst tới 752 |
| `ticker/price` all (Rest-Price-Loop, 3 s) | ~18–20/phút × 2 | ~40 |
| `ticker/24hr` all (watchdog lệch giá) | 1/phút × 40 | 40 |
| `premiumIndex` all (funding, 30 s) | 2/phút × 10 | ~20 |
| `/futures/data/*` OI/LS/taker (5 endpoint × 752, throttle 250 ms, mỗi 30′) | ~3 760 req/30′ | hạn mức riêng 1 000 req/5′ (tính weight IP chưa xác minh) |
| Restart | 15 lần × ~1 500 | burst |
| **Tổng collectData** | | **~950/phút nền, đỉnh >2 400 khi restart** |
- v_t_m (LEGACY + shadow) chỉ log REST ký: 10-30 14h `positionRisk` 60/h + `account` 3/h ⇒ **~5 weight/phút**; grep code `trading/` không thấy REST công khai trong vòng lặp.
- ⇒ Con số "LEGACY ~1 300/phút" (canary_1027) thực chất **phần lớn là collectData** (burst giây :30 = pass settle). Bỏ settle-mọi-symbol là đòn bẩy lớn nhất cho trần ≤600 của c3.

## 3. Vì sao ingestor WS v1 bị bỏ (git + audit)
- `TickerIngestor2Aerospike` (v1) chết **2026-04-24 13:02** (phút cuối chỉ 332/590 symbol), không ai phát hiện tới 04-25; commit `2cbf27c9`
  (04-25 "fix bug limit ws of binance at production") chuyển sang REST V8/V8.1 (`docs/audit/KLINE_242_DIVERGENCE.md` D3).
- Lỗi cụ thể của v1 (đọc `git show 2cbf27c:.../TickerIngestor2Aerospike.java`, c7cb961, KFIX_242_EVIDENCE):
  1. Endpoint: futures đã tách đường; `wss://fstream.binance.com/stream` & `/ws` **kết nối OK nhưng 0 message** (đo 10-10); chỉ `/market/stream` có kline. Đường cũ im lặng không báo lỗi.
  2. Không watchdog im lặng/không kiểm staleness từng symbol ⇒ kết nối chết dần không ai biết (SDK `autoReconnect` chỉ khi có lỗi).
  3. `handleNewSymbolsDynamic` nhồi symbol mới vào kết nối cuối ⇒ vượt trần stream/kết nối (giả thuyết của commit "limit ws"); `id` subscribe = `currentTimeMillis` bị sửa thành `% 1e6` cùng commit.
  4. Ghi cả phút mỗi 50 ms + 750 put `price_realtime` mỗi 50 ms (~10k put/s) — áp lực Aerospike/backpressure; `timeBuffer` chỉ xoá `lastMin` ⇒ phút sót không bao giờ xoá (rò RAM).
  5. Chốt nến theo giây 15 (không kiểm `x=true`, không lấp phút thiếu bằng REST).
  6. Không xử lý mốc 24h: vá bằng `System.exit` mỗi 4h (c7cb961) ⇒ mỗi restart là một lỗ.
- KFIX 10-10 đã dựng lại WS đúng cách cho kline (`KlineWsClient` `/market/stream`, 150 stream/kết nối, watchdog 75 s, `x=true`, `KlineIngestCore` có test):
  10-30 `ws_final` 952 784, `ws_reconnects=6` (= 6 kết nối đầu, 0 reconnect thật). WS kline **đang chạy tốt**; phần còn REST là settle/giá/funding/OI.
- Thiếu sót còn lại của WS hiện tại: không xoay chủ động trước 24h (dựa restart 12h); symbol mới ⇒ mở thêm 1 kết nối/lần (log 10-29 17:06–17:30 6 lần), không gom.

## 4. Bản đồ dữ liệu
| Dữ liệu | Ghi vào (ns `ticker` 242) | Người đọc | Độ trễ cần | WS có sẵn | REST bắt buộc |
|---|---|---|---|---|---|
| Nến 1m O/H/L/C/QV | set `kline_1m_opt`, key `yyyyMMdd-HHmm`, proto snappy merge theo symbol | v_t_m `LiveTickerWindow` (LEGACY, shadow v1.1, v1.2 c3), parity pull242, feature pipeline | chốt trước +6 s (live đọc +6,0 s); p99 ≤ 4,5 s | `<s>@kline_1m` x=true (/market) | lấp lỗ, startup |
| Nến phút đang mở | cùng set (nặn) | live (tick hiện tại) | 3 s | `<s>@kline_1m` x=false | — |
| Giá realtime | set `price_realtime` bins `price`,`ts` | LEGACY `updatePositionMarkPrice` (tiền thật), `ShadowBookC3.tick`, `DetectEntry:1129`, Reporter | ≤ 3 s | `!miniTicker@arr` (1 s, chỉ symbol đổi) / `!ticker@arr` | fallback khi WS stale |
| Funding rate + nextFundingTime | set `funding_data` (Funding-Sync 1′) | feature funding (refresh 30′/1h) | phút | `!markPrice@arr@1s` (`r`,`T`) | `fundingRate` lịch sử khi lấp lỗ |
| OI/LS/taker 5m | set `open_interest` + `oi_feat_*` (30′) | selector S1 (oi_feat), OI-GUARD-2 (stale >120′ chặn entry) | ≤ 60′ | KHÔNG có | `/futures/data/*` per symbol |
| Nến 15m/4h BTC/ETH | `kline_15m_btceth`, `kline_4h_btceth` | gate features | ≤ 2′ | `<s>@kline_15m/4h` | lấp lỗ |
| Universe | Redis `REDIS_KEY_BINANCE_ALL_SYMBOLS`; `symbol_mapper` | mọi process | 15′ | — | `exchangeInfo` (weight 1) |
Không dùng: depth, bookTicker, forceOrder, aggTrade (owner 10-16 bác thu forward). Giới hạn Binance UM cần tuân: ≤1 024 stream/kết nối
(dùng ≤200), 10 message gửi/s/kết nối, 300 lần mở kết nối/5′/IP, server ngắt sau 24h, ping server mỗi ~3′ phải pong (OkHttp tự trả).

## 5. Thiết kế ingestor lai
**Nguyên tắc:** WS là nguồn chính cho mọi thứ có trên WS; REST chỉ (a) lấp lỗ theo symbol, (b) đối soát lấy mẫu, (c) dữ liệu không có WS (OI/LS/taker, exchangeInfo).
Giữ NGUYÊN schema/key/bin mọi set ⇒ LEGACY/strategy không đổi. Tái dùng `KlineIngestCore` (đã có test) + writer `DataManagerAerospikeFloatSim`.

5.1 **WsHub** (thay `KlineWsClient`): combined stream `wss://fstream.binance.com/market/stream`; shard theo `INGEST_WS_STREAMS_PER_CONN` (mặc định 150, trần 200);
  kết nối riêng cho `!miniTicker@arr` + `!markPrice@arr@1s` + kline 15m/4h BTC/ETH. Symbol mới/delist ⇒ gửi `SUBSCRIBE/UNSUBSCRIBE` vào shard còn chỗ
  (hàng đợi ≤5 msg/s/kết nối, id int nhỏ), chỉ mở shard mới khi đầy. Reconnect: backoff mũ + jitter 1→60 s, trần mở 20 kết nối/5′.
  **Xoay chủ động** mỗi shard ở 23h ± 20′ (lệch nhau): mở bản thay thế, chờ message đầu tiên, rồi mới đóng bản cũ (không hở).
  Staleness: kết nối kline im lặng >30 s ⇒ kill+mở lại; mảng `!miniTicker` im >10 s ⇒ fallback REST giá.
5.2 **Kline 1m**: chỉ ghi nến đóng khi `x=true` (khớp settle backtest/Vision; probe 10-10 232/232 = 100 %). Flush +1,5 s; symbol thiếu final lúc +4 s ⇒
  REST sớm CHỈ cho symbol đó (limit 2) và **đánh dấu tạm**; kiểm lại 1 lần ở +35 s (limit 2) cho đúng các symbol đó. **Bỏ pass settle mọi symbol.**
  Đối soát lấy mẫu: 25 symbol/phút xoay vòng (phủ 752 symbol mỗi ~30′), REST limit 3 ⇒ 25 weight/phút; lệch ⇒ ghi đè + đếm `recon_diff` + cảnh báo.
  Đối soát ngày từ Vision chạy trên Oracle (không tốn weight 242).
5.3 **Giá realtime**: `!miniTicker@arr` `c` (last price — cùng nghĩa `ticker/price`) ghi `price_realtime` theo lô mỗi 1 s chỉ symbol đổi (bin `price`,`ts` như cũ).
  Fallback `ticker/price` (weight 2) mỗi 3 s chỉ khi WS stale. **Bỏ watchdog lệch giá + bỏ `ticker/24hr`**; thay bằng chỉ số `price_age_p99`.
5.4 **Funding**: `!markPrice@arr@1s` `r`,`T`; logic phát hiện settlement theo `T` nhảy giữ nguyên + **lưu `lastSeenNextFundingTime` vào Aerospike** (sống qua restart);
  REST `premiumIndex` mỗi 15′ để đối soát (10 weight).
5.5 **OI/LS/taker**: giữ REST `/futures/data/*` (không có WS) nhưng limiter riêng ≤150 req/phút (dưới 1 000/5′), con trỏ sweep lưu bền (restart không quét lại từ đầu).
5.6 **Ngân sách REST cứng** (`RestBudget`, token bucket dùng chung mọi REST của ingestor): `INGEST_REST_WEIGHT_CAP=300`/phút, mục tiêu nền ≤ 150;
  đọc `X-MBX-USED-WEIGHT-1M` từng response: >1 600 ⇒ chỉ lane lấp-lỗ kline; >2 000 ⇒ dừng mọi REST ingestor tới phút sau; 429/418 ⇒ cooldown theo `Retry-After` (BinanceRestGuard).
  Startup: lấp lỗ ≤30′ cũng đi qua bucket (752 symbol ≈ 3 phút) — không còn burst 1 500.
5.7 **Cách ly lỗi, không restart JVM**: bỏ `Utils.reset` theo lệch giá và lịch 12h; mỗi luồng (WS shard, price, funding, OI, roller) có try/catch + tự khởi động lại luồng;
  lỗi theo symbol (HTTP 400 `-1121 Invalid symbol`, delist) ⇒ bỏ symbol khỏi tập + WARN 1 lần/giờ; universe = `exchangeInfo` PERPETUAL + TRADING (refresh 15′), giữ symbol
  SETTLING tới khi WS im. Chỉ thoát JVM khi OOM (`ExitOnOutOfMemoryError`) — systemd/watchdog lo phần còn lại.
5.8 **Bỏ khỏi ingestor**: `changeInitialLeverage` (chuyển sang process giao dịch/c3live; ingestor không cần key ký).
5.9 **Health** (mỗi phút): dòng log `[INGEST-HEALTH]` + file `run/ingest_health.json` (đọc qua ssh, health_242 */5): `ws_conn_alive/total`, `kline_cov_5s`, `kline_cov_60s`,
  `final_lat_p50/p99`, `rest_early`, `recon_diff`, `rest_weight_own_1m`, `hdr_used_weight_1m_max`, `price_age_p99/max`, `funding_age_max`, `oi_age_max`, `n_symbols`,
  `skipped_symbols`, `thread_restarts`. Cảnh báo: cov_60s<100 %, price_age_max>30 s, header>1 800, 429/418, thread_restarts tăng.
5.10 **Cờ**: `INGEST_IMPL=legacy|hybrid` (rollback không đổi jar), `INGEST_SET_SUFFIX` (shadow ghi set `*_hyb`), `INGEST_SINK=aerospike|files`, `INGEST_CHAOS=0|1` (chỉ Oracle).

**Triển khai an toàn**
- S0: code + test đơn vị (WS parse, xoay không hở, budget, lỗi symbol, funding qua restart) — fake WS server cục bộ; build Oracle qua flock.
- S1 (Oracle, IP khác, KHÔNG ghi 242): hybrid `INGEST_SINK=files` ghi proto/phút ra `~/claude_master/ing_shadow/`; comparer chỉ đọc 242 so với `kline_1m_opt`/`price_realtime`/`funding_data` + REST/Vision. ≥14 ngày (prereg).
- S2 (242, owner chạy 1 script): process thứ hai `INGEST_SET_SUFFIX=_hyb` ghi set riêng ≥3 ngày; REST budget nền ≤150 ⇒ tổng IP không tăng đáng kể (collectData cũ vẫn chạy).
- S3 chuyển: script owner (khung :10–:44, PAUSE watchdog, backup env) đặt `INGEST_IMPL=hybrid`, restart collectData; tự kiểm 10′ (cov, price_age, header) ⇒ FAIL tự rollback.
  **Rollback 1 lệnh**: `bash ~/claude_master/deploy/rollback_ingest_hybrid.sh <TS>` (đặt lại env, restart). Không cần đổi jar (jar mới chứa cả legacy).
- Ước lượng: ~1 300 LOC prod (WsHub 450, RestBudget 150, price/funding WS 250, health 200, settle/recon 150, OI cursor 100) + ~800 LOC test; 4–6 ngày công + S1/S2 ≥17 ngày.
- Rủi ro LEGACY: chỉ ở S3 (1 restart collectData ~1 phút, settle startup lấp nến; `price_realtime` đổi nguồn ticker/price→miniTicker cùng nghĩa last price). Giảm weight IP ~800/phút là lợi cho LEGACY.
