# A1_DELTA_2D — audit delta `v1.2/c3-live` vòng 2d (9c5a786f → d2a42596)

Auditor: a1audit (Claude Opus, độc lập), 2026-10-25. Chỉ đọc branch c3-live. Build và proof chạy trong worktree tách riêng (detached d2a42596, đã xoá sau khi xong).
Không ssh 242, không gọi Binance, không push. Proof: `docs/result/a1audit/2d/`.

## 0. Kết luận risk-first

**G-CODE: TRƯỢT cho canary/live** vì còn **1 MAJ mới: MAJ-3**. MAJ-3 KHÔNG ảnh hưởng **dry** (DryGateway không có vị thế thật). Nếu MASTER ghi
ngoại lệ có chủ đích thì dry có thể chạy. Các mục khác: MAJ-2b ĐÓNG, MIN-18 ĐÓNG, MIN-19 ĐÓNG, hậu kiểm LATCH ĐẠT. Đường byte-identical của c3_shadow ĐẠT
(parity 10-23 4/4 md5 + bytecode).

**MAJ-3: stop c3s- của vị thế THẬT KHÔNG có trong sổ bị huỷ.** Proof `ProofFlat2` (Mock repo, jar 2d) cho hai ca:
- D (startup): sổ rỗng/mất (book file hỏng ⇒ `.corrupt` + sổ rỗng, hoặc file sổ bị đổi tên như `rollback_v12.sh` làm), sàn có vị thế XRP 100 + stop
  `c3s-` NEW ⇒ `Reconciler.startup()` xếp stop vào nhóm "mồ côi" và **huỷ** (`orphanCancelled=[XRPUSDT/c3s-…]`) ⇒ vị thế thật mất stop. Vị thế đó chỉ còn được báo "vị thế lạ" (chặn mở mới + Telegram).
- E (hằng giờ): vị thế lạ DOGE 50 có stop `c3s-` ⇒ `sweepOrphanStops` **huỷ** stop đó.
- Đây chính là failure mode mà sổ fail-closed đã thiết kế để chịu (file hỏng). Hệ quả cùng loại với MAJ-2: vị thế thật mất bảo vệ trên sàn.
- Sửa (rẻ): trước khi huỷ một stop `c3s-` "mồ côi", đọc positions (positionRisk + `account().positions`). Symbol còn vị thế ≠ 0 ⇒ **giữ stop**, xếp
  vào unknown + Telegram, KHÔNG huỷ. Chỉ huỷ khi cả hai nguồn đều báo phẳng. Thêm test cho ca D và E.

## 1. MAJ-2b (019f64f0) — ĐÓNG
- ProofFlat gốc (2 lần đọc rỗng cách 10 s): **giữ cụm + giữ stop**, vị thế 100 còn nguyên (`doc 2: closed=[] cum_con=true stop=1`).
- ProofFlat2 (jar 2d):
  - A (positionRisk rỗng ×6 cách 31 s, account vẫn có vị thế) ⇒ giữ.
  - B (positionRisk + `account().positions` cùng rỗng ×6) ⇒ giữ nhờ (c) "còn 1 stop c3s- NEW", Telegram 1 lần.
  - F/F2 (closeCluster TIME_STOP và FLATTEN step ×6 khi glitch) ⇒ giữ.
  - C (owner tự huỷ stop + 2 nguồn vẫn rỗng) ⇒ mới kết luận phẳng. Đúng thiết kế, vì ca này cần 3 tín hiệu sai cộng 1 thao tác người.
- Các đường khác có thể huỷ stop:
  - (ii) stop FINISHED/FILLED (`queryStop`): chỉ được xét SAU khi positionRisk đã báo phẳng. Với stop closePosition, FINISHED đồng nghĩa vị thế đã đóng.
    Với stop kiểu qty (fallback −4130 / adopt) mà qty < vị thế, FINISHED + positionRisk glitch ⇒ có thể xoá cụm còn phần dư. Ca hiếm (MIN).
  - Lệnh đóng của bot FILLED đủ qty ⇒ đúng, vì qty lấy từ positions lúc gửi.
  - Stream `pa=0` / `onSell` FILLED ⇒ bằng chứng dương.
  - Startup và hằng giờ ⇒ **MAJ-3**.
