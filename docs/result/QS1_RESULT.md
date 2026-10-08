# QS1_RESULT — quiet sleeve dạng GIỎ (đánh giá OFFLINE, DEV 2022–25)

Pre-reg `docs/prereg/PREREG_QS1.md` (3b69309e, commit TRƯỚC khi đo). Script `research/analysis/qsleeve_q1.py`; JSON `docs/result/QS1_RESULT.json`. 1 cấu hình, không tune; 0 sim/Kaggle/Java, 0 chạm 242/shadow, không mở nsel-*.

**Verdict DEV: NO-GO** — L1 FAIL · L2 PASS · L3 PASS · L4 FAIL

## Kết luận
- **NO-GO DEV (L1 FAIL sát, L4 FAIL cả 2 vế) ⇒ không mở holdout 2026, dừng.** Không đổi gì sau khi thấy số.
- **L2 mạnh:** giỏ ở phút kích hoạt R ≥ Q: ROI stress +1,03%/giỏ; giỏ ở phút yên ngẫu nhiên (cùng luật, cùng số giỏ/tháng)
  −0,94% [p5 −1,32; p95 −0,55] ⇒ p = 0,000 (8/8 seed p ≤ 0,005). Khớp QS0 T4b: giá trị nằm ở **thời điểm**, không ở "vào lúc yên".
- **L1 trượt sát:** ROI stress dương 8/8 seed, 4/4 năm, nhưng cận dưới bootstrap cụm ngày −0,09% (CI [−0,09; 2,13]). 41% chân
  có nến quyết định sập ⇒ stress ăn 0,68pp/giỏ. MAE p10 chân −31%, giỏ −23%; giữ p50 168h (giỏ mở tới chân cuối thoát). 2025 yếu nhất (0,40%).
- **L4 trượt:** tương quan return ngày sleeve vs nền 0,57 [0,54..0,60] > 0,5; Calmar ghép stress 2,062 < nền 2,151 (8/8 seed thấp hơn).
  Sleeve vào ĐẦU nhịp giảm nhỏ, giữ tới 168h, chồng lên đợt vào của nền: ngày có vị thế sleeve 36%, nền 40%, hợp chỉ 46%.
  Sleeve một mình (vốn sleeve, không lãi kép) +7,7%/năm, maxDD 12% — không bù được 10% vốn rút khỏi nền (CAGR nền ~31–37%).
- **Lệch kỳ vọng MASTER:** 37 giỏ/năm/seed (kích hoạt 22→51/năm 2022→2025) thay vì 80–130: Q là phân vị của R (max/phút)
  trên phút yên, cộng hồi chiêu 6h. Ghi nhận, không sửa.
- Diễn giải các chỗ pre-reg không nói rõ (E1–E10: hồi chiêu tính cả kích hoạt bị bỏ, "≥30 ngày" = ≥ 43 200 phút yên trong cửa sổ,
  pool đối chứng 1700 phút/tháng, nền stress post-hoc kiểu gkf_rescore…) chốt trong docstring, commit `cf15d7b9` TRƯỚC khi chạy.

## Tự kiểm
- Proxy tái lập QS0 K24/0,9995 (không giỏ): ROI net 1,514% vs QS0 1,514% (Δ -0,000 pp, ngưỡng ±0,05) → **PASS**; trùng từng lệnh 100,00%, cùng lý do thoát 100,00%, n 3787.
- Phút yên mới vs QS0 (tuổi leg0 ≥ 24h), phút DEV, TB 8 seed: Jaccard 0,928 [0,923..0,933]; yên-mới ⊂ QS0 0,928; QS0 ⊂ yên-mới 1,000; đồng ý 0,930; tỉ lệ yên mới 0,972 vs QS0 0,902.
- Không lookahead: assert pass < t (mọi phút); Q(ngày u) tính lại brute-force chỉ từ phút < u·D ≤ t trùng tuyệt đối 320 ngày kích hoạt (8 seed). Bất biến giỏ (6h, coin 24h, ≤5 mở, vol, coin khác nhau): PASS.
- Đường đi: 1966795 chân vũ trụ (phút kích hoạt ∪ pool đối chứng × top-24), nobar 18, cut 3874, ngày ticker thiếu 0, symbol lạ 0.
- Nền stress post-hoc: chân nền khớp entry = close nến quyết định 1,0000 [1,0000..1,0000]; đối chứng thiếu giỏ TB 1,7/1000 lần.

## T1. Theo năm (gộp 8 seed; tỉ lệ = /năm/seed)
| năm | kích hoạt | giỏ | chân | ROI net % | ROI stress % | win net % | win stress % | MAE p10 chân | MAE p10 giỏ | % giỏ <5 chân | giữ p50 h | % chân sập |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022 | 22,2 | 22,0 | 108,1 | 1,39 | 0,75 | 74,4 | 73,3 | -39,6 | -34,7 | 4,5 | 112 | 39,2 |
| 2023 | 35,4 | 35,4 | 173,1 | 2,23 | 1,35 | 78,8 | 71,4 | -21,9 | -17,6 | 3,5 | 168 | 54,2 |
| 2024 | 46,2 | 45,9 | 229,4 | 2,28 | 1,55 | 70,0 | 64,9 | -27,7 | -22,0 | 0,0 | 168 | 43,5 |
| 2025 | 50,8 | 46,5 | 223,5 | 0,90 | 0,40 | 65,1 | 63,4 | -34,6 | -22,6 | 7,5 | 145 | 29,4 |
| 2022–25 | — | 37,4 | 183,5 | 1,71 | 1,03 | 71,2 | 67,2 | -30,6 | -23,1 | 3,8 | 168 | 41,1 |

