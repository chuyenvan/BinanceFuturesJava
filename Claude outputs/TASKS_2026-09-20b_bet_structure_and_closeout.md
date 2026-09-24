# TASKS 2026-09-20b — Bigdown là nhân tố đồng-thua? + Điều phối vào lệnh động (pacing) thay gate fix cứng + close-out

Người soạn: MASTER (Claude). Người thực thi dự kiến: agent Sonnet. Chủ sở hữu quyết định: Uni.
Trạng thái: **KẾ HOẠCH — chưa thực thi gì.** Uni redirect 09-20 (đọc §0.5).

Tiền đề đọc trước (Oracle, branch `module`): `docs/result/RESULT_HEDGE_OVERLAY_A.md` (`38691b6`), `docs/design/DESIGN_HEDGED_BOOK.md` (`8a081ae`), `docs/analysis/ANALYSIS_BETA_DECOMP_T170.md` (`61a7fc7`), `docs/result/RESULT_VOL_TARGET.md` (`99208f7`), `docs/result/NBETS_RESULT.md` (mục 4.2, 5.1, 8), `docs/result/TICKLOG_RESULT.md`, `research/analysis/{nbets_step3_crosssec.py, hedge_overlay_a.py, c3_rates.py, beta_decomp_t170.py}`. Java: `BudgetManagerSimple.java`, `TradeUtils.java` (`managerBudget`/`throttle`), `Configs.java`, `SimulatorMarketLevelTicker1MStopLoss.java`, `VolTargetSizing.java`. Project memory: `round_2026-09-20_beta_decomp_and_data_survey.md`, `power_wall.md`, `oracle_access.md`.

---

## 0. LUẬT CHUNG — áp dụng cho mọi task, không nới

1. **An toàn tuyệt đối**: KHÔNG đụng HOLDOUT 2026 (`SIM_END_DATE=20251231`, `HoldoutSeal`); KHÔNG ssh box 242; KHÔNG `git push`; KHÔNG xoá `aerospike-data/ predwf_* claudedata/ featv2/ ledger/ wfo_ds_x1_2021/ derivs_store/ kaggle_data_hpo/ ds_feat*/ java/fsrun/ selector_pred_out/ shadow_c3/`; `.git/index.lock` → đợi 30s, không xoá.
2. **Oracle 1 job nặng/lần**: trước mọi sim/xgboost: `free -g` ≥ 12G VÀ `pgrep -af "Simulator|ExportWfo|s1_hpo|xgboost"` rỗng VÀ `pgrep java` rỗng. Nếu Uni đã restart shadow-c3, phải dừng shadow trước sim và ghi rõ trong log (không tự kill mà không ghi lại).
3. **Pre-registration**: PREREG commit TRƯỚC khi tính bất kỳ số nào của giả thuyết; không đổi ngưỡng sau khi thấy kết quả; mọi sửa thiết kế phải ghi "trước/sau khi thấy kết quả" (mẫu: `RESULT_HEDGE_OVERLAY_A.md` mục 5).
4. **Cổng tái lập T170** trước mọi sim variant: chạy T170 OFF-config, `md5 printDone.csv` phải = `efb793e2468ca3a7318da0f0ad23d4fc`. Không đạt → dừng, báo, không chạy variant.
5. **Khẩu vị rủi ro HIỆN HÀNH** (round 09-19): `maxDD ≤ 30 · UW ≤ 200 · quý ≥ −15 · coin ≤ 15%`. ⚠️ `x1_rates.py::hard_by_year` vẫn in theo ngưỡng CŨ (15/120/0/−5) — chấm lại theo mới khi báo cáo (TASK C sửa gốc).
6. **Luật CI**: block-bootstrap 72h; `inflate(k)=sqrt(2·ln k)` với k = số biến thể khai báo; `x1_rates.py --k` bắt buộc khi so CAGR.
7. Kết quả Kaggle chỉ so Kaggle, Oracle chỉ so Oracle (ARM64 vs x86_64).
8. Logging: Python `logging` (cấm `print`); Java SLF4J.
9. Sau mỗi task: cập nhật project memory (đọc lại trước khi ghi).

