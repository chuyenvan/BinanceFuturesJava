#!/usr/bin/env bash
# build_hotfix_jar.sh - [HOTFIX-KS 2026-11-19] tai tao jar hotfix = jar live r4u3fin2 + DUY NHAT KillSwitchEngine.class (commit 4fdda6f8).
#   KHONG doc / chep file key (PrivateConfig.java): moi entry khac cua jar live chep NGUYEN BYTE NEN (patch_jar.py).
#   Dau vao: KSE_CLASS = KillSwitchEngine.class bien dich bang mvn (LIVE_IS_SHADOW_HOST=true) o worktree hotfix (stub PrivateConfig -
#   KSE khong tham chieu PrivateConfig; 928/929 class com/binance/** bien dich lai giong HET byte jar live, chi KSE khac).
#   bash build_hotfix_jar.sh <KSE_CLASS>   => in md5 jar moi + bang so sanh tung entry
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd)
OLD=${OLD:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3fin2}
OLD_MD5=641803565297d4065d90245e04a00f11
KSE_MD5=d560bd8d1e55bcd4d82e6156e45b8f04
NEW=${NEW:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3fin2_hotfixks}
E=com/binance/chuyennd/ops/KillSwitchEngine.class
[ "$(md5sum < "$OLD" | cut -c1-32)" = "$OLD_MD5" ] || { echo "jar cu md5 sai"; exit 1; }
[ "$(md5sum < "$1" | cut -c1-32)" = "$KSE_MD5" ] || { echo "KSE class md5 khac $KSE_MD5"; exit 1; }
[ ! -e "$NEW" ] || { echo "da co $NEW - khong ghi de"; exit 1; }
umask 077
python3 -I "$H/patch_jar.py" "$OLD" "$NEW" "$E" "$1"
chmod 600 "$NEW"
echo "NEW=$NEW md5=$(md5sum < "$NEW" | cut -c1-32)"
python3 -I "$H/cmp_jar.py" "$OLD" "$NEW"
