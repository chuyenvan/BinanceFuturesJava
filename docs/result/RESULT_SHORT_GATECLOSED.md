# RESULT_SHORT_GATECLOSED — SHORT top-K8 (PA_t15_E10_S42) tại tick GATE LONG ĐÓNG × trailing CÓ ARM

Ngày **2026-10-03**, branch `module`. Pre-reg **`docs/prereg/PREREG_SHORT_GATECLOSED.md` (`64c711c8`, commit + push
TRƯỚC mọi phép đo; script chốt cùng commit, KHÔNG sửa sau đó)**. Code `research/analysis/short_gateclosed_sim.py`
(stage picks → sim → sanity → report). Số: `docs/result/RESULT_SHORT_GATECLOSED.json`. Cache lệnh (ngoài repo):
`~/claude_master/1003/sgc_cache/{picks,tr_YYYYMM}.parquet`, `sanity.json`.
Tuân thủ: 0 Java / 0 sửa `.java` / 0 chạm 242-shadow_c3 / DEV 2022–2025, 0 phút 2026 được đọc / dữ liệu v2 (lineage v2 +
CLOSES_1H_v2 + Aerospike 1m cắt tại `last_real_ts`) / funding EXACT / lock `oracle_heavy.lock`, RSS ≤ 4,3 GB.

## 0. KẾT LUẬN

**`NO-GO`** — 0/3 ô qua luật §5. Ô tốt nhất **E1** (arm 5 %/gap 3 %/SL +10 %/72h): **+0,225 %/lệnh**, CI raw
[−0,028; +0,473] (chứa 0), 3/4 năm dương, theo ngày +0,157 %, bỏ top-5 ngày +0,179 % — **nhưng** SL-rate 26,6 % > 25 % và
**không phải alpha**: random-K8 cùng tick gate đóng cho **+0,242 %** (SG − RG = −0,016 % [−0,236; +0,206]). Phần dương
là **beta của chế độ gate đóng** (short ngẫu nhiên cũng dương), selector không thêm gì. **E2 (no-SL, giả thuyết owner)
tệ hơn E1** (+0,027 %, 2/4 năm, theo ngày −0,081 %, p1 −49 %, min **−1 094 %**) ⇒ giả thuyết "cắt cứng làm mất lãi"
**bị bác** trong cấu hình này. E3 ≈ 0 (−0,017 %).

## 1. Feasibility (chi tiết ở pre-reg §1)

- Bins short `OLD_ndown_S42` / `PA_t15_E10_S42` chấm **toàn universe mọi tick 15'** (140 244 tick, trung vị 233 dòng/tick)
  — KHÔNG phải `cand_dev_x1`. Chỉ FULLCHAIN dùng `cand_dev_x1`. Các vòng SHORT_MODEL/LABEL2/PATHEXIT đã trộn gate mở ∪ đóng
  (≈92 % tick là gate đóng) nhưng chưa tách, trailing không arm, funding hằng số, dữ liệu v1.
- Không cần feature panel / export Java / train Kaggle: `PA_t15_E10_S42` chính là model phương án (c). Chi phí mở khoá = 0.
- Gate p15 tại phút m0 (khớp `cand_dev_x1.p15` 100 %). Tick gate đóng: **2022 32 066 · 2023 34 529 · 2024 32 866 ·
  2025 23 266** (gate mở 2 970 / 510 / 2 264 / 11 484).

## 2. Bảng chính — SG (SHORT top-K8, gate ĐÓNG), net %/lệnh sau phí 0,112 % + funding exact

n = **38 341** lệnh (2022 11 610 · 2023 9 503 · 2024 9 369 · 2025 7 859; 1 lệnh thiếu nến entry). Inflate ×1,4823.

| ô | mean | median | CI raw | CI infl | 2022 | 2023 | 2024 | 2025 | theo ngày | bỏ top-5 ngày | SL % | trail % | time % | gross | funding | giữ h | p1 | min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **E1** 5/3/SL10/72h | **+0,225** | +2,750 | [−0,028; +0,473] | [−0,150; +0,593] | +0,613 | −0,175 | +0,248 | +0,107 | +0,157 | +0,179 | **26,6** | 62,2 | 11,2 | +0,364 | −0,027 | 25,0 | −10,5 | −19,8 |
| **E2** 5/3/noSL/72h | +0,027 | +3,064 | [−0,371; +0,396] | [−0,564; +0,573] | +0,635 | −0,399 | +0,100 | −0,444 | −0,081 | −0,021 | 0 | 69,5 | 30,4 | +0,255 | −0,116 | 36,2 | **−49,4** | **−1 094** |
| **E3** 3/2/SL10/24h | −0,017 | +1,532 | [−0,146; +0,104] | [−0,208; +0,162] | +0,150 | −0,202 | +0,056 | −0,124 | −0,053 | −0,043 | 14,6 | 64,0 | 21,4 | +0,115 | −0,020 | 10,6 | −10,3 | −15,4 |

