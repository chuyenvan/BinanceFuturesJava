# A1 audit F2B driver v3 (overlay snapshot) - 2026-11-27
Doi tuong: research/r1_s1/f2b_driver.py sha256 ddf97c3cbdffa4dec8835fc5aa99477054603d0563ae3899275012ff097e3a5c
           research/r1_s1/test_f2b_driver.py sha256 bcce884ef566cdd431f10e2a2b6d0eb88ca627162da69d3095da0f7a972d12af
Base: HEAD 3426fc3a; driver HEAD == acbcb9de (commit 76c9f26e, da audit). Diff: +174/-? driver, +216 test, +29 F2B_DEV.

## KET LUAN: PASS-WITH-MINOR (khong co loi CHAN)

## 1. Overlay
- overlay_patch = K3.fpatch(K2.patch(code)) - goi TRUC TIEP ham cua ho5_k2.py (e13a449b) / ho5_k3.py (5539c193) sau khi kiem sha file (ghim).
  => Y HET co che ho5 theo cau truc.
- Bang chung thuc nghiem: run.py NEN S7 do driver sinh vs ~/claude_master/w3/ho5/kern/ho5-a3-rep4-s123/run.py: diff = 2 dong (chi dong CFG).
  CFG khac dung 3 gia tri: tag, pred_ds (gate-abl-seed7 vs gate-sb-s123), want_pred_md5. Tap key trung khit (gom 4 want_* overlay).
- Patch: bo PREFLIGHT TCP 3222; kiem sha mapper_snapshot.tsv 5c436e65 + ho5_mapper_overlay.jar 6143fa75 + funding_snapshot.tsvgz.bin
  fb024c40 (v3) + ho5_funding_overlay.jar 207e7c60, sai -> exit 2; AEROSPIKE_HOST_226 -> 127.0.0.1 trong ban copy WORK;
  java -cp fund_ovl:mapper_ovl:sim.jar; env SYMBOL_MAPPER_SNAPSHOT / FUNDING_SNAPSHOT dat trong run.py; atexit xoa a3_ds/a3_bins;
  result.json them ho5_mapper/ho5_funding. Jar van sim-jar-tsx (jar_ds khong doi; parity so jar_sha256 r1-a3 cc0f9d11).
- Ap cho moi cau hinh: build_f2b goi overlay_patch vo dieu kien; check_f2b (g) doi run.py == overlay_patch(r1-a3 + cfg) + dau overlay
  + khong con PREFLIGHT; dry 6 o x 2 seed: CHECK_OK, dataset_sources co 2 snapshot o ca 12.

## 2. Snapshot / cua so
- Kaggle (doc): ho5-a3-mapper-snap {mapper_snapshot.tsv 11KB, ho5_mapper_overlay.jar 5KB, ...}; ho5-a3-funding-snap {funding_snapshot.tsvgz.bin
  16MB, v3_info.json, gate2025.json, ...} = v3 (khop fund/ds3/SHA256SUMS fb024c40/207e7c60). Kernel tu kiem sha -> exit 2 neu sai.
- Cua so: rep3/rep4-s123 (result.json date_first 20210701, date_last 20251230, mapper 863, profile r4_kg0_k16_f015_g155) == cua so r1-a3
  (r1-a3-a1/s7 cung 20210701..20251230, mapper 863). => DU bang chung cho CUNG cua so, nhung CHI seed s123. A1/S7 chua kiem -> parity NEN quyet dinh.
  (ho5-a3-l26-* la duong 2026 co UNSEAL, KHONG phai bang chung, va code unseal KHONG co trong driver.)
- Funding v3: co ban ghi 2026-01..2026-09 (v3_info add_by_month dung o 2026-09; dump Aerospike toi 2026-08-05) -> khong co >= 2026-10-01.
  Sim dung o SIM_END_DATE 20251231 (cfg ghim, check (e)). Mapper snapshot = bang id<->symbol, khong co gia.

## 3. Key moi
- cfg: want_snap_sha, want_ovl_sha, want_fsnap_sha, want_fovl_sha (ghim HO5_CFG, check (g)). extra_env KHONG doi (chi WFO_DISABLE_DCA, whitelist giu).
  overrides KHONG doi. Khong key unseal. dataset_sources +2 (ho5-a3-mapper-snap, ho5-a3-funding-snap), regex chan 2026.
- Bang 25 cau hinh: hunk diff khong cham bang; `list` + `dry` 6 o (A05R05-S1, A20R2-S2, B05-S1, B20-S2, A10R1-S2, NEN) x A1/S7 khop prereg muc 4
  (TP = R x |SL|, nhanh A bo X14, S2 = 1,0,0,0 + F_BASE 0.0075, NEN rong). sim_end 20251231, jar sim-jar-tsx.
