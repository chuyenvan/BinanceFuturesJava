# RESULT — GATE × K FRONTIER (Phase 1: seed 42, daily-level)

Pre-reg `docs/prereg/PREREG_GATE_K_FRONTIER.md` (+ADDENDUM-1). Nền = `gkf-nen` (K24 pct base, md5 `ad26fd55…`, cổng nền PASS).
Chấm **daily-level** (CAGR22 / maxDD22 / Calmar22 từ equity ngày). **CHƯA** chấm MTM-minute + 3 seed + stress cost (§8/§9) ⇒ kết quả **sơ bộ, 1 seed**; Calmar ở đây KHÁC Calmar MTM của pre-reg (nền MTM 1,662 vs daily 2,363).

## 1. Bảng frontier (sort theo n/năm)

| tag | K | pct | n/năm | CAGR22 | maxDD22 | Calmar22 | eq_final |
|---|---|---|---|---|---|---|---|
| gkf-736-k40 | 40 | 0,999999884 | 256 | 18,20 | −7,00 | 2,600 | 73566 |
| gkf-p0b-k48 | 48 | 0,999999869 | 293 | 18,72 | −7,78 | 2,408 | 74937 |
| gkf-1k-k40 | 40 | 0,999993736 | 364 | 19,04 | −9,68 | 1,967 | 73868 |
| gkf-736-k32 | 32 | 0,999981560 | 466 | 25,43 | −10,87 | 2,338 | 108153 |
| gkf-736-k12 | 12 | 0,999924707 | 607 | 32,46 | −10,73 | 3,027 | 117291 |
| gkf-1k-k32 | 32 | 0,999971815 | 654 | 30,29 | −14,74 | 2,055 | 121843 |
| gkf-736-k16 | 16 | 0,999937768 | 662 | 31,31 | −15,59 | 2,008 | 117609 |
| **gkf-nen (NỀN)** | 24 | 0,999950829 | 736 | 36,93 | −15,63 | 2,363 | 146078 |
| **gkf-1k-k16** | 16 | 0,999922492 | **805** | 35,82 | −15,05 | **2,381** | 131313 |
| gkf-1k-k24 | 24 | 0,999939977 | **921** | 35,08 | −18,29 | 1,918 | 129135 |
| gkf-l2-k16 | 16 | 0,999880000 | **1133** | 35,73 | −20,21 | 1,768 | 130310 |
| gkf-l2-k24 | 24 | 0,999895000 | 1432 | 37,88 | −21,43 | 1,768 | 140945 |
| gkf-l2-k32 | 32 | 0,999915000 | 1602 | **41,08** | −20,13 | 2,041 | 156807 |
| gkf-l2-k24b | 24 | 0,999870000 | 1706 | 38,90 | −22,07 | 1,763 | 147386 |

## 2. Đọc kết quả

- Quy luật: **pct thấp hơn (nới cửa) ⇒ n tăng**; **K lớn hơn ⇒ n giảm** (cùng mục tiêu). Vùng tốt nhất K≈16–24.
- **Điểm "tăng n miễn phí": `gkf-1k-k16` (K16 @0,9999225) → 805 lệnh/năm** (+9% so nền 736), Calmar22 2,381 ≥ nền 2,363, CAGR22 35,82 ≈ nền 36,93 ⇒ chất lượng gần như KHÔNG giảm.
- **~1000 lệnh/năm:** gần nhất `gkf-1k-k24` (921/năm) và `gkf-l2-k16` (1133/năm).
- **Vượt 1000:** `l2-k24` 1432, `l2-k32` 1602 (CAGR22 41,08 = cao nhất), `l2-k24b` 1706 — nhưng maxDD sâu hơn (−20…−22 vs nền −15,6).

## 3. Verdict (sơ bộ, 1 seed, daily-level)

Luật GO iso-1000 (§9): Calmar22 ≥ 0,90 × NỀN **+ maxDD ≤ 40% + mean ΔPnL>0 + ≥3/4 năm ΔROI≥0**.

- (Proxy daily) Calmar ≥ 0,90 × 2,363 = **2,127**: nền (2,363), **1k-k16 (2,381)**, 736-k12 (3,027), 736-k32 (2,338), p0b-k48 (2,408), 736-k40 (2,600).
- Mọi arm ≥ ~1000 (1k-k24 1,918; l2-k16 1,768; l2-k24 1,768; l2-k32 2,041; l2-k24b 1,763) đều **Calmar < 2,127 ⇒ FAIL C4 (proxy)**.
- ⇒ **Không arm nào đạt ~1000 lệnh/năm mà giữ Calmar ≥ 0,90× nền** (theo proxy daily). Điểm cao nhất còn đạt là **1k-k16 = 805/năm**.

## 4. Hướng chốt (đề xuất)

- Ưu tiên **giữ chất lượng**: **K16 @0,999922492 → 805/năm** (+9% lệnh, Calmar không giảm).
- Cần **~1000**: **K24 @0,999939977 → 921/năm** (Calmar 0,81× nền) — gần 1000 nhất trong nhóm còn dùng được.
- Chấp nhận **rủi ro cao hơn**: **K32 @0,999915 → 1602/năm** (CAGR22 41,08 cao nhất, Calmar 0,86× nền).
- **Chưa chốt promotion**: cần Phase 2 (3 seed + MTM-minute + stress) theo §8/§9.

## 5. Lệch pre-reg

- pct hiệu chuẩn **offline** (ADDENDUM-1) lệch thực tế lớn, đặc biệt pct→1: offline ước K48 ≈1227/năm, sim thực **293/năm**. Bộ đếm offline chỉ đúng vùng pct 0,99985–0,99995 ⇒ pct các arm chặt bị sai; **vòng 2** phải chạy thêm 4 arm pct nới (K16/24/32 @ 0,99987–0,999915) để phủ vùng ~1000.
- Cần ADDENDUM-2 đính chính (sàn offline là ảo) + ghi rõ vòng 2 ngoài pre-reg.
