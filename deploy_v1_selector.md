# Deploy v1 selector (golive) — runbook 242

Atomic swap: jar module (feature 45 + NUM_FEATURES=45) + model selector 45-input. **KHONG lam le tung phan** (jar cu 21 + model 45 = vo, va nguoc lai).

## Tien dieu kien (da xong, code side)
- Branch `module`: fc1ee32 (OI fix) + 663eed1 (feature 21->45) + 92c8967 (convert script).
- `selector_wfo_4h.onnx` (Oracle `/home/ubuntu/selector_kaggle_out/`) — 45-input, parity verify 4.5e-7, dung chieu.

## Buoc deploy (Uni chay tren 242, user root, port 2222)
```
cd /home/chuyennd/java/v_t_m
# 0. BACKUP
cp target/binance-java-sdk-1.2.4.jar target/binance-java-sdk-1.2.4.jar.bak_$(date +%s)
cp ../storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx \
   ../storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx.bak_$(date +%s)

# 1. BUILD jar tu module (tren may build/dev co maven)
#    git -C <repo> checkout module && git pull && mvn -q package -DskipTests
#    -> copy binance-java-sdk-1.2.4(-shaded).jar -> 242 target/

# 2. PLACE model selector moi (scp selector_wfo_4h.onnx tu Oracle)
cp selector_wfo_4h.onnx ../storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx

# 3. CONFIG (xem "Config can set" duoi)

# 4. RESTART
bin/daemon.sh stop ; sleep 3 ; bin/daemon.sh start
tail -f logs/full.log   # cho "Funding AI System Ready" + predictBatch khong loi shape
```

## Config can set (task 19) — CHUA RO CHO SET, can xac nhan
Live doc qua env (Configs.getenv). `bin/start.sh` hien chi co JAVA_OPTS+main; env K5/threshold set o dau (conf/env.sh?) can xac nhan. Gia tri canonical WFO:
- `SELECTOR_RANK_TOPK=5`  (K5 — BAT BUOC, default -1 = sai)
- `SIM_MIN_MOMENTUM_15M` / `MIN_MOMENTUM_15M` = gia tri gate canonical
- `PREDICT_SYMBOL_RATE_MAX_THRESHOLD`, `AI_DYNAMIC_MIN/MULTIPLIER/MAX` = canonical
- `NUMBER_ENTRY_EACH_SIGNAL`: live=4, backtest=2 -> can thong nhat
- `CAPITAL_START`, `LEVERAGE_ORDER=1`

## 2 DIEM MO cho Uni quyet
1. **GATE model**: `FILE_AI_PREDICTIONS=ai_models_reg_v3` (gate `aiBrain` = reg_v3 cu). Backtest +878 dung gate WFO. -> reg_v3 CO phai gate WFO khong? Neu KHONG, v1 phai swap ca gate model (them 1 model).
2. **Cho set config env K5/threshold**: conf/env.sh hay hardcode? Can biet de set dung.

## Param rac (task 17) — xu ly qua config, KHONG xoa code
Cac param chet (DCA_*/BREAKER_*/SHORT_*/TIME_STOP) deu gated OFF san (default). "Delete" = KHONG set chung trong env/config (de default off). Khong xoa field trong Configs.java (tranh break compile + con dung o backtest).

## Sau deploy
- Paper/size nho truoc, reconcile live-vs-sim (task 21 harness), roi tang von.
- Roll-back: doi lai jar.bak + onnx.bak + restart.
