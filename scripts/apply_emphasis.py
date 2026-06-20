#!/usr/bin/env python3
"""Apply Sparse spoken-emphasis italics to the book edition.
Detect acoustic prominence (loudness/duration/pitch/pause) per word, pick sparse
per-sentence peaks, align the transcript to the book with difflib, and italicize
only eligible prose tokens (never scripture/headings/front-matter)."""
import json, wave, math, re, sys, difflib, pathlib, glob
import numpy as np

# Run from inside a sermon working dir. Auto-detects the book source file.
WAV, JS = "emphasis_full/audio.wav", "emphasis_full/audio.json"
_books = [f for f in sorted(glob.glob("SERMON-*-BOOK.md")) if "-emph" not in f]
if not _books:
    sys.exit("apply_emphasis: no SERMON-*-BOOK.md found in current directory")
BOOK = _books[0]
OUT  = BOOK[:-len("-BOOK.md")] + "-BOOK-emph.md"
PCT  = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0   # Sparse default = top 3% of content words

# ---------- audio + pitch ----------
w = wave.open(WAV, "rb"); sr = w.getframerate()
pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0
w.close()
WIN, HOP = int(0.04 * sr), int(0.01 * sr)
FMIN, FMAX = 80, 300
han = np.hanning(WIN); nfft = 1 << int(np.ceil(np.log2(2 * WIN)))
lag_min, lag_max = int(sr / FMAX), int(sr / FMIN)
grms = math.sqrt(float(np.mean(pcm * pcm)))
f0_t, f0_v = [], []
for s in range(0, len(pcm) - WIN, HOP):
    fr = pcm[s:s + WIN]
    if math.sqrt(float(np.mean(fr * fr))) < 0.12 * grms:
        continue
    fr = (fr - fr.mean()) * han
    F = np.fft.rfft(fr, nfft); acf = np.fft.irfft(F * np.conj(F))[:WIN]
    if acf[0] <= 0:
        continue
    k = int(np.argmax(acf[lag_min:lag_max])); peak = k + lag_min
    if peak <= lag_min or peak >= lag_max - 1 or acf[peak] / acf[0] < 0.45:
        continue
    a0, b0, c0 = acf[peak - 1], acf[peak], acf[peak + 1]; den = a0 - 2 * b0 + c0
    lag = peak + (0.5 * (a0 - c0) / den if abs(den) > 1e-12 else 0.0)
    f0_t.append((s + WIN / 2) / sr); f0_v.append(sr / lag)
f0_t, f0_v = np.array(f0_t), np.array(f0_v)
print(f"voiced pitch frames: {len(f0_v)}")

def rms_db(a, b):
    seg = pcm[int(a * sr):int(b * sr)]
    return -90.0 if seg.size < 1 else 20 * math.log10(math.sqrt(float(np.mean(seg*seg)) + 1e-12) + 1e-9)
def wpitch(a, b):
    m = (f0_t >= a) & (f0_t <= b)
    return float(np.median(f0_v[m])) if m.any() else np.nan

STOP = {"a","an","the","of","to","in","on","is","are","was","were","be","been","am",
        "and","or","but","that","this","these","those","it","its","he","she","they",
        "we","you","his","her","their","our","your","my","as","at","by","for","with",
        "from","into","what's","what","so","then","there","here","i",
        "one","all","up","off","if","both","out","me","us","him","them",
        "also","just","very","more","much","even","had","has","have","will","would"}

data = json.load(open(JS))
W, prev = [], None
for seg in data["segments"]:
    for wd in seg.get("words", []):
        tok = wd["word"].strip()
        if not tok:
            continue
        a, b = wd["start"], wd["end"]
        letters = sum(c.isalpha() for c in tok) or 1
        W.append(dict(tok=tok, start=a, end=b, spc=(b - a) / letters,
                      rms=rms_db(a, b), pitch=wpitch(a, b), letters=letters,
                      pause=0.0 if prev is None else max(0.0, a - prev),
                      stop=tok.lower().strip(".,;:!?—-\"'“”’()") in STOP,
                      endsent=tok.rstrip("\"'”’)").endswith((".", "?", "!", ";"))))
        prev = b
N = len(W)

# ---------- local z-scores over content words ----------
def feat(k): return np.array([x[k] for x in W], float)
rms, spc, pit, pause = feat("rms"), feat("spc"), feat("pitch"), feat("pause")
from collections import Counter
def _n(t): return t.lower().strip(".,;:!?—-\"'“”’()").replace("’", "'")
freq = Counter(_n(x["tok"]) for x in W if not x["stop"] and x["letters"] >= 2)
FREQUENT = {wd for wd, c in freq.items() if c >= 25}      # ubiquitous theme words -> not "emphasis"
print("demoted frequent words:", " ".join(sorted(FREQUENT)))
content = np.array([(not x["stop"]) and x["letters"] >= 2 and _n(x["tok"]) not in FREQUENT
                    for x in W])
