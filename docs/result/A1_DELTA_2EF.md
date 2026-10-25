# A1_DELTA_2EF — audit delta `v1.2/c3-live` vòng 2e+2f (d2a42596 → 00da87d2)

Auditor: a1audit (Claude Opus, độc lập), 2026-10-25. Chỉ đọc branch c3-live. Build và proof chạy trong worktree tách riêng (detached 00da87d2, đã xoá sau khi xong).
Không ssh 242, không gọi Binance, không push. Proof: `docs/result/a1audit/2ef/`.

## 0. Kết luận

**G-CODE: ĐẠT** — 0 CRIT, 0 MAJ mở. Áp dụng cho **dry**; với **canary** là ĐẠT về code, kèm điều kiện các mục G-CANARY ở §6.
MAJ-3 ĐÓNG. Cụm ma, file latch gắn nhãn, TZ của hậu kiểm LATCH: ĐẠT. Lớp chặn 2f: ĐẠT, không làm lọt lệnh sai, không chặn toàn hệ trên đường thường.
Byte-identity c3_shadow ĐẠT. Có 3 MIN mới (MIN-20..22), không chặn, nên làm trước hoặc trong canary.

## 1. MAJ-3 — ĐÓNG
- ProofFlat2 trên jar 2f:
  - D: sổ rỗng + vị thế thật có stop c3s- ⇒ `orphanCancelled=[]`, **stop còn 1**, symbol vào UNKNOWN.
  - E: vị thế lạ DOGE + stop c3s- ⇒ hourly **giữ stop**.
  - A/B/F/F2/C: như 2d.
- Grep độc lập `cancelStop|cancelOrder|cancelAll|allOpenOrders` trong `c3live.*`: `gw.cancelStop` chỉ còn ở `OwnStopGuard.doCancel`; `cancelOrder` không có call site nào;
  không có cancelAll. Mọi đường (Reconciler startup/sweep/retry, FillAccounting.closedOnExchange, Flattener.finalizeClosed, Trailing) đều đi qua
  guard. Runtime dùng chung **1 guard** (unknown → Reconciler).
- Hai ngoại lệ:
  - `cancelRetired`: chỉ gọi khi cụm đang giữ có stop nhưng `priceSL` NaN. NaN chỉ xảy ra sau `confirm(legIdx>0)`, tức DCA ĐÃ KHỚP thật (RESULT/queryOrder/stream).
    Huỷ stop lúc này đúng thiết kế (Q1a: không SL cứng trước arm). Glitch positions không thể tạo ra trạng thái này.
  - `cancelReplaced`: gọi (a) ngay sau khi `newStopMarket` trả về thành công và đã promote, hoặc (b) khi `queryStop` thấy stop pending không phải CANCELED/EXPIRED/REJECTED.
    **MIN-20**: ở (a), code không kiểm `algoStatus` trong response. Nếu sàn trả 200 nhưng stop bị từ chối, hoặc từ chối bất đồng bộ (CHƯA XÁC MINH với Algo API),
    thì stop cũ bị huỷ trong khi stop mới không sống ⇒ vị thế không có stop. Sửa rẻ: chỉ huỷ stop cũ khi status = NEW, hoặc `openStops` có cid mới. Canary K2 phải kiểm.

## 2. Lớp chặn 2f (A toàn hệ / B riêng symbol) — ĐẠT
Proof `ProofCrash.java` (Mock repo, guard dùng chung như runtime): 3 cụm A/B/C chốt cùng lúc (sàn kích stop, xử lý như stream `pa=0` → `closedOnExchange`),
positionRisk + account TRỄ 60 s, rồi 24 leg mới ở 24 symbol khác:

| ca | 24 leg symbol khác | 3 symbol vừa chốt | chặn | sau ~2′ (REST hết trễ) |
|---|---|---|---|---|
| R1 đường thường (chỉ stop vừa kích) | **24/24** | 0/3 | B=[A,B,C] | 24/24, 3/3, hết chặn |
| R2 mỗi cụm còn 1 stop c3s- cũ chưa huỷ (bị GIỮ vì REST còn vị thế) | **24/24** | 0/3 | B, stop giữ 3 | 24/24, 3/3, stop huỷ 3 |
| R3 = R2 + positionRisk LỖI ĐỌC lúc chốt | **0/24** | 0/3 | A UNKNOWN | 24/24, 3/3 |
| R4 = R2 + restart trong 10′ (mất mốc RAM) | **0/24** | 0/3 | A UNKNOWN | 24/24, 3/3 |

- Đường thường (R1/R2) **không chặn toàn hệ**. Leg mới của symbol khác vào đủ trong lúc cụm cũ đang chốt.
- R4 rơi về (A) là an toàn, đúng thiết kế.
- R3 (MIN-21): chỉ xảy ra khi còn stop c3s- MỞ ngoài stop vừa kích **và** đúng lúc đó REST đọc positions lỗi. Khi đó hệ chặn toàn bộ khoảng 1–2′ sau khi REST hồi phục — đúng vào đợt sập,
  lúc REST dễ lỗi. Nếu `openStops` lỗi thì chỉ rơi vào (B). Đề xuất: positions không đọc được nhưng symbol vừa chốt (< 10′) ⇒ (B), quá 10′ mới leo thang (A).
