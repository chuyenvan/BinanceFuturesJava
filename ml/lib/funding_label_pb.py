"""Đọc file LABEL định dạng protobuf columnar (TASK-251) -> pandas DataFrame.

Thay thế `pd.read_csv(LABEL_CSV, usecols=[...])` của các script train/WFO. Trả về DataFrame
có TÊN CỘT Y HỆT CSV cũ (tEpochMs, tDate, symbol, maxFav_4h, ... nBars_72h) nên phía gọi chỉ
cần đổi đúng 1 dòng đọc file, KHÔNG phải sửa logic phía sau.

VÌ SAO ĐỔI ĐỊNH DẠNG (số đo thật trên 3M dòng label, đã push Kaggle verify):
    CSV thô 601MB          -> quota Kaggle 161.8MB
    protobuf columnar+delta -> quota Kaggle  46.5MB  = giảm 3.48 lần
Kaggle tính quota theo BẢN NÉN NỘI BỘ (≈gzip) chứ không theo size thô, nên mẹo "nén sẵn bằng
gzip rồi push" KHÔNG giúp gì (file .gz tính ~100% dung lượng). Xem src/main/proto/funding_label.proto.

CÁCH DÙNG (khớp chữ ký cũ để thay 1 dòng):
    # CŨ:  df = pd.read_csv(LABEL_CSV, usecols=cols, on_bad_lines="skip")
    # MỚI: df = read_label(LABEL_PB, usecols=cols)

    from funding_label_pb import read_label
    df = read_label("funding_label_1m_20250101_to_20250401.pb",
                    usecols=["tEpochMs", "symbol", "maxFav_72h", "nBars_72h"])

TRÊN KAGGLE: cần cả file `funding_label_pb2.py` (sinh từ .proto) nằm cùng thư mục — nó được
ship kèm trong dataset code. Không cần cài thêm gì (Kaggle có sẵn `protobuf`).
"""

import glob as _glob
import logging
import os

import numpy as np
import pandas as pd

try:
    import funding_label_pb2 as _pb
except ImportError:  # khi dùng như package trong repo
    from . import funding_label_pb2 as _pb

log = logging.getLogger(__name__)

# Kích thước varint tối đa của length-prefix mà writeDelimitedTo sinh ra.
_MAX_VARINT = 10


def _read_varint(buf, pos):
    """Đọc 1 varint không dấu tại `pos`. Trả (giá trị, vị trí mới)."""
    result = 0
    shift = 0
    while True:
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7
        if shift >= 64:
            raise ValueError("varint quá dài — file hỏng hoặc không phải định dạng delimited")


def iter_chunks(path):
    """Duyệt lần lượt từng LabelChunk trong file (định dạng writeDelimitedTo của protobuf-java)."""
    with open(path, "rb") as f:
        buf = f.read()
    pos = 0
    n = len(buf)
    while pos < n:
        size, pos = _read_varint(buf, pos)
        chunk = _pb.LabelChunk()
        chunk.ParseFromString(buf[pos:pos + size])
        pos += size
        yield chunk


def _chunk_to_arrays(c, want):
    """Giải nén 1 chunk -> dict[tên cột] = ndarray. `want` = set tên cột cần (None = lấy hết)."""
    n = c.row_count
    scale = float(c.scale)
    step_ms = c.step_min * 60_000

    # sym_id / t_idx được ghi dạng delta -> cumsum để phục hồi giá trị gốc.
    out = {}
    need_sym = want is None or "symbol" in want
    need_ts = want is None or "tEpochMs" in want or "tDate" in want

    if need_sym:
        sym_idx = np.cumsum(np.asarray(c.sym_id, dtype=np.int64))
        symbols = np.array(c.symbols, dtype=object)
        out["symbol"] = symbols[sym_idx]
    if need_ts:
        t_idx = np.cumsum(np.asarray(c.t_idx, dtype=np.int64))
        out["tEpochMs"] = c.base_ms + t_idx * step_ms

    null_mask = np.asarray(c.null_mask, dtype=np.int64) if len(c.null_mask) else np.zeros(n, np.int64)

    # Các cột theo horizon: giá trị ghi ra là DELTA so với horizon liền trước -> cộng dồn.
    prev = {}
    for h_i, h_name in enumerate(c.horizons):
        hc = c.h[h_i]
        for field, arr_name, is_ratio in (
            ("max_fav", "maxFav", True),
            ("max_adv", "maxAdv", True),
            ("thit_fav", "tHitFav", False),
            ("thit_adv", "tHitAdv", False),
            ("ret_end", "retEnd", True),
        ):
            col = "%s_%s" % (arr_name, h_name)
            raw = np.asarray(getattr(hc, field), dtype=np.int64)
            cur = raw if h_i == 0 else prev[arr_name] + raw
            prev[arr_name] = cur
            if want is not None and col not in want:
                continue
            if is_ratio:
                v = cur.astype(np.float32) / scale
                # ô rỗng trong CSV cũ (NaN) được đánh dấu bằng bitmask, không phải bằng giá trị 0
                bit = {"maxFav": 0, "maxAdv": 1, "retEnd": 2}[arr_name]
                v = np.where((null_mask >> (h_i * 3 + bit)) & 1, np.nan, v)
                out[col] = v
            else:
                out[col] = cur.astype(np.int32)

        col_nb = "nBars_%s" % h_name
        if want is None or col_nb in want:
            # ghi ra là THIẾU HỤT so với kỳ vọng -> phục hồi: kỳ vọng − thiếu hụt
            expect = _horizon_minutes(h_name) // c.step_min
            deficit = np.asarray(hc.n_bars_deficit, dtype=np.int64)
            out[col_nb] = (expect - deficit).astype(np.int32)

    return out, n


