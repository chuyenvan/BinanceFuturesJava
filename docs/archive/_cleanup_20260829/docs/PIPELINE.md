# PIPELINE.md — Vận hành mô hình theo nhịp Walk-Forward 3 tháng

> **Vận hành định kỳ (cadence)** — bổ trợ `ROADMAP.md` (lộ trình kiểm chứng), KHÔNG thay thế. Lộ trình rebuild model → `REBUILD_ROADMAP.md`.

Tài liệu vận hành chính thức. Claude Code và người vận hành bám theo đây.
Mục tiêu: mỗi 3 tháng sinh một version model+tham số ĐÃ QUA CỔNG GÁC, không deploy thứ chưa chứng minh edge.

---

## 0. HAI PHA KHÁC NHAU — đừng lẫn

**Pha A — VALIDATE PIPELINE (làm MỘT LẦN, trước khi tin v1).**
Chạy WFO trên lịch sử để chứng minh *quy trình* tối-ưu-rồi-giao-dịch generalize qua nhiều regime.
Output là PHÁN QUYẾT (pipeline đáng tin hay không), KHÔNG phải bộ tham số.
Chưa PASS pha này thì v1 chỉ là "chạy thử vốn bé để trải nghiệm", KHÔNG được tăng vốn.

**Pha B — CADENCE 3 THÁNG (lặp lại mãi).**
Mỗi 3 tháng: re-train model → đo IC → (nếu PASS) HPO lại → backtest → deploy.
Đây là cái 1.8.2026 (v1), 1.11.2026 (v2), 1.2.2027 (v3)... chạy theo.

Holdout = OOS test = bước trượt = nhịp re-fit = **3 tháng**. Một con số cho cả pipeline.

---

## 1. LỊCH (CADENCE)

| Version | Ngày deploy | Train data tới | Holdout (đo IC) | HPO window |
|---------|-------------|----------------|-----------------|------------|
| v1      | 2026-08-01  | 2026-05-01     | 2026-05-01 → 08-01 | 12 tháng gần nhất |
| v2      | 2026-11-01  | 2026-08-01     | 2026-08-01 → 11-01 | 12 tháng gần nhất |
| v3      | 2027-02-01  | 2026-11-01     | 2026-11-01 → 02-01 | 12 tháng gần nhất |
| ...     | +3 tháng    | D − 3 tháng    | 3 tháng cuối    | 12 tháng |

Quy ước version: `vN` gắn với `CONFIG_VERSION="vN"` trong RunHpoMaster_Distributed.
Vì mỗi cadence re-train model → output predict đổi → BẮT BUỘC bump CONFIG_VERSION.

---

## 2. MỘT CHU KỲ CADENCE — 9 BƯỚC + 2 CỔNG GÁC

Ký hiệu D = ngày deploy (vd 2026-08-01). Holdout = [D−3th, D].

### B1. Export features (tới mốc D)
- Market: `RunFullDataCollection.main()` → `storage/training_data_big_sequential`
- Funding: `RunFundingDataCollection.main()` → `storage/training_data_funding`
- CSV PHẢI có cột `timestamp` (market) và `timestamp,symbol` (funding) ở đầu — để cắt holdout theo thời gian.

### B2. Validate data (cổng dữ liệu, tự động)
- Không gap thời gian quá ngưỡng; không NaN/Inf bất thường.
- Distribution drift: mean/std mỗi feature so với cadence trước; lệch quá ngưỡng → cảnh báo + dừng.
- Dùng tool có sẵn trong `aerospike/validate_data/`, `ai_ml/validation/`.

### B3. Train model + đo IC trên holdout
- `ai_market_xgboost_optuna.py` (33 feature, IC gate) — ĐỔI `HOLDOUT_MONTHS = 3`.
- `ai_fundingfee_xgboost_optuna.py` (21 feature, label6) — ĐỔI `HOLDOUT_MONTHS = 3`.
- Scaler fit CHỈ trên train; purge gap (market 24H, funding 72H); KHÔNG shuffle.

### 🚪 CỔNG GÁC 1 — IC (BẮT BUỘC, dừng nếu trượt)
PASS khi TẤT CẢ:
- Market: IC holdout (Spearman predicted-vs-realized) **dương** cho `futureReturn15M`, và `%tuần>0 ≥ 60%`.
- IC không sụp ở regime "down" (không được âm mạnh ở thị trường sập).
- Funding: rank-IC dương + lift hit-rate(<=4H) ở ngưỡng P(fast)≥0.5 phải **> 1.0** (tốt hơn base).
- IC nhỏ (0.03–0.06) vẫn PASS nếu ỔN ĐỊNH. IC ≈ 0 hoặc âm → **FAIL**.

FAIL → DỪNG. Không deploy. Quay lại feature/label (KHÔNG đụng HPO — lỗi ở model, không phải tham số).
PASS → đi tiếp.

### B4. Train model PRODUCTION (dùng hết data tới D)
- Sau khi cổng IC PASS, train lại trên TOÀN BỘ data tới D (gồm cả 3 tháng holdout) → model deploy.
- Lý do hợp lệ: đã chứng minh quy trình tạo model tốt qua holdout; giờ dùng hết data cho lần áp tương lai.
- Export ONNX, đặt đúng tên file inference live đang đọc.

### B5. Export predict (điền dự đoán model mới vào Aerospike 226)
- Chạy tool sinh predict trên toàn khoảng HPO window, lưu set predict trên 226.

