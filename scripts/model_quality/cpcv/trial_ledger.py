"""
trial_ledger.py — SỔ TRIAL append-only, chống-leak-loại-3 (leak qua não người).

Vấn đề nó giải: không dòng code nào ngăn được người nhìn OOS rồi chỉnh range/objective rồi chạy lại.
Thứ DUY NHẤT chặn được là ĐẾM: mọi trial từng chạy đều bị ghi, và n_trials đó đi thẳng vào DSR
(Bailey & López de Prado) làm ngưỡng pass cao lên. "Nhìn nhiều lần" ⇒ "phải giỏi hơn mới qua cửa".

Cơ chế chống sửa sổ:
  - JSONL append-only, mỗi bản ghi có prev_hash + hash = sha256(prev_hash || canonical_json(payload)).
  - Xoá/sửa/chèn bất kỳ bản ghi nào ⇒ đứt chuỗi ⇒ verify() phát hiện. Không "quên" được vài trial xấu.
  - assert_test_allowed(): TEST chỉ được chạm 1 LẦN cho mỗi (dataset_epoch, campaign). Chạm lần 2 ⇒
    raise. Muốn chạm lại PHẢI mở campaign mới (spec_hash mới) — và n_trials cũ vẫn cộng dồn.

KHÔNG phụ thuộc device/Oracle. Chạy: python3 trial_ledger.py -> self-test.
Logging: module `logging` (không print), theo rule dự án.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from typing import Any, Iterator

logger = logging.getLogger("ledger")

GENESIS_HASH = "0" * 64
PHASES = ("EXPLORE", "TEST", "FORWARD")


def canonical_json(obj: Any) -> str:
    """Chuỗi JSON tất định (sort key, không khoảng trắng) — nền của hash chain."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def spec_hash(spec: dict) -> str:
    """Vân tay của KHUNG đã đóng băng: search space + objective + PASS criteria.
    Đổi bất cứ thứ gì trong spec ⇒ hash đổi ⇒ đó là CAMPAIGN MỚI, không phải 'chạy lại'."""
    return hashlib.sha256(canonical_json(spec).encode("utf-8")).hexdigest()[:16]


class LedgerTamperError(RuntimeError):
    """Chuỗi hash đứt = sổ đã bị sửa/xoá. Mọi kết luận DSR/PBO dựa trên nó đều vô hiệu."""


class TestAlreadyTouchedError(RuntimeError):
    """TEST đã bị chạm cho campaign này. Chạm lần 2 = leak. Mở campaign mới nếu thật sự cần."""


