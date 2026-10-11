# MAPPER AUDIT 2026-10-11 (MAPAUD) — symbol_mapper symbol→id + 130 "đuôi settle" HO4

Agent MAPAUD. Chỉ ĐỌC 242/shadow (Aerospike get + log), không ghi/restart/deploy. Không mở printDone/equity 2026. JSON `docs/audit/MAPPER_AUDIT_20261011.json`. Script `research/analysis/mapaud_*.py`. Code fix: branch `fix/symbol-mapper` (KHÔNG merge, KHÔNG deploy).

## Kết luận (rủi ro trước)
1. **Live CÓ bị ảnh hưởng, nặng hơn HO4-P1 mô tả.** Ngoài sim, đường live dùng id ở `HistoryManager` (ring theo id) để tính feature lịch sử của Funding/net015 (`FundingDataCollectionManager.java:245,296-583`), quần thể cross-sectional (`DetectEntrySignal2TradeNormal.java:850` `EntrySignalFilter.selectCoins`) và basket (`:778` `CoinRankManager`). Với id trùng, `HistoryManager.processKline` (cùng `startTime` ⇒ ghi đè nến cuối) làm ring của id chỉ giữ nến của symbol được duyệt SAU ⇒ symbol kia nhận feature lịch sử (ret15m, rvol15m, volume z, ATR, RSI, high/low 15m, wick) **của symbol song sinh**. Live 242 đã đặt lệnh BUY thật (log `OrderHelper Create Order market`) trên **11/16** symbol này 2026-08-13 → 08-26 (MINIMAX 4 lệnh, BNC ~7, FWDI 3, SOFI 3, ZHIPU 2, GEV 2, MUU/XBI/VRT/SNOW/SHAZ 1). Không có log 07-16→08-12 (full.log bắt đầu 08-12).
2. **Nguyên nhân (cấu trúc, chắc chắn):** cấp id không nguyên tử giữa nhiều process — mỗi JVM giữ `counter` riêng trong RAM (= max lúc init), `getId` không synchronized, ghi `MapOperation.put` không kiểm trùng (`SimpleSymbolMapper.java:85-86,98-119` bản cũ; `DataManagerAerospikeFloatSim.java:162-177`); đọc mapper có thể từ bản sao Oracle (`getReadClient`) nhưng ghi vào 242. **Cặp writer cụ thể tháng 07 KHÔNG xác định được** (không còn log 07/2026 trên 242/Oracle). Mẫu 8 cặp liên tiếp 843–850, mỗi cặp 1 symbol từ 2 tập rời ⇒ khớp 2 writer độc lập cùng init ở max=842, mỗi writer gặp 8 symbol mới khác nhau. `docs/audit/FIX_NO_WRITE_242_20261003.md:42` đã dự báo đúng rủi ro này (R1′).
3. **Va chạm khác: không.** Toàn mapper 242 (933 symbol, 925 id) chỉ có 843–850. Id "lỗ" 752–759 (không symbol) có từ trước 07-08 — vô hại.
4. **Bom hẹn giờ:** id hardcode trần 1000 (`HistoryManager.MAX_COINS=1000` — live BỎ IM LẶNG symbol id ≥ 1000; `klineArray[1000]` ở `DataManagerAerospikeFloatSim.java:1245`, `KaggleDataLoader.java:110`, `HPOSmartCache.java:216` — sim AIOOBE). Max id 933, tăng ~1,06 id/ngày (863 ngày 08-06 → 933 ngày 10-11) ⇒ chạm 1000 khoảng giữa 12/2026 (cuối 11/2026 nếu sửa id trùng bằng 16 id mới). Chưa sửa trong branch này (đổi đường sim — cần MASTER quyết).
5. **Model đóng băng không bị** (gate p15, net015, S1 không dùng symId làm feature; chỉ là khoá join; cut train ≤ 2026-01-01, 16 symbol chưa tồn tại). Hướng "id ngoài miền train ⇒ OOV" không áp dụng — cách đúng là **id duy nhất**.
6. **130 "đuôi settle": 129 đúng, 0 nhầm, 1 không rõ (STGUSDT).** Volume bị cắt = 0 USDT (mọi symbol: 0 volume sau điểm bắt đầu đuôi trên cả Vision lẫn 242). Không cần đổi luật universe HO4.
7. Phụ: `config.properties` của live 242 chứa token bot dạng rõ; một lệnh grep của MAPAUD (lọc thiếu) đã in nó ra output phiên — không ghi vào file/commit nào. Khuyến nghị MASTER cân nhắc xoay token.

