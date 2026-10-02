# PRE-REG — SHORT_V2 Pha 0B: squeeze-predictability của model LONG (chỉ thông tin, không kill)

Ngày 2026-10-02 · Chương trình `docs/research/PROGRAM_SHORT_V2.md` (d1057bd1) §2 hàng 0B · Branch `module`.
Viết và commit TRƯỚC khi đo nhãn/metric. Chạy MỘT lần. Không tune sau khi thấy số (amend chỉ trước khi đo).

## 0. Câu hỏi
Các điểm số của model LONG hiện có dự báo SQUEEZE (đuôi phải) tốt tới đâu trên universe DEV, OOS, theo năm:
P(`maxFav_7d` ≥ +10%), P(≥ +20%) và `retEnd_7d`. Nếu tách được "sắp pump" vs "không pump" ⇒ dùng làm feature/gate
chống squeeze ở Pha 1. Không có ngưỡng GO/KILL.

## 1. Nguồn điểm số + bằng chứng leak-free (đã kiểm TRƯỚC khi đo)
| score | nguồn | leak-free? | bằng chứng |
|---|---|---|---|
| **S1** | `/home/ubuntu/ledger/pred_s1a2x1.parquet` (`ts,sym,score` f32; 6.573.909 dòng; 620 sym; 2021-12-31 17:30 → 2025-12-31 16:45) | **CÓ (WFO OOS)** | `docs/experiment/X1_EXTEND.md` §2: 16 fold `20220101..20251001`, OOS 3 tháng, manifest `leakFreeFrom=2022-01-01`, cổng G3 PASS (10 fold cũ byte-identical); `docs/design/C2B_SPEC.md` §2: XGBRanker, WFO expanding, **purge 72h**, `assert tr.ts.max() < cutoff`. Dùng chỉ `ts ≥ 2022-01-01` (2 tick 2021-12-31 loại). |
| pNoPump | `LATEST_SEL_PNOPUMP` = prob[0] của `Funding_Classifier_Final.onnx` (`DetectEntrySignal2TradeNormal.java:874`) | — | **CHỈ LIVE**, không có panel DEV OOS (model `.onnx` đóng băng; predict lại trên DEV sẽ là in-sample). ⇒ **BỎ**. Trong SIM, đường S1 dùng `1−P(win)` ≡ hàm đơn điệu của S1 ⇒ không thêm thông tin. |
| **p15** (`predReturn15M`) | `research/parity/data/p15_dev.csv` (phút, 2.500.260 dòng, 2021-03-31 → 2025-12-31 23:59), market-level | **CÓ (WFO OOS)** | `docs/audit/AUDIT_G2FLAT3_20261002.md` Q3: ≡ `wfo_gate_pred.csv` (corr 1,00000), 21 fold WFO expanding, OOS 3 tháng, purge 15'. |
| predRisk4H | cùng file, cột 3, market-level | **KHÔNG** (in-sample, AUDIT_G2FLAT3 Q3) | chỉ báo như **đối chứng nhãn "IN-SAMPLE"**; KHÔNG dùng cho kết luận. |

Quy ước dấu S1 (khoá): `score = −pred` của XGBRanker (C2B_SPEC §2; Java chọn top-K score THẤP nhất).
Định nghĩa `lp = −score` (**lp CAO = selector long thích = model cho là "sắp chạy"**). Mọi AUC/Spearman/decile dùng `lp`.
d0 = 10% `lp` THẤP nhất trong snapshot = "ít pump nhất theo model"; d9 = top pick long.
p15: giá trị cao = thị trường dự báo tăng ⇒ dùng `p15` thô (cao = "pump"). predRisk4H: dùng thô; AUC < 0,5 cũng báo nguyên.

## 2. Snapshot (cố định)
- **Tập S1 (chính):** S1 chỉ được chấm ở các tick selector (17.349 tick, KHÔNG đều: số ngày có tick 2022/23/24/25 = 244/137/225/343;
  tick tập trung theo regime). Tại mỗi tick gần như toàn universe được chấm (median 133 coin/tick 2022 vs 136 coin có close).
  Snapshot = **tick S1 ĐẦU TIÊN của mỗi ngày UTC** (giảm chồng lấp/cụm). Chỉ dùng score ĐÚNG tick (không forward-fill).
  Phụ (robust, chỉ AUC theo năm): **toàn bộ tick S1** (không lọc ngày).
- **Tập p15 (chính cho p15/predRisk4H):** lưới đều 00:00 UTC mỗi ngày 2022-01-01 .. 2025-12-24; universe = mọi coin có close
  tại entry và ≥ 720 close 1h lịch sử trước entry. Phụ: p15 trên tập S1 (cùng snapshot với S1) để so cùng tập.
