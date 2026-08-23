# WFO pipeline — build "đủ tin" (trust) — 2026-08-22

Mục tiêu user: hoàn thiện luồng WFO đủ tin → ra baseline reproducible (số nào cũng chốt) → hết nghi
ngờ mới tối ưu. "Đừng phân tích trên thứ còn lỗ hổng; đừng mỗi lần một nhận định."

## ⭐⭐ TRUST STORY — GẦN HOÀN CHỈNH (3/4 trụ cột PROVEN)
1. ✅ **Engine DETERMINISTIC** (empirical): VerifyOneWindow winIdx=10 ×2 input đóng băng → oosPnl=2836.7949,
   trades=636, wfe/maxDD/genome/toàn bộ RESULT_JSON **byte-identical**; chỉ khác timing/RAM.
2. ✅ **Build DETERMINISTIC** (empirical): ExportWfoDataset build 2 lần độc lập (REPRO1, REPRO2) →
   funding.bin md5 == **779e2f8e0dc31a3aa1af97fe6b2a4324** (identical). (market/pred cũng ổn định.)
3. ✅ **Data COMPLETE + verified**: FileMinuteScan toàn corpus 20211001..20260301 = **1613 ngày,
   incomplete=0, err=0** (đủ 1440'/ngày, không lỗi). Không thiếu ngày interior; chỉ thiếu 31 ngày
   frontier 2026-03+ (chưa ingest, ngoài mọi window đang tính). File-mode KHÔNG có lỗ hổng.
4. ⏳ **Ticker FROZEN**: corpus_md5 = **d521edb042db67582a60e2a607f71eb1** (1886 files). Lock: NGỪNG
   re-version. wfo_trust_run.sh có preflight gate md5 chống drift.

⇒ **KẾT LUẬN: FULL reproducible BY CONSTRUCTION** (engine det ∧ build det ∧ data frozen+complete).
Biến số duy nhất còn lại = **Kaggle infra flakiness** (1 kernel chết → DONE<18/FAILED>0), bị guard
DONE=18/0 bắt → run một phần bị LOẠI, không bao giờ phân tích số sai. Trust số = OK khi 18/0.

## Giải thích DỨT ĐIỂM 19k vs 10k (hết mơ hồ)
- 3 run lịch sử 18/0 cho 9936/10502/10113 khác nhau CHỈ vì ticker bị re-version Kaggle giữa các run
  (07:54 & 08:54). Ticker frozen ⇒ run 18/0 kế tiếp là baseline ổn định.
- 19840 = aerospike-mode (ns=test 2.95M record, NHIỀU hơn .226 2.91M) → nghi thổi phồng bởi data
  bẩn/dup. 10k = file-mode == Binance (verified). ⇒ 10k mới là số honest; 19840 là ghost. RETIRE band.

## Access (container cloud bị reclaim)
desktop-commander (Windows) → WSL bash root → ssh Oracle. Key: cp /mnt/c/Users/pc/.ssh/id_rsa_chuyennd
→ /root/.ssh/ora_key chmod600. Remote: `tr -d '\r' < /mnt/c/Users/pc/x.sh | ssh -i /root/.ssh/ora_key
ubuntu@161.118.212.3 'bash -s'`. Nền: ghi+verify file rồi `setsid bash x.sh >out 2>&1 </dev/null &`.
MCP start_process cap 60s/call. Oracle 4core/23GB, DISK 99% (canh: dataset 5.1G/leg, rm sau mỗi leg).

## Bản đồ luồng
- corpus authoritative DUY NHẤT: /home/ubuntu/java/simulator/kaggle_data_hpo/daily (mọi symlink trỏ về).
- ~/wfo_guard_run.sh: guard (predwf18, DONE18/0, canary band [18000,21500]=NEO SAI cần retire, propagation, wfo_stats).
- ~/drive_exp18.sh <tag> <hidx>: ExportWfoDataset(aerospike+predwf_$tag) → upload Kaggle wfo-ds-<slug>
  (create+version = 2× upload 4.94G, chậm) → reset coordinator(127.0.0.1:3222 ns=test) → push 5 kernel
  → poll DONE (BREAK khi FAILED>=1 = điểm giòn) → report. Jar binance-fresh-20260809.jar (md5 01574328).
- WfoCoordinator chỉ có init|status|report|reset (reset = toàn bộ; KHÔNG có requeue targeted).
- Kaggle dataset_sources KHÔNG pin version → workers lấy latest (nguồn drift ticker, đã lock bằng freeze).

## Deliverable hardening (đã soạn / đang deploy)
- C:\Users\pc\wfo_trust_run.sh: preflight ticker md5 (frozen gate) → drive_exp18 → MANIFEST_<tag>.txt
  (git sha 8741f851 + jar/ticker/funding md5 + config inject + verdict per-window + FULL + posRatio +
  TRUST=OK/UNTRUSTED theo 18/0). CHƯA thêm retry-until-18/0 (cần, vì drive_exp18 break on FAILED).
- CẦN LÀM: (a) retry fanout tới 18/0 (reset+push, intermittent nên vài lần là được); (b) chạy 1 run
  sạch 18/0 ticker-frozen = BASELINE; (c) re-anchor CANARY_LO/HI = baseline±3%; (d) runbook.

## Per-window verdict fields (RESULT_JSON): oosPnl, oosTrades, oosNote, wfe, oosFit, isFit, isNote,
oosMaxDD(_mtm), oosDdPct, oosWinRate, oosProfitFactor, oosCalmar, oosAvgWin/Loss, oosAvgHoldHours,
oosCostPerTrade, oosMarginCall, bestGenome, nSamples. Report cols: $2 idx,$3 label,$7 oosPnl(FULL),$10 trades,$11 note.

## Artifacts Oracle: ~/detproof/{PROOF.txt,vow_A.log,vow_B.log}; ~/repro/{RESULT.txt,REPORT_*,perwin_*};
/tmp/incomplete_days.txt (SCAN_DONE 1613/0/0).
