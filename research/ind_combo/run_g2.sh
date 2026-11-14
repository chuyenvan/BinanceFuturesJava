:
# IND_COMBO P0: chay ind_g2 tuan tu 8 seed qua flock + guard, nice/ionice, MemoryMax 3G
cd ~/claude_master/ind1114
exec 9>~/claude_master/locks/oracle_heavy.lock
flock 9
for s in S42 S7 S13 S21 S99 S123 S777 S2024; do
  if pgrep -af '[o]wner_deploy|[d]eploy_ingest|[d]eploy_v12|[u]pdate_watchdog' >/dev/null; then echo "DEPLOY dang chay -> DUNG"; exit 3; fi
  av=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo); fr=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
  echo "$s memavail ${av}MB disk ${fr}G"
  if [ "$av" -lt 4096 ] || [ "$fr" -lt 15 ]; then echo "THIEU RAM/DIA -> DUNG"; exit 4; fi
  /usr/bin/time -f "$s cpu_user %U sys %S maxrss_kb %M" systemd-run --user --scope -q -p MemoryMax=3G nice -n 19 ionice -c3 python3 ind_g2.py $s || { echo "FAIL $s"; exit 5; }
done
echo G2_ALL_DONE