Funding SG **âm** (short TRẢ): top score short rơi vào coin funding âm (đám đông đã short) — ngược với RG (+0,01…+0,03).

## 3. Đối chứng

| tập · ô | n | mean | CI raw | 2022 | 2023 | 2024 | 2025 | theo ngày | SL % |
|---|---|---|---|---|---|---|---|---|---|
| (a) SO short, gate MỞ · E1 | 14 334 | −0,060 | [−0,286; +0,172] | +0,080 | −0,775 | +0,027 | −0,003 | −0,189 | 30,3 |
| (a) SO · E2 | 14 334 | −0,234 | [−0,677; +0,215] | +0,095 | −1,053 | −0,160 | −0,261 | −0,479 | 0 |
| (a) SO · E3 | 14 334 | −0,098 | [−0,246; +0,050] | −0,031 | −0,484 | −0,004 | −0,086 | −0,237 | 18,1 |
| (b) SG-LONG gương · E1 | 38 341 | −0,459 | [−0,718; −0,202] | −0,831 | +0,065 | −0,552 | −0,433 | −0,401 | 29,1 |
| (b) SG-LONG · E2 | 38 341 | −0,406 | [−0,790; −0,034] | −1,012 | +0,390 | −0,406 | −0,473 | −0,350 | 0 |
| (b) SG-LONG · E3 | 38 341 | −0,296 | [−0,421; −0,170] | −0,410 | −0,063 | −0,344 | −0,350 | −0,266 | 13,0 |
| (c) RG random-K8 short, gate ĐÓNG · E1 | 241 678 | **+0,242** | [−0,072; +0,535] | +0,528 | −0,131 | +0,140 | +0,446 | +0,270 | 19,7 |
| (c) RG · E2 | 241 678 | +0,199 | [−0,200; +0,560] | +0,621 | −0,183 | +0,038 | +0,395 | +0,233 | 0 |
| (c) RG · E3 | 241 678 | +0,040 | [−0,102; +0,176] | +0,122 | −0,049 | +0,040 | +0,058 | +0,066 | 7,0 |

Chênh (CI block-72h resample chung): **SG − RG** E1 −0,016 [−0,236; +0,206] · E2 −0,172 [−0,470; +0,117] · E3 −0,056
[−0,164; +0,049]. **SG − SO** E1 **+0,285 [+0,070; +0,500]** (infl [−0,034; +0,604]) · E2 +0,261 [−0,098; +0,615] · E3
+0,082 [−0,060; +0,224].

## 4. Verdict cơ học (§5 pre-reg)

| ô | C1 net>0 ngoài CI raw & infl | C2 ≥3/4 năm | C3 theo ngày & bỏ top-5 > 0 | C4 n ≥ 1500 | C5 SL ≤ 25 % | C6 alpha ≠ beta | GO |
|---|---|---|---|---|---|---|---|
| E1 | ✗ (raw lo −0,028) | ✓ (3/4) | ✓ | ✓ | ✗ (26,6 %) | ✗ (RG +0,242 > 0; SG−RG CI chứa 0) | ✗ |
| E2 | ✗ | ✗ (2/4) | ✗ | ✓ | — (miễn) | ✗ | ✗ |
| E3 | ✗ | ✗ (2/4) | ✗ | ✓ | ✓ | ✗ | ✗ |

⇒ **NO-GO**. Không ô nào qua; E1 hỏng 3 điều kiện độc lập (CI, SL-rate, alpha).

## 5. Diễn giải (không đổi verdict)

1. **Beta chế độ, không phải selector.** Gate long đóng ≈ thị trường không có đà tăng ⇒ short ngẫu nhiên + trailing có arm
   dương ở điểm (+0,24 %/lệnh E1), selector top-K8 KHÔNG hơn random (−0,016 pp). IC +0,05 của model short (RESULT_SHORT_MODEL)
   không chuyển thành lợi thế sau cooldown/exit đường giá; một phần bị funding âm ăn (−0,027 % E1, −0,116 % E2).
2. **Gate đóng tốt hơn gate mở cho short** (SG − SO E1 +0,285 pp, CI raw ngoài 0, infl chứa 0) — khớp phát hiện FULLCHAIN
   (short tại gate mở âm). Nhưng mức tuyệt đối vẫn chưa ngoài 0.
3. **Hướng đúng**: LONG gương cùng lệnh âm, CI raw ngoài 0 ở cả 3 ô (−0,30…−0,46 %) — tức trong gate đóng, top-score short không
   phải coin nên long; nhưng short chúng cũng không hơn short ngẫu nhiên.
4. **Giả thuyết owner (bỏ SL cứng)**: E2 − E1 = −0,20 pp mean, đuôi −1 094 % (coin ×11 trong 72h), p1 −49 %, 2025 −0,44 %.
   Trailing có arm KHÔNG thay được SL: 30,4 % lệnh E2 thoát bằng time-stop 72h (không có stop nào chặn chiều tăng trước arm).
