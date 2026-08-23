# Phase 1 — NỀN DỮ LIỆU: XONG (18 fold) — 2026-08-13

## Kết quả
- **Features 5m: 22 quý** `2021Q1..2026Q2` (`features_<q>.t1c.gz`, TRUE 5m grid `ts%300000==0`,
  FF_GRID_MIN=5, FF_UNFILTERED=1, TICKER_SOURCE=aerospike). 2025Q3=12.2M dòng (OOM ở 1m đã giải quyết),
  2026Q2=504MB. 2025H2 lấp đủ.
- **Labels 5m: 22 quý** `2021Q1..2026Q2` (`funding_label_<q>.pb`, LABEL_STEP_MIN=5, horizon short
  4h/12h/24h/72h, horizonIdx=0=4h là cái selector dùng). Base 128M dòng + relabel 2026Q1/Q2 (~33.6M).
- **Join feature↔label** (key=ts*100000+symId, ts_align 5m=100%, mapmiss=0):
  2023Q1=99.64%, 2025Q3=99.66%, **2026Q1=99.34%**, **2026Q2=90.97%**.
  (Q2 thấp hơn: features UNFILTERED chứa thêm coin ngoài label-universe gated isAlt/isAlive — vẫn dùng tốt cho WFO, selector train trên phần joined.)
- **2 Kaggle dataset** (v2): `chuyendinh/funding-tool1-5m` (22 features + manifest) + `chuyendinh/funding-label-5m` (22 labels + meta). Manifest `wfo_ds_LF_20260813_5m_h4h_v1`: leakFreeFrom=20230101, gridMs=300000, horizonIdx=0, md5/file, nCleanOOSFolds=18.

## Số fold: 18 (KHÔNG phải 17)
`FIRST_CUTOFF=20220101` → **18 fold OOS sạch** `2022Q1..2026Q2`, fold cuối `20260401_to_20260701`.
Report Phase 3 sẽ kèm full-18 VÀ subset 2023+ (train sạch ≥2yr); fold 2022 train chỉ ~1yr (2021) — ghi rõ.
2026Q3 partial (`20260701_to_20261001`, Jul1–Aug13) có sẵn ở `label_5m_2026fix` nhưng **KHÔNG** đưa vào canonical (user skip, ít data).

## ROOT CAUSE đã gỡ: 2026Q2 label rỗng KHÔNG do thiếu data
- Ban đầu label chỉ ra tới 2026Q1 và 2026Q2 emit **0 dòng** dù local có kline Q2. Đào ra:
  **`symbol_lifecycle` local STALE** — mọi coin `last=1772409540000 (~2026-03-02)` dù status=LIVE
  (lifecycle build lần cuối ~Mar2). Label gate `isAlive(t)=t≤last` loại sạch anchor sau Mar2
  → 2026Q1 thiếu đoạn Mar2→Apr1, 2026Q2 rỗng. (Feature export KHÔNG dính vì FF_UNFILTERED bỏ gate.)
- **Fix:** `fix_lifecycle.py` set `last=1786579200000 (2026-08-13)` cho **626 coin LIVE** (72 coin non-live giữ nguyên → coin đã ngừng trade không có kline nên không sinh anchor giả). Relabel 2026Q1+Q2 → Q2 emit 19.8M dòng.
- Các quý ≤2025 KHÔNG ảnh hưởng (coin alive suốt, quarter end < Mar2).

## Sync data từ production .242
- `.242` = **103.157.218.242:3222 ns=ticker** (Aerospike production, có kline tới hôm nay).
  Reachable từ Oracle. SSH key Oracle KHÔNG vào được .242 (chỉ Aerospike port).
- `sync_kline_242.py` (threaded per-key get): copy `kline_1m_opt` `20260702..20260813` (61.393 key, miss 527 = phút tương lai của hôm nay, 0 lỗi) từ 242 ns=ticker → local ns=test. Local kline giờ tới 20260813.
- `symbol_lifecycle` KHÔNG có ở 242 ns=ticker (err record-not-found) → phải fix local trực tiếp (như trên).

## Sự cố + bài học
- Reboot Oracle giữa chừng: Aerospike disk-persisted `/home/ubuntu/aerospike-data/test.dat` tự hồi ~13min, data nguyên.
- **RAM:** TỔNG 23G. KHÔNG chồng label Xmx18g + join python (~2.5G) — đã gây thrash+crash 1 lần, sau đó serialize nghiêm.
- REPL PowerShell: TRÁNH `python3 -c` đa dòng trong OrBash (làm PS kẹt `>>`) — ghi .py bằng cat heredoc rồi chạy.
- CopyAerospikeSet = full-set scan (không range) → dùng targeted Python copy cho delta, nhẹ cho production.

## Tiếp theo
- **Phase 2**: rebuild jar 3 flag `WFO_VERDICT_NO_WFE + WFO_FREEZE_GENOME + WFO_STATE_SET`, test 13/13 byte-identical khi flag OFF.
- **Phase 3**: train 8 selector native (5m/15m × retEnd{0.008,0.015,0.02,0.03}), **FIRST_CUTOFF=20220101 → 18 fold**, fanout ×moveSL{0.03,0.05}=16 run; report full-18 + subset 2023+.
- **Phase 5 gate** (đã rà, `claude/wfo_gate_recheck_2026-08-13.md`): gate yếu + mù đuôi → thêm predictor đuôi WF-clean dùng label `maxAdv/maxFav`.
- **Deploy production** (user muốn sau WFO): CHƯA làm — cần hỏi rõ deploy config nào lên box nào (side-effect thật).
