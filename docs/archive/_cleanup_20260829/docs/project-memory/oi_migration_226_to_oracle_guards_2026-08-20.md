# OI migration 226→Oracle + stale-guards (2026-08-20)

Lý do: 226 (103.157.218.226) báo trả (khẩn). Compute oi_feat live đọc full OI history từ 226 → phải chuyển nguồn trước khi 226 tắt. Quyết định của user: **Oracle NGAY + stale-guard**.

## Kiến trúc OI compute (xác nhận từ code)
- Thread `ComputeOiFeat2Live242.runOnce` chạy TRONG ingestor `OpenInterestIngestor2AerospikeNew` (proc `BinanceDataIngestor`, dir `/home/chuyennd/java/collectData`), chu kỳ 60' (env OI_FEAT_INTERVAL_MS), delay đầu 300s, rolling write 2d (OI_FEAT_ROLL_DAYS).
- Mỗi cycle/coin: `mergedMetric` = full history đọc từ 226/Oracle (`getMetricMap226` → `getClientOracle`) ∪ 242-recent (`getMetricMap242`). Tính 5 feature (delta24h, z expanding, lsg, lst, takerBuy) → `writeMetricMap242` vào 242 (`OiFeatLiveSets`).
- Model trade `LiveOiFeatProvider.lookup` (trong `DetectEntrySignal2TradeNormal`, proc `BinanceOrderTradingManager`, dir `/home/chuyennd/java/v_t_m`) CHỈ đọc oi_feat từ 242, merge_asof backward tol `MERGE_TOL_MS`=2h. 226/Oracle KHÔNG nằm trên đường trade per-tick — chỉ là nguồn baseline nền mỗi giờ.

## Bước 2 — copy 226→Oracle (DONE, verified)
- Stream server-to-server: `asbackup -o - | ssh -C | asrestore -i -` (226→Oracle qua /tmp/o.key), không đi qua WSL, không landing disk.
- 7 set OI: open_interest 18501, oi_taker_vol 17811, oi_ls_global_acc 18332, oi_ls_toptrader_acc 17105, oi_ls_toptrader_pos 17124, oi_backfill_queue 832, oi_backfill_done 895. **Tổng 90600 records, restore 90600 inserted 0 failed, per-set khớp 100%.** → 226 trả được an toàn.
- Oracle asd = dockerized (container `aerospike-wfo`, port 3222, ns `test`+`ticker`). ns=test 34.29M objects (WFO intact). ticker.dat 15G pre-alloc.

## Bước 3 — repoint + guards (DONE, deployed, verified)
Repoint config (backup `.bak_oraclehost_20260820`):
- `collectData/config.properties` + `v_t_m/config.properties`: `AEROSPIKE_HOST_226=103.157.218.226` → `161.118.212.3` (port 3222 giữ nguyên, khớp Oracle).

Code (build clean từ HEAD, jar 99617533 bytes, deploy 2 target, backup `.bak_guard_20260820`):
- **Guard-1** `ComputeOiFeat2Live242.runOnce`: đầu run probe OI full-history BTC/ETH từ Oracle; rỗng/throw → LOG.error ABORT run, KHÔNG ghi (giữ oi_feat cũ, tránh baseline cụt ghi đè sai). Steady-state = no-op (Oracle khỏe, data == 226 bit-khớp). Chỉ log khi FAIL → success im lặng.
- **Guard-2** `LiveOiFeatProvider.pipelineFreshTs()` + `DetectEntrySignal2TradeNormal`: đo tuổi oi_feat (lastKey OI_Z của BTC/ETH trên 242); nếu freshTs>0 và (time-freshTs) > OI_STALE_HALT_MS (default 2h) → LOG.warn + GATE toàn bộ entry tick đó (return rỗng). Chỉ trigger khi TỪNG có data (tránh deadlock cold-start). Tắt qua env OI_STALE_HALT=0.

Verify:
- Dry-run: đọc Oracle full history OK (PENDLE fullPts=321878, PNUT 186248…), feature hợp lý, 0 exception.
- Ingestor restart pid 13245; run thật 19:03:13 (dry=false) → Guard-1 pass (0 log), "100 coin xu ly (100 push)" 19:07:27, 0 per-coin error.
- Bot restart pid 14343; 0 exception, 0 NoSuchField, env giữ (SHADOW_NO_PUSH=true, SELECTOR_RANK_TOPK=5, SIM_MIN_MOMENTUM_15M=0.008, SIM_RATE_PROFIT_STOP_MARKET=0.05); Guard-2 không gate nhầm (oi_feat tươi).

## Rủi ro còn lại / follow-up
- Oracle là box TEST, single-node, dockerized, gánh WFO nặng → SPOF cho live compute (dù shadow). Guard-1/2 chỉ giảm nhẹ (không corrupt + gate khi stale), KHÔNG loại bỏ. **Refactor C (đề xuất trung hạn):** đóng băng baseline lịch sử thành snapshot cục bộ trên 242, mỗi cycle chỉ merge đuôi 242 → cắt hẳn phụ thuộc box ngoài cho live.
- 242 RAM ~0 free (7G total) → KHÔNG đưa 11GB raw lên 242 (đã loại phương án B).
- Log console ingestor còn "?" (encoding log4j của box) — cosmetic, khác lỗi font Telegram (đã fix Utils URLEncoder UTF-8 trong bot).
- CHỜ user xác nhận 226 đã tắt vật lý trước khi coi migration đóng hoàn toàn. Key tạm /tmp/o.key trên 226 — 226 trả thì mất theo, không cần xoá.
- Guard-2 halt-all-entries khi stale là fail-safe mạnh; nếu muốn mềm hơn (chỉ gate coin NaN thay vì cả tick) cần kiểm tra parity train (model có được train với NaN-OI imputed không) trước khi đổi.