## M1 — Nguồn mapper
| Bên dùng | Nguồn thật | n / max / id khác nhau | Trùng 843–850 |
|---|---|---|---|
| **Live 242** `v_t_m` (`BinanceOrderTradingManager`, PID 18269, khởi 10-11 09:02, tự restart ~4 h) + `collectData` (`BinanceDataIngestor`, PID 5573) | Aerospike 242 `103.157.218.242:3222` ns `ticker` set `symbol_mapper` key `global_id_map` bin `data` (map String→Long), gen 1284. Jar cả 2 app sha256 `b0f23b7d…6315`. Log: `Loaded Symbol Mapper: 933` | 933 / 933 / 925; sha256(chuỗi `symbol,id\n` sắp theo symbol) `a5334902…826e` | CÓ |
| **Shadow** `~/shadow_c3/app`, `~/shadow_c3b/app` (Oracle) | Đọc 242 (`AEROSPIKE_READ_CLUSTER=242`), jar `b0f23b7d…` (cùng live), `[NO-WRITE-242]` bật (`LIVE_IS_SHADOW_HOST=true`) | 933 (log init 10-11 09:04/09:05) | CÓ |
| **Sim/bundle DEV, HO26, HO4** | Bản sao `ho3b-asdata` = `~/claude_master/1003/ho3b/ds_asdata/asdata_local.pkl` = Aerospike Oracle ns `test` (gen 2) = `symbol_map_863.csv` (= `~/claudedata/symbol_map_20260806.csv`, sha256 `3f817551…`) | 863 / 863 / 855 | CÓ |
| **Train model đóng băng** (gate p15, net015, S1) + pipeline cũ | `symbol_map.csv` 781 (`~/selector_pred_out`, `~/val_pred`, stage `symbol_map_781.csv`, sha256 `41ee8f1b…`, 07-08) và 863 cho Tool1/OI/CLOSES_1H | 781 / 789 / 781 | KHÔNG (16 symbol chưa có) |

- Mọi snapshot khớp live trên mọi symbol chung (0 id khác); chỉ thêm symbol mới. Id lỗ 752–759 có ở cả 781 (07-08) ⇒ không liên quan.
- **Thời điểm:** giữa 07-08 (781, max 789, 0 trùng) và 08-06 (863, đã trùng); 16 symbol có kline từ 2026-07-16.
- **Ai sinh / quy tắc cấp id (bản cũ):** `SimpleSymbolMapper.init` `:68-91` nạp map qua `DataManagerAerospikeFloatSim.loadSymbolMapper` `:134-156` (`getReadClient()` — có thể là bản sao Oracle), `counter = maxId`; `getId` `:98-119`: chưa có trong RAM ⇒ `newId = ++counter` (field `short` thường, không synchronized) ⇒ `saveSymbolMapping` `:162-177` = `getClient242().operate(MapOperation.put(MapPolicy.Default …))` — không kiểm id đã dùng, ghi đè nếu symbol đã có. Writer thực tế: mọi JVM gọi `getId` với symbol mới — live `v_t_m` qua `HistoryManager.updateHistory:62` mỗi tick; trước 10-02 cả tool/exporter/sim Oracle có `AEROSPIKE_HOST=242` (đọc bản sao Oracle cũ, ghi 242) và kernel Kaggle; shadow (từ 09-18, đã chặn từ 10-02). `BackfillTickerPilot` ghi tay nhưng có kiểm trùng (`:120`).
- **Vì sao 2 symbol chung id:** 2 process cùng `counter=842`, mỗi process gặp 8 symbol mới khác nhau ⇒ cả hai cấp 843..850 ⇒ map giữ cả 16 khoá. Thuật toán cũ tái hiện y hệt mẫu này trong JUnit `legacyAlgorithm_reproduces843to850`.

## M2 — Ảnh hưởng
**Model:** không model nào dùng symId làm feature/embedding. net015 (`g015_net_train.py:105-116`): Tool1 + OI ghép theo `(ts, symId)` rồi map tên qua `symbol_map` ⇒ id trùng = trộn dòng 2 symbol / nhân đôi dòng. S1: 9 feature theo tên (`S1FeatureLive.FEATURE_ORDER`). Gate: không có cột id. Train cut ≤ 2026-01-01 ⇒ 843–850 không thuộc miền train.

