# RESULT_LS_TAKER — ba cột CHƯA TỪNG CHẠM: `ls_global` · `ls_toptrader` · `taker_buy`

Ngày đo: 2026-09-24. Pre-reg: `docs/PREREG_LS_TAKER.md` (**commit `51cfe29`**, chốt **TRƯỚC** khi đo;
sau đó **không sửa thiết kế**). Script: `research/analysis/ls_taker_build.py` (dựng panel),
`research/analysis/ls_taker.py` (đo), `research/analysis/ls_taker_decle.py` (thang decile đầy đủ H1 —
phần `§1.H1` **đã đăng ký**, không phải post-hoc), `research/analysis/ls_taker_sim.py` (biến thể phí SIM).

Ràng buộc đã tuân: **thuần Python**; **không** Java/sim trên Oracle; **không** `claude-run`/Claude Code;
**không push**; **không chạm HOLDOUT 2026** (ma trận dừng ở `2025-12-31 23:00`, mọi cửa sổ `< 2026-01-01`).
Trung gian `/tmp/ls_study/`.

---

## 0. KẾT LUẬN (một dòng mỗi giả thuyết)

> **H1 — `ls_global` như factor cross-section: NO-GO.** Cả **10/10 decile đều net ÂM**; decile long-crowded
> nhất **Q9 = −0,2820%** vs EW `−0,2237%`, chênh **`Q9−EW = −0,0583%`** CI72h_x1.21 `[−0,4561, +0,3396]`,
> **MDE(p80) = 0,3239%** ⇒ hiệu ứng **dưới MDE 5,6×**. Hướng (ls_global cao ⇒ tệ hơn) **nhất quán nhưng vô
> dụng cho long-only**. **Không decile nào net > 0 ⇒ long-only BẤT KHẢ.**
>
> **H2 — `ls_toptrader` + phân kỳ smart-vs-retail: NULL.** Đây là giả thuyết **được kỳ vọng nhất** và nó
> **thất bại**: `div = log(lst) − log(lsg)`, `Q9−EW = −0,0324%` CI72h_x1.21 `[−0,4217, +0,3570]`,
> MDE `0,3107%`; mức `lst` `Q9−EW = −0,0623%` CI `[−0,4623, +0,3377]`. Q9 net `−0,2559%` **< 0**.
> **Không decile nào net > 0.**
>
> **H3 — `taker_buy` overlay lên MOM15: NULL (và hơi NGƯỢC dấu).** Tercile **cao `tak`** `+1,9590%` vs
> **thấp** `+3,0392%` ⇒ `ter2−ter0 = −1,0802%` CI72h_x1.21 `[−5,1451, +2,9847]`, **MDE(p80) = 2,3561%**
> ⇒ dưới MDE; OOS `−2,4916%` nhưng CI cực rộng; AUC `0,4854` (< 0,5). Biến thể `rank_cs` `−0,0718%`
> (AUC `0,4949`), `tak` như factor cross-section `Q9−EW = +0,0303%` (MDE `0,2867%`) ⇒ **zero**.
>
> ⇒ **(4) BA CỘT NÀY KHÔNG DÙNG ĐƯỢC — ĐÓNG TRỤC DỮ LIỆU OI HOÀN TOÀN (đủ 5/5 cột).**

---

## 1. Cổng tự-kiểm (chạy TRƯỚC khi đọc số)

| Cổng | Kỳ vọng | Vòng này | Đạt |
|---|---|---|---|
| **G1** sha256 `oi_percoin_full.bin` | `e3887f63…b305ec` | `e3887f63097299655213f8382ca7e473e126ee4d7ddf69a39658942651b305ec` | ✔ |
| **G1b** kích thước = N × 30B, dư 0 | 140 924 110 × 30 | 4 227 723 300, dư **0** | ✔ |
| **G1c** lưới 5m | `ts % 300000 == 0` | **100%** (mẫu 8 000 000 bản ghi) | ✔ |
| **G2** funding Aerospike | 627/627 đọc được, 0 miss | **miss = 0** | ✔ |
| **G3** **neo MOM15** (pre-reg §3b) | `net@0,10% = +1,6690%`, n = **7 128** | **+1,6690%**, n = **7 128** | ✔ |
| **G4** không có dòng ≥ 2026 trong cửa sổ đo | 0 | **0** (panel dừng `2025-12-31 23:00`) | ✔ |
| **G5** đối chứng universe EW cùng kỳ | có, mọi bảng | có (hàng `EW` **mọi** bảng) | ✔ |