Bootstrap cụm ngày 95% (gộp, 2000 lần): ROI stress [-0,09; 2,13], ROI net [0,53; 2,78]. Giỏ bị bỏ do trần 5: 1,2/năm/seed.

## T2. Theo seed (DEV 2022–25)
| seed | kích hoạt | giỏ mở | bỏ trần | rỗng | giỏ/năm | ROI net % | ROI stress % | win % | p đối chứng (seed) | Calmar nền S | Calmar ghép S | corr S |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | 151 | 146 | 5 | 0 | 36,5 | 1,66 | 0,95 | 71,2 | 0,001 | 2,038 | 1,952 | 0,560 |
| S7 | 153 | 149 | 4 | 0 | 37,2 | 1,68 | 1,00 | 71,1 | 0,000 | 1,922 | 1,840 | 0,568 |
| S13 | 158 | 152 | 5 | 1 | 38,0 | 1,85 | 1,16 | 71,7 | 0,001 | 1,985 | 1,912 | 0,599 |
| S21 | 157 | 152 | 5 | 0 | 38,0 | 1,78 | 1,09 | 70,4 | 0,000 | 1,702 | 1,647 | 0,589 |
| S99 | 152 | 146 | 6 | 0 | 36,5 | 1,65 | 0,94 | 72,6 | 0,003 | 2,403 | 2,269 | 0,564 |
| S123 | 155 | 150 | 5 | 0 | 37,5 | 1,44 | 0,78 | 68,0 | 0,005 | 1,914 | 1,820 | 0,562 |
| S777 | 155 | 151 | 4 | 0 | 37,8 | 1,94 | 1,30 | 75,5 | 0,000 | 3,347 | 3,236 | 0,538 |
| S2024 | 156 | 152 | 4 | 0 | 38,0 | 1,67 | 0,98 | 69,1 | 0,002 | 1,896 | 1,818 | 0,585 |

## T3. Đối chứng phút yên ngẫu nhiên (1000 lần, pool 81600 phút, cùng giỏ/tháng/seed)
- Sleeve gộp: ROI stress 1,03%, net 1,71%. Đối chứng gộp: stress TB -0,94% [p5 -1,32; p95 -0,55], net TB -0,89% [p95 -0,50].
- **p một phía (stress) = 0,000**; p (net) = 0,000. Giỏ/lần TB 1196 (sleeve 1198).

## T4. Danh mục ghép 0,9 nền + 0,1 sleeve vs nền 1,0× (MTM ngày 2022–25; TB 8 seed [min..max])
| danh mục | CAGR22 % | maxDD22 % | Calmar22 ngày |
|---|---|---|---|
| nền 1,0× (phí gốc) | 36,95 [35,58..39,31] | 14,49 [9,24..17,32] | 2,650 [2,069..4,255] |
| nền 1,0× stress | 31,41 [29,85..33,56] | 15,10 [10,03..17,91] | 2,151 [1,702..3,347] |
| ghép (phí gốc) | 34,42 [32,95..36,76] | 13,87 [8,88..16,49] | 2,575 [2,033..4,138] |
| ghép stress | 28,86 [27,25..31,04] | 14,47 [9,59..17,07] | 2,062 [1,647..3,236] |

- Tương quan return ngày sleeve vs nền: stress 0,570 [0,538..0,599], phí gốc 0,560 [0,525..0,591]. Sleeve (vốn sleeve, không lãi kép): stress 7,70 [5,86..9,85]%/năm, maxDD 12,24 [9,09..15,55]%. % ngày có vị thế: sleeve 36,4 [35,0..37,9], nền 40,4 [39,1..42,2], hợp 45,7 [43,9..47,0].

Theo năm (stress, TB 8 seed):
| năm | nền 1,0× stress % | ghép stress % | sleeve stress % vốn sleeve |
|---|---|---|---|
| 2022 | 4,05 [-0,49..17,53] | 3,92 [-0,15..16,52] | 3,29 [-0,67..7,82] |
| 2023 | 57,32 [50,97..61,98] | 51,87 [46,25..55,70] | 9,54 [8,12..10,87] |
| 2024 | 40,68 [35,07..45,42] | 37,88 [32,77..41,98] | 14,24 [12,38..15,87] |
| 2025 | 29,75 [23,30..32,84] | 26,90 [21,88..29,07] | 3,73 [-0,52..9,19] |

## Luật GO DEV (pre-reg)

| luật | điều kiện | số | kết quả |
|---|---|---|---|
| L1 | ROI stress gộp > 0 & cận dưới bootstrap > 0 & ≥ 6/8 seed > 0 | 1,03%; [-0,09; 2,13]; 8/8 | FAIL |
| L2 | p đối chứng (gộp) < 0,05 | 0,000 | PASS |
| L3 | ≥ 3/4 năm ROI stress > 0 | 4/4 | PASS |
| L4 | Calmar ghép S ≥ Calmar nền S & corr S ≤ 0,5 | 2,062 vs 2,151; 0,570 | FAIL |

**DEV NO-GO → không mở holdout 2026, dừng (theo pre-reg).**
