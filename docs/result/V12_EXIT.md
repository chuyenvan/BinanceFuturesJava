# V12_EXIT — vòng 2b: thoát thật (C6), kế toán fill (C7), reconcile (C9), mock e2e + replay (C12), script owner (O2)

Branch tích hợp `v1.2/c3-live` (worktree `~/claude_master/v12/c3live`), tiếp từ `dd54a27b`. Agent v12exit (Claude Opus), 2026-10-25.
Không push, không merge sang branch khác, không deploy, không gọi Binance, không đụng 242 (script O2 chỉ chạy thử trên "242 GIẢ" ở Oracle).

## 0. Risk-first (đọc trước)

1. **CHƯA XÁC MINH với sàn thật (phải kiểm ở canary trước tiền thật):**
   (a) Binance có từ chối stop `closePosition=true` thứ 2 cùng chiều không (−4130) với **Algo API** — code đặt mới-rồi-huỷ-cũ; nếu −4130 thì
   đặt stop `qty + reduceOnly` (vẫn không có khoảng trống), lần dời sau quay lại closePosition (xen kẽ). (b) URL user-data stream
   (`wss://fstream.binance.com/private/ws/<listenKey>` rồi fallback `/ws/<listenKey>`, xoay vòng khi kết nối lỗi — cấu hình `LIVE_C3_WS_URLS`).
   (c) Định dạng `ALGO_UPDATE` và `clientOrderId` của lệnh MARKET sinh ra khi stop kích (code nhận diện stop khớp bằng: cid `c3s-`/cid stop đang đặt/
   `ot=STOP_MARKET`; nếu không khớp mẫu nào ⇒ lý do `EXTERNAL` + Telegram, sổ vẫn được cập nhật đúng vì dựa `ACCOUNT_UPDATE pa=0`).
   (d) Mã −2021 ("would immediately trigger") ⇒ bot đóng MARKET ngay (coi như stop đã chạm).
2. **Stop sàn dùng MARK_PRICE, sổ giấy dùng giá last (price_realtime)**: quyết định arm/SL logic trùng 100 % (cùng hàm, cùng float), nhưng
   thời điểm/giá khớp thật lệch (mark ≠ last; stop sàn round-down tick và chỉ dời khi ≥ 1 tick VÀ ≥ 0,1 % ⇒ stop sàn ≤ SL logic tối đa ~0,1 % + 1 tick).
   Replay DEV (nến 1m) thoát cùng phút 105/105; tổng hợp 5/6 cùng phút, 1/6 trễ 1 phút (dải 0,1 %). Nếu giá bật lại trong dải 0,1 % thì
   live giữ tiếp còn giấy đã đóng — **lệch quyết định hiếm, thiết kế chấp nhận** (MASTER/owner Q1a).
3. **Đối chiếu equity hằng giờ (Q1b) có thể báo động giả theo thời gian**: BFUSD sinh lãi/đổi haircut KHÔNG đi qua `ACCOUNT_UPDATE` có lý do rõ
   ⇒ trôi dần; giảm thiểu: tự đặt lại mốc khi sổ trống (0 cụm, 0 leg treo) + script owner `c3live_reanchor.sh`. Nạp/rút khi stream sống được tự
   ghi "chuyển tiền"; khi stream chết ⇒ lệch ⇒ NO_NEW_ENTRY tới khi khớp 2 lần hoặc owner reanchor. Tài sản ký quỹ không ổn định (BTC, BNB…)
   KHÔNG quy USD (WARN).
4. **Loại TradFi khỏi feature (cờ `LIVE_C3_EXCLUDE_TRADFI_FEATURES`) ĐỔI input model ở c3_live** (MarketDataInline ⇒ cả market level quyết định vì
   242 chạy `LIVE_MD_SOURCE=inline`; HistoryManager/CoinRank; feature funding/EntrySignalFilter; pool rank). Sổ giấy twin trong c3_live cũng
   không còn mua TradFi (không có dự đoán) ⇒ twin c3_live ≠ c3_shadow ở các leg TradFi. **Phải kiểm bằng dry-run parity** (đã có kế hoạch).
   c3_shadow/sim: cùng map (byte-identical — parity §3).
