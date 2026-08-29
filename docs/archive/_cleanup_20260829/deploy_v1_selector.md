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

## Config can set (task 19) — DA XAC DINH: them vao conf/env.sh
DA KIEM: `conf/env.sh` KHONG set env selector/gate nao -> live dang chay DEFAULT cua Configs.java,
KHAC canonical WFO. Cu the live hien tai (default) vs WFO:
- `SELECTOR_RANK_TOPK`: default **-1** (sai) -> WFO **5** (K5). BAT BUOC set.
- `MIN_MOMENTUM_15M`: default **0.02284** -> WFO gate dung `SIM_MIN_MOMENTUM_15M=0.008`.
- `NUMBER_ENTRY_EACH_SIGNAL`: live config=4 -> backtest=2.

Them block nay vao `conf/env.sh` (242), roi restart:
```sh
export SELECTOR_RANK_TOPK=5
export SIM_MIN_MOMENTUM_15M=0.008
# (giu default AI_DYNAMIC_* / PREDICT_SYMBOL_RATE_MAX = genome WFO neu khop; verify o reconcile)
```
=> Neu KHONG set, live vao lenh khac han backtest du dung model. Day la diem lech backtest<->live lon.

## 2 DIEM MO cho Uni quyet
1. **GATE model**: `FILE_AI_PREDICTIONS=ai_models_reg_v3` (gate `aiBrain` = reg_v3 cu). Backtest +878 dung gate WFO. -> reg_v3 CO phai gate WFO khong? Neu KHONG, v1 phai swap ca gate model (them 1 model).
2. **Cho set config env K5/threshold**: conf/env.sh hay hardcode? Can biet de set dung.

## Param rac (task 17) — xu ly qua config, KHONG xoa code
Cac param chet (DCA_*/BREAKER_*/SHORT_*/TIME_STOP) deu gated OFF san (default). "Delete" = KHONG set chung trong env/config (de default off). Khong xoa field trong Configs.java (tranh break compile + con dung o backtest).

## Sau deploy
- Paper/size nho truoc, reconcile live-vs-sim (task 21 harness), roi tang von.
- Roll-back: doi lai jar.bak + onnx.bak + restart.