- list/dry: chay voi https_proxy=127.0.0.1:9 van OK; md5 cay f2b_state + kaggle_sim/f2b-* truoc/sau trung (khong ghi trang thai;
  base_r1a3 ghi vao mkdtemp roi xoa).

## 4. Test / mutant
- test_f2b_driver.py tai cho: 44/44 OK. Ban copy (khong phai git repo) baseline = 1 ERROR test_real_git_state_readonly (ky vong).
- 23 mutant: BAT 20 (quen overlay nhanh A; quen overlay NEN; them wfo-ticker-2026h1; them vz-x-2026 qua overlay_dss; env HOLDOUT_UNSEAL;
  key holdout_unseal trong cfg; doi jar_ds; fetch tai ca output; fetch cho .bin; smoke bo PREFLIGHT_FAIL; smoke bo 'from SNAPSHOT';
  WL_ADD mo rong; WL_ENV mo rong; push bo PARITY_OK; grid bo PARITY_OK; overlay_result_errs rong; bo kiem sha ho5_k2/k3; ghim funding v2;
  bo git_guard; bo kiem dataset_sources (g); bo FETCH_MAX).
  LOT 3 (deu la lop phong thu du phong, da duoc kiem tra bang-nhau bao phu): bo OVERLAY_GONE check; bo OVERLAY_MARKERS check; bo regex 2026.

## 5. Loi NHO (khong chan push parity)
N1 f2b_driver.py parity_ok() (~dong 473-503): khong kiem overlay_result_errs tren result.json DIA. PARITY_OK chi do parity_compare ghi
   (co kiem) nen hien an toan; them `why += overlay_result_errs(res)` cho chac.
N2 grid / cmd_fetch o luoi khong kiem overlay_result_errs + OVL_FORBIDDEN ("Connection refused"...) cho TUNG o; smoke chi phu A10R1-S1 A1.
   Neu nhanh B / S2 cham mot duong Aerospike khac (host da doi 127.0.0.1) ma Java nuot loi, ket qua o lech im lang. Sua: trong _row_state/
   fetch o luoi chay scan_logs + overlay_result_errs, danh LOI neu vi pham. Nen lam TRUOC grid (khong can truoc parity).
N3 select_output_files: Kaggle listing tra totalBytes=None (xem wait_rep4.log) -> FETCH_MAX_BYTES vo hieu; bao ve thuc te la loc theo ten (du).
N4 pushed/f2b-nen-a1.json, f2b-nen-s7.json, f2b-smk-A10R1-S1-a1.json (ban cu, kernel loi) con -> `parity <seed>` se thay marker + ERROR -> exit 7.
   MASTER phai chay `parity A1 --repush` / `parity S7 --repush` (va smoke --repush). Ghi vao F2B_DEV.
