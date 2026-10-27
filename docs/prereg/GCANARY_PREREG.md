# GCANARY_PREREG — prereg G-CANARY cho c3_live v1.2 (CHỐT — MASTER 10-25, xem §10)

> Bản gốc: bản nháp A1 `audit/a1@479adb1f:docs/prereg/GCANARY_PREREG.md` (giữ nguyên nội dung §1–§9). Các câu hỏi [MỞ-n] đã được MASTER
> chốt ở **§10 Quyết định MASTER 10-25**; §10 có hiệu lực hơn các đề xuất trong §1–§9 nếu khác nhau.

Soạn: a1audit (Claude Opus, auditor A1), 2026-10-25, trên branch `audit/a1`. **Chưa chốt.** Đây là bản nháp để MASTER sửa/duyệt. Các chỗ
**[MỞ-n]** là câu hỏi MASTER/owner phải trả lời trước khi chốt. Nguồn: GOLIVE_SCENARIO §3 G-CANARY và §4.2 (S3), A1_AUDIT_V12 §10,
A1_DELTA_2EF §6, A1_DELTA_2G §5, A1_DELTA_2H. Mọi ngưỡng dưới đây được đặt TRƯỚC khi chạy; không tune sau khi thấy kết quả.
Một chỉ số "không đo được" (thiếu log/file) = **TRƯỢT**, không được coi là "bỏ qua".

## 1. Mục tiêu
Xác minh bằng TIỀN THẬT nhỏ, trên tài khoản con c3_live, những hành vi sàn mà mock/dry không chứng minh được:
- đặt/khớp lệnh với ký quỹ Multi-Assets;
- Algo stop (closePosition, dời, huỷ, kích, −4130, −2021);
- user-data stream;
- reconcile/restart;
- guard huỷ stop;
- lớp chặn A/B;
- đối chiếu equity;
- rate limit.

Canary **không** đo alpha/PnL và **không** quyết định size.

## 2. Điều kiện vào (tất cả phải đúng; thiếu 1 ⇒ không chạy)
1. **G-CODE ĐẠT** cho đúng commit/jar dùng ở canary: A1 ký, 0 CRIT/MAJ mở (hiện tại: v1.2/c3-live 05f55fac, jar dry pin `e1b1b7ec…`). Jar canary phải là jar
   đã audit; mọi thay đổi code sau đó cần A1 delta trước.
2. **G-PROMO v1.1 ĐẠT** (chấm 11-18 → 11-20), có file gate MASTER ký.
3. **Dry-run (G-DRY) ≥ 5 ngày liên tục sạch** với jar pin, trên 242:
   - 0 dòng `[KILLSW] LATCH` ngoài kịch bản;
   - 0 exception đường adapter;
   - 0 `[C3-LIVE-ORDER]` (lệnh thật);
   - 100 % leg giấy có `[LIVE-DRY]` tương ứng (GOLIVE §3 G-DRY);
   - 0 lần UNKNOWN_POSITION / RECON_BLOCKED không giải thích được.

   **[MỞ-1]** GOLIVE ghi G-DRY ≥ 7 ngày; brief MASTER ghi ≥ 5 ngày cho điều kiện vào canary. Đề xuất: canary được chạy sau 5 ngày sạch, song song với
   2 ngày dry còn lại; G-MICRO vẫn cần đủ 7 ngày.
4. Tài khoản con + key:
   - `golive_keys_install.sh` đã chạy; key chỉ có quyền Futures, KHÔNG có quyền rút, có IP restrict 242 (xác minh ở K0);
   - Multi-Assets BẬT, one-way, CROSS, leverage 1 cho symbol canary;
   - 0 vị thế, 0 lệnh/algo mở.
5. Ký quỹ. **[MỞ-2] Nạp đệm USDT hay giữ USDT = 0?** Pilot dự kiến chạy với 10k BFUSD, USDT = 0. Ở chế độ này phí và lỗ đã chốt làm số dư USDT âm;
   hành vi của sàn (tự quy đổi BFUSD? cảnh báo? chặn lệnh −2019?) CHƯA XÁC MINH.
   **Khuyến nghị:** canary chạy ĐÚNG cấu hình pilot (USDT = 0) để xác minh nó, và chuẩn bị sẵn phương án B: nạp 50 USDT nếu K1 hoặc K8 TRƯỢT vì USDT âm / −2019.
   Nếu owner muốn an toàn trước, có thể nạp sẵn 50 USDT; khi đó K8 phải ghi rõ cấu hình pilot CHƯA được kiểm.
