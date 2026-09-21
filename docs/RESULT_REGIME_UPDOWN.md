# RESULT_REGIME_UPDOWN — Bước 4: up-gate CHẶT hơn (RA12 khoá) (2026-09-21)

Kết quả cho `docs/PREREG_REGIME_UPDOWN.md` (commit `ba3d7ba`, chốt TRƯỚC build/sim). Nối tiếp
Bước 2 (`docs/RESULT_REGIME_GATE.md`, R=up1.0/down1.7, VERDICT NULL vì vỡ UW-2025). Không đổi
biến thể khoá sau khi thấy số; RA14 (up=1.4) chỉ là sweep MÔ TẢ, không được phép thay RA12 làm
quyết định dù số của nó đẹp hơn (xem §5).

## 0. Cổng an toàn — PASS

- **OFF byte-identical**: sau khi sửa `EntryGate.java`/`Configs.java` (bỏ `final` khỏi
  `REGIME_SCALE_UP` + thêm nhánh đọc `SIM_REGIME_SCALE_UP` qua `Configs`, xem §6), build lại jar
  từ HEAD → chạy lại T170 (tag `X1_GS_T170_2021_REGIMEUPDOWN_OFFCHECK`, profile `x1_gs_t170.
  properties`, không khai báo `SIM_REGIME_SCALE_UP`) → `printDone.csv` md5 =
  `efb793e2468ca3a7318da0f0ad23d4fc` — **KHỚP CHÍNH XÁC** tham chiếu. **PASS.** (n=1089, rc=1
  là exit code bình thường của Simulator khi hết dữ liệu, không phải lỗi — không có Exception/
  OutOfMemory trong log.)
- **shadow-c3**: dừng lúc **12:03:22** (2026-09-21, +07) TRƯỚC chuỗi sim, chạy tuần tự 1
  JVM/lần: T170 OFF-verify (12:11:34→12:25:58, n=1089) → RA12 (12:30:05→12:44:10, n=1552) → RA14
  (12:46:16→13:00:29, n=1296). Khởi động lại `shadow-c3` lúc **13:01:36**, verify `active` lúc
  13:01:39; kiểm log ~3 phút gần nhất: **0 lỗi -2014**, 3 lỗi -2015 (IP-whitelist, đã biết trước,
  không ảnh hưởng) + 1 NullPointerException đã biết pattern cũ. Tổng thời gian dừng **58 phút 14
  giây** (12:03:22→13:01:36, xác nhận qua `systemctl show -p ActiveEnterTimestamp/
  InactiveEnterTimestamp`).
- Log xác nhận cơ chế mới hoạt động đúng: RA12 log có
  `[REGIME] adaptive ON file=.../regime_daily_ma200_x1_2021.csv (UP=>1.2 NOTUP=>1.7)`; RA14 có
  `(UP=>1.4 NOTUP=>1.7)` — đúng giá trị `SIM_REGIME_SCALE_UP` từng profile.

## 1. Bảng chính (2021-07-01..2025-12-31, Oracle ARM64)

| Tag | n lệnh | n_eff_total | ICC(roi,ngày) | maxDD% | UW (ngày, toàn kỳ) | CAGR% | CAGR CI95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **T170** (mốc) | 1089 | 606.26 | 0.0516 | −11.84 | 92 | 29.27 | [17.17, 43.86] (k=1) |
| **T100/gate-1.0** | 2559 | 1103.86 | 0.1016 | −16.13 | 248 | 31.94 | [11.72, 56.94] (k=2, Bước 2) |
| **R** (up=1.0, tái dùng Bước 2) | 2051 | 943.79 | 0.0898 | −11.84 | 223 | 32.95 | [14.86, 54.60] (k=2, Bước 2) |
| **RA12** (up=1.2, **KHOÁ, phán quyết**) | 1552 | 768.54 | 0.0768 | −11.84 | 221 | 30.50 | [16.99, 47.60] (k=1) |
| **RA14** (up=1.4, sweep mô tả) | 1296 | 678.68 | 0.0640 | −11.84 | 164 | 31.54 | [17.85, 48.49] (k=1) |

