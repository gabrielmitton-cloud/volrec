"""Unit tests for the auditor's own machinery (tools/audit.py), written 18 Nov 2026.

Why: on 17 Nov the full audit built all 260 worktrees before running the first one (8.1 GB, on a disk with 13 GiB
free). macOS made room by removing the local copies of iCloud files that the checks read, the checks waited on
downloads, pressure tests hit the 600 s limit and the run was void (HANDOFF 18, 17 Nov). Gabriel, 18 Nov: "i dont
see any reason why u have to make 260 copies". These tests run audit.main() on a tiny throwaway git repository with
fake mutants and a fake pressure test, and hold the machinery to: at most J copies exist at any moment; each mutant
gets a fresh copy, so no breakage leaks into another; the baseline copy is never broken; a mutation that cannot
apply is INCONCLUSIVE; a failed pressure test stops the mutants still waiting; every copy is removed afterwards,
even when a pressure test raises. No network and no real data: everything lives in temporary folders.

18 Nov, after Astra's first review (two MEDIUM findings on this file): the number of copies is read from git itself
(`git worktree list`, wherever a copy sits) right after each copy is made, since the count can only rise there;
counting folders when a pressure test starts could miss a copy made and removed between two starts, and a negative
control shows the new count catches exactly that. The stopped queue is tested deterministically: the mutants in
flight when the failure surfaces are held until the auditor has shut its queue, and none of the mutants waiting
behind them may start.

18 Nov, after Astra's second review (four MEDIUM findings on tools/audit.py): every copy must come from the commit
the run started on, though HEAD moves mid-run; a later failure must stop the queue at once, even while an earlier
pressure test is still running; a copy git cannot remove must void the run instead of letting more than J exist;
the auditor must leave an unrelated worktree's registration alone (no repository-wide prune).

  python tools/test_audit.py
"""
import contextlib
import importlib.util as iu
import io
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
from pathlib import Path

R = Path(__file__).resolve().parent.parent
fails = []


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


def tiny_repo(tmp):
    """A one-file repository standing in for the project: file.txt reads 'unbroken' at HEAD."""
    repo = Path(tmp) / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "file.txt").write_text("unbroken\n")
    git(repo, "add", "file.txt")
    git(repo, "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-q", "-m", "init")
    return repo


def live_copies(repo):
    """The worktrees git knows of besides the repository itself, wherever on the disk they sit."""
    return git(repo, "worktree", "list", "--porcelain").count("worktree ") - 1


