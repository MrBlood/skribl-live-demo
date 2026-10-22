SKRIBL v328 -- THE AUDIT PACKET
================================

Six files, each under 30 MB. Nothing needs joining or unsplitting.

  README-FIRST.txt                          this note
  SHA256SUMS-packet.txt                     the SHA-256 of every other file here
  skribl-v328-source.zip         26.3 MB    the repository as tracked at the seal
  skribl-v328-runtime.zip        18.4 MB    what a deployment needs, boot-verified
  skribl-v328-evidence.zip        7.9 MB    harness, fixtures, release records
  skribl-wheels-cp312-linux-x86_64.zip
                                 18.1 MB    every Python package, for running offline
                                            (README-OFFLINE.txt inside says how)

Start with the source zip: its ARCHIVE-README.md says what each package is,
and START-HERE.md is the project's own primer.


1. CHECK THE FILES ARRIVED WHOLE

    sha256sum -c SHA256SUMS-packet.txt          # every line must say OK

Each zip also carries its own SHA256SUMS inside, covering every file in it;
ARCHIVE-README.md ("Verifying the seal") gives the two lines to run.


2. CHECK WHERE THE THREE RELEASE ZIPS CAME FROM

These are byte-for-byte the zips GitHub built from main at the seal commit
(98067f8da84cfe0b46d222e61f62da671d361a8a), attested and published as the
v328 Release of MrBlood/skribl-live-demo. You do not have to trust this
packet for that:

    gh attestation verify skribl-v328-source.zip   --repo MrBlood/skribl-live-demo
    gh attestation verify skribl-v328-runtime.zip  --repo MrBlood/skribl-live-demo
    gh attestation verify skribl-v328-evidence.zip --repo MrBlood/skribl-live-demo

and the Release page lists the same SHA-256s as SHA256SUMS-packet.txt.
The wheels zip is not attested: its pins are constraints.txt's hashes in the
source zip, and pip checks every wheel against them on install.


3. WHAT THE SEAL SAYS (read the numbers there, not here)

harness/RELEASE.md in the source and evidence zips is the generated record:
FULL RELEASE PASS on SQLite, every suite on disk reporting, the tested tree
hash, and the two suites that cannot run in the seal's container listed by
name, each attested on the same tree by GitHub Actions (H.264 export in real
Chrome; the migration chain on PostgreSQL 16).


4. RUN IT, OFFLINE

Unzip the source zip, put the wheels zip beside it, and follow
README-OFFLINE.txt from the wheels zip: it makes a virtual environment,
installs every package with pip's network refused, and harness/bootstrap.sh
builds a fresh database and starts the app. That exact sequence was run
before this packet was made, in an unpacked copy, with the network off, to
an app that answered.

Playwright and its browser are not included (hundreds of MB); the harness's
browser suites need them. The app itself does not.


5. WHAT THE OWNER CHECKED BY HAND

Before this seal the owner went through thirteen checks on a Windows desk.
DECISIONS.md, in its "v328 -- the seal of everything since v327" entry, says
how each came out: nine passed; one failed and was fixed, with a check that
fails without the fix (the pointer over Flip's canvas in Recolor, #581); one
passed with a note that was fixed the same way (the canvas showing before
the hello on a reload, #582); two were not done on the PC and are covered by
verify_recolorplay. The entries above it, under "After v327", say what each
merge since the last seal did and how it was checked.


6. WHAT WAS NOT TESTED

There is no WebKit in the build container, so nothing here was run in
Safari or on an iPhone, which is where the owner uses it. The Windows (Segoe
UI) and Apple (SF) system fonts are not present either; type was checked in
the open fonts the container has. The owner's hand checks above were on
Windows, not on the iPhone.
