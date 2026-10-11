#!/usr/bin/env python3
"""F2: so thoi diem trading 242 doc nen M (log 'Start check level change' giay 6-10 cua M+1) voi thoi diem
ingest ghi chot nen M (log 'Chot nen phut M' ngay SAU writeMinuteBatch). Input: stdin tu kfix_r3.sh (CHI DOC log 242).
Dong I: 'I dd/MM/yyyy HH:mm:ss.SSS HH:MM(phut M) ...'; dong T: 'T dd/MM/yyyy HH:mm:ss.SSS'."""
import datetime, logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("kfix_race")
ing, trd = {}, {}
for l in sys.stdin:
    p = l.split()
    if len(p) < 3:
        continue
    t = datetime.datetime.strptime(p[1] + " " + p[2], "%d/%m/%Y %H:%M:%S.%f")
    if p[0] == "I":
        hh, mm = p[3].split(":")
        m = t.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if m > t:
            m -= datetime.timedelta(days=1)
        ing[m] = (t - m).total_seconds() - 60
    elif p[0] == "T":
        m = t.replace(second=0, microsecond=0) - datetime.timedelta(minutes=1)
        trd.setdefault(m, (t - m).total_seconds() - 60)
both = sorted(set(ing) & set(trd))
d = [trd[k] - ing[k] for k in both]
q = lambda a, p: sorted(a)[min(len(a) - 1, int(p * len(a)))]
iv, tv = list(ing.values()), list(trd.values())
log.info("ingest log 'Chot nen M' (giay sau khi M dong): p1 %.2f p50 %.2f p99 %.2f max %.2f n=%d", q(iv, .01), q(iv, .5), q(iv, .99), max(iv), len(iv))
log.info("trading doc nen M (giay sau khi M dong): p1 %.2f p50 %.2f p99 %.2f max %.2f n=%d", q(tv, .01), q(tv, .5), q(tv, .99), max(tv), len(tv))
late = [x for x in d if x < 0]
log.info("phut co ca 2=%d ; trading DOC TRUOC khi ingest chot M: %d (%.1f%%) ; chenh p50 %.3fs", len(both), len(late), 100.0 * len(late) / max(1, len(both)), q(d, .5))
miss = [k for k in trd if k not in ing]
log.info("phut trading doc ma ingest KHONG co log chot M: %d", len(miss))
