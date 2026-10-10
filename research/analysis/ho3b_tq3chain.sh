#!/bin/bash
# HO3b: ticker Q3 tu 242 (chi doc) theo thang -> dataset Kaggle -> xoa .bin.gz local (dia Oracle ~1.5G)
cd /home/ubuntu/claude_master/1003/ho3b
LOG=q3t/chain.log
while pgrep -f 'ho3b_ticker_q3.py q3t/07 ' > /dev/null; do sleep 20; done
run() {  # dir start end slug
  python3 ho3b_ticker_q3.py q3t/$1 $2 $3 242 >> q3t/$1.log 2>&1
  echo "$(date) build $1 rc=$?" >> $LOG
  python3 ho3b_ticker_upload.py q3t/$1 $4 >> q3t/$1.upload.log 2>&1
  echo "$(date) upload $1 rc=$?" >> $LOG
}
run 07 20260701 20260731 wfo-ticker-2026q3a
run 08 20260801 20260831 wfo-ticker-2026q3b
run 09 20260901 20261003 wfo-ticker-2026q3c
echo "$(date) TQ3_DONE" >> $LOG
