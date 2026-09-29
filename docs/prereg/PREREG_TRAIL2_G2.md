# PRE-REG — Trailing vòng 2 trên G2: TÁCH hai thành phần đối lập, chọn 1 luật đơn (owner 09-29)
Chốt TRƯỚC khi xem số. Baseline = G2 (arm 7%). Jar tái dùng `sim-jar-gdv2` (7368be46…) — chỉ đổi KEY, KHÔNG build, KHÔNG đổi gate/entry.

## Vấn đề (owner nêu, MASTER xác nhận từ code TradeUtils.trailFromCap)
gap = min(maxProfit × TS_GIVEBACK_RATIO(0.5), cap), cap = 3% (pNoPump>0.29) / 8% (ngược lại); SL = maxProfit − gap; làm tròn 0.5%.
⇒ Trộn 2 cơ chế ĐỐI LẬP: (A) TỈ LỆ 50% (gần arm: khoá tuyệt đối chặt, nhưng trả lại NỬA lãi) và (B) TRẦN PHẲNG 3–8%
(xa arm: trả lại một cục cố định). Crossover ở maxProfit = 2×cap = 6% (weak) / 16% (strong). Thêm tầng phức tạp weak/strong theo pNoPump.
Mục tiêu owner: test mỗi cơ chế PURE, bỏ min()+weak/strong, CHỌN 1 luật đơn (chống overfit, dễ kiểm soát).

## Tính chất sạch của test: arm=7% + entry cố định ⇒ 355 lệnh chết-trước-arm GIỐNG HỆT mọi arm (trailing không áp).
Chỉ khác ở 2154 lệnh đã arm ⇒ cô lập đúng tác động hình dạng trailing, nhiễu thấp.

## Arm (5 cấu hình; k=4; inflate = 1.665). Nền G2, arm 0.07, bỏ weak/strong bằng SIM_TS_MAX_GAP = SIM_TS_MAX_GAP_WEAK.
| arm | TS_GIVEBACK_RATIO | SIM_TS_MAX_GAP | SIM_TS_MAX_GAP_WEAK | nghĩa |
|---|---|---|---|---|
| **T0** (=G2, parity) | 0.5 | 0.08 | 0.03 | combined hiện tại; md5 BẮT BUỘC 853aaa086be7d2d811162879df0653f6, n2509, eq131374 |
| **PROP50** | 0.5 | 1.0 | 1.0 | PURE tỉ lệ: gap = 0.5×maxProfit (không trần, không weak/strong) — nới đuôi, trả nửa lãi |
| **PROP30** | 0.3 | 1.0 | 1.0 | PURE tỉ lệ chặt hơn: gap = 0.3×maxProfit |
| **FLAT3** | 1.0 | 0.03 | 0.03 | PURE phẳng 3%: gap = min(maxProfit, 3%) = 3% khi lãi>3% — khoá sát đỉnh |
| **FLAT5** | 1.0 | 0.05 | 0.05 | PURE phẳng 5%: gap = 5% khi lãi>5% |

(Ghi chú tái lập: caps=1.0 khiến min() không bao giờ chạm ⇒ pure proportional; RATIO=1.0 + cap=g khiến min()=g khi lãi>g ⇒ pure flat, SL≥entry.)

## Luật kết luận — đây là bài toán ĐƠN GIẢN HOÁ, KHÔNG phải "thắng G2"
1. Cổng: T0 md5 = 853aaa08… (byte-identical G2). |n − 2509| > 5% ⇒ ghi rõ.
2. T1 rủi ro tuyệt đối §9 mỗi arm (maxDD MTM ≤40%/năm, UW ≤250, quý xấu ≥−20%, 0 năm âm, conc ≤15%). FAIL ⇒ loại.
3. Non-inferiority: bootstrap CI95 ΔCalmar_MTM vs G2 (paired block-72h + episode-cluster sensitivity, NREP 2000, seed 20260905, inflate 1.665).
   - Nếu CI của một pure form KHÔNG chứa 0 & dương ⇒ nó THẮNG (hiếm, tường power).
   - Nếu mọi CI chứa 0 ⇒ các pure form KHÔNG tệ hơn G2 có ý nghĩa ⇒ ĐỀ XUẤT lấy luật ĐƠN GIẢN NHẤT không kém điểm G2
     (bỏ min()+weak/strong). Ưu tiên: point Calmar cao nhất trong nhóm pure; hoà thì chọn FLAT (1 tham số, dễ hiểu nhất).
4. Báo mô tả mọi arm: phân phối 2154 lệnh armed (med/p25/p75/p95/max), % lãi giữ lại so đỉnh, Calmar_MTM/CAGR/maxDD phút/UW/quý xấu;
   bảng quý+năm (qstat_r4.py) cho T0 + arm pure tốt nhất. So riêng đuôi phải (p95/max) giữa PROP vs FLAT — cơ chế nào giữ runner tốt hơn.
5. Không tune sau khi thấy số (đổi = amendment commit trước). Không đụng 242/shadow/holdout 2026. DEV ≤ 2025-12-31.
