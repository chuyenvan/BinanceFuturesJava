#!/usr/bin/env python3
"""Kiem "chi THEM lenh" muc method giua 2 jar. argv: ref.jar new.jar out.json class1 [class2 ...]
Moi method: day lenh (opcode + toan hang da bo chi so constant pool, giu comment javap = gia tri hang/ten method;
ldc_w -> ldc; khoang trang gop) cua ban cu phai la DAY CON cua ban moi theo SequenceMatcher chi gom 'equal' + 'insert'
(khong 'replace'/'delete'); moi lenh nhay/switch khop phai tro toi lenh khop tuong ung; bang exception cua ban cu
phai anh xa dung vao bang cua ban moi. In lenh duoc chen. Verdict IDENTICAL / ADDITIVE_OK / NOT_ADDITIVE."""
import difflib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import zipfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
log = logging.getLogger("methdiff3")
INS = re.compile(r"^\s+(\d+): (\w+)\s*(.*)$")
SW = re.compile(r"^\s+(-?\d+|default): (\d+)$")
EX = re.compile(r"^\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S.*)$")
BR = re.compile(r"^(if\w*|goto|goto_w|jsr|jsr_w)$")


def javap(jar, cls, td):
    p = os.path.join(td, "X.class")
    with zipfile.ZipFile(jar) as z:
        open(p, "wb").write(z.read(cls))
    return subprocess.run(["javap", "-c", "-p", "-constants", p], capture_output=True, text=True, check=True).stdout


def split_members(txt):
    out, cur, buf = {}, None, []
    for line in txt.splitlines():
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(";"):
            if cur is not None:
                out[cur] = buf
            cur, buf = line.strip(), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        out[cur] = buf
    return out


def parse(lines):
    """-> (ins: list[(key, targets)], ex: list[(from_i, to_i, tgt_i, type)], other: list[str])"""
    offs, order = {}, []
    for l in lines:
        m = INS.match(l)
        if m:
            offs[int(m.group(1))] = len(order)
            order.append(int(m.group(1)))
    end = len(order)
    ins, ex, other, in_ex, cur = [], [], [], False, None
    for l in lines:
        m = INS.match(l)
        if m:
            op, rest = m.group(2), m.group(3)
            op = "ldc" if op == "ldc_w" else op
            tg = []
            if BR.match(op):
                tg = [offs.get(int(rest.strip()))]
                rest = "BR"
            elif op in ("tableswitch", "lookupswitch"):
                rest = "SW"
            rest = re.sub(r"\s+", " ", re.sub(r"#\d+(:#\d+)?", "#", rest)).strip()
            cur = [op + " " + rest, tg]
            ins.append(cur)
            continue
        m = SW.match(l)
        if m and cur is not None and cur[0].startswith(("tableswitch", "lookupswitch")):
            cur[0] += " " + m.group(1)
            cur[1].append(offs.get(int(m.group(2))))
            continue
        if "Exception table" in l:
            in_ex = True
            continue
        m = EX.match(l)
        if in_ex and m:
            f, t, g = (int(x) for x in m.groups()[:3])
            ex.append((offs.get(f), offs.get(t, end if t >= (order[-1] if order else 0) else None), offs.get(g),
                       m.group(4).strip()))
            continue
        s = re.sub(r"\s+", " ", re.sub(r"#\d+(:#\d+)?", "#", l)).strip()
        if s and not s.startswith("from to target") and s != "Code:":
            other.append(s)
    return ins, ex, other


def analyse(a_lines, b_lines):
    ia, ea, oa = parse(a_lines)
    ib, eb, ob = parse(b_lines)
    ka, kb = [x[0] for x in ia], [x[0] for x in ib]
    if ka == kb and [x[1] for x in ia] == [x[1] for x in ib] and ea == eb and oa == ob:
        return "IDENTICAL", [], []
    sm = difflib.SequenceMatcher(None, ka, kb, autojunk=False)
    mp, inserted, problems = {}, [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                mp[i1 + k] = j1 + k
        elif tag == "insert":
            inserted.extend(kb[j1:j2])
        else:
            problems.append("%s A[%d:%d]=%s B[%d:%d]=%s" % (tag, i1, i2, ka[i1:i2][:4], j1, j2, kb[j1:j2][:4]))
    mp[len(ia)] = len(ib)
    for i, j in mp.items():
        if i >= len(ia):
            continue
        ta, tb = ia[i][1], ib[j][1]
        if [mp.get(t) for t in ta] != tb:
            problems.append("nhay lech o A%d (%s): %s -> %s" % (i, ia[i][0], ta, tb))
    exb = set(eb)
    for f, t, g, ty in ea:
        if (mp.get(f), mp.get(t), mp.get(g), ty) not in exb:
            problems.append("exception lech: %s" % ((f, t, g, ty),))
    if oa != ob:
        problems.append("phan khac (khong phai lenh) khac: %s" % list(difflib.unified_diff(oa, ob, lineterm="", n=0))[:6])
    return ("ADDITIVE_OK" if not problems else "NOT_ADDITIVE"), inserted, problems


def main():
    ref, new, outp = sys.argv[1:4]
    classes = sys.argv[4:]
    res = {}
    with tempfile.TemporaryDirectory() as td:
        for c in classes:
            a = split_members(javap(ref, c, td))
            b = split_members(javap(new, c, td))
            rc = {"added": sorted(set(b) - set(a)), "removed": sorted(set(a) - set(b)), "methods": {}}
            cnt = {}
            for k in sorted(set(a) & set(b)):
                v, ins, pb = analyse(a[k], b[k])
                cnt[v] = cnt.get(v, 0) + 1
                if v != "IDENTICAL":
                    rc["methods"][k] = {"verdict": v, "inserted": ins, "problems": pb}
                    print("%s %s :: %s" % (v, c.split("/")[-1], k))
                    for x in ins:
                        print("      + " + x)
                    for x in pb:
                        print("      ! " + x)
            rc["count"] = cnt
            res[c] = rc
            log.info("%s: %s added=%d removed=%d", c, cnt, len(rc["added"]), len(rc["removed"]))
    json.dump(res, open(outp, "w"), indent=1)


if __name__ == "__main__":
    main()