6. Không trong khung cấm giờ (`time_ok`); owner thức và có mặt suốt phiên (≈ 2–3 h); MASTER có mặt để quyết khi TRƯỢT.
7. Kill-switch tài khoản con: file latch/đỉnh sạch (dry → live đổi nhãn adapter; latch khác nhãn ⇒ owner reset có chủ đích trước canary).

## 3. Phạm vi
- **Symbol: 1 symbol**, chọn bằng LUẬT do script tính lúc chạy (không chọn theo PnL hay cảm tính).
  Luật đề xuất: trong `SymbolUniverseLive` buyable (TRADING, PERPETUAL, USDT, underlyingType=COIN, không TradFi/INDEX/non-ASCII,
  deliveryDate > now + 30 ngày), thoả MIN_NOTIONAL ≤ 10 USDT, tick/giá ≤ 0,01 %, không nằm trong tập LEGACY tài khoản chính, không có vị thế của bot;
  lấy symbol có `quoteVolume` 24h lớn nhất; hoà thì theo thứ tự chữ cái. Script in lý do chọn + dữ liệu thô.
  **[MỞ-3]** GOLIVE §3 ghi 3 symbol; brief MASTER ghi 1. Đề xuất: 1 symbol chính cho K1–K8. Thêm symbol thứ 2 (cùng luật, hạng 2) chỉ cho K7b
  (lớp chặn B: symbol này phải vào được trong lúc symbol 1 bị chặn).
- **Size:** 20 USDT notional mỗi lệnh (leverage 1). Vị thế tối đa cùng lúc 40 USDT. **Rủi ro tổng < 2 USDT** (phí + trượt + biến động), có trần cứng:
  lỗ đã chốt luỹ kế ≥ 2 USDT ⇒ dừng phiên (TRƯỢT "chi phí").
- **Nguồn lệnh. [MỞ-4] Đề xuất 2 pha:**
  - **Pha A (canary, bắt buộc):** lệnh do kịch bản bắn tay qua script owner, KHÔNG từ tín hiệu thật. Chạy bằng công cụ canary JVM riêng (`C3LiveCanary`, như GOLIVE
    S3) dùng chính các lớp của jar đã audit (C3LiveClient, LiveBookC3, executor, TrailingStopManager, OwnStopGuard, Reconciler, FlatConfirm, UserStream), sổ/latch
    riêng thư mục `run/canary/`. KHÔNG đụng JVM c3_live dry đang chạy.
  - **Pha B (tín hiệu thật, cap nhỏ):** KHÔNG làm trong canary. Pha này chính là G-MICRO (S4 `golive_micro_on.sh`, PILOT_EQUITY nhỏ). Lý do: đường tín hiệu thật đã có
    G-DRY bao phủ; trộn vào canary làm kịch bản không tái lập.

## 4. Kịch bản (chạy tuần tự; TRƯỢT ⇒ hành động ghi ở từng mục; mặc định khi TRƯỢT: dừng, `golive_canary_flatten.sh`, gửi log MASTER)

Mọi bước ghi vào `run/canary/canary_<TS>.jsonl`: timestamp ms, request (không key/signature), HTTP status, mã lỗi, các trường response nêu dưới,
header `X-MBX-USED-WEIGHT-1M` và `X-MBX-ORDER-COUNT-10S/1M`, sự kiện stream (raw, đã che listenKey).

