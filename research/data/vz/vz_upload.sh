#!/usr/bin/env bash
# B5 - upload a private Kaggle dataset and verify it round-trips.
# Usage: vz_upload.sh <slug> <src_dir> [create|version]
#   slug     dataset id without owner, e.g. vz-pilot-202408  (owner = chuyendinh)
#   src_dir  folder holding the (flat) files to upload + README.md + manifest.csv
# NOTE: kaggle -r skip ignores subdirectories, hence files must be flat.
set -euo pipefail
export KAGGLE_CONFIG_DIR="${KAGGLE_CONFIG_DIR:-$HOME/.kaggle}"

SLUG="$1"; SRC="$2"; MODE="${3:-create}"
OWNER="chuyendinh"
FULL_ID="$OWNER/$SLUG"

cd "$SRC"
cat > dataset-metadata.json <<EOF
{
  "title": "$SLUG",
  "id": "$FULL_ID",
  "licenses": [{"name": "other"}]
}
EOF

echo "[upload] dataset=$FULL_ID mode=$MODE dir=$SRC"
if [ "$MODE" = "version" ]; then
  kaggle datasets version -p "$SRC" -m "$(date -u +%Y-%m-%dT%H:%MZ) VZ upload" -r skip
else
  kaggle datasets create -p "$SRC" -r skip
fi

echo "[verify] remote file list"
kaggle datasets files "$FULL_ID" | tee /tmp/vz_remote_files.txt || true

echo "[verify] download one parquet back and compare sha256"
WORK=$(mktemp -d)
FIRST=$(ls -1 "$SRC"/*.parquet 2>/dev/null | head -n1 || true)
if [ -n "${FIRST:-}" ]; then
  BASE=$(basename "$FIRST")
  kaggle datasets download -d "$FULL_ID" -f "$BASE" -p "$WORK" --unzip 2>/dev/null || \
    kaggle datasets download -d "$FULL_ID" -p "$WORK" --unzip
  LOCAL_SHA=$(sha256sum "$FIRST" | awk '{print $1}')
  GOT=$(find "$WORK" -name "$BASE" | head -n1)
  GOT_SHA=$(sha256sum "$GOT" | awk '{print $1}')
  echo "[verify] $BASE local=$LOCAL_SHA remote=$GOT_SHA"
  if [ "$LOCAL_SHA" = "$GOT_SHA" ]; then echo "[verify] SHA256 MATCH"; else echo "[verify] SHA256 MISMATCH"; exit 1; fi
else
  echo "[verify] no parquet found to round-trip"
fi
rm -rf "$WORK"
echo "[upload] done $FULL_ID"
