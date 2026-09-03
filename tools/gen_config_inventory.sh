#!/bin/bash
# Sinh docs/CONFIG_INVENTORY.md tu CHINH ma nguon. Chay tu goc repo: bash tools/gen_config_inventory.sh
# CANH BAO ve mot lan sai truoc day: KHONG duoc chi grep Configs.java. Key duoc doc qua nhieu duong
# (Configs.getString/getInt/getDouble/getBoolean, properties.get, Cfg.get) va tu NHIEU FILE khac
# (vd DIED_SYMBOLS/SPECIAL_SYMBOLS doc trong client/constant/Constants.java, CAPITAL_START trong
# BudgetManager). Ban kiem ke cu da danh dau nham 3 key nay la "moi gia" — xoa theo no se gay
# survivorship bias. Script nay grep chuoi ten key tren TOAN BO src/.
set -u
[ -d src/main ] || { echo "chay tu goc repo"; exit 2; }
OUT=docs/CONFIG_INVENTORY.md
mkdir -p docs

keys_read() {  # moi key ma code doc tu config.properties
  grep -rhoE 'Configs\.get(String|Int|Double|Long|Boolean)\("[A-Za-z0-9_.]+"\)|properties\.get\("[A-Za-z0-9_.]+"\)' \
       src/ --include=*.java | grep -oE '"[A-Za-z0-9_.]+"' | tr -d '"' | sort -u
}
file_keys() { grep -ohE '^[A-Za-z0-9_.]+[[:space:]]*=' "$1" | tr -d ' =' | sort -u; }

{
echo "# BAN KIEM KE CAU HINH — sinh tu ma nguon boi tools/gen_config_inventory.sh"
echo
echo "Sinh luc: $(date -u '+%Y-%m-%d %H:%M UTC') · commit \`$(git rev-parse --short HEAD)\`"
echo
echo "> KHONG go tay file nay. Chay lai script sau moi lan doi cau hinh."
echo
echo '## 1. Key ma code THUC SU doc tu config.properties'
echo
echo '| key | doc o dau |'
echo '|---|---|'
keys_read | while read -r k; do
  w=$(grep -rn --include=*.java "\"$k\"" src/main/ | head -1 | sed 's|src/main/java/com/binance/||' | cut -c1-90)
  echo "| \`$k\` | $w |"
done
echo
for f in config.properties configs/sim_dev.properties; do
  [ -f "$f" ] || continue
  echo "## 2. \`$f\` — doi chieu"
  echo
  echo '| key | gia tri | trang thai |'
  echo '|---|---|---|'
  keys_read > /tmp/_kr.txt
  file_keys "$f" | while read -r k; do
    v=$(grep -E "^$k[[:space:]]*=" "$f" | head -1 | cut -d= -f2-)
    if grep -qx "$k" /tmp/_kr.txt; then echo "| \`$k\` | $v | active |";
    else echo "| \`$k\` | $v | **DEAD — gia tri nay bi BO QUA** |"; fi
  done
  echo
  echo "Key code doc nhung file nay KHONG khai bao (chay bang default hardcode):"
  echo
  comm -23 /tmp/_kr.txt <(file_keys "$f") | sed 's/^/- `/;s/$/`/'
  echo
done
echo '## 3. Tham so giao dich doc qua cong Cfg (env hoac TRADING_PROFILE)'
echo
grep -rhoE 'Cfg\.get(Or)?\("[A-Za-z0-9_.]+"' src/main/ --include=*.java \
  | grep -oE '"[A-Za-z0-9_.]+' | tr -d '"' | sort -u | sed 's/^/- `/;s/$/`/'
echo
echo '## 4. Kiem tra cong Cfg'
echo
echo '```'
bash tools/check_cfg_gateway.sh 2>&1
echo '```'
} > $OUT
echo "da sinh $OUT ($(wc -l < $OUT) dong)"