---

## 2. BƯỚC 0 — schema 3 cột mới (giá trị THẬT, không suy diễn)

Mẫu **8 000 000** bản ghi rải đều toàn file. `>f4` là **float32 thô** theo đơn vị tự nhiên ⇒ **không cần chia 1e**.

| cột | min | p01 | **p50** | p99 | max | mean | %NaN | đọc ra là gì |
|---|---|---|---|---|---|---|---|---|
| `ls_global` | 0,20712 | 0,45323 | **1,99335** | 5,83468 | 19,59666 | 2,15559 | **0,50%** | **ratio long/short** (p50 ≈ 2) ⇒ dùng `log()` |
| `ls_toptrader` | 0,00000 | 0,46518 | **2,11891** | 5,65241 | 15,04860 | 2,23854 | **9,57%** | **ratio long/short** ⇒ dùng `log()` |
| `taker_buy` | 0,00000 | 0,08878 | **0,49306** | 0,90953 | 1,00000 | 0,49348 | **3,41%** | **tỷ lệ KL mua chủ động ∈ [0,1]** ⇒ dùng mức |

**Không cột nào là hằng số / toàn NaN ⇒ không bỏ cột nào** (off cột: `ts` @0..7, `sym` @8..9, 5×`f4` @10..29;
thứ tự `oi_delta24h`, `oi_z`, `ls_global`, `ls_toptrader`, `taker_buy`).

### 2.1 ⚠ LỖ HỔNG DỮ LIỆU 2022 (phát hiện ở Bước 0, định hình cửa sổ)

| tháng | `ls_global` | `ls_toptrader` | `taker_buy` |
|---|---|---|---|
| 2022-01 | 40,5% | **4,1%** | 4,1% |
| 2022-02…2022-04 | 100% | **0,9-1,6%** | 0,9-1,6% |
| 2022-05 | 100% | 27,5% | 84,2% |
| 2022-06 | 100% | 64,1% | 99,8% |
| 2022-07…2022-11 | 100% | **~0,0-0,7%** | 100% |
| 2022-12 | 100% | 72,3% | 100% |
| **2023-01 → 2025-12** | **100%** | **100%** | **100%** |

⇒ Cửa sổ chính **W1 = 2023-01-01 → 2026-01-01** (26 304 mốc giờ, **297,7 symbol/mốc** min 142 max 531);
**IS = 2023-2024**, **OOS = 2025**. `ls_global` chạy **thêm** W0 = 2022-2025 như biến thể đã đăng ký.
Đây là lý do **không** tái dùng IS/OOS 2022-2023/2024-2025 của vòng OI — **ghi trước**, không phải cớ sau.

---

## 3. H1 — `log(ls_global)` như FACTOR cross-section (k_H1 = 6)

Lưới 1h, decile rank tất định, **Q9 = ls_global CAO nhất**. Phí CHÍNH = harness (0,10% RT + slip `0,5×range` + funding).
Thang decile **đầy đủ 0..9**, W1, H = 24h, net %/lệnh:

| Q | 24h net | CI72h_x1.21 | `Q−EW` (pp) | OOS net |
|---|---|---|---|---|
| **Q0** (crowded SHORT nhất) | **−0,1008%** | [−0,3629, +0,1613] | **+0,1229** | −0,2893% |
| Q1 | −0,2530% | [−0,5204, +0,0144] | −0,0293 | −0,4448% |
| Q2 | −0,1999% | [−0,4759, +0,0762] | +0,0239 | −0,3805% |
| Q3 | −0,2300% | [−0,5138, +0,0538] | −0,0062 | −0,3902% |
| Q4 | −0,2207% | [−0,5091, +0,0677] | +0,0031 | −0,4128% |
| Q5 | −0,2285% | [−0,5229, +0,0659] | −0,0048 | −0,4175% |
| Q6 | −0,2236% | [−0,5183, +0,0710] | +0,0001 | −0,3820% |
| Q7 | −0,2494% | [−0,5526, +0,0537] | −0,0257 | −0,4343% |
| Q8 | −0,2522% | [−0,5617, +0,0573] | −0,0285 | −0,4169% |
| **Q9** (crowded LONG nhất) | **−0,2820%** | [−0,5963, +0,0323] | **−0,0583** | −0,4111% |
| **EW (universe)** | −0,2237% | [−0,5083, +0,0609] | — | −0,3978% |