5. **2023 âm ở mọi ô short** (SG, SO, RG — 9/9); năm 2022 (bear) gánh phần lớn mean ⇒ phụ thuộc chế độ năm.
6. SL-rate E1 26,6 % > ngưỡng: ở ±10 % trong 72h, ¼ lệnh short bị bắn trước khi arm 5 %.

## 6. Sanity (đã chạy trước report)

- Causal: `e = m0+15`, `ts = m0·60 000`, p15 tại m0, đường giá từ e+1; SG/RG p15 < 0,008, SO ≥ 0,008; `e+4320 < 2026-01-01`
  — mọi assert PASS (trong `sim_month` + `sanity`).
- **Vectorized vs loop** ngày 2024-03-05: 138 lệnh / 453 phép so, **0 lệch**, max |Δpnl| = 0.
- **10 lệnh mẫu** (202403, rng 20261003) đọc lại Aerospike độc lập từng phút + loop: **10/10 khớp** P, pnl, phút thoát,
  lý do (bảng trong `sgc_cache/sanity.json`). Kiểm tay 1 lệnh: SG POWRUSDT tick 2024-03-11 12:15, P = 0,4861 (close
  m0+15), min low 0,45540 (arm ở phút 92 sau entry), thoát phút 174: high 0,47140 ≥ mức 0,46906 = 0,4554×1,03, open
  0,46850 < mức ⇒ fill mức, pnl +3,505 % = khớp sim.

| tập | symbol | tick UTC | p15 | hạng | P | E1 pnl / lý do / giữ h | E2 | E3 | khớp |
|---|---|---|---|---|---|---|---|---|---|
| SG | POWRUSDT | 2024-03-11 12:15 | 0,0071 | 2 | 0,4861 | +3,505 % / TRAIL / 2,9 | +3,505 / TRAIL / 2,9 | +3,477 / TRAIL / 1,7 | ✓ (LONG E1/E2 −7,20 TIME, E3 +2,82 TRAIL) |
| RG | KAVAUSDT | 2024-03-04 06:30 | 0,0065 | 5 | 0,9772 | +3,767 / TRAIL / 22,6 | idem | +1,883 / TRAIL / 11,3 | ✓ |
| RG | MOVRUSDT | 2024-03-06 23:00 | 0,0071 | 7 | 22,999 | +2,755 / TRAIL / 21,4 | idem | +1,060 / TRAIL / 7,2 | ✓ |
| RG | SEIUSDT | 2024-03-07 02:00 | 0,0078 | 6 | 0,8245 | +3,259 / TRAIL / 5,1 | idem | +2,243 / TRAIL / 2,1 | ✓ |
| RG | CYBERUSDT | 2024-03-15 02:00 | 0,0069 | 6 | 11,331 | +4,754 / TRAIL / 1,4 | idem | +3,383 / TRAIL / 0,7 | ✓ |
| RG | STXUSDT | 2024-03-18 07:00 | 0,0061 | 2 | 2,7394 | +2,772 / TRAIL / 9,0 | idem | +3,716 / TRAIL / 8,9 | ✓ |
| RG | RSRUSDT | 2024-03-18 21:15 | 0,0061 | 3 | 0,005636 | +4,310 / TRAIL / 4,9 | idem | +5,239 / TRAIL / 4,6 | ✓ |
| RG | NEARUSDT | 2024-03-27 10:30 | 0,0071 | 2 | 7,769 | +5,803 / TRAIL / 11,7 | idem | +2,700 / TRAIL / 3,6 | ✓ |
| RG | 1000LUNCUSDT | 2024-03-29 02:00 | 0,0062 | 2 | 0,1571 | −1,171 / TIME / 72 | idem | +1,526 / TRAIL / 6,9 | ✓ |
| RG | FETUSDT | 2024-03-31 09:15 | 0,0051 | 1 | 3,1342 | +7,382 / TRAIL / 20,4 | idem | +2,039 / TRAIL / 15,0 | ✓ |

(pnl gross trước phí/funding; "hạng" của RG = hạng theo số ngẫu nhiên u.)
- Dữ liệu: 5 lệnh thiếu nến entry (SG 1, RG 4) bị bỏ; cov < 90 % nến trong cửa sổ: SG 0,21 %, SO 0,47 %, RG 0,29 %;
  funding phủ 100 % lệnh; DELIST-exit ≤ 0,04 %.

## 7. Giới hạn

- 1 selector, 1 seed; nhãn train từ `.pb` v1 (nhiễu nhãn với symbol ma, không leak). Selector train trên mọi tick, không
  riêng gate đóng — một model train riêng gate đóng CHƯA thử (không có trong pre-reg; không khuyến nghị vì RG đã ≈ SG).
- Cooldown theo lệnh, lệnh cùng coin có thể chồng; thống kê theo lệnh, không phải equity danh mục.
- RG có n gấp 6,3× SG (cooldown ít chặn) ⇒ phân bố thời gian khác nhẹ; chênh SG − RG đã resample chung block 72h.
- Slippage chỉ nằm trong phí 0,112 % RT; trailing fill tại mức (trừ gap-open) — lạc quan nhẹ cho ô có nhiều trail.
