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
import shutil
import subprocess
import sys
import tempfile
import threading
import time
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
              hold_baseline=False, advance=False, stuck_at=None, stale_other=False):
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
    Returns what was observed."""
    spec = iu.spec_from_file_location("audit_under_test", R / "tools/audit.py")
    au = iu.module_from_spec(spec)
    spec.loader.exec_module(au)
    names = [f"mut{k:02d}" for k in range(1, n_mutants + 1)]
    seen = {"max_live": 0, "max_at_start": 0, "runs": [], "bases": set(), "marked": 0, "stuck": [], "released": []}
    lock = threading.Lock()
    released = threading.Event()
    real_make, real_drop = au.make_tree, getattr(au, "drop_tree", None)
    worker = threading.local()

    def mutate_for(name):
        if name in broken:                          # its target text is absent: _sub refuses
            return lambda w: au._sub(w / "file.txt", "text that is not there", name)
        return lambda w: au._sub(w / "file.txt", "unbroken", name)

    def counted_make(*args):
        tree = real_make(*args)
        with lock:
            seen["max_live"] = max(seen["max_live"], live_copies(au.ROOT))
        if late_drop and getattr(worker, "previous", None) is not None:
            real_drop(worker.previous)              # the fault: the previous copy goes only now
            worker.previous = None
        return tree

    def late_drop_tree(tree):
        if threading.current_thread() is threading.main_thread():
            return real_drop(tree)                  # the auditor's final clean-up stays honest
        worker.previous = tree
        return True

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
        if hold or hold_baseline:
            au.ThreadPoolExecutor = HeldPool
        au.drift = lambda: []
        out, err, code = io.StringIO(), None, None
        argv = sys.argv
        sys.argv = ["audit.py", "-j", str(j)]
        try:
            with contextlib.redirect_stdout(out):
                code = au.main()
        except Exception as e:                      # a pressure test that raises must surface, as before
            err = e
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
    seen.update(out=out.getvalue(), err=err, code=code, names=names)
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

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