5. **Dry trên 242 (sau 11-18)**: exchangeInfo lấy 1 lần lúc deploy (`run/c3live_exchangeInfo.json`), không tự làm mới ⇒ symbol niêm yết SAU
   deploy ⇒ `NOT_LISTED` trong dry (không mua). Telegram cảnh báo c3_live (khởi động, đóng bất thường, mất stream, lệch equity) đi vào kênh thật.
6. Sổ ledger `c3live_ledger.csv`: realizedPnl của fill đến SAU khi REST đã chốt đóng cụm không vào dòng ledger (vẫn vào tổng đối chiếu equity).
7. Sửa code cũ ngoài c3live: `Utils.sendSms2Telegram`, `HttpRequest` (log), `P2PTelegramNotifier` — **chỉ nhánh log lỗi** (che token), bytecode
   đổi nhưng quyết định giao dịch không đổi; `KillSwitchEngine/OpsHooks/OpsConfig` (C4/C3 mới chỉ ở mode ACT), `TsMktExt` (bật cho c3_live),
   `LiveFeaturePipeline`/`DetectEntrySignal2TradeNormal` (lọc TradFi sau cờ — tắt ⇒ cùng object).

## 1. Quyết định MASTER 10-25 đã áp

| quyết định | làm gì | test | trạng thái |
|---|---|---|---|
| C4 = điều kiện CÔNG SUẤT | `KillSwitchEngine.Params.c4Capacity` (OpsConfig bật ở act): C4 KHÔNG latch; `allowNewEntry` (mở cụm mới) = false khi C4 đạt; `allowDca` (mới) chỉ latch chặn ⇒ DCA vẫn chạy, vẫn throttle U_MAX của sizing; tự gỡ có trễ khi vị thế ≤ 85 VÀ U ≤ U_MAX − 0,05 (+ Telegram ON/OFF); file latch cũ có C4 ⇒ bỏ C4 khi nạp. `C3LiveEntry` dùng `allowDca` cho leg DCA | `KillSwitchCapacityTest` (9), `C3LiveExitE2ETest.killSwitchC4CapacityBlocksNewClusterButAllowsDca` | ĐẠT — **lệch GOLIVE §5.2 (C4 "tự nhả") đã giải quyết** |
| C3 tự gỡ | `autoReleaseCodes += C3` (act) + điều kiện thêm `apiOkConsec ≥ c3ReleaseOkConsec (3)`; vẫn cần 30′ sạch như C1/C5 | `c3AutoReleaseNeeds30minCleanAnd3ConsecutiveOk`, `c3ErrorBetweenOksResetsCounter`, e2e `killSwitchC3LatchesThenAutoReleases` | ĐẠT |
| giữ latch C2/C6/A40 | không đổi | `c2c6a40StillLatchUntilOwner`, e2e C2/A40 | ĐẠT |
| TradFi khỏi feature | `C3LiveHook.excludeTradFiFeatures()` = hook bật && `LIVE_C3_EXCLUDE_TRADFI_FEATURES`≠0 (c3_live mặc định 1; ngoài c3_live luôn 0); `LiveFeaturePipeline.setSnapshotFilter` (seed + catch-up + phút quyết định) ⇒ MarketDataInline, HistoryManager/CoinRank, feature, snapshot funding/EntrySignalFilter; `predictAllCandidates`: `fSnap` lọc + bỏ TradFi khỏi aiCandidates (pool rank); đường legacy (`LIVE_FEAT_INPUT=legacy`): map feature + history lọc. Phân loại = `SymbolUniverseLive.classification` (snapshot nạp đồng bộ lần đầu) | `TradFiFeatureFilterTest` (4: cờ chỉ c3_live, lọc sao chép không sửa gốc, pipeline nuôi map lọc/không lọc ⇒ cùng object) | ĐẠT (input model đổi CHỈ ở c3_live; kiểm dry-run parity sau) |
| X14 cho c3_live | `TsMktExt.decideEnabled` bỏ điều kiện `!profileLive`; cụm THẬT gọi `TsMktExt.deferTimeStop` qua `TrailingStopManager` | `TsMktExtTest` (đổi 1 kỳ vọng + danh sách tham chiếu thêm `TrailingStopManager.java`), e2e X14 | ĐẠT |
| Rò token Telegram | `Utils.sendSms2Telegram`: bỏ `printStackTrace` ⇒ `LOG.warn` thông điệp đã che; `HttpRequest`: mọi log `url=`/`e.getMessage()` qua `redactSecrets` (che `api.telegram.org/bot<token>` và `bot<số>:<chuỗi>`); `P2PTelegramNotifier`: không in stack | `TradFiFeatureFilterTest.telegramTokenRedactedInLogs` | ĐẠT — chỉ nhánh log lỗi |

