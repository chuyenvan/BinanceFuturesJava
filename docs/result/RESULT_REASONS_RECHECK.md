# RESULT — ĐÓNG LẠI 6 TRỤC BẰNG **LÝ DO ĐÚNG** + **P4** (incumbent vs `cc-t100`)

- Nguồn: `docs/result/RESULT_RECHECK_P12_P5.md` (commit `0b1bd73`) + `RECHECK_P12_P5.json`; `RISK_APPETITE.md`
  §7 (khẩu vị `latest`); `RULERS_CURRENT.md` §10.1–§10.4 (luật §10.2 = bộ rate siết; §10.3 = rào (a)/(b′) +
  `latest`); `RESULT_CONC_CAP_HIGHN.md`; `RESULT_TAIL50_RULER_REDUNDANCY.md`; `gross_asymmap.json`.
- **Thuần đọc + viết lại lý do. 0 train · 0 sim · 0 Java · 0 chạm 2026/242/ONNX/LIVE/shadow.** DEV ≤ 2025-12-31.
- Khẩu vị chuẩn để đóng lại: `latest` = maxDD ≤ 40 · UW ≤ 250 · quý ≥ −20 · **0 năm âm** · **conc ≤ 15%**.
- Luật §10.2: **≥2 rate ngoài CI · tối đa 1 rate nhóm tần suất · KHÔNG tính `meanP`**. Rào §10.3:
  **(a)** `%PnL top-1% ≤ 15%` · **(b′)** **`bỏ top-50% lệnh` ⇒ PnL vẫn > 0 (CỨNG)**.

## 0. KẾT LUẬN NGAY (3 dòng)

1. **Cấp VÒNG: cả 6 trục vẫn NULL.** 16 ô verdict **RÀO** đổi `FAIL→PASS` (**12 chắc + 4 điều kiện `conc`**)
   ⇒ **"MỞ LẠI" chỉ ở tầng RÀO**, KHÔNG mở lại tầng vòng (u1–u5 / 0-rate vẫn chặn).
2. **LÝ DO SAI đã bị thay**: **KHÔNG** trục nào còn đóng vì *"vỡ khẩu vị `UW > 200`"* — dưới `latest`
   (`UW ≤ 250`) rào đó không bind nữa. Lý do đúng của từng trục ở §1.
3. **P4**: incumbent **T170/KEEPLEG0 THẮNG** trên tail-robustness; **`cc-t100` phục hồi rào nhờ cap**
   (conc 27,23 → 10,83%) **nhưng KHÔNG vượt incumbent**, và **KHÔNG biến thể nào PASS hết** §10.2+§10.3
   (cả 4 đều vỡ **(a)** và vỡ **(b′) CỨNG**).

---

## 1. VIỆC 1 — ĐÓNG LẠI 6 TRỤC BẰNG LÝ DO ĐÚNG (0 compute)

**"Mở lại" (PASS ở tầng RÀO, trước bị loại):** 12 ô chắc + 4 ô điều kiện `conc` (họ `T100/gate-1.0`).

| trục | biến thể **MỞ LẠI** (rào `FAIL→PASS`) | **LÝ DO ĐÓNG ĐÚNG** (thay cho *"vỡ khẩu vị UW>200"*) |
|---|---|---|
| **breadth** | **BR0**, **BRC**, **BRCT50** | **u1**: `n_eff < ×1,5·T170` (BR ×1,224 · BRC ×1,243 · BRCT50 ×1,339 — thiếu breadth **thống kê**) + **u5** (CAGR-2023 < 90%·T100) + **u3** (`UW toàn kỳ > 115` so-T170). Cốt lõi: **coverage ≠ discrimination** — nới gate = tăng phơi nhiễm, KHÔNG tăng edge |
| **regime** | **R** (up=1.0), **RA12** (up=1.2) | **u3**: `UW toàn kỳ > 115` (223 / 221 so-T170); RA12 thêm **u1** (×1,268 < 1,5) + **u5** (mất uptrend 2023 & 2024). *("RA12 làm hỏng thêm 2024" HẾT đúng: 205 ≤ 250.)* |
| **pacing** | **P0**, **P3** | **t3**: pacing chỉ giảm **size**, KHÔNG rút ngắn **thời lượng** chuỗi UW (`UW toàn kỳ > 115`); P0 thêm **t2b** (CAGR 12,14% < floor 14,80%); P3 thêm **t4** (bigdown-share 74,8% > P0 72,7% — NGƯỢC giả thuyết) |
| **dd-throttle** | **DT** | **u2**: `UW toàn kỳ 332 > 250` — **TỆ HƠN cả T100 (248)** + **u4**: `UW(DT) ≥ UW(R0)` ⇒ throttle **không** rút ngắn UW. (FAIL ngay cả dưới `latest`.) |
| **gate-calib** | **T130** | **0/5 rate ngoài CI** (T130/T210 không phân biệt được trên rate). Mệnh đề *"T130 còn vỡ ràng buộc cứng UW 221 > 200"* **hết đúng** (221 ≤ 250) ⇒ nửa rào của kết luận rơi |
| **exit-high-n** | **GD92+LADDER L1** | **Bằng chứng (cơ chế)**: exit **0 TỐT / 0 XẤU** ngoài CI ở **2,4× n** (n 1.089→2.632) — cơ chế exit chỉ *dịch đường ra*, không sinh rate mới. *(T100 base vẫn FAIL vì conc 27,23; GD92 base/+HINGE FAIL vì UW 278.)* |

