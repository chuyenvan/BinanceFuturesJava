:
# MACRO_GATE P0: chay 1 lenh python qua flock + guard, nice/ionice, MemoryMax 2500M (cgroup) + RLIMIT_AS backup. Usage: run_job.sh macro.py <mode>
cd ~/claude_master/macro1114
exec 9>~/claude_master/locks/oracle_heavy.lock
flock 9
if pgrep -af '[o]wner_deploy|[d]eploy_ingest|[d]eploy_v12|[u]pdate_watchdog' >/dev/null; then echo "DEPLOY dang chay -> DUNG"; exit 3; fi
av=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo); fr=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
echo "$* memavail ${av}MB disk ${fr}G"
if [ "$av" -lt 4096 ] || [ "$fr" -lt 15 ]; then echo "THIEU RAM/DIA -> DUNG"; exit 4; fi
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 /usr/bin/time -f "$* cpu_user %U sys %S maxrss_kb %M wall %e" systemd-run --user --scope -q -p MemoryMax=2500M -p MemorySwapMax=0 nice -n 19 ionice -c3 python3 "$@" || { echo "FAIL $*"; exit 5; }
echo JOB_DONE "$@"
