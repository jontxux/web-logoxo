#!/usr/bin/env python3
"""Genera la web estática de Logoxo en publico/.

    python3 generar.py            genera publico/
    python3 generar.py --servir   genera y la sirve en http://localhost:8000

Solo usa la biblioteca estándar y ImageMagick (magick) para reducir las fotos.
Los ajustes están en config.toml y los textos en textos/<idioma>.toml.
"""

import argparse
import functools
import hashlib
import html
import http.server
import json
import shutil
import subprocess
import tomllib
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "publico"

CFG = tomllib.loads((AQUI / "config.toml").read_text(encoding="utf-8"))
IDIOMAS = CFG["sitio"]["idiomas"]
TXT = {i: tomllib.loads((AQUI / "textos" / f"{i}.toml").read_text(encoding="utf-8")) for i in IDIOMAS}
APTOS = {a["clave"]: a for a in CFG["apartamento"]}
C = CFG["contacto"]

ICONOS = {
    "ola": '<path d="M2 16c2 0 2-1.5 4-1.5S8 16 10 16s2-1.5 4-1.5 2 1.5 4 1.5 2-1.5 4-1.5M2 20c2 0 2-1.5 4-1.5S8 20 10 20s2-1.5 4-1.5 2 1.5 4 1.5 2-1.5 4-1.5"/><circle cx="16" cy="7" r="3"/>',
    "acceso": '<circle cx="11" cy="4.5" r="1.5"/><path d="M11 8v6h5l2.5 5"/><path d="M11 10.5h4.5"/><path d="M14.5 17.5A5 5 0 1 1 8 12"/>',
    "wifi": '<path d="M2.5 9.5a14 14 0 0 1 19 0M5.5 13a9.5 9.5 0 0 1 13 0M8.5 16.5a5 5 0 0 1 7 0"/><circle cx="12" cy="19.5" r=".8" fill="currentColor"/>',
    "cocina": '<path d="M7 3v8M4.5 3v4.5a2.5 2.5 0 0 0 5 0V3M7 11v10M17 21V3c-2 1-3.5 3.500-3.500 7 0 2 1.500 3 3.500 3"/>',
    "calor": '<path d="M12 3c1 3 4.500 4.500 4.500 9a4.500 4.500 0 0 1-9 0c0-1.500.5-2.500 1.500-3.500.3 1.500 1 2 1.500 2C10 8 10.500 5 12 3Z"/><path d="M5 21h14"/>',
    "cama": '<path d="M3 18v-6.500A2.500 2.500 0 0 1 5.500 9h13a2.500 2.500 0 0 1 2.500 2.500V18M3 15h18M3 18v2M21 18v2M6 9V6.500A1.500 1.500 0 0 1 7.500 5h9A1.500 1.500 0 0 1 18 6.500V9"/>',
    "flecha": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "mapa": '<path d="M12 21s-6.500-5.600-6.500-11a6.500 6.500 0 0 1 13 0c0 5.400-6.500 11-6.500 11Z"/><circle cx="12" cy="10" r="2.300"/>',
    "check": '<path d="m5 12.500 4.500 4.500L19 7.500"/>',
}


def e(texto):
    return html.escape(str(texto), quote=True)


def icono(nombre, clase="icono"):
    return (f'<svg class="{clase}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONOS[nombre]}</svg>')


# ---------------------------------------------------------------- fotos

def preparar_foto(origen, base):
    """Reduce una foto a los anchos de config y devuelve nombre base y medidas."""
    if not origen.exists():
        raise SystemExit(f"Falta la foto {origen}")
    destino = SALIDA / "fotos"
    destino.mkdir(parents=True, exist_ok=True)
    w, h = (int(x) for x in subprocess.run(
        ["magick", "identify", "-auto-orient", "-format", "%w %h", str(origen)],
        check=True, capture_output=True, text=True).stdout.split())
    anchos = [a for a in CFG["sitio"]["anchos"] if a <= w] or [w]
    for ancho in anchos:
        fichero_web = destino / f"{base}-{ancho}.webp"
        if not fichero_web.exists() or fichero_web.stat().st_mtime < origen.stat().st_mtime:
            # -strip quita los metadatos (fecha, móvil, posición) de la foto
            subprocess.run(["magick", str(origen), "-auto-orient", "-resize", f"{ancho}x", "-strip",
                            "-quality", "80", str(fichero_web)], check=True)
    return {"base": base, "w": w, "h": h, "anchos": anchos}