_H_MIN = {"4h": 240, "12h": 720, "24h": 1440, "72h": 4320,
          "7d": 10080, "14d": 20160, "30d": 43200}


def _horizon_minutes(name):
    if name not in _H_MIN:
        raise ValueError("horizon lạ: %s (cập nhật _H_MIN trong funding_label_pb.py)" % name)
    return _H_MIN[name]


def read_label(path, usecols=None, add_tdate=False):
    """Đọc 1 file .pb (hoặc glob nhiều file) -> DataFrame giống hệt CSV cũ.

    Args:
        path: đường dẫn 1 file .pb, hoặc glob pattern (vd ".../funding_label_1m_*.pb").
        usecols: danh sách tên cột cần (như tham số cùng tên của pd.read_csv). None = lấy hết.
                 Chỉ giải nén cột được yêu cầu -> nhanh và tiết kiệm RAM hơn hẳn đọc hết.
        add_tdate: True thì sinh thêm cột `tDate` dạng "YYYYmmdd-HHMM" (GMT+7) như CSV cũ.
                   Mặc định False vì cột này derive được và không script nào dùng.
    """
    if any(ch in path for ch in "*?["):
        files = sorted(_glob.glob(path))
        # LOẠI file partition tạm (`_YYYYMMDD_to_YYYYMMDD.partN.pb`): đó là file mà job export ĐANG
        # GHI DỞ, chunk cuối chưa hoàn chỉnh -> ParseFromString sẽ ném "Wire format was corrupt".
        # Chỉ file quý đã merge xong (không có ".part") mới là dữ liệu hoàn chỉnh để đọc.
        parts = [f for f in files if ".part" in os.path.basename(f)]
        if parts:
            log.warning("Bỏ qua %d file .part đang ghi dở (job export chưa merge xong): %s",
                        len(parts), [os.path.basename(f) for f in parts[:4]])
            files = [f for f in files if ".part" not in os.path.basename(f)]
    else:
        files = [path]
    if not files:
        raise FileNotFoundError("Không thấy file label hoàn chỉnh nào khớp: %s "
                                "(có thể job export đang chạy, chưa merge xong quý nào)" % path)

    want = set(usecols) if usecols else None
    if want and add_tdate:
        want.add("tEpochMs")

    parts = []
    total = 0
    for fp in files:
        for c in iter_chunks(fp):
            cols, n = _chunk_to_arrays(c, want)
            parts.append(pd.DataFrame(cols))
            total += n
    df = pd.concat(parts, ignore_index=True) if len(parts) > 1 else parts[0]
    log.info("read_label: %d dòng từ %d file (%s)", total, len(files), os.path.basename(files[0]))

    if add_tdate:
        df["tDate"] = (pd.to_datetime(df["tEpochMs"], unit="ms", utc=True)
                       .dt.tz_convert("Etc/GMT-7").dt.strftime("%Y%m%d-%H%M"))
    if usecols:
        df = df[[c for c in usecols if c in df.columns]]
    return df


def meta(path):
    """Đọc metadata từ chunk đầu tiên mà không giải nén toàn bộ dữ liệu."""
    for c in iter_chunks(path):
        return {"base_ms": c.base_ms, "step_min": c.step_min, "scale": c.scale,
                "horizons": list(c.horizons), "symbols_in_first_chunk": len(c.symbols),
                "rows_in_first_chunk": c.row_count}
    return None
