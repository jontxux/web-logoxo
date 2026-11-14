// Logoxo — lo justo de JavaScript: menú del móvil, fechas de la reserva y
// visor de fotos. Sin él la web sigue funcionando (el formulario envía igual
// y las fotos se abren como enlaces).
(() => {
  "use strict";

  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const sumar = (texto, dias) => { const d = new Date(`${texto}T12:00:00`); d.setDate(d.getDate() + dias); return iso(d); };

  // Menú del móvil
  const boton = document.querySelector("[data-menu]");
  const menu = document.getElementById("menu");
  if (boton && menu) {
    const cerrar = () => { menu.classList.remove("abierto"); boton.setAttribute("aria-expanded", "false"); };
    boton.addEventListener("click", () => {
      const abierto = menu.classList.toggle("abierto");
      boton.setAttribute("aria-expanded", String(abierto));
    });
    menu.addEventListener("click", (ev) => { if (ev.target.closest("a")) cerrar(); });
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") cerrar(); });
  }

  // Formularios de fechas: consultan qué apartamentos están libres y enseñan
  // los dos con su precio. Si la consulta falla, se enseñan igualmente con un
  // enlace a la pasarela, que es donde se ve la disponibilidad.
  const crear = (etiqueta, clase, texto) => {
    const el = document.createElement(etiqueta);
    if (clase) el.className = clase;
    if (texto != null) el.textContent = texto;
    return el;
  };

  for (const form of document.querySelectorAll("[data-reserva]")) {
    const llegada = form.querySelector("[data-llegada]");
    const salida = form.querySelector("[data-salida]");
    const huespedes = form.querySelector("[data-huespedes]");
    const nota = form.querySelector("[data-nota]");
    const caja = form.querySelector("[data-resultados]");
    const boton = form.querySelector("button[type=submit]");
    const datos = JSON.parse(form.dataset.datos);
    const tx = datos.textos;
    const textoNota = nota.textContent;
    const hoy = iso(new Date());
    let turno = 0;
    llegada.min = hoy;
    salida.min = sumar(hoy, 1);
    llegada.addEventListener("change", () => {
      if (!llegada.value) return;
      salida.min = sumar(llegada.value, 1);
      if (!salida.value || salida.value <= llegada.value) salida.value = sumar(llegada.value, 2);
    });
    form.addEventListener("input", () => { nota.textContent = textoNota; nota.classList.remove("error"); });

    const enlace = (apto) => {
      const p = new URLSearchParams();
      for (const [clave, valor] of Object.entries(datos.parametros)) {
        if (clave === "llegada") p.set(valor, llegada.value);
        else if (clave === "salida") p.set(valor, salida.value);
        else if (clave === "adultos") p.set(valor, huespedes.value);
        else p.set(clave, valor);
      }
      return `${apto.reserva}?${p}`;
    };
    const dinero = (n) => new Intl.NumberFormat(datos.idioma, {
      style: "currency", currency: "EUR", maximumFractionDigits: Number.isInteger(n) ? 0 : 2,
    }).format(n);

    // libres: Map de id → precio total; null si no se ha podido consultar.
    const pintar = (libres, noches) => {
      caja.replaceChildren();
      caja.hidden = false;
      const cabeza = crear("p", "resultados-cabeza");
      const fechas = new Intl.DateTimeFormat(datos.idioma, { day: "numeric", month: "short" });
      cabeza.textContent = `${fechas.format(new Date(`${llegada.value}T12:00`))} – ${fechas.format(new Date(`${salida.value}T12:00`))} · ${noches === 1 ? tx.noche : tx.noches.replace("{n}", noches)}`;
      caja.append(cabeza);
      if (libres === null) caja.append(crear("p", "resultados-aviso", tx.fallo));
      else if (libres.size === 0) caja.append(crear("p", "resultados-aviso", tx.ninguno));
      const lista = crear("ul", "resultados-lista");
      const orden = [...datos.aptos].sort((a, b) => (libres ? libres.has(b.id) - libres.has(a.id) : 0));
      for (const apto of orden) {
        const libre = libres === null ? null : libres.has(apto.id);
        const li = crear("li", `resultado${libre === false ? " resultado-ocupado" : ""}`);
        const img = crear("img");
        img.src = apto.foto; img.alt = ""; img.width = 640; img.height = 480; img.loading = "lazy";
        const cuerpo = crear("div", "resultado-cuerpo");
        cuerpo.append(crear("strong", "resultado-nombre", apto.nombre), crear("span", "resultado-lema", apto.lema));
        const estado = crear("div", "resultado-estado");
        if (libre) {
          const precio = libres.get(apto.id);
          estado.append(crear("span", "resultado-libre", tx.libre));
          if (precio > 0) {
            estado.append(crear("strong", "resultado-precio", tx.total.replace("{precio}", dinero(precio))));
            if (noches > 1) estado.append(crear("span", "resultado-noche", tx.por_noche.replace("{precio}", dinero(Math.round(precio / noches)))));
          }
        } else if (libre === false) {
          estado.append(crear("span", "resultado-no", tx.ocupado));
        }
        const acciones = crear("div", "resultado-acciones");
        if (libre !== false) {
          const a = crear("a", "boton", libre ? tx.elegir : tx.ver_precio);
          a.href = enlace(apto);
          acciones.append(a);
        }
        const ficha = crear("a", "resultado-ficha", tx.ver);
        ficha.href = apto.ficha;
        acciones.append(ficha);
        li.append(img, cuerpo, estado, acciones);
        lista.append(li);
      }
      caja.append(lista);
      caja.scrollIntoView({ block: "nearest", behavior: "smooth" });
    };

    form.addEventListener("submit", async (ev) => {
      if (!llegada.value || !salida.value) return;
      if (salida.value <= llegada.value) {
        ev.preventDefault();
        nota.textContent = form.dataset.error;
        nota.classList.add("error");
        salida.focus();
        return;
      }
      if (!datos.busqueda || !window.fetch) return;   // sin buscador: directo a la pasarela
      ev.preventDefault();
      const mio = ++turno;
      const noches = Math.round((new Date(`${salida.value}T12:00`) - new Date(`${llegada.value}T12:00`)) / 864e5);
      boton.disabled = true;
      nota.textContent = tx.buscando;
      let libres = null;
      try {
        const control = new AbortController();
        const reloj = setTimeout(() => control.abort(), 12000);
        const r = await fetch(datos.busqueda, {
          method: "POST", credentials: "omit", signal: control.signal,
          headers: { "Content-Type": "application/json", Accept: "application/json", "Accept-Language": datos.idioma },
          body: JSON.stringify({ people: Number(huespedes.value), start: llegada.value, end: salida.value }),
        });
        clearTimeout(reloj);
        const json = await r.json();
        if (!r.ok || !json.success) throw new Error("respuesta");
        libres = new Map(json.data.items.map((i) => [i.property_id, i.min_price]));
      } catch (error) {
        libres = null;
      }
      if (mio !== turno) return;
      boton.disabled = false;
      nota.textContent = textoNota;
      pintar(libres, noches);
    });
  }

  // Carruseles de las tarjetas: las flechas mueven una foto; con el dedo va solo.
  for (const carrusel of document.querySelectorAll("[data-carrusel]")) {
    const pista = carrusel.querySelector(".carrusel-fotos");
    const flechas = [...carrusel.querySelectorAll("[data-paso]")];
    const poner = () => {
      const fin = pista.scrollWidth - pista.clientWidth - 2;
      flechas[0].disabled = pista.scrollLeft <= 2;
      flechas[1].disabled = pista.scrollLeft >= fin;
    };
    for (const f of flechas) {
      f.hidden = false;
      f.addEventListener("click", () => pista.scrollBy({ left: Number(f.dataset.paso) * pista.clientWidth, behavior: "smooth" }));
    }
    pista.addEventListener("scroll", poner, { passive: true });
    poner();
  }

  // Visor de fotos
  const galeria = document.querySelector("[data-galeria]");
  if (galeria && typeof HTMLDialogElement !== "undefined") {
    const fotos = [...galeria.querySelectorAll("[data-foto]")];
    const d = galeria.dataset;
    const visor = document.createElement("dialog");
    visor.className = "visor";
    visor.innerHTML = `<div class="visor-caja">
<div class="visor-barra"><span data-cuenta></span><button type="button" data-cerrar>${d.cerrar}</button></div>
<div class="visor-foto"><img alt=""></div>
<p class="visor-pie"></p>
<button type="button" class="visor-flecha" data-paso="-1" aria-label="${d.anterior}">←</button>
<button type="button" class="visor-flecha" data-paso="1" aria-label="${d.siguiente}">→</button></div>`;
    document.body.append(visor);
    const imagen = visor.querySelector("img");
    const pie = visor.querySelector(".visor-pie");
    const cuenta = visor.querySelector("[data-cuenta]");
    let actual = 0;
    const mostrar = (n) => {
      actual = (n + fotos.length) % fotos.length;
      const f = fotos[actual];
      imagen.src = f.href;
      imagen.alt = f.dataset.titulo;
      pie.textContent = f.dataset.titulo;
      cuenta.textContent = d.cuenta.replace("{n}", actual + 1).replace("{total}", fotos.length);
    };
    const abrir = (n) => { mostrar(n); visor.showModal(); };
    fotos.forEach((f, n) => f.addEventListener("click", (ev) => { ev.preventDefault(); abrir(n); }));
    galeria.querySelector("[data-todas]").addEventListener("click", () => abrir(0));
    visor.addEventListener("click", (ev) => {
      const paso = ev.target.closest("[data-paso]");
      if (paso) mostrar(actual + Number(paso.dataset.paso));
      else if (ev.target.closest("[data-cerrar]") || ev.target === visor || ev.target.classList.contains("visor-foto")) visor.close();
    });
    visor.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowLeft") mostrar(actual - 1);
      if (ev.key === "ArrowRight") mostrar(actual + 1);
    });
    let inicioX = null;
    visor.addEventListener("touchstart", (ev) => { inicioX = ev.touches[0].clientX; }, { passive: true });
    visor.addEventListener("touchend", (ev) => {
      if (inicioX === null) return;
      const dx = ev.changedTouches[0].clientX - inicioX;
      if (Math.abs(dx) > 50) mostrar(actual + (dx < 0 ? 1 : -1));
      inicioX = null;
    }, { passive: true });
  } else if (galeria) {
    galeria.querySelector("[data-todas]").hidden = true;
  }

  const anio = document.querySelector("[data-anio]");
  if (anio) anio.textContent = new Date().getFullYear();
})();