@functools.cache
def foto(apto, fichero):
    """Foto de un apartamento (de la carpeta de originales de config)."""
    origen = Path(CFG["sitio"]["fotos"]).expanduser() / APTOS[apto]["carpeta"] / f"{fichero}.jpg"
    return preparar_foto(origen, f"{apto}-{fichero[-6:]}")


@functools.cache
def foto_zarautz(nombre):
    """Foto de Zarautz (de fotos-zarautz/, dentro del proyecto)."""
    return preparar_foto(AQUI / "fotos-zarautz" / f"{nombre}.jpg", f"zarautz-{nombre}")


def creditos(idioma):
    """Autor y licencia de las fotos de Zarautz que no son propias."""
    partes = []
    for nombre, f in CFG["zarautz"]["fotos"].items():
        if f.get("autor"):
            partes.append(f'<a href="{e(f["origen"])}" rel="noopener">{e(f["autor"])}</a> '
                          f'(<a href="{e(f["licencia_url"])}" rel="noopener license">{e(f["licencia"])}</a>)')
    return f'<p class="creditos">{e(TXT[idioma]["zarautz"]["creditos"])}: {", ".join(partes)}, Wikimedia Commons.</p>'


def img(raiz, f, alt, sizes, clase="", prioritaria=False):
    srcset = ", ".join(f"{raiz}fotos/{f['base']}-{a}.webp {a}w" for a in f["anchos"])
    medio = f["anchos"][min(1, len(f["anchos"]) - 1)]
    carga = 'fetchpriority="high"' if prioritaria else 'loading="lazy" decoding="async"'
    return (f'<img class="{clase}" src="{raiz}fotos/{f["base"]}-{medio}.webp" srcset="{srcset}" sizes="{sizes}" '
            f'width="{f["w"]}" height="{f["h"]}" alt="{e(alt)}" {carga}>')


def alt_foto(idioma, apto, tema):
    t = TXT[idioma]
    corto = next(a["corto"] for a in t["apto"] if a["clave"] == apto)
    return t["fotos"][tema] if tema == "fachada" else f"{corto}: {t['fotos'][tema]}"


# ---------------------------------------------------------------- rutas

def ruta(idioma, pagina="inicio"):
    """Ruta de una página dentro del sitio, sin barra inicial y con barra final."""
    t = TXT[idioma]
    if pagina == "inicio":
        return f"{idioma}/"
    for grupo in ("apto", "legal"):
        for x in t[grupo]:
            if x["clave"] == pagina:
                return f"{idioma}/{x['slug']}/"
    raise KeyError(pagina)


def url_reserva(idioma, apto):
    return CFG["reserva"]["url"].format(idioma=idioma, id=APTOS[apto]["id"])


def enlace_reserva(idioma, apto):
    fijos = "&".join(f"{k}={v}" for k, v in CFG["reserva"]["fijos"].items())
    return url_reserva(idioma, apto) + ("?" + fijos if fijos else "")


@functools.cache
def version(nombre):
    return hashlib.sha1((AQUI / "estatico" / nombre).read_bytes()).hexdigest()[:8]


# ---------------------------------------------------------------- piezas

