# PREREG_FAMILY2B_ERRATA1 - sua 4 cho mo ta sai / thieu sau A1 audit driver (truoc khi push bat ky kernel nao; khong doi luoi, seed, tieu chi)
Chot boi MASTER 2026-11-26. Prereg goc 5f917679. A1: ~/claude_master/w3/levz_rev/A1_F2B_DRIVER.md (2 vong, PASS-WITH-MINOR). Driver da audit:
research/r1_s1/f2b_driver.py sha256 acbcb9de72f4a0871bbe06ba7e090adb265eaf7bd41464cf2b0e94690c820997; test 4e111e6776330109e8bc5f4c735c8cf4dd23174b3042c92b6400372c6eabdb74.
G1. Muc 3: cong thuc leg con nhan tierMultiplier (chung moi o, khong doi so sanh giua cac o). Bay DCA_GRID_ENABLED=false cho leg 0,75 %
    (khong phai 0,375 %) - van CAM.
G2. Muc 9: dau hieu X14 trong log la dong "[TSX] extHours=<n>" (n > 0 = X14 bat); Java khong in "tsxDeferTicks". Nhanh A phai KHONG co dong
    nay voi n > 0; nhanh B va NEN phai CO (doc tay - driver chua tu kiem cho B / NEN).
G3. Muc 10: lenh chay tu ~/claude_master/vz_e1_wt/research/r1_s1/f2b_driver.py (khong phai ~/src/BinanceFuturesJava). Smoke dung tag rieng
    f2b-smk-<o>-<seed>. SIM_TAKE_PROFIT_ONLY phai la chuoi "true" (parseBoolean; "1" thanh false). SIM_PRE_ARM_SL chi bat khi AM.
G4. Smoke DAT khi `fetch --smoke` PASS (JAR cc0f9d11..., mapper >= 800, khong "SIM env override parse error", co "TAKEPROFIT sym=" va
    "PREARM_SL sym=", khong leg DCA_LEVEL*, khong "[TSX] extHours=" > 0) VA nguoi chay doc 5 dong TAKE_PROFIT_DONE cua o A10R1: muc thoat =
    gia vao x 1,10 (cot profit ~ +10 % truoc / sau phi - ghi ro thay gi). Smoke khong dat => DUNG, bao MASTER.
G5. Quy trinh chay: moi push qua driver (git_guard chan file chua commit); nguoi chay kiem phan hoi push co loi khong va dem slot bang
    `kernels status` tung kernel (CLI 1.6.17 khong in trang thai trong `kernels list`); luoi chay bang lenh `grid --max-slots N`, moi lan goi
    mot vong; kernel LOI khong tu push lai - bao MASTER.
