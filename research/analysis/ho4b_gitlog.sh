#!/bin/bash
# HO4-P0b Q1(ii): commit cham cac class exporter/feature tu 2026-07-25 toi nay (ngay, hash, file).
cd /home/ubuntu/src/BinanceFuturesJava
B=src/main/java/com/binance/chuyennd
F="$B/ai_ml/features/export/gate/ExportGateDataset.java
$B/ai_ml/features/export/fundingv2/ExportFeaturesForPythonTool.java
$B/ai_ml/features/export/ExportFundingLabel.java
$B/tradecore/MarketBigChangeDetector.java
$B/research/ExportMarketData2File.java
$B/aerospike/DataManagerAerospikeFloatSim.java"
for f in $F; do echo "== $f"; git log --since=2026-07-25 --format='%h %ad %s' --date=format:'%m-%d %H:%M' -- $f | head -20; done
for pat in ComprehensiveMarketFeatureExtractor HistoryManager CoinRankManager FundingFeeManager FundingFeatureExtractorV2 SymbolLifecycleManager MarketFeatures; do
  p=$(git ls-files | grep "/$pat.java" | head -3)
  for f in $p; do echo "== $f"; git log --since=2026-07-25 --format='%h %ad %s' --date=format:'%m-%d %H:%M' -- $f | head -20; done
done