**Sim (DEV/HO26/HO4):** đọc ticker theo id `readDataFromAerospike1M_ShortKey` (`DataManagerAerospikeFloatSim.java:1245-1250`: `klineArray[symbolId] = …` ⇒ symbol sau ghi đè symbol trước mỗi phút) + `HistoryManager` theo id. DEV/HO26 (≤ 2026-06-30): 16 symbol chưa tồn tại ⇒ không ảnh hưởng. HO4 (07–09/2026): §6.2a đã loại 843–850 khỏi Tool1/net015/bins/CLOSES_1H/feat_v2/OI. **Chưa kiểm (PLAUSIBLE):** §6.2a ghi "vẫn ở market/gate tính theo tên", nhưng exporter Java đi qua đường theo id ⇒ mỗi cặp có thể chỉ còn 1 symbol/phút trong market/gate breadth (8 symbol nhỏ / ~650; ảnh hưởng nhỏ). MASTER quyết có ghi chú hay không — không đổi luật, không nhìn kết quả.

**Live 242** — đường quyết định:
| Thành phần | Khoá | Bị id trùng? |
|---|---|---|
| Danh sách ứng viên, ticker cuối, OI (`LiveOiFeatProvider.lookup(symbol)`), S1, LiveBuildMap | tên | không |
| Feature lịch sử Funding/net015 Tier1 (`FundingFeatureExtractorV2` → `HistoryManager.getRsi14/getVolumeZScore/getAverageVolume/getAverageRange/getReturn/getVolatility/getHighN/getLowN/getAvgUpperWickRatio`) | **id** (ring `HistoryManager`, `MAX_COINS=1000`) | **CÓ**: ring id chỉ giữ nến symbol duyệt sau (ghi đè cùng phút, `HistoryManager.processKline`) |
| Quần thể cross-sectional `EntrySignalFilter.selectCoins` (`:850`) | id | CÓ (vol/ret của symbol song sinh) |
| Basket `CoinRankManager.getTopCoin` (`:778`) | id → `getSymbol(id)` | CÓ (id trùng chỉ ra 1 tên) |
| `ai_pred_1m` (market), `PumpDumpFilter`, `TickWeakBlock` | — / id | không chạy trong log live |

Ước lượng symbol "nạn nhân" (feature lịch sử = của song sinh) theo thứ tự duyệt `java.util.HashMap` (`research/analysis/mapaud_hashorder.py`; phụ thuộc dung lượng map — chỉ ước lượng): dung lượng 1024: XBI, SOXS, TZA, MINIMAX, SNOW, APP, GEV, PANW; 2048: đổi 845→FWDI, 846→VRT, 850→SKHY.

Log live 242 (`v_t_m` full.log từ 08-12, logt9 09-01..10, nohup.out.bak 09-14..28; chỉ đếm dòng):
| Symbol | AI PASS | Push order | Lệnh BUY (≈ dòng/2) | | Symbol | AI PASS | Push | BUY |
|---|---|---|---|---|---|---|---|---|
| MUUUSDT | 1 | 1 | 1 (08-22) | | XBIUSDT | 1 | 1 | 1 (08-19) |
| BNCUSDT | 125 | 16 | ~6 (08-17→08-22) + shadow 09-08 | | SOXSUSDT | 79 | 0 | 0 |
| FWDIUSDT | 10 | 4 | 3 (08-17→08-18) | | TZAUSDT | 0 | 0 | 0 |
| MINIMAXUSDT | 49 | 4 | 4 (08-13→08-14) | | VRTUSDT | 1 | 1 | 1 (08-18) |
| SNOWUSDT | 25 | 1 | 1 (08-17) | | ZHIPUUSDT | 3 | 3 | 2 (08-19) |
| APPUSDT | 0 | 0 | 0 | | SHAZUSDT | 22 | 1 | 1 (08-17) |
| GEVUSDT | 2 | 2 | 2 (08-13, 08-17) | | SOFIUSDT | 4 | 4 | 3 (08-17→08-21) |
| PANWUSDT | 2 | 0 | 0 | | SKHYUSDT | 0 | 0 | 0 |

Lệnh tháng 08 là lệnh thật (`OrderHelper: Create Order market … BUY`), trước khi 242 chạy `LIVE_PROFILE=c3_shadow` + `SHADOW_NO_PUSH=true` (giấy). Shadow Oracle: 0 sự kiện cho 16 symbol (log từ 09-18 / 10-08). Không có exception/UNKNOWN- id trong log. Không xác định được PnL theo symbol (ngoài phạm vi; không mở).

