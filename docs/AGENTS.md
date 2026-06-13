# AGENTS.md — Bản đồ CCD đang chạy (nguồn sự thật điều phối)

> Nhiều CCD chạy song song KHÔNG thấy nhau; Desktop là console nhưng cũng chỉ biết qua file này.
> File này là **nguồn sự thật DUY NHẤT** về "CCD nào đang làm task nào". Mục đích: reset máy / đổi session không mất vết, không hai CCD đụng một task.
> Cập nhật bằng tay (Desktop khi spec task; CCD khi claim/heartbeat/đóng). Không lock cứng — user là trọng tài khi tranh chấp/stale.

## Hiện trạng (cập nhật mỗi khi đổi)

| Task | Owner (CCD) | Status | Cập nhật | Job/PID nền | Ghi chú |
|------|-------------|--------|----------|-------------|---------|
| 005 backfill survivorship | — | ✅ DONE | 2026-06-13 | — | commit d387229; 30 core (id 760-789) |
| 007 fix ban + Reporter + OI + gom log | CCD #2 | ✅ DONE (commit 106baee) | 2026-06-13 | — | A-D xong (BinanceRestGuard chung); GỠ startHistoryCrawl (history→013); B/D golive OK |
| 016 fix ingest live (TickerFuturesHelper -1130/-1003) | CCD #1 | ✅ DONE (commit 3704b6e) | 2026-06-13 | — | clamp [1,1500] + guard -1003-rate 8s; self-test 10/10; ⚠️ CHƯA deploy — **gộp deploy với 019 + gỡ-crawl, 1 lần restart 242** |
| 019 fix funding live (FundingFeeManager + FundingIngestor flush) | CCD #1 (giao) | 🟡 TODO **ƯU TIÊN** | 2026-06-13 | 242 (live) | A: isProductionMode dead→refresh cache; B: flush ~1h thay 1′ (kiểm log-thưa vs bug); train/serve mismatch funding |
| 008 audit died-symbols | CCD #3 | ✅ DONE | 2026-06-13 | — | phương án A: gỡ 8 coin, config 129 symbol — đã APPLY live |
| 010 lifecycle 3-trạng-thái | CCD #3 | 🟣 REVIEW (code DONE; chờ chạy builder 226 + validate) | 2026-06-13 | — | 2 class compile PASS (javac11); builder = job nặng chạy trên 226; tool validate recompute đang chuẩn bị |
| 009 aggregate 15m/4h BTC/ETH | (CCD vừa xong) | ✅ DONE (historical) | 2026-06-13 | — | commit 3edb5b1; 15m~190k/4h~11.8k, validate khớp; ⚠️ forward-rolling CHƯA bật (cần khi golive) |
| 011 cải tiến validate-input | — | ⏸ CHỜ | — | — | sau 009/010 |
| 012 export gate LABEL (return) + validate | CCD (009) | ✅ DONE (commit 72c127a) | 2026-06-13 | — | gate_return.csv 190k dòng, 5 validate PASS; ⚠️ ret_24h≤−15% chỉ 0.92% → lớp GIẢM cực hiếm (H2 lưu ý) |
| 013 backfill OI/LS/taker history (metrics 2020) | CCD #2 (giao) | 🟡 TODO (verify B1 trước) | 2026-06-13 | tải Kaggle/226 · ghi 226 (+242 qua 226) | mở khoá OI funding (ADR-0011§5.3); chốt schema chung OI (B1.5) khớp 007-C |
| 015 feature gate NHÓM A (sẵn-có) | (giao CCD-012) | 🟡 TODO (chạy 226) | 2026-06-13 | 226 (đọc nặng) | momentum/vol/breadth/funding; export + validate riêng từng group (H1_GATE_SPEC §2.1) |
| 017 feature gate B giá/xu-hướng + funding-breadth | — | ⏸ (sau 015) | — | — | B1-B5 + B7; code mới 15m/4h + funding; LÀM NGAY (không chờ data) |
| 018 feature gate B crowdedness OI/LS-market | — | ⏸ (sau 013) | — | — | B6 OI-market + B8 LS-market (aggregate=gate); CHỜ 013 backfill |
| H1 ghép + export full | — | ⏸ (sau A+B) | — | — | validate chung + dataset versioned + fingerprint (§2.5/§3) |
| 014 khảo sát data.binance.vision | CCD #3 (giao) | 🟢 ƯU TIÊN THẤP | 2026-06-13 | **Kaggle** (tách khỏi 226) | dump mẫu+coverage data types → phân tích sau |

Status: 🟡 TODO · 🔵 DOING · 🟣 REVIEW (chờ user/Desktop soát) · ✅ DONE · ⏸ CHỜ (phụ thuộc task khác).

**Tài nguyên (chi tiết ở CLAUDE.md):** 242 = live PRIVATE (ghi 242 phải chạy trên 226/242) · 226 = backtest/train, open-net · Kaggle = tải-ngoài/train. **Tránh dồn nhiều job nặng cùng lúc trên 226**; tải-ngoài đẩy Kaggle.

## Quy ước (mọi CCD tuân — đọc TRƯỚC khi nhận task)

1. **Định danh CCD:** mỗi CCD tự đặt một nhãn ổn định trong phiên (vd `CCD-A`, hoặc theo terminal/cửa sổ user gán) + ghi PID job nền nếu có. Nhãn để phân biệt, không cần toàn cục.
2. **CLAIM trước khi làm:** đọc bảng trên + header task. Nếu task đã có owner KHÁC + DOING + `Cập nhật` còn gần đây → **KHÔNG đụng**, báo user. Nếu trống / STALE → ghi owner + `DOING` + `Cập nhật`=now vào **cả bảng này VÀ header task** rồi mới làm.
3. **HEARTBEAT:** cập nhật `Cập nhật` mỗi lần commit hoặc đổi bước lớn. Nếu một task `DOING` mà `Cập nhật` quá cũ (≳2h, không tiến triển) + nghi máy reset → coi **STALE**, user/Desktop có quyền reclaim cho CCD khác.
4. **ĐÓNG:** xong thì set `✅ DONE` + nhả owner + ghi commit hash. Cần user soát trước khi đóng → set `🟣 REVIEW`.
5. **Một task = một owner.** Không hai CCD cùng một task. Việc lớn thì tách task con (vd 007-A / 007-C) rồi claim riêng.
6. **Desktop (console)** khi spec task mới: thêm dòng `TODO` owner trống vào bảng + header task. Desktop KHÔNG tự claim (không chạy được).

## Liên kết
- Chi tiết từng task: `tasks/<id>-*.md` (mỗi task có header `owner/status/updated`).
- Tuyến đường tổng: `docs/REBUILD_ROADMAP.md`. Luật kỹ thuật: `CLAUDE.md`.
