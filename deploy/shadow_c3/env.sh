# ENV instance SHADOW C3 tren Oracle. KHONG deploy file nay len 242.
# [2026-09-18 T170-FIX] Sua cho KHOP T170 backtest chuan (profiles/x1_gs_t170.properties,
#   run md5 efb793e2468ca3a7318da0f0ad23d4fc). Xem docs/RESULT_SHADOW_T170_FIX.md.
#   GIU NGUYEN: SHADOW_NO_PUSH=true (paper, khong ra lenh that), LIVE_PROFILE=c3_shadow, PAPER_EQUITY.
export APP_MAIN_CLASS=com.binance.chuyennd.trading.BinanceOrderTradingManager
export APP_PID_DIR=./run

# --- CO C3 (mac dinh TAT o moi noi khac; chi instance nay bat) ---
export LIVE_PROFILE=c3_shadow
# SHADOW_NO_PUSH cung duoc HARDCODE true trong LiveProfileC3 khi co bat; dat o day cho ro rang.
# TUYET DOI KHONG tat — paper only.
export SHADOW_NO_PUSH=true
export PAPER_EQUITY=35000
# [FIX 2026-09-18b] CAPITAL_START goc tinh size lenh (Configs.capitalStart(): env > config.properties).
#   config.properties da =35000 nen hanh vi khong doi; ghi ro o day cho env tu-du, khop T170 (CAPITAL_START=35000).
export CAPITAL_START=35000
export SHADOW_C3_DIR=/home/ubuntu/shadow_c3
export S1_MODEL_ONNX=/home/ubuntu/s1_model/s1a2x1_cut20251001.onnx

# --- THAM SO T170 (nguon: profiles/x1_gs_t170.properties) ---
export SELECTOR_RANK_TOPK=8
# [FIX] 1 -> 0: T170 backtest KHONG tat market-signal/BIG_DOWN leg (SELECTOR_ONLY_ENTRY=0).
export SELECTOR_ONLY_ENTRY=0
export SIM_MIN_MOMENTUM_15M=0.008
export SIM_RATE_PROFIT_STOP_MARKET=0.07
export SIM_TS_GIVEBACK=1
export TS_GIVEBACK_RATIO=0.5
# [FIX] them: loser time-stop 168h (profile SIM_LOSER_TIME_STOP_HOURS=168; truoc day unset=0).
export SIM_LOSER_TIME_STOP_HOURS=168
export TIER_FLAT=1
# [FIX] gate scale 1.70 (T170). Truoc day KHONG set => default 1.0 (= T100, sai).
export SIM_GATE_DYN_SCALE=1.70
# --- DCA GRID (profile: ENABLED=true, WEIGHTS=1,1,3,8, SCALE=19.5) ---
# [FIX] ENABLED them (truoc unset=false=tat DCA); WEIGHTS 1,0,0,0 -> 1,1,3,8; SCALE them 19.5 (truoc unset=1.0).
export DCA_GRID_ENABLED=true
export DCA_GRID_WEIGHTS=1,1,3,8
export DCA_GRID_SCALE=19.5
# --- 3 bug-fix B1/B2/B3 (profile bat het; default cung true nhung ghi ro) ---
export SIM_FIX_B1=true
export SIM_FIX_B2=true
export SIM_FIX_B3=true
# --- breaker OFF (profile) ---
export SIM_BREAKER_MODE=OFF
# --- funding accounting (profile bat; anh huong PnL paper, KHONG anh huong entry) ---
export SIM_APPLY_FUNDING=true
export SIM_FUNDING_MARK=true

# --- ha tang ---
export EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json
export AEROSPIKE_BATCH_TOTAL_TIMEOUT_MS=20000
export AEROSPIKE_BATCH_SOCKET_TIMEOUT_MS=15000