| K | bước | quan sát phải ghi | ĐẠT (định lượng) | khi TRƯỢT |
|---|---|---|---|---|
| **K0** chỉ đọc | account v3, positionRisk v3, multiAssetsMargin, positionSide/dual, symbolConfig (tất cả + symbol canary), exchangeInfo, apiRestrictions (nếu có), listenKey + WS (URL 1, URL 2), keepAlive, chạy 65′ | `totalMarginBalance`, `assets[]` (BFUSD/USDT), `positions[]` (đủ 10 trường docs), `multiAssetsMargin`, `dualSidePosition`, `marginType`, `leverage`, URL WS nào mở, thời gian nối, keepAlive OK | tmb ≈ số đã nạp (±1 %); multiAssets=true; dual=false; CROSSED/1x; 0 vị thế/0 lệnh/0 algo; `account().positions` và `positionRisk` cùng rỗng; WS mở ≤ 5 s qua ít nhất 1 URL; keepAlive 2 lần OK; quyền rút = tắt (nếu đọc được) | dừng; không có lệnh nào được gửi |
| **K1** vào lệnh | MARKET BUY 20 USDT qua executor (cid `c3-…`, RESULT) | `status`, `executedQty`, `avgPrice`, `orderId`; stream `ORDER_TRADE_UPDATE` (X, z, ap, n, N, rp), `ACCOUNT_UPDATE` (B[], P[]); số dư USDT/BFUSD trước/sau; C2 có dấu (fill/ref−1) | response FILLED với executedQty = qty gửi; stream ≤ 2 s (p100); sổ CONFIRMED khớp sàn (qty, avg ±1 tick); KHÔNG −2019/−4164; ghi được hành vi số dư USDT sau phí | TRƯỢT vì −2019/USDT âm ⇒ phương án B [MỞ-2], A1 + MASTER xem; lỗi khác ⇒ flatten, dừng |
| **K2** stop | (a) đặt STOP_MARKET closePosition MARK_PRICE ở −20 % (A); (b) dời lên −19 % theo đúng đường trailing (đặt B → xác nhận NEW → huỷ A); (c) thử đặt closePosition C cùng chiều khi B còn (ghi −4130 hay chấp nhận); (d) nếu −4130 ⇒ đường qty+reduceOnly | `algoId`, `clientAlgoId`, `algoStatus` trong response; `openAlgoOrders` sau MỖI bước; mã lỗi bước (c) | sau mỗi lần dời: `openAlgoOrders` có **đúng 1** stop c3s- NEW của symbol (trừ khoảnh khắc chuyển); response `algoStatus=NEW`; `queryStop` theo clientAlgoId khớp; bước (c) ghi rõ kết quả (đây là dữ liệu, không phải tiêu chí) | còn 0 stop khi vị thế ≠ 0 ở bất kỳ thời điểm đo nào ⇒ TRƯỢT nặng: flatten, dừng, A1 |
| **K3** −2021 | đặt SELL STOP_MARKET trigger CAO hơn mark | mã lỗi, hành động bot | sàn trả −2021 (hoặc mã tương đương, ghi lại); bot đóng MARKET reduce-only (TRAILING_IMMEDIATE), vị thế 0, 0 stop | sai mã ⇒ ghi lại, A1 cập nhật ErrorMapper; vị thế còn ⇒ flatten |
| **K4** stop kích thật | mở lại 20 USDT; đặt stop ở mark −0,15 % (hoặc đợi biến động); chờ kích | `ALGO_UPDATE` (X, caid, ai), `ORDER_TRADE_UPDATE` của lệnh MARKET sinh ra (c = cid?, ot), `ACCOUNT_UPDATE` pa=0; sau đó `openAlgoOrders` | sổ đóng cụm, lý do **TRAILING** (không phải EXTERNAL); 0 stop mồ côi sau ≤ 30 s; ledger 1 dòng; ghi: sàn có tự huỷ/hết hạn stop closePosition còn lại khi vị thế = 0 không | lý do EXTERNAL ⇒ MIN (cập nhật nhận diện), không dừng; stop mồ côi > 60 s ⇒ TRƯỢT |
| **K5** time-stop/X14 | mở 20 USDT, gọi `closeCluster(TIME_STOP_168H)` qua công cụ canary | lệnh `c3x-…` reduceOnly, FILLED, huỷ stop qua guard | vị thế 0, 0 algo, sổ xoá cụm, guard ghi CANCELLED (positionRisk + account phẳng) | flatten, dừng |
| **K6** restart giữ sổ | mở 20 USDT + stop đã arm; kill JVM canary; khởi động lại | report startup reconcile | 12 trường cụm khôi phục bit-identical; stop không trùng (`openAlgoOrders` = 1); 0 lệnh mới trước dòng "reconcile khoi dong" | flatten, dừng, A1 |
| **K6b** sổ mất | như K6 nhưng đổi tên sổ trước khi khởi động lại | report startup: `orphanKept`, `unknownPositions` | stop c3s- **VẪN CÒN** trên sàn; symbol vào UNKNOWN (A); Telegram; 0 huỷ stop; sau đó owner dùng `golive_canary_flatten.sh` đóng tay | stop bị huỷ ⇒ TRƯỢT nặng (MAJ-3 hồi quy), dừng toàn bộ lộ trình |
| **K7** mất stream | khi có vị thế + stop: chặn WS (URL sai đứng đầu / đóng socket) | fallback REST mỗi 10 s, xoay URL, Telegram sau 5′, bù REST khi nối lại | 0 cụm/stop bị xoá sai; khi nối lại sổ = sàn; thời gian phát hiện ≤ 15 s | flatten, dừng |
| **K7b** lớp chặn B | symbol 1 vừa chốt (K4/K5) trong khi giả lập positionRisk lỗi/trễ (công cụ canary chèn lỗi đọc, KHÔNG đụng sàn); thử vào 1 leg symbol 2 | trạng thái blocks/symBlocks theo thời gian; số phút chặn | symbol 2 **vào được** trong lúc (B); symbol 1 chặn tới khi 2 lần đọc phẳng + account phẳng; không có chặn toàn hệ (A) nếu < 10′; ≥ 10′ ⇒ A + Telegram | symbol 2 bị chặn toàn hệ dưới 10′ ⇒ TRƯỢT (alpha) ⇒ A1 |
| **K8** đối chiếu | sau K1–K7b: hourly reconcile + equity | `bookEquity`, `tmb`, `lech`, phí (USDT/BNB?), funding, chuyển tiền, số dư USDT/BFUSD | \|equity sổ − tmb\| / tmb ≤ 1 %; sổ ↔ positionRisk 100 %; 0 vị thế, 0 algo cuối phiên | lệch > 1 % không giải thích được ⇒ TRƯỢT, MASTER |