## 2. Việc × tiêu chí GOLIVE_SCENARIO §2 × test × trạng thái

| mã | tiêu chí (GOLIVE §2 / task) | làm gì | test | trạng thái |
|---|---|---|---|---|
| C6 | arm 0,07 như sổ giấy; sau arm `newStopMarket(sym, SELL, stop, cid, closePosition=true)` MARK_PRICE; stop theo công thức trailing sổ giấy (tái dùng hàm) ratchet liên tục; dời khi ≥ 1 tick VÀ ≥ 0,1 %; dời = đặt mới rồi huỷ cũ, idempotent theo clientAlgoId; time-stop 168h + X14 ⇒ `closeCluster`; stop khớp (C7/C9) ⇒ cập nhật sổ, huỷ phần còn lại; replay 3 đợt DEV trùng 100 % trừ chênh giá khớp | `c3live.exit.TrailingStopManager` (nhịp 10 s, giá price_realtime như nhịp exit sổ giấy); `tradecore.selector.C3TrailRate` = cầu public tới `ShadowBookC3.trailRate` (⇒ `calRateLossDynamicBuyPNoPump`); VWAP float y hệt sổ giấy (`ClusterView.avgEntryF`); cid stop `c3s-<tok>-<min>-<seq>` (seq persist) + pending persist TRƯỚC gửi, timeout ⇒ `queryStop` sau cửa sổ an toàn; −4130 ⇒ qty+reduceOnly; −2021 ⇒ đóng MARKET; DCA khớp ⇒ reset arm (như `ShadowBookC3.addLeg`) + huỷ stop; không có giá ⇒ vẫn đặt lại stop thiếu cho cụm đã arm | `TrailingStopManagerTest` (10); `ExitReplayParityTest` (tổng hợp 20 ngày × 8 symbol: **3 075 sự kiện quyết định, 0 lệch**, 6 arm, 188 dời SL, 2 time-stop, X14 hoãn, 6 thoát trailing: 5 cùng phút, 1 trễ 1 phút); **replay DEV thật** `ExitReplayDevMain` (bảng §2.1) | ĐẠT |
| C7 | listenKey tài khoản con + keepAlive 30′; WS `ORDER_TRADE_UPDATE` + `ACCOUNT_UPDATE`; ghi qty/avgPrice/commission/realizedPnl/orderId vào sổ + audit; `OpsHooks.onFill` (C2 có dấu); mất stream ⇒ fallback REST + WARN; reconnect backoff; test WS server giả | `c3live.fill.{UserStream, UserStreamEvents, FillAccounting}` (okhttp như `ExecProbeWsSource`; backoff 1→60 s; xoay URL khi kết nối lỗi; `listenKeyExpired`/keepAlive lỗi ⇒ listenKey mới; mất > 2 s ⇒ fallback REST (resolveUnresolved + `Reconciler.checkPositions`) mỗi 10 s + Telegram 1 lần sau 5′; kết nối lại ⇒ bù REST 1 lần); xác nhận leg chỉ 1 lần (stream hoặc REST) ⇒ `onFill` 1 lần; phí quy USD tài sản ổn định; stop khớp/thanh lý `autoclose-`/ADL/`settlement_autoclose` ⇒ `closedOnExchange` (huỷ mọi stop `c3s-` của symbol, xoá cụm, ledger, Telegram nếu bất thường); `ACCOUNT_UPDATE` FUNDING_FEE ⇒ funding, DEPOSIT/WITHDRAW/... ⇒ chuyển tiền; vị thế lạ ⇒ Reconciler | `UserStreamWsTest` (2; server WS JDK tự viết `FakeWsServer`: fill ⇒ sổ, drop + từ chối kết nối ⇒ fallback + Telegram, kết nối lại ⇒ bù 1 lần, `listenKeyExpired` ⇒ key mới, xoay URL + backoff), `FillAccountingTest` (5), e2e `userStreamLossFallbackRestUpdatesBook` | ĐẠT (URL/định dạng thật: §0.1) |
| C9 | start: positions + openStops + sổ ⇒ sàn thắng qty/giá; thiếu stop cho cụm đã arm ⇒ đặt lại; stop mồ côi ⇒ huỷ; vị thế lạ ⇒ chặn + Telegram (không tự đóng); lệch ⇒ chặn entry tới khi khớp; hằng giờ \|equity sổ − tmb\|/tmb > 1 % ⇒ Telegram + NO_NEW_ENTRY (gỡ khi khớp 2 lần liên tiếp); vị thế bị sàn đóng ⇒ cập nhật sổ + Telegram; test restart (có/không stop, leg DCA dở, stop khớp khi bot chết) khôi phục tsFirstLeg/legCount/peak/stop 100 % | `c3live.recon.Reconciler` (chụp sổ TRƯỚC khi đọc sàn ⇒ không đóng nhầm cụm vừa khớp); đọc sàn lỗi lúc khởi động ⇒ `STARTUP_RECON` chặn, runtime thử lại mỗi 30 s; stop đã kích (queryStop) ⇒ lý do TRAILING_STOP; stop `c3s-` không được sổ tham chiếu ⇒ huỷ, stop khác (của người) ⇒ chỉ báo; hằng giờ quét stop mồ côi; mốc equity: lần đầu/sổ trống/`run/c3live_reanchor.req` (owner, áp ≤ 5 s); chặn = `C3LiveEntry.reconAllows` (Outcome `RECON_BLOCKED`, chặn cả DCA) | `ReconcilerTest` (10: restart có stop ⇒ 12 trường sổ trùng bit; stop thiếu ⇒ đặt lại kể cả không có giá; pending đã lên sàn ⇒ nhận, không trùng; leg DCA dở ⇒ xác nhận từ sàn + reset arm + huỷ stop cũ; stop khớp lúc chết ⇒ đóng cụm TRAILING_STOP + ledger; sàn thắng qty + stop mồ côi/ngoại lai; vị thế lạ chặn tới khi hết; lỗi đọc lúc start chặn; lệch equity 5 % chặn → khớp 2 lần gỡ → reanchor; fallback REST) | ĐẠT |
| C12 | mock e2e: mở→DCA→arm→dời stop ×N→stop khớp; mở→time-stop; mở→X14→đóng; restart; KS C2/C3/C4/A40; mất user stream; replay dry 1 ngày live thật (số leg dry vs sổ giấy, khác chỉ do TradFi/universe) | `C3LiveExitE2ETest` (9) — thành phần THẬT: KillSwitchEngine (ACT + C4 công suất + C3 tự gỡ), C3LiveEntry, executor idempotent, LiveBookC3 persist, C3LiveFlattener, TrailingStopManager, FillAccounting (sự kiện dạng stream do mock phát), Reconciler; DryGateway: stop kích theo giá mark giả lập, sự kiện dạng stream, phí 0,05 %, persist `LIVE_C3_DRY_STATE_FILE` (`DryGatewayStopTest`); `DryDayReplayMain` (§2.2) | 9/9 xanh; replay dry §2.2 | ĐẠT (G-DRY trên 242: sau 11-18) |
| O2 | `ops/c3live/`: `deploy_v12_dry.sh` (backup, time_ok, DRY=1, YES, tự kiểm sau start, từ chối trước 2026-11-18 08:00 +07 trừ `FORCE_DATE=1`), `rollback_v12.sh`, `killsw_reset.sh` (kiểm lại), `c3live_status.sh` (chỉ đọc); test DRY trên Oracle | 4 script + `c3live_reanchor.sh` (C9) + `test/test_fake242.sh`. `killsw_reset.sh` gốc (`ops/killsw_reset.sh`, chạy TRÊN 242) kiểm lại: đúng luồng DRY/YES/req/.done, không cần sửa; thêm bản bọc chạy từ Oracle (deploy chép `ops/killsw_reset.sh` lên 242). Deploy: thêm 9 dòng env (`LIVE_PROFILE=c3_live`, `LIVE_ADAPTER=dry`, `LIVE_KILLSW_MODE=act`, `LIVE_KILLSW_C2_SIGNED=1`, file sổ/exchangeInfo/dry state, `LIVE_C3_EXCLUDE_TRADFI_FEATURES=1`), giữ `SHADOW_NO_PUSH=true`, không `LIVE_ENTRY_ENABLED`; tự kiểm: jar md5, 1 process, env /proc, `c3_live BAT` + `PUSH=OFF`, `[KILLSW] BAT mode=act`, `[C3-LIVE] khoi dong adapter=DRY` + `killSwitchArmed=true`, `[C5] … OK`, universe tradable > 100, reconcile khởi động không lỗi, `[TS-EXT] BAT`, heartbeat, **0 dòng `[C3-LIVE-ORDER]`**, 0 exception, đếm `[LIVE-DRY]` | `test_fake242.sh` trên Oracle với "242 giả" (`SSH_242="bash -c"`, `SCP_242=cp`, process giả `BinanceOrderTradingManager fake242`, `PROC_PAT` để KHÔNG chạm process thật trên Oracle): **23/23 PASS** (DRY không đổi gì; từ chối trước 11-18; deploy đủ bước + backup + env + exchangeInfo + chép killsw; deploy lần 2 tự từ chối; status; killsw DRY/YES; reanchor DRY/YES; rollback DRY/YES ⇒ env/jar/process về c3_shadow, sổ dry đổi tên `.rb_<TS>`) | ĐẠT (chưa chạy trên 242 — đúng phạm vi) |