def formulario(idioma, raiz, apto=None, ident="reserva"):
    """Fechas y huéspedes. Con JavaScript consulta qué apartamentos están libres
    y los enseña con su precio; sin él, envía a la pasarela de reservas."""
    t, r = TXT[idioma], CFG["reserva"]
    tr = t["reserva"]
    campos = [
        f'<label class="campo"><span>{e(tr["llegada"])}</span>'
        f'<input type="date" name="{r["llegada"]}" data-llegada required></label>',
        f'<label class="campo"><span>{e(tr["salida"])}</span>'
        f'<input type="date" name="{r["salida"]}" data-salida required></label>',
    ]
    personas = "".join(f'<option{" selected" if n == 2 else ""}>{n}</option>'
                       for n in range(1, r["max_huespedes"] + 1))
    campos.append(f'<label class="campo campo-corto"><span>{e(tr["huespedes"])}</span>'
                  f'<select name="{r["adultos"]}" data-huespedes>{personas}</select></label>')
    ocultos = "".join(f'<input type="hidden" name="{e(k)}" value="{e(v)}">' for k, v in r["fijos"].items())
    accion = url_reserva(idioma, apto or t["apto"][0]["clave"])
    # Lo que necesita web.js para pintar los resultados; el apartamento de la
    # ficha en la que se está va el primero.
    aptos = sorted(t["apto"], key=lambda a: a["clave"] != apto)
    datos = {
        "busqueda": r.get("busqueda", ""), "idioma": idioma,
        "parametros": {"llegada": r["llegada"], "salida": r["salida"], "adultos": r["adultos"], **r["fijos"]},
        "textos": {k: tr[k] for k in ("buscando", "libre", "ocupado", "noche", "noches", "total", "por_noche",
                                      "ninguno", "fallo", "resultados", "elegir", "ver_precio")} | {"ver": t["aptos"]["ver"]},
        "aptos": [{
            "id": APTOS[a["clave"]]["id"], "nombre": a["corto"], "lema": a["lema"],
            "reserva": url_reserva(idioma, a["clave"]), "ficha": raiz + ruta(idioma, a["clave"]),
            "foto": f'{raiz}fotos/{foto(a["clave"], APTOS[a["clave"]]["fotos"][0]["f"])["base"]}-640.webp',
        } for a in aptos],
    }
    return f'''<form class="reserva" id="{ident}" action="{e(accion)}" method="get" data-reserva data-error="{e(tr["error"])}" data-datos="{e(json.dumps(datos, ensure_ascii=False))}">
<h2 class="reserva-titulo">{e(tr["titulo"])}</h2>
<div class="reserva-campos">{"".join(campos)}{ocultos}
<button class="boton" type="submit">{e(tr["boton"])}{icono("flecha")}</button></div>
<p class="reserva-nota" data-nota>{e(tr["nota"])}</p>
<div class="resultados" data-resultados aria-live="polite" hidden></div>
</form>'''


def lista_condiciones(idioma):
    items = "".join(
        f'<div class="condicion"><dt>{e(c["titulo"])}</dt>'
        f'<dd>{e(c["texto"].format(entrada=C["entrada"], salida=C["salida"]))}</dd></div>'
        for c in TXT[idioma]["condiciones"]["item"])
    return f'<dl class="condiciones">{items}</dl>'


def lista_zona(idioma):
    return '<dl class="cerca">' + "".join(
        f'<div><dt>{e(z["termino"])}</dt><dd>{e(z["texto"])}</dd></div>' for z in TXT[idioma]["zona"]["item"]) + "</dl>"


def mapa(idioma, raiz):
    """Recorte de OpenStreetMap servido desde aquí, con la marca de la casa."""
    m = CFG["mapa"]
    return f'''<figure class="mapa">
<a href="{e(C["mapa"])}" rel="noopener"><img src="{raiz}estatico/mapa.webp" width="1120" height="640" alt="{e(TXT[idioma]["zarautz"]["mapa_alt"])}" loading="lazy" decoding="async">
<span class="mapa-marca" style="left:{m["x"]}%;top:{m["y"]}%"><span>Logoxo</span></span></a>
<figcaption>© <a href="https://www.openstreetmap.org/copyright" rel="noopener">OpenStreetMap</a></figcaption>
</figure>'''


