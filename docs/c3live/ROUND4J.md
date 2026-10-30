# ROUND 4j — v1.2/c3-live: sửa A1 R4GHI (MAJ-1/2/3, MIN-1/4/5)

Nguồn: `~/claude_master/v12/A1_R4GHI_REPORT.md`; test đối kháng A1 `~/claude_master/v12/a1r4i_adv/` chép NGUYÊN (md5 trùng) vào suite:
`ai_ml/data/A1R4iAdvMapperTest`, `ai_ml/onnx/entry/A1R4iAdvSeedTest`, `c3live/canary/A1R4iAdvK7bTest` — trước 4j 5/6 TRƯỢT, nay 6/6 ĐẠT.
Script deploy dry VẪN pin r4f. Chưa push.

## Thứ tự (MAJ-3)
1. `4c0e9d0d` ĐÍNH CHÍNH 1 ADDENDUM K7B (commit TRƯỚC code): chỉ `X=EXPIRED`; `ts` bắt buộc là số; 0 `CALL_W cancelStop` của sid từ
   `K7B_INJECT_ON`; còn lại fail-closed; KEPT_B gần như không xảy ra trên sàn thật ⇒ nhánh guard-GIỮ chỉ chứng minh bằng test.
2. Code `c6c11e0e`.

## Sửa
- **MAJ-3** `CanaryEngine.stopEndExchangeReject` (:2488) bản siết 8 tham số; K7b gọi `expiredOnly=true, ownCancelSince=tInj` (:2718).
  Bản 6 tham số (K5) chỉ bị SIẾT: bắt buộc ts số + loại khi có cancelStop của chính stop sau mốc gửi; vẫn nhận CANCELED (§3k R1).
- **MAJ-1** `SimpleSymbolMapper`: `register` (:205) từ chối id đang thuộc symbol khác ⇒ `quarantine` (:249): id riêng từ đỉnh mảng
  (4095↓, không bao giờ trùng), `isQuarantined` (:269), Telegram KHẨN (chỉ process trading: `enableTelegramAlerts` :228 gọi ở
  `BinanceOrderTradingManager.main`; test/tool/ingestor chỉ log). Init policy WARN: symbol KHÔNG sở hữu id trùng cũng bị cách ly
  (242: `XUSDT` cách ly, `BTCUSDT` giữ id 1 — KHẨN 1 lần mỗi lần khởi động). `allocate` trả id thật đã gán. Chặn: bỏ khỏi
  `symbol2FinalTicker` (DetectEntrySignal, không vào lệnh/không ứng viên), `LiveFeaturePipeline.filt`, `HistoryManager.updateHistory`
  (không nạp history). Chủ id chạy bình thường.
- **MAJ-2** `LiveGateRollingRatio.initSeedBranch` (:118): KHÔNG còn `System.exit`. `applySeedFile`: file đánh dấu
  `<persist>.seeded` (:242) ⇒ restart / watchdog `Utils.reset` / reboot: persist THẮNG, bỏ qua seed + WARN (không kiểm lag/md5).
  Lần đầu seed hỏng (md5/định dạng/khoảng/lag) ⇒ `isSeedBlocked` (:143) ⇒ `AIRejectFilter.entryGate` (:93) REJECT MỌI leg
  (selector, BIG_DOWN, DCA) + Telegram KHẨN; trailing/stop/đóng không qua gate ⇒ vẫn quản lý vị thế.
- **MIN-1** `C3MergedGuard`: đọc bằng chứng (queryStop/queryOrder) lỗi ⇒ `retryAgain` (:312) tối đa 5×30 s trước khi LOST_FOREIGN
  (:379); khoá thử lại theo CỤM `retryKey = symbol@tsFirstLeg` (:305), cụm cũ cùng symbol bị xoá.
- **MIN-4** vòng selector production = `GatePreFilter.runSelector` (`GatePreFilter.java:127`, gọi ở `DetectEntrySignal2TradeNormal:561`);
  nguồn sổ c3 thật thay được khi test (`setC3OwnedSourceForTest`); `C3LiveHook.ownedSymbols` lỗi ⇒ WARN (5′).
- **MIN-5** `LiveFeatureDump.openMain` (:283): trần TỔNG thư mục dump `LIVE_FEAT_DUMP_MAX_TOTAL_MB` (mặc định 2048; 0 = không trần) —
  chạm trần ⇒ dừng dump, KHÔNG xoá file (242 hiện 38 MB).

## Test mới (24 + 6 A1)
`MapperQuarantineR4jTest` 3, `GateSeedR4jTest` 4 (lần đầu ⇒ restart watchdog tức thì ⇒ restart 48 h ⇒ reboot với md5 sai/file mất;
seed hỏng/quá cũ lần đầu ⇒ chặn + KHẨN, không exit, cả leg BIG_DOWN/DCA bị REJECT), `CanaryK7bStrictR4jTest` 7,
`MergedEvidenceRetryR4jTest` 2 (lỗi tạm ⇒ TRAILING_STOP; lỗi kéo dài ⇒ 4 lần giữ rồi LOST_FOREIGN), `GateSelectorProductionR4jTest` 1
(runSelector + heldPredicate C3_LIVE_BOOK đọc LiveBookC3 THẬT của rig + AIRejectFilter/LiveGateRollingRatio thật: coin giữ đếm hạng
không nạp r; LEGACY nạp r giữ chỗ, hạng 5 không thế; A1 không đếm hạng), `LiveFeatureDumpCapR4jTest` 1; `GateSeedR4hTest` sửa 1 dòng
(md5 sai sau khi đã đánh dấu ⇒ persist thắng); mock `failQueryStop/failQueryOrder`.

## Kiểm
- `mvn -o -T 1 package` (lock): **911 test, 0 fail, 1 skip**.
- Jar `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4j` md5 **ba71eab2da6aac7bd296d7d5812e2d83** (pin `canary_lib.sh`).
- Gói `~/claude_master/canary_3m/ops/c3live/canary` = repo (diff rỗng). KHÔNG chạy canary/soak.
- fake242: **TEST PASS 217/217** (`~/claude_master/v12/r4j_fake.log`).