---

## 0.5 REDIRECT CỦA UNI (09-20) — ĐỌC KỸ, ĐÂY LÀ TRỤC CỦA VÒNG NÀY

Nguyên văn ý Uni: *"cần đo tách và chung với bigdown, nó là nhân tố ảnh hưởng; cần đưa bigdown khỏi rủi ro vào ồ ạt; và cách khi đã thấy tín hiệu cần nới rộng hoặc phương pháp nào đó chứ fix cứng như hiện tại — có khi 1 tiếng bắt vài chục tín hiệu bigdown là nhồi hết vốn vào; hoặc điều phối bằng tỉ lệ vốn đang rảnh hay gì đó."*

Diễn giải của MASTER (khoá làm định hướng thiết kế):
- **bigdown = cú sập mạnh của thị trường** (BTC hoặc toàn universe rơi nhanh). Giả thuyết của Uni: bigdown là **nhân tố đồng-thua** (co-loss) chi phối maxDD/UW — đúng chỗ ICC-trên-ROI-cuối KHÔNG đo được (nó đo tương quan *kết quả*, không đo *đồng-thua đuôi*). ⇒ TASK A phải đo **có điều kiện theo bigdown**: tách (trong/ngoài bigdown) và chung.
- Vấn đề vận hành Uni lo: khi thị trường sập, gate/candidate đẻ hàng loạt tín hiệu cùng lúc ("vài chục/giờ") → hệ **nhồi hết vốn vào một cú** → đồng-thua. Muốn cơ chế **điều phối vào lệnh động** thay cho gate fix cứng: giãn theo thời gian, hoặc size theo **tỉ lệ vốn đang rảnh**, hoặc giảm admission khi phát hiện bigdown regime.

⚠️ **Đính chính risk-first (quan trọng, phải giữ trong đầu suốt vòng)**: kịch bản "1 tiếng vài chục tín hiệu nhồi hết vốn" **KHÔNG xảy ra ở T170** (k̄=3.55 vị thế đồng thời, 77% giờ trống, ~10 lệnh/ngày). Nó là kịch bản của **gate MỞ (T100)** hoặc của tầng **candidate trước gate**. Nghĩa là **gate 1.70 fix cứng đang kiêm luôn vai trò chống-bigdown-nhồi**. Kế hoạch phải: (i) đo hiện tượng nhồi ở T100/candidate, không phải T170; (ii) chỉ có ý nghĩa hạ gate (breadth) NẾU thay được vai trò chống-nhồi của gate bằng một cơ chế pacing đúng. Hai thứ đi thành **một cặp**.

Ba bẫy phương pháp phải chặn trong PREREG:
- **Causal bắt buộc**: "nới khi đã thấy tín hiệu" chỉ được dùng thông tin tới thời điểm t. Nới dựa trên biết trước lệnh nào thắng = curve-fit, chết trên holdout.
- **Đụng admission = đụng core sim** (rủi ro y hệt Phương án B hedge đã bị chặn): confound (đổi admission → đổi tập lệnh → không tách hiệu ứng) + rủi ro phá md5. Bắt buộc recon điểm cắm an toàn kiểu `SIZE_VOL_TARGET_MODE` (TASK5, byte-identical OFF) TRƯỚC khi viết code.
- **Chống "giảm size đều trá hình"**: nếu pacing không nhắm đúng bigdown (đo ở TASK A) mà chỉ giảm size chung → sẽ NULL như TASK5 COIN. Phải có một biến thể đối chứng "giảm size đều, không điều kiện regime" để chứng minh phần thắng (nếu có) đến từ *nhắm bigdown*, không phải từ *giảm size*.

