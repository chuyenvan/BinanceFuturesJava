# ROUND 4h — v1.2/c3-live: lọc trước gate theo quy ước sim, seed buffer, soak user-data stream, theo dõi rò native

Trên `36e3bd96` (4g). Quyết định MASTER 4g: MINOR-A hết 5 lần thử ⇒ giữ 4f (fail-closed, KHẨN, không ghi một phần) — không đổi.
Script deploy dry **vẫn pin r4f**. Chưa push.

## 1. Lệch parity ở gate (coin đang giữ vẫn nạp r)
- **Sim** (`SimulatorMarketLevelTicker1MStopLoss:445-463`, `isSymbolRunning:906`): `activeRunningIds` = cụm ĐANG MỞ (thêm lúc tạo lệnh
  `:1771`, bỏ lúc đóng cụm `:1271`; sim khớp/đóng tức thì ⇒ không có trạng thái chờ/đang đóng). Coin đang giữ **đếm hạng
  (cap-then-skip) nhưng không gọi `createOrderBUY` ⇒ không qua gate, không nạp r**. Chỉ nhánh selector (sp ≠ null) nạp r
  (`AIRejectFilter.entryGate`); nhánh BIG_DOWN/DCA không nạp ⇒ không đổi.
- **Live trước 4h**: chỉ loại `BudgetManager.symbol2Pos` (vị thế thật) ⇒ coin giữ trong sổ giấy qua gate, nạp r rồi mới bị
  `book.isHolding` chặn. LEGACY bị bỏ trước khi đếm hạng (không nạp r).
- **4h** (`trading/GatePreFilter.java`, `DetectEntrySignal2TradeNormal.java:542-575, 1212-1218`):
  - nguồn "đang giữ": `c3_live + LIVE_ADAPTER=live` ⇒ sổ c3 thật (`C3LiveHook.ownedSymbols`: cụm có qty / leg chờ / đang đóng —
    xấp xỉ "cụm mở" của sim, lệch nhỏ: cụm đang đóng trong phút đó vẫn bị coi là giữ); `dry`/`c3_shadow` ⇒ sổ giấy twin;
    profile tắt (HEAD) ⇒ `symbol2Pos` y nguyên;
  - LEGACY: **đếm hạng + qua gate (nạp r) nhưng không vào** (sim không có LEGACY ⇒ symbol đó là ứng viên thường). Hệ quả:
    LEGACY trong top-24 chiếm 1 slot (giống sim về số r nạp; sim có thể vào lệnh, live thì không). Trên 242 hiện 44 LEGACY.
  - UNIVERSE_A1=1: symbol A1 loại bỏ hẳn (không đếm hạng, không gate). Sim A1 không có TF/INDEX trong dữ liệu
    (`PREREG_HO2026_NOTF` V1: "ticker A1 có 0 symbol ∈ X") ⇒ không bao giờ nạp r — khớp. Pool selector live đã lọc A1 từ trước;
    nhánh này là phòng thủ + WARN nếu xảy ra.
  - log `[GATE-PRE] … nguon= bo_dang_giu= legacy_qua_gate_khong_vao= a1_bo=` (chỉ khi > 0).
- **Replay 10-30** (`GateHeldReplay1030R4hTest`, dữ liệu `~/claude_master/gst1030`, quy ước v1.1 của `gst_l.py`): buffer
  `gate_ratio_live_2242.bin` md5 `4e29c20c…`; 299 dòng coin đang giữ trong đợt 1 (03:30–04:00) — khớp **299/299** bản ghi buffer
  theo (ts, bit float) (python khớp 296 do làm tròn r 6 chữ số; kết quả q không đổi). Lõi quantile production `GateRatioBuffer`:
  **q giờ 04 cũ 0,00950214919 → mới 0,00756445155** (bit-exact với tính độc lập); **đợt 2 (04:00–11:00, q giờ 04) = 29 pass,
  mới = CAP, CT, DOS, IDOL, IRYS, NIL, PARTI, Q** — đúng kỳ vọng, không lệch symbol nào.
  Giới hạn: replay kiểm quy ước + lõi quantile + quyết định `GatePreFilter`; vòng lặp `DetectEntrySignal2TradeNormal` (cần
  Aerospike/ONNX) không chạy trong test — kiểm ở dry bằng dòng `[GATE-PRE]`.

## 2. Seed buffer (`GATE_BUFFER_SEED`, mặc định TẮT)
- `LiveGateRollingRatio.java:108` (init), `checkSeed:162`, `applySeedFile:198`. Env: `GATE_BUFFER_SEED=<file định dạng
  gate_ratio_live.bin>`, `GATE_BUFFER_SEED_MD5=<md5 hex>` (BẮT BUỘC), `GATE_BUFFER_SEED_MAX_LAG_H` (mặc định 24).
