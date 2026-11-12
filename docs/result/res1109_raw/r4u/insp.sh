#!/bin/bash
cd ~/claude_master/v12/c3live
md5sum target/binance-java-sdk-1.2.4.jar
# chi in TEN field va DO DAI gia tri, khong in gia tri
grep -nE 'String [A-Za-z_]+ *= *"' src/main/java/com/binance/chuyennd/config/PrivateConfig.java | sed -E 's/"([^"]*)"/<len \1>/' | awk '{match($0,/<len [^>]*>/); v=substr($0,RSTART+5,RLENGTH-6); sub(/<len [^>]*>/, "<len " length(v) (v ~ /STUB|stub|xxx|dummy|test/ ? " STUBLIKE" : "") ">"); print}' | head -12
echo == sec_check
sed -n 1,25p ~/claude_master/nup3_wk/jar_sec_check.py | grep -iE 'usage|argv|jar|stub'
echo == sec_check_tg
sed -n 1,25p ~/claude_master/nup4_fix/jar_sec_check_tg.py | grep -iE 'usage|argv|jar|stub'
grep -rl 'jar_sec_check' ~/claude_master/v12/*.sh ~/claude_master/v12/c3live/ops 2>/dev/null | head -3