## M3 — Đề xuất + sửa (branch `fix/symbol-mapper`, từ `origin/module` f9b41b28)
**Phương án chọn: id duy nhất, cấp nguyên tử, fail-fast khi nạp; không retrain.** OOV không áp dụng vì model không có embedding id — vấn đề là khoá join/ring trùng, chỉ id duy nhất mới sửa được.
- `SymbolIdRules` (thuần): `duplicateIds`, `assertUniqueIds`, `nextId = max(đã ghi, cục bộ)+1` (không tái dùng id cũ), `planRepair` (MỌI symbol của id trùng → id mới max+1…; id trùng cũ bỏ hẳn vì dữ liệu lịch sử theo id đó đã trộn 2 symbol).
- `SimpleSymbolMapper`: `init` fail-fast nếu id trùng (`SYMBOL_MAPPER_DUP_POLICY=FAIL` mặc định; `WARN` = log ERROR + `getSymbol(id trùng)` tất định = tên nhỏ nhất). `getId` fast-path RAM; cấp mới `synchronized` + CAS trên store: đọc map + generation từ CHÍNH cụm ghi (242), symbol đã có ⇒ dùng id đó (không ghi đè), chưa có ⇒ ghi với generation + `MapWriteFlags.CREATE_ONLY`, xung đột ⇒ đọc lại (≤ 20 lần). Process chỉ đọc (Live242WriteGuard chặn) hoặc lỗi store ⇒ id CỤC BỘ duy nhất trong JVM, không ghi. Log ERROR khi id ≥ 1000 (trần mảng).
- `AerospikeSymbolMapperStore` (CAS thật), `SymbolMapperRepairTool` (`check` / `plan` / `apply <backup.json>` cần `MAPPER_REPAIR_CONFIRM=YES`, backup trước, 1 lệnh `putItems` có generation, đọc lại assert 0 trùng), `Cfg.INFRA_KEYS` += `SYMBOL_MAPPER_DUP_POLICY`, `MAPPER_REPAIR_CONFIRM`; `MAPPER_BIN_NAME` public.
- JUnit `SymbolMapperIdTest` 9 ca: tái hiện thuật toán cũ ra đúng 8 cặp 843–850; 2 "JVM" xen kẽ ⇒ 16 id khác nhau; symbol JVM khác đã cấp ⇒ dùng lại, không ghi; CAS xung đột 2 lần ⇒ id kế tiếp; process chỉ đọc ⇒ id cục bộ không ghi; init FAIL/WARN; 4 JVM × 32 luồng chồng symbol ⇒ duy nhất + nhất quán; `planRepair` 16 symbol → 934..949.
- `mvn -o -q test` toàn module: **trước 264 test / 45 lớp PASS → sau 273 / 46 PASS**.
- Chưa làm (cần MASTER): nâng trần 1000 (`HistoryManager.MAX_COINS`, `klineArray[1000]` ×3) — đổi đường sim; `VolTargetSizing`/`PacingSizing` đọc `/home/ubuntu/selector_pred_out/symbol_map.csv` (781, cũ).

### Runbook deploy (MASTER; MAPAUD không chạy)
Tiền đề: KHÔNG deploy jar mới trước khi sửa dữ liệu — `init` sẽ fail-fast (live dừng). Cửa thoát khẩn: env `SYMBOL_MAPPER_DUP_POLICY=WARN`. Không đụng holdout HO4 (dùng bundle đóng băng).
1. Build jar từ `fix/symbol-mapper` (sau review/merge). Trên host ĐƯỢC ghi 242 (không `LIVE_IS_SHADOW_HOST`): `java -cp <jar> com.binance.chuyennd.aerospike.tools.SymbolMapperRepairTool check` ⇒ kỳ vọng exit 3, `idTrung=8`.
2. `… plan` ⇒ 16 symbol → `max+1…max+16` (hiện 934..949 nếu chưa có niêm yết mới). Lưu output.
3. Dừng 2 app 242 (`v_t_m`, `collectData`) — JVM cũ giữ `counter=933` trong RAM sẽ cấp 934+ trùng id vừa sửa.
4. `MAPPER_REPAIR_CONFIRM=YES java -cp <jar> …SymbolMapperRepairTool apply /root/mapper_backup_<yyyymmdd_HHMM>.json` ⇒ `[MAPPER-REPAIR] OK … 0 id trung`. Backup JSON (map + generation) giữ để pháp y; sửa là một chiều (rollback = chạy jar cũ với `WARN`, không khôi phục trùng).
5. `… check` ⇒ exit 0. Khởi động 2 app 242 bằng jar mới ⇒ log `SimpleSymbolMapper initialized. Total: 933, Next ID: 950`, không có `[MAPPER-DUP]`.
6. Restart 2 shadow Oracle (đọc 242) bằng jar mới. Làm tươi bản sao Oracle (`CopyAuxSets242To226`) và sinh lại `symbol_map.csv` cho pipeline mới; dòng cũ khoá 843–850 trong artefact Oracle sẽ không còn map (bị bỏ — đúng, vì đã trộn).
7. Sim Kaggle dùng jar mới + pickle mapper 863 cũ sẽ fail-fast ⇒ dùng mapper đã sửa hoặc `SYMBOL_MAPPER_DUP_POLICY=WARN` trong `extra_env` (quyết định parity của MASTER).
8. Kiểm sau 24 h: `check` exit 0; grep log 242 `[MAPPER] cap id moi` (CAS) cho niêm yết mới; không `[MAPPER-CAP]`.

