"""Command line: python -m lafractale.engine validate|run|audit (synthetic fixtures only)."""
from __future__ import annotations

import argparse
import json
import sys

from lafractale.engine import GATES, KIND, READY_FOR_KDP, EngineError
from lafractale.engine.contracts import load_spec_set
from lafractale.engine.pipeline import audit_existing_package, build_activities, generate_package
from lafractale.engine.render import ANSWER_NAME, INTERIOR_NAME
from lafractale.export.securefs import UnsafeOutputPath


def _banner() -> str:
    gates = " ".join(f"{key}={value}" for key, value in GATES.items())
    return f"kind={KIND} ready_for_kdp={str(READY_FOR_KDP).lower()} | {gates}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m lafractale.engine",
        description="Tranche verticale B3-B.1 (fixtures synthétiques uniquement, non publiable)")
    subs = parser.add_subparsers(dest="cmd", required=True)
    p_val = subs.add_parser("validate", help="Valider la source JSON et générer/vérifier les activités en mémoire")
    p_val.add_argument("spec")
    p_run = subs.add_parser("run", help="Générer, auditer et publier un paquet (aucun écrasement)")
    p_run.add_argument("spec")
    p_run.add_argument("--out", required=True)
    p_aud = subs.add_parser("audit", help="Auditer un paquet publié")
    p_aud.add_argument("--out", required=True)
    p_aud.add_argument("--spec", help="Source de confiance indépendante (sinon sources/spec.json du paquet)")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "validate":
            result = build_activities(load_spec_set(args.spec))
            print(f"SOURCE OK | {result.spec_set.spec_id} | {len(result.activities)} activités vérifiées | {_banner()}")
            return 0
        if args.cmd == "run":
            hashes = generate_package(args.spec, args.out)
            print(f"PAQUET CRÉÉ ET AUDITÉ : {args.out} | {_banner()}")
            print(json.dumps({"sha256": hashes}, indent=2, sort_keys=True))
            return 0
        errors = audit_existing_package(args.out, args.spec)
        if errors:
            print("AUDIT ÉCHEC :\n" + "\n".join(errors), file=sys.stderr)
            return 2
        print(f"AUDIT OK ({INTERIOR_NAME}, {ANSWER_NAME}) | {_banner()}")
        return 0
    except (EngineError, UnsafeOutputPath, RuntimeError, ValueError, OSError) as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
