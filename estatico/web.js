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

  // Calendario de rango, como el de un buscador de alojamientos: un solo
  // desplegable con dos meses donde se marca la llegada y luego la salida.
  // Pinta en gris los días en que no queda ningún apartamento libre y respeta
  // la estancia mínima. Sustituye a los dos campos de fecha del navegador, que
  // se quedan ocultos y siguen llevando el valor.
  const montarCalendario = (form, datos, llegada, salida) => {
    const tx = datos.textos;
    const hoy = iso(new Date());
    const dia = (texto) => new Date(`${texto}T12:00:00`);
    const fmtCampo = new Intl.DateTimeFormat(datos.idioma, { weekday: "short", day: "numeric", month: "short" });
    const fmtMes = new Intl.DateTimeFormat(datos.idioma, { month: "long", year: "numeric" });
    const fmtSemana = new Intl.DateTimeFormat(datos.idioma, { weekday: "short" });
    const fmtDia = new Intl.DateTimeFormat(datos.idioma, { weekday: "long", day: "numeric", month: "long" });

    // Ocupación: fecha → { libre, min } sumando los apartamentos.
    const ocupacion = new Map();
    let cargadoHasta = null;   // último día del que hay datos
    let cargando = false;
    let sinDatos = !datos.calendario || !window.fetch;
    const cargar = async (desde) => {
      if (sinDatos || cargando) return;
      cargando = true;
      try {
        const respuestas = await Promise.all(datos.aptos.map((a) =>
          fetch(datos.calendario.replace("{id}", a.id).replace("{fecha}", desde), { credentials: "omit", headers: { Accept: "application/json" } })
            .then((r) => { if (!r.ok) throw new Error("calendario"); return r.json(); })));
        let ultimo = desde;
        for (const r of respuestas) {
          for (const d of r.calendar) {
            const e = ocupacion.get(d.date) || { libre: false, min: Infinity };
            if (d.isAvailable) { e.libre = true; e.min = Math.min(e.min, d.minimalStay || 1); }
            ocupacion.set(d.date, e);
            if (d.date > ultimo) ultimo = d.date;
          }
        }
        cargadoHasta = ultimo;
      } catch (error) {
        sinDatos = true;   // sin ocupación: se deja elegir cualquier día futuro
        ocupacion.clear();
      }
      cargando = false;
      pintar();
    };
    const ocupado = (f) => { const e = ocupacion.get(f); return !!e && !e.libre; };

    // El control que se ve: «Llegada | Salida» en una sola caja.
    const control = crear("div", "fechas");
    const bLlegada = crear("button", "fechas-campo");
    const bSalida = crear("button", "fechas-campo");
    bLlegada.type = bSalida.type = "button";
    control.append(bLlegada, bSalida);
    const panel = crear("div", "calendario");
    panel.hidden = true;
    panel.setAttribute("role", "dialog");
    for (const etiqueta of form.querySelectorAll("[data-fecha]")) etiqueta.hidden = true;
    llegada.required = salida.required = false;
    form.querySelector(".reserva-campos").prepend(control);
    control.after(panel);

    let mes = dia(hoy); mes.setDate(1);
    let pasando = null;        // día bajo el ratón mientras se elige la salida
    const eligiendoSalida = () => llegada.value && !salida.value;
    const minimo = () => { const e = ocupacion.get(llegada.value); return e && Number.isFinite(e.min) ? e.min : 1; };
    // Primer día sin ningún apartamento libre a partir de la llegada: se puede
    // salir ese día, pero no más tarde.
    const tope = () => {
      let f = llegada.value;
      for (let i = 0; i < 400; i++) { if (ocupado(f)) return f; f = sumar(f, 1); }
      return null;
    };

    const campo = (boton, rotulo, valor, activo) => {
      boton.replaceChildren(crear("span", "fechas-rotulo", rotulo), crear("span", valor ? "fechas-valor" : "fechas-valor vacio", valor ? fmtCampo.format(dia(valor)) : "—"));
      boton.classList.toggle("activo", activo);
    };

    const pintar = () => {
      campo(bLlegada, tx.llegada, llegada.value, !panel.hidden && !eligiendoSalida());
      campo(bSalida, tx.salida, salida.value, !panel.hidden && eligiendoSalida());
      if (panel.hidden) return;
      const dosMeses = form.clientWidth >= 620;
      panel.classList.toggle("calendario-doble", dosMeses);
      const cabeza = crear("div", "calendario-cabeza");
      const atras = crear("button", "calendario-flecha", "←");
      const adelante = crear("button", "calendario-flecha", "→");
      atras.type = adelante.type = "button";
      atras.setAttribute("aria-label", tx.mes_anterior);
      adelante.setAttribute("aria-label", tx.mes_siguiente);
      atras.disabled = iso(mes) <= hoy;
      const limite = dia(hoy); limite.setMonth(limite.getMonth() + 18);
      adelante.disabled = mes >= limite;
      atras.addEventListener("click", () => { mes.setMonth(mes.getMonth() - 1); pintar(); });
      adelante.addEventListener("click", () => { mes.setMonth(mes.getMonth() + 1); pintar(); });
      cabeza.append(atras, crear("p", "calendario-guia", eligiendoSalida() ? tx.elegir_salida : tx.elegir_llegada), adelante);

      const meses = crear("div", "calendario-meses");
      const min = eligiendoSalida() ? minimo() : 1;
      const fin = eligiendoSalida() ? tope() : null;
      let ultimoVisible = hoy;
      for (let m = 0; m < (dosMeses ? 2 : 1); m++) {
        const primero = new Date(mes); primero.setMonth(mes.getMonth() + m);
        const caja = crear("div", "calendario-mes");
        caja.append(crear("p", "calendario-titulo", fmtMes.format(primero)));
        const rejilla = crear("div", "calendario-dias");
        for (let d = 0; d < 7; d++) rejilla.append(crear("span", "calendario-semana", fmtSemana.format(new Date(2024, 0, 1 + d))));   // 1/1/2024 fue lunes
        const hueco = (primero.getDay() + 6) % 7;
        for (let h = 0; h < hueco; h++) rejilla.append(crear("span"));
        const dias = new Date(primero.getFullYear(), primero.getMonth() + 1, 0).getDate();
        for (let n = 1; n <= dias; n++) {
          const f = iso(new Date(primero.getFullYear(), primero.getMonth(), n, 12));
          ultimoVisible = f;
          const b = crear("button", "calendario-dia", n);
          b.type = "button";
          b.dataset.fecha = f;
          let libre = f >= hoy;
          let lleno = false;
          if (eligiendoSalida() && f > llegada.value) {
            // Como salida: respeta el mínimo y no salta por encima de una noche sin sitio.
            if (f < sumar(llegada.value, min) || (fin && f > fin)) libre = false;
          } else if (ocupado(f)) { libre = false; lleno = true; }
          b.disabled = !libre;
          if (lleno && f >= hoy) b.classList.add("lleno");
          b.setAttribute("aria-label", fmtDia.format(dia(f)) + (lleno ? `, ${tx.ocupado_dia}` : ""));
          const hasta = salida.value || (eligiendoSalida() && pasando && pasando > llegada.value ? pasando : "");
          if (f === llegada.value) b.classList.add("extremo", "inicio");
          if (f === hasta && hasta) b.classList.add("extremo", "final");
          if (llegada.value && hasta && f > llegada.value && f < hasta) b.classList.add("dentro");
          if (f === hoy) b.classList.add("hoy");
          rejilla.append(b);
        }
        caja.append(rejilla);
        meses.append(caja);
      }
      const pie = crear("div", "calendario-pie");
      pie.append(crear("span", "calendario-aviso", eligiendoSalida() && min > 1 ? tx.min_noches.replace("{n}", min) : ""));
      const borrar = crear("button", "calendario-borrar", tx.borrar);
      borrar.type = "button";
      borrar.hidden = !llegada.value;
      borrar.addEventListener("click", () => { llegada.value = salida.value = ""; pasando = null; avisar(); pintar(); });
      pie.append(borrar);
      panel.replaceChildren(cabeza, meses, pie);
      if (!sinDatos && (!cargadoHasta || ultimoVisible > cargadoHasta)) cargar(cargadoHasta ? sumar(cargadoHasta, 1) : hoy);
    };

    const avisar = () => form.dispatchEvent(new Event("input", { bubbles: true }));
    const abrir = () => {
      if (!panel.hidden) return;
      panel.hidden = false;
      if (llegada.value) { mes = dia(llegada.value); mes.setDate(1); }
      pintar();
    };
    const cerrar = () => { if (panel.hidden) return; panel.hidden = true; pasando = null; pintar(); };

    panel.addEventListener("click", (ev) => {
      const b = ev.target.closest(".calendario-dia");
      if (!b || b.disabled) return;
      const f = b.dataset.fecha;
      if (eligiendoSalida() && f > llegada.value) {
        salida.value = f;
        avisar();
        cerrar();
        form.querySelector("button[type=submit]").focus();
        return;
      }
      llegada.value = f;       // primera pulsación, o volver a empezar
      salida.value = "";
      pasando = null;
      avisar();
      pintar();
    });
    panel.addEventListener("mouseover", (ev) => {
      const b = ev.target.closest(".calendario-dia");
      if (!b || b.disabled || !eligiendoSalida() || pasando === b.dataset.fecha) return;
      pasando = b.dataset.fecha;
      for (const d of panel.querySelectorAll(".calendario-dia")) {
        const f = d.dataset.fecha;
        d.classList.toggle("dentro", f > llegada.value && f < pasando);
        d.classList.toggle("final", f === pasando && pasando > llegada.value);
        d.classList.toggle("extremo", f === llegada.value || (f === pasando && pasando > llegada.value));
      }
    });
    bLlegada.addEventListener("click", () => { if (!panel.hidden && !eligiendoSalida()) return cerrar(); salida.value = ""; llegada.value = ""; avisar(); panel.hidden ? abrir() : pintar(); });
    bSalida.addEventListener("click", () => { if (!panel.hidden && eligiendoSalida()) return cerrar(); if (llegada.value) salida.value = ""; avisar(); panel.hidden ? abrir() : pintar(); });
    document.addEventListener("click", (ev) => { if (!control.contains(ev.target) && !panel.contains(ev.target) && ev.target.isConnected) cerrar(); });
    form.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !panel.hidden) { cerrar(); bLlegada.focus(); } });
    pintar();
    return { abrir };
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
    let turno = 0;
    const calendario = montarCalendario(form, datos, llegada, salida);
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
      if (!llegada.value || !salida.value) { ev.preventDefault(); calendario.abrir(); return; }
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
