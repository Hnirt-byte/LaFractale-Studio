"""CLI of the read-only scenario B reader: ``python -m lafractale.scenario_b``."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from lafractale.engine.contracts import read_bounded
from lafractale.scenario_b import ReaderError
from lafractale.scenario_b.analyzer import analyze, dumps_report
from lafractale.scenario_b.render import render_report, render_synthesis
from lafractale.scenario_b.schema import validate_report
from lafractale.security.strict_json import loads_strict

OUTPUT_NAMES = ("scenario_b_report.json", "scenario_b_report.md", "scenario_b_synthesis.md")
#: Directories holding sources: the reader refuses to write into them.
PROTECTED_DIRS = ("docs/editorial", "assets", "books")


class OutputError(ValueError):
    pass


def _check_out_dir(root: Path, out_dir: Path) -> Path:
    target = Path(os.path.realpath(out_dir))
    for part in PROTECTED_DIRS:
        protected = Path(os.path.realpath(root / part))
        if target == protected or protected in target.parents:
            raise OutputError(f"sortie refusée : {part} contient des sources en lecture seule")
    if Path(out_dir).is_symlink():
        raise OutputError("sortie refusée : lien symbolique")
    return target


def _write_new(target: Path, name: str, data: bytes, overwrite: bool) -> None:
    path = target / name
    if os.path.lexists(path):
        if path.is_symlink() or not path.is_file():
            raise OutputError(f"{name} : cible non régulière ou lien symbolique")
        if not overwrite:
            raise OutputError(f"{name} existe déjà (utiliser --overwrite pour remplacer un rapport précédent)")
    tmp = target / f".{name}.tmp{os.getpid()}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.lexists(tmp):
            os.unlink(tmp)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m lafractale.scenario_b",
                                     description="Lecteur en lecture seule du scénario B (B3-B.2) — aucune génération.")
    subs = parser.add_subparsers(dest="cmd", required=True)
    run = subs.add_parser("analyze", help="Analyser les sources et écrire le rapport JSON, le rapport Markdown et la synthèse")
    run.add_argument("--root", type=Path, default=Path("."), help="racine du dépôt (lue, jamais modifiée)")
    run.add_argument("--out-dir", type=Path, required=True, help="répertoire de sortie existant, hors des sources")
    run.add_argument("--overwrite", action="store_true", help="remplacer un rapport précédent du même nom")
    run.add_argument("--strict", action="store_true", help="code 1 si une contradiction ou anomalie de structure est détectée")
    chk = subs.add_parser("validate-report", help="Valider un rapport JSON contre le schéma")
    chk.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "validate-report":
            problems = validate_report(loads_strict(read_bounded(args.report, 8_000_000, label="rapport", error=ReaderError)))
            if problems:
                print("RAPPORT INVALIDE :\n" + "\n".join(problems), file=sys.stderr)
                return 2
            print("RAPPORT CONFORME AU SCHÉMA")
            return 0
        root = args.root
        out_dir = _check_out_dir(root, args.out_dir)
        if not out_dir.is_dir():
            raise OutputError("le répertoire de sortie doit exister")
        report = analyze(root)
        problems = validate_report(report)
        if problems:
            raise ReaderError(["rapport interne non conforme au schéma"] + problems)
        payloads = {OUTPUT_NAMES[0]: dumps_report(report), OUTPUT_NAMES[1]: render_report(report).encode("utf-8"),
                    OUTPUT_NAMES[2]: render_synthesis(report).encode("utf-8")}
        for name, data in payloads.items():
            _write_new(out_dir, name, data, args.overwrite)
    except (ReaderError, OutputError, ValueError, OSError) as exc:
        detail = "\n".join(exc.errors) if isinstance(exc, ReaderError) else str(exc)
        print(f"ANALYSE IMPOSSIBLE :\n{detail}", file=sys.stderr)
        return 2
    s = report["summary"]
    t = s["technical_status_activity_pages"]
    print(f"RAPPORT ÉCRIT | 56 pages | activités SUPPORTED {t['SUPPORTED']} PARTIAL {t['PARTIAL']} "
          f"UNSUPPORTED {t['UNSUPPORTED']} UNKNOWN {t['UNKNOWN']} | contrôles en échec {s['checks_failed']}/{s['checks_total']} "
          f"| aucune approbation, aucune génération")
    if args.strict and (not report["analysis"]["structure_ok"] or s["findings_by_severity"].get("CONTRADICTION")):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
