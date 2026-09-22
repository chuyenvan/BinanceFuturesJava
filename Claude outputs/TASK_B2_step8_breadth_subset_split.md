# TASK B2 Bước 8 — Breadth theo SUBSET (majors/alts split, ý Uni chọn) — thiết kế MASTER 2026-09-22

Người soạn: MASTER. Thực thi: agent. Chủ quyết định: Uni (đã chọn thử majors/alts split sau khi nghe rủi ro overfit).
Tiền đề: BRC (Bước 7, `RESULT_BREADTH_CONT.md`) = NULL. Phát hiện cấu trúc: **breadth all-coin 2025 ~11% (thị trường HẸP: majors lên, alt chết dưới MA200) → gate liên tục kẹt ~1.5, KHÔNG đủ chặt.** Số liệu quan trọng: **T170 (gate 1.7 phẳng) đã cho 2025 TỐT NHẤT (UW 52, ret 32.7)**; mọi biến thể breadth làm 2025 xấu vì NỚI gate xuống dưới 1.7 (BRC ~1.5 → UW 221, ret 28.7 < T170). ⇒ breadth chỉ có giá trị ở 2023/2024 (uptrend rộng, nới gate lấy thêm cược); ở 2022/2025 phải giữ ~1.7.

## CẢNH BÁO KHOÁ TRƯỚC (MASTER, chống giải-thích-xuôi)
- Đây là **cơ chế regime thứ 9 fit vào ĐÚNG 2 sự kiện UW (2022, 2025)**. power_wall đã cảnh báo phòng-thủ-per-regime vượt ngân sách sự kiện độc lập. Kể cả PASS ⇒ chỉ là **ứng viên shadow-forward**, KHÔNG phải proven. MASTER sẽ KHÔNG tuyên "giải được breadth" từ 1 sim pass.
- **Sửa chiều gợi ý agent**: agent ban đầu nói "2025 majors mạnh → nới gate". SAI: số liệu cho thấy 2025 phải SIẾT (T170 1.7 thắng). Regime-signal đúng phải **đọc 2025 là risk-off** ⇒ dùng **breadth của nhóm YẾU (alts)** mà 2025 xuống sâu, để gate → 1.7. KHÔNG nới.
- **Trần n_eff là cấu trúc, không phải do định nghĩa breadth**: hạ gate = thêm cược CÙNG cơ chế MOM15 → ICC cao → n_eff không lên. Đổi subset-breadth KHÓ phá trần u1 (×1.5). Dự báo MASTER: u1 nhiều khả năng vẫn fail; giá trị (nếu có) là ở **giữ được ret-2025 GẦN T170 mà vẫn thêm cược 2023/24** — tức "ít tệ hơn BRC", chưa chắc "hơn T170". Sim + recon phân giải.

## 0. LUẬT — như B2 (không nới)
An toàn (HOLDOUT 20251231/242/push/thư mục bảo vệ/index.lock đợi-30s-không-xoá); sim CHẠY KAGGLE (không đụng shadow-c3, không chạy sim nặng Oracle); PREREG trước; cổng tái lập T170 md5 `efb793e2468ca3a7318da0f0ad23d4fc`; **cổng OFF byte-identical**; `x1_rates.py --appetite current --k`; per-year (2021 = H2 only, ghi rõ); n_eff qua `icc_anova()`; logging chuẩn (Java SLF4J, Python logging).

## BƯỚC 1 — RECON 0-SIM (làm TRƯỚC, cổng GO/NO-GO, chống đốt sim vô ích)
Mục tiêu: biết subset-breadth có TÁCH được các năm tốt hơn all-coin không, TRƯỚC khi sim.

### 1.1 Book-composition T170 (pivot của định nghĩa "relevant breadth")
Từ printDone.csv T170 (`X1_GS_T170_2021_REPRO/storage/printDone.csv`): phân loại mỗi vị thế theo symbol → nhóm **majors** (BTC, ETH, + top market-cap ổn định — định nghĩa nhóm khoá trước theo danh sách cố định, KHÔNG chọn theo kết quả) vs **alts** (còn lại). Đo: % vị thế T170 là majors vs alts, toàn kỳ + per-year. ⇒ "relevant breadth" = breadth của nhóm T170 THỰC SỰ trade.
- Khoá danh sách majors trước (ví dụ market-cap-top ổn định 2021-2025): BTC, ETH, BNB, SOL, XRP, ADA, DOGE, AVAX, DOT, LINK, TRX, MATIC/POL, LTC — hoặc lấy theo một tiêu chí cố định (cap/volume trung bình toàn kỳ, top-N), ghi rõ tiêu chí trong PREREG. KHÔNG đổi danh sách sau khi thấy gate-profile.

### 1.2 Gate-profile per-year cho các định nghĩa breadth (DESCRIPTIVE — trả lời luôn câu top30/all của Uni)
Tính chuỗi breadth-score causal (all-coin sống trên MA200 của chính nó) cho các universe: **{all-coin, top50-vol, top30-vol, alt-only, major-only}**. Với MỖI cái, áp công thức gate BRC (`gate = 1.0 + 0.7×clip((0.5 − score)/0.5, 0, 1)`) và tính **gate trung bình per-year** 2021H2..2025.
- Bảng chính: gate-tb per-year × 5 định nghĩa. So với all-coin (BRC).
- Câu hỏi phán quyết recon: **có định nghĩa nào cho gate-2025 ≥ 1.60 (siết đúng, gần 1.7 T170-thắng) VÀ giữ gate-2023 & 2024 ≤ 1.20 (nới để lấy breadth) không?** Đây là điều all-coin KHÔNG làm được (all-coin 2025 ~1.5, chưa đủ siết).

