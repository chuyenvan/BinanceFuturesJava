# TASK B — Hạ gate + pacing bigdown (thiết kế MASTER, hướng Uni chọn 2026-09-21)

Người soạn: MASTER. Người thực thi: agent Sonnet (khi bridge Oracle sẵn). Chủ quyết định: Uni (đã chọn hướng "Hạ gate + pacing bigdown").
Trạng thái: **THIẾT KẾ — chưa chạy.** Đây là khung; agent viết PREREG cuối trên Oracle từ khung này, commit TRƯỚC khi chạy sim.

Đầu vào đã có (đọc trước): `docs/analysis/ANALYSIS_BIGDOWN_STRUCT.md` (`dc63488`), `docs/analysis/RECON_ADMISSION_PACING.md` (`4268254`), `docs/result/RESULT_VOL_TARGET.md`, `docs/analysis/ANALYSIS_BETA_DECOMP_T170.md`. Project memory: `round_2026-09-20_beta_decomp_and_data_survey.md` (mục TASK A + A-recon), `power_wall.md`, `oracle_access.md`.

---

## 0. LUẬT (không nới)
1. An toàn: KHÔNG HOLDOUT 2026 / KHÔNG ssh 242 / KHÔNG `git push` / KHÔNG xoá thư mục bảo vệ / `.git/index.lock` đợi 30s retry.
2. **Điều phối job nặng (Uni nhấn mạnh)**: sim java là job nặng, chỉ 1 job/lần. Trước MỖI sim: `free -g` ≥12G VÀ `pgrep -af "Simulator|ExportWfo|s1_hpo|xgboost"` rỗng. **shadow-c3 đang chạy (java) — phải `systemctl stop shadow-c3` TRƯỚC khi chạy sim (luật `pgrep java` rỗng), và `systemctl start shadow-c3` NGAY SAU khi chạy xong chuỗi sim.** Ghi rõ mốc dừng/bật shadow trong RESULT. Chuỗi sim ~40-50 phút → shadow tắt trong khoảng đó (chấp nhận được, paper).
3. Pre-reg: PREREG commit TRƯỚC khi chạy; không đổi ngưỡng sau khi thấy số; sửa thiết kế phải ghi trước/sau khi thấy kết quả.
4. **Cổng tái lập T170**: chạy T170 OFF-config, `md5 printDone.csv` = `efb793e2468ca3a7318da0f0ad23d4fc`. Không đạt → dừng, báo, không chạy variant.
5. **Cổng OFF byte-identical** cho MỖI flag pacing mới: bật flag ở chế độ OFF/no-op phải cho md5 T170 y hệt (tiền lệ `SIZE_VOL_TARGET_MODE`, `CONC_CAP_*` đã test — A-recon xác nhận).
6. Khẩu vị hiện hành: maxDD≤30, UW≤200, quý≥−15, coin≤15%. `x1_rates.py --appetite current` (đã có, TASK C `7bc3827`).
7. CI: `x1_rates.py --k <số biến thể>`, inflate(k)=sqrt(2·ln k).
8. Logging Python `logging`, Java SLF4J. KHÔNG `print`/`System.out`.

---

## 1. GIẢ THUYẾT (có thể bác bỏ)
H_B: Hạ gate 1.70 → 1.0 (lấy breadth) làm risk xấu (T100 gate 1.0 hiện FAIL: maxDD −16.13%, đồng-thua bigdown cao). **Thêm pacing regime-conditional nhắm bigdown** (giảm size/giãn nhịp vào khi thị trường đang sập) kéo risk về ĐẠT khẩu vị hiện hành, trong khi vẫn giữ được phần lớn breadth ⇒ `n_eff_total` tăng ≥1.5× T170 mà maxDD/UW không thua T170 quá 25%.
H0 (NULL): pacing không kéo được risk về đạt khẩu vị ở gate 1.0; HOẶC phần cải thiện risk chỉ do giảm size đều (biến thể đối chứng P0 đạt bằng P3) chứ không do nhắm bigdown.

**Vì sao đây là hướng đúng (không phải quét size)**: TASK A đã đo bigdown là nhân tố đồng-thua (φ lỗ bigdown gấp ~2×, 74.85% depth maxDD T100 trong bigdown). Pacing nhắm ĐÚNG nhân tố đó, khác GS wave-1 (quét gate/size độc lập, chấm CAGR ở size cố định — chưa từng kiểm regime-conditional). Đối chứng P0 tách "nhắm bigdown" khỏi "giảm size đều".

