#!/usr/bin/env bash
# CE NODE (local): build jar (corretto-17, target-11) -> scp len Oracle -> verify md5.
# Wrap dung chuoi build-local/deploy da chot trong memory (KHONG raw ad-hoc moi lan).
# Dung: build_deploy.sh [remote_jar] [host]
#   remote_jar = /home/ubuntu/java/simulator/gatecount.jar (default)
#   host       = ubuntu@161.118.212.3 (default, Oracle VPS)
# In: DEPLOY_OK md5=<hash> -> <remote_jar>  |  loi -> MD5_MISMATCH / build fail (exit!=0)
set -euo pipefail

REMOTE_JAR="${1:-/home/ubuntu/java/simulator/gatecount.jar}"
HOST="${2:-ubuntu@161.118.212.3}"
KEY="${CE_SSH_KEY:-/c/Users/pc/.ssh/id_rsa_chuyennd}"
REPO="${CE_REPO:-/e/educa/source/github/20260415/BinanceFuturesJava}"
JAVA_HOME_DIR="${CE_JAVA_HOME:-/c/Users/pc/.jdks/corretto-17.0.9}"
MVN="${CE_MVN:-/c/Users/pc/bin/mvn}"

cd "$REPO"
echo "[build_deploy] mvn package (skipTests) ..."
JAVA_HOME="$JAVA_HOME_DIR" "$MVN" -q -DskipTests package

# Artifact chinh = shaded uber-jar (shade thay the main). Bo -original, uu tien ban khong hau to.
JAR="$(ls -1 target/binance-java-sdk-*.jar 2>/dev/null | grep -v -- '-original' | grep -v -- '-shaded' | head -1)"
[ -z "$JAR" ] && JAR="$(ls -1 target/binance-java-sdk-*-shaded.jar 2>/dev/null | head -1)"
[ -z "$JAR" ] && { echo "BUILD_FAIL: khong tim thay target jar"; exit 2; }

LMD5="$(md5sum "$JAR" | awk '{print $1}')"
echo "[build_deploy] jar=$JAR local_md5=$LMD5 -> $HOST:$REMOTE_JAR"
scp -o StrictHostKeyChecking=no -i "$KEY" "$JAR" "$HOST:$REMOTE_JAR"
RMD5="$(ssh -o StrictHostKeyChecking=no -i "$KEY" "$HOST" "md5sum $REMOTE_JAR" | awk '{print $1}')"

if [ "$LMD5" = "$RMD5" ]; then
  echo "DEPLOY_OK md5=$LMD5 -> $REMOTE_JAR"
else
  echo "MD5_MISMATCH local=$LMD5 remote=$RMD5"; exit 3
fi