N5 import ho5_k2/k3 goi logging.basicConfig(force=True) (doi handler/format); chi level duoc khoi phuc. My quan.
N6 Mutant LOT 3: them test tach rieng cho OVERLAY_GONE / OVERLAY_MARKERS / regex 2026 (vd md tu-nhat-quan co 'x-2026').
N7 Phu thuoc file ngoai repo (~/claude_master/w3/ho5/*): ghim sha nen an toan, nhung git_guard khong phu; nen copy vao repo sau nay.

## 6. Rui ro con lai
R1 Parity lech: parity_compare -> ParityMismatch exit 3, xoa PARITY_OK, push luoi bi chan (test + mutant M9a/b xac nhan). Driver DUNG va bao.
   Nguyen nhan kha di: v3 them 3 420 moc funding 2025 (BTCST/SNT/STPT/PLANCK...) khong co trong store luc r1-a3 chay. Khi do MASTER quyet
   (dataset v2 b39b63ed khong con tren Kaggle -> phai tao lai = viec owner).
R2 Parity NEN dat KHONG chung minh 24 o: o khac tap lenh co the giu symbol co moc funding v3-only (2025) -> lech so voi "duong Aerospike"
   (nhung gan su that hon). Anh huong: tang theo thoi gian giu; nhanh B (X14 toi 504 h) > nhanh A (<= 168 h). Do lon ky vong rat nho
   (3 420/~2.3M moc, symbol it thanh khoan). Doi chieu duoc: lenh o luoi co symbol thuoc tap v3-only - de nghi bao cao so lenh do.
R3 Overlay la class CFR decompile (SimpleSymbolMapper / FundingFeeManager) dat truoc jar tren classpath; s123 trung byte -> rui ro thap,
   nhung code-path TP/SL/no-DCA chua duoc trung-byte (khong co tham chieu Aerospike cho chung).

## Vong v4 (DELTA, 2026-11-27) - ban copy ~/claude_master/w3/levz_rev/f2b_v4
f2b_driver.py    8310d262804c5572282d9c3ce1e12b3596d065cc7dafe9ec95ad8f612a6ed79c
test_f2b_driver.py 8d93d6280a604a264b37debbb4f2ccd73ee56b4619917b0bc611b5d4742de37b
KET LUAN v4: PASS-WITH-MINOR (khong loi CHAN).

(1) diff vs worktree (ddf97c3c): chi THEM (docstring, import datetime, N1 dong 506, N2/N2b 871-979, _done_state/_row_state,
    score 1067-1281, argparse). Bang / overlay / whitelist / git_guard / parity md5 / seed / sim_end KHONG doi.
    Chay tren ban copy (mktemp, cau truc r1_s1 day du): `list` md5 trung worktree; `dry` 6 o x A1/S7: cfg+metadata trung byte (12/12 SAME);
    proxy gia, cay f2b_state truoc/sau trung -> khong mang, khong ghi trang thai.
(2) N1 dung (parity_ok them overlay_result_errs tren dia). N2: cell_output_errs kiem overlay sha, OVL_FORBIDDEN + parse error,
    JAR == r1-a3, mapper >= 800, ok is True, co printDone, java_rc == run tham chieu (r1-a3-a1/s7 result.json java_rc = 1).
    _done_state: XONG chi khi cell_check == OK; o LOI khong bi grid push lai (grid chi push CHUA_PUSH; mutant V13 bat).
    Java a8690d46 SimulatorMarketLevelTicker1MStopLoss.java: `System.exit(1)` sau simulatorWithInitEntry + sleep -> o DONG 145
    (DEV ghi 161 - sai so dong, noi dung dung). Ban v3 cu dung java_rc == 0 => moi o se la LOI; v4 sua dung.
    N2b: tap v3-only = {BTCST, SNT, STPT, PLANCK} tu gate2025.json (sha ghim c66396e4, tong 3 420 khop only_crawl). r1-a3-a1: 0 lenh.
(3) score: du lieu THAT r1-a3-a1: CAGR 37.2429 %, maxDD -16.8465 %, Calmar 2.2107, n 3 622, eq 35 000 -> 145 391, 1 644 ngay
    20210701..20251230; tinh doc lap tren cung chuoi trung. PnL nam 2022..2025 = 2 518 / 34 231 / 34 194 / 32 502 (ca 4 duong).
    Du lieu gia: giu dong CUOI moi ngay (b+unP), CAGR 41.4549 % == tay ((2)^(365.25/730)-1), maxDD -25 % dung, PnL theo nam ngay DONG
    (lenh mo 2022 dong 2023-01-01 -> 2023), bo dong start khong parse. _verdict: maxDD so `c >= nen` (am: -15 tot hon -17) DUNG chieu;
    CAGR >= 0.5 x nen; Calmar strict >; nam = so nam CA 2 seed cung duong >= 3 - khop prereg muc 5. score khong goi mang, o thieu -> "chua co".
(4) Test ban copy: 60 chay, 59 OK + 1 ERROR du kien (khong phai git repo). 25 mutant phan moi: BAT 23, LOT 2:
    - LOT V7 PnL nam theo ngay MO (code dung, test khong phan biet) -> NHO: them test lenh mo 2022 dong 2023.
    - LOT V14 Calmar `>` -> `>=` (bien bang nhau) -> NHO: them test Calmar bang nen = KHONG DAT.
    BAT: parity_ok bo overlay; bo java_rc; _done_state bo cell_check; bo ok; bo printDone; dao maxDD; CAGR >= nen; nam theo any-seed;
    N2b thieu / them symbol / khong bo USDT; fetch .bin; bo dong cam; bo JAR; mapper 0; grid push lai LOI; cmd_fetch khong raise;
    equity dong DAU ngay; bo overlay sha o luoi; NEN khong can parity; nam >= 2.
NHO v4: V7/V14 (test), so dong Java 161 -> 145 trong docstring / F2B_DEV. N3 (FETCH_MAX vo hieu khi totalBytes None) van nhu cu.
MASTER: chep 3 file f2b_v4 vao research/r1_s1/, kiem lai sha 2 file tren, chay test (60 OK trong worktree), commit; sau do
`parity A1 --repush`, `parity S7 --repush`.
