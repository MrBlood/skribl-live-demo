"""verify_onepill, again, with Panels set to Colour.

Colour makes the panels you open to work with a block of Skribl violet, and
every pill inside one re-themes by its tokens: a white pill with violet ink on
the block, the dock's selected tool solid violet. This runs verify_onepill's
census, tray and fallback under Colour -- one placed pill, the one shape, and
every label's contrast read on what is painted -- on the two editors, where
the blocks are.

Its own suite because it is its own budget: Calm and Colour in one process
ran 618s against run_harness.sh's 600s per suite. verify_onepill.py runs Calm,
and its COLOUR BLOCK section checks which surfaces are blocks under each.
"""
import os
import pathlib
import runpy

os.environ.setdefault("ONEPILL_PANELS", "colour")
os.environ.setdefault("ONEPILL_SECTIONS", "census,tray,fallback")
runpy.run_path(str(pathlib.Path(__file__).with_name("verify_onepill.py")), run_name="__main__")
