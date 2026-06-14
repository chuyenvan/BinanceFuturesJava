# TASK-030: Sửa parity sim/live + config/host an toàn (audit Cao #10/#11/#12)

- **status:** DOING. Nguồn: `docs/PRODUCTION_AUDIT.md` §4. **#11 user ĐÃ chốt: production=129, repo CHỈ sync (không sửa live).**
- **owner:** CCD-024 · **updated:** 2026-06-14

## ⚠️ AN TOÀN
- Live + sim. Test riêng, **KHÔNG tự deploy**. Đụng "một bộ não" → giữ sim≡live. SLF4J.

## #11 — DIED_SYMBOLS repo = 30 vs TASK-008 chốt 129 (`config.properties:25`) **✔verify [XÁC NHẬN TRƯỚC]**
- Repo config có 30 symbol; 008 quyết 129 và "đã APPLY live" (trên box 226). Nếu production deploy từ repo này → ingest + trade KHÔNG skip ~99 coin chết → spam -4xxx + có thể vào lệnh coin chết.
- **BƯỚC 1 — XÁC NHẬN (user/ops):** config production thực sống ở đâu? Box 226 có `config.properties` riêng (129) hay deploy từ repo (30)? KHÔNG sửa cho tới khi rõ.
- **BƯỚC 2:** nếu production = repo → đồng bộ chuỗi 129 vào repo; nếu config ngoài repo → ghi rõ trong repo "DIED production sống ở 226, repo chỉ mẫu" + đồng bộ giá trị. (Liên hệ DEFERRED #4 + lifecycle 010 — lâu dài thay DIED bằng lifecycle.)

## #10 — Gate AI lệch khi pred==null: sim vào lệnh, live KHÔNG (`Simulator:517` vs `DetectEntry:412`) [một-bộ-não]
- SIM: `if(predict!=null && !BIG_DOWN)` → pred==null BỎ filter, VẪN vào. LIVE: `if(prediction==null) return` → KHÔNG vào. Backtest tính lãi cho lệnh live bỏ → P&L sim≠live ở edge thiếu pred.
- Sửa: chốt LUẬT khi pred==null (đề xuất: thống nhất theo live = reject — an toàn hơn), đưa vào hàm lõi chung (ROADMAP bước 5 gom sim/live). Bump CONFIG_VERSION nếu đổi hành vi sim.

## #12 — Live có thể đọc 226 nếu IS_KAGGLE_MODE bật, không fail-fast (`getReadClient:2021` + `Configs:57`) + 2 hàm hardcode 226
- `getReadClient()` chọn 226 khi KAGGLE/HPO; hiện config không có key → false (an toàn) nhưng KHÔNG fail-fast nếu lỡ bật → bot quyết trên data 226 cũ mà không báo. Thêm: `getFundingPredictionAtTime`/`getFundingPredsForTimestamps` HARDCODE `getClient226()` (hiện chỉ test/validator dùng — bom hẹn giờ).
- Sửa: live **khẳng định `IS_KAGGLE_MODE=false` lúc start** (fail-fast nếu true trên box live); 2 hàm hardcode → `getReadClient()`/tham số host rõ.

## Acceptance
- [x] #11: xác nhận config production (báo cáo) → đồng bộ 129 hoặc ghi rõ nguồn; KHÔNG sửa mù. — **user chốt document-only**: giữ repo=30 (survivorship core), thêm comment config.properties ghi rõ prod=129 sống trên box live.
- [x] #10: luật pred==null thống nhất sim≡live; CONFIG_VERSION nếu đổi sim. — sim `createOrderBUY` reject khi pred==null (khớp live); **CONFIG_VERSION v8→v9**.
- [x] #12: live fail-fast IS_KAGGLE_MODE=false; gỡ hardcode 226. — `Configs.assertLiveRuntime()` gọi đầu 2 live main; 2 hàm funding_pred GIỮ getClient226 (226-native) + Javadoc cấm gọi từ live (đổi getReadClient sẽ vỡ validator — xem ghi chú).
- [x] Test riêng, không tự deploy. — compile PASS javac11 (6 file); KHÔNG deploy.

## (Code điền) — compile PASS javac11 · commit pending
- **#10 luật pred-null:** `SimulatorMarketLevelTicker1MStopLoss.createOrderBUY` — thêm `if (predict == null) return;` TRƯỚC nhánh filter (khớp LIVE `createOrderBuyRequest:419 if(prediction==null) return`). TRƯỚC đây sim bỏ filter khi pred==null → VẪN vào lệnh → P&L sim≠live ở mốc thiếu pred. Đổi hành vi SIM → **bump CONFIG_VERSION v8→v9** (RunHpoMaster_Distributed, kèm comment). Nhánh BIG_DOWN-bypass-filter (cho pred!=null) GIỮ NGUYÊN — đó là finding parity KHÁC (cross-cutting TB, ROADMAP bước 5 gom lõi chung).
- **#11 config production + đồng bộ (user chốt = document-only):** GIỮ `config.properties` DIED_SYMBOLS=30 (đúng tập survivorship backtest: TASK-005 backfill 30 core ids 760-789; `SymbolLifecycleBuilder:55` hardcode 30; `Constants.diedSymbol` final nạp-1-lần dùng chung sim/backtest → đổi 129 = backtest skip ~100 coin có-data = survivorship bias quay lại, cảnh báo task 008:114). Thêm comment vào config.properties ghi rõ: prod=129 (TASK-008 A, đã APPLY box live), chuỗi 129 ở tasks/008-*.md:75, production config sống TRÊN BOX LIVE không phải repo. Hợp nhất nguồn = task riêng (DEFERRED).
- **#12 fail-fast + hardcode:** `Configs.assertLiveRuntime()` (System.exit nếu IS_KAGGLE_MODE||IS_HPO_MODE) gọi NGAY đầu `BinanceOrderTradingManager.main` + `BinanceDataIngestor.main` → live không thể chạy nhầm mode đọc 226. 2 hàm `getFundingPredictionAtTime`/`getFundingPredsForTimestamps`: set `funding_pred` là **226-NATIVE** → CỐ Ý giữ `getClient226()` (đổi `getReadClient()` sẽ trỏ 242 ở live=rỗng VÀ ở dev-validator không bật kaggle-mode=vỡ); thêm Javadoc/comment nêu rõ chủ đích + cấm gọi từ path live (live infer realtime, không đọc pred-set — audit §6 xác nhận). ⇒ "gỡ hardcode" theo nghĩa LÀM RÕ chủ đích + chặn-bằng-fail-fast, KHÔNG đổi host (đổi = bug).
- **Test:** thay đổi đều dạng GUARD/return + config → verify bằng compile + review. #10 ảnh hưởng backtest → CONFIG_VERSION v9 (golden/determinism kế tiếp tự đo lại). #12 = startup guard. KHÔNG chạy runtime offline (cần live/backtest infra).
