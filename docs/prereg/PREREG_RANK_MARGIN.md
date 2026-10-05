# PREREG_RANK_MARGIN — size leg SELECTOR giảm dần theo rank k (trên nền C2 = K24 + skipFull)

Ngày 2026-10-05 (GMT+7). Chốt TRƯỚC mọi số. Owner chốt thiết kế: **linear 1 tham số** (không step-tier), sweep α ∈ {0.3, 0.5, 0.7} trên nền **C2**.
Bối cảnh: C2 (K24 + `GATE_QUOTA_SKIP_WHEN_FULL=true`) đạt mục tiêu n≈700 lệnh/năm nhưng quality giảm theo k (rank 17–24 edge thấp hơn — S1_K24 "edge dài 17–24 giảm"); hiện sizing cào bằng margin cho mọi rank trong topK. Giả thuyết: dồn vốn về rank cao (size giảm dần theo k) giữ n≈700 nhưng kéo Calmar/maxDD/2022 về gần C0 hơn.
Ràng buộc: 0 Java sim trên Oracle (chỉ `mvn -o test` + build), 0 chạm 242/shadow_c3, 0 merge, DEV ≤ 2025-12-30, Kaggle ≤ 2 kernel song song, df < 500 MB ⇒ dừng.

## 1. Cơ chế (thiết kế CỐ ĐỊNH)
- Key `SIM_RANK_MARGIN_ALPHA` (đọc qua `Cfg` trong `Configs`, mặc định **0**). α=0 ⇒ **byte-identical C2**.
- Áp cho leg SELECTOR entry (`PREDICT_SYMBOL_TRADE`), chỉ khi `selRank != null` (1-based, rank 1 = tốt nhất = pNoPump thấp nhất tick). BIG_DOWN / DCA_LEVEL1 có `selRank == null` ⇒ giữ nguyên size.
- Công thức: `m(k) = 1 − α·(k−1)/(K−1)`, K = `SELECTOR_RANK_TOPK` (=24 trên C2). k=1 ⇒ m=1 (full); k=K ⇒ m=1−α. Clamp m ≥ 0.
- Vị trí nhân: trong `SimulatorMarketLevelTicker1MStopLoss.createOrder`, **sau** `budget *= tierMultiplier`, **trước** VolTargetSizing/DCA-grid ratio ⇒ toàn bộ cụm (entry + các leg DCA cùng coin) cùng co theo rank.
- Lưu ý: `DCA_SIGNAL_GATE` OFF trên C2 ⇒ không có leg-signal mang selRank; chỉ leg selector chịu tác động. Live chưa sửa (vòng này chỉ sim, đánh giá "xem sao"); live path ghi trong RESULT nếu GO.

## 2. Điểm sửa dự kiến
| file | chỗ | sửa |
|---|---|---|
| `tradecore/Configs.java` | cạnh `GATE_QUOTA_SKIP_WHEN_FULL` (~:159) + parse (~:906 cạnh `SIM_F_BASE`) | field `RANK_MARGIN_ALPHA=0f`; `Cfg.get("SIM_RANK_MARGIN_ALPHA")` → `Float.parseFloat` |
| `research/SimulatorMarketLevelTicker1MStopLoss.java` | sau `budget *= tierMultiplier` (~:1423) | khối `if (RANK_MARGIN_ALPHA>0 && selRank!=null && TOPK>1) budget *= m(selRank)` |

Kiểm: `mvn -o test` 0 fail; `bash tools/check_cfg_gateway.sh` OK; jar sha256 ghi vào RESULT + upload dataset Kaggle riêng `sim-jar-rm` (kèm `prof_r4_kg0_k16_f015_g155.properties` md5 0e0caef0).

## 3. Cổng byte-identical OFF (P0, trước khi chạy ON)
- Class diff `target/classes` (build HEAD `a5e347a5` vs build branch): chỉ được khác **2 file** ở §2 (+ inner class do LineNumberTable nếu có); mọi class khác byte-identical.
- Kaggle P0 = C2 α=0 (default): profile `r4_kg0_k16_f015_g155` + B0OV + `SELECTOR_RANK_TOPK=24` + `GATE_QUOTA_SKIP_WHEN_FULL=true`, bundle `sim-x1-2021-bundle`, bins deploy, jar MỚI, kernel `tools/kaggle_sim.py` HEAD (md5 8b60b00a, NOWRITE242), recipe `gate_skipfull_driver` (A1 = pred.bin gốc bundle). PASS ⇔ md5 printDone bắt đầu **`ad26fd55`** (= gqsf-a1, C2 seed 42). FAIL ⇒ DỪNG, không chạy ON.

## 4. Sim (Kaggle) — seed A1 (42) trước
- 3 arm α ∈ {0.3, 0.5, 0.7} × seed **A1** (pred.bin gốc bundle), nền C2 (K24 + skipFull), jar `sim-jar-rm`, tag `rm-a1-030/050/070`. P0 (α=0) = đối chứng = chính run gqsf-a1 (md5 ad26fd55).
- Parity từng arm (sai ⇒ VOID): jar sha256 = sha jar mới; `SELECTOR_RANK_TOPK=24`; `GATE_QUOTA_SKIP_WHEN_FULL=true` + B0OV trong prof_run; `SIM_RANK_MARGIN_ALPHA=<α>`; pred md5 = 5dd6bb4c; log `[RANK-MARGIN] alpha=<α>`; result.ok.

## 5. Số đo + luật GO (CỐ ĐỊNH, seed A1)
Thước dùng lại (`reset_rule_score` / `gate_skipfull_driver.score`): CAGR22, maxDD22 (MTM phút), Calmar22, UW22, n/năm, ROI năm 2022, ΣPnL theo rank-band (1–8 / 9–16 / 17–24, từ `selRank` trong printDone/ledger nếu có; nếu không có sẵn thì dùng proxy rank từ printDone order).
Luật GO (đề xuất cho MASTER, seed A1, KHÔNG tự merge/deploy):
- **C1** n/năm ≥ 700 (giữ mục tiêu; vẫn mở đủ 24 slot).
- **C2** maxDD22 (MTM) không sâu hơn C2 baseline (−22,21), và Calmar22 ≥ C2 (1,662).
- **C3** ROI 2022 ≥ C2 baseline (6,51%) — không làm năm bear yếu hơn nữa.
- Báo thêm (không phải luật): CAGR22, ΣPnL theo rank-band 17–24 (kỳ vọng bớt lỗ/ít dilutive), tổng ΣPnL.
- Kỳ vọng khai trước: CAGR22 giảm nhẹ so với C2 (vốn dồn về rank cao, tổng notional thấp hơn), maxDD/Calmar/2022 cải thiện về hướng C0, n giữ ~700–742.

## 6. Rủi ro khai trước
- 1 seed (A1) ⇒ chưa đo phương sai seed; đây là "xem sao". Nếu A1 khả quan ⇒ mở rộng seed xấu (S7/S13/S21) 1 vòng pre-reg bổ sung trước khi xét live.
- Linear giảm đều, có thể quá hiền cho rank 17–24 (edge giảm mạnh) — ghi nhận, không đổi thiết kế sau khi thấy số.
- Mọi thay đổi size đổi sổ lệnh ⇒ CAGR22 tuyệt đối lệch; đánh giá chính = maxDD/Calmar/2022/rank-band, không phải CAGR tuyệt đối.

## 7. Đầu ra
`docs/result/RESULT_RANK_MARGIN.md` + `docs/result/rank_margin.json`; driver `research/analysis/rank_margin_driver.py`. Code trên branch `feat/rank-margin` (push branch, KHÔNG merge).