### 1.3 Cổng GO/NO-GO (khoá trước)
- **GO** nếu định nghĩa relevant-breadth (theo book T170 §1.1) đạt: gate-2025 ≥ 1.60 VÀ gate-2023 ≤ 1.20 VÀ gate-2024 ≤ 1.20 VÀ gate-2022 ≥ 1.55 (giữ phòng thủ bear). Tức nó TÁCH năm tốt/xấu rõ hơn all-coin.
- **NO-GO** nếu: relevant-breadth per-year ~ trùng all-coin (chênh gate mọi năm < 0.10 → không đổi gì) HOẶC nó siết cả 2023/24 (gate > 1.30 → giết breadth) HOẶC book T170 hoá ra majors-heavy và major-breadth đọc 2025 là "khoẻ" (gate < 1.4 → sẽ nới 2025 → thảm, đúng chiều sai của agent). NO-GO → DỪNG, ghi power_wall "subset-breadth không tách được năm", KHÔNG sim.
- Ngưỡng theo lý lẽ (1.60 gần 1.7-thắng; 1.20 đủ lỏng lấy breadth; chênh 0.10 = đủ khác all-coin để đáng sim), khoá trước.

Output BƯỚC 1: `docs/DIAG_BREADTH_SUBSET.md` + script + json. Trả MASTER: book-comp T170, bảng gate-profile 5 định nghĩa × per-year, GO/NO-GO + định nghĩa relevant-breadth khoá.

## BƯỚC 2 — SIM (chỉ khi BƯỚC 1 GO)
PREREG `docs/PREREG_BREADTH_SUBSET.md` khoá trước.
- **BRM (chính, khoá)**: gate liên tục, breadth = **relevant-breadth (subset T170 trade, khoá ở §1.1)**, gate_up/down/thr = **1.0/1.7/0.50 (KHOÁ y BRC, KHÔNG re-tune)**. Chỉ đổi ĐỊNH NGHĨA breadth so BRC.
- **BRM0 (đối chứng)**: gate flat khớp tổng n ≈ BRM (tách "subset-adaptive" khỏi "giảm chung"; nội suy khớp n, không sweep).
- Baseline dùng lại số: T170 (verify md5), BRC (Bước 7), BR nhị phân (Bước 6).
- k phán quyết = 1 (BRM). {top30/all/major-only...} chỉ DESCRIPTIVE ở recon, KHÔNG vào phán quyết.
- Cơ chế cắm: dùng hạ tầng gate-value CSV của Bước 7 (`RegimeSchedule` đọc cột gate float/ngày, `SIM_REGIME_GATE_VALUE_COL`), chỉ sinh CSV gate-value mới từ relevant-breadth. 0 dòng Java mới kỳ vọng → verify OFF md5 `efb793e2`.

### TIÊU CHÍ (khoá trước, y Bước 7)
- u1 breadth: n_eff_total(BRM) ≥ 1.5× T170 (=909).
- u2 khẩu vị current: PASS, UW ≤ 200 MỌI NĂM + CAGR ≥ CI-floor T170.
- u3 vs incumbent: maxDD ≤ −14.8% VÀ UW ≤ 115.
- u4 tách đúng: UW(BRM) < UW(BRM0) VÀ **ret-2025(BRM) ≥ ret-2025 T170 × 0.95** (bằng chứng subset-breadth giữ 2025 GẦN T170 — cái BRC/BR đều không làm được: BRC ret-2025 28.7, BR 22.9, T170 32.7).
- u5 giữ uptrend: CAGR 2023 & 2024 BRM ≥ 90% gate-1.0.
- THẮNG = BRM đạt u1–u5. Nếu u1 fail nhưng BRM **giữ ret-2025 ≥ 0.95×T170 VÀ UW mọi năm ≤ 200 VÀ thêm cược 2023/24 (n > T170)** ⇒ ghi "ứng viên incumbent/shadow-forward" (khác NULL), MASTER đánh giá mức vượt, KHÔNG tự tuyên THẮNG. NULL = không tách được (u4 fail) hoặc vẫn vỡ UW.

## 3. QUY TRÌNH
BƯỚC 1 recon → GO/NO-GO báo MASTER. Nếu GO: PREREG commit → sinh CSV gate-value từ relevant-breadth + profile BRM/BRM0 → cổng OFF md5 → sim Kaggle tuần tự (T170 verify, BRM, khớp-n rồi BRM0) → u1–u5 per-year, so BRM vs BRC vs BR vs T170 → `docs/RESULT_BREADTH_SUBSET.md` verdict + đối chiếu dự báo → commit branch module (KHÔNG push) → cập nhật project memory (`round_2026-09-20...md` + index) → dọn wfo_ds tạm, giữ printDone/sim.out.
OFF không byte-identical → DỪNG báo MASTER.

## 4. Ý NGHĨA
- BRM giữ ret-2025 ~ T170 + thêm cược 2023/24 + khẩu vị pass ⇒ subset-breadth là bản breadth ĐẦU TIÊN không hi sinh 2025 ⇒ ứng viên shadow-forward (sau khi feed shadow sửa xong). Vẫn KHÔNG tuyên đổi incumbent từ 1 sim.
- NO-GO recon hoặc NULL sim ⇒ breadth (mọi định nghĩa subset) đã cạn với dữ liệu hiện có ⇒ ĐÓNG breadth như lever, ghi power_wall, chuyển TASK D (event-alpha độc lập MOM15) làm hướng chính cho mục tiêu tăng n_eff.

## 5. Sau mỗi bước: cập nhật project memory, báo MASTER GO/NO-GO (Bước 1) hoặc verdict + u1–u5 + bảng so (Bước 2).