**4 ô ĐIỀU KIỆN `conc`** (chỉ PASS nếu bật `CONC_CAP_PERCOIN=15%`; `x1_rates` KHÔNG đo conc):
`RESULT_REGIME_GATE:40` T100/gate-1.0 · `RESULT_REGIME_UPDOWN:45` T100/gate-1.0 ·
`RESULT_BREADTH_GATE_SIM:77` T100/gate-1.0 · `RESULT_PACING_BIGDOWN:39` T100 — **conc đã biết 27,23% > 15%**
⇒ vẫn FAIL nếu cap OFF; cap ON ⇒ `cc-t100` conc 10,83% ⇒ PASS rào.

**3 chỗ LÝ DO bị ĐẢO (giữ nguyên cấp vòng, phải viết lại):** (1) `BREADTH_GATE_SIM:77` — *"BR là biến thể
ĐẦU TIÊN đưa UW-2025 < 200"* **mất tính duy nhất** (dưới 250, T100=227 & BR0=221 cũng PASS); (2)
`DD_THROTTLE:61`/`PACING_BIGDOWN:39` — *"P0/P3/DT không đưa gate 1.0 về đạt khẩu vị"* **hết đúng**;
(3) `REGIME_UPDOWN:45` — *"RA12 làm hỏng thêm 2024"* **không còn đứng** (205 ≤ 250).

---

## 2. VIỆC 2 — P4: T170/KEEPLEG0 vs T100 (+`CONC_CAP 15%`, tag `cc-t100`) dưới §10.2 + `latest`

| chỉ số | **T170** | **KEEPLEG0** | T100 (`hn-t100`, OFF) | **`cc-t100`** (cap 15%) |
|---|---|---|---|---|
| maxDD năm xấu nhất (ngày) | −11,84 | −11,21 | −16,13 | −16,13 |
| maxDD **MTM phút** (năm xấu) | **−19,96** | **−19,96** | **−26,26** | **THIẾU** |
| UW dài nhất (ngày) | 92 | 147 | 248 | 248 |
| UW **MTM phút** | 144,4 | 147,2 | 248,2 | **THIẾU** |
| quý xấu nhất | −0,92 | −1,08 | −4,64 | −4,64 |
| **0 năm âm** | ✓ | ✓ | ✓ | ✓ |
| **conc 1 coin** | 9,77 ✓ | 7,12 ✓ | **27,23 ✗** | 10,83 ✓ |
| **`%PnL top-1%` (a ≤ 15)** | 25,90 ✗ | 23,74 ✗ | 40,85 ✗ | **41,93 ✗** |
| **`bỏ top-50%` (b′ > 0)** | −35,3k ✗ | −33,1k ✗ | −155,8k ✗ | **−157,3k ✗** |
| **RÀO `latest` (rủi ro)** | **PASS** | **PASS** | FAIL (conc) | **PASS** |
| **§10.2 rate + §10.3 (a)+(b′)** | **FAIL** | **FAIL** | **FAIL** | **FAIL** |

- **AI THẮNG?** **T170/KEEPLEG0** — thoả **toàn bộ** rào `latest` **và** gần ngưỡng (a) nhất (23,7–25,9%),
  TF50 âm **ít hơn 4–5×** so họ T100 (−33k/−35k vs −156k/−157k). Đây là **incumbent thắng**.
- **`cc-t100`**: cap xoá đúng **1 mục FAIL duy nhất** (conc 27,23 → 10,83%) ⇒ PASS rào `latest`; nhưng
  **KHÔNG** cải thiện (a)/(b′) — (a) còn **tệ hơn nhẹ** (41,93 vs 40,85 OFF) ⇒ cap **không** cứu tail.
