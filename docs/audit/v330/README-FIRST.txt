SKRIBL v330 -- THE AUDIT PACKET
================================

Eight files, each under 30 MB. Python 3.12 comes in two halves that one
line joins (part 4); nothing else needs joining or unsplitting.

  README-FIRST.txt                          this note
  SHA256SUMS-packet.txt                     the SHA-256 of every other file here
  skribl-v330-source.zip         29.8 MB    the repository as tracked at the seal
  skribl-v330-runtime.zip        18.9 MB    what a deployment needs, boot-verified
  skribl-v330-evidence.zip       10.8 MB    harness, fixtures, release records
  skribl-wheels-cp312-linux-x86_64.zip
                                 18.1 MB    every Python package, for running offline
                                            (README-OFFLINE.txt inside says how)
  cpython-3.12.13-linux-x86_64.tar.gz.part1
                                 17.1 MB    Python 3.12 itself, in two halves,
  cpython-3.12.13-linux-x86_64.tar.gz.part2
                                 17.1 MB    for a machine without it (part 4)

Start with the source zip: its ARCHIVE-README.md says what each package is,
and START-HERE.md is the project's own primer.


1. CHECK THE FILES ARRIVED WHOLE

    sha256sum -c SHA256SUMS-packet.txt          # every line must say OK

The three release zips each carry their own SHA256SUMS inside, covering
every file in them; ARCHIVE-README.md ("Verifying the seal") gives the two
lines to run. The wheels zip has none inside: the line for it in
SHA256SUMS-packet.txt covers it, and pip checks the app's wheels against
constraints.txt as they install (part 2).


2. CHECK WHERE THE THREE RELEASE ZIPS CAME FROM

These are byte-for-byte the zips GitHub built from main at the seal commit
(5fbfd3d30c9de0173b611f73671abe1bd76656c2), attested and published as the
v330 Release of MrBlood/skribl-live-demo. You do not have to trust this
packet for that:

    gh attestation verify skribl-v330-source.zip   --repo MrBlood/skribl-live-demo
    gh attestation verify skribl-v330-runtime.zip  --repo MrBlood/skribl-live-demo
    gh attestation verify skribl-v330-evidence.zip --repo MrBlood/skribl-live-demo

and the Release page lists the same SHA-256s as SHA256SUMS-packet.txt.

The wheels zip is not attested. The app's own packages install from it with
pip's --require-hashes against constraints.txt in the source zip, so pip
refuses any wheel whose hash differs. The test harness's Flask-WTF, WTForms
and Pillow install from the same zip without hashes; the app imports none of
the three.


3. WHAT THE SEAL SAYS (read the numbers there, not here)

harness/RELEASE.md in the source and evidence zips is the generated record:
FULL RELEASE PASS, every suite on disk reporting, the tested tree hash, and
the one suite that cannot run in the seal's container (the migration chain on
PostgreSQL 16), named with the GitHub Actions job that ran it on the same
tree. The H.264 export suite ran in the seal itself this time (the browser
the harness drives is now Chromium 153, which encodes H.264) and in real
Chrome on GitHub Actions, on the same tree.

DECISIONS.md, "v330 -- the seal of everything since v329", says what changed
since v329, and what the move to the new browser found and fixed: a broken
MP4 export in Firefox 155, a long drawing's file opening in one long task,
and four checks that read the new browser wrong.

How this seal was run, said plainly. It was started five times. The first
three were stopped early, on purpose, to fix what the new browser had just
shown. The fourth went red at its twelfth batch on one timing row of
verify_helpdemos (How it works rising on Flip, "no frame jumping 40% of the
way"): the page held a frame as the sheet set off. The same row passed on
GitHub Actions on the same tree and in ten runs here. The fifth start ran the
whole battery again, from the start, on the same tree with that row
unchanged, and is the record. The row's fix (telling a held start from a
snap, on the transition's own clock checked against the wall clock) comes
after the seal; pull request #694 says the same.


4. RUN IT, OFFLINE, ON PYTHON 3.12

The wheels are built for Linux on x86_64 with Python 3.12, the version the
app is deployed and sealed on, and harness/bootstrap.sh stops on a machine
without python3.12. If yours has it, go to the README-OFFLINE.txt lines. If
not, Python 3.12 is here, in two halves. Joined, they are
python-build-standalone's own build, byte for byte: release 20260718 of
github.com/astral-sh/python-build-standalone, the file
cpython-3.12.13+20260718-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz,
SHA-256 5854aa6ec71cad00334d5065633c210b2e7feb40956767a59a91791cadcf0b79,
which is what that release's own SHA256SUMS lists for it (the same two
halves v328's packet sent). It runs without installing anything.

Unzip the source zip, put the wheels zip and the two halves in the folder it
makes (skribl-v330-source/), and run these lines there, in one shell, so that
the PATH and the environment carry from line to line:

    cat cpython-3.12.13-linux-x86_64.tar.gz.part1 cpython-3.12.13-linux-x86_64.tar.gz.part2 > cpython-3.12.13-linux-x86_64.tar.gz
    sha256sum cpython-3.12.13-linux-x86_64.tar.gz     # 5854aa6e...0b79, as above
    tar -xzf cpython-3.12.13-linux-x86_64.tar.gz      # makes ./python
    export PATH="$PWD/python/bin:$PATH"               # python3.12 is now this one
    python3.12 -V                                     # Python 3.12.13

then the lines of README-OFFLINE.txt, from the wheels zip, exactly as
written: the unzip, the environment, the two installs, harness/bootstrap.sh.

That whole sequence was run before this packet was made, from this packet's
own source zip, wheels zip and halves, in an empty folder, with pip's
network refused (no index, and every outside address sent to a proxy that
does not answer): python3.12 was the joined Python, 3.12.13, the two
installs came from the wheels alone, and bootstrap.sh brought the app up on
Python 3.12.13 (Flask 3.1.3), its home page (the Pad), Flip, the Gallery and
the Library answering 200. The machine's own Python 3.12 was still
installed; the joined one came first on the PATH, and that is the one the
environment and the app ran on. If the sandbox will not run programs from
where the files sit ("Permission denied"), do all of this in a copy under
/tmp.

Playwright and its browser are not included (hundreds of MB); the harness's
browser suites need them, Playwright 1.63 with its Chromium build 1243
(harness/requirements.txt says why the two go together). The app itself
needs neither.


5. WHAT THE OWNER CHECKED BY HAND

No list of hand checks was run for this seal. The entries under "After
v329" in DECISIONS.md say what each merge since the last seal did, how it
was checked, and where the owner looked at it on a phone.


6. WHAT WAS NOT TESTED

The seal ran in a Linux container: Chromium 153 only, and the open fonts it
has. Nothing in the seal ran in Safari, on an iPhone, or with the Windows
(Segoe UI) or Apple (SF) system fonts. Outside the seal, GitHub Actions ran a
WebKit smoke on an iPhone's screen and a Firefox smoke on the same tree, both
green; those are smokes, a few rows each, not the harness. Firefox 155's MP4
fix was checked by that Firefox smoke, not in a Firefox here.