def run_audit(n_mutants, j, broken=(), raise_at=None, delay=0.05, late_drop=False, hold=False,
              hold_baseline=False, advance=False, stuck_at=None, stale_other=False, add_fails_at=None,
              drop_raises_at=None):
    """Run audit.main() with n fake mutants. Each writes its own name into file.txt; the fake pressure test
    FAILs exactly the check named in file.txt. Every copy the auditor makes is counted through git right after it
    is made (max_live), and again whenever a pressure test starts (max_at_start, the first version's count).
    late_drop: a deliberate fault, for the negative control - each worker removes its previous copy only after
    making the next one, so two copies exist for a moment though only one exists whenever a pressure test starts.
    hold: every pressure test but the baseline's and raise_at's waits until the auditor has shut its queue.
    hold_baseline: only the baseline's pressure test waits so (an earlier job still running when a later fails).
    advance: the baseline's pressure test commits a new file, so HEAD moves while the run goes on.
    stuck_at: that mutant's pressure test leaves a folder in its copy that cannot be deleted.
    stale_other: an unrelated worktree, its folder since deleted, is registered in the repository before the run.
    add_fails_at: git fails to add copy number i (an exception, as from a full disk).
    drop_raises_at: removing copy number i raises in its worker (the final clean-up still removes it).
    Returns what was observed; "made" lists the copies asked for, in order, and with add_fails_at or drop_raises_at,
    "stop_at_release" says whether stop was already set when that planted failure left the auditor's lock."""
    spec = iu.spec_from_file_location("audit_under_test", R / "tools/audit.py")
    au = iu.module_from_spec(spec)
    spec.loader.exec_module(au)
    names = [f"mut{k:02d}" for k in range(1, n_mutants + 1)]
    seen = {"max_live": 0, "max_at_start": 0, "runs": [], "bases": set(), "marked": 0, "stuck": [], "released": [],
            "made": []}
    lock = threading.Lock()
    released = threading.Event()
    real_make, real_drop = au.make_tree, getattr(au, "drop_tree", None)
    worker = threading.local()

    def mutate_for(name):
        if name in broken:                          # its target text is absent: _sub refuses
            return lambda w: au._sub(w / "file.txt", "text that is not there", name)
        return lambda w: au._sub(w / "file.txt", "unbroken", name)

    def counted_make(*args):
        with lock:
            seen["made"].append(args[1])
        if add_fails_at is not None and args[1] == add_fails_at:
            raise RuntimeError("git worktree add failed (planted)")
        tree = real_make(*args)
        with lock:
            seen["max_live"] = max(seen["max_live"], live_copies(au.ROOT))
        if late_drop and getattr(worker, "previous", None) is not None:
            real_drop(worker.previous)              # the fault: the previous copy goes only now
            worker.previous = None
        return tree

    def raising_drop_tree(tree):
        if (Path(tree).name == f"m{drop_raises_at:02d}" and threading.current_thread() is not threading.main_thread()
                and not seen.get("drop_raised")):
            seen["drop_raised"] = True
            raise OSError("git worktree remove crashed (planted)")
        return real_drop(tree)

    def late_drop_tree(tree):
        if threading.current_thread() is threading.main_thread():
            return real_drop(tree)                  # the auditor's final clean-up stays honest
        worker.previous = tree
        return True

    class WatchedLock:
        """The auditor's _GIT lock, watched (18 Nov 2026, Astra 2's follow-up review): when a planted failure leaves
        the lock, is stop already set? That decides whether another worker could build a copy before the main thread
        saw the failure, whatever the threads' timing; the copies asked for afterwards depend on that timing."""
        def __init__(self):
            self.inner = threading.Lock()

        def __enter__(self):
            self.inner.acquire()
            return self

        def __exit__(self, kind, exc, tb):
            if exc is not None and "(planted)" in str(exc):
                seen["stop_at_release"] = seen["stop"].is_set()
            self.inner.release()
            return False

    real_audit_one = au.audit_one

    def watched_audit_one(base, rev, stop, i, mutate=None):
        seen["stop"] = stop
        return real_audit_one(base, rev, stop, i, mutate)

    class HeldPool(au.ThreadPoolExecutor):
        """Lets the held pressure tests go only once shutdown has run, after any cancelling it was asked for."""
        def shutdown(self, wait=True, *, cancel_futures=False):
            super().shutdown(wait=False, cancel_futures=cancel_futures)
            released.set()
            super().shutdown(wait=wait)

    def fake_pressure(tree):
        tree = Path(tree)
        content = (tree / "file.txt").read_text().strip()
        with lock:
            seen["bases"].add(tree.parent)
            seen["runs"].append(content)
            seen["marked"] += (tree / "marker.txt").exists()
            seen["max_at_start"] = max(seen["max_at_start"], live_copies(au.ROOT))
        if advance and content == "unbroken":       # a commit lands while the audit runs
            (Path(au.ROOT) / "marker.txt").write_text("a later commit\n")
            git(au.ROOT, "add", "marker.txt")
            git(au.ROOT, "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-q", "-m", "later")
        if stuck_at is not None and content == stuck_at:
            stuck = tree / "stuck"
            stuck.mkdir()
            (stuck / "f").write_text("cannot be deleted while its folder is read-only\n")
            stuck.chmod(0o500)
            with lock:
                seen["stuck"].append(stuck)
        if (hold and content not in ("unbroken", raise_at)) or (hold_baseline and content == "unbroken"):
            got = released.wait(timeout=10)         # False: let go by the timeout, not by the auditor's shutdown
            with lock:
                seen["released"].append(got)
        else:
            time.sleep(delay)
        if raise_at is not None and content == raise_at:
            raise subprocess.TimeoutExpired("pressure_test.py", 600)
        return {f"check for {n}": ("FAIL" if content == n else "PASS") for n in names}

    with tempfile.TemporaryDirectory() as tmp:
        repo = tiny_repo(tmp)
        head0 = git(repo, "rev-parse", "HEAD").strip()
        other = None
        if stale_other:
            other = Path(tmp) / "other"
            git(repo, "worktree", "add", "--detach", "--quiet", str(other), "HEAD")
            other = other.resolve()
            shutil.rmtree(other)
        au.ROOT = repo
        au.MUTANTS = [(n, f"breaks {n}", mutate_for(n), f"check for {n}") for n in names]
        au.run_pressure = fake_pressure
        au.make_tree = counted_make
        if late_drop:
            au.drop_tree = late_drop_tree
        if drop_raises_at is not None:
            au.drop_tree = raising_drop_tree
        if add_fails_at is not None or drop_raises_at is not None:
            au._GIT, au.audit_one = WatchedLock(), watched_audit_one
        if hold or hold_baseline:
            au.ThreadPoolExecutor = HeldPool
        au.drift = lambda: []
        out, errs, err, code = io.StringIO(), io.StringIO(), None, None
        argv = sys.argv
        sys.argv = ["audit.py", "-j", str(j)]
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(errs):
                code = au.main()
        except (Exception, SystemExit) as e:        # a pressure test that raises must surface, as before;
            err = e                                 # SystemExit: the command line was refused
        finally:
            sys.argv = argv
        listing = git(repo, "worktree", "list", "--porcelain")
        seen["worktrees_left"] = listing.count("worktree ") - 1
        seen["other_kept"] = other is not None and any(
            Path(ln[9:]).resolve() == other for ln in listing.splitlines() if ln.startswith("worktree "))
        seen["head_moved"] = git(repo, "rev-parse", "HEAD").strip() != head0
        seen["bases_left"] = [b for b in seen["bases"] if b.exists()]
        for stuck in seen["stuck"]:                 # undo the planted fault, so everything can be deleted
            if stuck.exists():
                stuck.chmod(0o700)
        for b in seen["bases"]:
            shutil.rmtree(b, ignore_errors=True)
    seen.update(out=out.getvalue(), stderr=errs.getvalue(), err=err, code=code, names=names)
    return seen


