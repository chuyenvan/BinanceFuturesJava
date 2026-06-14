# AGENTS.md — Bản đồ CCD đang chạy (nguồn sự thật điều phối)

> Nhiều CCD chạy song song KHÔNG thấy nhau; Desktop là console nhưng cũng chỉ biết qua file này.
> File này là **nguồn sự thật DUY NHẤT** về "CCD nào đang làm task nào". Mục đích: reset máy / đổi session không mất vết, không hai CCD đụng một task.
> Cập nhật bằng tay (Desktop khi spec task; CCD khi claim/heartbeat/đóng). Không lock cứng — user là trọng tài khi tranh chấp/stale.

## Hiện trạng (cập nhật mỗi khi đổi)

| Task | Owner (CCD) | Status | Cập nhật | Job/PID nền | Ghi chú |
|------|-------------|--------|----------|-------------|---------|
| 005 backfill survivorship | — | ✅ DONE | 2026-06-13 | — | commit d387229; 30 core (id 760-789) |
| 007 fix ban + Reporter + OI + gom log | CCD #2 | ✅ DONE (commit 106baee) | 2026-06-13 | — | A-D xong; startHistoryCrawl **ĐÃ gỡ** ở TASK-023 (`b231b6d`) — history OI → 013; B/D golive OK |
| 016 fix ingest live (TickerFuturesHelper -1130/-1003) | CCD #1 | ✅ DONE + DEPLOYED | 2026-06-14 | — | clamp [1,1500] + guard -1003-rate 8s; self-test 10/10; ĐÃ deploy gộp 016+019+gỡ-crawl (live -1130 hết) |
| 019 fix funding live (FundingFeeManager + FundingIngestor) | CCD #1 | ✅ DONE + VERIFIED LIVE | 2026-06-14 | 242 (live) | refresh THỰC: '754 symbol' @08:55 (N>0 ✓); -1130 hết; OI-History-Crawl HẾT; ingest 622 sym. **Deploy gộp 016+019+gỡ-crawl TRỌN VẸN** |
| 020 audit production 2-process (rà lỗi ẩn) | CCD-audit | ✅ DONE | 2026-06-14 | — | OUT docs/PRODUCTION_AUDIT.md (12 Cao); Desktop đã bóc → TASK-027 (entry) / 028 (ingest) / 029 (concurrency) / 030 (parity-config) |
| 021 dump trạng thái thực (reconcile mất log) | CCD-recon | ✅ DONE | 2026-06-14 | đọc-only (git+Aerospike+fs) | OUT: docs/STATUS_RECON.md. CHỐT: 019 wiring+B chưa commit (refresh DEAD ở HEAD); startHistoryCrawl CHƯA gỡ (note 007 sai); 013-B2/015 chưa code; 010 builder chưa chạy; #record cần scan 226/242 |
| 023 gỡ-crawl + scan Aerospike + deploy-prep | CCD #1 | 🟣 REVIEW | 2026-06-14 | 226 (scan) + code | P1 gỡ startHistoryCrawl `b231b6d` (+fix catch-câm); P2 tool `AerospikeStateScan` `ff579a6`, đo 226 thật (lifecycle RỖNG, OI@226=0, kline/funding@226 dừng 2026-06-07) → STATUS_RECON §5, **số 242 chờ chạy scan TRÊN 226**; P3 runbook `docs/DEPLOY_242.md`. KHÔNG tự deploy |
| 008 audit died-symbols | CCD #3 | ✅ DONE | 2026-06-13 | — | phương án A: gỡ 8 coin, config 129 symbol — đã APPLY live |
| 010 lifecycle 3-trạng-thái | CCD #2 (giao RUN) | 🟡 RUN trên KAGGLE | 2026-06-14 | Kaggle (đọc/ghi 226) | code done; **RUN builder trên KAGGLE** (chỉ đụng 226, KHÔNG 242) → mở 024+lifecycle; ⚠️ kiểm builder ghi 226-only trước launch |
| 009 aggregate 15m/4h BTC/ETH | (CCD vừa xong) | ✅ DONE (historical) | 2026-06-13 | ⚠️ 2 PID thừa | commit 3edb5b1; 15m~190k/4h~11.8k; writeSeries ghi **CẢ 226+242**; FORWARD-rolling CHƯA bật → **TASK-031** (ghi 242 realtime cho golive gate). ⚠️ 2 process Aggregate (PID 23709+27609) còn chạy 226 → kill |
| 011 cải tiến validate-input | — | ⏸ CHỜ | — | — | sau 009/010 |
| 012 export gate LABEL (return) + validate | CCD (009) | ✅ DONE (commit 72c127a) | 2026-06-13 | ⚠️ PID 31944 thừa | gate_return.csv 190k dòng, 5 validate PASS; ret_24h≤−15% chỉ 0.92% → lớp GIẢM cực hiếm (H2). ⚠️ **ExportGateReturn (PID 31944) còn chạy 226 → kill** (đã xong) |
| 013 backfill OI/LS/taker history (metrics) | CCD #2 | 🟡 B1 VERIFY DONE · B2 backfill CHƯA | 2026-06-14 | tải Kaggle/226 · ghi 226(+242) | B1: coverage 896 sym, nền metrics ~2021-12 (chỉ BTC 2020-09), 5m UTC, đơn vị == API diff 0% (khớp 007-C); schema 1.5 **CHỜ user chốt**; B2 chưa có class |
| 015 feature gate NHÓM A (sẵn-có) | CCD-audit | 🔵 DOING (RUN Kaggle) | 2026-06-14 | Kaggle (đọc 226→CSV) | code done (`ExportGateFeaturesGroupA` 19 feat, survivorship OK). RUN Kaggle: jar→dataset java-run, kernel enable_internet đọc Aerospike 226→outputs/gate_features_groupA.csv. Ra feature→mở 017 |
| 017 feature gate B giá/xu-hướng + funding-breadth | — | ⏸ (sau 015) | — | — | B1-B5 + B7; code mới 15m/4h + funding; LÀM NGAY (không chờ data) |
| 018 feature gate B crowdedness OI/LS-market | — | ⏸ (sau 013) | — | — | B6 OI-market + B8 LS-market (aggregate=gate); CHỜ 013 backfill |
| 025 H1 ghép + export full dataset gate | — | ⏸ (sau 015+017+018) | — | — | §3: ghép + validate chung (corr/leakage/drift/screen) + dataset versioned + fingerprint → H2 |
| 026 H2 train gate 3-class | — | ⏸ (sau 025) | — | — | §4: purged K-fold+embargo, threshold grid X/Y, beat rule baseline, OOS đông lạnh; Kaggle |
| 014 khảo sát data.binance.vision | CCD #3 | ✅ DONE | 2026-06-13 | — | KQ trong task: metrics 2020-09 (OI/LS/taker 5m); premiumIndex/mark/index basis 1m (CAO); **liquidationSnapshot KHÔNG còn**; bookDepth 2023+; bookTicker dừng 2024 |
| 024 funding LABEL triple-barrier (path thô) | CCD #2 (giao) | 🟡 chờ 010→RUN KAGGLE | 2026-06-14 | Kaggle (đọc/ghi 226) | code done; chờ builder 010 (cùng CCD2) ra lifecycle → RUN trên KAGGLE (226). ⚠️ ghi 226-only |
| 022 verify basis 1m (premiumIndex/mark/index) | CCD-basis | 🟣 REVIEW (B1 verify DONE) | 2026-06-14 | tải vision (đọc-only) | OUT `docs/basis_verify.md`: 1m UTC, 3 loại 12-cột; BTC từ **2020-01** (đính chính 014 ghi 2019-12); đại diện = **premiumIndex.close** (=input funding, corr0.895 với mark−index); bổ trợ funding CAO. CHỜ user chốt dùng+schema→B2 backfill |
| 027 fix entry correctness (audit #6/7/8) | CCD-audit | 🟣 REVIEW (code DONE, BUILD OK) | 2026-06-14 | live (test riêng) | #6 dọn dead V4 (logic GIỮ V3); #7 size theo price_realtime+tuổi 30s (Configs, live-only no-bump); #8 aiBrain null→Telegram+fail-fast; +NPE BTC null-check. File: OnnxInferenceManager/DetectEntry/Configs (KHÔNG đụng 028). Chờ soát+gộp deploy |
| 028 fix ingest robustness (audit #1/2/3) | CCD-basis | 🟣 REVIEW (code DONE; chờ gộp deploy) | 2026-06-14 | live (test riêng) | #1 funding qua BinanceRestGuard (await+reportBan), self-test -1003→cooldown PASS; #2 watchdog **BẬT LẠI**+fix counter++/log (user chốt); #3 HttpRequest hết catch rỗng (classifyError TIMEOUT/DNS/SSL/...). javac11 PASS. CHƯA deploy — gộp 016/019/gỡ-crawl |
| 029 fix concurrency+position (audit #4/5/9) | CCD-024 | 🟣 REVIEW (code DONE, test 4/4 PASS) | 2026-06-14 | code (test riêng) | commit `409ab7e`: #4 striped-lock writeMinuteBatch · #5 ForkJoinPool chung · #9 swap-map+removeLock try/finally. Task029ConcurrencyCheck 4/4 PASS. KHÔNG deploy |
| 030 fix parity+config/host (audit #10/11/12) | CCD-024 | 🟣 REVIEW (code DONE, compile PASS) | 2026-06-14 | code (test riêng) | #10 sim reject pred==null (khớp live) + **CONFIG_VERSION v8→v9**; #11 user chốt **document-only** (giữ repo DIED=30 survivorship; comment prod=129 sống box live); #12 `Configs.assertLiveRuntime()` đầu 2 live main + Javadoc 2 hàm funding_pred (226-native, KHÔNG đổi getReadClient kẻo vỡ validator). KHÔNG deploy. ⚠️ commit kèm field 027 PRICE_REALTIME_MAX_AGE (chung Configs.java) |
| 031 forward-rolling kline_15m/4h ghi 242 | CCD #1 | 🟣 REVIEW | 2026-06-14 | 242 (live, test riêng) | `Kline15m4hForwardRoller` (`dd883f9`) wire vào BinanceDataIngestor: loop 60s, khung đóng+grace120s → gom 1m@242 → append record-tháng 242; format/quy tắc Y HỆT 009 (một bộ não); resume qua restart; main() test 1 vòng. javac11 PASS. **Verify ts-tiến + historical@242 chờ chạy AerospikeStateScan TRÊN 226**; gộp deploy 242 có soát |
| 032 scan TOÀN DIỆN 242 → file inventory | CCD #1 (giao) | 🟡 TODO | 2026-06-14 | 226 (đọc 242) | nâng AerospikeStateScan: namespace-stats + MỌI set (#record/bytes) + market ts-range/schema + so 226 → `docs/aerospike_242_inventory.md`; phục vụ chốt DATA_ARCHITECTURE §6 (A/B + replicate). Đọc-only, ưu tiên info/asinfo |

Status: 🟡 TODO · 🔵 DOING · 🟣 REVIEW (chờ user/Desktop soát) · ✅ DONE · ⏸ CHỜ (phụ thuộc task khác).

**Tài nguyên (chi tiết ở CLAUDE.md):** 242 = live PRIVATE (ghi 242 phải chạy trên 226/242) · 226 = backtest/train, open-net · Kaggle = tải-ngoài/train. **Tránh dồn nhiều job nặng cùng lúc trên 226**; tải-ngoài đẩy Kaggle. **226 KHÔNG có job live (user 2026-06-14: cả BinanceOrderTradingManager + BinanceDataIngestor đều trên 242) → kill rác/job thừa 226 tự do (theo PID, KHÔNG killall đụng HPO).**

## Quy ước (mọi CCD tuân — đọc TRƯỚC khi nhận task)

1. **Định danh CCD:** mỗi CCD tự đặt một nhãn ổn định trong phiên (vd `CCD-A`, hoặc theo terminal/cửa sổ user gán) + ghi PID job nền nếu có. Nhãn để phân biệt, không cần toàn cục.
2. **CLAIM trước khi làm:** đọc bảng trên + header task. Nếu task đã có owner KHÁC + DOING + `Cập nhật` còn gần đây → **KHÔNG đụng**, báo user. Nếu trống / STALE → ghi owner + `DOING` + `Cập nhật`=now vào **cả bảng này VÀ header task** rồi mới làm.
3. **HEARTBEAT:** cập nhật `Cập nhật` mỗi lần commit hoặc đổi bước lớn. Nếu một task `DOING` mà `Cập nhật` quá cũ (≳2h, không tiến triển) + nghi máy reset → coi **STALE**, user/Desktop có quyền reclaim cho CCD khác.
4. **ĐÓNG:** xong thì set `✅ DONE` + nhả owner + ghi commit hash. Cần user soát trước khi đóng → set `🟣 REVIEW`.
5. **Một task = một owner.** Không hai CCD cùng một task. Việc lớn thì tách task con (vd 007-A / 007-C) rồi claim riêng.
6. **Desktop (console)** khi spec task mới: thêm dòng `TODO` owner trống vào bảng + header task. Desktop KHÔNG tự claim (không chạy được).

## Liên kết
- Chi tiết từng task: `tasks/<id>-*.md` (mỗi task có header `owner/status/updated`).
- Tuyến đường tổng: `docs/REBUILD_ROADMAP.md`. Luật kỹ thuật: `CLAUDE.md`.