### B6. HPO (bump CONFIG_VERSION!)
- `CONFIG_VERSION = "vN"` (model đổi = config đổi = cache cũ phải cô lập).
- `RunHpoMaster_Distributed` + worker (226 + Kaggle) trên HPO window 12 tháng gần D.
- Genome: **18 gene** (sensitivity đã chốt — [ADR-0012](decisions/0012-genome-18-gene-off-cung-cum-C.md): cụm A 13 + B 5, OFF cứng 9 gene cụm C), tối ưu theo nhóm. (Con số cũ "13→8" đã bị số liệu sensitivity bác.)

### B7. Backtest verify (BacktestIntegrityGuard luôn bật)
- `simulatorWithInitEntry` (dòng đầu) tự gọi `assertProductionGrade()`: look-ahead OFF, slippage ON, fee ON. *(xem ADR-0002 — KHÔNG phải `BackTestEngineMaster.run`)*
- Chạy với bộ tham số HPO tốt nhất.
- `EdgeAttributionReport`: kiểm AI edge (first-leg MAE/rescueRate vs random), `profitFactor`, `worstSingleLoss`.

### 🚪 CỔNG GÁC 2 — Backtest health (BẮT BUỘC)
PASS khi:
- `profitFactor` ≥ 1.3 trên đoạn OOS.
- `worstSingleLoss` trong ngưỡng chịu được (vd ≤ X% vốn — tự đặt).
- Ablation: model A rõ ràng tốt hơn entry random C (first-leg). Nếu A≈C → AI vô dụng, không deploy AI.
- Max drawdown OOS < 40% (kill-switch của fitness).

FAIL → giữ version cũ đang chạy, KHÔNG deploy bộ mới. Điều tra tầng khai thác (HPO/chiến lược).
PASS → đi tiếp.

### B8. Release product (vốn bé)
- Build jar, deploy lên 242 (product). Config = bộ HPO mới + LUẬT Bước 0 (look-ahead/slippage) đang bật.
- Bắt đầu vốn bé để trải nghiệm. KHÔNG tăng vốn khi Pha A (WFO lịch sử) chưa PASS.

### B9. Validate product vs backtest (liên tục, tới cadence sau)
- Định kỳ: gom log lệnh thật product → chạy lại backtest trên ĐÚNG khoảng + ĐÚNG tham số product đã chạy.
- So PnL / số lệnh / drawdown thực vs backtest. Lệch quá ngưỡng → cảnh báo (dấu hiệu sim≠product hoặc data drift).

---

## 3. GIỮA HAI CADENCE — chính sách "thời gian dư"

KHÔNG deploy off-cadence. Thời gian dư + CPU rảnh dùng cho:
1. **Tối ưu HPO sâu hơn** trên cùng window (thêm trial, tinh chỉnh genome) — kết quả chỉ áp ở cadence kế.
2. **Cải thiện model theo IC**: thử feature mới / label mới, đo IC trên holdout. Chỉ giữ cái nâng IC ỔN ĐỊNH.
3. **Pha A WFO lịch sử** nếu chưa làm xong — đây là ưu tiên cao nhất khi rảnh, vì nó gác cổng việc tăng vốn.
4. **Monitor drift**: dashboard IC predicted-vs-realized theo tuần trên data live mới. IC tụt → trigger re-train sớm (không đợi đủ 3 tháng).

Trigger re-train SỚM (trước cadence) chỉ khi: drift monitor báo IC sụp dưới ngưỡng. Khi đó chạy lại B3 ngay.

---

## 4. LUẬT BẤT DI BẤT DỊCH (nhắc lại, tham chiếu CLAUDE.md)

- Mỗi cadence đổi model → BẮT BUỘC: export predict mới → HPO lại → bump CONFIG_VERSION → mới deploy. KHÔNG thay model giữ tham số cũ.
- `taskId` HPO băm ĐỦ mọi gene.
- Backtest luôn qua `BacktestIntegrityGuard` (look-ahead OFF, slippage/fee ON).
- Hai cổng gác là HARD STOP. FAIL thì DỪNG, không "linh hoạt cho qua". Đặc biệt với product vốn thật.
- Tách bạch: Cổng 1 đo MODEL (lỗi → sửa feature/label). Cổng 2 đo CHIẾN LƯỢC (lỗi → sửa HPO/sim). Đừng chữa nhầm tầng.

---

## 5. HẠ TẦNG CHẠY (ai làm gì)

- **Máy cá nhân + Claude Code**: điều khiển, sửa code, commit/push, đọc kết quả (CSV dump từ 226) để phân tích + quyết định cổng gác.
- **Kaggle (GPU)**: B3 train model, B6 HPO worker.
- **226 (CentOS)**: B1 export, B6 HPO worker + master, B7 backtest. `git pull` + build qua deploy script.
- **242 (product)**: B8 chạy live. Firewall đã khóa, chỉ 226/Oracle/VPN vào Aerospike.
- Trục liên lạc: git (code) + Aerospike (job + kết quả). Không có kênh tự nói chuyện giữa các Claude Code.

---

## 6. TRẠNG THÁI HIỆN TẠI (cập nhật mỗi cadence)

- [ ] Pha A — WFO lịch sử: CHƯA chạy. (Ưu tiên cao — gác cổng tăng vốn.)
- [x] Bước 0 — look-ahead/slippage: ĐÃ bịt, thành rule (BacktestIntegrityGuard).
- [~] Train scripts: ĐÃ sửa time-split + IC gate. CẦN đổi HOLDOUT_MONTHS 12→3.
- [ ] v1 (2026-08-01): chạy cadence lần đầu, vốn bé.