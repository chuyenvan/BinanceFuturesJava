#!/bin/bash
# SYMLIFE (2026-10-25) — SOAN SAN, CHUA CHAY. Bo POWR, MDT khoi DIED_SYMBOLS tren 242 (ca 2 dang TRADING tren Binance).
# Chay tu Oracle:  bash ~/claude_master/vz_e1_wt/research/symlife/owner_died_fix_242.sh          (DRY-RUN: chi bao se doi gi)
#                  bash ~/claude_master/vz_e1_wt/research/symlife/owner_died_fix_242.sh --apply  (sua that, co backup)
# KHONG restart. Hieu luc chi sau restart CA collector (TickerIngestor/Funding/OI) LAN app trading (Constants static init).
# KHONG chay trong cua so promotion parity (den 2026-11-18) tru khi MASTER duyet — doi universe live so voi harness.
# Chi sua dong ^DIED_SYMBOLS= ; khong in noi dung config (co token).
set -u
APP=${APP_242:-/home/chuyennd/java/v_t_m}          # thu muc app trading (theo pull242_daily.sh); collector: CHUA XAC MINH
S242="ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"
MODE=${1:-dry}
$S242 "bash -s" <<EOF
set -u
for CFG in \$(grep -l '^DIED_SYMBOLS=' $APP/config.properties $APP/*/config.properties 2>/dev/null); do
  L=\$(grep -E '^DIED_SYMBOLS=' "\$CFG")
  N0=\$(echo "\$L" | cut -d= -f2 | tr ',' '\n' | grep -c .)
  HAS=\$(echo "\$L" | cut -d= -f2 | tr ',' '\n' | grep -xE 'POWR|MDT|POWRUSDT|MDTUSDT' | tr '\n' ' ')
  echo "\$CFG: DIED n=\$N0 co_trong_danh_sach=[\$HAS]"
  [ -z "\$HAS" ] && continue
  if [ "$MODE" = "--apply" ]; then
    TS=\$(date +%Y%m%d_%H%M%S); cp -p "\$CFG" "\$CFG.bak_symlife_\$TS" || { echo FAIL_BACKUP; exit 1; }
    NEW=\$(echo "\$L" | cut -d= -f2 | tr ',' '\n' | grep -vxE 'POWR|MDT|POWRUSDT|MDTUSDT' | grep . | paste -sd, -)
    sed -i "s|^DIED_SYMBOLS=.*|DIED_SYMBOLS=\$NEW|" "\$CFG"
    N1=\$(grep -E '^DIED_SYMBOLS=' "\$CFG" | cut -d= -f2 | tr ',' '\n' | grep -c .)
    echo "  DA SUA: n \$N0 -> \$N1 (backup \$CFG.bak_symlife_\$TS). Can restart collector + app de co hieu luc."
  else
    echo "  DRY-RUN: se bo [\$HAS]. Chay lai voi --apply de sua."
  fi
done
EOF