### 2.1 Replay DEV thật (C6) — `ExitReplayDevMain`, dữ liệu `~/vz_e1/raw` (close 1m), chân = SELRANK printDone `tsx-x14-s123`, cờ X14 = `SIM_LOSER_TS_EXT_DAYS` của chính lần sim

| ngày (+07) | chân | symbol | sự kiện quyết định | lệch | arm | dời SL | time-stop | thoát trailing (cùng phút) | lệch giá thoát TB (live − giấy)/giấy | còn mở cuối |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-02-03 | 68 | 37 | 534 | **0** | 63 | 471 | 0 | 37 (37) | −0,32 % | 0 / 0 |
| 2024-08-05 | 43 | 41 | 424 | **0** | 42 | 382 | 0 | 41 (41) | −0,16 % | 0 / 0 |
| 2022-06-13 | 41 | 29 | 153 | **0** | 37 | 114 | 2 | 27 (27) | −0,39 % | 0 / 0 |

⇒ **1 111/1 111 quyết định (arm/từng mức SL bit float/time-stop) trùng sổ giấy**; 105/105 thoát trailing cùng phút; lệch duy nhất = giá khớp (stop
sàn round-down + ngưỡng dời + khớp ở close phút). X14 không hoãn lần nào ở 3 đợt (cụm hoặc arm, hoặc 168h rơi vào ngày cờ OFF) — hoãn X14 được
phủ ở replay tổng hợp CI (2 879 phút hoãn trùng). tick size = 4 chữ số có nghĩa theo giá leg đầu (fixture, CHƯA XÁC MINH với sàn).
Kết quả: `~/claude_master/v12/exit_wk/dev/exit_replay_dev.json` (chép vào `docs/result/v12exit/`).

