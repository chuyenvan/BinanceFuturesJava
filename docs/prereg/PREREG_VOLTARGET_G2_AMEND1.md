# AMENDMENT 1 — PREREG_VOLTARGET_G2 (agent thuc thi, 2026-09-30, TRUOC khi co bat ky so VT nao tren G2+FLAT3)

Pre-reg goc: docs/prereg/PREREG_VOLTARGET_G2.md (md5 24369f259e37b81065af2e5020219d0f) — KHONG sua. File nay chi them.

## 1. Loi thiet ke TASK5 (RESULT_VOL_TARGET.md §5) la gi
- Loi = THAM SO PORTFOLIO: TARGET_ANNUAL_VOL = 25%/nam chot "hop ly" ma KHONG doi chieu vol tu nhien cua baseline (T170 do duoc 14.46%/nam).
  Target > vol tu nhien => multiplier = target/sigma_20d > 1 gan nhu luon => vol-target thanh LEVER-UP, khong phai giam rui ro.
  Ket qua TASK5: PORTFOLIO xau maxDD/UW/sd/CV o moi nam. COIN khong dinh loi nay (SIGMA_REF = trung vi universe, khong phu thuoc target).
- Hang so nam trong code: VolTargetSizing.PORTFOLIO_TARGET_ANNUAL_VOL = 0.25f (public static final, KHONG doc tu key/Cfg). Jar sim-jar-gdv2 (sha 7368be46...) chua class nay voi 0.25f.

## 2. Do tren B0 (G2+FLAT3, chi doc baseline g2flat3-val, md5 650c386f — KHONG phai so cua arm VT)
Script ~/claude_master/0929/vt_natvol.py, equity ngay = b+unP (logs/sim.out), log-return, ddof=1, x sqrt(365):
- sd ngay 0.688% => vol nam hoa 13.14%. rolling-20d vol nam hoa: p10~0.0, p25 1.6%, p50 6.6%, p75 10.9%, p90 17.4%, mean 8.6% (chien luoc "bursty": nhieu cua so gan phang).
- Voi target 25% + clamp [0.5, 2.0]: multiplier trung binh 1.86, 79.4% so ngay bi kep o 2.0 => THUC CHAT la lever co dinh ~2x tren B0.
  (target 14%: mean 1.63, 52% o 2.0; target 6%: mean 1.16, median 0.91.)
=> VT_PORT voi target 25% tren nen G2 la CUNG loi TASK5, nang hon (nen G2 vol thap hon T170). KHONG hop le de phan xet "vol-target co ich hay khong".

## 3. Xu ly (amendment)
- Sua dung = doi PORTFOLIO_TARGET_ANNUAL_VOL thanh tham so key-driven (hoac hang so khac) => can SUA JAVA + BUILD JAR MOI.
  Rang buoc task: "KHONG build" => KHONG THE thuc thi ban sua trong luot nay. Agent KHONG tu y build/khong tu y doi target.
- Hanh dong: VT_PORT HOAN (BLOCKED, khong chay o 25%, khong bao nhu mot arm hop le). Dinh nghia cac arm con lai giu NGUYEN pre-reg goc:
  B0 (OFF) + VT_COIN (COIN, SIGMA_REF 0.010657, clamp [0.5,2.0], khong doi). Luat §9 chay cho B0 vs VT_COIN, k=3 inflate 1.482 giu nguyen (khong ha k khi 1 arm hoan — bao thu).
- DE XUAT cho MASTER (KHONG khoa, can quyet dinh + cho phep build): (a) them key SIZE_VOL_TARGET_ANNUAL_VOL doc qua Cfg.getOr (mac dinh 0.25 => OFF/COIN byte-identical);
  (b) chon target THEO QUY TAC chot truoc (vi du "target sao cho multiplier trung binh tren B0 ~ 1.0", gan 6%/nam theo do tren), 1 gia tri, khong quet;
  (c) rebuild jar, dong goi dataset moi, chay lai parity B0 650c386f voi jar moi truoc khi tin VT_PORT.

## 4. Ha tang COIN tren Kaggle (khong doi thiet ke)
VolTargetSizing COIN doc CLOSES_1H.bin + symbol_map.csv tu duong dan cung /home/ubuntu/... (khong co trong bundle Kaggle). Dung dataset phu chuyendinh/sim-vt-data
(CLOSES_1H.bin 144513404B + symbol_map.csv, copy nguyen tu Oracle, sha ghi trong RESULT) + kernel tao symlink toi dung 2 duong dan do TRUOC khi chay java. Khong doi jar, khong doi profile ngoai 1 key SIZE_VOL_TARGET_MODE.