- Kiểm: file tồn tại, md5 khớp, `GateRatioPersist` đọc sạch (0 chunk hỏng), ts tăng dần, r hữu hạn, bản ghi đầu ≤ now − (days−1) ngày,
  không ở tương lai (> now + 60 s), bản ghi cuối ≥ now − lag. Sai ⇒ `⛔ [GATE-SEED] FAIL-FAST: <lý do>` + `System.exit(2)` (deploy
  hậu kiểm thấy process chết ⇒ rollback).
- Nạp: buffer = seed (trong cửa sổ 90 ngày) + persist có ts > bản ghi cuối của seed; bỏ seed Aerospike cũ. Persist khác ⇒ sao lưu
  `<file>.preseed_<ts>` rồi viết lại gọn; restart cùng seed ⇒ idempotent (không sao lưu/viết lại). Bản ghi persist v1.1 nằm giữa
  cuối seed và lúc deploy vẫn được giữ (quy ước cũ) ⇒ agent gate nên dựng seed sát giờ deploy (lag nhỏ).

## 3. Soak user-data stream (CHỈ ĐỌC) — `c3live/soak/*`, `ops/c3live/ws_soak_242.sh`
- **Xác minh trước khi viết (an toàn với LEGACY):** (a) code LEGACY v1.1 (`v1.1/exec-probe`) và v1.2 ngoài `c3live/`: 0 nơi gọi
  `startUserDataStream/keep/close/subscribeUserDataEvent` (chỉ có trong SDK `com.binance.client`); (b) `full.log` v_t_m: 0 dòng
  listenKey/user-data; (c) socket PID 8468: Redis/Aerospike + 1 HTTPS REST, không WS. ⇒ LEGACY KHÔNG dùng user-data stream.
  Binance: POST listenKey trả key đang hiệu lực (không vô hiệu hoá người khác), PUT chỉ gia hạn, DELETE cắt mọi kết nối dùng key.
- `SoakGuard.readOnly` (Proxy): CHỈ `startUserStream` (POST) + `keepAliveUserStream` (PUT); mọi hàm khác — kể cả `closeUserStream`
  (DELETE) và mọi lệnh — ném lỗi + log. `UserStreamSoak` dùng chính máy trạng thái `UserStream` (qua `UserStream.forSink`, không
  FillAccounting), không bao giờ gọi `stop()`, kết thúc bằng `System.exit` (listenKey tự hết hạn ≤ 60′).
- Log: `[WS-SOAK] KEEPALIVE OK/LOI`, `LISTENKEY POST`, `KHE HO #n: mất … → có lại … = s; trước đó kết nối liền h (=> CAT 24h)`,
  thống kê 10′/lần, `KET THUC … KET_QUA=DAT|CHUA_DAT` (ĐẠT = thấy cắt ~24 h + kết nối lại + 0 gọi bị chặn).
- **Lệnh owner (Oracle):** `DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/ws_soak_242.sh` (chỉ kiểm) rồi bỏ `DRY=1`. Theo dõi
  `MODE=status …`, dừng sớm `MODE=stop …`. JVM riêng `/home/chuyennd/java/ws_soak`, -Xmx256m, jar r4h pin md5. **Từ chối** khi
  canary (`C3LiveCanary`) hoặc v_t_m `LIVE_ADAPTER=live` đang chạy (`stop()` của chúng DELETE listenKey ⇒ khe hở giả) —
  10-30 22:4x **canary đang chạy trên 242** ⇒ phải chờ canary xong. Thử script với 242 giả (DRY, md5 sai, LIVE_ADAPTER=live,
  chạy/status/chạy lần 2/stop) đạt.

## 4. Rò native
- `ops/OpsProcStat` + `InPlaceRefresh`: mỗi `LIVE_PROC_STAT_MIN` (60′) log `[OPS-PROC] rss_mb hwm_mb threads jvm_threads heap_used_mb
  heap_committed_mb uptime_h` (đọc `/proc/self/status`). `c3live_status.sh`: VmRSS/VmHWM/Threads hiện tại + 3 dòng `[OPS-PROC]` cuối.

## 5. Kiểm
- Code commit `de5b7e96`. `mvn -o -T 1 package` qua `flock oracle_heavy.lock` + `nice`: **883 test, 0 fail, 1 skip** (869 + 14 mới:
  GateHeldReplay1030R4hTest 1, GateSeedR4hTest 3, GatePreFilterR4hTest 3, UserStreamSoakR4hTest 4, OpsProcStatR4hTest 3).
- fake242: **TEST PASS 219/219** (r4g chạy 217/217 — số mục thay đổi theo thời gian chạy như các vòng trước 217–219).
- Jar `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4h` md5 **08112d73429e7b9c2917d4f254f6d144** (pin trong `ws_soak_242.sh`).
  `deploy_v12_dry_r4.sh` VẪN pin r4f.
- Prereg: `PREREG_PARITY_V12_DRY_ADDENDUM1.md` (research/vz-e1 `7788cce9`, sha256 `8eee6ae2…a4cb72`) — sửa §2.6 LEGACY (242 có 44)
  + luật S1-I/GV-I/P2 theo lọc trước gate; viết trước deploy.
