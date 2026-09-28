# B_bugs — Verdict nào có thể SAI vì lỗi harness / confound / định nghĩa (audit đối kháng, 2026-09-28)

Phạm vi: đọc `docs/` + `research/analysis/*.py` đã giải nén. KHÔNG chạy sim, KHÔNG truy cập Oracle/Kaggle.
Nhãn: **[ĐO]** = số/dòng có trong doc/code (ghi file:dòng) · **[SUY LUẬN]** = lập luận của auditor · **[KHÔNG RÕ]** = doc không đủ.

---

## 0. TÓM TẮT RỦI RO (đọc trước)

1. **Lỗi chiều điểm ở OFI_MONEY ĐƯỢC XÁC NHẬN BẰNG CODE, verdict chưa chạy lại.** [ĐO] `ofi_money_score.py:149`
   và `:165`, `ofi_money_ext.py:106` đều dùng `np.argsort(-score)` (điểm CAO trước), trong khi `pred_ofi_*_v2`
   là `score = −pred` (điểm THẤP = tốt; `RESULT_TAIL_ROBUST_RULERS.md:70-77`: corr(score, rank pool) của OFI
   = +0,899…+0,937). ⇒ top-K của **cả 3 arm** là **K coin TỆ NHẤT**. Triệu chứng đã nằm sẵn trong doc:
   "100 % top-K nằm NGOÀI P32", "top-8 của candidate là major" (`RESULT_OFI_MONEY.md:84-95`). Đường B2 ("đường
   trả lời duy nhất", `:95`, `:196`) dựng pool mở rộng 166.080 cặp **từ chính các top-8 sai chiều** (`:57`) ⇒
   **cả hai đường đo đều không đo đúng đối tượng**. Nhánh sửa chiều ở TAIL_ROBUST dùng seed 42 + **chính pool
   B2 sai đó** (`RESULT_TAIL_ROBUST_RULERS.md` §9.1, §10) ⇒ chưa thay được. Verdict "OFI không ra tiền (lần 3)"
   hiện **chưa có bằng chứng hợp lệ**.
2. **Rào (b′) — rào đang giết 100 % cấu hình — được chốt trên hai tiền đề sai.** [ĐO] (i) Owner chốt 50 % lúc
   09-26 23:17 với "hệ quả đã biết trước: bỏ top-5 % đã ÂM" (`RULERS_CURRENT.md` §8) — con số này sau đó bị
   đính chính là **bịa** (§9.1: bỏ top-5 % vẫn DƯƠNG, `q*` KEEPLEG0 = 19 %). (ii) Doc giải thích cho owner rằng
   (b′) "≈ lệnh TRUNG VỊ phải có lãi" (`RULERS_CURRENT.md:98-99`) — **sai**: `RESULT_RATE_REDUNDANCY.md:28-31`
   đo `median > 0` ở **8/8** biến thể nhưng Σ nửa dưới âm 8/8. Không thấy dòng nào owner **xác nhận lại** (b′)
   sau đính chính [KHÔNG RÕ]; §10.3 chỉ chép lại rào.
3. **Bộ 4 thước chuẩn mâu thuẫn với chính số đo đã có.** [ĐO] Owner chốt `wl_ratio · tf_5 · loss_mean · conc_5`
   (`RULERS_CURRENT.md:138`), trong khi `RESULT_TAIL_ROBUST_RULERS.md:169` kết luận `conc_5` **không phân giải
   được** (Δw 4,3–330) và `RESULT_TAIL50_RULER_REDUNDANCY.md:26,148` kết luận `loss_mean ≈ mP|SL` (ρ −0,96)
   **không được vào bộ chuẩn**. ⇒ luật "≥2 thước" trên bộ này thực chất chỉ còn ~2 thước độc lập
   (`wl_ratio`, `tf_5`), và `loss_mean`+`wl_ratio` chung mẫu số "lỗ trung bình".
4. **Tín hiệu duy nhất "sống sót" chưa ai theo.** [ĐO] `MRA4/MRB8/MRB32` đạt D1 trên 3 thước downside
   (`loss_mean`,`wl_ratio`,`max_loss`) ngoài CI vs **cả hai** đối chứng (`RESULT_TAIL_ROBUST_RULERS.md` §6) —
   theo chữ của bộ thước chuẩn mới thì đủ "≥2". Kết luận "kinh tế = 0" của MONEY_RANKER/PNL_RULER dựa trên
   `glift8/netm8` (mean-based, chính dự án đã hạ cấp). Không có vòng xác nhận nào sau 09-27 [ĐO: grep MRB8
   không có doc mới].
5. **Mẫu hình chung:** ~28 lỗi ghi nhận trong 09-12→09-28; **~70 % phát hiện SAU khi công bố**; khi phát hiện
   sau, **đa số KHÔNG chạy lại** — kết luận được giữ bằng lập luận ("hướng không đổi"), bằng biến thể mô tả,
   hoặc bằng việc rào mới đằng nào cũng FAIL. Loại lỗi trội nhất: **định nghĩa thước/luật** (≈10) và
   **đổi luật/đổi nền giữa chừng** (≈7).

---

## 1. DANH MỤC LỖI (09-12 → 09-28, kèm vài lỗi nền cũ còn chi phối)

Cột "Phát hiện": TRƯỚC = trước khi công bố verdict · SAU = sau khi đã có RESULT/commit.
Cột "Chạy lại?": CÓ (chạy lại số) · CHẤM LẠI (tính lại từ output cũ) · KHÔNG.

| # | Ngày | File | Loại | Phát hiện | Verdict bị ảnh hưởng | Chạy lại? |
|---|---|---|---|---|---|---|
| 1 | 09-17 | `audit/AUDIT_CI_INFLATE_STANDARDIZATION.md:196,303` | định nghĩa thước (CI ×1,21 "bao k=3" — sai số học) | SAU | các vòng k≥3 (quá lỏng) + T170 k=2 (quá chặt) | CHẤM LẠI (`AUDIT_READJUDICATE_CI_RESCORE`) |
| 2 | 09-19 | `result/RESULT_DCA_ROUND_CAP.md:3`, `RESULT_DCA_AGG_PERCOIN.md:3` | định nghĩa thước (CI nhân chồng 1,21×1,4823) | SAU | PASS → FAIL | CHẤM LẠI |
| 3 | 09-20 | `result/RESULT_HEDGE_OVERLAY_A.md:217-240` | harness code (guard `MIN_OBS` đếm ngày `Nopen=0`) | SAU (MASTER review sau commit) | ICC×4,3 / maxDD / UW = **artefact**; verdict NULL giữ bằng biến thể mô tả (F) in-sample | **KHÔNG** (cố ý không sửa) |
| 4 | 09-20 | `notes/power_wall.md:14-24` | baseline sai (ICC 0,247 là của C2b, T170 = 0,0516) | SAU | kết luận NBETS "tường power" + lever "thêm vị thế" | KHÔNG (NBETS không đo lại cho T170/KEEPLEG0) |
| 5 | 09-20 | `result/RESULT_S1_FREE_OFI.md:199-214` | confound (missingness = chỉ báo subset symbol) | TRƯỚC (gắn HARNESS_NGHI_NGO) | S1_FREE_OFI | CÓ (V3 universe/multiseed) |
| 6 | 09-22 11:47 | `result/RESULT_SELECTOR_LEG_CUT.md:41-44` | harness infra (marker merge-conflict commit vào `tools/kaggle_sim.py`) | SAU (09-23) | mọi sim Kaggle 09-22 chiều | sửa tool; [KHÔNG RÕ] có run nào bị mất/báo nhầm |
| 7 | 09-22 → nay | `prereg/PREREG_REVERSAL_BOUNCE.md:1,144,232`, `analysis/RECON_EVENT_ALPHA.md:1,142,285` | harness/tài liệu (marker conflict **vẫn còn** trong PRE-REG) | chưa ai sửa | REVERSAL_BOUNCE (nhóm A1 "NULL đáng tin"): 2 bản pre-reg khác nhau cùng tồn tại (ngưỡng 1 % vs "~0,6–1,0 %") | KHÔNG |
| 8 | 09-23 | `result/RESULT_TICK_BLOCK.md:34-40` | harness code (Java `float[]` = 0.0f ⇒ warm-up vô hiệu) | TRƯỚC (bỏ bản 1) | TICK_BLOCK | CÓ |
| 9 | 09-23 | `prereg/PREREG_SELECTOR_LEG_CUT.md:33-40` | định nghĩa công tắc (`SELECTOR_ONLY_ENTRY` tắt BIG_DOWN, không phải selector) | TRƯỚC | SELCUT | CÓ (cờ mới) |
| 10 | 09-23 | `result/RESULT_EXIT_HIGH_N.md:35-44` | baseline sai (arm "GD92-only" của GD92_X_EXIT thực là T170) | SAU | GD92_X_EXIT | CÓ (vòng EXIT_HIGH_N) |
| 11 | 09-23 | `result/RESULT_TAIL_LEVER.md:47-60` | dữ liệu (ma trận giá theo symbol nến đầu ⇒ mất MTM) | TRƯỚC | TAIL_LEVER | CÓ |
| 12 | 09-24 | `result/RESULT_SIM_CADENCE_MATCH.md` §2 | harness ≠ live (sim 1′ cho MỌI leg; live selector 15′) | SAU (cho mọi vòng sim trước 09-24) | mọi verdict sim trên T170/KEEPLEG0 1′ | KHÔNG (chỉ vòng mới dùng `sel15`) |
| 13 | 09-24 | `runbooks/RISK_APPETITE.md:170-192`, `RESULT_INTRADAY_DD` | định nghĩa thước (maxDD ngày che 7,8–10,1 pp; năm xấu nhất xếp sai) | SAU | rào maxDD mọi vòng trước | CHẤM LẠI 4 nền; **vòng 09-27 vẫn dùng ngày** (#26) |
| 14 | 09-24 | `result/RESULT_GATESCALE_SWEEP.md:30-34,317` | đổi luật giữa chừng (chuẩn maxDD đổi khi kernel đang chạy) | trong vòng | GATESCALE_SWEEP | KHÔNG (báo "hướng không đổi") |
| 15 | 09-24 | `result/RESULT_CONC_CAP_HIGHN.md:29-31,127-143` | đổi luật giữa chừng (UW 200→250 nới 09:06, pre-reg 08:37) | trong vòng | CONC_CAP_HIGHN — dưới khẩu vị mới `cc-t100`, `cc-g-cp` **PASS hết rào cũ** | báo thêm; **không mở ứng viên** |
| 16 | 09-24 | `plan/PREP_STAGE2_TRAIN.md:72-74`, `RESULT_PRESCREEN_FEAT.md:138` | định nghĩa nhãn (ghi nhãn selector `maxFav_4h≥0,06`, thật `retEnd_4h>0,015`) | SAU (tái phát, đã từng đính chính 09-06 `AGENT_RUNBOOK.md:335`) | tài liệu/prereg dẫn nhãn sai (vd `PREREG_FEAT_ABLATION.md:78`) | sửa doc |
| 17 | 09-24 | `research/analysis/stage2_score.py:106-112` | đổi luật sau khi thấy số ("hơn" = rank-IC **âm hơn**) | SAU khi xem số | STAGE2 (NULL giữ) | KHÔNG cần (NULL cả 2 cách) |
| 18 | 09-25 | `result/RESULT_MODEL_RULER.md:518-526, 284` | định nghĩa thước (`auc8` đếm trùng tử số) | SAU (phiên song song) | M1 các vòng MODEL_RULER/ARM44/V0 | một phần (`auc8c`); số §13 "phải thay" |
| 19 | 09-25 | `result/RESULT_MODEL_RULER.md` §13.4 | dữ liệu (điểm 72h NaN 100 % mọi bins) | trong vòng | mọi điều kiện "h=72h" | không đánh giá được |
| 20 | 09-25 | `result/RESULT_PNL_RULER.md:203-208`, `RESULT_AUDIT_PNL.md` | số sai lưu hành ("0 chỉ số Δ ngoài CI"; thật 38, đều âm) | SAU | PNL_RULER (kết luận giữ) | CHẤM LẠI |
| 21 | 09-25 | `result/RESULT_STAGE3_SIM_XCHECK.md` §1 | harness infra (bundle ship 16 bin, `funding.bin` phủ 18 fold) | trong vòng | đường đổi-bins Kaggle | chỉ đường đã công bố PASS |
| 22 | 09-26 | `result/RESULT_OFI_MONEY.md:69-73` | harness code (mask `order<K` sai ⇒ `e_t/d_t/net_gr1dv` sai) | TRƯỚC | OFI_MONEY | CÓ |
| 23 | 09-26/27 | `result/RESULT_TAIL_ROBUST_RULERS.md:62-77` | **chiều dấu** (S1/OFI `score=−pred`, lấy nhầm 8 coin tệ nhất) | TRƯỚC (bản đầu bỏ) | TAIL_ROBUST | CÓ |
| 24 | 09-26 | `research/analysis/ofi_money_score.py:149,165`; `ofi_money_ext.py:106` | **chiều dấu** (cùng lỗi #23) | SAU — cảnh báo ở `RESULT_TAIL_ROBUST_RULERS.md:77` | **OFI_MONEY** | **KHÔNG** |
| 25 | 09-26 | `research/analysis/x1_rates.py:29-40` | đổi luật (mặc định khẩu vị `current` 30/200 thay vì `latest` 40/250 ⇒ "mọi verdict PASS/FAIL tính ra bị LỆCH") | SAU | các vòng dùng `x1_rates` giữa 09-24 và 09-26 | sửa code; [KHÔNG RÕ] danh sách verdict chấm lại |
| 26 | 09-26 | `analysis/RULERS_CURRENT.md` §6/§7/§8 → §9.1 | **số bịa** ("bỏ top-5 % đã âm") làm tiền đề chốt rào (b′) | SAU | rào (b′) (chi phối MỌI verdict 09-27) | đính chính số; **rào không được hỏi lại** |
| 27 | 09-26 | `analysis/RULERS_CURRENT.md:98-99` vs `RESULT_RATE_REDUNDANCY.md:28-31,199` | định nghĩa thước (giải thích (b′) ≈ median>0 — sai) | SAU | (b′) | KHÔNG |
| 28 | 09-26 | `runbooks/RISK_APPETITE.md` §8 → §8-ERRATA; `RULERS_CURRENT.md` §11 | định nghĩa thước (gross lệch 46× ⇒ "size 0,83×" sai) | SAU | CAP70_FEE06, §10.3 | CHẤM LẠI (GROSS_ASYMMAP) |
| 29 | 09-26/27 | `RULERS_CURRENT.md:138` vs `RESULT_TAIL_ROBUST_RULERS.md:169`, `RESULT_TAIL50_RULER_REDUNDANCY.md:26,148` | định nghĩa thước (chốt `conc_5` không phân giải + `loss_mean` trùng `mP|SL`) | chưa ai nêu | mọi vòng từ 09-27 | KHÔNG |
| 30 | 09-27 | `result/RESULT_EXIT_STRUCT.md:56,115` | confound size (grid OFF tắt `DCA_GRID_SCALE=6` ⇒ ~1/6 size) | trong vòng | A2/A3 | KHÔNG (chỉ kiểm size-neutral) |
| 31 | 09-27 | `research/analysis/size_count_score.py:151-163` vs `c3_rates.py:94-109` | định nghĩa thước (5 rate tính trên `pnl` USDT, chuẩn là `profit` %) | chưa ai nêu (chỉ ghi "artifact size") | SIZE_COUNT, SHAPE1, FAMILY2 | KHÔNG |
| 32 | 09-27 | `RESULT_SIZE_COUNT.md:87`, `RESULT_SHAPE1…`, `RESULT_FAMILY2…`, `RESULT_EXIT_STRUCT` | vi phạm chuẩn đã chốt (maxDD/UW theo **ngày**, trái `RISK_APPETITE.md:192`) | chưa ai nêu | câu "rào cũ PASS" của các arm | KHÔNG |
| 33 | 09-15 → 09-26 | `audit/AUDIT_READJUDICATE_CI_RESCORE.md:45-47` vs `RESULT_RATE_REDUNDANCY` §9.2 | định nghĩa thước (incumbent T170 thắng trên {win%, TSloss%, meanP}; nay win%≈TSloss%, meanP là đồng nhất thức) | SAU | **chọn T170 → KEEPLEG0 làm nền** | KHÔNG |

### 1.1 Tần suất theo loại (33 mục; 1 mục có thể thuộc 2 loại)

| Loại | Số mục | Ví dụ |
|---|---|---|
| Định nghĩa thước / luật bằng chứng | **11** | #1 #2 #13 #18 #27 #28 #29 #31 #33, CI ×1,21, gross 46× |
| Đổi luật / đổi nền giữa chừng hoặc sau khi thấy số | **7** | #14 #15 #17 #25 #26, #12 (đổi nhịp), baseline T170→KEEPLEG0→sel15 |
| Harness infra / code | **8** | #3 #6 #7 #8 #21 #22 #11, kaggle conflict |
| Baseline / nền sai | **3** | #4 #10 #12 |
| Chiều dấu | **2** (+1 post-hoc #17) | #23 #24 |
| Confound size / grid | **2** | #30 #31 |
| Số bịa / số sai lưu hành | **3** | #20 #26, INVENTORY A16→B16 |
| Nhãn / dữ liệu | **3** | #16 #19 #11 |

**Thời điểm phát hiện:** TRƯỚC công bố ≈ 8/33 (#5 #8 #9 #11 #22 #23 + 2 trong vòng); **SAU công bố ≈ 21/33**;
chưa ai nêu ≈ 4 (#7 #29 #31 #32). **Khi phát hiện SAU**, chạy lại thật (CÓ) chỉ ≈ 2 (#10 #5); CHẤM LẠI ≈ 6;
**KHÔNG chạy lại ≈ 13**. Mật độ: ≈ 2 lỗi/ngày trong 16 ngày, tăng mạnh 09-24→09-27 (≈ 17 mục / 4 ngày) —
đúng giai đoạn thay nền (KEEPLEG0, sel15), thay thước (tail-robust), thay rào (a)/(b′), thay khẩu vị. [ĐO đếm từ bảng]

### 1.2 Ba cơ chế lặp lại [SUY LUẬN]

1. **"Kết luận giữ, lý do thay"**: HEDGE (#3: artefact → "r² thấp"), PNL_RULER (#20), INTRADAY_DD (#13: "0/4
   đổi hướng" nhưng chỉ kiểm 4 nền), GATESCALE_SWEEP (#14), OFI_MONEY (#24: cảnh báo nhưng không chạy lại).
   Lỗi được ghi errata, verdict không bị đặt lại trạng thái "chưa phân giải".
2. **Luật siết chỉ áp cho ứng viên mới, không áp ngược cho incumbent**: T170 chọn trên 3 rate mà 2 rate trùng +
   1 đồng nhất thức (#33); nới UW 250 không mở lại các NULL đóng vì UW 200 (breadth, GD92+L1, cc-t100).
3. **Rào mới "đằng nào cũng FAIL" che các lỗi đo**: từ 09-27 mọi verdict chốt bằng (a)/(b′), nên lỗi rate USDT
   (#31), maxDD ngày (#32), size confound (#30) không đổi verdict — nhưng cũng nghĩa là **bằng chứng thực chất
   của các vòng này = 1 rào**, và rào đó có lỗi tiền đề (#26 #27).

---

## 2. KIỂM ≥12 VERDICT NULL/NO-GO CHI PHỐI KẾT LUẬN "CẠN"

Trục kiểm: (a) nền/đối chứng · (b) chiều điểm · (c) size/grid/DCA đổi ngầm · (d) phí · (e) cửa sổ/universe/nhãn ·
(f) cùng hạ tầng · (g) thước đã hạ cấp / rate trùng.

| # | Verdict (ngày) | Rủi ro | Phát hiện chính (file:dòng) |
|---|---|---|---|
| V1 | **OFI_MONEY** (09-26) — "OFI không ra tiền" | 🔴 **CAO** | (b) `ofi_money_score.py:149,165`, `ofi_money_ext.py:106` `argsort(-score)` trên `score=−pred` ⇒ chọn coin tệ nhất; triệu chứng `RESULT_OFI_MONEY.md:84-95` (100 % ngoài P32, top-8 = major). Pool B2 dựng từ top-8 sai chiều (`:57`). Kiểm hợp lệ (K=32 trùng khít, noise−cand) **không bắt được lỗi chiều**. (g) 3 đường "lần thứ 3" chung nhãn (b) + pool S1 ⇒ không phải 3 bằng chứng độc lập. |
| V2 | **MONEY_RANKER** (09-25) — "kinh tế = 0" | 🟠 TRUNG BÌNH–CAO | (g) chốt bằng `glift8/netm8` (mean-based, `RULERS_CURRENT.md` §6 #5 đề nghị hạ cấp); TAIL_ROBUST sau đó thấy MR đạt D1 trên downside vs cả 2 đối chứng (`RESULT_TAIL_ROBUST_RULERS.md` §6) — không vòng xác nhận. (e) nhãn (b) = WEAK `cap=0,03` cho mọi ứng viên, 1 leg, không gate/DCA/funding (`RESULT_MONEY_RANKER.md` §1; `RESULT_PNL_RULER.md` §6.5) ≠ exit thật. (a) pool = top-K S1 ⇒ ranker chỉ xếp lại trong rổ S1. (d) 0,8 % nhưng Δ bất biến phí (`RESULT_CAP70_FEE06.md:43-45`) ⇒ phí không phải vấn đề. |
| V3 | **PNL_RULER** (09-25) — "đóng trục ranker 45-feature" | 🟠 TRUNG BÌNH | như V2 (cùng nhãn/pool/thước); errata #20. AUDIT_PNL "S1 không đóng góp" (R1−R3 +0,10 pp) chỉ trên **200 tick** (`RESULT_AUDIT_PNL.md` §0(c)) ⇒ CI ±0,6 pp, power thấp. Đóng "trục" từ 1 nhãn + 1 pool + 1 thước mean-based là suy rộng. |
| V4 | **S1_MAXFAV** (09-25) — "bước cuối trục đổi nhãn" | 🟡 TRUNG BÌNH–THẤP | (g) phần tiền dùng `glift8/netm8` (mean-based); nhãn đổi thật (`RESULT_S1_MAXFAV.md:42-49`). Kết luận "tất cả NULL ở trục tiền" kế thừa hạn chế V2/V3. |
| V5 | **STAGE2 / STAGE3** (09-24/25) — giữ 45 feature | 🟡 THẤP–TB | (17) luật "hơn" đảo nghĩa sau khi thấy rank-IC âm (`stage2_score.py:106-112`). STAGE3: "V0 2 rate XẤU" = `mP|SM` + `meanP` (`RESULT_STAGE3_SIM.md` §0) — `meanP` là đồng nhất thức ⇒ thực chất 1. (c) đổi feature ⇒ đổi `symbolPred` ⇒ đổi ngưỡng gate ⇒ `n` +10–17 % (`:§2`) — thử feature bị lẫn hiệu chuẩn gate. (a) nền KEEPLEG0 **1′**, không phải `sel15`. Hướng NULL bền. |
| V6 | **ARM44** (09-25) | 🟢 THẤP | Có `A44−A45` sạch (`RESULT_ARM44.md` §4); tự khai sim không thấy kênh xếp hạng. Chỉ còn: nền 1′. |
| V7 | **EXIT_STRUCT** (09-27) — "không nhồi thêm" | 🟠 TRUNG BÌNH (A2/A3) | (c) grid OFF ⇒ size ~1/6 (`RESULT_EXIT_STRUCT.md:56,115`), không có arm khớp size; size-neutral (b′) vẫn xấu hơn A0 ⇒ kết luận hướng có đỡ. (d) sim 0,8 %/vòng (`RATE_FEE 0,002×1 + SLIP 0,003×2`, `PREREG_EXECUTION_MAKER.md:47`) — doc ghi "0,002/chân" (sai mô tả). Maxdd/UW theo ngày (#32). A1 (bỏ TS168) kết luận bền. |
| V8 | **SHAPE1_EARLY_CUT** (09-27) — "KHÔNG THỂ đạt (a)+(b′) bằng chỉnh tham số" | 🟠 TRUNG BÌNH | (g) 5 rate tính trên USDT (`size_count_score.py:151-163`) ≠ chuẩn `c3_rates.py:94-109` (%), nên "chỉ còn mP\|SL artifact" là sản phẩm của định nghĩa lệch; maxDD/UW ngày. Kết luận "cả HỌ" suy từ 4 arm. Phụ thuộc hoàn toàn rào (b′) (#26 #27). |
| V9 | **FAMILY2_TP_SL** (09-27) | 🟢 THẤP | Lỗ nặng, bền với phí: [SUY LUẬN] N2 (TP1 %/SL1 %, win 41,8 %) ở chi phí thật 0,2 % vẫn ≈ 0,418·0,8 − 0,582·1,2 ≈ −0,36 %/lệnh. Chỉ phạm vi hẹp (TP 1–3 %, engine hiện tại) — doc tự giới hạn. |
| V10 | **SIZE_COUNT** (09-27) | 🟡 THẤP–TB | Rate USDT (#31); UW/maxDD/gross từ equity **ngày** (`RESULT_SIZE_COUNT.md:87`); B3/B4 FAIL "UW tổng 278 > 250" theo ngày. Kết luận "(b′) không đổi dấu khi scale" là số học đúng. |
| V11 | **GATESCALE_SWEEP** (09-24) — "tăng lệnh không giảm rủi ro" | 🟡 TB | (g) "3 rate XẤU" gồm `meanP` + cặp win%/TSloss% (`RESULT_GATESCALE_SWEEP.md` §0) ⇒ ≤1–2 độc lập. (#14) chuẩn DD đổi giữa chừng. UW 1.00 = 248 nay ≤ 250; conc 27,23 % xử lý được bằng cap (`RESULT_CONC_CAP_HIGHN.md:131-143`: `cc-t100` PASS hết rào cũ). Nền T170 **1′**. |
| V12 | **GATESCALE_KEEPLEG0** (09-24) | 🟡 TB | nền 1′; UW 248 vs trần 250 theo ngày (cách 2 ngày; `RESULT_GATESCALE_KEEPLEG0.md:297`), UW phút [KHÔNG RÕ]. |
| V13 | **FUNDING_TOPK_LONG/ROTATE/K13, SHORT_CARRY** (09-22/23) | 🟢 THẤP | Neo MOM15 tái lập chính xác, quy ước dấu funding chốt riêng (`RESULT_FUNDING_SIGN.md` §0), thua ngay ở gross (`RESULT_FUNDING_TOPK_LONG.md` §0). Không thấy lỗi. |
| V14 | **LEVEL_SENSITIVITY / HARNESS_CONTROL** (09-22) | 🟢 THẤP (nhưng là NULL **power**, không phải "cạn") | có positive control MOM15 + placebo FP 0/200 (`INVENTORY_RECENT_MEASURES.md` §0). Chính MOM15 đang chạy live cũng **không** qua được DEV (B2) ⇒ DEV không phân giải được edge cỡ này. |
| V15 | **CAPACITY_DIAG H2** (09-23) → cả họ exit (TRAIL_LADDER, TRAIL_CAP_1030, PEAK_CLOSE, TRAIL_HINGE, EXIT_HIGH_N, GD92_X_EXIT) | 🟠 TB | Chính doc chẩn đoán "thước (meanP) SAI cho exit" (Kendall 0,333, 7/21 cặp đảo; `RESULT_CAPACITY_DIAG.md` §0.2) và đề nghị "đo lại các vòng cũ, phải pre-reg mới" — **không có vòng chấm lại** (grep Calmar: chỉ `RESULT_EXIT_HIGH_N.md:460` nhắc). Các NULL exit vẫn đứng trên thước đã bị chẩn đoán sai. |
| V16 | **HEDGE_OVERLAY_A** (09-20) | 🟡 TB | #3: số chính là artefact; verdict giữ bằng biến thể (F) beta in-sample; `INVENTORY_RECENT_MEASURES.md:193` và `power_wall.md:19` vẫn ghi "ICC tăng 4,3 lần" như **cơ chế** — trái với (E). |
| V17 | **REVERSAL_BOUNCE** (09-22, nhóm A1 "NULL đáng tin") | 🟡 TB–THẤP | (d) raw +0,31 % bị "fee 0,10 + slip ~0,24 + funding" ăn (`RESULT_REVERSAL_BOUNCE.md:24,35`); slip = ½ biên độ nến 1m là **giả định** (AUDIT_PNL: chi phí chắc chắn chỉ 0,1 %). Pre-reg file đang chứa 2 phiên bản xung đột (#7). "Đáng tin" chỉ đúng với mô hình chi phí đó. |
| V18 | **Họ BREADTH / REGIME / PACING** (09-21/22) — "ĐÓNG DỨT ĐIỂM, UW là nút thắt nội tại" | 🟡 TB | Lý do đóng chính = UW 221–223 > 200 (`power_wall.md` mục breadth, `INVENTORY…` §5) — trần nay là 250; UW phút ≈ UW ngày ở nền UW-bound (`RISK_APPETITE.md:178-183`: T100 248/248,2). Các tiêu chí u khác (n_eff ×1,5, ret-2025) cũng FAIL ⇒ verdict có thể vẫn NULL, nhưng **lý do "đóng dứt điểm vì UW" không còn đúng**; power_wall tự ghi "breadth CÓ alpha thật (CAGR 31–34 %)". |
| V19 | (không phải NULL) **Chọn T170 làm incumbent** (09-15) | 🟠 TB | #33: thắng trên win% + TSloss% + meanP (`AUDIT_READJUDICATE_CI_RESCORE.md:45-47`); dưới luật siết §10.2 còn **1 rate** ⇒ không qua luật hiện hành. Mọi NULL "vs T170/KEEPLEG0" đo trên một nền mà chính nó không qua luật. `NOBD_READJUDICATE` cùng dạng (2 rate = win%+TSloss%, `RESULT_NOBD_READJUDICATE.md:83-88`). |

---

## 3. VERDICT BỊ ERRATA LÀM LUNG LAY NHƯNG "ĐÓNG HƯỚNG" GIỮ NGUYÊN, KHÔNG CHẠY LẠI

| Hướng đã đóng | Errata làm lung lay | Tình trạng | Đánh giá |
|---|---|---|---|
| **OFI → tiền** (OFI_MONEY) | #24 chiều điểm (`RESULT_TAIL_ROBUST_RULERS.md:77`: "cần vòng riêng kiểm lại") | KHÔNG chạy lại; `RESULT_OFI_MONEY` vẫn "KHÔNG đưa vào lộ trình" | **Phải coi là CHƯA PHÂN GIẢI** |
| **Tầng equity "chết" / power wall** (NBETS, `power_wall.md`) | #4 ICC 0,247 là C2b; T170 = 0,0516 (trần 19,4 cược thay vì 4) | Chỉ thêm banner; MDE 3,78 pp không tính lại cho T170/KEEPLEG0 | Lung lay (hướng "thêm vị thế" từng bị coi vô ích vì ICC sai) |
| **Hedge beta** | #3 artefact | Giữ NULL bằng biến thể in-sample; INVENTORY lan truyền artefact | NULL có thể đúng nhưng **bằng chứng đã công bố sai** |
| **Ranker 45-feature → tiền** (PNL_RULER, MONEY_RANKER) | TAIL_ROBUST: thước mean-based ~100 % đuôi; MR có tín hiệu downside ngoài CI | "Đóng trục" giữ | Kết luận "kinh tế = 0" chỉ đúng trên thước đã hạ cấp |
| **Exit (6 vòng NULL)** | CAPACITY_DIAG H2: meanP là thước sai cho exit | Không chấm lại | Chưa phân giải theo đúng thước |
| **Breadth / regime** | Nới UW 200 → 250 (09-24) | "Đóng dứt điểm" giữ | Lý do đóng không còn nguyên |
| **Nhồi DCA (A2/A3)** | #30 size 1/6 | Không chạy arm khớp size | Bán phần (size-neutral hỗ trợ kết luận) |
| **Mọi cấu hình FAIL (b′)** | #26 số bịa làm tiền đề; #27 giải thích sai | Rào giữ, không hỏi lại owner | **Tiền đề quyết định phải được xác nhận lại** |
| **Incumbent T170** | #33 rate trùng | Không tái xét | Nền so sánh không qua luật hiện hành |

---

## 4. ĐỘ TIN CẬY KHỐI NULL HIỆN TẠI (theo trục)

| Trục | Độ tin cậy | Lý do chính |
|---|---|---|
| Model/xếp hạng (feature, nhãn, tầng thống kê) | **TRUNG BÌNH–CAO** | nhiều thước độc lập, đối chứng retrain + nhiễu sạch (`RESULT_MODEL_RULER` §13.2); lỗi `auc8` nhỏ (~0,009) |
| Xếp hạng → **tiền** (money ruler) | **THẤP–TRUNG BÌNH** | 1 nhãn (WEAK cap, 1 leg) + 1 pool (S1 top-32) + thước mean-based cho cả 4 vòng (pseudo-replication); OFI sai chiều; tín hiệu downside MR bỏ ngỏ |
| Exit / cấu trúc lãi | **TRUNG BÌNH** | thước rate bị chính CAPACITY_DIAG chê; size confound; 09-27 dựa (b′) |
| Tần suất vào lệnh / gate / breadth | **TRUNG BÌNH** | phần lớn chạy nhịp 1′ ≠ live; khẩu vị đổi 3 lần (15/120 → 30/200 → 40/250); maxDD đổi thước giữa chừng |
| Sự kiện / factor Python (funding, level, reversal, OI) | **TRUNG BÌNH–CAO** | có positive/negative control, neo tái lập; điểm yếu duy nhất là giả định slip |
| Rào (a)/(b′) như **số học** | **CAO** | đồng nhất thức kiểm 8/8, size-neutral cũng âm (A0 −6,54) |
| Rào (a)/(b′) như **luật hợp lệ** | **THẤP** | tiền đề bịa + giải thích sai + đơn vị (USDT/leg, gồm DCA scale ×6, lãi kép) chưa chốt |

**Kết luận chung [SUY LUẬN]:** câu "DEV đã cạn" hiện được chống đỡ chủ yếu bởi (i) rào (b′) (hợp lệ về số học,
chưa hợp lệ về quyết định) và (ii) họ thước tiền dùng chung một nhãn/pool. Bỏ hai trụ này thì phần còn lại
nói được là: **"trong khung S1 + luật thoát hiện tại, không có cải thiện đo được vượt CI"** — không phải "cạn".

---

## 5. DANH SÁCH CẦN CHẠY LẠI / XÁC NHẬN LẠI TRƯỚC KHI GỌI LÀ "ĐÓNG" (xếp ưu tiên)

| Ưu tiên | Việc | Chi phí ước | Vì sao |
|---|---|---|---|
| **P1** | Chấm lại **OFI_MONEY** với `ORIENT=−1` (sửa `ofi_money_score.py:149,165`, `ofi_money_ext.py:106`); **dựng lại pool B2** từ top-K đúng chiều (kernel nhãn Kaggle CPU, ~145 phút theo `RESULT_OFI_MONEY.md:196`); ensemble 43/44/45 | thấp–vừa, 0 quota | lỗi xác nhận bằng code; verdict hiện không hợp lệ |
| **P2** | **Owner xác nhận lại rào (b′)** với số đúng: bỏ top-5 % vẫn dương, `q*` KEEPLEG0 19 %, `median>0` PASS 8/8 nhưng Σ nửa dưới âm; chốt **đơn vị** (USDT hay size-neutral; leg hay cụm; có/không lãi kép) | 0 compute | rào đang chi phối mọi verdict, chốt trên tiền đề sai |
| **P3** | Sửa **bộ thước chuẩn** (bỏ/giải trình `loss_mean`≡`mP\|SL`, `conc_5` không phân giải) rồi **pre-reg vòng xác nhận** tín hiệu downside `MRA4/MRB8/MRB32` (multi-seed ≥3, đối chứng A45/V5) | thấp (dữ liệu có sẵn) | tín hiệu duy nhất sống sót, chưa theo |
| **P4** | Tái xét **incumbent T170/KEEPLEG0 vs T100(+CONC_CAP 15 %)** dưới luật §10.2 + khẩu vị latest + MTM phút | thấp (chấm lại output có sẵn) | nền so sánh hiện không qua luật hiện hành |
| **P5** | Chấm lại **EXIT_STRUCT / SHAPE1 / FAMILY2 / SIZE_COUNT** bằng rate chuẩn `profit` % (`c3_rates.rates`) + maxDD/UW MTM phút (`s3_intraday`) | thấp (Python trên `printDone` có sẵn) | lỗi định nghĩa #31 #32; câu "rào cũ PASS" chưa tin được |
| **P6** | EXIT_STRUCT: 1 arm **A2 khớp size** (`F_BASE`×~6) | 1 chân Kaggle ~20′ | confound #30 chưa khử |
| **P7** | Chấm lại **họ exit 6 vòng** theo endpoint CAPACITY_DIAG (Calmar/maxDD + SumPnL + capture) — phải pre-reg | thấp | thước cũ đã bị chẩn đoán sai |
| **P8** | Chấm lại **breadth/regime/pacing + GATESCALE 1.00/1.10 + cc-t100 + GD92+L1** dưới khẩu vị latest + MTM phút + (a)/(b′) — để đóng **với lý do đúng** | thấp (output có sẵn) | lý do đóng "UW>200" hết hiệu lực |
| **P9** | HEDGE: sửa guard (`valid` chỉ đếm `nopen>0`) và chạy lại, **hoặc** gỡ câu "ICC tăng 4,3 lần" khỏi `INVENTORY_RECENT_MEASURES.md:193` / `power_wall.md:19` | rất thấp | artefact đang được trích như cơ chế |
| **P10** | REVERSAL_BOUNCE: độ nhạy chi phí (slip 0 / proxy / ½ range) + gỡ marker conflict ở pre-reg (và `RECON_EVENT_ALPHA.md`) | rất thấp | "NULL đáng tin" phụ thuộc giả định slip; pre-reg mơ hồ |
| **P11** | Họ thước tiền: nhãn phản ánh exit thật (cap STRONG/WEAK theo pred, grid DCA, funding) + pool **không** do S1 định nghĩa (toàn universe) | vừa | 4 vòng "kinh tế = 0" chung một nhãn/pool |
| **P12** | Liệt kê verdict chấm bằng `x1_rates` giữa 09-24 và 09-26 (mặc định khẩu vị `current`) và chấm lại | rất thấp | #25, danh sách chưa có |

---

## 6. GHI CHÚ PHƯƠNG PHÁP / GIỚI HẠN CỦA AUDIT NÀY

- Không có commit log ⇒ thời điểm "trước/sau công bố" suy từ nội dung doc (errata/amendment ghi rõ).
- Không đọc được `research/pipeline/*` (ví dụ `ofi_train_eval_v3.py:150,177`, `mr_label_build.py`) — quy ước
  `score=−pred` cho OFI lấy từ `RESULT_TAIL_ROBUST_RULERS.md:70-77` và `tail_robust_rulers.py:70-73`.
- Không kiểm được edge5 +1,76 pp của `RESULT_S1_FREE_OFI_V3_MULTISEED` (code eval không có ở đây) [KHÔNG RÕ].
- Ước lượng phí cho FAMILY2 và (b′) (0,2 %/leg ≈ 1,1k USDT trên ~372 leg nửa dưới của A0, không lật −17.551)
  là [SUY LUẬN] số học thô, không phải số đo.
