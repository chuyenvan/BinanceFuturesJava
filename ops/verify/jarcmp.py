#!/usr/bin/env python3
"""So 2 jar theo CRC32 tung entry. argv: ref.jar new.jar [out.json]. In: so entry trung/khac/chi-ref/chi-new + danh sach khac."""
import json
import logging
import sys
import zipfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
log = logging.getLogger("jarcmp")


def crcs(p):
    with zipfile.ZipFile(p) as z:
        return {i.filename: i.CRC for i in z.infolist() if not i.is_dir()}


def main():
    a, b = crcs(sys.argv[1]), crcs(sys.argv[2])
    same = [k for k in a if k in b and a[k] == b[k]]
    diff = sorted(k for k in a if k in b and a[k] != b[k])
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    cls_same = sum(1 for k in same if k.endswith(".class"))
    res = {"ref": sys.argv[1], "new": sys.argv[2], "n_ref": len(a), "n_new": len(b), "same": len(same),
           "same_class": cls_same, "diff": diff, "only_ref": only_a, "only_new": only_b}
    log.info("ref=%d new=%d same=%d (class %d) diff=%d only_ref=%d only_new=%d", len(a), len(b), len(same), cls_same,
             len(diff), len(only_a), len(only_b))
    for k in diff:
        print("DIFF", k)
    for k in only_a:
        print("ONLY_REF", k)
    for k in only_b:
        print("ONLY_NEW", k)
    if len(sys.argv) > 3:
        json.dump(res, open(sys.argv[3], "w"), indent=1)


if __name__ == "__main__":
    main()
