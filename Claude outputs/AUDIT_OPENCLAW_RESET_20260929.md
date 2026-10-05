# AUDIT MASTER — vòng OpenClaw 28-29/09 (D0–D5: COST_TRUTH · TRACKB_REDFLAGS · RESET_RULE P1/P2/P3 · RULERS §13)

Nguồn: commit `2c724ce`…`37d46af` (branch module). Đọc: RESULT_COST_TRUTH, RESULT_TRACKB_REDFLAGS, RESULT_RESET_RULE_P1/P2/P3,
docs/analysis/RULERS_CURRENT.md §13.

## 0. Kết luận
- **Quy trình: TỐT.** Pre-reg trước số ở cả 6 vòng, parity R0 legacy md5 `99e42b75` PASS, dự báo MASTER ghi trước và đối chiếu
  thẳng (lệch 2/3, đã khai), amendment post-hoc khai rõ, lỗi tool tự bắt (datetime64, hậu tố USDT, công thức hậu kiểm lệch
  8,6%), kết luận theo đúng luật (R4 qua P2 nhưng FAIL P3 ⇒ trả về B*). Không thấy dredging.
- **Kết quả chính đứng vững:** chi phí sim bị thổi (0,8 → 0,112%/vòng) ⇒ B* nhịp 1' CAGR 27,14 → **32,97%**; Track B chết
  (edge = artifact stop −10%); R0–R4 **không phân biệt được về Calmar** (CI chênh R4−B* chứa 0), B* hơn **có ý nghĩa về CAGR**
  (R4 −5,62pp, CI [−9,41; −2,34]).
- **Ý nghĩa cho giả thuyết owner ("giảm margin, tăng cược"):** đổi được **số lệnh/tập trung/DD lấy CAGR ở gần cùng Calmar**
  (R1/R3/R4 ~1,51–1,68 vs B* 1,66) — tức **edge trên mỗi đơn vị rủi ro gần như cố định** (~Calmar MTM 1,66, Sharpe năm ~2);
  "nhiều cược nhỏ" là **lựa chọn khẩu vị**, không tạo thêm edge. Rào tự tạo đã gỡ; bức tường còn lại là **edge thật + số episode**.

## 1. Phát hiện audit (xếp theo rủi ro)
1. 🔴 **"+1,675%/chân lúc vào khi sập" (n=37, CI [+0,90; +2,67]) bị diễn giải là "look-ahead của sim" — CHƯA chắc đúng, và
   CHƯA được áp vào bất kỳ vòng chấm nào (P1/P2/P3).** `s_close` đo so với close của nến CHỨA LỆNH KHỚP (nến t+1), còn sim vào
   ở close của NẾN QUYẾT ĐỊNH (nến t). Fill ≈ open(t+1) ≈ close(t) nghĩa là live khớp ≈ đúng giá sim; +1,675% chỉ là nến t+1
   sập tiếp. Hai khả năng: (a) không có bias (đo lệch mốc); (b) **độ trễ live** (một lượt quét ~228 s) làm lệnh khớp muộn trong
   cú sập — chi phí THẬT của live, không phải lỗi sim, và cascade sửa được. Vì lệnh lúc sập gánh phần lớn đuôi lợi nhuận, đây là
   **rủi ro sim-vs-live lớn nhất còn lại**. ⇒ Việc D6.
2. 🟠 **Tầng 4 (Calmar_MTM) thực chất do 1 sự kiện quyết định**: "năm xấu nhất = 2025" cho MỌI arm (cửa sổ 09–13/10/2025) ⇒
   xếp hạng T4 = arm nào lỗ ít nhất đúng tuần đó (n=1). Đề xuất thay/đi kèm: Calmar trung vị theo năm hoặc CVaR theo episode.
3. 🟠 **DSR khung hẹp**: N_eff 1,27 (ρ̄ 0,785 trên 236 run) đánh giá thấp số phép thử thật của cả chương trình (~200 vòng, nhiều
   cấu trúc khác nhau). Ở N=50/200: B* 0,950/0,820 ⇒ incumbent **có rủi ro chọn lọc vừa phải** ⇒ HOLDOUT là bắt buộc trước live.