print("=== the auditor builds its copies as it needs them, J at a time (18 Nov 2026) ===")
s = run_audit(8, 2)
check("all eight fake safeguards are proven: 'RESULT: 8 of 8' and exit 0",
      "RESULT: 8 of 8 safeguards proven to fail when broken" in s["out"] and s["code"] == 0)
check(f"at most J=2 copies of the repository exist at once, counted by git after every copy made (saw {s['max_live']})",
      0 < s["max_live"] <= 2)
check("the baseline copy is unbroken and each mutant's copy holds its own breakage and no other",
      sorted(s["runs"]) == sorted(["unbroken"] + s["names"]))
check("every copy is removed afterwards: no worktree record, no temporary folder",
      s["worktrees_left"] == 0 and not s["bases_left"])

s = run_audit(6, 1)
check(f"with J=1, one copy at a time (saw {s['max_live']}) and still 6 of 6",
      s["max_live"] == 1 and "RESULT: 6 of 6 safeguards proven" in s["out"])

print("\n=== negative control: the count sees a copy that outlives the making of the next one ===")
s = run_audit(5, 1, late_drop=True)
check(f"with the fault planted, the count after each copy reads 2 against J=1 (saw {s['max_live']}), "
      f"while a count at each pressure test's start reads 1 (saw {s['max_at_start']})",
      s["max_live"] == 2 and s["max_at_start"] == 1)

print("\n=== every copy comes from the commit the run started on, though HEAD moves meanwhile ===")
s = run_audit(4, 1, advance=True)
check(f"HEAD moved during the run, yet no copy holds the later commit ({s['marked']} did) and the result is 4 of 4",
      s["head_moved"] and s["marked"] == 0 and "RESULT: 4 of 4 safeguards proven" in s["out"])