### 2.2 Replay dry 1 ngày live thật (C12) — `DryDayReplayMain`, log 242 kéo về `~/claude_master/pull242/2026-10-2{3,4}`, cửa sổ 10-23 07:00 → 10-25 07:00 +07

| exchangeInfo | leg sổ giấy | dry SUBMITTED (`[LIVE-DRY]` FILLED) | khác |
|---|---|---|---|
| dump THẬT `fixtures/exchangeInfo_20261025_1457.json.gz` (owner, 932 symbol, 225 TRADIFI_PERPETUAL) | 25 | **22** (22) | 2 TradFi `NOT_BUYABLE` (UNITREEUSDT, IBKRUSDT — `contractType=TRADIFI_PERPETUAL`); 1 `HOLDING` IRYSUSDT = giả tạo của replay (sổ giấy đóng trailing 02:26 rồi mở lại 02:27; replay dry không mô phỏng thoát) |
| pin cũ + danh sách proxy TradFi 116 (`live_low_activity_1023.csv`) | 25 | 23 | chỉ IBKRUSDT bị loại — **danh sách proxy thiếu UNITREEUSDT** ⇒ dùng phân loại từ exchangeInfo thật |

Notional dry/giấy (486 / 3 054 USDT) KHÔNG đại diện: config sizing trên Oracle ≠ profile 242, vốn dry 10 000 vs PAPER_EQUITY 35 000, tier = 1.