- "Cụm ma" (vị thế thật đã đóng ngoài bot trong lúc mất stream, stop closePosition vẫn NEW nếu sàn không tự huỷ — CHƯA XÁC MINH):
  - Phạm vi chặn: chỉ symbol đó (`allowsEntry(XRP)=false`, BTC=true). Nhưng margin của cụm ma vẫn tính vào `marginUsed`, nên bóp throttle/U_MAX toàn hệ.
  - Lãi/lỗ đã chốt không vào sổ, nên đối chiếu equity hằng giờ dễ lệch > 1 % ⇒ `EQUITY_MISMATCH` **chặn toàn hệ**.
  - Time-stop lặp lại mà không làm gì. Telegram chỉ báo 1 lần.
  - Cách gỡ: owner huỷ stop c3s- bằng tay (ca C) rồi reanchor; hiện CHƯA có script. MIN; đưa vào G-CANARY (runbook/script + nhắc lại định kỳ).
- `AccountSnapshot.positions`: theo docs Binance `GET /fapi/v3/account` (developers.binance.com, Account-Information-V3), mỗi phần tử `positions` gồm
  `symbol, positionSide, positionAmt, unrealizedProfit, isolatedMargin, notional, isolatedWallet, initialMargin, maintMargin, updateTime`. Chỉ trả symbol
  "had position / open orders"; weight 5. Client đọc `symbol`/`positionAmt` (đúng). `entryPrice`/`markPrice` không có trong v3, nên `dec()` trả null — FlatConfirm không dùng
  hai trường này ⇒ không sao. **CHƯA XÁC MINH với sàn thật** (đưa vào canary K0: so `account().positions` với `positionRisk`).

## 2. MIN-18 / MIN-19 — ĐÓNG, không hồi quy C6/A40
- MIN-18: UNKNOWN chỉ được gỡ sau ≥ 2 lần đọc nhất quán cách ≥ 30 s. ProofFlat gốc: lần đọc rỗng đầu tiên KHÔNG gỡ chặn (`allowsEntry(BTC)=false`).
- MIN-19 (ProofKs3):
  - Đỉnh C6 và `acct_peak` ghi kèm `adapter=`. Đi từ dry (đỉnh 12 000) sang live (tmb 7 000) ⇒ cả hai đỉnh dry bị BỎ QUA + WARN ⇒ C6/A40 không latch giả.
  - Restart live→live giữ đỉnh 7 000 ⇒ tmb 4 000 (−42,9 %) ⇒ C6 **và** A40 latch FLATTEN đúng.
  - ProofKs2 (S1–S9) chạy lại trên jar 2d cho kết quả y hệt 2c. File đỉnh của c3_shadow giữ nguyên định dạng (`peakTag` null).
  - Ghi chú: file latch (mã latch + `c2_events_ms`) KHÔNG gắn nhãn adapter ⇒ latch dry mang sang live (fail-safe). Sự kiện C2 của dry = 0 vì dry khớp ở giá ref.
    MIN: deploy canary nên bắt đầu với file latch sạch.

## 3. Hậu kiểm LATCH (2b3628d1) — ĐẠT; không PASS giả, có thể FAIL giả theo hướng an toàn
- Đếm theo mốc `run/.v12_start_epoch` (ghi ngay trước `daemon.sh start`). Gom `full.log` + file đã xoay (`full.log.*`, `full*.gz`) có mtime > mốc.
  Thiếu mốc / thiếu log / không có file sau mốc / không thấy dòng MainClass sau mốc ⇒ `LATCH_COUNT=<lý do>` ≠ 0 ⇒ **FAIL + rollback tự động**.
  Hai lỗ PASS giả của lần 2c (thiếu log, log xoay) đã đóng.