def tarjeta_apto(idioma, raiz, a, titulo="h3"):
    t = TXT[idioma]
    cfg = APTOS[a["clave"]]
    datos = [t["ficha"]["m2"].format(n=cfg["m2"]), t["aptos"]["huespedes"], t["aptos"]["camas"], t["aptos"]["planta"]]
    destino = raiz + ruta(idioma, a["clave"])
    # Las cinco primeras fotos, que se pasan con el dedo o con las flechas.
    fotos = "".join(
        f'<li>{img(raiz, foto(a["clave"], f["f"]), alt_foto(idioma, a["clave"], f["t"]), "(min-width: 900px) 560px, 100vw")}</li>'
        for f in cfg["fotos"][:5])
    return f'''<article class="apto">
<div class="carrusel" data-carrusel>
<ul class="carrusel-fotos" tabindex="0" aria-label="{e(a["corto"])}">{fotos}</ul>
<button class="carrusel-flecha" type="button" data-paso="-1" aria-label="{e(t["ficha"]["anterior"])}" hidden>←</button>
<button class="carrusel-flecha" type="button" data-paso="1" aria-label="{e(t["ficha"]["siguiente"])}" hidden>→</button>
</div>
<div class="apto-cuerpo">
<{titulo} class="apto-nombre"><a href="{destino}">{e(a["corto"])}</a></{titulo}>
<p class="apto-lema">{e(a["lema"])}</p>
<ul class="datos">{"".join(f"<li>{e(d)}</li>" for d in datos)}</ul>
<p>{e(a["resumen"])}</p>
<p class="acciones"><a class="boton" href="{destino}">{e(t["aptos"]["ver"])}</a>
<a class="boton boton-claro" href="{e(enlace_reserva(idioma, a["clave"]))}">{e(t["aptos"]["reservar"])}</a></p>
</div></article>'''


def bloque_contacto(idioma):
    t = TXT[idioma]["contacto"]
    tel = C["telefono"].replace(" ", "")
    return f'''<section class="seccion contacto" id="contacto">
<div class="ancho contacto-caja">
<div><p class="etiqueta">{e(t["etiqueta"])}</p><h2>{e(t["titulo"])}</h2><p class="entrada">{e(t["texto"])}</p>
<p class="acciones"><a class="boton boton-inverso" href="#reserva">{e(TXT[idioma]["reserva"]["titulo"])}</a></p></div>
<ul class="vias">
<li><span>{e(t["whatsapp"])}</span><a href="https://wa.me/{C["whatsapp"]}" rel="noopener">{e(C["telefono"])}</a></li>
<li><span>{e(t["llamar"])}</span><a href="tel:{tel}">{e(C["telefono"])}</a></li>
<li><span>{e(t["correo"])}</span><a href="mailto:{C["correo"]}">{e(C["correo"])}</a></li>
</ul></div></section>'''


