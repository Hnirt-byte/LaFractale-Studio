"""Source -> activities -> verified solutions -> rendered, audited, published package.

Publication is all-or-nothing: the package is built and audited in a private
staging directory, then written to the destination with exclusive file creation
(never overwriting anything) and re-verified. The destination must be absent or
an empty real directory.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path
import stat
import tempfile

from lafractale.activities.engine import generate, stable_seed
from lafractale.activities.models import Activity
from lafractale.engine import EngineError
from lafractale.engine.contracts import (SYNTHETIC_FORBIDDEN_NAMES, SpecSet, canonical_json_bytes,
                                         load_spec_set, parse_spec_set, read_bounded, read_source_file,
                                         sha256_hex)
from lafractale.engine.qa import (audit_package, build_manifest, build_report,
                                  content_checks, package_limit)
from lafractale.engine.registry import MECHANICS
from lafractale.engine.render import (ACTIVITIES_NAME, ANSWER_NAME, INTERIOR_NAME, MANIFEST_NAME,
                                      PACKAGE_FILES, REPORT_NAME, SOURCE_DIR, SOURCE_NAME,
                                      render_slice_with_fonts)
from lafractale.export.securefs import new_regular_file
from lafractale.quality.checks import validate_collection
from lafractale.security.text import UnsafeEditorialText, verify_text_policy


@dataclass(frozen=True)
class SliceResult:
    spec_set: SpecSet
    activities: tuple[Activity, ...]


def build_activities(spec_set: SpecSet) -> SliceResult:
    """Generate every activity with the existing generators, then verify them."""
    activities: list[Activity] = []
    errors: list[str] = []
    for page in spec_set.pages:
        mechanic = MECHANICS[page.mechanic]
        common = {"id": page.unit_id, "page": page.page, "age_band": spec_set.age_band,
                  "scene": page.scene, "vocabulary": ()}
        seed = stable_seed(spec_set.spec_id, page.unit_id, spec_set.seed)
        activity = generate(mechanic.build_spec(common, page.params), seed)
        expected = mechanic.expected_geometry_key(page.params)
        if activity.type != mechanic.name or (
                expected is not None and activity.geometry.get(expected[0]) != expected[1]):
            errors.append(f"{page.unit_id}: le générateur n'a pas produit {mechanic.name} {page.params}")
            continue
        # Texts come from the source; the generator never decides them here.
        activities.append(replace(activity, prompt_fr=page.prompt_fr, prompt_en=page.prompt_en))
    if errors:
        raise EngineError("Génération refusée : " + "; ".join(errors))
    errors.extend(validate_collection(activities))
    for activity in activities:
        errors.extend(MECHANICS[activity.type].verify(activity))
    try:
        verify_text_policy([a.as_dict() for a in activities], forbidden_names=SYNTHETIC_FORBIDDEN_NAMES,
                           location="activités générées")
    except UnsafeEditorialText as exc:
        errors.append(str(exc))
    if errors:
        raise EngineError("Activités invalides : " + "; ".join(dict.fromkeys(errors)))
    return SliceResult(spec_set, tuple(activities))


def _build_staging(spec_bytes: bytes, spec_set: SpecSet, result: SliceResult, staging: Path) -> dict[str, bytes]:
    """Build the package in ``staging``; every file is read ONCE and the same bytes are
    analysed, hashed and returned."""
    (staging / SOURCE_DIR).mkdir()
    (staging / SOURCE_NAME).write_bytes(spec_bytes)
    interior, answer, fonts = render_slice_with_fonts(spec_set, result.activities, staging)
    (staging / ACTIVITIES_NAME).write_bytes(canonical_json_bytes([a.as_dict() for a in result.activities]))
    contents = {INTERIOR_NAME: read_bounded(interior, package_limit(INTERIOR_NAME), label=INTERIOR_NAME),
                ANSWER_NAME: read_bounded(answer, package_limit(ANSWER_NAME), label=ANSWER_NAME)}
    checks = content_checks(spec_set, result.activities, contents[INTERIOR_NAME], contents[ANSWER_NAME])
    report = build_report(spec_set, result.activities, checks, fonts)
    if not report["pass"]:
        failed = [f"{c['id']} : {c['detail']}" for c in checks if c["status"] == "FAIL"]
        raise EngineError("QA refusée : " + " | ".join(failed))
    contents[REPORT_NAME] = canonical_json_bytes(report)
    contents[ACTIVITIES_NAME] = read_bounded(staging / ACTIVITIES_NAME, package_limit(ACTIVITIES_NAME),
                                             label=ACTIVITIES_NAME)
    contents[SOURCE_NAME] = spec_bytes
    contents[MANIFEST_NAME] = canonical_json_bytes(build_manifest(
        spec_set, {name: sha256_hex(data) for name, data in contents.items()}, fonts))
    for name in (REPORT_NAME, MANIFEST_NAME):
        (staging / name).write_bytes(contents[name])
    return {name: contents[name] for name in PACKAGE_FILES}


def _check_destination(out_dir: Path) -> None:
    try:
        info = os.lstat(out_dir)
    except FileNotFoundError:
        return
    if not stat.S_ISDIR(info.st_mode):
        raise EngineError("Sortie refusée : la destination existe et n'est pas un répertoire réel")
    if any(out_dir.iterdir()):
        raise EngineError("Sortie refusée : répertoire de destination non vide (aucun écrasement)")


def generate_package(spec_path: str | os.PathLike, out_dir: str | os.PathLike) -> dict[str, str]:
    """Build, audit and publish a package. Returns {relative path: sha256}."""
    out = Path(os.path.abspath(out_dir))
    _check_destination(out)
    spec_bytes = read_source_file(spec_path)
    spec_set = parse_spec_set(spec_bytes)
    result = build_activities(spec_set)
    with tempfile.TemporaryDirectory(prefix="lafractale-engine-") as scratch:
        staging = Path(scratch) / "package"
        staging.mkdir()
        contents = _build_staging(spec_bytes, spec_set, result, staging)
        errors = audit_package(staging, spec_set, result.activities)
        if errors:
            raise EngineError("Audit du paquet refusé : " + " | ".join(errors))
    _check_destination(out)  # re-check right before writing
    # Missing ancestors (deepest first) are created by new_regular_file through
    # O_NOFOLLOW directory descriptors; remember them to roll back completely.
    missing: list[Path] = []
    probe = out
    while not os.path.lexists(probe):
        missing.append(probe)
        probe = probe.parent
    created: list[Path] = []
    try:
        for name in PACKAGE_FILES:
            with new_regular_file(out / name) as stream:
                created.append(out / name)
                stream.write(contents[name])
        errors = audit_package(out, spec_set, result.activities)
        if errors:
            raise EngineError("Audit après publication refusé : " + " | ".join(errors))
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        for directory in [out / SOURCE_DIR, *missing]:
            try:
                directory.rmdir()
            except OSError:
                pass
        raise
    return {name: sha256_hex(contents[name]) for name in PACKAGE_FILES}


def audit_existing_package(out_dir: str | os.PathLike, spec_path: str | os.PathLike | None = None) -> list[str]:
    """Audit a published package against a trusted source.

    With ``spec_path`` the source is independent of the package. Without it the
    package's own ``sources/spec.json`` is used: that proves internal consistency
    only, not authenticity.
    """
    out = Path(os.path.abspath(out_dir))
    try:
        spec_set = (load_spec_set(spec_path) if spec_path is not None
                    else parse_spec_set(read_source_file(out / SOURCE_NAME)))
        result = build_activities(spec_set)
    except EngineError as exc:
        return [f"source de confiance refusée : {exc}"]
    return audit_package(out, spec_set, result.activities)
