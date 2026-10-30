# ROUND 4i — v1.2/c3-live: chẩn đoán K7b TRƯỢT (canary 3k 10-30) + jar r4i + gói canary_3l

Trên `6cb98d2b` (4h). Jar r4i = 4g + 4h + 4i. Script deploy dry VẪN pin r4f. Chưa push.

## 1. Chẩn đoán K7b — (b) lỗi CHECKER canary, production đúng
Bằng chứng (242 `c3canary/run/canary/canary_jvm.log`, journal `canary_20261030_232923_step_K7B.jsonl`):
- 23:30:01.749 `K7B_INJECT_ON` (positionRisk lỗi phía client); 01.761 Flattener `positions() loi … => dung qty trong so`.
- c3x-ZECUSDT gửi ~01.764, khớp sàn `T=…801806`, CALL_W `status=FILLED executedQty=0.016` (= qty cụm 0.016).
- Sàn TỰ kết thúc stop closePosition: ALGO_UPDATE `c3s-ZECUSDT-29889630-1 X=EXPIRED T=…801810` (+4 ms sau khớp; WS tới 02.212).
- 01.952 sổ đóng cụm; 02.059 `stop c3s-: 1 xu ly, 0 GIU` — `OwnStopGuard.cancelOwnStopGuarded` (`recon/OwnStopGuard.java:68-83`)
  đọc openStops (đọc này KHÔNG bị tiêm lỗi) thấy stop đã final ⇒ `GONE`, không cần đọc positionRisk ⇒ không có stop nào bị GIỮ.
- Lớp (B) chỉ sinh khi guard GIỮ stop (`Reconciler.syncKnownKept`) hoặc positionRisk còn vị thế cho symbol vừa chốt
  (`Reconciler.unknownCheck:581-598`) ⇒ đúng thiết kế: có bằng chứng phẳng dương (c3x- FILLED đủ qty + sàn hết hạn stop
  closePosition, vốn chỉ xảy ra khi vị thế về 0) thì KHÔNG cần chặn symbol. Checker cũ (`CanaryEngine.k7b`) đòi (B) vô điều kiện —
  kịch bản viết khi chưa biết sàn tự EXPIRE stop closePosition (phát hiện 10-29 ở K5, 3k R1).

## 2. Phụ thuộc thứ tự sự kiện (như K5)
CÓ: kết quả phụ thuộc đua giữa REST openStops của guard và lúc sàn EXPIRE stop (~4 ms sau khớp). Guard đọc TRƯỚC ⇒ thấy stop mở ⇒
đọc positionRisk (lỗi tiêm) ⇒ GIỮ ⇒ (B) (đường mock cũ). Đọc SAU ⇒ GONE ⇒ không (B) (đường thật 10-30). Mốc chứng minh dùng
`firstSentMs` (như K5 4g), không dùng ts ACK; sự kiện WS tới SAU lúc kiểm (02.212 > 01.952) ⇒ checker chờ có giới hạn
(`fillEventWaitMs`).

## 3. Sửa (chỉ canary checker)
- `CanaryEngine.k7b`: chụp stop/qty cụm trước khi đóng; sau khi đóng chấp nhận (i) `KEPT_B` (như cũ) hoặc (ii) `EXCHANGE_TERMINAL`
  = `stopEndExchangeReject` (caid đúng stop cụm, stop closePosition, ALGO_UPDATE CANCELED/EXPIRED sau `firstSentMs` của c3x-)
  VÀ `k7bCloseFull` (c3x- FILLED, executedQty ≥ qty cụm). Không có bằng chứng ⇒ vẫn TRƯỢT (fail-closed). Data thêm `s1.stopEnd`,
  `s1.stopEndWhy`, `s1.closeFull`, `s1.closeSince`. Phần còn lại K7b (symbol phụ vào được, không (A) < 10′, gỡ chặn, dọn) giữ nguyên.
- Test `CanaryK7bExchangeExpiryR4iTest` (4): tái hiện đúng chuỗi 10-30 bằng mock `expireStopsOnSellFill` (sàn EXPIRE stop ngay
  sau khớp SELL) ⇒ trước sửa b1=false ⇒ TRƯỢT; sau sửa ĐẠT với `EXCHANGE_TERMINAL`; đường cũ (stop còn mở) vẫn `KEPT_B` ĐẠT;
  không bằng chứng ⇒ vẫn bị từ chối.
- **Prereg G-CANARY**: tiêu chí K7b đổi (chấp nhận đường (ii)) ⇒ MASTER cần ADDENDUM trước khi chạy canary_3l.

## 4. Kiểm, jar, gói
- `mvn -o -T 1 package` (lock): **887 test, 0 fail, 1 skip**. fake242: xem báo cáo.
- Jar `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4i` md5 **2487acdb3a7fe770db27f949a6983156**; pin trong `ops/c3live/canary/canary_lib.sh`
  (`CANARY_JAR`, `CANARY_JAR_MD5`) như cách gói 3k.
- Gói `~/claude_master/canary_3l/ops/c3live/canary` = bản sao y repo (diff rỗng). KHÔNG chạy canary.
- Lệnh owner dự kiến (SAU A1 + ADDENDUM prereg + file gate MASTER): `CANARY_RESET=1 bash ~/claude_master/canary_3l/ops/c3live/canary/canary_early_all.sh`.
  Lỗ cộng dồn hiện 0,2587 USDT (trần 4).
