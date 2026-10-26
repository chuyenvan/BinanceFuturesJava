# PREREG_NUP3B — ADDENDUM TECH (2026-10-27)

Prereg goc `docs/prereg/PREREG_NUP3B.md` (MASTER, 9b49f7a9, sha256 `c544278c…`). Addendum chi ghi cach hien thuc va cho phai
dien giai ky thuat. KHONG doi arm, s, nguong, seed. Viet + commit TRUOC kernel do dau tien; chua co so nao cua NUP3b.

Code: branch `research/nup3-sleeve`, commit **6d0b4802** (tren c80d87c2). Jar (PrivateConfig STUB) sha256
`8aba4090bd39ec45853df68d5b5538d6c3edd324aba20285bfb875ad7396e676`, `jar_sec_check` ok.
Duong dan tuong doi `src/main/java/com/binance/chuyennd/`; `Sim` = `research/SimulatorMarketLevelTicker1MStopLoss.java`.

## B1. Key `BASE_SKIP_SLEEVE_SYMBOLS` (mac dinh false) — `tradecore/Configs.java:194`, `:956`
**Dien giai E1.** "So nen KHONG mo cum moi tren symbol sleeve dang giu" duoc hien thuc nhu one-way live: symbol sleeve dang
giu duoc coi la **"dang giu"** o DUNG cac diem so nen loai symbol dang giu khi chon ung vien:
- Leg PREDICT (selector top-K): bo qua symbol TRUOC `createOrder`, giong `isSymbolRunning` (`Sim:444-446`). He qua: ung vien do
  KHONG vao gate nen, KHONG nap r vao buffer, KHONG tinh quota (dung nhu symbol dang giu). Rank top-K van dem tren toan pool
  (cap-then-skip), khong lay them coin thay the.
- Leg BIG_DOWN / market-signal: symbol sleeve dang giu duoc them vao `symbolLocked` (`Sim:348-349`, helper `Sim:1920`), nen
  `getTopSymbolArray` chon coin khac thay vao, dung nhu voi symbol nen dang giu.
- DCA cua so nen chi tren cum nen san co => khong bi anh huong.
- Lop chan cuoi trong `createOrder` (`Sim:1999-2004`): neu van co lenh nen mo cum moi tren symbol sleeve dang giu => bo, dem
  `base_skip_backstop` (ky vong 0).
- Luat chi ap cho so NEN (khong trong pha sleeve); symbol nen DA giu thi khong lien quan (khong phai cum moi).
- Bat co ma `SLEEVE_ENABLED=false` => fail-fast (`Sim:1415-1417`).
- TAT: `baseSkipSleeveSym` tra false ngay, khong ghi gi (`Sim:1906`) => byte-identical (cong G-OFF).

## B2. Do luong cho S1x (prereg §4 "Bao them", chi mo ta) — `storage/sleeve_summary.json`
- `base_skip_pred_cand_ticks`, `base_skip_locked_ticks`: so luot (tick x symbol) bi bo/khoa.
- `base_skip_distinct_sleeve_clusters`: so cum sleeve da chan nen it nhat 1 lan (xap xi "so cum nen bi bo", moi cum sleeve tinh 1).
- Log `BASE-SKIP-SLEEVE sid tMs lvl sleeveT0` (1 dong / cum sleeve, lan dau) => ghep voi printDone B0 cung seed de tinh so cum nen
  bi bo va PnL B0 cua chung (chi phi co hoi) o buoc cham.
- `overlap_base_opens_sleeve_sym` voi S1x phai = 0.

## B3. Arm va jar
- S0b = V0 + `SLEEVE_SIZE_MULT=0.525`; S1b = V1 + `0.574`; S1x = S1b + `BASE_SKIP_SLEEVE_SYMBOLS=true`. Cac key sleeve khac giu
  nhu NUP3 (pct 0.99985, U_S_MAX 0.35, burst 10/60').
- **Lech ky thuat L2 — ten dataset jar.** Prereg ghi "cung jar `sim-jar-nup3-sleeve`". De tranh rui ro kernel lay nham version cu
  khi tao version moi cua dataset do, jar moi upload vao dataset private MOI `sim-jar-nup3b` (sha tren). Ca 3 arm va moi cong
  dung CUNG jar nay (tinh than prereg giu nguyen). Orchestrator kiem `jar_sha256` cua tung run = `8aba4090…`.

## B4. Cong (truoc Pha 1) — `research/nup3/orch3b.py`
- G-OFF B0: `nup3b-goff-a1` (SLEEVE_ENABLED=false) => md5 printDone = `tsx-x14-a1` (`dc62609b…`).
- G-OFF NUP3: `nup3b-offv1-s7` = cau hinh NUP3 V1 (size 1.0) + `BASE_SKIP_SLEEVE_SYMBOLS=false` => md5 = `nup3-v1-s7` jar cu
  b269f96b (`881abeb7…`).
- G-INV: `nup3b-s0b-a1` VA `nup3b-s1b-a1` loc `book=sleeve` => md5 = B0 a1. Hai run nay cung la run Pha 1 (khong chay trung).
- Pha 1 con lai (10 run) chi push khi ca 3 cong PASS. Chi push khi con slot (dem theo dateRun, thay ca kernel OpenClaw NUP2c).
- Prereg §4: equity tu 2021-07 (gom 2021H2), khong niem phong 2021H2.