def pagina(idioma, pag, titulo, descripcion, cuerpo, *, raiz, alternos, imagen=None, datos=None, clase=""):
    """Envuelve el cuerpo con la cabecera, el menú y el pie comunes."""
    t = TXT[idioma]
    dominio = CFG["sitio"]["dominio"].rstrip("/")
    inicio = raiz + ruta(idioma)
    canonica = f"{dominio}/{alternos[idioma]}"
    hreflang = "".join(f'<link rel="alternate" hreflang="{i}" href="{dominio}/{r}">' for i, r in alternos.items())
    hreflang += f'<link rel="alternate" hreflang="x-default" href="{dominio}/{alternos[IDIOMAS[0]]}">'
    og = ""
    if imagen:
        og = f'<meta property="og:image" content="{dominio}/fotos/{imagen["base"]}-{imagen["anchos"][min(1, len(imagen["anchos"]) - 1)]}.webp">'
    ld = f'<script type="application/ld+json">{json.dumps(datos, ensure_ascii=False)}</script>' if datos else ""
    secciones = [("apartamentos", "apartamentos"), ("ubicacion", "ubicacion"),
                 ("condiciones", "condiciones"), ("contacto", "contacto")]
    menu = "".join(f'<a href="{inicio if pag != "inicio" else ""}#{ancla}">{e(t["nav"][clave])}</a>'
                   for clave, ancla in secciones)
    lenguas = "".join(
        f'<a href="{raiz}{r}" lang="{i}" hreflang="{i}" title="{e(TXT[i]["meta"]["nombre"])}"'
        f'{" aria-current=\"true\"" if i == idioma else ""}>{TXT[i]["meta"]["etiqueta"]}</a>'
        for i, r in alternos.items())
    legales = "".join(f'<a href="{raiz}{ruta(idioma, l["clave"])}">{e(l["titulo"])}</a>' for l in t["legal"])
    tel = C["telefono"].replace(" ", "")
    return f'''<!doctype html>
<html lang="{idioma}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)}</title>
<meta name="description" content="{e(descripcion)}">
<link rel="canonical" href="{canonica}">
{"" if CFG["sitio"].get("indexar", True) else '<meta name="robots" content="noindex">'}
{hreflang}
<meta property="og:type" content="website">
<meta property="og:site_name" content="Logoxo">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(descripcion)}">
<meta property="og:url" content="{canonica}">
<meta property="og:locale" content="{t["meta"]["locale"]}">
{og}
<meta name="theme-color" content="#f6f3ee">
<link rel="icon" href="{raiz}estatico/icono-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{raiz}estatico/icono-180.png">
<link rel="preload" href="{raiz}estatico/fuentes/fraunces.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{raiz}estatico/estilos.css?v={version("estilos.css")}">
<script src="{raiz}estatico/web.js?v={version("web.js")}" defer></script>
{ld}
</head>
<body class="{clase}">
<a class="saltar" href="#contenido">{e(t["nav"]["saltar"])}</a>
<header class="cabecera">
<div class="ancho cabecera-fila">
<a class="marca" href="{inicio}" aria-label="Logoxo · {e(t["nav"]["inicio"])}"><img src="{raiz}estatico/logo.png" width="53" height="40" alt=""><span>Logoxo</span></a>
<button class="menu-boton" type="button" aria-expanded="false" aria-controls="menu" data-menu>{e(t["nav"]["menu"])}</button>
<nav class="menu" id="menu" aria-label="{e(t["nav"]["menu"])}">{menu}
<span class="lenguas" role="group" aria-label="{e(t["nav"]["idioma"])}">{lenguas}</span>
<a class="boton boton-menu" href="{"" if pag in ("inicio", *APTOS) else inicio}#reserva">{e(t["nav"]["reservar"])}</a></nav>
</div>
</header>
<main id="contenido">
{cuerpo}
</main>
<footer class="pie">
<div class="ancho pie-fila">
<div class="pie-marca"><img src="{raiz}estatico/logo-blanco.png" width="64" height="48" alt="" loading="lazy"><p><strong>Logoxo</strong><br>{e(t["pie"]["lema"])}</p></div>
<address>{e(C["calle"])}<br>{e(C["cp"])} {e(C["localidad"])}, {e(C["provincia"])}<br><a href="tel:{tel}">{e(C["telefono"])}</a><br><a href="mailto:{C["correo"]}">{e(C["correo"])}</a></address>
<nav class="pie-legal" aria-label="Legal">{legales}</nav>
</div>
<div class="ancho pie-final"><p>{e(t["pie"]["registro"])}: {e(C["registro"])}</p><p>© <span data-anio>2026</span> Logoxo · {e(t["pie"]["derechos"])}</p></div>
</footer>
</body>
</html>
'''


# ---------------------------------------------------------------- páginas

def datos_estructurados(idioma):
    dominio = CFG["sitio"]["dominio"].rstrip("/")
    f = foto_zarautz(CFG["portada"]["fondo"])
    return {
        "@context": "https://schema.org", "@type": "LodgingBusiness", "name": "Logoxo",
        "description": TXT[idioma]["meta"]["descripcion"], "url": f"{dominio}/{ruta(idioma)}",
        "image": f"{dominio}/fotos/{f['base']}-{f['anchos'][-1]}.webp",
        "telephone": C["telefono"], "email": C["correo"],
        "address": {"@type": "PostalAddress", "streetAddress": C["calle"], "postalCode": C["cp"],
                    "addressLocality": C["localidad"], "addressRegion": C["provincia"], "addressCountry": "ES"},
        "checkinTime": C["entrada"], "checkoutTime": C["salida"], "petsAllowed": False,
        "numberOfRooms": len(APTOS),
    }