## 3. Validation

- `mvn -o package -DskipTests=false` (HEAD code `28be5cbb`): **EXIT 0, 574 test, 0 fail, 0 error, 1 skip** (vòng 2a: 523/2 skip). +51 test mới:
  TrailingStopManagerTest 10, ExitReplayParityTest 1, FillAccountingTest 5, UserStreamWsTest 2, ReconcilerTest 10, KillSwitchCapacityTest 9,
  TradFiFeatureFilterTest 4, DryGatewayStopTest 1, C3LiveExitE2ETest 9. Skip giảm 2→1 vì dump exchangeInfo thật đã có ⇒
  `SymbolRulesTest.invariantsOnRealDumpIfPresent` chạy và ĐẠT (7/7). Sửa test cũ: `TsMktExtTest` (2 dòng — c3_live bật X14, tham chiếu
  `TrailingStopManager.java`), `MockExchangeGateway` (thêm kích stop/sự kiện; hành vi cũ giữ nguyên trừ listenKey có số thứ tự).
- **Bytecode** `target/classes` base `dd54a27b` (821 lớp) ↔ HEAD (852): **782 giống hệt**, 0 xoá, 31 thêm (30 `c3live.*` + `C3TrailRate`),
  **39 đổi** = đúng các file nguồn đã khai: c3live (`DryGateway`, `GatewayFactory`(+inner), `LiveBookC3`(+inner), `C3LiveEntry`(+inner),
  `C3LiveCids`, `C3LiveHook`, `C3LiveRuntime`(+$1)) và lớp cũ ngoài c3live: `LiveFeaturePipeline`(+$1), `P2PTelegramNotifier`,
  `KillSwitchEngine`(+$Action,$CodeState,$Mode,$Params,$Resolved — lệch số dòng), `OpsConfig`, `OpsHooks`, `TsMktExt`,
  `DetectEntrySignal2TradeNormal`(+$1,$TickGate), `HttpRequest`, `Utils`. Danh sách: `~/claude_master/v12/exit_parity/bytecode_diff.json`.
- **Parity offline 2026-10-22 (cờ tắt)** — `~/claude_master/v12/exit_parity/` (driver = bản sao `core_parity/drv.py`, cache chia sẻ
  `core_parity/d22_core`, jar md5 `a55be721…` = HEAD `28be5cbb`): **ĐẠT**. CTL gate 1440/1440 (only_ref 0, only_new 0,
  bad_min 0, mọi cột bit=1.0); md5 (giải nén) trùng tham chiếu `dcae2e2b`: out_BT = out_NEW2 = `2c7c336d…`, fund_BT `1a6d1521…`,
  fund_NEW2 `f4acab23…`; CTL fund 0.944253 (f3, 79 phút, 2714 ô) = y hệt base — không phải do vòng này. strace: 0 connect AF_INET
  (BT + 3 segment NEW2). Tóm tắt: `docs/result/v12exit/exit_compare.json`.
- Không gọi Binance/242; `PrivateConfig.java` chỉ chép để biên dịch (gitignored, không commit/in); jar ở Oracle.

## 4. CHƯA LÀM / để A1 + vòng sau

1. A1 (audit độc lập): bytecode diff + harness `ops/verify/harness_*.sh` theo G-CODE; xem §0.
2. Canary (G-CANARY) xác minh §0.1 (−4130 Algo API, URL private stream, ALGO_UPDATE, cid lệnh kích stop, −2021).
3. Dry-run parity trên 242 (sau 11-18, ≥ 7 ngày): leg `[LIVE-DRY]` vs sổ giấy; đo ảnh hưởng loại TradFi lên gate (input model đổi).
4. Script owner khác của GOLIVE §4.2 (S2 key, S3 canary, S4 micro_on, S5–S11) — chưa thuộc vòng này. Script vòng này nằm trong repo
   `ops/c3live/`; MASTER chép sang `~/claude_master/deploy/` kèm md5 sau A1 (deploy cần jar build lại ⇒ cập nhật `NJ_MD5`).