## M4 — 130 "đuôi settle" (`ho4p1_excl26.json`, chi tiết `~/claude_master/1011/ho4p1/no_funding_union.json`)
Luật (`mapaud_settle.py`, cố định trước khi chạy): **nhầm** = có volume > 0 sau ngày bắt đầu đuôi (Vision ngày ≥ from_day+1) hoặc 242 volume > 0 sau from_ts ở ≥ 2 ngày mẫu; **đúng** = không volume sau đuôi VÀ (pin ≠ TRADING hoặc lifecycle ≠ LIVE hoặc Vision hết file); còn lại **không rõ**. Nguồn: Vision kline 1d (monthly 2026-01..09 + daily 10-01..10), Aerospike 242 `kline_1m_opt` mẫu 12:00 +07 mỗi ngày 2026-01-01..10-10 (282 record, CHỈ ĐỌC), `exchange_info_pin.json` (2026-09-03). Set `symbol_lifecycle` trên 242 không có record theo khoá symbol (130/130 NOT_FOUND) ⇒ không dùng được.

| Kết quả | n | Ghi chú |
|---|---|---|
| đúng (settle/delist) | 129 | 127 `SETTLING` trong pin; BDXNUSDT, SXPUSDT không có trong pin và file Vision dừng 2026-03-31 / 2026-05-31 |
| nhầm (đang giao dịch) | **0** | Vision: 0 ngày có volume sau đuôi (130/130); 242: 0 mẫu volume > 0 sau đuôi |
| không rõ | 1 | **STGUSDT**: đuôi từ 2026-09-24; pin 09-03 còn TRADING (trước đuôi); Vision + 242 volume 0 từ 09-24 → 10-10 ⇒ nhiều khả năng delist cuối 09, thiếu nguồn trạng thái độc lập sau 09-03 |

- 68/130 không có giao dịch nào trong cửa sổ (đuôi từ 2025-12-01 = đầu lead-in): symbol đã chết nhưng Vision vẫn phát kline volume 0.
- 122/130 vẫn có dòng kline volume 0 trên 242 sau điểm đuôi (ingest tiếp tục ghi nến 0 cho symbol settle — lưu ý cho universe live).
- **Ảnh hưởng:** volume quote bị cắt = 0 USDT mọi tháng (universe 821 symbol; tổng 1,14–1,54e12 USDT/tháng) ⇒ tỉ trọng 0. **Đề xuất: không sửa luật universe HO4.** Tuỳ chọn ghi chú STGUSDT trong ADDENDUM — MASTER quyết trước khi chấm; MAPAUD không nhìn kết quả sim 2026.

## Rủi ro còn lại
- Không xác định được cặp writer gây trùng tháng 07 (thiếu log); fix chặn mọi tổ hợp writer, không phụ thuộc biết thủ phạm.
- Ước lượng symbol nạn nhân dựa thứ tự HashMap (giả định dung lượng 1024/2048) — chưa kiểm bằng feat_dump live.
- Lệnh live 07-16→08-12 trên 16 symbol chưa biết (không còn log).
- Trần id 1000 (≈ 6–9 tuần) — rủi ro live im lặng; ưu tiên cao sau khi sửa trùng.
- §6.2a market/gate breadth có thể thiếu 8 symbol (PLAUSIBLE, chưa kiểm).