## 5. Tiêu chí tổng G-CANARY (tất cả phải ĐẠT)
1. **0 lệnh trùng cid** (đếm từ `allOrders`/trades theo clientOrderId, độc lập với log bot).
2. **0 stop mồ côi** sau mỗi kịch bản (đo `openAlgoOrders` ≤ 60 s sau khi cụm đóng); **0 thời điểm vị thế ≠ 0 mà 0 stop** khi cụm đã arm.
3. **Sổ = sàn 100 %** (qty, avgPrice ±1 tick) ở mọi điểm đo.
4. **0 latch kill-switch ngoài kịch bản** (C1–C6, A40, STATE).
5. **Weight**: max `X-MBX-USED-WEIGHT-1M` < 50 % giới hạn exchangeInfo (2400 ⇒ < 1200); 0 HTTP 429/418.
6. **0 bí mật trong log**: grep log JVM + jsonl + log script không có API key, secret, `signature=`, listenKey đầy đủ, token Telegram.
7. **Lớp chặn**: ghi số phút (A) và (B) từng lần; (A) chỉ được xuất hiện ở K6b và K7b ≥ 10′. (B) kéo dài > 10′ mà không leo thang ⇒ TRƯỢT.
8. **Độ trễ leg**: quyết định → gửi → FILLED (p50/p100) từ log; ghi để so G-EXEC (không phải ngưỡng ĐẠT, chỉ thông tin — không tune).
9. **Chi phí** ≤ 2 USDT (phí + lỗ đã chốt).
10. Mọi điểm CHƯA XÁC MINH ở §7 có kết quả ghi lại (giá trị/mã cụ thể).

Kết quả: `docs/result/GCANARY_<date>.md` + jsonl. A1 kiểm độc lập jsonl trước khi MASTER ký `GOLIVE_GATE_CANARY.ok`.
Lặp lại canary (bản rút gọn K0, K1, K2, K4, K6) sau MỌI thay đổi jar trước micro-live.

