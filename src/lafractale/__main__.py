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
            p.add_argument("--pip-placement", help="Politique C2 opt-in de placement de Pip (après routage C1)")
            p.add_argument("--editorial-profile", help="Profil éditorial opt-in C4 (après routage C1 + placement C2 V2)")
        p.add_argument("--seed",type=int,default=2026)
    p_qa=subs.add_parser("qa",help="Vérifier les artefacts d'une démo")
    p_qa.add_argument("out",type=Path)
    p_qa.add_argument("--book",required=True,type=Path,help="YAML source de confiance obligatoire pour recalculer les noms réservés")
    p_qa.add_argument("--illustration-id", help="Visuel monochrome explicitement autorisé")
    p_qa.add_argument("--illustration-routing", help="Politique C1 fermée de routage par activité")
    p_qa.add_argument("--pip-placement", help="Politique C2 opt-in de placement de Pip (après routage C1)")
    p_qa.add_argument("--editorial-profile", help="Profil éditorial opt-in C4 (après routage C1 + placement C2 V2)")
    p_qa.add_argument("--approvals-sha256", help="Empreinte de registre approuvée hors sorties")
    p_prev=subs.add_parser("preview",help="Aperçu PDF de 56 pages du livre (non destiné à la publication)")
    p_prev.add_argument("book_dir",type=Path,help="Dossier du livre (book.yaml + pages.csv)")
    p_prev.add_argument("--out",type=Path,default=Path("dist/book_preview"))
    p_prev.add_argument("--seed",type=int,default=2026)
    p_prev.add_argument("--overwrite",action="store_true",help="Remplacer explicitement un aperçu existant")
    p_assets=subs.add_parser("assets",help="Illustrations : liste, import/remplacement de PNG")
    p_assets.add_argument("action",choices=("list","import"))
    p_assets.add_argument("files",nargs="*",type=Path,help="PNG à importer (nom du fichier = id de l'asset)")
    p_assets.add_argument("--id",help="id de l'asset si le nom du fichier ne le donne pas")
    p_assets.add_argument("--book-dir",type=Path,default=Path("books/halloween_2026"))
    p_pil=subs.add_parser("pilots",help="Aperçu PDF/PNG des pages pilotes illustrées")
    p_pil.add_argument("book_dir",type=Path)
    p_pil.add_argument("--out",type=Path,default=Path("dist/pilots"))
    p_pil.add_argument("--pages",default="4,5,13,20")
    p_pil.add_argument("--overwrite",action="store_true")
    args=parser.parse_args(argv)
    try:
        if args.cmd in ("assets","pilots"):
            from lafractale.book.pages import BookError
            from lafractale.book import assets as A
            try:
                if args.cmd=="pilots":
                    from lafractale.book.preview import build_preview
                    s=build_preview(args.book_dir,args.out,overwrite=args.overwrite,
                                    only=tuple(int(p) for p in args.pages.split(",")))
                    missing=[i for i in s["assets"] if i["status"]=="ASSET_MANQUANT"]
                    print(f"PILOTES CRÉÉS : {args.out} | {s['pages']} pages | {len(missing)} ASSET_MANQUANT | "
                          "NON DESTINÉ À LA PUBLICATION")
                    return 0
                root=args.book_dir.resolve().parents[1]
                man=A.load_manifest(args.book_dir/"assets_manifest.yaml",root)
                if args.action=="list":
                    for row in A.status_rows(man):
                        print("  ".join(row))
                    return 0
                if not args.files:
                    raise BookError("indiquer au moins un PNG à importer")
                if args.id and len(args.files)!=1:
                    raise BookError("--id n'accepte qu'un seul fichier")
                for f in args.files:
                    r=A.import_png(man,args.id or f.stem,f)
                    print(f"IMPORTÉ {r['asset']} v{r['version']} ({r['width']}x{r['height']}, {r['mode']})")
                return 0
            except BookError as exc:
                raise ConfigError(str(exc)) from exc
        if args.cmd=="preview":
            from lafractale.book.pages import BookError
            from lafractale.book.preview import build_preview
            try:
                s=build_preview(args.book_dir,args.out,seed=args.seed,overwrite=args.overwrite)
            except BookError as exc:
                raise ConfigError(str(exc)) from exc
            print(f"APERÇU CRÉÉ : {args.out} | {s['pages']} pages | {s['jouables']} jouables | "
                  f"{s['provisoires']} provisoires | NON DESTINÉ À LA PUBLICATION")
            return 0
        if args.cmd=="qa":
            errors=audit_output(args.out,book=load_book(args.book,require_plan=False),
                illustration_id=args.illustration_id, illustration_routing=args.illustration_routing,
                pip_placement=args.pip_placement,
                editorial_profile=getattr(args, "editorial_profile", None),
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
            pip_placement=getattr(args, "pip_placement", None),
            editorial_profile=getattr(args, "editorial_profile", None),
            trusted_approvals_sha256=args.approvals_sha256)
        errors=audit_output(out,book=book,
            illustration_id=args.illustration_id,
            illustration_routing=getattr(args, "illustration_routing", None),
            pip_placement=getattr(args, "pip_placement", None),
            editorial_profile=getattr(args, "editorial_profile", None),
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