- **CÓ BIẾN THỂ NÀO PASS HẾT? → KHÔNG.** Cả 4 vỡ **(b′) CỨNG** (âm sâu) và vỡ **(a)**.
- ⚠️ **MTM phút cho `cc-t100` THIẾU** (`intradaydd/series.npz` chỉ có 4 nền T170/KEEPLEG0/T100/GD92;
  ticker 1m offline đã mất) ⇒ **KHÔNG suy diễn** số cho `cc-t100`; dùng maxDD/UW **ngày** + tuyên bố thiếu.
- **Run `cc-t100` TỒN TẠI**: `/home/ubuntu/kaggle_sim/out/cc-t100` (result.json + log `[CONC-PC] MODE pct=0.15`,
  `blocked=44`; md5 `9ba7b022…`; n=2.557, equity 129.024) — xác nhận cap **bind thật**.

---

## 3. TRẢ LỜI (bắt buộc)

**(1) Có biến thể nào MỞ LẠI (PASS) không?** **CÓ — 16 ô ở tầng RÀO** (KHÔNG mở lại tầng vòng):
`R`(regime ×2 doc) · `RA12` · `BR0` · `BRC`(×2 doc) · `BRCT50` · `P0` · `P3` · `DT` · `T130` ·
`GD92+LADDER L1` = **12 chắc**; **+4 điều kiện** `T100/gate-1.0` (chỉ PASS nếu `CONC_CAP=15%`). Tổng sàng 460
tag: **85 tag** `FAIL→PASS`, **100% do `UW ∈ (200,250]`**.

**(2) Lý do đúng từng trục:** breadth → **u1 thiếu `n_eff` (+u5/u3)**; regime → **u3 UW toàn kỳ > 115**;
pacing → **t3 UW không rút ngắn (+t2b/t4)**; dd-throttle → **UW toàn kỳ 332 > 250, tệ hơn T100**;
gate-calib → **0/5 rate ngoài CI**; exit-high-n → **bằng chứng: exit không nhân theo n**.

**(3) P4:** dưới `latest` + luật mới, **incumbent T170/KEEPLEG0 thắng**; **`cc-t100`** chỉ **phục hồi rào**
nhờ cap (conc → 10,83%) chứ **không thắng**; **KHÔNG biến thể nào PASS hết** (§10.3 (a) và (b′) giết 4/4).

**(4) Nếu có PASS hết ⇒ bước tiếp:** *không có biến thể PASS hết* ⇒ **không có bước "GO"**. Rào **(b′) CỨNG
đã giết 8/8 (TAIL50) + 4/4 (đây)** và **(a)** giết toàn bộ nền nhiều lệnh ⇒ trục "nền nhiều lệnh" **đóng
bằng bằng chứng**. Muốn *tin* thêm (nếu owner muốn mở lại) cần theo thứ tự: ① **MTM phút cho `cc-t100`**
(chạy `s3_intraday.py` trên Kaggle — cần ticker 1m, 0 compute ở đây); ② **multi-seed ≥3** cho
T170/KEEPLEG0 để xác nhận (a)/(b′) ổn định; ③ **endpoint khác** (vd Calmar/UW trên nền T170 **đã PASS**)
phải **pre-reg riêng** — không dùng kết quả này để GO.

---

## 4. MỤC BỎ + GIỚI HẠN

- **BỎ** câu *"đóng vì vỡ khẩu vị (UW>200)"* cho 6 trục (nguồn sai: `x1_rates` mặc định `current`); thay bằng
  u1–u5 / t1–t4 / 0-rate ngoài CI ở §1.
- **BỎ `meanP`** (đồng nhất thức) · **BỎ rate trên cột `pnl` để ra verdict**.
- **THIẾU dữ liệu (ghi rõ, KHÔNG suy diễn):** MTM phút cho `cc-t100` và cho 16 tag 4 vòng (thiếu ticker 1m
  offline). `%PnL top-1%`/`bỏ top-50%` của `cc-t100` lấy từ `gross_asymmap.json` (`top1_share`,
  `TF50`); T170/KEEPLEG0/T100 lấy từ đó + `RESULT_TAIL50_RULER_REDUNDANCY.md` (chênh ≤ 0,1% do khác bản leg).
- Không chấm lại tier MODEL/money-ruler; không mở lại ứng viên; không chạm 2026/242/ONNX/LIVE.