def local_z(vals, half=400):
    z = np.zeros(N)
    for i in range(N):
        lo, hi = max(0, i - half), min(N, i + half + 1)
        seg = vals[lo:hi]; m = content[lo:hi] & ~np.isnan(seg)
        base = seg[m] if m.sum() >= 8 else vals[~np.isnan(vals)]
        mu, sd = base.mean(), (base.std() or 1.0)
        z[i] = 0.0 if np.isnan(vals[i]) else (vals[i] - mu) / sd
    return z
zr, zd, zf = local_z(rms), local_z(spc), local_z(pit)
zp = (pause - pause.mean()) / (pause.std() or 1)
score = zr + 0.9 * zd + 1.0 * zf + 0.5 * zp

# ---------- sparse selection ----------
sentences, cur = [], []
for i, x in enumerate(W):
    cur.append(i)
    if x["endsent"]:
        sentences.append(cur); cur = []
if cur:
    sentences.append(cur)

sc = score[content & ~np.isnan(score)]
thr = float(np.percentile(sc, 100 - PCT))         # global prominence cutoff
cand_flags = content & (score >= thr)
emph, recent = set(), []
for sent in sentences:                            # >=1 strong outlier per sentence, else nothing
    cands = [i for i in sent if cand_flags[i]]
    if not cands:
        continue
    best_i = max(cands, key=lambda i: score[i])
    lemma = W[best_i]["tok"].lower().strip(".,;:!?—-\"'“”’()")
    if lemma in recent[-8:]:                       # suppress litany repetition
        continue
    idxs = {best_i}                                # collapse an adjacent phrase
    j = best_i - 1
    while j >= sent[0] and content[j] and score[j] >= thr * 0.8:
        idxs.add(j); j -= 1
    j = best_i + 1
    while j <= sent[-1] and content[j] and score[j] >= thr * 0.8:
        idxs.add(j); j += 1
    emph |= idxs
    recent.append(lemma)
print(f"sentences: {len(sentences)}   top {PCT}% cutoff score={thr:.2f}   emphasized words: {len(emph)}")

# ---------- align to book + italicize ----------
book_lines = pathlib.Path(BOOK).read_text(encoding="utf-8").split("\n")
def eligible(ln):
    s = ln.strip()
    return not (s == "" or s.startswith(("#", ">", "---", "<!--", "[^", "*")))
TOK = re.compile(r"[A-Za-z][A-Za-z'’]*")
EMSPAN = re.compile(r"\*+[^*\n]+\*+")          # existing markdown emphasis on the line
book_tokens = []   # (line, mstart, mend, norm, eligible)
for li, ln in enumerate(book_lines):
    base_el = eligible(ln)
    spans = [(m.start(), m.end()) for m in EMSPAN.finditer(ln)]
    for m in TOK.finditer(ln):
        in_em = any(a <= m.start() < b for a, b in spans)
        book_tokens.append((li, m.start(), m.end(),
                            m.group().lower().replace("’", "'"), base_el and not in_em))

def norm(t): return t.lower().strip(".,;:!?—-\"'“”’()").replace("’", "'")
tr_norm = [norm(x["tok"]) for x in W]
bk_norm = [bt[3] for bt in book_tokens]
sm = difflib.SequenceMatcher(None, tr_norm, bk_norm, autojunk=False)
tr2bk = {}
for blk in sm.get_matching_blocks():
    for k in range(blk.size):
        tr2bk[blk.a + k] = blk.b + k

book_emph, mapped = set(), 0
for ti in emph:
    bi = tr2bk.get(ti)
    if bi is None:
        continue
    mapped += 1
    if book_tokens[bi][4]:
        book_emph.add(bi)
print(f"mapped to book: {mapped}/{len(emph)}   applied (prose only): {len(book_emph)}")

byline = {}
for bi in book_emph:
    li, a, b, _, _ = book_tokens[bi]
    byline.setdefault(li, []).append((a, b))
applied = []
for li in sorted(byline):
    spans = sorted(byline[li]); ln = book_lines[li]
    merged = []
    for a, b in spans:                      # merge tokens separated only by whitespace
        if merged and ln[merged[-1][1]:a].strip() == "":
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    for a, b in merged:
        applied.append(ln[a:b])
    for a, b in reversed(merged):
        ln = ln[:a] + "*" + ln[a:b] + "*" + ln[b:]
    book_lines[li] = ln
print("applied phrases:\n  " + "\n  ".join(applied))

pathlib.Path(OUT).write_text("\n".join(book_lines), encoding="utf-8")
print(f"wrote {OUT}")