Ghi chú: `n_eff_total`/ICC/maxDD/UW: `research/analysis/regime_updown_metrics.py` (mới, tái dùng
nguyên văn hàm của `bigdown_struct.py`/`c3_rates.py`). CAGR+CI: `cagr_ci_t170.py` (bootstrap
khối-72h, 2000 rep, seed 20260905). T100/R lấy nguyên số Bước 2 (không chạy lại theo đúng thiết
kế §3 PREREG); k=2 của chúng phản ánh ngữ cảnh multiplicity của round đó (2 ứng viên R/R0), khác
k=1 dùng cho RA12 ở round này — chỉ so sánh CAGR điểm, không so trực tiếp độ rộng CI giữa 2 round.
CI-floor(T170, k=1)=17.17%; CI-floor(T170, k=3, minh bạch)=10.73% — RA12 CAGR=30.50% vượt cả hai.

## 2. Khẩu vị hiện hành THEO NĂM (`x1_rates.py --k 1|3 --appetite current`: maxDD≤30%, UW≤200/năm,
năm không âm, quý≥−15%) — bảng dưới không đổi theo k (chỉ CI đổi theo k, xem §1)

| Tag | 2021 | 2022 | 2023 | 2024 | 2025 | Kết luận |
|---|---|---|---|---|---|---|
| T170 | PASS (UW37) | PASS (UW72) | PASS (UW63) | PASS (UW92) | PASS (UW52) | **PASS toàn kỳ** |
| T100/gate-1.0 | PASS (UW47) | PASS (UW64) | PASS (UW45) | PASS (UW121) | **FAIL** (UW227) | FAIL |
| R (up=1.0) | PASS (UW47) | PASS (UW72) | PASS (UW57) | PASS (UW200, sát biên) | **FAIL** (UW223) | FAIL |
| **RA12 (up=1.2, KHOÁ)** | PASS (UW47) | PASS (UW72) | PASS (UW57) | **FAIL** (UW205) | **FAIL** (UW221) | **FAIL** |
| RA14 (up=1.4, sweep) | PASS (UW38) | PASS (UW72) | PASS (UW57) | PASS (UW119) | PASS (UW164) | **PASS toàn kỳ** |

**Phát hiện quan trọng nhất**: up-gate 1.2 (RA12) **KHÔNG đủ chặt** để cứu 2025 (UW 221 vs 223 của
R — giảm chỉ 2 ngày, gần như không đổi) và **còn làm HỎNG THÊM năm 2024** — năm mà cả T170, T100,
R đều PASS thoải mái (UW 92/121/200) thì RA12 lại FAIL (UW=205, vượt ngưỡng 200 lần đầu tiên xuất
hiện ở năm này trong toàn bộ round). Chỉ khi chặt tới up=1.4 (RA14, sweep mô tả) thì CẢ 5 năm mới
PASS đồng thời (UW max = 164 ở 2025). Điều này cho thấy quan hệ up-gate → UW **không tuyến tính
êm**: 1.0→1.2 gần như không cải thiện được gì (chưa đủ ngưỡng), 1.2→1.4 mới thực sự "gãy khúc"
UW xuống dưới ngưỡng khẩu vị ở mọi năm — nhưng RA14 không phải biến thể được phép chọn ở round
này (xem §5, luật khoá PREREG).

## 3. Đường cong breadth-vs-UW theo up-gate (R→RA12→RA14, down=1.7 cố định)

| up-gate | tag | n_eff_total | ×T170 | UW toàn kỳ | UW 2025 | UW 2024 | Khẩu vị toàn kỳ |
|---:|---|---:|---:|---:|---:|---:|---|
| 1.0 | R | 943.79 | ×1.557 | 223 | 223 | 200 | FAIL |
| **1.2** | **RA12 (khoá)** | **768.54** | **×1.268** | **221** | **221** | **205** | **FAIL** |
| 1.4 | RA14 (sweep) | 678.68 | ×1.119 | 164 | 164 | 119 | PASS |
| — (T170 mốc, up=down=1.7) | — | 606.26 | ×1.000 | 92 | 52 | 92 | PASS |

