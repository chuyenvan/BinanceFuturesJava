# PREREG_PARITY_V12_DRY — ADDENDUM 10: A1 loại PREMARKET (MASTER 4q chọn phương án b), 2026-11-05

## Thay đổi
- `UniverseA1Classifier` thêm `Kind.PREMARKET`, và `excluded()` nay loại cả nó. Commit gốc 0fcfc981, đã merge vào v1.2/c3-live.
- Tác động lên universe A1:
  - tín hiệu, nạp r / buffer: `UniverseA1Filter`;
  - sim / ExportGateDataset: dùng chung `UniverseA1Filter`.
- R7 (`SymbolUniverseLive`, strictCoin) giữ `NOT_COIN`, nên hai phía nhất quán.
- Harness parity được cập nhật cho khớp:
  - `a1cls.py` (port của classifier) loại PREMARKET. Commit 601e0906, đã merge.
  - r6 (`r456.py`): symbol PREMARKET chỉ có ở phía live thì ghi vào `explained_PREMARKET_b`, không tính là unexplained.

## Vì sao không export lại backtest / dataset
- Theo MASTER 4q, backtest A1 có **0 leg PREMARKET**.
- Vì vậy các con số đã kiểm (sim A1, các ngưỡng parity) không đổi, và **không** export lại.
- Snapshot 10-27 có đúng 1 PREMARKET là PREDICTUSDT (test `UniverseA1FilterTest.realSnapshot_1027`).

## Điểm mù (ghi rõ)
- Phân loại dựa trên **snapshot** exchangeInfo, không theo thời điểm.
- Một hợp đồng PREMARKET đã chuyển sang COIN sẽ được nhận là CRYPTO ở **mọi** thời điểm theo snapshot mới, kể cả giai đoạn nó còn
  là PREMARKET.
- Ngược lại, một symbol đang PREMARKET bị loại kể từ onboardDate của nó.
- Hệ quả: lịch sử trước ngày chuyển sang COIN có thể khác với thực tế lúc đó. Live và sim dùng cùng một snapshot nên vẫn nhất quán
  với nhau.

## Ngày parity
- Ngày restart để nạp jar có thay đổi này là ngày **XÁM** (luật cũ), không đếm vào chuỗi ngày sạch.
- Ngưỡng H / K giữ nguyên.
