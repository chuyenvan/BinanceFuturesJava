# V4.2 OBJECTIVE (thuong tan-suat-lenh) — ĐÓNG HỒ SƠ 2026-07-17

## Là gì
`HPOFitnessCalculatorV4.finalFitness = calmar × freqFactor` (V4.2, TASK-3a).
- `freqFactor` ramp 0.5→1.0 khi tradeCount: san-min-trade → 2×san. Const: `FREQ_TARGET_MULT=2.0`,
  `FREQ_FLOOR=0.5`. Tat = `FREQ_TARGET_MULT<=0`.
- Muc dich: Calmar la ti so BAT BIEN so lenh → HPO chon genome it-lenh sat mep san → OOS regime khac
  thi tut < san → TOO_FEW. V4.2 thuong genome trade nhieu hon TRONG IS de chong TOO_FEW.
- Chi doi genome nao duoc chon; KHONG dung calmar/note/verdict (bat bien pre-register).

## Vì sao ARCHIVE (ket luan do, khong doan)
1. **A/B V4.1 vs V4.2 = y het 43.8% OOS-positive / WFE~1.0** → doi objective KHONG nhuc nhich kim.
2. **Co che chi bias IS genome-selection**, khong tao duoc co hoi ma OOS khong co. WFO V42_pipe: 8/16
   quy ZERO_TRADES/TOO_FEW, roi 2025Q4 no 1154 lenh — trades cuc ky khong deu. Rang buoc that =
   **opportunity frequency trong DATA/regime, khong phai ham muc tieu.**
3. Nhat quan nguyen tac da chot: binding constraint = opportunity frequency, KHONG phai sizing/objective.

## Thay bang gì (huong hien tai)
- Tan suat giai bang **horizon 12h (1152 keo/quy) + bo gate**, KHONG phai van objective.
- Huong full EV2 + SL-cung: **KHONG con HPO genome/fitness objective** (selector = threshold tren
  model prob) → V4.2 vo dung.
- V4.2 chi con y nghia NEU giu path market-gate-model HPO cu (hybrid). Nhung ngay ca khi giu,
  V4.2 KHONG sua duoc evenness → phai dung bien phap data-level (mo universe, ha nguong setup),
  khong van objective.

## Trang thai code
- Code V4.2 GIU NGUYEN trong `HPOFitnessCalculatorV4.java` (khong xoa — off duoc bang FREQ_TARGET_MULT<=0).
- KHONG dau tu them vao objective. Market-gate-model: da FAIL WFO (43.8% <70% ca DCA-on lan DCA-off,
  Track A 2026-07-17) → cho quyet dinh song/chet path nay khi chot kien truc cuoi (EV2-only vs hybrid).

## Con tro
- Chi tiet DCA ablation: docs/insights/ (commit 5a7fc12). Chon-n + exit: docs/insights/sl4h_label_experiment.md.
- Fitness goc: HPOFitnessCalculatorV4.java. Sensitivity gene: docs/archive/insights/SENSITIVITY_TASK111.md.
