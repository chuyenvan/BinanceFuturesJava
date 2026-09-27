# RESULT_SHAPE1_EARLY_CUT — Hình dạng #1: CẮT LỖ SỚM (3 giá trị CHƯA THỬ) — **0/4 arm PASS**

**Ngày:** 2026-09-27 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_SHAPE1_EARLY_CUT.md` (`8668f51` — chốt **TRƯỚC** khi chạy).
**Runner:** `research/analysis/shape1_run.py` · **Scorer (tái dùng):** `research/analysis/size_count_score.py` (`--base cd-sel15 --k 4`) · **Martingale:** `research/analysis/shape1_martingale.py`.
**Số thô:** `docs/result/shape1_early_cut.json` · `docs/result/shape1_martingale.json`.
**Chi phí:** 4 chặn Kaggle CPU, **0** (KHÔNG chạy sim trên Oracle). DEV only ≤ 2025-12-31 (0 run chạm 2026). **KHÔNG sửa 1 dòng Java** ⇒ **không cần parity lại** (cổng knob `sc-par` đã chứng minh 2 knob default vô hại: md5 `= cd-sel15`).

---

## 0. KẾT LUẬN NGẮN

1. **PASS (a) VÀ (b′) = 0/4 arm.** (a): 3 arm **LỖ** (S1,S2,S4) ⇒ không tính; S3 `%top-1`=**32,30** > 15 ⇒ FAIL. (b′): `TF50` **âm ở cả 4** (−24.032 … −50.893) ⇒ **FAIL 4/4**.
2. **`asym<1` + PnL dương: VẪN KHÔNG TỒN TẠI.** S2 `asym`=**0,711** và S4 **0,716** (<1) nhưng **cả hai LỖ** (equity 25.395 / 25.201 < 35.000); S3 dương (53.698) thì `asym`=**1,463** >1.
3. **SL cứng sớm (S1/S4) làm (b′) TỆ HƠN:** `TF50` −17.551 → **−48.012** (S1) / **−39.057** (S4); `maxDD` −6,27 → **−21,40 / −28,57** %; `UW` 166 → **1.487**. Cắt lỗ sớm giết luôn nhóm thắng (median/leg < 0, coin "chết" tăng vọt).
4. **⇒ KẾT LUẬN CỨNG (đúng như KỲ VỌNG ghi trước): trong HỌ chiến lược hiện tại (arm +7 % → trailing + DCA grid) KHÔNG THỂ đạt (a)+(b′) bằng chỉnh tham số ⇒ PHẢI ĐỔI HỌ CHIẾN LƯỢC.**

---

## 1. BẢNG ARM (base `S0` = `cd-sel15`, dùng lại; `k=4`, inflate 1,6651)

| arm | thay đổi | n | entry/m | CAGR% | maxDD% | UW | qmin | conc% | coin max/TB | grossT/M% | %top-1 | TF50 (USDT) | q*% | asym | sign% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S0** `cd-sel15` | (base) | 744 | 13,77 | **+17,29** | −6,27 | 166 | −3,36 | 6,77 | 24/0,5 | 1,7/49,5 | **19,13** | **−17.551** | 21,2 | **3,375** | 88,44 |
| **S1** `sh1-s1-sl05` | `PRE_ARM_SL=-0,05` K=8 | 1.285 | 23,79 | **−3,81** *(lỗ)* | −21,40 | 1.487 | −9,00 | 4,85 | 13/0,1 | 0,4/38,7 | −89,81 *(lỗ)* | **−48.012** | 0,1 | **1,036** | 47,86 |
| **S2** `sh1-s2-sl03k16` | `PRE_ARM_SL=-0,03` + `K=16` | 2.510 | 46,47 | **−6,88** *(lỗ)* | −28,84 | 1.487 | −16,10 | 5,03 | 22/0,2 | 0,4/49,0 | −66,22 *(lỗ)* | **−50.893** | 0,0 | **0,711** | 37,13 |
| **S3** `sh1-s3-ts8` | `LOSER_TIME_STOP=8h` | 833 | 15,42 | **+9,98** | −4,56 | 233 | −0,89 | 6,22 | 24/0,1 | 0,3/48,1 | **32,30** | **−24.032** | 8,5 | **1,463** | 70,83 |
| **S4** `sh1-s4-sl03` | `PRE_ARM_SL=-0,03` K=8 | 1.506 | 27,88 | **−7,04** *(lỗ)* | −28,57 | 1.487 | −13,06 | 4,92 | 12/0,1 | 0,3/35,0 | −47,28 *(lỗ)* | **−39.057** | 0,1 | **0,716** | 35,92 |

*(equity cuối: S0 71.718 · S1 29.386 · S2 25.395 · S3 53.698 · S4 25.201, gốc 35.000.)*

### 1.1 Bộ 4 thước chuẩn + dự bị

| arm | wl_ratio | tf_5 | loss_mean | conc_5 | median | tf_10 |
|---|---|---|---|---|---|---|
| S0 | 0,296 | 27,75 | −337,0 | 46,65 | 62,08 | 17,42 |
| S1 | 0,965 | −15,94 | −73,2 | −246,4 | −44,68 | −22,69 |
| S2 | 1,406 | −11,67 | −35,9 | −189,6 | −20,87 | −16,17 |
| S3 | 0,684 | 5,67 | −116,6 | 76,0 | 38,65 | −2,36 |
| S4 | 1,397 | −16,13 | −46,8 | −135,4 | −32,63 | −21,75 |

---

## 2. RÀO — PASS/FAIL TỪNG ARM (định nghĩa §4 pre-reg)

| arm | **(a)** `%top-1≤15` (& ΣPnL>0) | **(b′)** `TF50>0` | **CẢ HAI** | rào cũ (appetite latest) | gross TB/MAX ≤70 |
|---|---|---|---|---|---|
| S0 | FAIL 19,13 | FAIL −17.551 | **FAIL** | PASS (−6,27·166·−3,36·6,77·0 năm âm) | PASS 1,7 / 49,5 |
| S1 | **FAIL (LỖ)** | FAIL −48.012 | **FAIL** | **FAIL** (năm âm 2022/2024/2025; UW 363/329) | PASS 0,4 / 38,7 |
| S2 | **FAIL (LỖ)** | FAIL −50.893 | **FAIL** | **FAIL** (năm âm 2021/2022/2024/2025; UW 263/329) | PASS 0,4 / 49,0 |
| S3 | FAIL 32,30 | FAIL −24.032 | **FAIL** | **PASS** (−4,56·233·−0,89·6,22) | PASS 0,3 / 48,1 |
| S4 | **FAIL (LỖ)** | FAIL −39.057 | **FAIL** | **FAIL** (năm âm 2021/2022/2024/2025; UW 342/263/329) | PASS 0,3 / 35,0 |

**PASS (a) = 0/4 · PASS (b′) = 0/4 · PASS CẢ HAI = 0/4.** (S1/S2/S4 hiện `%top-1` **âm** — artifact của `ΣPnL<0`; **không** phải PASS.)
Trần gross 70 % theo **định nghĩa LEDGER** (errata §11): **không bind** ở mọi arm (MAX ≤ 49,0 % < 60 % = `U_MAX`).

## 3. 5 RATE + CI vs S0 (block-72h, 2.000 rep, seed `20260905`, inflate 1,6651) + luật siết §10.2

| arm | ngoài CI | "hướng TỐT" §10.2 | kết |
|---|---|---|---|
| S1 | win%, TSloss%, mP\|SM, mP\|SL, meanP, mMargin | **mP\|SL** (artifact size) | KHONG (<2) |
| S2 | cả 6 | **mP\|SL** | KHONG (<2) |
| S3 | win%, TSloss%, mP\|SL, meanP, mMargin | **mP\|SL** | KHONG (<2) |
| S4 | cả 6 | **mP\|SL** | KHONG (<2) |

- `win%`/`TSloss%` (2 rate **không phụ thuộc size**): **giảm chất lượng ở CẢ 4** (win% −17,6 … −52,5; TSloss% +25,5 … +54,2 — ngoài CI theo hướng **XẤU**). Đây là **thay đổi chất lượng THẬT**, không phải artifact.
- `mP|SL` dương ngoài CI ở mọi arm nhưng **là artifact nhân size USDT** ⇒ theo luật siết chỉ còn **1 rate** ⇒ **KHÔNG đạt "≥2 rate cùng hướng TỐT"** ở bất kỳ arm.

## 4. 3 CHỈ SỐ MARTINGALE

| arm | conc 1 coin% | conc>15 | lỗ lớn nhất 1 vị thế/1 coin (theo năm, USDT) | coin "chết" (ΣPnL<0) |
|---|---|---|---|---|
| S0 | 6,77 | KHÔNG | −321 · −450 · −731 · −913 · **−2.483** (2025) | 52 / 272 |
| S1 | 4,85 | KHÔNG | −201 · −251 · −130 · −296 · **−548** | **140 / 257** |
| S2 | 5,03 | KHÔNG | −200 · −222 · −113 · −261 · **−500** | **200 / 348** |
| S3 | 6,22 | KHÔNG | −235 · −705 · −185 · −292 · **−675** | 93 / 271 |
| S4 | 4,92 | KHÔNG | −200 · −227 · −118 · −265 · **−494** | **154 / 255** |

- **conc 1 coin ≤ 15 %: PASS mọi arm** (không martingale-tập-trung về 1 coin).
- **Cắt lỗ sớm CÓ giảm lỗ đuôi 1 vị thế** (−2.483 → **−494…−548**) — nhưng **đổi giá rất đắt**: số coin "chết" **52 → 140–200** (S1/S2/S4) và `median`/leg **>0 → <0**.

## 5. TRẢ LỜI 4 CÂU BẮT BUỘC

**(1) Arm nào PASS (a) VÀ (b′)? → KHÔNG có (0/4).** Cụ thể: (a) 0/4 (S1/S2/S4 **lỗ** ⇒ loại; S3 `%top-1`=32,30); (b′) 0/4 (`TF50` = −48.012 / −50.893 / −24.032 / −39.057).
**(2) `asym` từng arm — có `<1` mà PnL dương?** S1 1,036 (lỗ) · **S2 0,711 (lỗ)** · S3 1,463 (dương) · **S4 0,716 (lỗ)** ⇒ **KHÔNG**: 2 arm `<1` đều **LỖ**; arm dương duy nhất có `asym`>1. **Tái xác nhận: `asym<1` ⟺ lỗ ở họ này.**
**(3) SL cứng sớm (S1/S4) làm gì `TF50` / `maxDD` / `UW`?** `TF50` **âm THÊM** (−17.551 → −48.012 / −39.057), `maxDD` **sâu gấp 3–4,5×** (−6,27 → −21,40 / −28,57 %), `UW` **166 → 1.487**. **Không lật được dấu (b′) — còn tệ hơn base.** Cơ chế: `PRE_ARM_SL` cắt ở `firstEntryPrice·(1−k)` trên cụm **trước khi arm** ⇒ đóng đúng những cụm đang DCA mà lẽ ra hồi ⇒ `median`/leg < 0, coin chết tăng.
**(4) KẾT LUẬN CỨNG.** **0/4 arm PASS ⇒ trong HỌ hiện tại KHÔNG thể đạt (a)+(b′) bằng tinh chỉnh tham số; phải ĐỔI HỌ chiến lược.**
Họ MỚI (theo số, 1 dòng): họ có **win-rate thấp + lỗ nhỏ + winner không lồ** — tức **thoát phụ thuộc đuôi thắng** (đối lập trực tiếp với họ hiện tại: `asym≈3,4`, `conc_5`=46,7 %, `q*`=21,2 % ⇒ PnL đến từ 21 % lệnh lớn nhất). Kênh "cắt lỗ sớm" **đã thử và bị loại** vì nó phá chính nhóm thắng.

## 6. MỤC BỎ + LÝ DO

- **Không bỏ arm nào** (ngân sách đủ 4 slot ≤ 5; S1,S2,S3,S4 đều chạy xong).
- Bỏ **CI cho (a)/(b′)/4 thước**: là **đại lượng tổng toàn chuỗi** (không phải ước lượng mẫu) ⇒ điểm là đủ (nhất quán `RESULT_GROSS_ASYMMAP` §4).
- **KHÔNG suy diễn** grid vs reactive DCA (thiếu metadata — mọi `multi_leg_frac≈0`, như `RESULT_GROSS_ASYMMAP`).

## 7. TÁI LẬP

```
python3 research/analysis/shape1_run.py arms        # submit + wait + fetch (4 chặn Kaggle)
python3 research/analysis/size_count_score.py sh1-s1-sl05 sh1-s2-sl03k16 sh1-s3-ts8 sh1-s4-sl03 \
        --base cd-sel15 --k 4 --json /home/ubuntu/kaggle_sim/out/shape1_score.json
python3 research/analysis/shape1_martingale.py cd-sel15 sh1-s1-sl05 sh1-s2-sl03k16 sh1-s3-ts8 sh1-s4-sl03
```
Jar `sha256 43888ebd…ad518d` (`sim-jar-cadence`). Kernel: `chuyendinh/sim-sh1-s1-sl05` · `sim-sh1-s2-sl03k16` · `sim-sh1-s3-ts8` · `sim-sh1-s4-sl03` (private, Kaggle CPU, chi phí 0).