class TrialLedger:
    """Sổ append-only. Một file cho một dataset_epoch (đổi data = đổi sổ)."""

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        d = os.path.dirname(os.path.abspath(path))
        if d:
            os.makedirs(d, exist_ok=True)

    # ---------------------------------------------------------------- đọc
    def records(self) -> Iterator[dict]:
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def last_hash(self) -> str:
        h = GENESIS_HASH
        for rec in self.records():
            h = rec["hash"]
        return h

    def verify(self) -> tuple[bool, str]:
        """Duyệt lại toàn bộ chuỗi. Trả (ok, thông điệp). Gọi TRƯỚC mọi lần tính DSR/PBO."""
        prev = GENESIS_HASH
        n = 0
        for rec in self.records():
            payload = {k: v for k, v in rec.items() if k != "hash"}
            want = hashlib.sha256((prev + canonical_json(payload)).encode("utf-8")).hexdigest()
            if rec.get("prev_hash") != prev:
                return False, f"rec#{n}: prev_hash lech (so={rec.get('prev_hash')} vs thuc={prev})"
            if rec.get("hash") != want:
                return False, f"rec#{n}: hash lech -> ban ghi da bi sua"
            prev = rec["hash"]
            n += 1
        return True, f"OK {n} ban ghi, chuoi lien tuc"

    # ---------------------------------------------------------------- ghi
    def append(self, *, campaign: str, phase: str, spec_fingerprint: str, dataset_epoch: str,
               knobs: dict, block: str, metrics: dict, seq: int, note: str = "") -> dict:
        """Ghi 1 lần đánh giá (1 config trên 1 block). seq = số thứ tự trial trong campaign.

        LƯU Ý: gọi 1 lần cho MỖI lần backtest thực sự chạy — kể cả lần bị bỏ, bị lỗi, chạy thử.
        Bỏ sót = tự làm nhẹ n_trials = tự nói dối DSR.
        """
        if phase not in PHASES:
            raise ValueError(f"phase phai thuoc {PHASES}, nhan '{phase}'")
        with self._lock:
            prev = self.last_hash()
            payload = {
                "seq": int(seq),
                "campaign": campaign,
                "phase": phase,
                "spec": spec_fingerprint,
                "dataset_epoch": dataset_epoch,
                "knobs": knobs,
                "block": block,
                "metrics": metrics,
                "note": note,
                "prev_hash": prev,
            }
            h = hashlib.sha256((prev + canonical_json(payload)).encode("utf-8")).hexdigest()
            rec = dict(payload)
            rec["hash"] = h
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(canonical_json(rec) + "\n")
            return rec

    # ---------------------------------------------------------------- đếm
    def n_trials(self, dataset_epoch: str | None = None, distinct_knobs: bool = True) -> int:
        """Số trial để nạp vào DSR.

        distinct_knobs=True: đếm số CẤU HÌNH KHÁC NHAU từng được thử (mỗi config chạy trên nhiều block
        vẫn là 1 trial). Đây là nghĩa đúng của n_trials trong Bailey-LdP.
        Đếm TOÀN BỘ phase (EXPLORE có tham gia định hình lựa chọn cuối ⇒ phải tính), TOÀN BỘ campaign
        trên cùng dataset_epoch — vì cùng một tập dữ liệu thì mọi lần thử đều tiêu tốn "độ tin cậy".
        """
        seen: set = set()
        n = 0
        for rec in self.records():
            if dataset_epoch is not None and rec["dataset_epoch"] != dataset_epoch:
                continue
            if distinct_knobs:
                seen.add(canonical_json(rec["knobs"]))
            else:
                n += 1
        return len(seen) if distinct_knobs else n

    def test_campaigns(self, dataset_epoch: str) -> set:
        return {r["campaign"] for r in self.records()
                if r["dataset_epoch"] == dataset_epoch and r["phase"] == "TEST"}

    def assert_test_allowed(self, dataset_epoch: str, campaign: str) -> None:
        """Chốt 'chạm TEST một lần'. Cứng, không có cờ bỏ qua — muốn chạm lại thì đổi campaign."""
        touched = self.test_campaigns(dataset_epoch)
        if campaign in touched:
            raise TestAlreadyTouchedError(
                f"campaign '{campaign}' DA cham TEST tren dataset '{dataset_epoch}'. "
                f"Cham lan 2 = leak. Mo campaign moi (doi spec) neu that su can.")
        if touched:
            logger.warning("dataset '%s' da bi cham TEST boi campaign khac: %s "
                           "-> DSR phai deflate theo TONG n_trials, khong phai rieng campaign nay",
                           dataset_epoch, sorted(touched))


# ---------------------------------------------------------------------------
def _selftest() -> None:
    import tempfile
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "trials.jsonl")
        led = TrialLedger(p)
        spec = {"knobs": {"TP": [0.01, 0.06]}, "O": "median-0.5std", "pass": {"pbo": 0.2}}
        sf = spec_hash(spec)
        # 3 config x 2 block = 6 ban ghi, nhung chi 3 TRIAL
        for i, tp in enumerate([0.02, 0.04, 0.06]):
            for b in ("b0", "b1"):
                led.append(campaign="c1", phase="EXPLORE", spec_fingerprint=sf,
                           dataset_epoch="ds_b329fa06", knobs={"TP": tp}, block=b,
                           metrics={"calmar": 0.5 + i}, seq=i)
        ok, msg = led.verify()
        logger.info("[LEDGER] verify=%s (%s)", ok, msg)
        assert ok
        nt = led.n_trials("ds_b329fa06")
        logger.info("[LEDGER] n_trials=%d (ky vong 3 config, khong phai 6 ban ghi)", nt)
        assert nt == 3

        # cham TEST lan 1 -> OK ; lan 2 -> phai raise
        led.assert_test_allowed("ds_b329fa06", "c1")
        led.append(campaign="c1", phase="TEST", spec_fingerprint=sf, dataset_epoch="ds_b329fa06",
                   knobs={"TP": 0.04}, block="test2025", metrics={"calmar": 0.9}, seq=99)
        try:
            led.assert_test_allowed("ds_b329fa06", "c1")
            raise AssertionError("PHAI raise o lan cham TEST thu 2")
        except TestAlreadyTouchedError:
            logger.info("[LEDGER] cham TEST lan 2 -> bi chan dung nhu thiet ke")

        # gia lap XOA 1 ban ghi xau -> chuoi phai dut
        lines = open(p, encoding="utf-8").read().splitlines()
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines[:2] + lines[3:]) + "\n")
        ok2, msg2 = led.verify()
        logger.info("[LEDGER] sau khi xoa len 1 ban ghi: verify=%s (%s)", ok2, msg2)
        assert not ok2

    logger.info("LEDGER SELF-TESTS PASSED")


if __name__ == "__main__":
    _selftest()
