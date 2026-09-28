# RESULT_BAR_A_CALIBRATION — Rào (a) `share top-1 % ≤ 15 %`: LỌC HỮU ÍCH hay KHÔNG THỂ ĐẠT?

Pre-reg: `docs/prereg/PREREG_BAR_A_CALIBRATION.md` (`71e3d2b`, chốt TRƯỚC). Harness:
`research/analysis/bar_a_calibration.py`. Dữ liệu: `docs/result/bar_a_calibration.json`.
Đơn vị: **U1 = cấp “lệnh” (1 leg = 1 lệnh/vị thế)** — đơn vị đúng của rào. Offline Python, 0 train/0 sim,
DEV ≤ 2025-12-31, **0** chạm 2026/242/ONNX/LIVE. **Tái lập `gross_asymmap` khớp 5e-11** (461/461).

## 0. Phân bố `share top-1 %` (định nghĩa pre-reg §2)

| tập | n | min | p25 | median | p75 | max | ≤15 | ≤25 | ≤50 | ≤100 |
|---|---|---|---|---|---|---|---|---|---|---|
| **POP arm (ledger, 461 run)** | 461 | −48 482 | 25,90 | 29,31 | 39,53 | 803,28 | **12** | **54** | **411** | **450** |
| **POP hợp lệ `Σ>0`** | 452 | **6,55** | 25,95 | 29,73 | 39,65 | 803,28 | **3** | **45** | **402** | **441** |
| **BOOK U1 (Track B: BOOK_EW+4)** | 5 | **209,85** | 257,63 | 264,94 | 374,84 | 381,84 | 0 | 0 | 0 | **0** |
| **SCORE_OBJ (45deploy/A44/A45/MRA4/MRB8/MRB32/S1/OFI×3)** | 15 | 25,28 | 30,03 | 30,99 | 32,42 | 36,04 | 0 | 0 | 15 | 15 |
| **G-D (exit/shape/family2/size_count)** | 16 | −89,81 | −2,28 | 15,53 | 17,27 | 37,35 | 7 | 14 | 16 | 16 |

**Đọc nhanh:** ở cấp **lệnh của arm**, trung vị ≈ 29 %, p25 ≈ 26 % ⇒ **15 % nằm dưới cả p25** (chỉ 0,66 % số arm).
Ở **đơn vị đúng của Track B (book U1)**, `share top-1 %` = **210–382 %** ⇒ 15 % **vượt 14–25×**;
thậm chí cả ngưỡng **100 %** cũng **không** đối tượng book nào đạt (top-25 % còn >1 000 %). Bộ 10 **SCORE_OBJ**
(45deploy…OFI) đều 25–36 %, **0/15** đạt 15 %.

**Đối tượng share THẤP NHẤT (hợp lệ `Σ>0`) = `selcut-cut`** (6,55 %): `n=248` lệnh ·
**winrate 87,1 %** · **asym 2,07** · **median/lệnh 66,5** · tần suất **58,8 lệnh/năm** · `q*=41,5 %`.
⇒ Mẫu hình đạt được `share top-1 %` thấp = **arm định hướng, TẦN SUẤT THẤP, winrate CAO, payoff ratio vừa
(asym≈2)** — net trải rộng trên nhiều lệnh, **không** dựa vào vài lệnh đuôi. (Ngược lại, book market-neutral
có net≈0 nên vài vị thế top-1 % “gánh” >200 % tổng ⇒ không thể hạ.)

## 1. Có đối tượng nào `share top-1 % ≤ 15 %` **và** PnL DƯƠNG BỀN (CI ngoài 0)?

**CÓ — nhưng chỉ 3/452 (0,66 %), và KHÔNG bền:**

| tag | n | share top-1 % | CI95 share (inflate k=8) | Σ PnL, CI95 | drop-25 % | CI drop-25 |
|---|---|---|---|---|---|---|
| `selcut-cut` | 248 | **6,55** | [0,68 ; **12,99**] (bền <15) | 12 911 [1 876 ; 24 386] | +3 841 | **[−3 629 ; +10 999]** |
| `gr-kg0-q998-15m` | 420 | 12,91 | [2,64 ; **23,69**] (KHÔNG bền) | 21 149 [7 534 ; 35 478] | +4 002 | **[−6 551 ; +13 906]** |
| `cd-sel15-q999` | 563 | 14,37 | [−1,37 ; **31,70**] (KHÔNG bền) | 28 188 [8 015 ; 48 629] | +1 973 | **[−16 504 ; +19 226]** |

- Cả 3 **PnL dương, CI ngoài 0** ⇒ (1) **không thể nói “15 % bất khả thi” theo nghĩa tuyệt đối**.
- Nhưng chỉ **1/3** có share **bền dưới 15 %** (`selcut-cut`); **0/3** qua **rào (b′)** một cách bền
  (CI của “bỏ top-25 %” **chứa 0** cho cả 3) ⇒ `PASS_both` **bền = 0/452**.
