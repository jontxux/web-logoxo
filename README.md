# web-logoxo

Web propia de los apartamentos Logoxo: estática, en castellano, euskera e
inglés, sin las plantillas de Lodgify. La reserva y el pago siguen en la
pasarela de Lodgify: el formulario de fechas manda allí con el apartamento,
las fechas y los huéspedes ya puestos.

El buscador de fechas pregunta a la consulta pública de Lodgify
(`busqueda` en `[reserva]`) qué apartamentos están libres y enseña los dos
con su precio; si la consulta falla, enlaza a la pasarela sin más.

Está en pruebas en https://jontxux.github.io/web-logoxo/ (GitHub Pages, rama
`gh-pages`), con `indexar = false` para que no la recojan los buscadores.
logoxoat.com sigue siendo la web de Lodgify.

## Uso

    python3 generar.py            # genera publico/
    python3 generar.py --servir   # y la sirve en http://localhost:8000
    ./publicar.sh                 # genera y sube publico/ a GitHub Pages

Solo necesita Python 3.11+ y ImageMagick (`magick`). La primera vez tarda
unos 20 s porque reduce las fotos; luego las reutiliza.

## Qué hay

- `config.toml`: dominio, contacto, motor de reservas, fotos de cada
  apartamento y su orden, redirecciones de las direcciones antiguas.
- `textos/<idioma>.toml`: todos los textos. Los de la web de Lodgify se han
  copiado tal cual; los nuevos (formulario, condiciones, equipamiento) están
  escritos para esta web.
- `legales/`: aviso legal y privacidad (copia de
  `~/Documentos/Papeles/Apartamentos/Web_logoxoat/2026/`) y una política de
  cookies nueva, porque esta web no pone cookies.
- `fotos-zarautz/`: las fotos de Zarautz. Cinco son de Wikimedia Commons, con
  licencia CC BY o CC BY-SA: su autor, licencia y origen están en
  `[zarautz.fotos]` de `config.toml` y salen solos en los créditos de la
  portada, que no se pueden quitar. `atardecer.jpg` es de Jon.
- `estatico/mapa.webp`: recorte de OpenStreetMap (zoom 16); la marca de la casa
  se coloca con `[mapa]` de `config.toml`. Lleva su «© OpenStreetMap».
- `estatico/`: estilos, JavaScript, logo y la tipografía Fraunces (OFL),
  servida desde aquí: la página no pide nada a otros servidores.
- `generar.py`: el generador. `publico/` es su salida y no va al git.

Las direcciones son las mismas que en Lodgify (`/es/logoxo-1-loft-...`,
`/es/aviso-legal`...), para que no se rompan los enlaces ni lo indexado si
algún día el dominio apunta aquí.

## Cambiar de motor de reservas

Todo está en `[reserva]` de `config.toml`: la URL de la pasarela y los
nombres de los parámetros. El `id` de cada `[[apartamento]]` es el de ese
motor.

## Antes de publicarla

- La pasarela de Lodgify ya va en verde (colores del tema publicados el
  15/11/2026). El día del cambio: `indexar = true` y un fichero `CNAME` con el
  dominio en la rama `gh-pages` (o el dominio propio en los ajustes de Pages).
- El DNS de logoxoat.com lo lleva Lodgify (los registros los añaden ellos a
  mano): para apuntar el dominio aquí hay que pedírselo a su soporte.

- Repasar la política de privacidad: habla del formulario de contacto, de
  reCAPTCHA y de Chekin, que aquí no existen.
- El aviso de la tasa turística, cuando la ordenanza sea definitiva.
- Decidir dónde se aloja y probarla antes en un subdominio.
