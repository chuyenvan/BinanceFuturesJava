# PREREG_FAMILY2B_ERRATA2 - duong chay doi sang "overlay snapshot" (khong doi luoi, seed, tieu chi); chot truoc khi co ket qua kernel nao
Chot boi MASTER 2026-11-27 10:45. Prereg 5f917679 + ERRATA1 76c9f26e.
P1. Su co: (i) dataset sim-x1-2021-bundle bi xoa nham 26/11 -> da dung lai ban rut gon (khong funding.bin, khong sim.jar; BUNDLE_REBUILD.md;
    duong A3 tu tao funding, md5 trung run cu); (ii) kernel parity chet o PREFLIGHT vi Kaggle khong toi duoc Aerospike Oracle cong 3222
    (owner dong cong tu 2026-11-11; KHONG mo lai). PARITY_DIAG.md.
P2. Khac phuc: driver ap overlay snapshot symbol mapper + funding_data dung co che ho5_k3 (da kiem chung 19/11: tai lap r1-a3-s123 trung
    byte, cung cua so 2021-07..2025-12), cho MOI cau hinh (NEN, smoke, 24 o); jar sim-jar-tsx cc0f9d11 khong doi. Driver moi: f2b_driver.py
    sha256 ddf97c3cbdffa4dec8835fc5aa99477054603d0563ae3899275012ff097e3a5c; test bcce884ef566cdd431f10e2a2b6d0eb88ca627162da69d3095da0f7a972d12af;
    A1 PASS-WITH-MINOR (~/claude_master/w3/levz_rev/A1_F2B_DRIVER_V3.md).
P3. Parity NEN (md5 printDone trung r1-a3 cho A1 va S7) van la dieu kien BAT BUOC truoc luoi. Parity lech => DUNG, bao owner (khong chay luoi).
P4. Gioi han da biet (A1): bang chung trung byte moi co cho seed s123; snapshot funding v3 co 3 420 moc funding 2025 chi co trong v3 => o
    nao giu symbol do co the lech nhe so voi duong Aerospike (nhanh B giu toi 504 h nhay hon nhanh A). Bao kem so lenh tren cac symbol nay.
    Overlay la class decompile; duong TP / SL / khong DCA chua co tham chieu trung byte ngoai smoke.
P5. Truoc khi chay LUOI phai sua 2 loi nho A1 neu: parity_ok kiem overlay_result_errs tren result.json; fetch tung o luoi kiem sha overlay +
    dong cam. Parity duoc phep push truoc khi sua (dung --repush vi marker cu con).