def inicio(idioma, raiz):
    t = TXT[idioma]
    p, z = CFG["portada"]["foto"], CFG["zona"]["foto"]
    tz = t["zarautz"]
    cifras = "".join(f'<div><dt>{e(c["texto"])}</dt><dd>{e(c["valor"])}</dd></div>' for c in t["cifras"])
    ventajas = "".join(
        f'<li>{icono(v["icono"])}<h3>{e(v["titulo"])}</h3><p>{e(v["texto"])}</p></li>' for v in t["ventajas"]["item"])
    directo = "".join(
        f'<li><span class="numero">{n:02d}</span><h3>{e(d["titulo"])}</h3><p>{e(d["texto"])}</p></li>'
        for n, d in enumerate(t["directo"]["item"], 1))
    mosaico = "".join(
        f'<figure>{img(raiz, foto_zarautz(n), tz["fotos"][n], "(min-width: 900px) 50vw, 100vw" if i == 0 else "(min-width: 900px) 25vw, 50vw")}'
        f'<figcaption>{e(tz["fotos"][n])}</figcaption></figure>'
        for i, n in enumerate(CFG["zarautz"]["mosaico"]))
    fondo = CFG["portada"]["fondo"]
    return f'''<section class="portada">
{img(raiz, foto_zarautz(fondo), tz["fotos"][fondo], "100vw", "portada-fondo", prioritaria=True)}
<div class="ancho portada-texto">
<p class="etiqueta">{e(t["portada"]["etiqueta"])}</p>
<h1>{e(t["portada"]["titulo"])}</h1>
<p class="subtitulo">{e(t["portada"]["subtitulo"])}</p>
</div>
</section>
<div class="ancho portada-buscador">{formulario(idioma, raiz)}</div>

<section class="seccion presentacion">
<div class="ancho dos">
<div><p class="etiqueta">{e(tz["presentacion"])}</p>
<p class="grande">{e(t["portada"]["texto"])}</p>
<dl class="cifras">{cifras}</dl>
<p class="acciones"><a class="enlace-flecha" href="#apartamentos">{e(t["portada"]["ver"])}{icono("flecha")}</a></p></div>
<figure class="presentacion-foto">{img(raiz, foto(p["apto"], p["f"]), alt_foto(idioma, p["apto"], p["t"]), "(min-width: 900px) 50vw, 100vw")}</figure>
</div>
</section>

<section class="seccion" id="apartamentos">
<div class="ancho">
<header class="seccion-cabeza"><p class="etiqueta">{e(t["aptos"]["etiqueta"])}</p><h2>{e(t["aptos"]["titulo"])}</h2><p class="entrada">{e(t["aptos"]["texto"])}</p></header>
<div class="aptos">{"".join(tarjeta_apto(idioma, raiz, a) for a in t["apto"])}</div>
</div>
</section>

<section class="seccion seccion-suave" id="equipamiento">
<div class="ancho">
<header class="seccion-cabeza"><p class="etiqueta">{e(t["ventajas"]["etiqueta"])}</p><h2>{e(t["ventajas"]["titulo"])}</h2><p class="entrada">{e(t["ventajas"]["texto"])}</p></header>
<ul class="ventajas">{ventajas}</ul>
</div>
</section>

<section class="seccion zarautz" id="zarautz">
<div class="ancho">
<header class="seccion-cabeza"><p class="etiqueta">{e(tz["etiqueta"])}</p><h2>{e(tz["titulo"])}</h2><p class="entrada">{e(tz["texto"])}</p></header>
<div class="mosaico">{mosaico}</div>
{creditos(idioma)}
</div>
</section>

<section class="seccion" id="ubicacion">
<div class="ancho dos">
<figure class="zona-foto">{img(raiz, foto(z["apto"], z["f"]), alt_foto(idioma, z["apto"], z["t"]), "(min-width: 900px) 520px, 100vw")}
<figcaption>{e(C["calle"])}, {e(C["localidad"])}</figcaption></figure>
<div><p class="etiqueta">{e(t["zona"]["etiqueta"])}</p><h2>{e(t["zona"]["titulo"])}</h2><p class="entrada">{e(t["zona"]["texto"])}</p>
{lista_zona(idioma)}
<p class="acciones"><a class="enlace-flecha" href="{e(C["mapa"])}" rel="noopener">{icono("mapa")}{e(t["zona"]["mapa"])}</a></p></div>
</div>
<div class="ancho">{mapa(idioma, raiz)}</div>
</section>

<section class="seccion seccion-suave" id="directo">
<div class="ancho">
<header class="seccion-cabeza"><p class="etiqueta">{e(t["directo"]["etiqueta"])}</p><h2>{e(t["directo"]["titulo"])}</h2><p class="entrada">{e(t["directo"]["texto"])}</p></header>
<ol class="directo">{directo}</ol>
<aside class="superhost"><p class="estrellas" aria-hidden="true">★★★★★</p><div><h3>{e(t["directo"]["superhost_titulo"])}</h3><p>{e(t["directo"]["superhost_texto"])}</p></div></aside>
</div>
</section>

<section class="seccion" id="condiciones">
<div class="ancho">
<header class="seccion-cabeza"><p class="etiqueta">{e(t["condiciones"]["etiqueta"])}</p><h2>{e(t["condiciones"]["titulo"])}</h2><p class="entrada">{e(t["condiciones"]["texto"])}</p></header>
{lista_condiciones(idioma)}
</div>
</section>

{bloque_contacto(idioma)}'''


