# PREREG_RANK_MARGIN_INV — size leg SELECTOR TĂNG dần theo rank k (đảo ngược, trên C2 = K24 + skipFull)

Ngày 2026-10-05 (GMT+7). Chốt TRƯỚC mọi số. Bổ sung cho `docs/prereg/PREREG_RANK_MARGIN.md` (8b6c902d) sau khi owner phản biện hướng tư duy.
Bối cảnh: vòng 1 (cắt rank thấp, `m(k)=1−α(k−1)/(K−1)`) cho **NO-GO** — Calmar22 phẳng (1,662→1,649). Owner giả thuyết: **rank cao (rank 1) = win-prob cao NHƯNG coin biến động mạnh ⇒ rủi ro cao; rank thấp (rank 24) = tín hiệu yếu nhưng ít biến động ⇒ rủi ro thấp** ⇒ lẽ ra phải **THÊM margin vào rank thấp**, không cắt. Vòng này test đúng giả thuyết đó: **đảo dấu**.
Ràng buộc: 0 Java sim trên Oracle (chỉ `mvn -o test` + build), 0 chạm 242/shadow_c3, 0 merge, DEV ≤ 2025-12-30, Kaggle ≤ 2 song song.

## 1. Cơ chế (thiết kế CỐ ĐỊNH)
- Dùng LẠI key `SIM_RANK_MARGIN_ALPHA`, cho phép **alpha âm**. Công thức giữ nguyên `m(k) = 1 − α·(k−1)/(K−1)` ⇒ alpha = **−a** (a>0) ⇔ `m(k) = 1 + a·(k−1)/(K−1)` (THÊM margin vào rank thấp).
- alpha = 0 ⇒ byte-identical C2 (parity). alpha > 0 = hướng cũ (đã đo, NO-GO).
- Thay đổi code duy nhất so với 8b6c902d: gate `if (RANK_MARGIN_ALPHA > 0f …)` → `if (RANK_MARGIN_ALPHA != 0f …)`. Clamp `_rm < 0` giữ nguyên (alpha âm ⇒ _rm ≥ 1, clamp không kích hoạt). **Không** cap trần _rm (đây là điều cần đo: thêm bao nhiêu thì maxDD nở bao nhiêu).
- `m(k)` tại rank 24 = 1+a ⇒ a=0.3/0.5/0.7 → rank 24 = 1.3/1.5/1.7 lần size cũ. Tổng vốn triển khai TĂNG (đây là "thêm", không phải rebalance).

## 2. Điểm sửa dự kiến
| file | chỗ | sửa |
|---|---|---|
| `research/SimulatorMarketLevelTicker1MStopLoss.java` | ~:1430 | `> 0f` → `!= 0f` |

Kiểm: `mvn -o test` 0 fail; `bash tools/check_cfg_gateway.sh` OK; jar sha256 ghi vào RESULT + dataset Kaggle riêng `sim-jar-rm2`.

## 3. Cổng byte-identical OFF (P0)
- Class diff build HEAD `8b6c902d` (branch feat/rank-margin) vs build mới: chỉ khác `SimulatorMarketLevelTicker1MStopLoss.class` (1 class). `Configs` không đổi.
- Kaggle P0 = C2 alpha=0: md5 printDone phải bắt đầu **`ad26fd55`** (byte-identical gqsf-a1). FAIL ⇒ DỪNG.

## 4. Sim (Kaggle) — seed A1
- 3 arm a ∈ {0.3, 0.5, 0.7} → `SIM_RANK_MARGIN_ALPHA = -0.3 / -0.5 / -0.7`, nền C2 (K24 + skipFull), jar `sim-jar-rm2`, tag `rm-inv-030/050/070`.
- Parity từng arm: jar sha256, topk=24, skipfull=true, alpha = `-a` trong prof_run, b0ov, pred md5 verified, result.ok.

## 5. Số đo + luật GO (CỐ ĐỊNH, seed A1)
Đối chứng = baseline `gqsf-a1` (C2, alpha=0): CAGR22 36,90 · maxDD22 −22,21 · Calmar22 1,662 · n/năm 736.
Luật GO (đề xuất MASTER, KHÔNG tự merge/deploy):
- **C1** Calmar22 > 1,662 (cải thiện so baseline) — đây là tiêu chí CHÍNH cho giả thuyết "thêm rank thấp = thêm vốn ít rủi ro".
- **C2** maxDD22 không sâu quá −25% (đỏi vốn thêm vẫn trong khung rủi ro chấp nhận).
- **C3** n/năm ≥ 736 (không giảm lệnh).
- Báo thêm: CAGR22, ΣPnL 2022–25, ROI năm 2022 (kỳ vọng tăng vì thêm vốn), UW22.
- Kỳ vọng khai trước: nếu giả thuyết owner đúng ⇒ Calmar22 tăng > 1,662, maxDD không nở tương ứng; nếu rank trung tính ⇒ Calmar phẳng, chỉ CAGR/ΣPnL/equity tăng (thuần "thêm vốn").

## 6. Rủi ro khai trước
- 1 seed (A1). Thêm vốn không rebalance ⇒ ΣPnL/equity chắc chắn tăng, KHÔNG dùng làm bằng chứng — chỉ Calmar/maxDD có ý nghĩa.
- alpha âm không cap trần: rank 24 tới 1.7× có thể đẩy U lên gần U_MAX sớm hơn ⇒ throttle gián tiếp giảm size toàn sổ — ghi nhận, không đổi thiết kế sau khi thấy số.

## 7. Đầu ra
`docs/result/RESULT_RANK_MARGIN_INV.md` + `docs/result/rank_margin_inv.json`; driver `research/analysis/rank_margin_inv_driver.py`.