4. 🟢 **Cập nhật một nhận định cũ của MASTER**: placebo "cùng phút vào, coin ngẫu nhiên" (P3 T4) cho **chọn coin +1,56pp/leg**
   (thật +3,29% vs random +1,72%, CI [+0,81; +2,39]) ⇒ S1/selector **CÓ giá trị tiền tại phút vào** (audit C 09-28 nói "S1 không có
   edge tiền" — sai ở phạm vi này). Và riêng timing gate: coin ngẫu nhiên vào đúng phút gate mở đã +1,72%/leg ⇒ timing và selection
   đóng góp **ngang nhau**. (Chưa chạy P2 "phút ngẫu nhiên + coin ngẫu nhiên" ⇒ chưa có mốc không-timing.)
5. 🟢 Track B: phân rã 2×2 sạch (stop 89% của gross control; universe tĩnh +0,010%/ngày); bỏ stop ⇒ chênh +0,006%/ngày CI chứa 0.
   Kết luận chết là đúng. Bài học chung: **stop −10% với slip cố định 0,5% = quyền chọn miễn phí trong harness** — kiểm lại mọi harness
   Python có stop (exit replay dùng min(open,close) cho SL, live STOP_MARKET slip ≈0 n=331 ⇒ sim chính ổn; STOP_LOSS live chỉ n=3).
6. 🟢 Chi phí: key `SIM_RATE_FEE`/`SIM_SLIPPAGE_RATE` gated, legacy = byte-identical ⇒ an toàn. Lưu ý mọi con số DEV cũ (CAGR 27%,
   các verdict ở phí 0,8/0,6) là ở phí sai — số chuẩn mới là @base.

## 2. Hướng đi tiếp (đề xuất cho owner/OpenClaw)
- **D6 — Độ trễ + giá khớp lúc sập (0 sim, đọc log 242 read-only):** cho mỗi chân VÀO live, lấy ts quyết định (log tạo lệnh/
  `would-BUY`) và nến quyết định; đo `fill vs close(nến quyết định)` + latency (giây), tách theo độ sập của nến. Rồi chấm lại B*
  @base với phạt đo được cho leg vào ở nến ≤ −1% (hậu kiểm, khai là xấp xỉ). Luật: nếu phạt thật > 0,5%/leg sập ⇒ cascade/giảm
  latency thành điều kiện bắt buộc trước live.
- **D7 — Đóng băng B* và pre-reg HOLDOUT 2026 một lần:** cấu hình (KEEPLEG0 + nhịp 1' + CONC_CAP 15% + phí base), rào tầng 1 +
  Calmar>0 + không tệ hơn DEV ngoài CI; cần dựng lại pred/gate 2026 bằng WFO retrain (RESULT_PREDBIN_REPRO: tái lập được) + S1 bins;
  khai phần 2026 đã nhìn (p15/feature 08–09, audit-only).
- **D8 — Kỹ thuật live:** cascade (`ENTRY_CASCADE`) → đo chi phí/tick → shadow nhịp 1' ≥ 4 tuần (owner duyệt; parity 2 md5 +
  EntryCascadeTest). Đây là đòn bẩy duy nhất còn lại có số: sel15 17% → 1' 27–33% CAGR DEV.
- **Nghiên cứu:** ngừng quét tham số trong họ hiện tại (đã chứng minh edge/rủi ro cố định). Họ mới chỉ mở khi có nguồn cược độc
  lập thật (không phải cross-section có stop như Track B); pre-reg + placebo + control cùng turnover từ đầu.
- **Owner chốt:** (i) đưa §13.2 vào `RISK_APPETITE.md`; (ii) chọn điểm trên đường biên: B* (CAGR cao, conc 7,1%) hay R1/R4 (CAGR
  thấp hơn 5–7pp, DD −16,5%, conc 3,8–5,3%, gấp 1,6–1,9× lệnh) — đây là khẩu vị, số không phân xử; (iii) live 15' → 1'.
