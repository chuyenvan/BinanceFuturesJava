# DATA PREFLIGHT REPORT — 2026-07-11 22:41:03

VERDICT: FAIL ⛔

BLOCK-fail: 1 · WARN: 1 · infra-error: 0

| Check | Nhóm | Kết quả | Mức | Số đo / Lý do |
|---|---|---|---|---|
| A1 | A | FAIL | BLOCK | Pred thieu giai doan (coverage gap): [gate: 30 thang < nguong 0 (median=0, span=DEFAULT): [202101=0, 202102=0, 202103=0, 202104=0, 202105=0, 202106=0, 202107=0, 202108=0, 202109=0, 202110=0, 202111=0, 202112=0, 202201=0, 202202=0, 202203=0, 202204=0, 202205=0, 202206=0, 202207=0, 202208=0, 202209=0, 202210=0, 202211=0, 202212=0, 202301=0, 202302=0, 202303=0, 202304=0, 202305=0, 202306=0]] {gate.ref=ai_pred_market_gate_wfo, gate.totalRecords=0, gate.monthsWithData=0, gate.monthsExpected=67, gate.monthsZeroInSpan=67, gate.median=0, gate.threshold=0, gate.defaultedSpan=true, gate.gapMonths=[202101=0, 202102=0, 202103=0, 202104=0, 202105=0, 202106=0, 202107=0, 202108=0, 202109=0, 202110=0, 202111=0, 202112=0, 202201=0, 202202=0, 202203=0, 202204=0, 202205=0, 202206=0, 202207=0, 202208=0, 202209=0, 202210=0, 202211=0, 202212=0, 202301=0, 202302=0, 202303=0, 202304=0, 202305=0, 202306=0], funding.skipped=khong co WFO_FUNDING_PRED_DIR (bo qua nguon funding)} |
| A4 | A | PASS | BLOCK | Du 17 fold WFO (= expectedFolds). {totalJobs=17, strategyJobs=17, distinctFolds=17, expectedFolds=17, folds=[strat-w00, strat-w01, strat-w02, strat-w03, strat-w04, strat-w05, strat-w06, strat-w07, strat-w08, strat-w09, strat-w10, strat-w11, strat-w12, strat-w13, strat-w14, strat-w15, strat-w16]} |
| A5 | A | PASS | BLOCK | Universe giữ 180 coin DEAD (>= 72), lifespan hợp lệ. {total=809, live=0, dead=180, expectedMinDead=72, invalidLifespan=0} |
| F2 | F | PASS | BLOCK | CONFIG_VERSION = 'v12' khớp baseline hằng số. TODO: thiếu env EXPECTED_CONFIG_VERSION — chưa kiểm được drift so pre-register/stamp. {actual=v12, expected=v12, expectedSource=baseline-constant(TODO)} |
| D1 | D | FAIL | WARN | Funding lệch lưới UTC: 36228 mốc giờ LẺ + 0 mốc phút != 0 (chữ ký GMT+7/offset). Giờ vi phạm nhiều nhất: {01h=3064, 02h=3191, 03h=3044, 05h=3041, 06h=3153, 07h=2995, 09h=3021, 10h=3163, 11h=3005, 13h=3022, 14h=3155, 15h=2995, 17h=3021, 18h=3148, 19h=2995, 21h=3018, 22h=3155, 23h=3007}. Kỳ vọng chốt tại 00/08/16h (hoặc lưới 4h) UTC. {symbols=754, settlements=2053547, onGrid4hUtc=1998354, stdGrid8hUtc=1377244, oddHour=36228, nonZeroMinute=0, decodeErrors=0, topOffendingHours={01h=3064, 02h=3191, 03h=3044, 05h=3041, 06h=3153, 07h=2995, 09h=3021, 10h=3163, 11h=3005, 13h=3022, 14h=3155, 15h=2995, 17h=3021, 18h=3148, 19h=2995, 21h=3018, 22h=3155, 23h=3007}} |
| D3 | D | PASS | BLOCK | Guard look-ahead nội nến BẬT (BLOCK_INTRABAR_LOOKAHEAD = true). {BLOCK_INTRABAR_LOOKAHEAD=true, expected=true} |