- "X vừa chốt mà sàn còn vị thế thật": (B) chỉ gỡ khi không còn stop bị giữ **và** 2 lần đọc positionRisk phẳng cách ≥ 30 s. Vị thế thật ⇒ không bao giờ phẳng
  ⇒ quá 10′ leo thang (A) + Telegram. Không mở lại X được.
  **MIN-22**: điều kiện gỡ (B) chỉ dùng positionRisk, không đối chứng `account().positions` như FlatConfirm. Glitch rỗng 2 lần + stop đã mất ⇒ có thể mở lại X
  chồng lên vị thế thật (sổ < sàn; runtime không phát hiện lệch qty vì chỉ startup mới "sàn thắng"). Hiếm; đề nghị thêm điều kiện account.
- Cụm ma: Telegram nhắc mỗi 6 h (FlatConfirm và guard).

## 3. `c3live_ghost_clear.sh` — ĐẠT
- Không đọc/in key: chỉ ghi `run/c3live_ghost_clear.req` và đọc `.result`. SYMBOL kiểm `[A-Z0-9]` ở cả script lẫn JVM. Cần **YES=1**, không có thì chỉ xem.
- `ProofGhost` (Reconciler.ghostClear thật):
  - G1 vị thế 100 ⇒ `REFUSED … vị thế != 0`, stop còn, cụm còn.
  - G2 symbol `XRP;rm` ⇒ REFUSED.
  - G3 vị thế 0 (owner đóng tay) ⇒ OK, huỷ stop, xoá cụm.
- `test_fake242.sh` A1 chạy lại: **41/41 PASS** (5 ca ghost), không còn process giả. `bash -n` OK với 7 script.

## 4. File latch gắn nhãn — không hồi quy C2/C6/A40
- File latch ghi `adapter`. Nếu nạp phải file khác nhãn mà có latch hoặc sự kiện C2 ⇒ **GIỮ nguyên** + WARN + Telegram (hướng dẫn `killsw_reset.sh`). Không có gì ⇒ bỏ qua.
  Cảnh báo phát sinh trước `setAlert` được giữ lại (tối đa 8) và gửi sau; chỉ áp dụng khi `peakTag != null` (c3_live).
- ProofKs2 (S1–S9) và ProofKs3 (dry→live bỏ đỉnh dry; live→live C6 + A40 latch FLATTEN đúng ở −42,9 %) trên jar 2f: **y hệt 2d**.

## 5. Byte-identity c3_shadow — ĐẠT
- Build lại 00da87d2: **613 test, 0 fail, 1 skip** (có sẵn).
- Bytecode `dcae2e2b` ↔ 2f: 622 → 740 lớp, 0 xoá, 5 lớp thêm ngoài c3live (như cũ), **26 lớp đổi = đúng tập cũ**. `javap` khác 2d chỉ ở `KillSwitchEngine`
  (3507→3645): nhánh mới chặn bởi `prm.peakTag != null`, chỉ c3_live đặt. Thay đổi main ngoài c3live của 2e/2f chỉ có `KillSwitchEngine`.
- **Parity cờ TẮT 2026-10-23** (jar tự build): md5 out_BT/out_NEW2/fund_BT/fund_NEW2 = e0918a33/e0918a33/a81b3b03/8dea3f70 **4/4 trùng dcae2e2b**. CTL gate 1440/1440 bit,
  CTL fund y hệt lượt ref, strace 0 AF_INET / 0 tới 242, rc 0.
- TZ hậu kiểm LATCH: mốc nay ép `TZ=Asia/Ho_Chi_Minh` (log 242 là +07, đã đối chiếu ở 2d) + in `tz_shell` ra log deploy. ĐẠT.

## 6. Prereg G-CANARY — danh sách cuối
1. **K0 chỉ đọc**: tmb BFUSD, multiAssets=true, dualSide=false, symbolConfig toàn bộ (MIN-5), `account().positions` khớp `positionRisk`, URL WS private, keepAlive ≥ 65′.
2. **K1 vào lệnh** (20 USDT): Multi-Assets với USDT=0 không bị −2019; RESULT FILLED + avgPrice; stream ≤ 2 s; C2 có dấu.
3. **K2 stop**: closePosition thứ 2 (−4130?); **mỗi lần dời phải kiểm `openAlgoOrders` = đúng 1 stop c3s- NEW** (MIN-20); `algoStatus` trong response.
4. **K3 −2021**, **K4 stop kích thật**: ALGO_UPDATE + cid/ot lệnh MARKET ⇒ lý do TRAILING, 0 stop mồ côi; ghi lại sàn có tự huỷ stop closePosition khi vị thế = 0 không
   (quyết định tần suất cụm ma).
5. **K5 time-stop/X14** (`closeCluster`) ⇒ phẳng, stop huỷ qua guard.
6. **K6 restart** giữ sổ ⇒ 12 trường khôi phục; **K6b** đổi tên sổ khi có vị thế + stop ⇒ restart ⇒ stop CÒN trên sàn, UNKNOWN chặn, Telegram.
7. **K7 mất stream** ⇒ fallback REST; không cụm/stop nào bị xoá sai.
8. **K8 đối chiếu equity** ≤ 1 % sau K1–K5 (BFUSD, phí).
9. **Đo lớp chặn trong đợt nhiều lệnh**: số phút chặn (A)/(B), số leg bị chặn vì RECON_BLOCKED (MIN-21), độ trễ leg cuối (MIN-5).
10. **Chuyển dry → canary**: đỉnh + latch đã gắn nhãn (latch khác nhãn ⇒ giữ; owner reset có chủ đích).
11. MIN mở (không chặn): MIN-20/21/22 (trên); MIN-3/4/8/9/14/15/16 (lần 1); adopt stop kiểu qty (2c).