---

## 1. HƯỚNG — TÓM TẮT

| # | Task | Model | Sim? | Mục đích | Điều kiện |
|---|---|---|---|---|---|
| A | **Bigdown là nhân tố đồng-thua?** đo tách/chung + đo "nhồi ồ ạt" (T170 vs T100) | Sonnet | **0** | Xác nhận tiền đề + định lượng hiện tượng nhồi → GO/NO-GO cho B | chạy ngay |
| A-recon | Recon admission/budget/throttle/sizing hiện tại (đọc code) | Sonnet | 0 | Biết "fix cứng hiện tại" chính xác là gì; tìm điểm cắm an toàn | chạy ngay, song song A |
| B | **Điều phối vào lệnh động (pacing) regime/capital-aware** | Sonnet | 3–4 run | Thay gate fix cứng bằng pacing để lấy breadth mà không nhồi bigdown | chỉ khi A = GO **và** A-recon tìm được điểm cắm an toàn |
| C | Close-out vòng hedge + vệ sinh + chấm lại ngưỡng | Sonnet | 0 | Sổ sách đúng, tái lập được | chạy ngay, song song A |
| D | (ghi nhận, chưa brief) Alpha mới listing/delisting | — | — | Tăng số NGÀY có cược bằng trigger không tương quan MOM15 | Uni quyết sau A/B |

**KHÔNG làm**: Phương án B hedge (Java); retune PORTFOLIO vol-target; quét gate/size dạng grid; mở HOLDOUT; mở lại OFI khi chưa có thiết kế universe mới.

---

## 2. TASK A — BIGDOWN LÀ NHÂN TỐ ĐỒNG-THUA? (descriptive, 0 sim, ~1 ngày)

### 2.1 Câu hỏi
(Q1) Đồng-thua (co-loss) của T170 có tập trung trong bigdown không? maxDD/UW đến từ bigdown bao nhiêu %? (Q2) Ở gate mở (T100), thị trường sập có gây "nhồi ồ ạt" (nhiều lệnh mở mới/giờ, vốn triển khai vọt) không, và đó có phải nguồn đồng-thua không? (Q3) ICC/đồng-thua **tách theo bigdown** khác gì so với **chung**? (Q4) Đơn vị "vị thế" thật (dòng printDone = lệnh hay leg DCA)?

### 2.2 Dữ liệu (chỉ đọc)
- T170: `/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv` (1089) + `logs/sim.out`.
- T100 (gate 1.0, 2559): `/home/ubuntu/java/devrun/X1_C3_FULL_2021/storage/printDone.csv` + `logs/sim.out`.
- `ls /home/ubuntu/java/devrun/` — nếu còn run gate-scale trung gian (từ `AUDIT_GATEDYN_GD92`) → đưa vào bảng liều-đáp ứng theo độ chặt gate; **không chạy run mới**.
- BTC 1h: `/home/ubuntu/java/fsrun/CLOSES_1H.bin` (loader `beta_decomp_t170.py::btc_at_or_before`, `trend_rank_ic.py::load_closes`; đã lọc `ts<2026-01-01`).
- Universe breadth: nếu có sẵn per-symbol closes trong `CLOSES_1H.bin`/`featv2` → tính % coin đỏ/giờ; nếu quá tốn thì chỉ dùng BTC-based (BD1) và ghi rõ đã bỏ BD2 vì chi phí.
- Tái dùng: `icc_anova()`, `c3_rates.py::{trades,equity}`, `hedge_overlay_a.py::k_bar`.
- Nếu tick/candidate log tồn tại (`TICKLOG_RESULT` nói `TickDecisionLog`, nhưng `pos.bin` từng không đọc được — kiểm `ls`): dùng để đếm **candidate signals/giờ** (số tín hiệu trước gate). Nếu không có → dùng **T100 admitted làm proxy** cho "nếu gate mở thì burst cỡ nào", ghi rõ là proxy.