- **Số decile net > 0 = 0/10. Không decile nào CI ngoài 0 phía dương.**
- Dạng **giống hệt H1 của `RESULT_OI_STUDY`**: nửa trên đơn điệu — **càng crowded-long càng tệ**
  (Q6→Q9: `+0,0001 → −0,0257 → −0,0285 → −0,0583` so EW). **Hướng thông tin có, nhưng chỉ dùng được ở
  phía short/avoid — long-only thì không có hướng nào.**

**Tương phản + biến thể đã đăng ký** (net %/lệnh):

| ô (đăng ký) | hiệu ứng | CI72h_x1.21 | CI_adj(√6) | MDE(p80) | OOS | q+OOS |
|---|---|---|---|---|---|---|
| **1. H1 W1 24h `Q9−EW`** | **−0,0583%** | [−0,4561, +0,3396] | **[−1,0328, +0,9162]** | 0,3239% | −0,0133% | 50% |
| 2. H1 W1 4h `Q9−EW` | −0,0008% | [−0,0777, +0,0762] | [−0,1892, +0,1877] | — | +0,0064% | 50% |
| 3. H1 W1 1h `Q9−EW` | +0,0066% | [−0,0150, +0,0282] | [−0,0462, +0,0594] | — | +0,0090% | 75% |
| 4. `Δ24h log(lsg)` 24h `Q9−EW` | −0,0450% | [−0,4253, +0,3353] | [−0,9766, +0,8866] | — | −0,0020% | 50% |
| 5. W0 (2022-2025) 24h `Q9−EW` | −0,0703% | [−0,4513, +0,3108] | [−1,0037, +0,8631] | — | −0,0133% | 50% |
| **6. H1-REGIME (EW 24h) `ter2−ter0`** | **−0,5487%** | [−1,2278, +0,1303] | **[−2,2121, +1,1146]** | — | −1,4986% | 0% (1q) |

**H1-REGIME (tercile THEO THỜI GIAN của median cross-section `log(lsg)`) — EW 24h:**

| regime | N | net 24h | CI72h_x1.21 | IS | OOS |
|---|---|---|---|---|---|
| ter0 (ít crowded-long nhất) | 3 700 179 | −0,0556% | [−0,4791, +0,3679] | +0,5442% | −0,1334% |
| ter1 | 2 230 269 | −0,1120% | [−0,5648, +0,3408] | +0,2257% | −1,3000% |
| **ter2 (crowded-long nhất)** | 2 192 340 | **−0,6044%** | **[−1,1516, −0,0571]** | −0,4523% | −1,6320% |

- Đây là chỗ **duy nhất** trong cả vòng có `p(diff>0) = 0,023` (< 0,05 một phía) và **hướng đúng dự đoán**
  ("thị trường crowded-long ⇒ forward return xấu hơn"). **NHƯNG không GO:**
  (a) `CI72h_x1.21` **chứa 0** (`[−1,2278, +0,1303]`), CI hiệu chỉnh càng chứa 0;
  (b) **OOS chỉ có 1 quý** có mặt ở nhánh ter2 ⇒ `q+OOS` vô nghĩa về mặt thống kê;
  (c) tercile **theo thời gian** = các **khối thời gian liền mạch** ⇒ lẫn với **"thời kỳ" thị trường**,
  không phải một chỉ báo regime dừng. ⇒ ghi rõ là **UNCONFIRMED**, và nó là câu hỏi **cấp THỊ TRƯỜNG**
  (giảm rủi ro), **không** phải cấp coin, và **không** phải tín hiệu vào lệnh.
- **Biến thể phí SIM (0,80% phẳng, `ls_taker_sim.py`):** EW `−0,7991%`, Q9 `−0,8664%`, Q0 `−0,6248%`,
  `Q9−EW = −0,0673%` ⇒ **cùng dấu, cùng cỡ** với phí harness ⇒ **không đổi kết luận**.

