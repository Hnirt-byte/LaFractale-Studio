"""Command line: validate | build-demo | build | qa."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from lafractale.config.schema import ConfigError,load_book,validate_plan_vocabulary
from lafractale.story.plan import demo_specs,full_build_blockers
from lafractale.export.builder import build_demo,audit_output


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(prog="lafractale",description="Moteur LaFractale Studio (démo non publiable)")
    subs=parser.add_subparsers(dest="cmd",required=True)
    p_val=subs.add_parser("validate",help="Valider le YAML et le plan de pages")
    p_val.add_argument("book")
    for cmd in ("build-demo","build"):
        p=subs.add_parser(cmd,help="Créer une démo de 3 pages / refuser les ouvrages incomplets")
        p.add_argument("book");p.add_argument("--out",type=Path)
        p.add_argument("--illustration-id", help="Visuel monochrome approuvé (optionnel)")
        p.add_argument("--approvals-sha256", help="SHA-256 approuvé séparément du catalogue graphique")
        if cmd == "build-demo":
            p.add_argument("--illustration-routing", help="Politique C1 fermée de routage par activité")
        p.add_argument("--seed",type=int,default=2026)
    p_qa=subs.add_parser("qa",help="Vérifier les artefacts d'une démo")
    p_qa.add_argument("out",type=Path)
    p_qa.add_argument("--book",required=True,type=Path,help="YAML source de confiance obligatoire pour recalculer les noms réservés")
    p_qa.add_argument("--illustration-id", help="Visuel monochrome explicitement autorisé")
    p_qa.add_argument("--illustration-routing", help="Politique C1 fermée de routage par activité")
    p_qa.add_argument("--approvals-sha256", help="Empreinte de registre approuvée hors sorties")
    args=parser.parse_args(argv)
    try:
        if args.cmd=="qa":
            errors=audit_output(args.out,book=load_book(args.book,require_plan=False),
                illustration_id=args.illustration_id, illustration_routing=args.illustration_routing,
                trusted_approvals_sha256=args.approvals_sha256)
            if errors:
                print("QA ÉCHEC :\n"+"\n".join(errors),file=sys.stderr);return 2
            print("QA TECHNIQUE OK | approbation visuelle et KDP toujours en attente");return 0
        book=load_book(args.book,require_plan=False)
        errors=validate_plan_vocabulary(book)
        if errors:
            raise ConfigError("\n".join(errors))
        if args.cmd=="validate":
            demo_specs(book)
            print(f"CONFIGURATION OK | {book.book_id} | {book.pages} pages prévues | {len(book.plan)} pages documentées | démonstration possible")
            return 0
        if args.cmd=="build":
            blockers=full_build_blockers(book)
            if blockers:
                raise ConfigError("ASSEMBLAGE INTÉGRAL REFUSÉ :\n"+"\n".join(blockers))
            raise ConfigError("ASSEMBLAGE INTÉGRAL REFUSÉ : layouts et approbations prépresse V0.2+ indisponibles")
        out=args.out or (book.root/"dist"/book.book_id)
        report=build_demo(book,out,seed=args.seed,
            illustration_id=args.illustration_id,
            illustration_routing=getattr(args, "illustration_routing", None),
            trusted_approvals_sha256=args.approvals_sha256)
        errors=audit_output(out,book=book,
            illustration_id=args.illustration_id,
            illustration_routing=getattr(args, "illustration_routing", None),
            trusted_approvals_sha256=args.approvals_sha256)
        if errors:
            raise ConfigError("QA des artefacts :\n"+"\n".join(errors))
        print(f"DÉMO CRÉÉE : {out} | 3 fiches + 3 corrigés | logique VALIDÉE | revue visuelle EN ATTENTE")
        return 0
    except (ConfigError,RuntimeError,ValueError,OSError) as exc:
        print(f"ERREUR : {exc}",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