print("\n=== a mutation that cannot apply is a finding, and its copy is removed too ===")
s = run_audit(5, 1, broken=("mut03",))
check("the unappliable mutant reads INCONCLUSIVE 'could not apply', and the result is 4 of 5 with exit 1",
      "INCONCLUSIVE" in s["out"] and "could not apply" in s["out"] and "mut03" in s["out"]
      and "RESULT: 4 of 5 safeguards proven" in s["out"] and s["code"] == 1)
check("its pressure test never ran (a copy that was not broken proves nothing)", "mut03" not in s["runs"]
      and s["runs"].count("unbroken") == 1)
check(f"its copy is removed at once, not left to the final clean-up: with J=1, never two copies (saw {s['max_live']})",
      s["max_live"] == 1)
check("no copy is left behind", s["worktrees_left"] == 0 and not s["bases_left"])

print("\n=== a pressure test that raises voids the run, stops the queue, and leaves nothing behind ===")
s = run_audit(20, 2, raise_at="mut01", hold=True)
check("the timeout surfaces: no RESULT line is printed, so the push gate refuses",
      isinstance(s["err"], subprocess.TimeoutExpired) and "RESULT:" not in s["out"])
started = set(s["runs"]) - {"unbroken", "mut01"}
check(f"only the J=2 mutants already in flight when it failed may finish; none of the 17 queued behind them "
      f"starts (started besides the baseline and mut01: {sorted(started)})",
      started <= {"mut02", "mut03"} and len(s["runs"]) == len(set(s["runs"])))
check("every copy is removed even so", s["worktrees_left"] == 0 and not s["bases_left"])

s = run_audit(20, 2, raise_at="mut01", hold_baseline=True)
check(f"a later failure stops the queue at once, even while an earlier pressure test is still running: only the "
      f"held baseline and mut01 ran (saw {sorted(set(s['runs']))})",
      set(s["runs"]) <= {"unbroken", "mut01"} and isinstance(s["err"], subprocess.TimeoutExpired)
      and "RESULT:" not in s["out"])
check(f"the failure surfaces at once, not after the earlier test: the auditor shut its queue while the baseline was "
      f"still held (released by that shutdown, not by the test's 10 s timeout: {s['released']})",
      s["released"] == [True])
check("and every copy is removed", s["worktrees_left"] == 0 and not s["bases_left"])

print("\n=== a copy git cannot remove voids the run; the auditor removes only its own copies ===")
s = run_audit(5, 1, stuck_at="mut02")
check(f"the run is void (no RESULT line) and no further copy is made: J=1 held (saw {s['max_live']}), "
      f"nothing ran after mut02 (ran: {s['runs']})",
      s["err"] is not None and "RESULT:" not in s["out"] and s["max_live"] <= 1
      and s["runs"] == ["unbroken", "mut01", "mut02"])
s = run_audit(3, 1, stale_other=True)
check("an unrelated worktree's stale registration is left alone (no repository-wide prune), and the run reads 3 of 3",
      s["other_kept"] and s["worktrees_left"] == 1 and "RESULT: 3 of 3 safeguards proven" in s["out"])

# 18 Nov 2026 (later), Astra 2's review of this file: git failing to add a copy, or a removal that raised, left the
# auditor's lock without setting stop, so another worker could make a copy before the main thread saw the failure;
# and -j 0 silently ran one copy at a time.
print("\n=== a copy git cannot add, or a removal that raises, voids the run before any other copy is made ===")
s = run_audit(6, 1, add_fails_at=2)
check(f"git failing to add mut02's copy voids the run (no RESULT line), and no copy is asked for after it "
      f"(asked for, in order: {s['made']})",
      isinstance(s["err"], RuntimeError) and "RESULT:" not in s["out"] and s["made"] == [0, 1, 2])
check(f"and stop is already set when that failure leaves the auditor's lock, so no worker can build another copy "
      f"first, whatever the threads' timing (saw {s.get('stop_at_release')})", s.get("stop_at_release") is True)
check("and nothing is left behind", s["worktrees_left"] == 0 and not s["bases_left"])
s = run_audit(6, 1, drop_raises_at=1)
check(f"a removal that raises voids the run (no RESULT line), and no copy is asked for after it "
      f"(asked for, in order: {s['made']})",
      isinstance(s["err"], OSError) and "RESULT:" not in s["out"] and s["made"] == [0, 1])
