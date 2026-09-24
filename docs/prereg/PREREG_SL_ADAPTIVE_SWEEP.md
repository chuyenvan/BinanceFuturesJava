# PRE-REG: SWEEP SL TUY BIEN THEO RANK (3 LEVER A/B/C) — DEV MO RONG 2021

Pre-registration CHOT truoc khi sim variant. KHONG doi sau khi thay ket qua.
Repo BinanceFuturesJava branch `module`. Sim: SimulatorMarketLevelTicker1MStopLoss.
Recon: docs/analysis/RESEARCH_SL_ADAPTIVE.md (commit 3ac3f03).

## 1. GIA THUYET & THIET KE
Rank split: STRONG = selRank 1-4, WEAK = selRank 5-8 (top-K=8, chia doi).
selRank == null (leg DCA_LEVEL1 / BIG_DOWN, khong qua selector) -> WEAK (quy uoc bao thu, giong X3).
Moi lever 1 config, default OFF = byte-identical baseline mo rong.

- B (SL_ADAPT_TSTOP): LOSER_TIME_STOP theo rank cho vi the CHUA arm: WEAK=72h, STRONG=168h.
- A (SL_ADAPT_HARDSL): PRE_ARM_SL theo rank: WEAK=-0.08 (cap -8% coin yeu), STRONG=0 (giu).
- C (SL_ADAPT_ARM): arm rate theo rank: WEAK=0.05, STRONG=0.03.

Ly do (nguyen tac, khong hau nghiem): coin rank thap/do tin thap -> phong thu hon
(cat zombie som / cap downside / khoa loi som) = nham collapse-risk. Coin rank cao -> cho room.

Caveat pre-reg: moi lever them CO CHE MOI so baseline (baseline cac knob nay = off) nen day la
test "adaptive-SL co giup khong" chu chua tach "adaptive vs fixed" — neu lever nao thang,
follow-up tach sau (pre-reg rieng).

## 2. THAM SO CHOT (KHONG DOI)
| lever | flag (profile key) | STRONG (rank<=4) | WEAK (rank>4/null) |
|---|---|---|---|
| B TSTOP | SIM_SL_ADAPT_TSTOP=1 | 168h | 72h |
| A HARDSL | SIM_SL_ADAPT_HARDSL=1 | 0 (off) | -0.08 |
| C ARM | SIM_SL_ADAPT_ARM=1 | 0.03 | 0.05 |

Rank split N=4 (SIM_SL_ADAPT_RANK_N default 4).

## 3. GHI CHU TRIEN KHAI (them luc pre-reg, TRUOC sim — de ghi chinh xac)
- Baseline mo rong that su chay bang profile `profiles/x1_c3_full.properties`
  (PROFILE_HASH 135750e0, 19 key, SELECTOR_ONLY_ENTRY=0), config `configs/sim_dev_file_2021.properties`,
  env WFO_DATA_DIR=/home/ubuntu/wfo_ds_x1_2021 SIM_END_DATE=20251231; printDone md5 = dc16e4da, n=2559.
  Harness goc: /home/ubuntu/x1log2021/driverAB.sh.
- Gia tri baseline THAT cua cac knob (KHAC gia dinh "0.03/off" trong van ban lever):
  * arm rate baseline = SIM_RATE_PROFIT_STOP_MARKET = 0.07 (KHONG phai 0.03).
  * LOSER_TIME_STOP baseline = 168h (KHONG phai 0/tat).
  * PRE_ARM_SL baseline = 0 (off).
  => Lever B STRONG=168 = GIU baseline; WEAK=72 = cat som. Nhat quan voi baseline.
  => Lever A STRONG=0 = GIU baseline (off); WEAK=-0.08 = them cap. Nhat quan.
  => Lever C: baseline arm = 0.07, nhung lever dat STRONG=0.03/WEAK=0.05 => KHI BAT, CA HAI rank
     deu arm SOM HON baseline. Vay lever C KHONG "giu strong o baseline"; no la test
     "arm som hon + chia rank". CAVEAT lech giua so pre-reg va van ban ly do.
     Van GIU dung so pre-reg (khong tune): STRONG=0.03, WEAK=0.05.
- Parity dam bao bang KIEN TRUC: khi flag OFF, moi nhanh exit chay NGUYEN code cu (gia tri hieu dung
  = Configs cu), IEEE-identical. Flag chi doc selRank co san tren orderMulti, khong them plumbing.

## 4. IMPLEMENT (behind flag, default OFF; 3 flag rieng)
- Configs: SIM_SL_ADAPT_{TSTOP,HARDSL,ARM} (bool) + SIM_SL_ADAPT_RANK_N + gia tri STRONG/WEAK,
  doc qua Cfg.get (profile la nguon su that). Khong khai bao => OFF/gia tri cu.
- Sim exit: B tai nhanh LOSER_TIME_STOP (Sim:682), A tai nhanh PRE_ARM_SL (Sim:663),
  C tai cong arm (Sim:708). PreArmSlUtils them ban *Val nhan preArmSl tuong minh.
- Build: mvn -o package (bo clean). mvn test PASS.

## 5. CONG (GATES) — CHOT
(a) Moi variant flag OFF -> printDone md5 = dc16e4da (byte-identical baseline mo rong).
    FAIL => revert lever do, bao, DUNG.
(b) mvn test PASS.

## 6. CHAM — CHOT
- x1_rates.py moi variant vs X1_C3_FULL_2021, k=3 (multiplicity sqrt(2 ln 3)=1.48 => CI_INFLATE=1.48).
- Quyet dinh = luat cu: >=2 rate CHAT LUONG ngoai CI CUNG huong TOT + PASS rang buoc cung
  (maxDD<=15 / UW<=120 / nam>=0 / quy>=-5) tung nam.
- Rate chat luong: win%, TSloss%, mP|SM, mP|SL, meanP (bo n, mMargin).

## 7. LUAT CUNG
Chi Oracle. KHONG cham 242, KHONG git push, KHONG tune (dung dung tham so muc 2),
KHONG cham holdout 2026. Parity fail -> DUNG + bao.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
