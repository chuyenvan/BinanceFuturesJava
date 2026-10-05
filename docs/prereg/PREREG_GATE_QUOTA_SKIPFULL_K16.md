# PREREG_GATE_QUOTA_SKIPFULL_K16 — bổ sung @K16 (khung live/242)

Ngày 2026-10-05 (GMT+7). Chốt TRƯỚC khi đẩy kernel. Gốc: `PREREG_GATE_QUOTA_SKIPFULL.md` (19072857, 5fcfcc92); kết quả K24 f089f37d. Không đổi code/key/thiết kế; không tune.

## Cấu hình
- Profile `r4_kg0_k16_f015_g155` + B0OV (= `profiles/g2_flat3.properties`, TOPK 16), bundle `sim-x1-2021-bundle` (bins S1 deploy), jar `sim-jar-gqsf` sha256 0944841ca1b3…, kernel `tools/kaggle_sim.py` HEAD (8b60b00a) + khối pred_ds cho seed 21/7.
- ON = + `GATE_QUOTA_SKIP_WHEN_FULL=true`: `gqsf16-a1` (seed 42, pred.bin gốc 5dd6bb4c), `gqsf16-s21` (gate-sb-s21 0b541d22), `gqsf16-s7` (gate-abl-seed7 b737fb6d).
- OFF = cùng jar MỚI, key vắng: seed 42 = `gqsf-p0` (ff3ce513, có sẵn); thêm `gqsf16off-s21`, `gqsf16off-s7`. Tổng 5 kernel mới, ≤ 2 song song. (OFF dùng jar mới vì P0 đã chứng minh OFF ≡ jar cũ; cặp chỉ khác key.)
- Parity: jar sha; `SELECTOR_RANK_TOPK=16`; B0OV; ON có key=true + log `[GATE-QUOTA] SKIP_WHEN_FULL=ON` + skipFull; OFF không có key; pred md5; result.ok. Sai ⇒ VOID.

## Số đo + luật (giống vòng K24, áp cho 3 cặp — CHỈ BÁO CÁO, không là cổng)
- Ghép cặp ON−OFF theo seed: CAGR22, maxDD (2022+ và toàn kỳ), Calmar22, UW22, n/năm, phút vào 2022, skipFull; bootstrap ngày MTM khối 10 ngày từng cặp (inflate √(2 ln 3) = 1,482).
- C1 mean ΔCAGR22 > 0 và CI 95% paired t **df 2 (t = 4,303)** không chứa 0 — **sức mạnh rất yếu (n = 3)**; C2 sd CAGR22 ON < sd OFF (3 seed @K16, tính từ run OFF); C3 mọi seed |maxDD| ≤ 40%; C4 mean Calmar22 ON ≥ 0,9 × mean OFF@K16; C5 mean ΔCAGR23 ≥ −1,0 pp.
- Kỳ vọng khai trước: seed 42 Δ CAGR22 ≈ 0 (±0,5 pp); seed 21 và 7 Δ +3…+6 pp.
- Đầu ra: mục "Bổ sung K16" trong `docs/result/RESULT_GATE_QUOTA_SKIPFULL.md` + khóa `k16` trong `docs/result/gate_skipfull.json`; driver `gate_skipfull_driver.py --k16`.