### 2.3 Định nghĩa bigdown — đo SONG SONG nhiều định nghĩa (causal), Uni chọn sau
Không chốt 1 ngưỡng trước; đo dose-response để thấy độ nhạy (đây là descriptive, không phải variant nên không tính vào k):
- **BD1 (BTC drawdown)**: cờ giờ t nếu BTC rơi ≤ −X% trong cửa sổ lùi H giờ, với (X,H) ∈ {(5%,24h),(8%,24h),(10%,72h)} và một bản theo quantile: 1h-return ≤ q02/q05 của rolling-60-ngày.
- **BD2 (breadth, nếu tính được)**: ≥ P% universe có 1h-return < 0 tại t, P ∈ {70,80,90}.
- **BD3 (severity buckets)**: chia cường độ mild/moderate/severe để xem liều-đáp ứng.
Tất cả cờ bigdown phải **causal** (chỉ dùng dữ liệu tới t). Ghi rõ công thức từng định nghĩa trong PREREG.

### 2.4 PRE-REG lite — commit `docs/prereg/PREREG_BIGDOWN_STRUCT.md`, metric khoá TRƯỚC
Mô tả, không verdict THẮNG/THUA, chỉ cổng GO/NO-GO cho B (§2.6). Mỗi run, cửa sổ 2021-07-01..2025-12-31:

**(M1) Đơn vị dòng**: dùng `sym`,`time_order`,cột leg/blk; xác định 1 dòng = 1 lệnh symbol hay 1 leg DCA. Báo số dòng, số "symbol-episode" (gộp dòng cùng `sym` chồng lấn thời gian), tỉ lệ dòng/episode. Mọi metric burst/k̄ báo theo **cả hai** đơn vị (dòng và episode).

**(M2) Nhồi ồ ạt (trọng tâm Uni)**: phân bố **số lệnh mở MỚI** trong cửa sổ trượt 1h và 4h — tách `trong-bigdown` vs `ngoài-bigdown`, cho **T170 VÀ T100** (và run trung gian nếu có). Báo p50/p90/p99/max mỗi nhóm. Câu hỏi trả lời trực tiếp: "có giờ nào mở vài chục lệnh mới không, và ở gate nào, trong bigdown hay không". Kèm: candidate signals/giờ (tick log hoặc proxy T100) tách theo bigdown.

**(M3) Vốn triển khai**: Σnotional_mở / equity theo giờ — p50/p90/p99/max, tách trong/ngoài bigdown, cho T170 & T100. Trả lời "khi sập có all-in không". Kèm: tại các thời điểm **bắt đầu** một chuỗi bigdown, vốn nhảy từ bao nhiêu lên bao nhiêu trong 1h/4h.

**(M4) Đồng-thua tách/chung (trọng tâm Uni)**:
- ICC (cohort ngày vào lệnh; 72h; tuần) trên: (i) ROI thô, (ii) ROI winsorized p1/p99, (iii) chỉ báo lỗ `1[ROI<0]`, (iv) lỗ nặng `1[ROI<p10 của run]` — báo J,N,k₀.
- **Có điều kiện bigdown**: gán mỗi lệnh nhãn "vào-trong-bigdown" (theo ngày/giờ vào) VÀ "trải-qua-bigdown-khi-đang-mở" (bigdown rơi vào [start,end)) — hai nhãn riêng. Tính ICC và tỉ lệ lỗ/lỗ nặng **riêng cho nhóm bigdown vs non-bigdown**. Giả thuyết Uni: đồng-thua tập trung ở bigdown.
- **Overdispersion đuôi φ**: cohort ngày có k_j≥3, số lệnh lỗ ~Binomial(k_j,p̂) nếu độc lập; φ = Σ(L_j−k_j p̂)²/(k_j p̂(1−p̂))/(J−1). Tính φ **toàn bộ, chỉ-bigdown, chỉ-non-bigdown** (cả cho "lỗ" và "lỗ nặng"). φ≈1 độc lập, φ≫1 đồng-thua.