---

## 4. H2 — `ls_toptrader` + **phân kỳ smart-vs-retail** (k_H2 = 3)

| ô (đăng ký) | hiệu ứng | CI72h_x1.21 | CI_adj(√3) | MDE(p80) | OOS | q+OOS |
|---|---|---|---|---|---|---|
| **7. W1 `div = log(lst)−log(lsg)` 24h `Q9−EW`** | **−0,0324%** | [−0,4217, +0,3570] | **[−0,7068, +0,6421]** | 0,3107% | −0,1168% | **0%** |
| 8. W1 `div` 4h `Q9−EW` | +0,0105% | [−0,0631, +0,0841] | [−0,1170, +0,1379] | — | +0,0080% | 75% |
| 9. W1 `log(lst)` mức 24h `Q9−EW` | −0,0623% | [−0,4623, +0,3377] | [−0,7551, +0,6305] | — | −0,0609% | 25% |

- Net tuyệt đối: `div` Q9 `−0,2559%`, `div` Q0 `−0,2930%`, `lst` Q9 `−0,2858%`, `lst` Q0 `−0,0959%`,
  EW `−0,2235%` ⇒ **Q9 net < 0 ở mọi ô; long-only bất khả.**
- **Giả thuyết được kỳ vọng nhất ("top trader long hơn đám đông ⇒ forward tốt hơn") KHÔNG có tín hiệu**:
  hiệu ứng ~0 và **ngược dấu ở 24h** (−0,032% và −0,062%), dưới MDE ~10×, `q+OOS = 0%`.
- Biến thể phí SIM: EW `−0,7990%`, `div` Q9 `−0,8418%`, `Q9−EW = −0,0429%` ⇒ cùng dấu ⇒ không đổi.

---

## 5. H3 — `taker_buy` OVERLAY lên MOM15 (k_H3 = 3)

Bộ event = MOM15 M-LEVEL k=1 (`/tmp/funding_factor/pools.npz`), n_DEV = **7 128**, HOLD 24h,
net lấy nguyên `m_raw[24h] − m_slip − m_fund[24h] − 0,0010`. Trong W1: **5 436** event, coverage tra
`taker_buy` (**≤15 phút**) = **99,9%**.

| ô (đăng ký) | hiệu ứng | CI72h_x1.21 | CI_adj(√3) | MDE(p80) | OOS | q+OOS |
|---|---|---|---|---|---|---|
| **10. `tak` MỨC `ter2−ter0` 24h** | **−1,0802%** | [−5,1451, +2,9847] | **[−8,1208, +5,9604]** | 2,3561% | −2,4916% | 50% |
| 11. `tak` **rank(cs)** `ter2−ter0` 24h | −0,0718% | [−2,7992, +2,6555] | [−4,7957, +4,6521] | — | −0,4954% | 50% |
| 12. `tak` MỨC decile cross-section 24h `Q9−EW` | +0,0303% | [−0,3450, +0,4056] | [−0,6197, +0,6804] | 0,2867% | +0,0324% | 75% |

Chi tiết tercile `tak` MỨC (n = 5 433, W1):

| tercile | N | net 24h | CI72h_x1.21 | IS | OOS | AUC(thắng/thua) |
|---|---|---|---|---|---|---|
| ter0 (tak thấp) | 1 811 | **+3,0392%** | [−0,3527, +6,4312] | +2,3233% | +3,7159% | — |
| ter1 | 1 811 | +1,5118% | [−0,1482, +3,1718] | +2,8388% | +0,3740% | — |
| ter2 (tak cao) | 1 811 | +1,9590% | [−0,0474, +3,9655] | +3,0983% | +1,2243% | — |
| | | | | | | **0,4854** (toàn bộ) |

- **Toàn bộ tercile đều net rất dương (+1,5% … +3,0%) — đó là EDGE CỦA MOM15, không phải của `taker_buy`.**
  Cái phải đọc là **tương phản**: `−1,0802%` (dưới MDE 2,36%; hơi **ngược dấu** dự đoán), AUC **0,4854 < 0,5**.