- **Causal entry:** tick S1 tại `ts` ⇒ entry = close 1h có `ctime` = trần-giờ của (`ts` + 15′) (bảo thủ: phủ trường hợp `ts` là
  open-time của nến 15m). Lưới 00:00 ⇒ entry `ctime` = 00:00. p15/predRisk4H = dòng phút cuối có `ts ≤ snap − 2′`.
- Năm = năm UTC của entry. DEV 2022–2025. Cửa sổ forward kết thúc ≤ 2026-01-01 00:00 (close cuối 2025); 2026 KHÔNG chạm.

## 3. Nhãn (1h closes `/home/ubuntu/java/fsrun/CLOSES_1H.bin`, `[ts>i8,sym>i2,c>f4]`, ctime = ts+1h, cắt ts < 2026-01-01)
- `retEnd_7d = c(entry+168h)/c(entry) − 1` (yêu cầu close đúng tại entry+168h).
- `maxFav_7d = max c(entry+1h .. entry+168h)/c(entry) − 1` (đỉnh adverse cho short). 1h closes ⇒ **cận DƯỚI** squeeze thật (wick).
- Hợp lệ khi ≥ 160/168 close trong cửa sổ. `SQ10 = 1[maxFav_7d ≥ 0,10]`, `SQ20 = 1[maxFav_7d ≥ 0,20]`.
- `bleed` = mean / median `retEnd_7d` (âm = tốt cho short).

## 4. Metric (cố định)
1. **AUC(score → SQ10)** theo năm 2022..2025 (pool mọi coin-snapshot trong năm) + toàn kỳ; **AUC(score → SQ20)** tương tự.
   Cho S1 thêm **AUC trong-snapshot** (mean qua snapshot của AUC cross-section, snapshot cần ≥ 3 dương và ≥ 3 âm) — đây là
   dạng dùng được cho gate per-coin. p15/predRisk4H hằng trong snapshot ⇒ chỉ AUC pool (đo biến thiên theo thời gian).
2. **Decile S1**: mỗi snapshot (≥ 20 coin) xếp `lp` thành 10 decile (rank method=first, qcut); d0 = ít pump nhất theo model.
   Mỗi decile: pSQ10, pSQ20, mean retEnd_7d, median retEnd_7d, n — toàn kỳ + theo năm; kèm dòng "universe" (cùng tập).
3. **Decile p15** (market-level): chia NGÀY theo decile p15 (toàn kỳ: biên trên toàn DEV; theo năm: biên trong năm);
   mỗi decile cùng 4 số + n trên coin-ngày. Bảng tương tự cho predRisk4H, nhãn **IN-SAMPLE**.
4. **Ổn định**: Spearman(lp, maxFav_7d) cross-section mỗi snapshot; mean theo năm + CI 95% block-7d (khối = 7 ngày lịch,
   resample khối có hoàn lại, trọng số = số snapshot/khối), NREP 2000, seed 20260905, percentile 2,5/97,5, KHÔNG inflate.
5. **"Mức có ích" (ghi trước, KHÔNG phải GO):** ĐẠT ⇔ S1 d0 pSQ10 ≤ 0,6 × pSQ10 universe (cùng tập S1) ở **4/4 năm**.
   Báo kèm: d0 bleed vs universe bleed (mean & median) — nếu d0 pSQ10 thấp nhưng bleed d0 ≈/kém universe ⇒ ghi rõ
   "model long chỉ dự báo YÊN, không dự báo GIẢM".

## 5. Sanity (bắt buộc trước khi báo)
- Số snapshot và số coin-snapshot hợp lệ theo năm (tập S1, tập p15); tỉ lệ nhãn hợp lệ.
- Causal: score tại t chỉ dùng ≤ t — kiểm bằng doc/ledger (§1) + kiểm cơ học: mọi entry `ctime` > `ts` tick; mọi forward
  window ≤ 2026-01-01 00:00; mọi S1 `ts` ≥ 2022-01-01.
- AUC 1 năm (2024, S1→SQ10) tính bằng 2 cách: `sklearn.metrics.roc_auc_score` vs công thức rank Mann-Whitney (rank average) —
  phải khớp tới 1e-9.
- Spot-check nhãn: 3 coin-snapshot ngẫu nhiên (seed 20260905) tính lại thủ công từ chuỗi close.

## 6. Output
Script `research/analysis/short_v2_p0b_squeeze.py` (Python `logging`, float32 lưu trữ, xử lý theo sym, RAM ≤ 8G) →
`docs/result/RESULT_SHORT_V2_P0B.json` + `docs/result/RESULT_SHORT_V2_P0B.md`. Lock `~/claude_master/1002/oracle_heavy.lock`.

## 7. Không làm
Không sửa `.java`, không Java/Kaggle, không chạm 242, không 2026, không xoá dữ liệu, không thêm biến thể sau khi thấy số.
