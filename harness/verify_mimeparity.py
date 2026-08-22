"""Every MIME spelling validation accepts must map to a real extension+type.

THE GAP (outside review, P1). Validation accepted 20 spellings; the storage
tables mapped 13. The other seven — audio/flac, audio/x-flac, audio/opus,
audio/m4a, audio/x-m4a, audio/vnd.wave, image/jpg — fell through `_EXT.get(...,
".bin")` and were served back as application/octet-stream: bytes the validator
had just PROVED were FLAC arriving at an <audio> element as a type it refuses
to probe. The upload succeeded, the post rendered, the audio was silent.

Pinned STRUCTURALLY, not as a list of seven: the invariant is that the two
modules agree, so this recomputes the accepted set from validation's own tables
and requires every member to round-trip through storage's. A new accepted
spelling added without its mapping fails here on arrival.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


from skribl import validation as V
from skribl import storage as S

accepted = ({f"audio/{s}" for s in V.ALLOWED_AUDIO_SUBTYPES}
            | {f"image/{s}" for s in V.ALLOWED_IMAGE_SUBTYPES})

print(f"\nMIME PARITY — {len(accepted)} accepted spellings, every one mapped")
unmapped = sorted(t for t in accepted if t not in S._EXT)
check("every accepted MIME spelling has an extension in _EXT",
      not unmapped, f"missing: {unmapped}")

badext = sorted(t for t in accepted
                if S._EXT.get(t) and S._EXT[t] not in S._TYPE_FOR_EXT)
check("every mapped extension has a canonical serve type in _TYPE_FOR_EXT",
      not badext, f"extension unserved for: {badext}")

for t in sorted(accepted):
    ext = S._EXT.get(t)
    served = S._TYPE_FOR_EXT.get(ext) if ext else None
    check(f"{t} -> {ext} -> {served}",
          bool(ext) and ext != ".bin" and bool(served)
          and served.split("/")[0] == t.split("/")[0],
          "octet-stream fallback" if not served else "")

# The normalisation property the tables promise: aliases of one format share
# one extension, so identical bytes are served identically whichever spelling
# the uploader sent.
for aliases, ext in ((("audio/wav", "audio/x-wav", "audio/wave",
                       "audio/vnd.wave"), ".wav"),
                     (("audio/flac", "audio/x-flac"), ".flac"),
                     (("audio/mp4", "audio/m4a", "audio/x-m4a"), ".m4a"),
                     (("image/jpeg", "image/jpg"), ".jpg")):
    check(f"{' / '.join(aliases)} all normalise to {ext}",
          all(S._EXT.get(a) == ext for a in aliases),
          str({a: S._EXT.get(a) for a in aliases}))

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(f"{n} ({d})" for n, d in bad)) if bad else ""))
sys.exit(1 if bad else 0)