## 6. Script owner một lệnh cần viết (chưa viết code; theo luật GOLIVE §4.1: DRY=1, time_ok, YES, backup, không in secret, log)
| tên | chức năng |
|---|---|
| `golive_keys_install.sh` (S2, đã có trong GOLIVE) | nhập key bằng `read -s`, ghi `keys.env` 600 root trên 242, kiểm chỉ-đọc K0 |
| `golive_canary_preflight.sh` | K0 chỉ đọc + tính symbol canary theo luật §3, in lý do chọn; kiểm điều kiện vào §2 (file gate, jar md5, dry sạch) |
| `golive_canary.sh` (S3) | chạy công cụ `C3LiveCanary` (JVM riêng, thư mục `run/canary/`) K1→K8 tuần tự; dừng ở bước TRƯỢT đầu tiên; YES trước K1; tự đóng hết khi TRƯỢT |
| `golive_canary_step.sh <Kx>` | chạy lại 1 kịch bản đơn lẻ (sau khi MASTER cho phép) |
| `golive_canary_flatten.sh` | khẩn cấp: đóng hết vị thế tài khoản con reduce-only + huỷ stop c3s- (qua guard: chỉ khi vị thế đã 0) + in trạng thái cuối |
| `golive_canary_report.sh` | kéo jsonl + log về Oracle, tính tiêu chí §5 (đếm cid từ `allOrders`, max weight, grep bí mật), sinh bảng ĐẠT/TRƯỢT cho MASTER/A1 |
| `golive_canary_cleanup.sh` | xác nhận 0 vị thế / 0 algo / 0 lệnh; đổi tên `run/canary/` có TS; không đụng JVM dry |

## 7. Rủi ro và điểm CHƯA XÁC MINH — xác minh ở bước nào
| điểm | rủi ro | bước |
|---|---|---|
| Multi-Assets BFUSD, USDT = 0: lệnh có bị −2019, USDT âm xử lý thế nào | CAO | K0 (số dư), K1, K8 |
| Algo API: closePosition thứ 2 cùng chiều (−4130?), `algoStatus` trong response, từ chối bất đồng bộ | CAO | K2 |
| Sàn có tự huỷ stop closePosition khi vị thế = 0 (quyết định tần suất "cụm ma") | TB | K4, K5 |
| URL WS private, định dạng ORDER_TRADE_UPDATE / ACCOUNT_UPDATE / ALGO_UPDATE, cid lệnh MARKET khi stop kích | TB | K0, K1, K4 |
| −2021 khi trigger vượt mark | THẤP–TB | K3 |
| `/fapi/v3/account` positions khớp positionRisk; symbolConfig không tham số trả đủ symbol | TB | K0 |
| Weight endpoint (số bảo thủ trong code) và header | THẤP | mọi bước (§5.5) |
| Phí trả bằng tài sản nào; đối chiếu equity khi USDT âm | TB | K1, K8 |
| Lớp chặn B/A ngoài đời (REST trễ thật) | TB (alpha) | K7b |
| Key: quyền rút tắt, IP restrict (`apiRestrictions` CHƯA XÁC MINH là đọc được bằng key thường) | CAO (an toàn vốn) | K0 / S2 |

Rủi ro vận hành của chính canary:
- (a) canary JVM chạy cạnh JVM dry trên 242 — phải dùng thư mục/sổ/latch riêng và KHÔNG ghi Aerospike;
- (b) owner phải có mặt;
- (c) biến động lớn trong phiên ⇒ trần lỗ 2 USDT dừng phiên;
- (d) công cụ chèn lỗi (K7/K7b) chỉ được tác động phía client, không gửi request lạ lên sàn.

## 8. Lệch so với GOLIVE_SCENARIO §3 G-CANARY (để MASTER quyết)
- Ngân sách: GOLIVE ~200 USDT tài khoản con / 3 symbol; bản này 1 symbol (+1 cho K7b), 20 USDT/lệnh, ≤ 40 USDT mở. Tài khoản con đã có 10k BFUSD, nên đây là trần **lệnh**, không phải số dư.
- Thêm K2(c), K3, K6b, K7, K7b, K8 so với chuỗi 8 bước của GOLIVE (do A1 2a–2h phát hiện).
- [MỞ-5] "Tiêm lỗi timeout sau khi gửi" (GOLIVE bước 5, kiểm 0 lệnh trùng): đề xuất làm ở phía client (công cụ canary giả lập mất response sau khi sàn nhận) trong K1 —
  cần MASTER đồng ý vì là lệnh thật.

