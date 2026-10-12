"""MINOR-1: dependencies installed with ``pip install --user`` stay usable by the isolated render
process WITHOUT giving it the caller's HOME, user-site hooks (.pth, usercustomize) or ReportLab settings."""
import os
import subprocess
import sys
import site
from pathlib import Path

import pytest

from lafractale.engine import render


@pytest.fixture
def fake_user_site(tmp_path, monkeypatch):
    user_site = tmp_path / "userbase" / "lib" / "pythonX" / "site-packages"
    user_site.mkdir(parents=True)
    (user_site / "lf_user_probe.py").write_text("VALUE = 'importé depuis le user site'\n")
    marker = tmp_path / "EXECUTED"
    (user_site / "evil.pth").write_text(f"import os; open({str(marker)!r}, 'w').write('pth')\n")
    (user_site / "usercustomize.py").write_text(f"open({str(marker)!r}, 'a').write('usercustomize')\n")
    monkeypatch.setattr(site, "ENABLE_USER_SITE", True)
    monkeypatch.setattr(site, "getusersitepackages", lambda: str(user_site))
    monkeypatch.setattr(sys, "path", [*sys.path, str(user_site)])
    return user_site, marker


def _run_probe(code, home):
    env = render.worker_environment(home)
    return subprocess.run([*render.python_command(), "-c", code], env=env, capture_output=True, text=True, timeout=60)


def test_the_parent_user_site_is_handed_to_the_render_process(fake_user_site, tmp_path):
    user_site, marker = fake_user_site
    assert render.user_site_entries() == [str(user_site)]
    done = _run_probe("import lf_user_probe; print(lf_user_probe.VALUE)", str(tmp_path / "home"))
    assert done.returncode == 0, done.stderr
    assert "importé depuis le user site" in done.stdout


def test_user_site_hooks_are_never_executed_by_the_render_process(fake_user_site, tmp_path):
    user_site, marker = fake_user_site
    done = _run_probe("import lf_user_probe", str(tmp_path / "home"))
    assert done.returncode == 0, done.stderr
    assert not marker.exists(), marker.read_text()  # neither the .pth nor usercustomize ran


def test_home_stays_empty_and_isolated_in_the_render_process(fake_user_site, tmp_path):
    home = tmp_path / "emptyhome"
    home.mkdir()
    code = ("import os; h = os.path.expanduser('~'); print(h); "
            "print(os.path.exists(os.path.join(h, '.reportlab_settings')))")
    done = _run_probe(code, str(home))
    assert done.stdout.split() == [str(home), "False"], done.stdout


def test_no_user_site_when_the_parent_does_not_use_one(tmp_path, monkeypatch):
    monkeypatch.setattr(site, "ENABLE_USER_SITE", False)
    assert render.user_site_entries() == []
    monkeypatch.setattr(site, "ENABLE_USER_SITE", True)
    monkeypatch.setattr(site, "getusersitepackages", lambda: str(tmp_path / "absent"))
    assert render.user_site_entries() == []  # directory missing
    present = tmp_path / "present"
    present.mkdir()
    monkeypatch.setattr(site, "getusersitepackages", lambda: str(present))
    assert render.user_site_entries() == []  # not imported by the parent (not in sys.path)


def test_child_search_path_keeps_the_package_root_first_and_stays_absolute(fake_user_site, tmp_path, monkeypatch):
    user_site, _ = fake_user_site
    monkeypatch.chdir(tmp_path)
    parts = render.child_pythonpath("rel" + os.pathsep + "/opt/x").split(os.pathsep)
    import lafractale
    assert parts[0] == str(Path(lafractale.__file__).resolve().parents[1])
    assert str(user_site) in parts and "/opt/x" in parts and str(tmp_path / "rel") in parts
    assert all(os.path.isabs(p) for p in parts)


def test_user_hooks_of_an_inherited_user_base_are_not_executed(tmp_path, monkeypatch):
    """The only case where ``-s`` acts: a user base inherited through PYTHONUSERBASE."""
    base = tmp_path / "base"
    user_site = base / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    user_site.mkdir(parents=True)
    marker = tmp_path / "EXECUTED"
    (user_site / "evil.pth").write_text(f"import os; open({str(marker)!r}, 'w').write('pth')\n")
    env = {**render.worker_environment(str(tmp_path / "home")), "PYTHONUSERBASE": str(base)}
    without_s = [sys.executable, "-P", "-c", "pass"]
    subprocess.run(without_s, env=env, check=True, timeout=60)
    if not marker.exists():  # negative control: this interpreter ignores the user site anyway
        pytest.skip("interpréteur sans user-site actif (environnement virtuel) : le contrôle négatif ne s'exécute pas")
    marker.unlink()
    subprocess.run([*render.python_command(), "-c", "pass"], env=env, check=True, timeout=60)
    assert not marker.exists()


@pytest.mark.parametrize("spelling", ["relative", "double-slash", "trailing-slash"])
def test_user_site_given_by_an_unnormalised_user_base_is_still_handed_over(tmp_path, monkeypatch, spelling):
    real = tmp_path / "ub" / "lib" / "pythonX" / "site-packages"
    real.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    raw = {"relative": "ub/lib/pythonX/site-packages",
           "double-slash": str(tmp_path) + "//ub/lib/pythonX/site-packages",
           "trailing-slash": str(real) + "/"}[spelling]
    monkeypatch.setattr(site, "ENABLE_USER_SITE", True)
    monkeypatch.setattr(site, "getusersitepackages", lambda: raw)
    monkeypatch.setattr(sys, "path", [*sys.path, str(real)])  # what ``site`` really stores: absolute
    assert render.user_site_entries() == [str(real)]


def test_user_site_comes_after_the_inherited_pythonpath_like_in_the_parent(fake_user_site):
    user_site, _ = fake_user_site
    parts = render.child_pythonpath("/opt/first").split(os.pathsep)
    assert parts.index("/opt/first") < parts.index(str(user_site))


def test_render_process_disables_the_user_site_and_the_working_directory():
    command = render.python_command()
    assert command[0] == sys.executable and "-P" in command and "-s" in command