Breadth (n_eff_total) giảm ĐƠN ĐIỆU và gần TUYẾN TÍNH khi up-gate chặt dần (944→769→679→606 khi
up: 1.0→1.2→1.4→1.7); UW toàn kỳ giảm CHẬM từ 1.0→1.2 (−2, −0.9%) rồi giảm NHANH từ 1.2→1.4
(−57, −25.8%). ⇒ up=1.2 nằm ở vùng "trả giá breadth mà chưa mua được UW" của đường cong này.

## 4. Đánh giá u1–u5 cho RA12 (khoá trong PREREG §4)

| Tiêu chí | Ngưỡng | Giá trị RA12 | Kết quả |
|---|---|---|---|
| **u1** breadth | `n_eff_total ≥ 909.39` (=1.5×606.26) | 768.54 (×1.268, thiếu ×1.5) | **❌ FAIL** |
| **u2** khẩu vị + CAGR floor | PASS mọi năm (đặc biệt UW≤200) + CAGR≥17.17% (k=1) | FAIL 2024 (UW=205) **và** 2025 (UW=221); CAGR=30.50%✅ | **❌ FAIL** (vỡ vì khẩu vị 2 năm) |
| **u3** vs T170 | `maxDD≥−14.80%` ∧ `UW≤115` | maxDD=−11.84✅ / UW=221❌ (ngưỡng 115) | **❌ FAIL** (vỡ vì UW) |
| **u4** cứu 2025 + giữ 2022 | `UW(RA12,2025)<UW(R,2025)` ∧ `UW(RA12,2022)≈UW(T170,2022)` (±5%) | 221<223✅ (chỉ −0.9%) ∧ 72=72 (0% lệch)✅ | **✅ PASS** (nhưng cải thiện 2025 rất nhỏ) |
| **u5** không phá uptrend | CAGR 2023 & 2024 RA12 ≥90%×T100 | 2023: 50.49/60.43=83.5%❌ (cần≥54.39); 2024: 32.08/45.28=70.8%❌ (cần≥40.75) | **❌ FAIL** (cả hai năm) |

**Kết quả: 1/5 PASS (chỉ u4), 4/5 FAIL.** Điều kiện THẮNG (khoá trong PREREG §8: cần đạt ĐỦ cả
u1∧u2∧u3∧u5, u4 là điều kiện xác nhận cơ chế đúng hướng chứ không đủ để thắng một mình) KHÔNG đạt.

## 5. Phán quyết — NULL (RA12 không thắng)

**NULL.** up-gate 1.2 (RA12) đúng HƯỚNG (cơ chế PROACTIVE, khác bản chất 3 cơ chế REACTIVE đã NULL
trước đó — TASK B, Bước 2-pacing, Bước 3 dd-throttle) nhưng **độ lớn không đủ**:
- Không đạt ngưỡng breadth (u1: ×1.27 thay vì ×1.5 kỳ vọng).
- Không cứu được UW-2025 một cách có ý nghĩa (221 vs 223 của R — cải thiện chỉ 0.9%, trong khi cả
  hai đều vẫn vỡ khẩu vị UW≤200).
- Tệ hơn: RA12 **mở ra một điểm yếu MỚI ở 2024** mà R/T100/T170 không có (UW=205>200) — cái giá
  phải trả cho việc siết up-gate không chỉ rơi vào breadth mà còn ăn vào chính năm uptrend tốt mà
  Bước-2 từng dùng làm bằng chứng "không phá uptrend" (u5 giờ FAIL cả 2023 và 2024, mất 16-29
  điểm % CAGR so với T100).
- Điểm sáng duy nhất (u4 PASS): RA12 giữ đúng hành vi bear-2022 y hệt T170 (lệch 0%) — xác nhận
  lại cơ chế `RegimeSchedule`/CSV MA200 vẫn hoạt động chính xác như Bước 2, không phải do bug mới.