## 9. Câu hỏi mở cho MASTER (tóm tắt)
- [MỞ-1] Dry ≥ 5 hay ≥ 7 ngày trước canary.
- [MỞ-2] USDT = 0 hay nạp đệm (khuyến nghị: USDT = 0, phương án B 50 USDT).
- [MỞ-3] 1 hay 3 symbol (khuyến nghị: 1 + 1 cho K7b).
- [MỞ-4] Pha B tín hiệu thật trong canary hay để G-MICRO (khuyến nghị: G-MICRO).
- [MỞ-5] Tiêm lỗi timeout bằng lệnh thật trong K1.
- Ai viết `C3LiveCanary` + script §6, và A1 audit chúng trước canary (bắt buộc — đây là code mới gửi lệnh thật).

## 10. Quyết định MASTER 10-25 (CHỐT — thay cho các mục [MỞ-n] ở trên)

Ghi bởi agent v12exit theo chỉ thị MASTER (round 3, 2026-10-25), TRƯỚC khi viết bất kỳ dòng code canary nào. Từ đây prereg này là bản CHỐT; mọi
ngưỡng ở §2–§5 giữ nguyên, không tune sau khi thấy kết quả.

- **MỞ-1 → CHỐT:** canary chạy sau **≥ 5 ngày dry sạch** (§2.3) với jar pin. G-MICRO vẫn yêu cầu **đủ 7 ngày** G-DRY.
- **MỞ-2 → CHỐT:** giữ **USDT = 0** (đúng cấu hình pilot, 10k BFUSD). Phương án B (owner nạp 50 USDT) **chỉ** dùng khi K1 hoặc K8 TRƯỢT vì −2019
  hoặc số dư USDT âm; khi đó MASTER quyết chạy lại K1/K8 và ghi rõ "cấu hình pilot USDT = 0 KHÔNG đạt".
- **MỞ-3 → CHỐT:** **1 symbol chính** (K1–K8) + **1 symbol phụ chỉ cho K7b**. Cả hai do LUẬT §3 tính bằng script (`canary_preflight`): hạng 1 = chính,
  hạng 2 = phụ. Không chọn tay; công cụ canary từ chối mọi lệnh ngoài 2 symbol này.
- **MỞ-4 → CHỐT:** **không có Pha B** trong canary. Tín hiệu thật để dành cho G-MICRO.
- **MỞ-5 → CHỐT (CHO PHÉP):** trong K1 được tiêm timeout phía client **sau khi** gửi đúng 1 lệnh MARKET 20 USDT (sàn nhận lệnh; client giả mất
  response) để kiểm đường `queryOrder` theo cid + idempotency (0 lệnh gửi lại, 0 cid trùng). **Chỉ 1 lần** cho cả phiên, cờ riêng
  `CANARY_INJECT_TIMEOUT=1`, **mặc định TẮT**; công cụ ghi đã dùng vào trạng thái và từ chối lần thứ 2.
- **Người viết:** agent v12exit viết `C3LiveCanary` (package `c3live.canary`) + script owner ở `ops/c3live/canary/`; **A1 audit bắt buộc**
  trước khi chạy canary.

Ánh xạ tên script §6 → tên thật (ops/c3live/canary/):

| §6 | script |
|---|---|
| `golive_keys_install.sh` | `c3live_keys_install.sh` |
| `golive_canary_preflight.sh` | `canary_preflight.sh` |
| `golive_canary.sh` | `canary.sh` |
| `golive_canary_step.sh <Kx>` | `canary_step.sh <Kx>` |
| `golive_canary_flatten.sh` | `canary_flatten.sh` |
| `golive_canary_report.sh` | `canary_report.sh` |
| `golive_canary_cleanup.sh` | `canary_cleanup.sh` |

Giới hạn CỨNG trong code canary (không ghi đè được bằng config): notional ≤ 25 USDT/lệnh (lệnh chuẩn 20 USDT), tổng mở ≤ 40 USDT, trần lỗ
2 USDT (chạm ⇒ tự flatten rồi dừng phiên), chỉ 2 symbol do luật chọn, không chạm vị thế/lệnh ngoài 2 symbol đó, từ chối chạy khi runtime
c3_live chính (adapter live) đang giữ lock tài khoản con, từ chối khi tài khoản có vị thế/lệnh của symbol khác.

