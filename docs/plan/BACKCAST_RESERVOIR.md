# BACKCAST_RESERVOIR — hướng dẫn mở kho backcast 2020 (cho agent tương lai)

Pre-reg kho: `docs/prereg/PREREG_BACKCAST_RESERVOIR.md` (`596c1ef8`, hiệu lực). Kết quả dựng: `docs/result/bcast/BCAST_BUILD.md` (+ `.json`). Kho = bằng chứng PHỤ, không thay holdout 2026.

## 0. Trước khi mở — bắt buộc
1. Ý tưởng phải đã CHỐT trên DEV (2021-07..2025-12), có số DEV.
2. Viết pre-reg riêng `docs/prereg/PREREG_BCAST_<Y>.md`, commit TRƯỚC khi đẩy kernel nào: giả thuyết; cấu hình ý tưởng (override chính xác); k biến thể (inflate √(2 ln k)); thước + ngưỡng (§3); scorer (script chấm commit cùng pre-reg, CHƯA đọc output).
3. Ghi 1 dòng vào sổ §5 (ngày, ý tưởng, hash pre-reg). Mỗi ý tưởng mở kho ĐÚNG 1 lần; chạy lại chỉ khi lỗi hạ tầng (rc≠ok, mapper < 800, timeout) với cfg y hệt.
4. Không dùng kho để tìm/tune. FAIL ⇒ không "sửa rồi mở lại".

## 1. Dữ liệu kho
- Kernel output (nguồn dùng cho sim, như `bcast-tech`): exporter `chuyendinh/bcast-x20-a` (ticker `out/ticker/ticker_YYYYMMDD.bin.gz` 20200101..20210103, gate/Tool1/nhãn/CLOSES_1H/funding Vision/lifecycle), chuỗi `chuyendinh/bcast-ch20-a` (`out/market.bin`, `out/pred_s<seed>/pred.bin` ×8, `out/bins/predict_wf_2020{0101,0401,0701,1001}.bin`, `out/net015/…`, `out/s1_bcast20.parquet`, `out/feat_v2_bc20.parquet`). KHÔNG chạy lại 2 kernel này (Kaggle chỉ giữ output version mới nhất).
- Bản niêm phong bền: dataset private `chuyendinh/bcast-2020-2021h1-p1` (phẳng; `MANIFEST_bcast.json` = md5 + đường dẫn gốc trong kernel). md5 ở `BCAST_BUILD.json`.
- Mọi kernel mở kho phải assert md5 các file dùng == manifest.

## 2. Chạy sim trên kho (mẫu `research/analysis/bcast_sim.py`)
- Template = `gate_ablation_driver.template()` (tools/kaggle_sim.py HEAD NOWRITE242, md5 `8b60b00a…`) + khối BCAST (TIME_RUN=20200101 trên bản copy config.properties của bundle; TICKER_BCAST 369/369 md5) + `ho4p1_fund_block.py` đã vá trong `bcast_sim.template()` (thu bản ghi tự kiểm DEV ở vòng giữa vì `lo`=1577811600000 < mọi bản ghi bundle; `hi`=9e15) ⇒ funding.bin chỉ gồm 526 620 bản ghi kho, md5 `669d2206…` (phải trùng). Dùng lại hàm `template()`/`push()` của `bcast_sim.py`, chỉ đổi tag/overrides/seed/pred.
- OI NaN toàn kho (ghim không có hàng 2020); BTCUSDT/ETHUSDT không có trong bins.
- Datasets: `sim-ho26a-bundle`, `sim-jar-nsel` (jar `b7c89f09`); kernel_sources: `bcast-ch20-a`, `bcast-x20-a`; KHÔNG gắn dataset ticker DEV; `ticker_min_days`=369; `SIM_END_DATE=20210101`; `pred_ds`=`pred_s<seed>`, `want_pred_md5` theo `BCAST_BUILD.json`, `want_pred_base`=`22f69456…`.
- Kaggle: kiểm Python API trước mỗi lần đẩy; tối đa 2 kernel toàn tài khoản (chia với agent khác).
- Output tải thẳng vào thư mục niêm phong (chmod 700) cho tới khi scorer (đã commit) chấm.

## 3. Cấu hình nền + thước
- Nền chuẩn (chạy CÙNG lần mở kho đầu tiên, dùng lại về sau): **b0** = profile `r4_kg0_k16_f015_g155` + `GA.B0OV`; **k24** = b0 + `SELECTOR_RANK_TOPK=24` + `GATE_QUOTA_SKIP_WHEN_FULL=true`; × {phí gốc; stress `SIM_CRASH_ENTRY_PENALTY=0.005`} × 8 seed (42/7/13/21/99/123/777/2024, pred `pred_s<seed>`) = 32 kernel. Ý tưởng: cấu hình nền tương ứng + override ý tưởng, cùng 8 seed × 2 bản chi phí.
- **Cửa sổ chấm: 2020-05-01 00:00 → 2020-12-31 23:59 +07** (chính); báo kèm kết thúc 2020-11-30 23:59 +07. Trước 2020-05-01 = warm-up (không chấm, kể cả COVID 03-12). 2021 = không bao giờ.
- Thước như HO26/HO4 scorer: n theo start trong cửa sổ, ΣPnL theo end trong cửa sổ, MTM phút; maxDD MTM đặt lại peak tại 2020-05-01 00:00 +07; bản chính = stress 0,005.
- **E0 tuyệt đối của ý tưởng:** mean ΣPnL_S > 0 VÀ ≥ 6/8 seed > 0.
- **Δ ghép cặp seed vs nền cùng kho** (mẫu H-A HO4): mean ΔΣPnL_S ≥ 0 VÀ mean ΔmaxDD ≥ −5 pp (ngưỡng ý tưởng có thể siết, không nới, trong pre-reg riêng). Báo kèm: phí gốc, theo tháng, bootstrap MTM block-10d, inflate k.
- Đọc kết quả: universe nhỏ (25→80 symbol) ⇒ k24 ≈ b0 đầu kho; OI NaN; chế độ 2020 khác DEV ⇒ PASS ở kho = ủng hộ phụ, FAIL ở kho = cờ vàng cần giải thích, không tự động bác bỏ.

## 4. Mẫu scorer
Theo `research/analysis/ho4_score_a.py` / `ho4_score_b.py` (đổi mép cửa sổ sang hằng +07 ở §3, đổi tập kernel); commit TRƯỚC khi tải output; hai scorer độc lập + đối chiếu.

## 5. Sổ mở kho
| Ngày | Ý tưởng | Pre-reg | Kernel | Người đọc số | Kết quả |
|---|---|---|---|---|---|
| 2026-10-12 | (dựng kho, sim kỹ thuật `bcast-tech` B0 s42 phí gốc — KHÔNG phải mở kho; n 548, printDone md5 `2b7ded8f…` niêm phong ở `~/kaggle_sim/sealed/bcast-tech`, chưa ai đọc) | 596c1ef8 | bcast-tech | — | — |
