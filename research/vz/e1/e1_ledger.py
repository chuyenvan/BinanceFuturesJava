"""VZ E1 - exploration ledger helper (docs/research/VZ_EXPLORE_LEDGER.md).

One row per variant whose outcome was computed. T2 (pure description) records
0 tests as a single note row.
"""
import os

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "..", "..", "docs", "research", "VZ_EXPLORE_LEDGER.md")
HEADER = ("# VZ EXPLORE LEDGER - so phep thu kham pha 2024\n\n"
          "Mỗi biến thể ĐÃ TÍNH outcome = 1 dòng. Vai trò năm: `docs/plan/VZ_RESEARCH_SPLIT.md`.\n"
          "Chi phí: bucket EXEC thực + phí 2 chân (SIM_RATE_FEE=0.000982). "
          "Bootstrap block 5 ngày, NREP 2000, seed 20261014.\n\n"
          "| # | task | họ | biến thể | n sự kiện | kết quả chính | ngày |\n"
          "|---|---|---|---|---|---|---|\n")


def ensure(path=LEDGER):
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(HEADER)
    return path


def count(path=LEDGER):
    path = ensure(path)
    n = 0
    with open(path) as f:
        for line in f:
            if line.startswith("|") and "task" not in line and "---" not in line:
                n += 1
    return n


def append(rows, path=LEDGER):
    """rows: list of dicts(task, family, variant, n, result, date)."""
    path = ensure(path)
    start = count(path) + 1
    with open(path, "a") as f:
        for i, r in enumerate(rows):
            f.write("| %d | %s | %s | %s | %s | %s | %s |\n" % (
                start + i, r["task"], r["family"], r["variant"], r["n"],
                r["result"], r["date"]))
    return count(path)


def note(text, path=LEDGER):
    path = ensure(path)
    with open(path, "a") as f:
        f.write("\n> %s\n" % text)
