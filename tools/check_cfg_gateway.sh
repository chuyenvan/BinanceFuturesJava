#!/bin/bash
# GUARD: moi tham so GIAO DICH phai doc qua Cfg.get/Cfg.getOr, KHONG duoc System.getenv truc tiep.
# Ly do: neu doc env truc tiep thi TRADING_PROFILE khong kiem soat duoc key do => lai co cau hinh "an"
# (dung loi da gay ra 2 ket luan sai truoc day). Chay tu goc repo. rc=1 neu vi pham.
set -u
cd "$(dirname "$0")/.." 2>/dev/null || true
[ -d src/main ] || { echo "check_cfg_gateway: khong thay src/main (chay tu goc repo)"; exit 2; }

# Tien to / ten key duoc coi la THAM SO GIAO DICH (khop TRADING_PREFIXES + TRADING_KEYS trong Cfg.java)
PAT='System\.getenv\(\)?\.?(getOrDefault)?\("(SIM_|DCA_|TS_|SELECTOR_|TIER_|CONF_SIZE_|TRAIL_|GATE_|LIVE_|SIZE_MULT|MAX_CONCURRENT|TIME_STOP_HOURS|ENABLE_SHORT|ABLATION_MODE|SHORT_|SEL_BACKTEST|NUMBER_ORDER_BUDGET|HARD_STOP_LOSS_RATE|DISABLE_PREDICT_SYMBOL|CAPITAL_START)'

# Ngoai le HOP LE (kill-switch / ha tang, co chu dich doc env de KHONG phu thuoc file cau hinh):
#   SIM_END_DATE, SHADOW_NO_PUSH, OI_STALE_HALT*  -> khai bao trong INFRA_KEYS cua Cfg.java
ALLOW='SIM_END_DATE|SHADOW_NO_PUSH|OI_STALE_HALT'

HITS=$(grep -rnE --include=*.java "$PAT" src/main/ \
  | grep -v '/tradecore/Cfg.java' \
  | grep -vE "\"($ALLOW)" || true)

if [ -n "$HITS" ]; then
  echo "*** VI PHAM CONG Cfg: tham so giao dich doc System.getenv truc tiep ***"
  echo "$HITS"
  echo
  echo "Sua: doi thanh com.binance.chuyennd.tradecore.Cfg.get(\"KEY\") / Cfg.getOr(\"KEY\", \"default\")."
  echo "Neu that su la kill-switch/ha tang: them key vao INFRA_KEYS (Cfg.java) VA vao ALLOW cua script nay."
  exit 1
fi
echo "check_cfg_gateway: OK — khong co tham so giao dich nao lach cong Cfg."
