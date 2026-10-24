# PREREG_PARITY_V11_WINDOW — ADDENDUM 1: thu hẹp nhãn K (K1′, K3′, K6), báo cáo tích luỹ P2

- **Ngày chốt:** 2026-10-24 (+07). **Quyết định:** MASTER. Agent chỉ chuẩn hoá câu chữ và bổ sung chi tiết kỹ thuật thực thi (§3), không đổi tinh thần.
- **Gốc:** `docs/prereg/PREREG_PARITY_V11_WINDOW.md` (`481701b2`). Mọi điều không nhắc ở đây giữ nguyên.
- **Thời điểm:** commit **TRƯỚC** khi chạy bất kỳ phép đo nào của lượt D2 (ngày UTC 2026-10-22 và 2026-10-23) và trước khi xem bất kỳ số nào của D2.

## 1. Lý do

D1 ADDENDUM1 (`a7e2764f`, `docs/result/PARITY_V11_WINDOW_D1_ADDENDUM1.md` §0 mục 2, §6) cho thấy nhãn **K3** theo đúng chữ prereg §5 phủ **1387/1387 phút** của cửa sổ D1. Nguyên nhân: 3 symbol `BACUSDT`, `CEGUSDT`, `IBKRUSDT` niêm yết trong ngày, nên điều kiện "`nsym` live ≠ |U_D| hoặc U đổi trong [M−1440′, M]" đúng ở mọi phút. Khi đó nhãn K không còn phân loại được phút nào và "K5 = 0" mất ý nghĩa. Tương tự, khung K1 [M−20′, M+10′] dựa trên bộ đếm không theo symbol, nên gán K1 mà không chỉ ra symbol nào gây lệch (D1 ADDENDUM1 §7.1).

Quyết định này được chốt **trước khi xem bất kỳ số nào của D2**.

## 2. Luật mới (thay §5 của prereg gốc ở các điểm nêu dưới)

- **K3′ (thay K3).** Phút lệch M chỉ mang nhãn K3′ nếu phép drop-one **chứng minh** được rằng lệch biến mất khi loại các symbol có thay đổi thành viên U trong [M−1440′, M] khỏi phép tính feature/thị trường. Không chứng minh được ⇒ không phải K3′.
- **K1′ (mở rộng K1).** Lệch do nến collector đến muộn/bị ghi đè được tính K1′ nếu có bằng chứng log/manifest (reread/overwritten) cho **chính symbol gây lệch**, trong khoảng thời gian mà các nến khả dụng dùng cho feature đó trải ra (ví dụ 15 nến khả dụng của một symbol ít giao dịch có thể trải ~40′), tối đa tới M+10′. Không có bằng chứng ⇒ không phải K1′.
- **K6 (mới; chỉ mô tả, không tính vào K5).** Hoán đổi thứ hạng S1-V giữa 2 ứng viên kề nhau, khi |Δscore| ≤ 1e-6·max(|score|) (float32 live vs float64 offline) và tập top-K không đổi. "score" ở đây là giá trị được xếp hạng: điểm S1 đối với thứ tự top-24; feature gốc đối với cột rank (`f2` = rank `dd_7d`, `f5` = rank `ret_3d`).
- **K2** (a/b/c) và **K4** giữ nguyên như prereg gốc.
- **K5.** Mọi phút lệch không thuộc K1′/K2/K3′/K4/K6 ⇒ K5 (XÁM ⇒ điều tra trước lượt kế).
- **Ngưỡng không đổi:** P1, P2, P3, TSX, S1-I, GV-I, CTL giữ nguyên ngưỡng và luật verdict của prereg gốc §4–§5.
- **Báo cáo tích luỹ** qua các lượt: số cặp r/q ≥ 0,9 và ≥ 0,8, tách live và offline. Mục đích: đo mức độ P2 thực sự bị thử.
- **Áp lại nhãn K′ cho D1.** Chỉ áp nhãn; không đổi verdict P* của D1. Mục đích: nhất quán giữa các lượt.

## 3. Chi tiết kỹ thuật thực thi (agent bổ sung, không đổi tinh thần)

1. **Đơn vị gán nhãn = (phút, nguồn lệch).** Nguồn lệch như D1 ADDENDUM1: P1-F, P1 (rel > 1e-3), MD, FUND, NET, GV-O, S1-V. Một phút là K5 nếu **có ít nhất một nguồn** của nó không mang nhãn nào trong K1′/K2/K3′/K4/K6. Nhờ vậy, K6 ở S1-V không che được lệch P1-F chưa giải thích ở cùng phút.
2. **Mốc thay đổi thành viên U (cho K3′).** Lấy cho ngày D−1 và D, gồm:
   - niêm yết = nến Vision đầu tiên của symbol có trong ngày này nhưng không có trong ngày trước;
   - huỷ niêm yết = nến Vision cuối cùng của symbol có trong ngày trước nhưng không có trong ngày này.

   S_M = tập symbol có mốc ∈ [M−1440′, M].
3. **Phép drop (K3′).**
   - **P1-F/P1/MD/FUND/NET/GV-O:** chạy lại OFF-BT (cùng harness, cùng tham số) trên cache Vision của U_D \ S_M. Mỗi tập S_M khác nhau chạy một lần.
   - **S1-V:** tính lại cột rank sau khi loại S_M khỏi tập xếp hạng.
   - Lệch ở (M, nguồn) "biến mất" nếu sau drop mọi giá trị so sánh của nguồn đó tại M khớp live theo cùng dung sai §4. Riêng P1 là rel ≤ 1e-3.
   - S_M rỗng ⇒ không phải K3′.
4. **K1′ cần bằng chứng nêu tên symbol.** Bằng chứng phải là dòng log hoặc manifest nêu tên symbol đó bị reread/overwritten/rewritten, với thời điểm nằm trong [nến khả dụng sớm nhất mà feature dùng, M+10′].
   - Dòng chỉ có bộ đếm (`[LIVE-KLINE] … reread_overwritten=N`, `S1 doc lai close …: N coin, sua K`) **không đủ** làm bằng chứng.
   - Nhãn K1 cũ (theo bộ đếm) vẫn được tính và báo cáo để mô tả, nhưng không loại phút khỏi K5.
5. **K6 cơ học.** Áp cho từng dòng S1-V lệch, tại giờ M và cột rank c ∈ {f2, f5}. Dòng lệch là K6 nếu:
   - tồn tại đối tác s′ sao cho hạng live và hạng offline của (s, s′) đổi chỗ cho nhau, với |Δhạng| = 1/n;
   - |v_s − v_s′| ≤ 1e-6·max(|v_s|, |v_s′|) cho giá trị gốc v ở phía live hoặc phía offline;
   - top-24 của giờ đó trùng tập.

   Dòng lệch `score` thuộc K6 nếu mọi lệch feature của dòng đó đều là K6 và top-24 trùng tập. Nguồn S1-V của phút M là K6 khi mọi dòng lệch của nó là K6.
6. **Ngày không có Vision.** Theo prereg gốc §3, ngày D mà Vision chưa phát hành cho ≥ 99 % U_D thì mọi chỉ số cần Vision của ngày đó = **KHÔNG ĐO ĐƯỢC** ở lượt này và được chấm gộp ở lượt kế. Các chỉ số không cần Vision (P3, S1-I, S1-m, GV-I, P1-m, `[GATE] n_pass`) vẫn chấm.