def ficha(idioma, raiz, a):
    t = TXT[idioma]
    tf = t["ficha"]
    cfg = APTOS[a["clave"]]
    total = len(cfg["fotos"])
    fotos = []
    for n, f in enumerate(cfg["fotos"]):
        datos = foto(a["clave"], f["f"])
        alt = alt_foto(idioma, a["clave"], f["t"])
        fotos.append(
            f'<a class="galeria-foto" href="{raiz}fotos/{datos["base"]}-{datos["anchos"][-1]}.webp" data-foto '
            f'data-titulo="{e(alt)}">'
            f'{img(raiz, datos, alt, "(min-width: 900px) 50vw, 100vw" if n == 0 else "(min-width: 900px) 25vw, 50vw", prioritaria=n == 0)}</a>')
    datos_apto = [tf["m2"].format(n=cfg["m2"]), t["aptos"]["huespedes"], t["aptos"]["camas"],
                  t["aptos"]["bano"], t["aptos"]["planta"]]
    otro = next(x for x in t["apto"] if x["clave"] != a["clave"])
    equip = "".join(f'<li>{icono("check")}{e(x)}</li>' for x in tf["lista"])
    return f'''<article class="ficha">
<div class="ancho">
<header class="ficha-cabeza">
<p class="etiqueta">{e(t["portada"]["etiqueta"])}</p>
<h1>{e(a["corto"])} <span>{e(a["lema"])}</span></h1>
<ul class="datos">{"".join(f"<li>{e(d)}</li>" for d in datos_apto)}</ul>
</header>
<div class="galeria" data-galeria data-cerrar="{e(tf["cerrar"])}" data-anterior="{e(tf["anterior"])}" data-siguiente="{e(tf["siguiente"])}" data-cuenta="{e(tf["foto"])}">
{"".join(fotos)}
<button class="galeria-todas" type="button" data-todas>{e(tf["fotos"].format(n=total))}</button>
</div>
<div class="ficha-fila">
<div class="ficha-texto">
<p class="entrada">{e(a["intro"])}</p>
<h2>{e(a["destacado_titulo"])}</h2><p>{e(a["destacado_texto"])}</p>
<h2>{e(tf["espacio"])}</h2><p>{e(a["espacio"])}</p>
<h2>{e(tf["equipamiento"])}</h2><ul class="equipamiento">{equip}</ul>
<h2>{e(tf["barrio"])}</h2><p>{e(t["zona"]["texto"])}</p>
{lista_zona(idioma)}
<p class="acciones"><a class="enlace-flecha" href="{e(C["mapa"])}" rel="noopener">{icono("mapa")}{e(t["zona"]["mapa"])}</a></p>
<h2>{e(t["condiciones"]["titulo"])}</h2>
{lista_condiciones(idioma)}
</div>
<aside class="ficha-lado">{formulario(idioma, raiz, a["clave"])}</aside>
</div>
</div>
</article>

<section class="seccion seccion-suave">
<div class="ancho">
<header class="seccion-cabeza"><h2>{e(tf["otro"])}</h2></header>
<div class="aptos aptos-uno">{tarjeta_apto(idioma, raiz, otro)}</div>
</div>
</section>

{bloque_contacto(idioma)}'''


