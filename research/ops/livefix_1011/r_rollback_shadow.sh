#!/bin/bash
# ROLLBACK shadow [Oracle]: r_rollback_shadow.sh <c3|c3b>  — jar + buffer tu .bak_livefix_<TS> (TS trong run/livefix_1011.ts).
case $1 in c3) U=shadow-c3; A=/home/ubuntu/shadow_c3/app;; c3b) U=shadow-c3b; A=/home/ubuntu/shadow_c3b/app;; *) echo "usage: c3|c3b"; exit 2;; esac
TS=$(cat $A/run/livefix_1011.ts) || exit 2
J=$A/target/binance-java-sdk-1.2.4.jar; BF=$A/run/gate_ratio_live.bin
sudo systemctl stop $U; for i in $(seq 1 30); do [ "$(systemctl is-active $U)" != active ] && break; sleep 2; done
cp -p $J.bak_livefix_$TS $J && cp -p $BF.bak_livefix_$TS $BF
echo "$U jar=$(sha256sum < $J | cut -c1-16) (ky vong b0f23b7d)"
sudo systemctl start $U; sleep 5; echo "$U $(systemctl is-active $U)"
