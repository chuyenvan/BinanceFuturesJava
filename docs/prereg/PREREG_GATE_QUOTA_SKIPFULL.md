# PREREG_GATE_QUOTA_SKIPFULL — quota gate G2 bỏ qua khi sổ đầy (Pha E chương trình GATE)

Ngày 2026-10-04 (GMT+7). Chốt TRƯỚC mọi số của vòng này (cổng offline, code, sim). MASTER chốt thiết kế; agent không đổi sau khi thấy số.
Bối cảnh: `docs/audit/GATE_QUOTA_DIAG_20261004.md` (15d3e2d5) — seed xấu (S21/S7/S123/S13/S2024) tiêu 115–255 lượt gate PASS trong 11–31/05/2022 khi `TradeUtils.managerBudget` trả null (U ≥ U_MAX); giả thuyết (CHƯA đo): r cực trị tháng 5 nạp vào buffer 90d nâng q_t ⇒ đói T6–T9.
Ràng buộc: 0 Java sim trên Oracle (chỉ `mvn -o test` + build), 0 chạm 242/shadow_c3, 0 merge, DEV ≤ 2025-12-31 (2026 niêm phong), Kaggle ≤ 2 kernel song song, df < 500 MB ⇒ dừng.

## 1. Cơ chế (thiết kế CỐ ĐỊNH)
- Branch `feat/gate-quota-skipfull` từ `origin/module` HEAD (15d3e2d5). Key `GATE_QUOTA_SKIP_WHEN_FULL` (đọc qua `Cfg` trong `Configs`, mặc định **false**).
- Khi true, tại mỗi ứng viên PREDICT_SYMBOL_TRADE (symbol-phút, `sp != null`) đi tới gate: nếu sổ KHÔNG thể mở lệnh mới — điều kiện = `TradeUtils.managerBudget(...)` trả **null** (U = marginRunning/equity ≥ U_MAX hoặc equity ≤ 0), gọi CHÍNH hàm đó với CÙNG nguồn marginRunning/equity mà đường mở lệnh dùng ngay sau gate (không chép công thức) — thì:
  (i) KHÔNG gọi `GateRollingRatio.threshold` / `LiveGateRollingRatio.threshold` ⇒ r KHÔNG nạp vào `GateRatioBuffer`;
  (ii) quyết định = REJECT (lý do "BOOK FULL"), KHÔNG `notePass` (không tính pass, không log pass). `noteCandidate` (seen) giữ nguyên.
  Mọi thứ khác y nguyên: BIG_DOWN/DCA_LEVEL1 không đổi; q_t vẫn tính ở truy vấn đầu mỗi giờ (causal, giờ chỉ có ứng viên bị bỏ thì q được tính ở truy vấn kế tiếp — cùng mốc h, cùng tập r có ts < h).
- Hệ quả lệnh: tại chính phút đó lệnh vốn đã bị chặn bởi `managerBudget` null (các bước giữa gate và budget cho PREDICT: PumpDumpFilter OFF, GATE_COUNT_ONLY OFF, tier chỉ DCA) ⇒ ON chỉ đổi lệnh qua q_t về sau.
- Sim và live đi qua CÙNG `AIRejectFilter.entryGate` (overload thêm `bookFull`) + `GateRatioBuffer`. Live chỉ đọc key; default live không đổi.

## 2. Điểm sửa dự kiến (file:line ở 15d3e2d5)
| file | dòng | sửa |
|---|---|---|
| `tradecore/Configs.java` | 156 (+ đọc ở ~903 cạnh `SIM_U_MAX`) | field `GATE_QUOTA_SKIP_WHEN_FULL=false`; `Cfg.get("GATE_QUOTA_SKIP_WHEN_FULL")` → `Boolean.parseBoolean` |
| `ai_ml/onnx/entry/AIRejectFilter.java` | 61–90 | overload `entryGate(pred, sp, predictSymbolTrade, bookFull)`; bản 3 tham số gọi với `false` |
| `ai_ml/onnx/entry/GateRollingRatio.java` | 48–153 | đếm `skipFull` (chỉ in trong `stats()` khi key bật), log khởi động key; accessor test |
| `research/SimulatorMarketLevelTicker1MStopLoss.java` | 1330 (+1388–1399) | key bật & PREDICT ⇒ `bookFull = managerBudget(null, marginRunning, equity-sizing, level) == null`; tách 2 helper nguồn marginRunning/equity dùng chung với chỗ sizing 1388–1396 |
| `trading/DetectEntrySignal2TradeNormal.java` | 940 (+975–996) | key bật & PREDICT ⇒ cùng kiểm tra trên nguồn live (BudgetManager; ShadowBookC3 khi `LiveProfileC3.on()`) |
| `src/test/.../GateQuotaSkipFullTest.java` | mới | ON/OFF: buffer không tăng + không pass khi ON&full; OFF&full = hành vi 3 tham số; ON&!full = OFF; ngưỡng U_MAX |
Kiểm: `mvn -o test` 0 fail; `bash tools/check_cfg_gateway.sh` OK; jar sha256 ghi vào RESULT + upload dataset Kaggle riêng `sim-jar-gqsf` (kèm `prof_r4_kg0_k16_f015_g155.properties` md5 0e0caef0).