def legal(idioma, clave):
    cuerpo = (AQUI / "legales" / f"{clave}_{idioma}.html").read_text(encoding="utf-8")
    return f'<article class="ancho legal">{cuerpo}</article>'


def redireccion(idioma, destino):
    return f'''<!doctype html>
<html lang="{idioma}"><head><meta charset="utf-8"><title>Logoxo</title>
<meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url={destino}">
<link rel="canonical" href="{destino}"></head>
<body><p>{e(TXT[idioma]["pie"]["redireccion"])} <a href="{destino}">{destino}</a></p></body></html>
'''


def escribir(rel, contenido):
    destino = SALIDA / rel / "index.html" if not rel.endswith((".xml", ".txt", ".html")) else SALIDA / rel
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(contenido, encoding="utf-8")


def generar():
    SALIDA.mkdir(exist_ok=True)
    for viejo in SALIDA.iterdir():           # las fotos se conservan: tardan en hacerse
        if viejo.name != "fotos":
            shutil.rmtree(viejo) if viejo.is_dir() else viejo.unlink()
    shutil.copytree(AQUI / "estatico", SALIDA / "estatico")

    dominio = CFG["sitio"]["dominio"].rstrip("/")
    urls = []
    paginas = ["inicio", *APTOS, *(l["clave"] for l in TXT[IDIOMAS[0]]["legal"])]
    for pag in paginas:
        alternos = {i: ruta(i, pag) for i in IDIOMAS}
        for idioma in IDIOMAS:
            t = TXT[idioma]
            raiz = "../" * alternos[idioma].count("/")
            extra = {}
            if pag == "inicio":
                titulo, desc, cuerpo = t["meta"]["titulo"], t["meta"]["descripcion"], inicio(idioma, raiz)
                extra = {"imagen": foto_zarautz(CFG["portada"]["fondo"]), "datos": datos_estructurados(idioma)}
            elif pag in APTOS:
                a = next(x for x in t["apto"] if x["clave"] == pag)
                titulo, desc, cuerpo = f'{a["titulo_seo"]} | Logoxo', a["descripcion_seo"], ficha(idioma, raiz, a)
                extra = {"imagen": foto(pag, APTOS[pag]["fotos"][0]["f"])}
            else:
                l = next(x for x in t["legal"] if x["clave"] == pag)
                titulo, desc, cuerpo = f'{l["titulo"]} | Logoxo', l["titulo"], legal(idioma, pag)
            escribir(alternos[idioma], pagina(idioma, pag, titulo, desc, cuerpo, raiz=raiz, alternos=alternos, **extra))
            urls.append(f"{dominio}/{alternos[idioma]}")

    # La raíz del dominio muestra la portada del primer idioma (canonical a /es/).
    primero = IDIOMAS[0]
    escribir("index.html", pagina(primero, "inicio", TXT[primero]["meta"]["titulo"], TXT[primero]["meta"]["descripcion"],
                                  inicio(primero, ""), raiz="", alternos={i: ruta(i) for i in IDIOMAS},
                                  imagen=foto_zarautz(CFG["portada"]["fondo"]), datos=datos_estructurados(primero)))

    for origen, destino in CFG.get("redirecciones", {}).items():
        escribir(origen, redireccion(origen.split("/")[0], "../" * (origen.count("/") + 1) + destino))

    escribir("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
             + "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    escribir("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {dominio}/sitemap.xml\n")
    (SALIDA / ".nojekyll").write_text("")   # GitHub Pages: servir tal cual
    print(f"{len(urls) + 1} páginas en {SALIDA}")


def servir(puerto, red=False):
    manejador = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SALIDA))
    print(f"http://localhost:{puerto}/  (Ctrl+C para parar)")
    http.server.ThreadingHTTPServer(("0.0.0.0" if red else "127.0.0.1", puerto), manejador).serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--servir", action="store_true", help="tras generar, servir publico/ en local")
    ap.add_argument("--puerto", type=int, default=8000)
    ap.add_argument("--red", action="store_true", help="servir también al resto de la red local (para verla en el móvil)")
    args = ap.parse_args()
    generar()
    if args.servir:
        servir(args.puerto, args.red)