check(f"and stop is already set when that removal's failure leaves the auditor's lock, whatever the threads' timing "
      f"(saw {s.get('stop_at_release')})", s.get("stop_at_release") is True)
check("and the final clean-up still removes that copy", s["worktrees_left"] == 0 and not s["bases_left"])

print("\n=== -j must be 1 or more ===")
for _bad in (0, -2):
    s = run_audit(3, _bad)
    check(f"-j {_bad} is refused before any copy is made (exit {getattr(s['err'], 'code', None)}, copies asked for: "
          f"{s['made']})",
          isinstance(s["err"], SystemExit) and s["err"].code == 2 and s["made"] == [] and "RESULT:" not in s["out"])

print("\n=== the audit's copies never read the licensed lab files ===")
# 18 Nov 2026, Gabriel: "14 gb is atrocious". Every copy's pressure test ran lab/verify_purchases.py over the lab's
# 8,073 licensed files (18.3 GB), so all of them had to stay on the disk through the whole audit while macOS keeps
# 11-14 GiB free by moving iCloud files off it. No verdict depends on them (no mutant names that check), so each
# copy's pressure test runs with VOLREC_LICENSED_DIR naming a folder that does not exist: the check reads SKIP there.
spec = iu.spec_from_file_location("audit_env_under_test", R / "tools/audit.py")
au = iu.module_from_spec(spec)
spec.loader.exec_module(au)
seen = {}


def fake_subprocess_run(args, **kw):
    seen.update(kw, args=args)
    return types.SimpleNamespace(stdout="  PASS  a check\n  FAIL  another\nRESULT: 1 fail, 0 warn\n", returncode=1)


with tempfile.TemporaryDirectory() as tmp:
    tree = Path(tmp) / "m01"
    tree.mkdir()
    au.subprocess = types.SimpleNamespace(run=fake_subprocess_run, TimeoutExpired=subprocess.TimeoutExpired)
    res = au.run_pressure(tree)
    env = seen.get("env") or {}
    lab = Path(env["VOLREC_LICENSED_DIR"]) if env.get("VOLREC_LICENSED_DIR") else None
    check(f"each copy's pressure test runs with VOLREC_LICENSED_DIR naming a folder that does not exist, outside the "
          f"copy and the repository (saw {lab})",
          lab is not None and not lab.exists() and lab != tree and tree not in lab.parents
          and R not in lab.resolve().parents)
    check("the rest of the environment is passed on unchanged",
          bool(env) and {k: v for k, v in env.items() if k != "VOLREC_LICENSED_DIR"}
          == {k: v for k, v in os.environ.items() if k != "VOLREC_LICENSED_DIR"})
    check("its lines are read as before, in the copy, with the 600 s limit",
          res == {"a check": "PASS", "another": "FAIL"} and seen.get("cwd") == tree and seen.get("timeout") == 600)


# 18 Nov 2026 (later), Astra 2's review: this guard looked for "purchases verified" inside each target, while the
# auditor's find() looks for the target inside the check's label, so a target from the middle of the label passed it.
# Now it reads the label from the pressure test and asks the auditor's own lookup.
_lab_label = next((ln.strip().strip('"),') for ln in (R / "tools/pressure_test.py").read_text().splitlines()
                   if ln.strip().startswith('"lab/ purchases verified:')), "")


def names_lab_check(mutants):
    return any(au.find({_lab_label: "PASS"}, m[3]) is not None for m in mutants)


check(f"no auditor mutant names the check that reads the licensed lab files (in the copies it reads SKIP, so such a "
      f"mutant could never be KILLED); this guard sees one if it is added, by the label's start or by a phrase from "
      f"its middle (label read from the pressure test: {_lab_label[:40]!r}...)",
      _lab_label.startswith("lab/ purchases verified: every used file has data") and not names_lab_check(au.MUTANTS)
      and names_lab_check(au.MUTANTS + [("x", "y", None, "lab/ purchases verified")])
      and names_lab_check(au.MUTANTS + [("x", "y", None, "every used file has data")]))

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
