# SOAK user-data stream — ADDENDUM R4l: bài thử KẾT NỐI LẠI CƯỠNG BỨC (~1 h, chỉ đọc)

Ghi TRƯỚC khi sửa code và TRƯỚC khi chạy (MASTER duyệt 2026-11-02). Không nới tiêu chí sau khi thấy kết quả.

## Lý do
Soak 26 h (`ws_soak_242.sh`, jar r4j, 2026-10-31 14:49 → 11-01 16:49): `connect=1 down=0`, keepAlive ok=51 loi=0, khe_ho=0,
0 DELETE — **sàn không cắt kết nối lần nào** ⇒ `KET_QUA=CHUA_DAT`; đường ngắt → kết nối lại của `UserStream` (production)
chưa được chứng minh trên sàn thật trước micro-live.

## Bài thử
- Lệnh: `SOAK_HOURS=1.1 SOAK_FORCE_CLOSE_MIN=10 bash ops/c3live/ws_soak_242.sh` (jar soak RIÊNG `…jar_v12_soak_r4l`;
  jar production r4j `ba71eab2` không đổi). Chỉ đọc: SoakGuard chỉ cho POST/PUT listenKey (chặn DELETE và mọi gọi khác).
- `UserStreamSoak` bọc `UserStream.Connector` production (okhttp): ở phút 10, 20, …, 60 (**6 lần**), chỉ khi đang CONNECTED
  và lần trước đã kết nối lại, client gọi `Socket.close()` của socket hiện tại (okhttp close 1000). Sàn trả close frame ⇒
  `onClosing` ⇒ `Listener.onClosed` ⇒ `UserStream.closed` ⇒ `markDown` ⇒ kết nối lại với backoff — **đúng code production,
  không sửa `UserStream.java`**. listenKey giữ nguyên (không POST mới).
- Đo: `reconnect_ms` = từ lúc gọi close đến `onOpen` của socket mới (listener bọc). Khe hở sự kiện = `SoakGapMonitor`
  (mẫu 1 s, như soak 26 h).

## Tiêu chí ĐẠT (tất cả; thiếu 1 ⇒ CHƯA ĐẠT)
1. Đóng cưỡng bức **6** lần và kết nối lại thành công **6/6**.
2. Thời gian kết nối lại **p100 ≤ 10 s**.
3. Khe hở sự kiện: số khe hở ≤ 6 (không có khe hở ngoài kế hoạch); khe hở lớn nhất ≤ min(10 s, p100 kết nối lại + 1 s
   — độ phân giải mẫu 1 s).
4. listenKey **không bị DELETE**: SoakGuard `chan=0` (0 gọi ngoài POST/PUT listenKey).
5. keepAlive lỗi = 0 và listenKey POST lỗi = 0.
6. Process thoát sạch: cuối phiên `state=CONNECTED`, dòng `[WS-SOAK] KET THUC … KET_QUA=DAT`, JVM thoát mã 0,
   `MODE=status` báo `KHONG CHAY`, không còn process `UserStreamSoak` trên 242.

`KET_QUA` trong log do code tính theo đúng 1–5 (+ `state=CONNECTED`); mục 6 kiểm bằng `MODE=status` sau phiên.

## Giới hạn (ghi rõ)
- Đóng phía client ≠ sàn cắt ở 24 h. Hai trường hợp cùng đi vào `Listener.onClosed` ⇒ `UserStream.closed` (nhánh
  `onClosing` của okhttp). Nhánh `onFailure` (mất mạng / TCP reset) **không** được bài này chứng minh trực tiếp
  (đã có unit test `UserStream`).
- Nếu sàn không trả close frame, okhttp hủy sau 60 s ⇒ `onFailure` ⇒ vẫn kết nối lại nhưng > 10 s ⇒ CHƯA ĐẠT (đúng: báo
  MASTER, không chạy lại để "cầu may").

## An toàn vận hành
Không chạy song song với canary (Oracle: `canary_early_*`/`canary_step`/`canary.sh`; 242: JVM `C3LiveCanary`) hay job
deploy/rollback (`deploy_v12_dry_r4`, `deploy_ingest*`, `rollback_*`, khóa deploy dry); script TỪ CHỐI (FORCE=1 bỏ qua — không khuyến nghị).
