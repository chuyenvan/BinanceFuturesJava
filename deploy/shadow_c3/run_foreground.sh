#!/bin/bash
# [2026-09-18] Foreground launcher cho systemd shadow-c3.service.
# Source env.sh (SHADOW_NO_PUSH=true, T170 params) roi exec start.sh (start.sh tu exec java foreground).
set -e
cd /home/ubuntu/shadow_c3/app
set -a
. conf/env.sh
set +a
exec bin/start.sh