⚠️ **Rủi ro đã biết (ghi vào PREREG)**: lệnh biên T100∖T170 có ROI +1.9% nhưng M7 match_rate chỉ 32.6% → KHÔNG đáng tin để kết luận "breadth có alpha" chắc chắn. Nếu breadth thực ra không có alpha, hạ gate chỉ thêm cược nhiễu → n_eff tăng nhưng CAGR giảm. Tiêu chí t phải bắt được điều này (xem t2/CAGR floor).

---

## 2. NỀN GATE
Nền = **gate 1.0** (= T100, đã có baseline sim, breadth tối đa, risk FAIL rõ ràng nên thấy được tác dụng pacing). Nếu run T100 (`X1_C3_FULL_2021`) còn nguyên `printDone.csv`+`sim.out` thì dùng lại làm "gate 1.0 không pacing"; nếu nghi ngờ cũ, chạy lại 1 lần để đồng bộ môi trường.
(Không chọn mức trung gian: gate gần-PASS sẵn sẽ che tác dụng pacing. Cần nền FAIL rõ để đo pacing cứu được bao nhiêu.)

## 3. BIẾN THỂ (Uni chốt mặc định P0+P3; k=2 trừ khi thêm)
Baseline so sánh (không phải biến thể, không tính k): **T170** (incumbent) + **T100 gate 1.0 no-pacing**.

- **P0 — đối chứng "giảm size đều" (BẮT BUỘC)**: gate 1.0 + giảm size bằng multiplier CỐ ĐỊNH (không điều kiện regime), chọn hệ số để Σnotional/equity trung bình ≈ T170 (đọc từ `bigdown_struct.json`/A-recon: T170 median ~0.058, T100 ~0.27 → hệ số ~0.2, agent tính chính xác từ dữ liệu, chốt 1 giá trị trước). Cắm tầng sizing (điểm cắm `VolTargetSizing.multiplier()`, an toàn byte-identical OFF). Mục đích: mốc để chứng minh P3 thắng nhờ *nhắm bigdown* chứ không nhờ *giảm size*.
- **P3 — pacing regime-conditional nhắm bigdown (CHÍNH)**: gate 1.0 + size multiplier = γ khi cờ bigdown causal bật, = 1.0 khi tắt. Cờ bigdown = định nghĩa BD1a của TASK A (BTC ret 24h ≤ −5%, **causal**: tính tới t−1, không lookahead — agent phải xác nhận engine tính được cờ này online không lookahead; nếu engine đã có `MarketBigChangeDetector` 1-phút thì dùng, ghi rõ định nghĩa khớp/khác BD1a). γ chốt trước = **0.5** (1 giá trị, KHÔNG quét). Cắm tầng sizing (không confound tập lệnh). 
  - Lưu ý: P3-sizing giảm SIZE trong bigdown; nếu Uni muốn "giãn nhịp/rate-limit" (P2, chặn bớt lệnh mới trong bigdown) thì đó là tầng admission (đổi tập lệnh, confound) — KHÔNG làm mặc định, chỉ thêm nếu Uni yêu cầu, và khi đó PREREG khai báo rõ là thay đổi tập lệnh + đo confound riêng.

Mỗi biến thể = 1 profile mới copy từ `x1_gs_t170.properties`, đổi `SIM_GATE_DYN_SCALE=1.0` + khoá pacing mới. `git diff` phải chỉ ra đúng các khoá khai báo.

## 4. TIÊU CHÍ (khoá TRƯỚC khi chạy)
Gọi các số của T170 làm mốc: n_eff_total(T170), maxDD −11.84%, UW 92, CAGR 29.27%.
- **t1 breadth**: `n_eff_total(biến thể)` ≥ 1.5 × n_eff_total(T170). (n_eff_total = Σ_j k_j/(1+(k_j−1)·ICC_ROI), cohort ngày ≥2 — đúng script TASK A `bigdown_struct.py`.)
- **t2 khẩu vị**: PASS toàn bộ ràng buộc hiện hành (maxDD≤30, UW≤200, quý≥−15, coin≤15%) theo `x1_rates.py --appetite current --k 2`. VÀ CAGR floor: CAGR biến thể ≥ cận dưới CI-72h (k=2) của T170 — chặn trường hợp breadth chỉ thêm cược nhiễu làm loãng CAGR.
- **t3 risk vs incumbent**: maxDD và UW không xấu hơn T170 quá 25% tương đối (maxDD ≥ −14.8%, UW ≤ 115). (Chặt hơn t2; T170 vốn dư an toàn nên đây là bài test thật.)
- **t4 cơ chế đúng (then chốt P3 vs P0)**: % depth maxDD-trong-bigdown của P3 **thấp hơn** của P0 (pacing nhắm đúng bigdown cắt được đồng-thua bigdown, không phải giảm đều). Đo bằng `bigdown_struct.py` M5 áp cho sim mới.

