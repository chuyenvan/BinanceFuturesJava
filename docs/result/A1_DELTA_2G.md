# A1_DELTA_2G — audit delta `v1.2/c3-live` vòng 2g (00da87d2 → 05b04165)

Auditor: a1audit (Claude Opus, độc lập), 2026-10-25. Chỉ đọc branch c3-live. Build và proof chạy trong worktree detached tạm (đã xoá).
Không ssh 242, không gọi Binance, không push. Proof: `docs/result/a1audit/2g/`.

## 0. Kết luận

**G-CODE: VẪN ĐẠT** — 0 CRIT, 0 MAJ. MIN-20, MIN-21, MIN-22 ĐÓNG. Có 1 MIN mới: **MIN-23** — vị thế "vừa chốt" mà sàn thật còn, cộng với positionRisk lỗi kéo dài ⇒ kẹt ở (B), không leo thang lên (A).
MIN-23 không chặn G-CODE. Trong suốt thời gian đó stop vẫn được GIỮ, và hành vi này cùng loại với "đọc lỗi hằng giờ thì không chặn" vốn đã chấp nhận ở lần 1.
Byte-identity c3_shadow ĐẠT.

## 1. MIN-20 — ĐÓNG
- `cancelReplacedIfConfirmed`: chỉ huy stop cũ khi stop mới có `algoStatus=NEW` trong response, hoặc thấy NEW trong `openStops` (đọc tối đa 2 lần cách 1 s).
  Không xác nhận được ⇒ GIỮ CẢ HAI. Stop cũ vào `orphanStops`; nhịp sau đi qua `OwnStopGuard`, guard chỉ huỷ khi stop active mới ĐANG MỞ trên sàn, hoặc khi cả positionRisk
  lẫn account đều báo phẳng. Còn vị thế ⇒ GIỮ.
- **Có đường nào để vị thế còn 0 stop?** Không thấy. Nếu stop mới "chết" (bị từ chối bất đồng bộ), stop cũ vẫn bị giữ mãi (bảo vệ ở mức cũ, chênh ≤ ~0,1 %
  + 1 tick); lần dời được xác nhận kế tiếp sẽ dọn cả hai. Lưu ý (MIN): runtime không kiểm stop active có còn sống không; chỉ startup mới phát hiện `stopsDropped`.
- **Hai stop tồn tại lâu dài:** chỉ xảy ra khi `openStops` lỗi kéo dài. Hai stop closePosition cùng chiều là vô hại (cái kích sau không còn vị thế).
  −4130 ở lần đặt kế ⇒ fallback qty+reduceOnly (`allowFallback`), không kẹt trailing. Sàn có cho 2 closePosition cùng chiều qua Algo API không
  vẫn CHƯA XÁC MINH (G-CANARY K2). Ghi chú: OPS thread ngủ 1 s mỗi lần không xác nhận được ngay (không đáng kể).
- Test tác giả: `replacedStopKeptUntilNewStopConfirmed`, `replacedStopConfirmedViaOpenStops`. `OrderStatus.parse(algoStatus)` dùng chung cho response và query.

## 2. MIN-21 — ĐÓNG (kèm MIN-23)
`OwnStopGuard.keep`: cụm vừa chốt (< 10′) ⇒ (B), kể cả khi đọc vị thế lỗi; quá 10′ hoặc sổ không biết symbol ⇒ (A).

ProofCrash (jar 2g): R1/R2 24/24; **R3 (REST lỗi lúc chốt) nay 24/24** (2f: 0/24); R4 (restart) 0/24 (A, an toàn); cả 4 ca hết chặn sau ~2′.

Proof mới `ProofB`: stream báo đóng nhưng sàn THẬT còn 100, theo dõi 16′:

| ca | 0–8′ | ≥ 10′ | stop |
|---|---|---|---|
| R5 đọc OK | B (Y vào được) | **A** (chặn toàn hệ) | giữ |
| R7 account lỗi kéo dài | B | **A** | giữ |
| R6 positionRisk lỗi kéo dài | B | **vẫn B tới 16′** | giữ |
| R8 cả hai lỗi | B | **vẫn B** | giữ |

**MIN-23:** `retryKeptStops` và `unknownCheck` chỉ chạy SAU khi `positionsBySymbol()` thành công. positionRisk lỗi liên tục ⇒ không có lần giữ nào sau 10′ ⇒ không leo thang;
Telegram chỉ có lần đầu. Hệ quả: symbol đó bị chặn, vị thế thật ngoài sổ vẫn có stop, các symbol khác vẫn vào lệnh.
Sửa rẻ: trong `confirmPendingFlat` (hoặc nhịp ops), mục (B) nào quá 10′ thì chuyển (A) theo thời gian, không cần đọc thành công; kèm Telegram nhắc lại.

## 3. MIN-22 — ĐÓNG
Gỡ (B) nay cần thêm `account().positions` vắng/0 ở mỗi lần đọc được tính (lỗi/null ⇒ lần đó không tính). Account còn vị thế ⇒ đếm lại; quá 10′ ⇒ (A) (R5/R7 ở trên).

## 4. Byte-identity c3_shadow — ĐẠT
- Build lại 05b04165: **618 test, 0 fail, 1 skip** (có sẵn).
- Bytecode `dcae2e2b` ↔ 2g: 622 → 740 lớp, 0 xoá, 5 lớp thêm ngoài c3live, **26 lớp đổi = đúng tập cũ**, số dòng `javap` khác của từng lớp cũ **y hệt 2f**.
  Thay đổi main của 2g chỉ nằm trong `c3live.*` (3 file).
- **Parity cờ TẮT 2026-10-23** (jar tự build): md5 out_BT/out_NEW2/fund_BT/fund_NEW2 = e0918a33/e0918a33/a81b3b03/8dea3f70 **4/4 trùng dcae2e2b**; CTL gate 1440/1440 bit; CTL fund y hệt lượt ref; strace 0 AF_INET / 0 tới 242; rc 0.

## 5. G-CANARY (bổ sung vào danh sách 2ef §6)
- K2: mỗi lần dời phải kiểm `openAlgoOrders` = đúng 1 stop NEW; ghi `algoStatus` trong response; thử 2 closePosition cùng chiều.
- K7b: giả lập positionRisk lỗi khi một cụm vừa chốt ⇒ xác nhận hành vi (B), ghi thời gian chặn (liên quan MIN-23).