**Ghi chú anti-overfitting quan trọng (đúng như PREREG §1 đã cảnh báo trước khi chạy)**: RA14
(up=1.4, sweep MÔ TẢ, KHÔNG phải ứng viên phán quyết) lại là biến thể **duy nhất PASS khẩu vị
`current` ở cả 5/5 năm** trong toàn bộ bảng (§2-§3) — con số "đẹp" nhất của cả round. Theo đúng
luật đã khoá TRƯỚC khi chạy (PREREG §1: "KHÔNG được dùng RA14/R để chọn winner sau khi thấy số —
luật cấm mở biến thể quanh winner"), kết quả này **KHÔNG được dùng để thay RA12 làm quyết định
của round này**. Số của RA14 chỉ được ghi nhận như một QUAN SÁT/gợi ý giả thuyết cho một round
PREREG MỚI trong tương lai (nếu Uni muốn thử up=1.4 hoặc cao hơn như ứng viên phán quyết chính
thức, cần chốt PREREG riêng TRƯỚC khi biết đây là "ứng viên đã có số đẹp" — tức phải coi round đó
là round độc lập, không phải "mở lại" round này).

## 6. Khuyến nghị

- **KHÔNG đưa RA12 (up=1.2/down=1.7) vào production.** Giữ T170 làm incumbent — kết luận này nối
  tiếp đúng chuỗi NULL của TASK B → Bước 2 → Bước 3 → Bước 4 (4/4 round breadth-improvement đều
  NULL tính đến nay).
- **RA14 (up=1.4) là giả thuyết đáng theo đuổi TIẾP, KHÔNG phải kết luận của round này** — nếu
  Uni muốn kiểm định chính thức, mở round mới với PREREG riêng khoá up=1.4 (hoặc quét thêm 1.5/
  1.6) làm ứng viên phán quyết DUY NHẤT, và cần một biến thể sweep mô tả khác (không phải RA12/R
  đã dùng) để tránh lặp lại đúng cấu trúc "chọn winner sau khi thấy số" dưới hình thức khác.
- Cơ chế `SIM_REGIME_SCALE_UP` (Configs→EntryGate, xem §7) đã kiểm chứng hoạt động đúng (log xác
  nhận UP=>1.2/1.4 đúng theo profile) — có thể tái dùng nguyên trạng cho round up=1.4 tương lai,
  chỉ cần profile mới, không cần sửa `.java` thêm.

## 7. Thay đổi code

- **`.java`: 2 file, đã commit ở `ba3d7ba` (commit PREREG, TRƯỚC khi chạy sim — không phải diff
  mới ở bước này).** Không phải 0-diff như kỳ vọng ban đầu của nhiệm vụ: recon phát hiện
  `REGIME_SCALE_UP`/`REGIME_SCALE_NOTUP` trong `EntryGate.java` là hằng số Java
  (`public static final float`), không đọc được từ profile. Đã sửa tối thiểu (đã lường trước
  trong thiết kế nhiệm vụ như phương án dự phòng):
  - `EntryGate.java`: bỏ `final` khỏi `REGIME_SCALE_UP` (giữ giá trị mặc định `1.00f`).
    `REGIME_SCALE_NOTUP` KHÔNG đổi (vẫn hằng số `1.70f`).
  - `Configs.java`: thêm nhánh đọc key mới `SIM_REGIME_SCALE_UP` — không khai báo hoặc giá trị
    `<=0` thì giữ nguyên `1.00f` (mặc định Bước 2), đảm bảo đường OFF/không-khai-báo
    byte-identical (xác nhận PASS ở §0).
- `research/analysis/regime_updown_metrics.py` (mới, ~150 dòng): tính u1/u3/u4 cho 5 tag, tái
  dùng nguyên văn hàm của `bigdown_struct.py`/`c3_rates.py`, không sửa 2 file gốc.
- `profiles/x1_c3_full_regime_ra12.properties`, `profiles/x1_c3_full_regime_ra14.properties`
  (đã có từ `ba3d7ba`): mỗi file = `x1_c3_full_regime_r.properties` (Bước 2) + 1 dòng
  `SIM_REGIME_SCALE_UP=1.2/1.4`, tái dùng nguyên văn CSV regime MA200 của Bước 2 (không tạo CSV
  mới).
- **Cổng OFF byte-identical: PASS** (md5 khớp tuyệt đối `efb793e2468ca3a7318da0f0ad23d4fc`).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
