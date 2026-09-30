"""
Optimiza los escudos de crests_raw/ y los deja en app/static/crests/.

  * Recorta el borde transparente, los centra en un cuadrado y los reduce a --size px.
  * Los guarda como WebP (chico y con transparencia). Con --formato png sale PNG optimizado.
  * Nombra cada archivo con la abreviatura del equipo en minusculas (boca.png -> boc.webp),
    porque las plantillas buscan /static/crests/<abreviatura>.webp. Si no puede deducir el
    equipo, conserva el nombre original y te avisa.

Uso (desde la raiz del repo):
  pip install Pillow
  python scripts/optimizar_escudos.py              # procesa lo nuevo o modificado
  python scripts/optimizar_escudos.py --simular    # solo muestra que haria
  python scripts/optimizar_escudos.py --forzar     # reprocesa todo
  python scripts/optimizar_escudos.py --size 96 --calidad 80
"""
import argparse, difflib, sys, unicodedata
from pathlib import Path

from PIL import Image, ImageOps

RAIZ = Path(__file__).resolve().parent.parent
EXTENSIONES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from equipos_abreviaturas import LISTA      # (nombre, abreviatura, texto de busqueda)
except Exception:                                # sin psycopg instalado, etc.
    LISTA = []


# Nombres de archivo que el emparejamiento automatico no resuelve (clave normalizada -> abreviatura).
# Agrega aca lo que te marque [revisar nombre].
ALIAS = {
    "boca 2026": "boc", "estudiantes": "est", "estudiantes lp": "est",
    "gimnasia": "glp", "independiente": "ind", "independienteriv": "iri",
    "independiente riv": "iri", "newells": "nob", "riestra": "rie",
}


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return " ".join("".join(c if c.isalnum() else " " for c in s).split())


def slug(s):
    return norm(s).replace(" ", "-") or "escudo"


def puntajes(stem):
    """Lista de (puntaje, abreviatura) contra cada equipo conocido."""
    n = norm(stem)
    out = []
    for nombre, ab, busq in LISTA:
        candidatos = [norm(nombre)] + ([norm(busq)] if busq else [])
        if n == ab.lower() or n in candidatos:
            p = 1.0
        elif any(c.startswith(n + " ") for c in candidatos):
            p = 0.85                              # "river" -> "river plate"
        else:
            p = max(difflib.SequenceMatcher(None, n, c).ratio() for c in candidatos)
        out.append((p, ab.lower()))
    return out


def deducir_destinos(archivos):
    """({Path: nombre_sin_extension}, {Path: motivo}). Solo asigna si hay un unico mejor candidato (>= 0.8)."""
    destino, motivo = {}, {}
    for f in archivos:
        if norm(f.stem) in ALIAS:
            destino[f] = ALIAS[norm(f.stem)]
            continue
        ps = sorted(puntajes(f.stem), reverse=True)
        if ps and ps[0][0] >= 0.8 and (len(ps) == 1 or ps[1][0] < ps[0][0]):
            destino[f] = ps[0][1]
        else:
            destino[f] = slug(f.stem)
            motivo[f] = "ambiguo" if ps and ps[0][0] >= 0.8 else "sin equipo"
    valores = list(destino.values())
    for f, d in list(destino.items()):              # dos archivos al mismo equipo: no pisar ninguno
        if valores.count(d) > 1:
            destino[f] = slug(f.stem)
            motivo[f] = "repetido"
    return destino, motivo


def procesar(origen, salida, size, fmt, calidad, recortar):
    img = ImageOps.exif_transpose(Image.open(origen)).convert("RGBA")
    if recortar:
        caja = img.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
        if caja:
            img = img.crop(caja)
    margen = round(size * 0.04)
    img = img.convert("RGBa")                       # alpha premultiplicado: evita bordes oscuros al achicar
    img.thumbnail((size - 2 * margen,) * 2, Image.LANCZOS)
    img = img.convert("RGBA")
    lienzo = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    lienzo.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
    if fmt == "webp":
        lienzo.save(salida, "WEBP", quality=calidad, method=6)
    else:
        lienzo.save(salida, "PNG", optimize=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origen", default=str(RAIZ / "crests_raw"))
    ap.add_argument("--destino", default=str(RAIZ / "app" / "static" / "crests"))
    ap.add_argument("--size", type=int, default=128, help="lado del cuadrado final en px (default 128)")
    ap.add_argument("--calidad", type=int, default=85, help="calidad WebP 1-100 (default 85)")
    ap.add_argument("--formato", choices=("webp", "png"), default="webp")
    ap.add_argument("--sin-recorte", action="store_true", help="no recortar el borde transparente")
    ap.add_argument("--forzar", action="store_true", help="reprocesar aunque el destino este al dia")
    ap.add_argument("--simular", action="store_true", help="no escribe nada")
    a = ap.parse_args()

    origen, destino = Path(a.origen), Path(a.destino)
    if not origen.is_dir():
        sys.exit(f"No existe {origen}")
    todos = sorted(p for p in origen.iterdir() if p.is_file() and not p.name.startswith("."))
    for p in (p for p in todos if p.suffix.lower() == ".svg"):
        print(f"  ! {p.name}: SVG no soportado, exportalo a PNG")
    archivos = [p for p in todos if p.suffix.lower() in EXTENSIONES]
    if not archivos:
        sys.exit(f"No hay imagenes en {origen}")
    if not LISTA:
        print("  ! No pude leer la lista de equipos: los archivos conservan su nombre original.")

    nombres, motivo = deducir_destinos(archivos) if LISTA else ({f: slug(f.stem) for f in archivos}, {})
    if not a.simular:
        destino.mkdir(parents=True, exist_ok=True)

    antes = despues = hechos = 0
    for f in archivos:
        salida = destino / f"{nombres[f]}.{a.formato}"
        peso_ini = f.stat().st_size
        if not a.forzar and salida.exists() and salida.stat().st_mtime >= f.stat().st_mtime:
            print(f"  = {f.name} -> {salida.name} (al dia)")
            continue
        aviso = f"   [{motivo[f]}: revisar nombre]" if f in motivo else ""
        if a.simular:
            print(f"  ? {f.name} -> {salida.name}{aviso}")
            continue
        try:
            procesar(f, salida, a.size, a.formato, a.calidad, not a.sin_recorte)
        except Exception as e:
            print(f"  ! {f.name}: {e}")
            continue
        antes += peso_ini; despues += salida.stat().st_size; hechos += 1
        print(f"  + {f.name} -> {salida.name}  {peso_ini/1024:.1f} KB -> {salida.stat().st_size/1024:.1f} KB{aviso}")

    if hechos:
        print(f"\n{hechos} escudos. Total {antes/1024:.0f} KB -> {despues/1024:.0f} KB ({100 - 100*despues/max(antes,1):.0f}% menos).")


if __name__ == "__main__":
    main()