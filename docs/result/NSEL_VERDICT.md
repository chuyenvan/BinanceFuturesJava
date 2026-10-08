# NSEL — VERDICT (MASTER, 2026-10-08)

Pre-reg: docs/prereg/PREREG_NSEL.md (9986c929). Scorer A: docs/result/NSEL_RESULT_A.md (122aac8d). Scorer B (độc lập, không import thước cũ): docs/result/NSEL_RESULT_B.md (42f9fbe0). J-D: docs/result/NSEL_JD_20261008.md (fa749e23).

## Khớp nối
- J-A 263 test PASS; J-B md5 trùng gqsf-a1/s7; J-C 0 lệnh đổi; J-D M0 trùng byte arm D (3 seed); J-E PASS 24/24 (CORE_ADD = counter, ≤1/cụm, 100% trong cụm leg0 THÊM, chân phạt = chân nến sập 100%, CONC max 8,43%).
- J-F đối chiếu A vs B — mọi số dùng trong luật GO trùng: Δn +1195/+848; ΔΣPnL −3919±8875 / +5648±7836; cận dưới −9864 / +400; ΔmaxDD −6,85 / −5,13; Calmar nền 1,212–1,213, M1 0,936–0,937, M2 1,095–1,096 (lệch ≤0,1%); ΔROI 2022 −10,35 / −7,32 và 2025 −9,71 / −4,82 trùng. Lệch duy nhất: ΔROI 2023 (A 25,26/30,48 vs B 25,58/30,64, ≤0,6%) do mốc ngày/múi giờ biên năm khác nhau (A: equity ngày + đỉnh DD reset 00:00 UTC; B: MTM phút +07). Không chạm ngưỡng nào (G5 chỉ cần dấu và mốc −8pp) ⇒ J-F PASS, ghi nhận.

## Verdict §6
- M1-S (2 tầng + CORE_ADD): NO-GO — G2 FAIL (mean −3,9k, LB −9,9k < −8k), G4 FAIL (Calmar 0,77× < 0,85×), G5 FAIL (2022 −10,35pp).
- M2-S (2 tầng + CORE_ADD + F1): GO — G1 +848 chân/năm; G2 +5,6k (LB +0,4k); G3 DD tệ nhất 28,9%, ΔDD −5,13pp; G4 0,903×; G5 2/4 năm ≥0, năm tệ nhất −7,32pp; G6 PASS.
- Chọn: M2-S (arm duy nhất GO).

## Cảnh báo bắt buộc kèm GO
- 8 seed đo nhiễu model/gate, KHÔNG đo nhiễu đường giá (mọi seed cùng 1 lịch sử thị trường). Bootstrap MTM block-10d ΔΣPnL M2: +5,6k, CI95 [−15,6k; +27,9k], P(≤0) 0,30 ⇒ GO là "không kém + thêm lệnh", không phải bằng chứng tăng lãi.
- maxDD xấu hơn nền ở 8/8 seed (−5,1pp); 2022 âm 8/8 seed; lợi dồn vào 2023 (+30pp); quý 2022Q1, 2022Q4, 2024Q2, 2025Q1 âm 8/8 seed.
- Phân rã ΔΣPnL M2: chân LÕI −26,3k, chân THÊM +26,7k, CORE_ADD +8,1k (~244 chân/năm), BIG_DOWN/DCA −2,9k.
- Phí gốc (penalty 0, seed 42/7): ΔΣPnL +19,9k/+20,9k, ΔCAGR22 +6,4pp ⇒ lợi phụ thuộc mạnh chi phí khớp nến sập.
- Giả thuyết sinh ra trên DEV (N_DEEP/P0) ⇒ thiên lệch chọn lọc còn đó.

## Bước tiếp (theo pre-reg: GO chỉ đủ điều kiện port live + shadow)
1. Port live NSEL M2: buffer THÊM thứ 2 + persist + seed; CORE_ADD live (resize STOP_MARKET, giữ priceSL/timeStart); F1 live; truyền rank ≥32; test parity.
2. Shadow paper riêng (K24 + skipFull + NSEL M2) so với shadow #2, tiêu chí pre-reg riêng trước khi start.
3. Holdout 2026 một lần cho cấu hình cuối (K24+skipFull và +NSEL M2), pre-reg trước khi mở.
