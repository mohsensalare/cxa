"""Exercise cxa's Windows branches from a Unix machine.

Forces os.name to "nt" and stubs msvcrt, so the console reading, tasklist
parsing and launcher paths can be checked without a Windows box. Run it with
`python3 test_windows.py` from the repository root; it prints a line per check
and raises on the first failure.
"""
# Imported first so cxa's own imports are cache hits: shutil reads os.name at
# import time and would fail once it is patched.
import base64, calendar, ctypes, dataclasses, glob, json, re, shutil, subprocess
import sys, time, typing, urllib.error, urllib.request
import importlib.machinery, importlib.util, os, types
from unittest import mock

keys = []
stub = types.ModuleType("msvcrt"); stub.getwch = lambda: keys.pop(0)
sys.modules["msvcrt"] = stub

spec = importlib.util.spec_from_loader("cxa", importlib.machinery.SourceFileLoader(
    "cxa", os.path.join(os.path.dirname(os.path.abspath(__file__)), "cxa")))
cxa = importlib.util.module_from_spec(spec)
sys.modules["cxa"] = cxa                       # dataclass resolves types via this
with mock.patch.object(os, "name", "nt"):
    spec.loader.exec_module(cxa)

assert cxa.WINDOWS and cxa.DAY_FORMAT == "%b %#d" and cxa.NEWLINE == "\n"
print("platform     WINDOWS=True  DAY_FORMAT=%r  NEWLINE=%r" % (cxa.DAY_FORMAT, cxa.NEWLINE))
assert cxa.DIM == "" and cxa.enable_ansi() is False
print("ansi         refused (no ctypes.windll here) -> colours disabled, not garbled")
assert cxa.make_private("/nonexistent/path") is None
print("make_private no-op, and never raises on a path chmod would reject")

for sequence, expect in [(["a"], "a"), (["Z"], "Z"), (["\x1b"], "esc"),
                         (["\x00", "H"], "up"), (["\xe0", "H"], "up"),
                         (["\x00", "P"], "down"), (["\xe0", "P"], "down"),
                         (["\r"], "\r"), (["\x08"], "\x08"), (["\t"], "\t"),
                         (["\x03"], "\x03"), (["\xe0", "S"], "")]:
    keys[:] = sequence
    got = cxa.read_key()
    assert got == expect, (sequence, got, expect)
print("read_key     12/12 sequences decode (arrows, esc, enter, backspace, tab, ctrl-c)")

def raising():
    raise KeyboardInterrupt
stub.getwch = raising
assert cxa.read_key() == "\x03"
stub.getwch = lambda: keys.pop(0)
print("read_key     a console Ctrl-C comes back as \\x03, so the picker quits cleanly")

sample = ('"System Idle Process","0","Services","0","8 K"\n'
          '"codex.exe","19244","Console","1","112,404 K"\n'
          '"codex.exe","4120","Console","1","64,000 K"\n'
          '"ChatGPT.exe","7788","Console","1","250,112 K"\n'
          '"chrome.exe","5012","Console","1","98,000 K"\n')
with mock.patch.object(cxa, "process_list", lambda cmd: sample):
    assert cxa.running_codex() == ([19244, 4120], True), cxa.running_codex()
print("tasklist     two codex.exe found, ChatGPT.exe seen, chrome ignored")
with mock.patch.object(cxa, "process_list", lambda cmd: ""):
    assert cxa.running_codex() == ([], False)
print("tasklist     missing or failing -> ([], False), never blocks a switch")

with mock.patch.object(cxa.shutil, "which", lambda n: r"C:\Users\me\AppData\npm\codex.cmd"), \
     mock.patch.object(cxa.subprocess, "run") as run, \
     mock.patch.object(cxa.os.path, "exists", lambda p: True), \
     mock.patch.object(cxa.os, "remove", lambda p: None), \
     mock.patch.object(cxa, "save_active", lambda name=None: None), \
     mock.patch.object(cxa, "sync_active", lambda: None):
    cxa.login()
    assert run.call_args[0][0] == ["cmd", "/c", r"C:\Users\me\AppData\npm\codex.cmd", "login"]
print("login        a .cmd shim is launched through cmd.exe:", run.call_args[0][0])