## §ADD-1 CANARY-EARLY (MASTER 10-27, owner duyệt)

Ghi bởi agent v12exit theo chỉ thị MASTER (round 3b, 2026-10-27), TRƯỚC khi viết code/script mode early. §ADD-1 có hiệu lực hơn §2 cho
riêng canary-early; mọi mục khác (§1, §3–§7, §10) giữ nguyên, không tune sau khi thấy kết quả.

- **Phạm vi:** canary-early chỉ kiểm **CƠ CHẾ sàn** (K0–K8, K6b, K7b) bằng lệnh do kịch bản bắn tay; **không** chạy tín hiệu strategy, không
  dùng JVM bot, không đọc/ghi Aerospike/Redis/symbol_mapper. Chạy được NGAY (owner duyệt 10-27), trước khi deploy dry và trước khi cửa sổ
  promotion v1.1 đóng (2026-11-18).
- **Điều kiện vào KHÔNG áp cho canary-early:** §2.2 "G-PROMO v1.1 ĐẠT" và §2.3 "dry ≥ 5 ngày sạch" (MỞ-1). Hai điều kiện này **vẫn áp nguyên
  cho G-MICRO** (và cho G-CANARY bản chuẩn sau deploy dry).
- **Điều kiện vào THAY THẾ (tất cả phải đúng; thiếu 1 ⇒ không chạy):**
  1. G-CODE ĐẠT cho đúng jar canary-early; **A1 audit vòng 3 + 3b ĐẠT** (MASTER tạo file gate `~/claude_master/deploy/gates/GOLIVE_GATE_CODE_V12.ok`
     trên Oracle SAU khi A1 ĐẠT; thiếu file ⇒ script từ chối).
  2. Canary chạy ở **thư mục riêng** `/home/chuyennd/java/c3canary` trên 242 (jar riêng, sổ/state/journal/lock riêng `run/`), **JVM riêng**,
     env sạch (không `LIVE_PROFILE` / `TRADING_PROFILE` / `LIVE_TS_MKT_EXT`).
  3. **v_t_m không bị đổi:** md5 jar (`target/binance-java-sdk-1.2.4.jar`), md5 `conf/env.sh` + `bin/start.sh`, PID process bot chụp trước phiên
     và so TRƯỚC + SAU mỗi bước; lệch ⇒ dừng ngay + flatten (TRƯỢT "v_t_m"). v_t_m phải đang chạy `LIVE_PROFILE=c3_shadow` +
     `SHADOW_NO_PUSH=true`, không `LIVE_ADAPTER=live` (tài khoản chính không bị đụng).
  4. **RAM trống 242 (MemAvailable) ≥ 1 GB** trước khi start (install/K0 và đầu phiên); trước mỗi bước sau đó ≥ 768 MB, thấp hơn ⇒ dừng +
     flatten.
  5. Các mục còn lại của §2 giữ nguyên: key/tài khoản con (§2.4), USDT = 0 + phương án B (§2.5, MỞ-2), time_ok + owner có mặt (§2.6),
     tài khoản con 0 vị thế / 0 lệnh / 0 algo (K0).
- **Giữ nguyên:** mọi giới hạn cứng (§10), kịch bản §4, tiêu chí tổng §5, MỞ-1..5 (MỞ-5 tiêm timeout mặc định TẮT).
- **Phương án B (MỞ-2):** USDT = 0 và K1 TRƯỢT vì −2019 ⇒ dừng; owner nạp 50 USDT vào tài khoản con; MASTER quyết chạy lại và ghi "cấu hình
  pilot USDT = 0 KHÔNG đạt".
- **Kết quả:** 1 file txt trên Oracle (`~/claude_master/canary/canary_early_result_<TS>.txt`, không chứa key) cho MASTER/A1; A1 kiểm jsonl
  độc lập trước khi MASTER ký kết quả canary-early. Kết quả canary-early **không** thay G-CANARY bản chuẩn trước G-MICRO nếu jar đổi
  (§5: lặp lại bản rút gọn sau mọi thay đổi jar).
