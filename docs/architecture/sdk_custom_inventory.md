# Inventory custom trong SDK vendored `com/binance/client/**` (khảo sát 2026-07-04, master)

## Bối cảnh
SDK là fork có SỬA — không phải thư viện nguyên bản. Các fix sinh ra từ sự cố thực (dấu vết AGLD nằm trong
git history: f202486/77fd32d..., code hiện tại không còn hardcode AGLD). Tài liệu này là căn cứ trước khi
bất kỳ ai định "thay lib chuẩn" hay "xoá code SDK".

## NHÁNH SỐNG — custom đang phục vụ live 242 (TUYỆT ĐỐI không đụng thiếu suy nghĩ)
| File | Custom | Vì sao sống còn |
|---|---|---|
| `impl/RestApiInvoker.java` | OkHttpClient: `followRedirects(false)` + `followSslRedirects(false)` (comment gốc: "QUAN TRỌNG NHẤT") · timeout connect/read/write 10s · pingInterval 20s | Chống treo/chuyển hướng bất thường khi đặt lệnh; timeout chặt cho vòng lệnh |
| `impl/SyncRequestImpl.java` | (1) `builder.delete()` cho DELETE — comment gốc: "Bắt buộc phải có thì mới HỦY được [lệnh]" (2) **`postAlgoOrder`** — method custom HOÀN TOÀN không có trong SDK gốc, dùng cho stop-loss ALGO (STOP_MARKET) (3) xử lý riêng parse `ExchangeInformation` | Huỷ lệnh + stop-loss là đường sống của hệ long-only không hard-SL |
| `SyncRequestClient.java` | khai báo `postAlgoOrder` | interface của (2) |
| `impl/BinanceApiInternalFactory.java`, `impl/utils/Channels.java`, `constant/Constants.java` | sửa nhỏ (wiring/hằng) | đang trong chuỗi gọi ClientSingleton → SyncRequestImpl |

## Tầng gọi liên quan (chuyennd — ngoài SDK nhưng cùng chuỗi "loop đặt lệnh khi lỗi")
`helper/OrderHelper.java` + `SymbolOrderLockingManager`: bắt mã lỗi Binance cụ thể —
`-4400` reduce-only → khoá symbol · `-1008` throttle → khoá + **sleep 1.5s chống ban IP** (comment gốc "CỰC KỲ QUAN TRỌNG") ·
`-4411` TradFi-Perps agreement → khoá chống retry-spam. Đây chính là "check loop đặt lệnh khi lỗi".

## NHÁNH CHẾT (34 class unreachable — TASK-127 flag, chưa xoá)
`impl/RestApiRequestImpl.java` (REST-impl SDK gốc — bị SyncRequestImpl custom THAY THẾ hoàn toàn, 0 caller) ·
`ChannelParser`, `ApiSignature`, `InternalUtils` (một phần), `ResponseCallback` · ~29 enum không reference tĩnh.

## ĐÁNH GIÁ (khuyến nghị master)
1. **Thay lib chuẩn (binance-futures-connector): KHÔNG.** Phải port lại 3 fix sống còn + hành vi hiện tại đã
   tôi luyện qua sự cố tiền thật; lợi ích = 0 tính năng mới; rủi ro regression tầng đặt lệnh. Không sửa thứ
   đang chạy đúng ở tầng tiền thật.
2. **Xoá nhánh chết: chỉ nên tỉa RẤT hạn chế nếu muốn** — `RestApiRequestImpl` (+ ChannelParser/ApiSignature
   nếu websocket cũ xác nhận không dùng) là an toàn nhất; **GIỮ toàn bộ enum** (rẻ, có rủi ro Gson/reflection
   deserialize không thấy bằng grep tĩnh). Phương án 0-rủi-ro: giữ nguyên cả nhánh — code nằm im không tốn gì.
3. Mọi thay đổi vùng này (nếu có) phải: branch riêng + review Uni + KHÔNG deploy 242 cho tới khi test huỷ-lệnh
   + stop-loss trên testnet/small-capital.

## QUYẾT ĐỊNH (Uni, 2026-07-04 đêm)
GIỮ SDK vendored nguyên trạng — KHÔNG thay lib chuẩn, KHÔNG xoá nhánh chết (kể cả RestApiRequestImpl/enum).
Lý do: 3 fix sống còn + hành vi đã tôi luyện qua sự cố tiền thật; mọi thay đổi tương lai theo mục 3 ở trên.
