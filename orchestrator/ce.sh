#!/usr/bin/env bash
# CE button wrapper (bash / git-bash) — TUONG DUONG ce.cmd, dung khi shell goi la bash
# (ce.cmd LF-only nen cmd.exe misparse trong mot so host: bao "'M' is not recognized").
# Dung: bash ce.sh wfo_status | bash ce.sh wfo_run /path/ds jar 30 42 2 tag | bash ce.sh --sync bg_selftest
set -uo pipefail
KEY=${CE_SSH_KEY:-/c/Users/pc/.ssh/id_rsa_chuyennd}
HOST=${CE_HOST:-ubuntu@161.118.212.3}
TOOL=${CE_TOOL:-/home/ubuntu/claudedata/.run/mcp_tools-v3.py}
ENVS="CE_RUN_DIR=/home/ubuntu/claudedata/.run/mcp_ce CE_LOCKS_DIR=/home/ubuntu/claudedata/.run/mcp_ce/locks"
HERE="$(cd "$(dirname "$0")" && pwd)"

# NUT LOCAL (chay tren may nay, KHONG qua ssh)
case "${1:-}" in
  build_deploy)     shift; exec bash "$HERE/build_deploy.sh" "$@" ;;
  kaggle_jar_bump)  shift; exec bash "$HERE/kaggle_jar_bump.sh" "$@" ;;
  # verify_stage — GATE BAT BUOC TRUOC FANOUT (jar stale 2 lan lien tiep 2026-08-01,
  #   ca 2 lan deu im lang va cho ra ket qua GIA). Soi jar DA STAGE tren Oracle, khong
  #   phai jar local. Dung: ce.sh verify_stage [remote_jar] [profile...]
  #   vd: ce.sh verify_stage /home/ubuntu/java/simulator/gatecount.jar dca_grid exit
  verify_stage)
    shift
    VS_JAR="${1:-/home/ubuntu/java/simulator/gatecount.jar}"; [ $# -gt 0 ] && shift
    VS_ARGS=""
    if [ $# -eq 0 ]; then VS_ARGS="--profile base"; else
      for p in "$@"; do VS_ARGS="$VS_ARGS --profile $p"; done
    fi
    scp -o StrictHostKeyChecking=no -i "$KEY" "$HERE/tools/verify_stage.py" \
        "$HOST:/home/ubuntu/claudedata/.run/verify_stage.py" >/dev/null || exit 1
    exec ssh -o StrictHostKeyChecking=no -i "$KEY" "$HOST" \
        "python3 /home/ubuntu/claudedata/.run/verify_stage.py $VS_JAR $VS_ARGS"
    ;;
esac

if [ "${1:-}" = "--sync" ]; then
  scp -o StrictHostKeyChecking=no -i "$KEY" "$HERE/mcp_tools-v3.py" "$HOST:$TOOL" || exit 1
  echo SYNCED
  shift
fi

exec ssh -o StrictHostKeyChecking=no -i "$KEY" "$HOST" "$ENVS python3 $TOOL $*"