- Biến thể `rank_cs` (không phụ thuộc mức thị trường) `−0,0718%`, AUC **0,4949**; `tak` như factor
  cross-section riêng `+0,0303%` (MDE 0,287%) ⇒ **zero**. **Cả 3 ô ⇒ NULL.**
- **Không ô nào cho một ngưỡng lọc coin/entry dùng được.**
- Biến thể phí SIM: `ter2−ter0 = −1,1087%`, `tak` cs `Q9−EW = +0,0149%` ⇒ cùng dấu ⇒ không đổi.

---

## 6. MDE (p80 nửa-độ-rộng ×1,21 trên 500 chuỗi null sign-flip 72h)

| nhánh | N | half ×1,21 | **MDE(p80)** | MDE_adj | 2,8×SD(null) |
|---|---|---|---|---|---|
| H1 W1 24h Q9 | 769 747 | 0,3143% | **0,3239%** | 0,7935% | 0,3737% |
| H1 W1 24h EW | 7 807 520 | 0,2846% | 0,2951% | 0,7228% | 0,3413% |
| H2 `div` W1 24h Q9 | 769 659 | 0,2932% | **0,3107%** | 0,5381% | 0,3616% |
| H2 `div` W1 24h EW | 7 806 619 | 0,2846% | 0,2950% | 0,5110% | 0,3413% |
| H3 `tak` ter2 | 1 811 | 2,0064% | **2,3561%** | 4,0810% | 2,9982% |
| H3 `tak` ter0 | 1 811 | 3,3920% | 3,7806% | 6,5482% | 5,0169% |
| H3var `tak` cs Q9 | 769 747 | 0,2733% | 0,2867% | 0,4966% | 0,3314% |
| H3var `tak` cs EW | 7 807 518 | 0,2846% | 0,2951% | 0,5111% | 0,3413% |

**Mọi hiệu ứng đã đo đều nhỏ hơn MDE tương ứng** (H1 24h: 0,058% vs 0,324%; H2 24h: 0,032% vs 0,311%;
H3: 1,08% vs 2,36%) ⇒ **không ô nào đạt ngưỡng phán quyết**.

---

## 7. Số giả thuyết / biến thể đã thử (chống multiplicity)

- **k = 3 giả thuyết chính** (H1/H2/H3) — **12 ô đo đã đăng ký trước** (3 chính + 9 biến thể),
  `k_H1 = 6`, `k_H2 = 3`, `k_H3 = 3`.
- Cộng **thang decile đầy đủ 0..9** cho H1 24h (phần `§1.H1` đã đăng ký "đo từng decile") ⇒ **+8 ô**
  (Q9/Q0 đã nằm trong 12) ⇒ **tổng 20 ô đo**.
- CI phán quyết = `CI72h_x1.21 × √k_giả_thuyết` (H1 √6 = 2,449; H2/H3 √3 = 1,732); mức **toàn cục**
  √12 = 3,464 đã ghi trong pre-reg. **Không ô đo nào của 3 giả thuyết có `CI72h_x1.21` ngoài 0 theo
  hướng dương** (ban đầu chưa hiệu chỉnh) ⇒ hiệu chỉnh multiplicity không làm thay đổi kết luận nào.
- **Không** thêm biến thể nào ngoài đăng ký để "cứu" kết quả âm.

## 8. LỖI HARNESS đã phát hiện & sửa (ghi rõ để minh bạch)

Trong lần trích **giá trị 5m tại sự kiện MOM15**, bản đầu tôi so khớp bằng **`symId` của file OI**, nhưng
`pools.npz::m_sym` là **CHỈ SỐ CỘT 0-based** (0..626, `max = ncol−1 = 626`, theo thứ tự `sorted glob RAW/*.f32`),
**không phải `symId`** (`symId` của cột 0..4 là 524/453/311/210/300; `symId` tối đa 789). Hệ quả: chỉ
**48,1%** "khớp" và **lệch coin**. Đã sửa (quy `symId → cột` trước khi so khớp) ⇒ coverage **99,9%**.
- Bản **bị lỗi**: `tak` MỨC `ter2−ter0 = +0,3214%` (CI [−4,8059, +5,4487]) ⇒ **NULL**.
- Bản **đã sửa**: `−1,0802%` (CI [−5,1451, +2,9847]) ⇒ **NULL**.
- Nhánh `rank_cs` **không bị ảnh hưởng** (nó tra panel giờ theo **đúng** chỉ số cột) — và cũng **NULL**.
⇒ **Kết luận H3 bất biến với lỗi này**; nêu ra để người sau không lặp lại.