**Phán quyết**: THẮNG = P3 đạt t1∧t2∧t3∧t4 VÀ vượt P0 ở t1 hoặc t4. NULL = không biến thể nào đạt t1-t3, HOẶC P0 đạt ngang P3 ở t3/t4 (phần thắng chỉ là giảm size). HỖN HỢP = còn lại (không khuyến nghị đổi incumbent).

## 5. ĐO — TRÁNH CONFOUND MATCH_RATE
KHÔNG dùng khoá `(sym,start)` để so tập lệnh giữa các run (M7 TASK A: match chỉ 32.6% dù chỉ khác 1 tham số — gate động lệch giờ vào lệnh). So bằng **metric tổng hợp/phân phối**: n_eff_total, ICC(roi,ngày), phân rã maxDD theo bigdown, CAGR+CI, số lệnh/ngày, k̄, Σnotional/equity phân phối. Mọi so sánh cùng cửa sổ 2021-07-01..2025-12-31, cùng kiến trúc (Oracle ARM64, chỉ so Oracle).

## 6. QUY TRÌNH CHẠY (agent)
1. PREREG `docs/prereg/PREREG_PACING_BIGDOWN.md` từ khung này (điền γ, hệ số P0 tính từ dữ liệu, định nghĩa cờ bigdown causal chính xác trong engine, khoá config mới) → commit TRƯỚC.
2. Code: thêm khoá pacing vào `Configs.java` + điểm cắm sizing (`VolTargetSizing`-style hoặc mở rộng nó), giữ OFF byte-identical. Cổng OFF: chạy T170 với flag OFF → md5 `efb793e2`.
3. `systemctl stop shadow-c3`. Kiểm `pgrep java` rỗng + `free -g`.
4. Chạy tuần tự (1 java/lần, ~13 phút/run): (a) cổng T170 verify md5; (b) P0; (c) P3; (d) T100 no-pacing nếu cần sim mới. KHÔNG song song.
5. `systemctl start shadow-c3` NGAY sau chuỗi sim. Verify shadow active + log sạch.
6. Tính t1-t4 bằng `bigdown_struct.py` + `x1_rates.py --appetite current --k 2` cho từng run. Bảng so T170/T100/P0/P3.
7. `docs/result/RESULT_PACING_BIGDOWN.md`: 4 tiêu chí ✅/❌ mỗi biến thể, verdict, khuyến nghị. Commit code+doc branch `module` (KHÔNG push). Dọn `wfo_ds_*` tạm; giữ printDone/sim.out từng biến thể.

## 7. Ý NGHĨA QUYẾT ĐỊNH
- THẮNG ⇒ đề xuất Uni cân nhắc incumbent mới **chỉ sau** shadow paper song song ≥1 tháng (PLAN_SHADOW_T170_PARALLEL) — không đổi live vì 1 run.
- NULL/HỖN HỢP ⇒ ghi `power_wall.md`: hạ-gate-lấy-breadth + pacing bigdown đã đo, không mua được power ở rủi ro cố định ⇒ đóng; power T170 chỉ còn đường alpha mới (TASK D listing/delisting).

## 8. Sau khi xong
Cập nhật project memory `round_2026-09-20...md` (đọc lại, ghi full giữ nội dung cũ, thêm mục TASK B) + `MEMORY.md` bullet đầu. Trả lời MASTER: bảng T170/T100/P0/P3 (n_eff_total, ICC, maxDD, UW, CAGR+CI, %depth-maxDD-bigdown), 4 tiêu chí từng biến thể, verdict, mốc dừng/bật shadow-c3, có sửa Java gì (diff).
