# PHA 1 — THAM CHIẾU GENE + HƯỚNG DẪN QUYẾT (đọc kỹ code, xác nhận 2026-08-24)

> Đọc trực tiếp từ StrategyWfoTask.GENOME, Configs.java, DcaUtils, TradeUtils, AIRejectFilter,
> SimulatorMarketLevelTicker1MStopLoss, OrderTargetInfo(updateTPSL). Cột "backtest chạm?" là
> KẾT LUẬN từ code, không suy đoán.

## ⚠️ HAI GENE CHẾT (HPO tune nhưng backtest KHÔNG chịu tác động) — quyết BỎ ở 1.2
- **HARD_RISK_LIMIT_4H** (-0.2): AIRejectFilter (docstring 2026-08-08) đã bỏ hẳn nhánh risk4h;
  biến chỉ còn tồn tại để "khỏi lệch index gene", KHÔNG ảnh hưởng PASS/REJECT. → gene rỗng.
- **BUDGET_MARGIN_RATIO_1** (0.4820): TradeUtils guard `if(!OFF_FLAT_HARD && ...)`; mà
  `OFF_FLAT_HARD=true` (mặc định) → tầng này bị bỏ → gene vô tác dụng khi OFF_FLAT_HARD còn true.

## Cờ quyết định gene NÀO có trong GENOME (mặc định env rỗng)
- `DCA_GRID_ENABLED`=false, `DCA_GRID_SCALAR`=false → **nhánh DCA grid TẮT** → GENOME dùng
  DCA_LOSS_BIG_DOWN + DCA_TIME_BIG_DOWN. (Worker WFO có thể bật qua env → khi đó dùng 5 gene grid.)
- `DCA_TIER_MARGIN_ENABLED`=false → 2 gene tier-cap KHÔNG vào GENOME.
- `TS_GIVEBACK_FLOOR`=false → dùng TS_MAX_GAP/TS_MAX_GAP_WEAK/TS_WEAK_MOMENTUM_THRES;
  nếu true → dùng TS_MIN_GAP/TS_GIVEBACK_RATIO thay thế.
- `OFF_FLAT_HARD`=true, `FILTER_MODE`="A" (MOM15 gate BẬT).

## Bảng gene (default value | backtest chạm? | làm gì)

### Cụm GATE (entry) — AIRejectFilter, luôn xét
| gene | default | chạm? | làm gì |
|---|---|---|---|
| MIN_MOMENTUM_15M | 0.02284 | ✅ | REJECT entry nếu predReturn15M < ngưỡng. Worker WFO override 0.008. ⚠️range nhiễm |
| PREDICT_SYMBOL_RATE_MAX_THRESHOLD | 0.15 | ✅ (nhánh dynamic) | baseline prob để scale gate + early-hard-gate. ⚠️ |
| AI_DYNAMIC_MULTIPLIER | 1.2876 | ✅ (dynamic) | scale = (symbolPred/baseline)×MULT. ⚠️ |
| AI_DYNAMIC_MIN | 0.26787 | ✅ (dynamic) | cận DƯỚI clamp của scale (can TREN da bi XOA KHOI CODE 2026-09-03 cung voi co OFF_FLAT_HARD; nguong gate khong co tran). ⚠️ |
| HARD_RISK_LIMIT_4H | -0.2 | ❌ CHẾT | (xem trên) |

### Cụm MARKET regime
| MS_DOWN_BIG_AVG | -0.03157 | ✅ | ngưỡng nhận diện BIG_DOWN trong MarketBigChangeDetector. ⚠️ |

### Cụm DCA — chỉ 1 nhánh vào GENOME tuỳ cờ
| DCA_LOSS_BIG_DOWN | -0.15 | ✅ (grid OFF) | mức lỗ kích hoạt nhồi ở BIG_DOWN (getDcaConfig). ⚠️ |
| DCA_TIME_BIG_DOWN | 8 | ✅ (grid OFF) | số phút chờ trước khi nhồi. ⚠️ |
| DCA_GRID_L1 | -0.50 | ✅ (grid ON) | mốc nhồi bậc đầu, đo trên firstEntryPrice (dcaGridLevel) |
| DCA_GRID_STEP | 0.20 | ✅ (grid ON) | độ giãn giữa 2 bậc: level[i]=L1−STEP×i |
| DCA_GRID_LEGS | 3 | ✅ (grid ON) | trần số bậc nhồi (dcaGridLegs) |
| DCA_GRID_W_RATIO | 2.0 | ✅ (grid ON) | tỉ trọng vốn theo bậc: w[i]=W_RATIO^i (dcaGridWeight) |
| DCA_GRID_SCALE | (env) | ✅ (grid ON) | nhân bù tổng tỉ trọng (gridLegWeightRatio) |
| DCA_TIER_CAP_BASE | 0.50 | ⚠️ chưa xác nhận wiring | cap margin bậc: cap[i]=BASE+STEP×i (accessor Configs, chưa thấy sim gọi) |
| DCA_TIER_CAP_STEP | 0.10 | ⚠️ chưa xác nhận wiring | như trên |

