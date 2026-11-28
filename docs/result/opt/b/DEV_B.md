# DEV_B - PROGRAM_OPT muc B: nen cho trailing / DCA (cum lenh, OHLC 1m, funding, engine thoat, cong parity)
Thu muc: ~/claude_master/w3/opt/b (code/ work/ out/ test/ logs/). Python /usr/bin/python3; chay voi nice -n 15.
Moi lenh chay tu ~/claude_master/w3/opt/b. Thoi gian = do that 28/11/2026 tren Oracle.
| buoc | lenh | thoi gian | ra |
|---|---|---|---|
| P1 cum | python3 code/clusters.py build && python3 code/clusters.py tzcheck | 25 s | out/clusters_<seed>.parquet x6, clusters_unique.parquet, P1_CHECKS.json, P1_TZCHECK.json |
| P2 plan | python3 code/fetch_ohlc.py plan | 1.7 min | work/ohlc_plan.json |
| P2 tai | nohup nice -n 15 python3 code/fetch_ohlc.py run > logs/fetch_run.log 2>&1 & | 26 min | work/ohlc/<SYM>/<YYYY-MM>.parquet (4603), work/ohlc_done.jsonl |
| P2 kiem | python3 code/fetch_ohlc.py verify | 12 s | out/OHLC_VERIFY.json |
| delist | python3 code/delist_check.py | 10 s | work/delist_months.json (6 thang sau huy niem yet, da xac nhan) |
| funding | python3 code/fetch_aux.py funding | 25.5 min | work/funding/<SYM>/<YYYY-MM>.parquet (4596), work/funding_done.jsonl |
| float32 | python3 code/fetch_aux.py digits | 42 s | out/FLOAT32_SCAN.json |
| P4 parity | python3 code/parity_b.py | ~10 min | out/parity_rows.parquet, PARITY_B.json, PARITY_B.md |
| P5 test | python3 test/test_b.py | 0.5 s | 28 test (KHONG dung `-m unittest test.x`: ten `test` trung goi stdlib) |
| manifest | python3 code/manifest.py | 5 s (cache) | work/ohlc_manifest.csv, work/funding_manifest.csv (so dong + sha256 tung file) |
| P6 sha | bash code/sha_all.sh | <30 s | SHA256SUMS.txt |
Chuoi tu dong vong 2: code/chain_r2.sh (doi tai xong -> verify -> parity -> funding -> digits -> parity -> test -> sha).

## Goi engine cho phan THUC TE (CHUA chay tren cum that - cho audit)
    import sys; sys.path.insert(0, 'code'); import exit_engine_b as E, parity_b as PB, fetch_aux as FA, common_bb as C
    days, hours = C.ext_days('c0s42')                     # tap ngay X14 + 336 h tu prof_run
    p = E.Params(arm=0.07, giveback=1.0, cap=0.03,          # E4d: arm in {.03,.05,.07,.10,.15}, gap=cap in {.02,.03,.05}
                 ts_hours=168, ext_hours=hours, ext_days=days,
                 extra_dca=[(0.20, 1.0)])                   # E5: MOT leg them tai -x% (x in {.10,.20,.30}), qty = leg dau
    b, _ = PB.Bars(PB.delist_months()).get(sym, t0 - 3600000, min(t0 + 45*86400000, C.CUT - 60000))
    res = E.simulate(legs, b, p, tick=E.load_tick_sizes().get(sym + 'USDT'), funding=FA.load_funding(sym), bars_until=t1)
    ret, pnl, cap = E.cluster_return(res, p)                # loi suat tren VON TOI DA da dung; funding engine (Vision)
legs = [(t_utc_ms, entry, qty), ...] lay tu out/clusters_<seed>.parquet (leg_t_utc, leg_entry, leg_qty). O che do phan
thuc te muon bo DCA ledger thi chi truyen leg dau. res: ok, status, reason (trail | time | delist | sl_below), t_exit,
price, n_arm, legs_used, legs_final, funding_engine, diag (n_ratchet, n_defer_ticks, gap_fill, tick_known, n_dca_merges).
res['ok']=False & why='bars_end' => cum con mo cuoi cua so (bao rieng). Khong co phan hoi danh muc (U, slot, skipFull).
Lua chon / dan Java: CHOICES_B.md. Theo doi tai: work/RUN_OHLC.md.