**(M5) Phân rã maxDD/UW theo bigdown**: từ sim.out, chuỗi equity; đánh dấu giai đoạn bigdown; báo % tổng drawdown depth và % số ngày dưới nước xảy ra TRONG giai đoạn bigdown. 10 ngày equity tệ nhất: có phải bigdown không, mở bao nhiêu lệnh mới, % lệnh lỗ trong ngày.

**(M6) n_eff**: `n_eff_total = Σ_j k_j/(1+(k_j−1)·ICC_ROI)` (cohort ≥2) và bản NBETS `J·k̄/(1+(k̄−1)·ICC)`; báo cả hai + trần 1/ICC. Tách theo đơn vị dòng/episode.

**(M7) Lệnh biên T100∖T170**: kiểm T170 ⊂ T100 bằng khoá (`sym`,`start`). Nếu đúng, tách tập "biên" (có ở T100, không ở T170) → báo riêng ROI trung bình (CI bootstrap-cohort), % thắng, ICC, φ, VÀ **tỉ lệ lệnh biên rơi vào bigdown**. Đây là số quyết định cho B: lệnh biên có alpha không, và có phải chủ yếu là lệnh-bigdown (đồng-thua cao) không.

### 2.5 Dự báo ghi trước (để không "giải thích xuôi")
MASTER dự báo: (a) φ(lỗ,bigdown) ≫ φ(lỗ,non-bigdown) ở CẢ hai run — bigdown đúng là nhân tố đồng-thua; (b) T100 có burst nhồi trong bigdown rõ hơn T170 nhiều (p99 lệnh mới/giờ và Σnotional/equity cao hơn); (c) phần lớn maxDD của cả hai đến từ bigdown; (d) lệnh biên T100∖T170 tập trung bất cân xứng vào bigdown và có φ cao hơn lõi, ROI trung bình dương nhưng mỏng. Nếu sai, ghi là sai.

### 2.6 Cổng GO/NO-GO cho TASK B — KHOÁ TRƯỚC
**GO** nếu ĐỒNG THỜI:
- (g1) φ(lỗ) chỉ-bigdown > φ(lỗ) chỉ-non-bigdown với tỉ số ≥ 1.5 (bigdown thật sự là nhân tố đồng-thua — nếu không, pacing theo bigdown vô nghĩa);
- (g2) ≥ 50% depth của maxDD (T100) xảy ra trong bigdown (có gì đáng để pacing cắt);
- (g3) lệnh biên T100∖T170 có ROI trung bình > 0 với CI-cohort 90% không nằm hoàn toàn dưới −0.5pp (breadth không phải alpha âm);
- (g4) A-recon tìm được **điểm cắm admission/sizing giữ được cổng OFF byte-identical** (nếu không có, B phải hoãn — không đụng core mù như Phương án B hedge).

**NO-GO** nếu vi phạm bất kỳ điều nào — ghi kết luận tương ứng vào `power_wall.md`: bigdown không phải nhân tố đồng-thua / breadth không có alpha / không có điểm cắm an toàn ⇒ hướng pacing đóng.
Lý do ngưỡng: g1 tỉ số 1.5 = đồng-thua bigdown phải trội rõ mới đáng nhắm riêng; g2 50% = pacing chỉ cứu được phần rủi ro nằm trong bigdown; g3 như cũ (không thêm cược alpha âm); g4 là bài học Phương án B.

### 2.7 Đầu ra
`docs/analysis/ANALYSIS_BIGDOWN_STRUCT.md` + `research/analysis/bigdown_struct.py` (+ json `research/analysis/out/`), commit. Cập nhật memory. Trả lời MASTER: bảng metric M1–M7 (2–3 run), GO/NO-GO với số, và gì không tính được.

---