## 3. Cổng byte-identical OFF (trước khi chạy ON)
- Class diff `target/classes` (build HEAD 15d3e2d5 vs build branch): chỉ được khác các class ở §2 (+ inner class do LineNumberTable) + class test; mọi class khác byte-identical.
- Kaggle P0 = B0@K16 OFF: profile `r4_kg0_k16_f015_g155` + B0OV (= `profiles/g2_flat3.properties`), bundle `sim-x1-2021-bundle`, bins deploy (bundle), jar MỚI, kernel `tools/kaggle_sim.py` HEAD (md5 8b60b00a, NOWRITE242), recipe `research/analysis/selector_ablation_b0ref.py`. PASS ⇔ md5 printDone bắt đầu `ff3ce513` (n 2517, eq 131 908). FAIL ⇒ DỪNG, không chạy ON.
- sha256 jar ghi bằng commit pre-reg bổ sung (amendment chỉ chứa sha/dataset) TRƯỚC khi đẩy kernel P0.

## 4. Cổng offline TRƯỚC sim (`research/analysis/gate_offline.py`, thêm tuỳ chọn skip-when-full)
- U xấp xỉ từ run OFF của chính seed: `U(t) = Σ margin(printDone, mọi level, s ≤ t < e) / E(t)`, `E(t)` = b+unP của dòng `BudgetManagerSimple: Update yyyymmdd hh:mm` gần nhất ≤ t trong `logs/sim.out` của run OFF; `full(t) ⇔ U(t) ≥ 0,60` (U_MAX mặc định, profile không override). Xấp xỉ khai: margin printDone = margin lúc đóng (gồm leg DCA ⇒ thổi U trước leg), E ngày, sổ lệnh = sổ OFF (không phản hồi bậc 2).
- ON offline: bỏ khỏi buffer r của mọi ô hợp lệ tại phút full; pass_ON = hợp lệ ∧ qua ngưỡng ∧ ¬full.
- Số đo (S21, S7 là cổng; 6 seed còn lại mô tả): (a) số pass symbol-phút 01/06–30/09/2022 (GMT+7) ON vs OFF; (b) q_h trung bình trên các giờ có truy vấn (ngoài warm-up) trong cùng cửa sổ ON vs OFF. Mô tả: pass tháng 5/2022; tỉ lệ pass-lãng-phí OFF (pass không vào lệnh, D2) bị gắn full; tỉ lệ lệnh vào thật OFF bị gắn full (kỳ vọng ≈ 0).
- Kỳ vọng khai trước: q_h T6–T9 ON < OFF ở cả S21 và S7; pass T6–T9 ON/OFF ≥ 1,30. Nếu offline KHÔNG thấy q giảm ⇒ giả thuyết cơ chế sai ⇒ VẪN sim, ghi rõ trong RESULT. Cổng offline không chặn sim (chỉ ghi).

