"""Black-and-white vector layout; no generated character or fabricated illustration."""
from __future__ import annotations
import math
import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from lafractale.activities.models import Activity
from lafractale import __version__


def fonts() -> tuple[str, str]:
    # Bundle no proprietary or system font: require local licensed fonts.
    regular = Path(os.getenv("LAFRACTALE_FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    bold = Path(os.getenv("LAFRACTALE_FONT_BOLD_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    if not regular.is_file() or not bold.is_file():
        raise RuntimeError("DejaVu Sans TTF absent : définir LAFRACTALE_FONT_PATH et LAFRACTALE_FONT_BOLD_PATH")
    for name, filename in (("LaFractaleRegular", regular), ("LaFractaleBold", bold)):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(filename)))
    return "LaFractaleRegular", "LaFractaleBold"


def write_pdf(path: Path, activities: list[Activity], book: dict, *, answer_key: bool) -> None:
    regular, bold = fonts()
    width, height = book["trim"]["width_in"] * 72, book["trim"]["height_in"] * 72
    margin = 55
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=(width, height), invariant=1, pageCompression=1)
    c.setTitle(("CORRIGES" if answer_key else "DEMONSTRATION") + " - " + book["title"])
    c.setAuthor(book["publisher"])
    for index, activity in enumerate(activities, start=1):
        c.setFillColorRGB(0,0,0)
        c.setStrokeColorRGB(0,0,0)
        c.setLineWidth(1)
        c.setFont(bold, 19)
        c.drawString(margin, height - 69, "CORRIGÉ" if answer_key else (f"Je joue avec {activity.companion_name} !" if activity.companion_name else "Je joue et j’apprends !"))
        c.setFont(regular, 10)
        c.drawRightString(width - margin, height - 64, f"Démo {__version__} | fiche {activity.page}")
        c.line(margin,height-82,width-margin,height-82)
        # Never silently truncate instructions or stories.
        for value, font_name, size in ((activity.scene,bold,13),(activity.prompt_fr,regular,12),
                                       (activity.prompt_en,regular,10)):
            if pdfmetrics.stringWidth(value,font_name,size) > width - 2 * margin:
                raise ValueError(f"Texte déborde la zone sûre : {activity.id}: {value}")
        c.setFont(bold, 13)
        c.drawString(margin,height-113,activity.scene)
        c.setFont(regular, 12)
        c.drawString(margin,height-143,activity.prompt_fr)
        c.setFont(regular, 10)
        c.drawString(margin,height-163,activity.prompt_en)
        if activity.type == "maze":
            _maze(c, activity, width, height, answer_key, bold)
        elif activity.type == "match":
            _match(c, activity, width, height, answer_key, regular)
        elif activity.type == "connect_dots":
            _dots(c, activity, width, height, answer_key, bold)
        else:
            raise ValueError(f"Type de rendu absent : {activity.type}")
        c.setFont(regular, 8)
        c.setFillColorRGB(.28,.28,.28)
        c.drawString(margin,50,"MAQUETTE TECHNIQUE | contrôle visuel et KDP non effectués")
        c.drawRightString(width-margin,50,f"{index} / {len(activities)}")
        c.showPage()
    c.save()


def _maze(c, act, width, height, solution, font):
    g=act.geometry
    n=g["size"]
    side=61
    ox=(width-n*side)/2
    oy=227
    passages={tuple(sorted((tuple(a),tuple(b)))) for a,b in g["open_edges"]}
    c.setLineWidth(2.7)
    for y in range(n):
        for x in range(n):
            # Each shared wall is drawn only once (north and west for each cell).
            left=(x,y)
            if y==0 or tuple(sorted((left,(x,y-1)))) not in passages:
                c.line(ox+x*side,oy+y*side,ox+(x+1)*side,oy+y*side)
            if x==0 or tuple(sorted((left,(x-1,y)))) not in passages:
                c.line(ox+x*side,oy+y*side,ox+x*side,oy+(y+1)*side)
    c.line(ox,oy+n*side,ox+n*side,oy+n*side)
    c.line(ox+n*side,oy,ox+n*side,oy+n*side)
    c.setFont(font,11)
    c.drawCentredString(ox+side/2, oy+side/2 - 5, "D")
    c.drawCentredString(ox+(n-.5)*side, oy+(n-.5)*side - 5, "A")
    c.setFont(font,9)
    c.drawString(ox,oy-35,"D = Départ")
    c.drawRightString(ox+n*side,oy-35,"A = Arrivée")
    if solution:
        c.saveState()
        c.setStrokeColorRGB(.45,.45,.45)
        c.setLineWidth(5)
        c.setLineCap(1)
        path=c.beginPath()
        for i,(x,y) in enumerate(act.answer["path"]):
            px,py=ox+(x+.5)*side,oy+(y+.5)*side
            if i==0:path.moveTo(px,py)
            else:path.lineTo(px,py)
        c.drawPath(path)
        c.restoreState()