5. Làm mới exchangeInfo định kỳ cho dry/live (hiện dry: 1 lần lúc deploy; live: REST 6h/15′ như vòng 2a).
6. BFUSD trôi số dư trong đối chiếu equity (§0.3) — cân nhắc nới ngưỡng hoặc quy đổi theo `account().assets`.

## 5. Cấu hình mới (mặc định = tắt / hành vi cũ)

| key | mặc định | ý nghĩa |
|---|---|---|
| `LIVE_C3_EXCLUDE_TRADFI_FEATURES` | 1 (CHỈ khi c3_live + adapter; ngoài c3_live luôn 0) | loại TradFi khỏi feature cắt ngang/thị trường |
| `LIVE_C3_STOP_MODE` | `close_position` | `reduce_only_qty` = luôn stop qty + reduceOnly |
| `LIVE_C3_WS_URLS` | `wss://fstream.binance.com/private/ws/{key},wss://fstream.binance.com/ws/{key}` | URL user stream (xoay khi lỗi) |
| `LIVE_C3_WS_PING_MS` | 60000 | ping okhttp |
| `LIVE_C3_EQUITY_TOL` | 0.01 | ngưỡng lệch equity hằng giờ |
| `LIVE_C3_REANCHOR_FILE` | `run/c3live_reanchor.req` | yêu cầu đặt lại mốc (script owner) |
| `LIVE_C3_DRY_STATE_FILE` | (trống = chỉ RAM) | persist vị thế/stop dry (deploy đặt `run/c3live_dry_state.json`) |
| `LIVE_C3_DRY_FEE_RATE` | 0.0005 | phí dry |
| KS act (OpsConfig) | `c4Capacity=true`, `autoReleaseCodes += C3`, `c3ReleaseOkConsec=3`, `c4ReleasePos=85`, `c4ReleaseUGap=0.05` | quyết định MASTER 10-25 |

## 6. API công khai mới (cho A1 / vòng sau)