## 5. Sim (Kaggle)
- 8 seed × ON @K24 = profile `r4_kg0_k16_f015_g155` + B0OV + `SELECTOR_RANK_TOPK=24` + `GATE_QUOTA_SKIP_WHEN_FULL=true`; jar `sim-jar-gqsf`; kernel `tools/kaggle_sim.py` HEAD + khối pred_ds (`gate_ablation_driver.template`) cho 7 seed có pred riêng (S7 `gate-abl-seed7` b737fb6d; S13/S21/S99/S123/S777/S2024 `gate-sb-*`, md5 trong `~/claude_master/1004/gsb/pred_*/meta.json`); A1 (seed 42) = pred.bin gốc trong bundle (đường `ks.submit` như `n700-a1`). Tag `gqsf-<seed>`.
- OFF ghép cặp = run đã có (jar 7368be46): `n700-a1`, `gabl-seed7`, `gsb-s13`, `gsb-s21`, `gsb-s99`, `gsb-s123`, `gsb-s777`, `gsb-s2024` (dải K24 OFF CAGR22 34,18 ± 3,58). Hợp lệ so cặp vì P0 chứng minh jar mới OFF ≡ jar cũ (§3).
- Parity từng run ON (sai ⇒ VOID, không chấm): jar sha256 = sha jar mới; `SELECTOR_RANK_TOPK=24`; `GATE_QUOTA_SKIP_WHEN_FULL=true` + B0OV trong prof_run; pred md5 used = md5 khai; log `[GATE-QUOTA] SKIP_WHEN_FULL=ON` có mặt; result.ok.
- Chạy: P0 trước (1 kernel) → nếu PASS, 8 ON tối đa 2 song song.

## 6. Số đo + luật GO (CỐ ĐỊNH)
Thước (dùng lại `reset_rule_score` / `n700_driver.arm_metrics` / `selector_ablation_driver.daily_boot`, không viết lại):
- CAGR22 = CAGR trên equity NGÀY MTM (b+unP) cửa sổ 2022-01-01..2025-12-30, rebase 2021-12-31; maxDD22/UW22 = MTM phút trong cửa sổ (`run_mtm`, cost legacy); Calmar22 = CAGR22/|maxDD22|; maxDD toàn kỳ = MTM phút 2021-07..2025-12; n/năm = lệnh đóng 2022–2025 / 4; phút vào PREDICT theo năm.
- Ex-2022: CAGR23 = CAGR equity ngày từ 2022-12-31 đến 2025-12-30; lợi suất theo năm từ equity ngày.
- Từng cặp seed (ON−OFF): bootstrap khối 10 ngày ghép cặp trên lợi suất ngày MTM (2000 rep, seed 20260905), ΔCAGR/ΔmaxDD/ΔCalmar, CI raw + inflate √(2 ln 8) = 2,039 (8 cặp nhìn cùng lúc). Thước cùng tập lệnh không áp (ON đổi tập lệnh).
- Luật GO (cả 5):
  - **C1** mean(ΔCAGR22, 8 cặp) > 0 VÀ CI 95% paired t (df 7, t = 2,365) không chứa 0.
  - **C2** sd(CAGR22 ON, 8 seed) < 3,58 (sd OFF).
  - **C3** mọi seed ON: |maxDD MTM| ≤ 40% (toàn kỳ và 2022+).
  - **C4** mean(Calmar22 ON) ≥ 0,9 × mean(Calmar22 OFF) = 0,9 × 1,529 = 1,376.
  - **C5** mean(ΔCAGR23) ≥ −1,0 pp.
- Báo thêm: seed xấu S21/S7/S123 Δ bao nhiêu; seed tốt S777/S99/A1 Δ bao nhiêu; Δn/năm; Δ phút vào 2022; skipFull (số lượt) từ log.
- Kỳ vọng khai trước: mean ΔCAGR22 +2…+4 pp; sd CAGR22 giảm ~30% (≈ 2,5); seed tốt |Δ| ≤ 1 pp.
- KHÔNG thêm biến thể (không thử ngưỡng U khác, không thử buffer khác, không đổi pct/K/W). GO chỉ là đề xuất cho MASTER; không merge, không deploy.

## 7. Rủi ro khai trước
- n = 8 seed, 1 sự kiện (05/2022) chi phối; GO dựa paired t 8 cặp ⇒ sức mạnh thấp.
- Live: sổ 242 có 48–62 vị thế legacy ⇒ U live có thể sát/vượt trần lâu ⇒ khi bật, buffer live có thể ngừng nạp dài hạn (q_t đứng yên/cũ) — phải đo U live trước khi xét bật; vòng này KHÔNG bật live.
- Offline dùng sổ OFF làm xấp xỉ U ⇒ chỉ chỉ báo hướng.

## 8. Đầu ra
`docs/result/RESULT_GATE_QUOTA_SKIPFULL.md` + `docs/result/gate_skipfull.json`; driver `research/analysis/gate_skipfull_driver.py`; offline `docs/audit/gate_skipfull_offline.json`. Code trên branch `feat/gate-quota-skipfull` (push branch, KHÔNG merge).