- **Ở đơn vị đúng của Track B (book/U1)**: 0/5 đạt, min 209,85 % ⇒ (a)@15 **bất khả thi với chính họ chiến lược mà rào nhắm tới** (17,7×).

## 2. Mức nào thì ĐẠT ĐƯỢC (trên 452 arm hợp lệ)

| ngưỡng T | PASS (a) `share≤T` | % | PASS (b′) `drop-25 %>0` | PASS **cả (a)+(b′)** |
|---|---|---|---|---|
| **15 %** | **3** | 0,66 % | 3 | **3** (bền: **0**) |
| **25 %** | **45** | 10,0 % | 7 | **7** |
| 50 % | 402 | 89,0 % | 9 | 9 |
| 100 % | 441 | 97,6 % | 9 | 9 |

⇒ **15 % ở mức bất khả thi-thực tế (0,66 %, p≈p0,7)**; **25 %** là mức tròn gần **p25 của phân bố arm (25,95 %)**
và **vẫn là bộ lọc thật** (10 % pass). **50/100 %** để gần như cả pool qua (a) ⇒ **mất tính lọc**.
(Trên **book U1** không mức nào ≤100 % đạt được.)

## 3. Đánh đổi: nới (a) thì (b′) có còn chặn?

Nới (a) **15 %→25 %**: `PASS_a` 3→45, `PASS_both` 3→**7**. Nhưng **rào (b′) mới là rào BINDING**:
chỉ **7–9/452** arm qua (b′) **bất kể (a)** (kể cả khi cho (a) tới 100 %).
⇒ Trên trục “thấp–cao của (a)”, **(b′) luôn là bên chặn** ⇒ **hai rào KHÔNG buộc phải đi cùng nhau**:
có thể nới (a) lên 25 % mà (b′) vẫn giữ nguyên tác dụng lọc.
**Cảnh báo:** nếu đòi cả hai rào phải **bền theo CI** thì **0/452** đạt (CI share ⊄ 15 hoặc CI drop-25 ∋ 0)
⇒ bộ **hai rào cùng lúc là không thoả mãn được một cách bền** — phải nới ít nhất một, hoặc coi (b′) là điểm không CI.

## 4. Kết luận + đề xuất

- **R-1 (bất khả thi tuyệt đối) KHÔNG kích hoạt**: `PASS_both(15)=3>0` ⇒ theo đúng luật đã chốt, **không**
  tuyên bố 15 % “không thể đạt” theo nghĩa chặt.
- **Nhưng 15 % là bộ lọc GẦN-DEGENERATE/không có nghĩa**: 0,66 % pass; **0 bền**; **bất khả thi 14–25× ở
  đơn vị đúng (book)**; chỉ đạt được ở **3 arm nhỏ, tần suất thấp, không đại diện họ chiến lược mục tiêu**.
- **ĐỀ XUẤT (theo R-2 — mức tròn nhỏ nhất có `PASS_both≥1` và `PASS_a≤50 %`):**
  1. **Với arm định hướng (“lệnh”): hạ (a) `15 % → 25 %`** (p25 arm ≈ 25,95 %; 45/452 pass; 7 pass cả (b′)).
     ✅ `T*=25 %`.
  2. **Với book market-neutral (Track B + 4 tín hiệu): BỎ (a)** (hoặc thay bằng thước tập trung khác) —
     `share top-1 %` **cấu trúc không tương thích** với book net≈0 (min 210 %, top-25 % >1 000 %); giữ **(b′)** làm rào chính.
  3. **Giữ (b′) `drop-25 %>0`** làm rào binding (nhưng nên ghi rõ hiện **chỉ điểm**, không bền theo CI).
- **KHÔNG bỏ (b′)**: nó đang là rào thực sự chặn (7–9/452), còn (a)@15 chỉ chặn 3.

## 5. Trả lời ngắn (task)

1. `share≤15 %` + PnL dương CI ngoài 0: **CÓ, 3 đối tượng** — nhưng 0 bền cả 2 rào, và book (đơn vị đúng) 0/5.
2. Mức đạt được: **≤25 % → 45/452**; ≤50 % → 402/452 (mất lọc). **Đề xuất 25 %**.
3. Đánh đổi: nới (a) **không** làm hỏng (b′) ((b′) vẫn là rào chặn, 7–9/452) ⇒ không buộc đi cùng nhau.
4. **Đổi 15 % → 25 %** (arm) và **bỏ (a) cho book**; giữ (b′). Lý do: 15 % gần-degenerate + bất khả thi ở đơn vị đúng.