- Múi giờ (chỉ dùng log đã kéo về Oracle): log 242 có dạng `25/10/2026 08:23:10.888` (dd/MM/yyyy HH:mm:ss.SSS, không ghi múi). Dòng cuối của bản kéo
  2026-10-24 là 08:23:10, trong khi `pull.log` (Oracle, +0700) ghi 2026-10-25 08:23:17+0700 và `check.txt` ghi 01:23:28Z ⇒ **timestamp log = +07**. Dòng HOURLY
  `hour=…T07+07` lúc 08:00 cũng khớp.
  Script tính mốc bằng `date -d @ST +%Y%m%d%H%M%S` theo múi **mặc định của shell root qua ssh** — chưa xác định được (các script Oracle luôn ép
  `TZ=Asia/Ho_Chi_Minh`, gợi ý giờ hệ thống có thể không phải +07). Hai trường hợp:
  - Shell UTC, log +07 ⇒ cửa sổ rộng thêm 7 h về trước, gồm cả phần log c3_shadow (KS mode log không bao giờ in `LATCH`) ⇒ kết quả vẫn đúng. Chỉ khi
    có một lượt v12 latch trong vòng 7 h trước thì mới FAIL giả (an toàn).
  - Shell +07 mà log là UTC ⇒ không thấy MainClass ⇒ luôn FAIL + rollback (an toàn nhưng chặn deploy). Bằng chứng trên cho thấy log là +07 nên ca này khó xảy ra.
  - **Không có ca nào PASS giả.** Khuyến nghị (MIN): đổi thành `TZ=Asia/Ho_Chi_Minh date -d @$ST …`, hoặc in `date +%z` ra log deploy.
- Một lần restart thật (10-23 09:37, KS mode log) có 0 `WOULD_TRIGGER` ⇒ khả năng C1/C5 lúc khởi động gây FAIL giả là thấp (mới 1 mẫu).

## 4. Byte-identity c3_shadow — ĐẠT
- Build lại d2a42596: **600 test, 0 fail, 1 skip** (có sẵn). Jar A1 md5 `f395b9df…` (không tái lập byte so với `6829a6ed` của tác giả; đã so từng lớp).
- Bytecode `dcae2e2b` ↔ 2d: 622 → 738 lớp, 0 xoá, 5 lớp thêm ngoài c3live (y như trước), **26 lớp đổi = đúng tập các lần trước**. `javap` khác lần 2c chỉ ở
  `KillSwitchEngine` (3296→3507) và `OpsHooks` (600→623) = MIN-19; mọi nhánh mới chặn bởi `prm.peakTag != null`, mà chỉ `build(c3live=true)` đặt
  ⇒ c3_shadow không đổi (ProofKs2 S9 + file đỉnh sổ giấy giữ định dạng). Mọi thay đổi khác của 2d nằm trong `c3live.*`.
- **Parity offline cờ TẮT 2026-10-23** (jar tự build, `drv.py`): md5 out_BT/out_NEW2/fund_BT/fund_NEW2 = e0918a33/e0918a33/a81b3b03/8dea3f70
  **4/4 trùng dcae2e2b**. CTL gate 1440/1440 bit. CTL fund y hệt lượt ref (cand 0,99750, f3 0,94586). strace 0 AF_INET, 0 tới 242, rc 0.

## 5. Đưa vào prereg G-CANARY (mục còn mở)
1. **MAJ-3** (nếu MASTER cho dry chạy trước khi sửa): bắt buộc sửa + test trước canary. Kịch bản canary K6b: xoá/đổi tên sổ khi đang có vị thế + stop ⇒ restart
   ⇒ stop PHẢI còn trên sàn.
2. Sàn có tự huỷ stop closePosition (Algo) khi vị thế về 0 không (quyết định có "cụm ma" hay không); `account().positions` khớp `positionRisk`.
3. Runbook/script owner gỡ "cụm ma" (huỷ stop c3s- + reanchor) + Telegram nhắc định kỳ thay vì chỉ 1 lần.
4. File latch/đỉnh sạch khi chuyển dry → canary (đỉnh đã gắn nhãn; latch + `c2_events` chưa gắn nhãn).
5. TZ của mốc hậu kiểm LATCH (ép +07).
6. Các điểm CHƯA XÁC MINH từ lần 1: BFUSD/Multi-Assets, −4130 Algo, URL WS private, ALGO_UPDATE, −2021, symbolConfig toàn bộ, weight.
7. MIN-3/4/8/9/14/15/16 của lần 1 (không chặn).