### Cụm EXIT / trailing stop — TradeUtils + updateTPSL
| RATE_PROFIT_STOP_MARKET | 0.03 | ✅ | ngưỡng arm + mức dời SL tối thiểu (sim line 724, TradeUtils). ⚠️(TASK-139) |
| TS_PROFIT_MULTIPLIER | 5.21847 | ✅ | nhân ngưỡng ratchet (dead-zone arm→ratchet); active khi TS_RATCHET_DECOUPLED=false. ⚠️ |
| TS_DYNAMIC_K | 0.29774 | ✅ | dynamicRate=predReturn15M×K, nâng ngưỡng dời SL. ⚠️ |
| TS_MAX_GAP | 0.08 | ✅ (floor OFF) | trần gap trailing (nhả lãi tối đa) |
| TS_MAX_GAP_WEAK | 0.03 | ✅ (floor OFF) | trần gap khi momentum yếu |
| TS_WEAK_MOMENTUM_THRES | 0.004 | ✅ (floor OFF) | ngưỡng coi momentum yếu |
| TS_MIN_GAP | (env) | ✅ (floor ON) | sàn gap tuyệt đối |
| TS_GIVEBACK_RATIO | (env) | ✅ (floor ON) | tỉ lệ nhả lại lợi nhuận |

### Cụm BUDGET (chia vốn) — TradeUtils.managerBudget
| BUDGET_MARGIN_RATIO_1 | 0.4820 | ❌ CHẾT (khi OFF_FLAT_HARD=true) | (xem trên) |
| BUDGET_MARGIN_RATIO_2 | 0.7475 | ✅ | nếu marginRatio≥ngưỡng → budget/=BUDGET_DIVIDER_2 |
| BUDGET_DIVIDER_2 | 1.5984 | ✅ | hệ số chia vốn ở tầng 2 |

## Cost model (Configs.java) — đã xác nhận
- RATE_FEE = 0.002 (2 chân); SLIPPAGE_RATE = 0.003 (2 chân), APPLY_SLIPPAGE=true.
  Tổng chi phí round-trip ≈ 0.8% (comment Configs line 230). fee tính ở HPOFitnessCalculatorV4:186.
- CAPITAL_START: scan không bắt được literal (runbook nói 35000) — xác nhận lại nếu 1.2 cần con số.

## Feature f0..f39 + label
- 40 feature Tool1 (opaque, positional) + 5 OI (oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy).
  Tên đầy đủ f0..f39 KHÔNG phải string literal trong exporter (không rút được bằng scan) — nằm rải theo
  thứ tự ghi trong bộ export funding v2. Nếu 1.2 quyết ĐỘNG tới feature set → tôi trace đầy đủ thứ tự sau.
- Label: 2-sided triple-barrier (train_funding_selector_wfo.load_labels). TP=SEL_FAV_PCT=0.06,
  SL=SEL_ADV_PCT=0.03 (⚠️ "placeholder, user chốt sau"), horizon 4h, lấy mẫu grid 15m (⚠️ overlap).

---

## HƯỚNG DẪN LÀM 1.2 — "chốt" nghĩa là gì (không phải chỉ "bỏ")

Với MỖI dòng trong `PHASE1_DECISION_SURFACE.md`, bạn chọn 1 trong 4 và ghi lý do THEO LÝ THUYẾT
(cơ chế thị trường/vật lý giao dịch), TUYỆT ĐỐI không dựa vào "kết quả 2024-2025 thấy tốt":

- **GIỮ** — cố định 1 giá trị, KHÔNG cho máy search (khi bạn tin chắc a priori). VD cost model.
- **NỚI** — cho máy search, ghi [lo, hi] RỘNG theo lý thuyết (rộng hơn range cũ). Dùng cho gene bạn
  muốn máy tự tìm. Đây là cách "rửa" bias: space không còn là tập con của cái đã sweep.
- **CỐ ĐỊNH giá trị mới** — đóng băng 1 hằng số bạn quyết theo lý thuyết (VD label SL=? theo tỉ lệ
  TP, không theo backtest).
- **BỎ** — loại khỏi search / tắt hẳn. VD 2 gene chết (HARD_RISK_LIMIT_4H, BUDGET_MARGIN_RATIO_1).

### Thứ tự quyết (theo phụ thuộc, làm từ trên xuống)
1. **Cờ trước tiên** (quyết gene nào tồn tại): DCA grid ON/OFF? TS_GIVEBACK_FLOOR ON/OFF?
   OFF_FLAT_HARD giữ true? → chốt xong mới biết GENOME gồm gene nào.
2. **Label** (A2): kiểu barrier, TP, SL (đang placeholder!), horizon, lấy-mẫu grid vs nonoverlap.
3. **Feature set** (A1) + **universe/survivorship** (A4).
4. **Selector** hp + có Optuna hay không (A3).
5. **Range 17 gene sống** (B7): mỗi gene NỚI/GIỮ/BỎ + lý do.
6. **Gate/rank-K/cost** (B5,B6,B8).
7. **Objective O + ngưỡng pass + CPCV + budget n_trials + stopping** (C9–C12).

### 2 gene chết xử sao
BỎ khỏi GENOME. Nhưng lưu ý comment code: xoá field làm "lệch index gene" cho pipeline cũ →
cách an toàn là để field tồn tại nhưng KHÔNG đưa vào search space v-mới (không put vào GENOME).