## 3. TASK A-recon — ADMISSION/BUDGET/SIZING HIỆN TẠI (đọc code, 0 sim, ~0.5 ngày, song song A)

Mục đích: biết chính xác "fix cứng hiện tại" là gì, để thiết kế pacing đúng chỗ và tìm điểm cắm an toàn. Đọc, không sửa, không sim. Trả lời:

1. **Admission**: một tín hiệu BUY đi qua những cổng nào để được mở? (`EntryGate` + `SIM_GATE_DYN_SCALE`, `TradeUtils.managerBudget`, `BudgetManagerSimple`). Vẽ luồng từ candidate → admitted.
2. **Có cap vốn triển khai không?** Hiện có giới hạn tổng notional/số vị thế đồng thời không, hay chỉ gate + budget? Nếu "nhồi hết vốn" bị chặn bởi một cap sẵn có thì cap đó là gì, giá trị bao nhiêu (⇒ có thể vấn đề Uni lo đã một phần được cap giải quyết — phải nói rõ).
3. **Có rate-limit vào lệnh theo thời gian không?** (số lệnh mở mới/đơn vị thời gian). Gần như chắc là KHÔNG — xác nhận.
4. **Sizing quyết theo gì?** fixed fraction? theo equity? theo vốn rảnh? DCA grid scale? `SIM_F_BASE`/`DCA_GRID_SCALE` (GS wave-1 nói đây là 2 đòn size mạnh nhất) vào ở đâu.
5. **Điểm cắm cho pacing giữ OFF byte-identical**: `VolTargetSizing` (TASK5) cắm ở đâu trong luồng sizing, và một rule pacing (điều tiết size/admission theo vốn rảnh hoặc regime) có cắm được cùng chỗ với 1 flag mặc-định-OFF không? Nếu cắm được ở tầng sizing (nhân multiplier) thì rẻ+an toàn; nếu bắt buộc sửa admission (chặn/hoãn lệnh) thì đắt+rủi ro như Phương án B — nêu rõ chi phí dòng và rủi ro md5.

Đầu ra: `docs/analysis/RECON_ADMISSION_PACING.md`, commit. **Không code cơ chế.** Đây là recon quyết định B khả thi qua config hay phải hoãn.

---

## 4. TASK B — ĐIỀU PHỐI VÀO LỆNH ĐỘNG (PACING) (chỉ khi A=GO & A-recon có điểm cắm; ~1.5–2 ngày)

### 4.1 Giả thuyết
H_B: Thay vai trò "chống bigdown-nhồi" của gate fix cứng bằng một **cơ chế pacing động regime/capital-aware**, ta có thể **hạ gate để lấy breadth** (nhiều lệnh/ngày hơn, k̄ cao hơn) mà **maxDD/UW không xấu hơn T170**, và `n_eff_total` tăng — vì pacing cắt đúng phần đồng-thua bigdown (đo ở TASK A) thay vì cắt size đều.
H0 (NULL): pacing không cải thiện n_eff ở rủi ro cố định, HOẶC phần thắng chỉ do giảm size đều (biến thể đối chứng P0 cũng thắng bằng).

Đây KHÔNG phải "biến thể quanh winner" (luật B4) và KHÁC GS wave-1 (quét gate/size độc lập, chấm CAGR ở size cố định): nó kiểm một **rule cấu trúc regime-conditional** chưa từng có trong hệ.