def _symbol(c,name,x,y,r):
    if name.startswith("hat_"):
        # Four distinct hat insignia, not an unrelated shape on a hat activity.
        p=c.beginPath();p.moveTo(x-r*.78,y-r*.42)
        p.lineTo(x-r*.46,y-r*.42);p.lineTo(x,y+r*.95)
        p.lineTo(x+r*.46,y-r*.42);p.lineTo(x+r*.78,y-r*.42)
        p.lineTo(x+r*.85,y-r*.63);p.lineTo(x-r*.85,y-r*.63)
        p.close();c.drawPath(p,stroke=1,fill=0)
        _symbol(c,name[4:],x,y-r*.22,r*.26)
        return
    if name.startswith("gift_"):
        # Identical boxes with a distinct center emblem, for visual matching.
        c.rect(x-r*.80,y-r*.72,r*1.6,r*1.4,stroke=1,fill=0)
        c.line(x-r*.80,y+r*.35,x+r*.80,y+r*.35)
        c.line(x,y+r*.35,x,y+r*.67)
        _symbol(c,name[5:],x,y-r*.18,r*.29)
        return
    p=c.beginPath()
    if name=="circle": c.circle(x,y,r,stroke=1,fill=0);return
    if name=="square": c.rect(x-r,y-r,2*r,2*r,stroke=1,fill=0);return
    if name=="triangle": count=3;offset=math.pi/2
    elif name=="diamond":count=4;offset=math.pi/2
    elif name=="star":count=10;offset=math.pi/2
    elif name=="hexagon":count=6;offset=math.pi/2
    else:raise ValueError(f"Symbole non implémenté : {name}")
    for i in range(count):
        rr=(r if i%2==0 else .47*r) if name=="star" else r
        theta=offset+2*math.pi*i/count
        px,py=x+rr*math.cos(theta),y+rr*math.sin(theta)
        (p.moveTo if i==0 else p.lineTo)(px,py)
    p.close()
    c.drawPath(p,stroke=1,fill=0)


def _match(c, act, width, height, solution, font):
    leftx=width*.30
    rightx=width*.70
    ys=[557,465,373,281]
    c.setLineWidth(2.4)
    for i,name in enumerate(act.geometry["left_symbols"]):
        c.circle(leftx+43,ys[i],3,stroke=1,fill=1)
        _symbol(c,name,leftx-42,ys[i],21)
    for i,name in enumerate(act.geometry["right_symbols"]):
        c.circle(rightx-43,ys[i],3,stroke=1,fill=1)
        _symbol(c,name,rightx+42,ys[i],21)
    if solution:
        c.saveState();c.setStrokeColorRGB(.43,.43,.43);c.setLineWidth(1.6)
        for i,j in enumerate(act.answer["left_to_right"]):
            c.line(leftx+43,ys[i],rightx-43,ys[j])
        c.restoreState()
    c.setFont(font,10)
    family=act.geometry.get("family", "shapes")
    label={"hats":"Chaque chapeau a son jumeau.", "gifts":"Chaque cadeau a son jumeau.",
           "shapes":"Chaque forme a une seule jumelle."}[family]
    c.drawCentredString(width/2,205,label)


def _dots(c,act,width,height,solution,font):
    points=act.geometry["points"]
    ox,oy=(width-330)/2,210
    points_xy=[(ox+p["x"]*330,oy+p["y"]*380) for p in points]
    if solution:
        c.saveState();c.setStrokeColorRGB(.45,.45,.45);c.setLineWidth(2.7)
        p=c.beginPath()
        for i,(x,y) in enumerate(points_xy):
            (p.moveTo if i==0 else p.lineTo)(x,y)
        p.close();c.drawPath(p)
        c.restoreState()
    c.setFont(font,11)
    for item,(x,y) in zip(points,points_xy):
        c.circle(x,y,3.5,stroke=1,fill=1)
        # Position number away from contour: alternate systematic offsets.
        dx=10 if x < width/2 else -24
        dy=7 if y < (oy+200) else 5
        c.drawString(x+dx,y+dy,str(item["n"]))
    c.setFont(font,10)
    label={"moon":"lune", "star":"étoile", "house":"maison"}[act.geometry["shape"]]
    c.drawCentredString(width/2,177,f"Forme : {label} | du point 1 au {len(points)} puis au 1")