---

## 9. KẾT LUẬN — trả lời trực tiếp 4 câu hỏi

**(1) Cột nào có thông tin THẬT (ngoài MDE), theo hướng nào?**
**KHÔNG cột nào.** 20/20 ô đo đều **nhỏ hơn MDE**. Hai "hint" duy nhất cùng hướng — **đều ÂM**, tức
"crowded-long / taker-buy cao ⇒ forward return XẤU HƠN" — là:
(i) **H1-REGIME** `ter2−ter0 = −0,5487%` (p một phía 0,023, OOS `−1,50%`) nhưng **CI chứa 0**, **chỉ 1 quý OOS**,
tercile theo thời gian ⇒ lẫn "thời kỳ"; (ii) **H3** `tak` cao ⇒ `−1,08%` nhưng **CI ±5%**, AUC 0,485.
Cả hai **không dùng được cho long-only** (hướng thông tin chỉ nằm ở phía short/avoid — mà long-only thì
**không có hướng nào khả thi**: 0/10 decile net > 0). Trục "phân kỳ smart-vs-retail" — kỳ vọng nhất —
là **NULL rõ ràng** (`q+OOS = 0%`).

**(2) Có đề xuất lọc coin / đặt ngưỡng tín hiệu không?**
**KHÔNG.** Không ô nào vượt MDE; và **filter cấp-coin đã biết VÔ HIỆU** (hệ lấy coin kế tiếp) — nên kể cả
có hiệu ứng cũng không đề xuất. Hint H1-REGIME là **cấp THỊ TRƯỜNG (thời gian)**, không phải cấp coin,
và ở trạng thái **UNCONFIRMED**.

**(3) Nếu có ⇒ cải tiến cổng AI thế nào + ước lượng tác động lên số ung viên PASS?**
**Không áp dụng** — không có cơ sở. Không tăng/giảm gì ở cổng AI.

**(4) Nếu không ⇒ đóng trục dữ liệu OI hoàn toàn?**
**CÓ. ĐÓNG TRỤC DỮ LIỆU OI HOÀN TOÀN, đủ 5/5 cột.** `oi_delta24h` + `oi_z` ⇒ NO-GO/NULL (`RESULT_OI_STUDY`,
commit `745d722`); vòng này `ls_global` + `ls_toptrader` (+ phân kỳ) + `taker_buy` ⇒ **NO-GO / NULL / zero**,
không cột nào vượt MDE, không decile nào net > 0. ⇒ **`oi_percoin_full.bin` không còn cột nào chưa đo và
không có cột nào dùng được cho long-only hay cho lọc coin.** Trục này **đóng**; nguồn lực nên rời khỏi họ
đặc trưng "vị thế/đám đông/OI" và quay về **tín hiệu vào lệnh** (nơi có đòn bẩy thật theo chính kết luận
của chủ dự án: cổng AI + không nới cổng).

### Bước tiếp (đề xuất — **KHÔNG** tự tích hợp)
Chỉ còn **một** hướng chưa bị phủ định và **không** thuộc trục OI: **regime crowded-long cấp THỊ TRƯỜNG**
(H1-REGIME, `−0,55%`/24h, p một phía 0,023, OOS `−1,50%`) — nhưng đó là câu hỏi **giảm rủi ro/quản trị
exposure**, **không** phải tín hiệu vào lệnh và **không** phải lọc coin. Muốn dùng phải **pre-reg riêng**
với thiết kế chuỗi thời gian đúng: **quantile trượt** (không phải tercile chia theo thời gian — hiện tại
tercile là khối thời gian liền mạch nên lẫn "thời kỳ"), **neo MOM15 + EW** cùng kỳ, CI block-72h có hiệu
chỉnh multiplicity, và **chỉ** đánh giá như luật *giảm size / đứng ngoài* — **không** đưa vào cổng AI.