### 4.2 Biến thể — thiết kế sau A-recon, khai báo TRONG PREREG, tính inflate(k) đúng
Nền chung: gate hạ về mức cho breadth (đề xuất gate 1.0 = T100, hoặc mức trung gian A-recon gợi ý). Trên nền đó, các cơ chế pacing (chọn tối đa 2–3, mỗi cái 1 giá trị tham số chốt trước, KHÔNG quét):
- **P0 (đối chứng, BẮT BUỘC)**: gate hạ + giảm size đều (multiplier cố định = tỉ lệ để Σnotional/equity trung bình khớp T170), KHÔNG điều kiện regime. Đây là mốc để chứng minh P1–P3 thắng nhờ *nhắm bigdown*, không nhờ *giảm size*.
- **P1 capital-availability pacing**: size lệnh mới ∝ (vốn rảnh/vốn tổng), hoặc cap "vào tối đa X% vốn rảnh mỗi giờ" — không all-in. Tham số X chốt trước (đề xuất từ M3 của TASK A: đặt cap ở p90 lịch sử của T170).
- **P2 burst rate-limit**: tối đa K lệnh mở mới/cửa sổ W giờ; vượt → bỏ tín hiệu yếu hơn (theo điểm gate). K,W chốt trước từ M2.
- **P3 regime-conditional (nhắm bigdown trực tiếp)**: khi cờ bigdown causal bật (định nghĩa Uni chọn từ TASK A), giảm admission/size theo hệ số cố định. Đây là biến thể gần ý Uni nhất ("đưa bigdown khỏi rủi ro vào ồ ạt").
Mặc định MASTER đề: chạy **P0 + P3** (2 biến thể, k=2) — P3 là giả thuyết chính, P0 là đối chứng. P1/P2 chỉ thêm nếu Uni muốn (mỗi cái +1 vào k).
Mỗi biến thể là 1 profile mới, `git diff` với `x1_gs_t170.properties` phải chỉ ra đúng các khoá đã khai báo. Rule phải **causal**. Cổng OFF byte-identical bắt buộc cho flag mới.

### 4.3 Quy trình
1. PREREG `docs/PREREG_PACING.md` commit trước: giả thuyết, định nghĩa bigdown đã chọn, biến thể + tham số + k, 4 tiêu chí (dưới), ngưỡng, dự báo.
2. Oracle rảnh (§0.2). Cổng T170 md5 `efb793e2` (§0.4). Cổng OFF byte-identical cho từng flag pacing mới.
3. Chạy lần lượt (≈13 phút/18 fold mỗi run), không song song.
4. Tính theo **khẩu vị hiện hành**; `x1_rates.py --k <k>` cho CI CAGR; `n_eff_total` bằng script TASK A; **phân rã maxDD theo bigdown** (M5) cho mỗi biến thể — để thấy pacing có thật sự cắt drawdown bigdown không; bảng theo năm.
5. `docs/RESULT_PACING.md`: 4 tiêu chí ✅/❌ mỗi biến thể; verdict.
6. Dọn `wfo_ds_*` tạm; giữ `printDone.csv`+`sim.out` từng biến thể.

### 4.4 Bốn tiêu chí (khoá trước)
(t1) `n_eff_total` ≥ 1.5× T170; (t2) PASS mọi ràng buộc cứng khẩu vị hiện hành; (t3) maxDD và UW không xấu hơn T170 quá 25% tương đối; (t4) **% depth maxDD trong bigdown giảm so với chính biến thể ở nền gate-hạ-không-pacing** (P0) — bằng chứng cơ chế đúng. THẮNG = một biến thể P1/P2/P3 đạt cả 4 VÀ vượt P0 ở (t1) hoặc (t4). NULL = không biến thể nào đạt, hoặc P0 đạt bằng biến thể regime (phần thắng chỉ là giảm size). HỖN HỢP = còn lại (không khuyến nghị đổi incumbent).

### 4.5 Ý nghĩa quyết định
THẮNG ⇒ đề xuất Uni cân nhắc incumbent mới **chỉ sau** shadow paper song song ≥1 tháng (PLAN_SHADOW_T170_PARALLEL) — không đổi live vì 1 run.
NULL/HỖN HỢP ⇒ ghi `power_wall.md`: pacing động đã đo, đóng; gate fix cứng vẫn là cách kiểm soát bigdown tốt nhất; power T170 chỉ còn đường alpha mới (TASK D).

