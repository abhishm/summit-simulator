"""Offline checks that the strict packet verifier catches real errors.

uv run python tests/test_packets_verify.py   (or pytest, if installed)
"""
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.packets import schedule, verify, verify_artifacts  # noqa: E402

RUN = json.loads((ROOT / "data/runs/demo-5block.json").read_text())
SCHED = schedule(RUN["history"][2]["plan"])
IDS = [p["id"] for p in RUN["personas"]]
PERS = RUN["personas"]
BUNDLE = ROOT / "data/approved/demo-5block-r2-bundle.zip"


def _packets() -> dict[str, str]:
    if BUNDLE.exists():
        z = zipfile.ZipFile(BUNDLE)
        return {Path(n).stem: z.read(n).decode() for n in z.namelist() if n.startswith("packets/") and n.endswith(".md")}
    d = ROOT / "data/approved/demo-5block-r2-packets"
    return {f.stem: f.read_text() for f in d.glob("*.md")}


def _errs(pk, pid="eu_regulator"):
    return [e for e in verify(SCHED, pk, IDS, PERS) if e.startswith(pid)]


def _mut(fn, pid="eu_regulator"):
    pk = _packets()
    new = fn(pk[pid])
    assert new != pk[pid], "corruption did not change the packet"
    pk[pid] = new
    return _errs(pk, pid)


def test_cached_packet_is_clean():
    assert _errs(_packets()) == []


def test_room_swapped_on_line():
    errs = _mut(lambda md: md.replace("09:00-10:00 | Breakout A", "09:00-10:00 | Breakout C", 1))
    assert any("block 1 room 'Breakout C'" in e for e in errs), errs


def test_time_and_room_on_different_lines():
    # the right start time and room both still appear in the packet, but not on the same line
    errs = _mut(lambda md: md.replace("10:15-11:15 | Breakout B", "10:15-11:15 | Breakout A", 1))
    assert any("block 2 room" in e for e in errs), errs


def test_wrong_end_time():
    errs = _mut(lambda md: md.replace("09:00-10:00 |", "09:00-10:30 |", 1))
    assert any("block 1 ends 10:30" in e for e in errs), errs


def test_extra_coparticipant():
    def f(md):
        lines = md.splitlines()
        i = next(i for i, ln in enumerate(lines) if ln.lstrip("- ").startswith("09:00-10:00"))
        lines[i] += ", labor_advocate (Labor)"
        return "\n".join(lines)
    errs = _mut(f)
    assert any("block 1 lists labor_advocate" in e for e in errs), errs


def test_missing_coparticipant():
    def f(md):
        lines = md.splitlines()
        i = next(i for i, ln in enumerate(lines) if ln.lstrip("- ").startswith("09:00-10:00"))
        lines[i] = lines[i].replace("uk_aisi", "someone")
        return "\n".join(lines)
    errs = _mut(f)
    assert any("block 1 co-participant uk_aisi missing" in e for e in errs), errs


def test_missing_openings_section():
    def f(md):
        return "\n".join(ln.replace("Openings", "Notes").replace("openings", "notes") if ln.startswith("## ") else ln
                         for ln in md.splitlines())
    errs = _mut(f)
    assert any("no 'Openings' section" in e for e in errs), errs


def test_openings_address_outsider():
    def f(md):
        lines = md.splitlines()
        i = next(i for i, ln in enumerate(lines) if ln.startswith("### ") and "09:00" in ln)
        lines.insert(i + 1, "- Ask `labor_advocate` about severance funds.")
        return "\n".join(lines)
    errs = _mut(f)
    assert any("block 1 openings address labor_advocate" in e for e in errs), errs


def test_generic_openings_rejected():
    def f(md):
        out, in_op = [], False
        for ln in md.splitlines():
            if ln.startswith("## "):
                in_op = "opening" in ln.lower()
            if in_op and ln.lstrip().startswith(("- ", "* ")):
                ids = [i for i in IDS if i in ln][:1]
                ln = f"- Say hello to {ids[0] if ids else 'uk_aisi'} and be nice."
            out.append(ln)
        return "\n".join(out)
    errs = _mut(f)
    assert any("don't engage co-participants' red lines" in e for e in errs), errs


def test_templated_verbatim_openings_rejected():
    by_id = {p["id"]: p for p in PERS}

    def f(md):
        out, in_op = [], False
        for ln in md.splitlines():
            if ln.startswith("## "):
                in_op = "opening" in ln.lower()
            if in_op and ln.lstrip().startswith(("- ", "* ")):
                o = next((i for i in IDS if i in ln and i != "eu_regulator"), "uk_aisi")
                ln = (f"- For **{o}**: how can we respect your red line against \"{by_id[o]['red_lines'][0]}\" while "
                      f"building on your tradeoff \"{by_id[o]['tradeoffs'][0]}\"?")
            out.append(ln)
        return "\n".join(out)
    errs = _mut(f)
    assert any("openings are templated" in e for e in errs), errs
    assert any("paste persona red lines/tradeoffs verbatim" in e for e in errs), errs


def test_counterparts_missing_and_extra():
    pid, out = next((p, o) for p in IDS for o in IDS if o != p and not any(
        p in g["members"] and o in g["members"] for b in SCHED if b["format"] != "plenary" for g in b["groups"]))
    keep = next(m for g in SCHED[0]["groups"] if pid in g["members"] for m in g["members"] if m != pid)

    def f(md):
        head, _, tail = md.partition("Know your counterparts")
        tail = "\n".join(ln for ln in tail.splitlines() if f"**{keep}**" not in ln)
        return head + "Know your counterparts" + tail + f"\n- **{out}** (X) — Top red line: x | Would trade: y"
    errs = _mut(f, pid)
    assert any(f"counterparts missing {keep}" in e for e in errs), errs
    assert any(f"counterparts lists {out}" in e for e in errs), errs


def test_counterpart_entry_without_substance():
    def f(md):
        return "\n".join("- **uk_aisi** (UK AISI) — a key partner." if "**uk_aisi**" in ln else ln
                         for ln in md.splitlines())
    errs = _mut(f)
    assert any("counterpart uk_aisi entry doesn't reflect their red lines" in e for e in errs), errs


def test_artifacts():
    if not BUNDLE.exists():
        print("  (no cached bundle; skipping artifact test)")
        return
    z = zipfile.ZipFile(BUNDLE)
    files = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    assert verify_artifacts(SCHED, files, IDS) == []
    bad = dict(files)
    bad["ics/eu_regulator.ics"] = files["ics/eu_regulator.ics"].replace(b"Breakout A", b"Breakout D", 1)
    bad["pdf/uk_aisi.pdf"] = b"not a pdf"
    del bad["ics/us_natsec.ics"]
    errs = verify_artifacts(SCHED, bad, IDS)
    assert any(e.startswith("eu_regulator: ics event") for e in errs), errs
    assert "uk_aisi: pdf is not a valid PDF with pages" in errs and "us_natsec: ics missing" in errs, errs


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {name}: {str(e)[:300]}")
    print("all strict-check errors on cached packets:")
    for e in verify(SCHED, _packets(), IDS, PERS):
        print("  ", e)
    sys.exit(1 if fails else 0)
