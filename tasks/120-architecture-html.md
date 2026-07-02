# TASK-120: Folder docs/architecture/ + 2 trang HTML kiến trúc (CCD sonnet)

- **status:** doing (giao CCD 2026-07-03 sáng)
- **resource:** local · **touches_live_process:** không

## Việc làm
1. Tạo folder `docs/architecture/` (nơi lưu MỌI tài liệu kiến trúc từ nay).
2. **`docs/architecture/wfo_architecture.html`** — kiến trúc WFO 6 lớp, nguồn sự thật: `docs/insights/WFO_ROADMAP.md` §3a
   (đọc thêm §3b/3c + tasks/112..119 để lấy TRẠNG THÁI MỚI NHẤT: V4.1 đã PASS gate 2026-07-03, cặp so V4 đang chạy,
   vế A chờ launch, gate/market per-fold + survivorship + maxDD margin-call + exit clamp vẫn chưa làm).
3. **`docs/architecture/system_architecture_all.html`** — kiến trúc TOÀN hệ thống BinanceFuturesJava:
   4 node (242 live ingest+trading GMT+7 write-protected · 226 Aerospike ticker/funding/OI + jobstore Kaggle ·
   Oracle compute chính 23GB + Aerospike local ns=test · Kaggle 5 slot CPU) + local dev Windows; luồng dữ liệu
   live→Aerospike→export per-fold models→WfoDataset→workers→verdict; model pipeline (funding selector, gate/market);
   nguồn đọc: docs/PIPELINE_PROVENANCE.md, docs/KAGGLE_RULES.md, docs/db/aerospike-226.md, docs/insights/WFO_ROADMAP.md.
4. Yêu cầu HTML: single-file tự chứa (CSS inline, không build step), tiếng Việt, màu trạng thái (xanh=xong/vàng=đang/đỏ=chưa)
   + legend, responsive, click node hiện tooltip mô tả + đường dẫn file nguồn. Cuối file ghi chú cách cập nhật trạng thái.
5. `docs/architecture/README.md` ngắn: quy ước folder + cách cập nhật.

## Output: 3 file trên + commit theo quy ước (không git add .). Ghi Kết quả + tạo /d/claudedata/CCD120_DONE.

## Kết quả
<CCD điền>