---

## 5. TASK C — CLOSE-OUT + VỆ SINH (0 sim, 2–3 giờ, song song A)

1. **Chú thích `RESULT_HEDGE_OVERLAY_A.md` mục 5, thêm (E) — phát hiện khi MASTER review, sau khi RESULT đã commit**: thay đổi (B) làm guard `MIN_OBS=20` vô hiệu (`rolling_beta()`: `valid = np.isfinite(y) & np.isfinite(x)` với `y=dpnl`,`x=z` ⇒ ngày `Nopen=0`/z=0 vẫn được đếm là quan sát ⇒ cửa sổ 60 ngày luôn "đủ 20 obs" dù chỉ 3–5 ngày có vị thế ⇒ β̂ nhiễu, hedge notional 6.1× equity, ICC×4.3/maxDD/UW là artefact). Khẳng định verdict NULL không đổi (lý do thật: r²=0.031, TASK1). **Tuỳ chọn mô tả ≤30 phút**: chạy `hedge_overlay_a.py` với β cố định = beta FULL-period in-sample per-notional (biến môi trường mới `HEDGE_BETA_CONST`, gắn nhãn "cận trên lạc quan"), chỉ báo ICC/maxDD/UW để cho thấy hedge "tốt nhất có thể" cũng không giảm ICC — nếu làm, ghi rõ là số mô tả thêm sau.
2. **Commit** `profiles/x1_gs_t170_vt_coin.properties`, `x1_gs_t170_vt_portfolio.properties` (đối chiếu tham số với `RESULT_VOL_TARGET.md`). Xử lý 5 json `research/analysis/out/*` untracked (tìm vòng sinh qua `git log -S`; commit kèm ghi chú hoặc chuyển scratch). Kiểm `git show --stat 38691b6` có `dump_funding_btc.py` chưa; nếu chưa, commit từ `/home/ubuntu/hedge_a/`.
3. **`x1_rates.py --appetite {old,current}`** (mặc định `current`: 30/200/−15/coin15; giữ `old` để tái lập). Thêm bảng "chấm theo khẩu vị hiện hành" vào `RESULT_VOL_TARGET.md` và `RESULT_HEDGE_OVERLAY_A.md` (không xoá bảng cũ). Xác nhận T170 PASS theo cả hai.
4. **Docs Oracle**: `docs/notes/power_wall.md` (repo) thêm banner đính chính C2b/T170 (giống project memory); `docs/runbooks/AGENT_RUNBOOK.md` sửa RSS shadow 1.7G→2.6–3.2G; `docs/index.md` banner thêm dòng vòng 09-20.
5. Cập nhật project memory.

---

## 6. TASK D — ALPHA MỚI (chưa brief chi tiết, Uni quyết sau A/B)
Nếu A/B cho thấy breadth/pacing không mua được power, đường còn lại để tăng số cược độc lập T170 là **thêm ngày có cược bằng trigger không tương quan MOM15** (hiện ~110/1644 ngày). Ứng viên free còn sống: listing/delisting event (`EVENT_DATA_SURVEY.md`). Ràng buộc khi brief: (1) noise control cùng NaN-mask (bài học OFI); (2) đo tầng xếp hạng (rank-IC CPU) trước; (3) kiểm lookahead announcement vs effective. Chưa làm gì tới khi Uni chốt.

---

## 7. VIỆC CỦA UNI (không giao agent)
- shadow-c3 DOWN từ 09-20 06:13 (API key −2014): cập nhật key, restart `shadow-c3.service`.
- Quyết: định nghĩa bigdown ưu tiên (sau khi thấy dose-response TASK A); có thêm biến thể P1/P2 cho TASK B không (mặc định chỉ P0+P3); có làm TASK D không.
- Quyết mua L2 depth (Tardis ~$4.5–14.8k/năm) — chưa cần bây giờ.
