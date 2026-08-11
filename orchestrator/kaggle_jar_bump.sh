#!/usr/bin/env bash
# CE NODE (local): build jar SANITIZED tu HEAD -> stage -> bump dataset Kaggle (java-run-lc).
# Ly do co nut nay: jar tren dataset Kaggle la SNAPSHOT co dinh; moi lan HEAD doi ma muon fanout
# Kaggle deu phai lam lai dung chuoi nay (>=2 lan => R1 CE-FIRST bat buoc thanh nut).
# Dung: kaggle_jar_bump.sh "<message>" [dataset_slug] [stage_dir]
# In: JAR_BUMP_OK md5=... size=...   |  loi -> SANITIZE_FAIL / BUILD_FAIL / SECRET_LEAK / UPLOAD_FAIL
# AN TOAN: PrivateConfig.java duoc backup + RESTORE bang trap EXIT; KHONG bao gio echo gia tri secret.
set -euo pipefail

MSG="${1:-rebuild HEAD}"
SLUG="${2:-chuyendinh/java-run-lc}"
STAGE="${3:-/c/Users/pc/java-run-lc-stage}"
REPO="${CE_REPO:-/e/educa/source/github/20260415/BinanceFuturesJava}"
JAVA_HOME_DIR="${CE_JAVA_HOME:-/c/Users/pc/.jdks/corretto-17.0.9}"
MVN="${CE_MVN:-/c/Users/pc/bin/mvn}"
KAGGLE="${CE_KAGGLE_LOCAL:-/d/claudedata/kaggle-clean-env/Scripts/kaggle.exe}"
JAR_NAME="${CE_KAGGLE_JAR_NAME:-binance-java-sdk-1.2.4-shaded.jar}"
PC="$REPO/src/main/java/com/binance/chuyennd/config/PrivateConfig.java"

[ -f "$PC" ] || { echo "SANITIZE_FAIL: khong thay PrivateConfig.java"; exit 2; }
[ -x "$KAGGLE" ] || { echo "UPLOAD_FAIL: khong thay kaggle CLI tai $KAGGLE"; exit 5; }

BAK="$(mktemp)"; chmod 600 "$BAK"; cp "$PC" "$BAK"
cleanup() { cp "$BAK" "$PC"; rm -f "$BAK"; }
trap cleanup EXIT

# 1) SANITIZE (thay gia tri bang placeholder, khong in ra)
sed -i 's/\(String API_KEY *= *\)"[^"]*"/\1"SANITIZED_API_KEY"/' "$PC"
sed -i 's/\(String SECRET_KEY *= *\)"[^"]*"/\1"SANITIZED_SECRET_KEY"/' "$PC"
grep -q 'SANITIZED_API_KEY' "$PC" || { echo "SANITIZE_FAIL: API_KEY khong thay the duoc"; exit 2; }
grep -q 'SANITIZED_SECRET_KEY' "$PC" || { echo "SANITIZE_FAIL: SECRET_KEY khong thay the duoc"; exit 2; }
echo "[jar_bump] sanitize OK (placeholder SANITIZED_*)"

# 2) BUILD (CE_SKIP_BUILD=1 -> dung lai jar da co trong target, chi re-stage + re-upload)
cd "$REPO"
if [ "${CE_SKIP_BUILD:-0}" = "1" ]; then
  echo "[jar_bump] CE_SKIP_BUILD=1 -> bo qua mvn package"
else
  echo "[jar_bump] mvn package (skipTests) ..."
  JAVA_HOME="$JAVA_HOME_DIR" "$MVN" -q -DskipTests package
fi
JAR="$(ls -1 target/binance-java-sdk-*.jar 2>/dev/null | grep -v -- '-original' | head -1)"
[ -n "${JAR:-}" ] || { echo "BUILD_FAIL: khong tim thay target jar"; exit 3; }
echo "[jar_bump] jar=$JAR"

# 3) GATE SECRET: jar KHONG duoc chua chuoi secret live (chi in SO LUONG match, khong in noi dung)
PAT="$(mktemp)"; chmod 600 "$PAT"
sed -n 's/.*String API_KEY *= *"\([^"]*\)".*/\1/p'    "$BAK" >  "$PAT"
sed -n 's/.*String SECRET_KEY *= *"\([^"]*\)".*/\1/p' "$BAK" >> "$PAT"
sed -i '/^$/d;/^SANITIZED_/d' "$PAT"
HITS=0
if [ -s "$PAT" ]; then HITS="$(grep -a -c -F -f "$PAT" "$JAR" || true)"; fi
rm -f "$PAT"
if [ "${HITS:-0}" != "0" ]; then
  echo "SECRET_LEAK: jar con khop secret live ($HITS) -> DUNG, KHONG upload"; exit 4
fi
echo "[jar_bump] secret gate PASS (0 match secret live)"

# 4) STAGE (kernel glob 'binance-java-sdk-*.jar' => chi duoc DUNG 1 jar trong stage)
mkdir -p "$STAGE"
find "$STAGE" -maxdepth 1 -name 'binance-java-sdk-*.jar' -delete
cp "$JAR" "$STAGE/$JAR_NAME"
MD5="$(md5sum "$STAGE/$JAR_NAME" | awk '{print $1}')"
SIZE="$(stat -c%s "$STAGE/$JAR_NAME")"
echo "[jar_bump] staged $JAR_NAME md5=$MD5 size=$SIZE"

# 4b) INVARIANT config.properties cho Kaggle (bug 2026-07-30: stage thieu 2 key nay ->
#     Configs.TICKER_SOURCE=null -> WfoWorker FAILED 16/16 "Thieu/sai TICKER_SOURCE").
#     Kaggle KHONG co Aerospike local => ticker phai doc file; moi read Aerospike khac di 226 (network).
CFG="$STAGE/config.properties"
[ -f "$CFG" ] || { echo "UPLOAD_FAIL: thieu $CFG"; exit 7; }
ensure_kv() { # ensure_kv <file> <key> <value>
  if grep -q "^$2=" "$1"; then sed -i "s|^$2=.*|$2=$3|" "$1"; else printf '%s=%s\n' "$2" "$3" >> "$1"; fi
}
ensure_kv "$CFG" TICKER_SOURCE "${CE_KAGGLE_TICKER_SOURCE:-file}"
ensure_kv "$CFG" AEROSPIKE_READ_CLUSTER "${CE_KAGGLE_READ_CLUSTER:-226}"
echo "[jar_bump] config.properties: $(grep -e '^TICKER_SOURCE=' -e '^AEROSPIKE_READ_CLUSTER=' "$CFG" | tr '\n' ' ')"

# 5) UPLOAD version moi
cd "$STAGE"
"$KAGGLE" datasets version -p . -m "$MSG" || { echo "UPLOAD_FAIL: kaggle datasets version rc!=0"; exit 6; }
"$KAGGLE" datasets status "$SLUG" || true
echo "JAR_BUMP_OK md5=$MD5 size=$SIZE slug=$SLUG msg=$MSG"