```java
// c3live.exit
public final class TrailingStopManager { static Builder builder(); int step(Map<String, Float> prices); String stats();
  static void startTsExtIfEnabled(); static boolean tsExtEnabled(); static void tsExtOnClosed(String, long, String, long);
  enum StopMode { CLOSE_POSITION, REDUCE_ONLY_QTY }; interface TrailFn/TimeStopDefer/ArmHook/Closer/EventSink;
  static final String REASON_TIME_STOP = "TIME_STOP_168H", REASON_TRAIL_IMMEDIATE = "TRAILING_IMMEDIATE"; }
// tradecore.selector
public final class C3TrailRate { static float trailRate(float peakRate, Float symbolPred, String symbol); static float armRate(); static int timeStopHours(); }
// c3live.fill
public final class UserStream { UserStream(ExchangeGateway, Connector, List<String> urlTemplates, FillAccounting, Runnable fallback,
  Consumer<String> alert, ApiObserver, LongSupplier clock, long connectTimeoutMs, long fallbackEveryMs, long maxBackoffMs, long alertDownMs);
  void start(); void stop(); void tick(long now); boolean isConnected(); long catchUpCount(); static Connector okHttp(long pingMs);
  static List<String> parseUrls(String); interface Connector/Socket/Listener }
public final class FillAccounting { FillAccounting(LiveBookC3, ExchangeGateway, OrderAuditLog, FillObserver, Consumer<String> alert,
  ApiObserver, LongSupplier, ClosedHook); void dispatch(UserStreamEvents.Event); void closedOnExchange(String sym, String reason, long now);
  void setUnknownPositionSink(Consumer<String>); static String exitReason(String cid, String origType, String activeStopCid); }
public final class UserStreamEvents { static Event parse(String json); OrderUpdate/AccountUpdate/AlgoUpdate/ListenKeyExpired/Other }
// c3live.recon
public final class Reconciler { Reconciler(ExchangeGateway, LiveBookC3, FillAccounting, Supplier<SymbolRules>, Consumer<String>, ApiObserver,
  LongSupplier, double equityTol, int matchToRelease, File reanchorFile); Report startup(); Report hourly(); Report checkPositions();
  boolean allowsEntry(String sym); Map<String,String> blocks(); void onUnknownPosition(String sym); }
// c3live.book.LiveBookC3 (thêm)
setMeta(sym, Float pred, int rank, now); setTrail(sym, float peakRate, float priceSL, now); nextStopSeq; setPendingStop; clearPendingStop;
promotePendingStop; retireActiveStop; removeOrphanStop; referencedStopCids(); addFillCosts; addExitFill; overrideFromExchange; addFunding;
addTransfer; anchor; account() -> AccountView; ClusterView += avgEntryF, peakRate, priceSL, symbolPred, rank, stopSeq, pendingStop*,
stopQtyMode, orphanStops, commission, realizedPnl, exitQty, exitAvgPx, exchangeOverride, trailArmed(); confirm(legIdx>0) reset arm.
// c3live.entry.C3LiveEntry: LegInput(…, Float symbolPred, int rank); KillSwitchView.allowDca (default = allowNewEntry);
//   Builder.reconAllows(Predicate<String>); Outcome.RECON_BLOCKED
// c3live.exec.C3LiveCids: STOP_PREFIX = "c3s-"; static String stop(String sym, long minute, int seq)
// c3live.adapter.DryGateway: DryGateway(…, File stateFile, double feeRate); int onPrices(Map<String, Float>); void setEventSink(Consumer<String>)
// c3live.runtime.C3LiveHook: excludeTradFiFeatures(); tradFiFeatureFilterOrNull(); <V> Map<String,V> dropTradFi(Map<String,V>)
// ai_ml…LiveFeaturePipeline: setSnapshotFilter(UnaryOperator<Map<String, KlineObjectSimple>>)
// ops: KillSwitchEngine.allowDca(sym), capacityBlocked(); Params.c4Capacity/c4ReleasePos/c4ReleaseUGap/c3ReleaseOkConsec; OpsHooks.allowDca(sym)
// utils.HttpRequest.redactSecrets(String)
```

## 7. File đổi

Mới (main): `c3live/exit/TrailingStopManager`, `c3live/fill/{UserStream, UserStreamEvents, FillAccounting}`, `c3live/recon/Reconciler`,
`tradecore/selector/C3TrailRate`. Sửa (main): `c3live/{book/LiveBookC3, exec/C3LiveCids, entry/C3LiveEntry, adapter/DryGateway,
adapter/GatewayFactory, runtime/C3LiveRuntime, runtime/C3LiveHook}`, `ops/{KillSwitchEngine, OpsHooks, OpsConfig}`,
`tradecore/selector/TsMktExt`, `ai_ml/features/export/entry/LiveFeaturePipeline`, `trading/DetectEntrySignal2TradeNormal`,
`utils/{Utils, HttpRequest}`, `client/P2PTelegramNotifier`.
Test mới: `c3live/exit/TrailingStopManagerTest`, `c3live/fill/{FakeWsServer, UserStreamWsTest, FillAccountingTest}`,
`c3live/recon/ReconcilerTest`, `c3live/e2e/C3LiveExitE2ETest`, `c3live/adapter/DryGatewayStopTest`, `c3live/runtime/TradFiFeatureFilterTest`,
`c3live/replay/DryDayReplayMain`, `ops/KillSwitchCapacityTest`, `tradecore/selector/{ExitParityEngine, ExitReplayParityTest,
ExitReplayDevMain}`; sửa `c3live/mock/MockExchangeGateway`, `tradecore/selector/TsMktExtTest`.
Khác: `research/v12exit/extract_dev_klines.py`, `ops/c3live/{deploy_v12_dry, rollback_v12, killsw_reset, c3live_status, c3live_reanchor}.sh`,
`ops/c3live/test/test_fake242.sh`, `docs/result/v12exit/*.json` (kết quả replay), tài liệu này.
Artefact ngoài repo (Oracle): `~/claude_master/v12/exit_parity/` (drv.py, jar, d22_exit, bytecode_diff.json), `~/claude_master/v12/jar/
binance-java-sdk-1.2.4.jar_v12dry` (md5 a55be721…, mặc định của deploy script).
