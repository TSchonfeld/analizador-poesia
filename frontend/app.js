"use strict";

(() => {
  const $ = (sel, raiz = document) => raiz.querySelector(sel);
  const $$ = (sel, raiz = document) => Array.from(raiz.querySelectorAll(sel));

  const CATEGORIAS = ["fónicos", "semánticos", "léxicos", "gramaticales", "sintácticos"];
  const VAR_CATEGORIA = {
    "fónicos": "--c-fonicos",
    "semánticos": "--c-semanticos",
    "léxicos": "--c-lexicos",
    "gramaticales": "--c-gramaticales",
    "sintácticos": "--c-sintacticos",
  };
  const TITULOS = {
    metrica: "A. Métrica",
    versificacion: "B. Versificación",
    recursos: "C. Recursos poéticos",
    temas: "D. Temas centrales",
    interpretacion: "E. Posibles líneas de lectura e interpretación",
  };

  let ultimo = null; // último resultado del análisis
  let filtros = new Set(CATEGORIAS);

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  /* ---------- Tema ---------- */
  const raiz = document.documentElement;
  const temas = ["sistema", "claro", "oscuro"];
  const etiquetasTema = { sistema: "Tema del sistema", claro: "Modo claro", oscuro: "Modo oscuro" };
  function leerTema() {
    try { return localStorage.getItem("tema") || "sistema"; } catch (e) { return "sistema"; }
  }
  function aplicarTema(t) {
    if (t === "claro") raiz.dataset.theme = "light";
    else if (t === "oscuro") raiz.dataset.theme = "dark";
    else delete raiz.dataset.theme;
    $("#tema-texto").textContent = etiquetasTema[t];
    $("#tema-icono").textContent = t === "claro" ? "☀" : t === "oscuro" ? "☾" : "◐";
    try { localStorage.setItem("tema", t); } catch (e) {}
  }
  $("#tema").addEventListener("click", () => {
    const actual = leerTema();
    aplicarTema(temas[(temas.indexOf(actual) + 1) % temas.length]);
  });
  aplicarTema(leerTema());

  /* ---------- Ejemplos ---------- */
  $$("[data-ejemplo]").forEach((b) =>
    b.addEventListener("click", () => {
      $("#poema").value = window.EJEMPLOS[b.dataset.ejemplo] || "";
      $("#poema").focus();
    })
  );

  /* ---------- Pestañas ---------- */
  const pestanas = $$('[role="tab"]');
  function activarPestana(tab, enfocar = false) {
    pestanas.forEach((t) => {
      const activa = t === tab;
      t.setAttribute("aria-selected", String(activa));
      t.tabIndex = activa ? 0 : -1;
      $("#" + t.getAttribute("aria-controls")).hidden = !activa;
    });
    if (enfocar) tab.focus();
  }
  pestanas.forEach((t, i) => {
    t.addEventListener("click", () => activarPestana(t));
    t.addEventListener("keydown", (e) => {
      let j = null;
      if (e.key === "ArrowRight") j = (i + 1) % pestanas.length;
      if (e.key === "ArrowLeft") j = (i - 1 + pestanas.length) % pestanas.length;
      if (e.key === "Home") j = 0;
      if (e.key === "End") j = pestanas.length - 1;
      if (j !== null) { e.preventDefault(); activarPestana(pestanas[j], true); }
    });
  });

  /* ---------- Análisis ---------- */
  const estado = $("#estado");
  function mostrarEstado(texto, error = false) {
    estado.textContent = texto;
    estado.classList.toggle("estado--error", error);
  }

  async function analizar() {
    const texto = $("#poema").value.trim();
    if (!texto) { mostrarEstado("Pegá un poema para analizar.", true); return; }
    const boton = $("#analizar");
    boton.disabled = true;
    const interpretar = $("#interpretar").checked;
    mostrarEstado(interpretar ? "Analizando la métrica y consultando el análisis interpretativo…" : "Analizando la métrica…");
    try {
      const r = await fetch("/api/analizar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto, interpretar }),
      });
      const datos = await r.json().catch(() => ({}));
      if (!r.ok) {
        const detalle = typeof datos.detail === "string" ? datos.detail : "No se pudo analizar el poema.";
        throw new Error(detalle);
      }
      ultimo = datos;
      filtros = new Set(CATEGORIAS);
      renderizar(datos);
      mostrarEstado("");
      $("#resultados").hidden = false;
      activarPestana(pestanas[0]);
      $("#resultados").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      mostrarEstado(e.message || "Error de conexión con el servidor.", true);
    } finally {
      boton.disabled = false;
    }
  }
  $("#analizar").addEventListener("click", analizar);
  $("#poema").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) analizar();
  });

  function renderizar(d) {
    const avisos = $("#avisos");
    avisos.hidden = !d.avisos.length;
    avisos.innerHTML = d.avisos.map((a) => `<p>${esc(a)}</p>`).join("");
    for (const [id, titulo] of Object.entries(TITULOS)) $("#panel-" + id).dataset.titulo = titulo;
    $("#panel-metrica").innerHTML = htmlMetrica(d);
    $("#panel-versificacion").innerHTML = htmlVersificacion(d);
    renderizarRecursos(d);
    $("#panel-temas").innerHTML = htmlTemas(d);
    $("#panel-interpretacion").innerHTML = htmlInterpretacion(d);
  }

  const badge = (c) => `<span class="confianza confianza--${esc(c)}" title="Nivel de confianza">${esc(c)}</span>`;
  const leyFinal = (v) => {
    const signo = v.ajuste_final > 0 ? "+" + v.ajuste_final : v.ajuste_final < 0 ? "−" + Math.abs(v.ajuste_final) : "0";
    return `${v.ley_acento_final} (${signo})`;
  };

  /* A. Métrica */
  function htmlMetrica(d) {
    const m = d.metrica;
    const metros = m.metros.map((n) => `${n}`).join(" y ");
    const dudosos = m.versos.filter((v) => v.confianza !== "alta").length;
    let html = `<div class="resumen">
      <div class="tarjeta"><h3>Versos</h3><p>${m.versos.length}</p></div>
      <div class="tarjeta"><h3>Metro${m.metros.length > 1 ? "s" : ""}</h3><p>${esc(metros)} sílabas</p>
        <p class="detalle">${m.isometrico ? "Poema isométrico" : "Poema heterométrico"}</p></div>
      <div class="tarjeta"><h3>Versos dudosos</h3><p>${dudosos}</p><p class="detalle">Con confianza media o baja</p></div>
    </div>
    <div class="tabla-envoltura"><table>
      <thead><tr><th>N.º</th><th>Verso</th><th>Silabeo</th><th>Licencias</th><th>Sílabas</th><th>Rima</th></tr></thead><tbody>`;
    let estrofaPrevia = null;
    for (const v of m.versos) {
      const lic = v.licencias.length
        ? `<div class="licencias">${v.licencias.map((l) => `<span class="lic lic--${esc(l.tipo)}" title="${esc(l.tipo)}">${esc(l.tipo)}: ${esc(l.texto)}</span>`).join("")}</div>`
        : `<span class="sub">—</span>`;
      const alt = v.alternativas.length
        ? `<details class="alternativas"><summary>${v.alternativas.length} lectura${v.alternativas.length > 1 ? "s" : ""} alternativa${v.alternativas.length > 1 ? "s" : ""}</summary><ul>${v.alternativas
            .map((a) => `<li>${esc(a.silabeo)} <strong>(${a.silabas})</strong>${a.licencias.filter((l) => l.tipo !== "sinalefa").map((l) => ` · ${esc(l.tipo)}`).join("")}</li>`)
            .join("")}</ul></details>`
        : "";
      const ritmo = v.ritmo ? `<span class="sub">${esc(v.ritmo)}</span>` : "";
      const clase = estrofaPrevia !== null && v.estrofa !== estrofaPrevia ? ' class="cambio-estrofa"' : "";
      estrofaPrevia = v.estrofa;
      html += `<tr${clase}>
        <td class="num">${v.numero}</td>
        <td class="verso">${esc(v.texto)}</td>
        <td class="silabeo">${esc(v.silabeo)}${alt}</td>
        <td>${lic}<span class="sub">Acento final: ${esc(leyFinal(v))}</span></td>
        <td class="silabas"><strong>${v.silabas}</strong> ${badge(v.confianza)}<span class="sub">${esc(v.nombre)}</span><span class="sub">${esc(v.arte)}</span>${ritmo}</td>
        <td class="rima"><span class="rima-letra">${esc(v.rima)}</span><span class="sub">${esc(v.terminacion || "")}</span></td>
      </tr>`;
    }
    html += `</tbody></table></div>
      <p class="nota">«‿» marca sinalefa, «‖» marca hiato y « / » la cesura de los versos compuestos. Las sílabas métricas incluyen la ley del acento final.</p>`;
    return html;
  }

  /* B. Versificación */
  function htmlVersificacion(d) {
    const v = d.versificacion;
    const c = v.composicion;
    const rimaTxt = { consonante: "Consonante", asonante: "Asonante", libre: "Libre (sin rima)" }[v.rima.tipo];
    let html = `<div class="tarjeta composicion">
        <h3>${esc(capitalizar(c.tipo))} ${badge(c.confianza)}</h3>
        <p>${esc(c.justificacion)}</p>
      </div>
      <div class="resumen">
        <div class="tarjeta"><h3>Rima</h3><p>${esc(rimaTxt)} ${badge(v.rima.confianza)}</p></div>
        <div class="tarjeta"><h3>Esquema</h3><p style="font-family:var(--fuente-mono);word-break:break-all">${esc(v.rima.esquema)}</p></div>
        <div class="tarjeta"><h3>Estrofas</h3><p>${v.estrofas.length}</p></div>
      </div>
      <div class="estrofas">`;
    for (const e of v.estrofas) {
      const rango = e.versos.length > 1 ? `versos ${e.versos[0]}–${e.versos[e.versos.length - 1]}` : `verso ${e.versos[0]}`;
      html += `<div class="tarjeta estrofa">
        <h3>${e.numero}. ${esc(capitalizar(e.tipo))} ${badge(e.confianza)}</h3>
        <p class="sub">${rango}</p>
        <p class="esquema">${esc(e.esquema)}</p>
      </div>`;
    }
    return html + `</div>`;
  }

  /* C. Recursos */
  function sinInterpretacion(d) {
    const motivo = d.avisos.length ? d.avisos[0] : "Activá «Recursos, temas e interpretación» y volvé a analizar.";
    return `<p class="vacio">${esc(motivo)}</p>`;
  }

  function regexCita(cita) {
    const palabras = cita.normalize("NFC").split(/[^\p{L}\p{N}]+/u).filter(Boolean);
    if (!palabras.length) return null;
    const escapar = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(palabras.map(escapar).join("[^\\p{L}\\p{N}]+"), "iu");
  }

  function rangosResaltado(versos, recursos) {
    // rangos[i] = lista de {ini, fin, id} sobre el texto del verso i
    const rangos = versos.map(() => []);
    recursos.forEach((r, id) => {
      if (!filtros.has(r.categoria)) return;
      const re = regexCita(r.cita);
      if (!re) return;
      const desde = r.verso - 1;
      const hasta = Math.min(r.hasta_verso - 1, versos.length - 1);
      const tramo = versos.slice(desde, hasta + 1);
      const unido = tramo.join("\n");
      const m = re.exec(unido);
      if (!m) return;
      let ini = m.index;
      let fin = m.index + m[0].length;
      let base = 0;
      tramo.forEach((linea, k) => {
        const a = Math.max(ini, base);
        const b = Math.min(fin, base + linea.length);
        if (a < b) rangos[desde + k].push({ ini: a - base, fin: b - base, id });
        base += linea.length + 1;
      });
    });
    return rangos;
  }

  function htmlLinea(texto, rangos, recursos) {
    if (!rangos.length) return esc(texto);
    const cortes = new Set([0, texto.length]);
    rangos.forEach((r) => { cortes.add(r.ini); cortes.add(r.fin); });
    const puntos = Array.from(cortes).sort((a, b) => a - b);
    let html = "";
    for (let k = 0; k < puntos.length - 1; k++) {
      const a = puntos[k], b = puntos[k + 1];
      const ids = rangos.filter((r) => r.ini <= a && r.fin >= b).map((r) => r.id);
      const trozo = esc(texto.slice(a, b));
      if (!ids.length) { html += trozo; continue; }
      const cats = ids.map((i) => recursos[i].categoria);
      const estilo = cats.length > 1 ? ` style="--marca-2: var(${VAR_CATEGORIA[cats[1]]})"` : "";
      const titulo = ids.map((i) => recursos[i].nombre).join(", ");
      html += `<mark class="cat-${esc(cats[0])}${cats.length > 1 ? " varios" : ""}" data-ids="${ids.join(" ")}" title="${esc(titulo)}"${estilo}>${trozo}</mark>`;
    }
    return html;
  }

  function renderizarRecursos(d) {
    const panel = $("#panel-recursos");
    const interp = d.interpretativo;
    if (!interp) { panel.innerHTML = sinInterpretacion(d); return; }
    const versos = d.metrica.versos;
    const textos = versos.map((v) => v.texto);
    const recursos = interp.recursos;
    const rangos = rangosResaltado(textos, recursos);

    let poema = "";
    let estrofa = null;
    versos.forEach((v, i) => {
      if (estrofa !== null && v.estrofa !== estrofa) poema += `<span class="separador-estrofa"></span>`;
      estrofa = v.estrofa;
      poema += `<span class="linea"><span class="linea-num">${v.numero}</span>${htmlLinea(v.texto, rangos[i], recursos)}</span>`;
    });

    const conteo = Object.fromEntries(CATEGORIAS.map((c) => [c, recursos.filter((r) => r.categoria === c).length]));
    const chips = CATEGORIAS.map((c) =>
      `<button type="button" class="boton boton--chip cat-${c}" data-filtro="${c}" aria-pressed="${filtros.has(c)}"><span class="punto"></span>${capitalizar(c)} (${conteo[c]})</button>`
    ).join("");

    let lista = "";
    CATEGORIAS.forEach((c) => {
      if (!filtros.has(c)) return;
      recursos.forEach((r, id) => {
        if (r.categoria !== c) return;
        const versosTxt = r.verso === r.hasta_verso ? `v. ${r.verso}` : `vv. ${r.verso}–${r.hasta_verso}`;
        lista += `<article class="tarjeta recurso cat-${esc(c)}" data-id="${id}" tabindex="0">
          <h4><span>${esc(capitalizar(r.nombre))}</span> ${badge(r.confianza)}</h4>
          <div class="meta">${esc(capitalizar(c))} · ${versosTxt}</div>
          <blockquote>«${esc(r.cita)}»</blockquote>
          <p>${esc(r.explicacion)}</p>
        </article>`;
      });
    });
    if (!recursos.length) lista = `<p class="vacio">No se detectaron recursos con evidencia textual suficiente.</p>`;
    else if (!lista) lista = `<p class="vacio">Ninguna categoría seleccionada.</p>`;

    const descartados = interp.recursos_descartados.length
      ? `<p class="nota">Se descartaron ${interp.recursos_descartados.length} recurso(s) propuestos por el modelo porque su cita no aparece en el poema.</p>`
      : "";

    panel.innerHTML = `<div class="filtros" role="group" aria-label="Filtrar por categoría">${chips}</div>
      <div class="recursos">
        <div class="tarjeta poema-resaltado" aria-label="Poema con los recursos resaltados">${poema}</div>
        <div><div class="lista-recursos">${lista}</div>${descartados}</div>
      </div>`;

    $$("[data-filtro]", panel).forEach((b) =>
      b.addEventListener("click", () => {
        const c = b.dataset.filtro;
        filtros.has(c) ? filtros.delete(c) : filtros.add(c);
        renderizarRecursos(d);
      })
    );
    const activar = (id, desplazar) => {
      $$(".activo", panel).forEach((x) => x.classList.remove("activo"));
      if (id === null) return;
      $$(`mark`, panel).filter((m) => m.dataset.ids.split(" ").includes(String(id))).forEach((m) => m.classList.add("activo"));
      const tarjeta = $(`.recurso[data-id="${id}"]`, panel);
      if (tarjeta) {
        tarjeta.classList.add("activo");
        if (desplazar) tarjeta.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    };
    $$(".recurso", panel).forEach((t) => {
      t.addEventListener("mouseenter", () => activar(t.dataset.id, false));
      t.addEventListener("focus", () => activar(t.dataset.id, false));
      t.addEventListener("mouseleave", () => activar(null));
    });
    $$("mark", panel).forEach((m) => m.addEventListener("click", () => activar(m.dataset.ids.split(" ")[0], true)));
  }

  /* D. Temas */
  function htmlTemas(d) {
    const i = d.interpretativo;
    if (!i) return sinInterpretacion(d);
    const subs = i.temas.subtemas.map((s) => `<li>${esc(s)}</li>`).join("");
    return `<div class="tarjeta">
      <h3 class="sub">Tema principal</h3>
      <p class="tema-principal">${esc(i.temas.principal)}</p>
      <h3 class="sub">Subtemas</h3>
      <ul class="subtemas">${subs || '<li class="vacio">Sin subtemas</li>'}</ul>
      ${i.temas.subtemas_insuficientes ? '<p class="nota">El modelo propuso menos de dos subtemas.</p>' : ""}
    </div>`;
  }

  /* E. Interpretación */
  function htmlInterpretacion(d) {
    const i = d.interpretativo;
    if (!i) return sinInterpretacion(d);
    return `<div class="tarjeta interpretacion">
      <p class="texto">${esc(i.interpretacion.texto)}</p>
      <p class="nota">${i.interpretacion.palabras} palabras${i.interpretacion.recortada ? " · recortada al máximo de 50" : ""} · propuesta de ${esc(i.modelo || "modelo")}</p>
    </div>`;
  }

  function capitalizar(s) {
    s = String(s || "");
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  /* ---------- Exportación ---------- */
  function celda(s) {
    return String(s ?? "").replace(/\|/g, "\\|").replace(/\n/g, " ");
  }

  function aMarkdown(d) {
    const m = d.metrica, v = d.versificacion, i = d.interpretativo;
    const L = [];
    L.push("# Análisis del poema", "");
    let estrofa = null;
    for (const x of m.versos) {
      if (estrofa !== null && x.estrofa !== estrofa) L.push(">");
      estrofa = x.estrofa;
      L.push(`> ${x.texto}`);
    }
    L.push("", "## A. Métrica", "");
    L.push(`Metro${m.metros.length > 1 ? "s" : ""}: ${m.metros.join(" y ")} sílabas.`, "");
    L.push("| N.º | Verso | Silabeo | Licencias | Sílabas | Rima |", "|---|---|---|---|---|---|");
    for (const x of m.versos) {
      const lic = x.licencias.map((l) => `${l.tipo} (${l.texto})`).join(", ") || "—";
      const alt = x.alternativas.length ? ` (alternativas: ${x.alternativas.map((a) => `${a.silabeo} = ${a.silabas}`).join("; ")})` : "";
      L.push(`| ${x.numero} | ${celda(x.texto)} | ${celda(x.silabeo + alt)} | ${celda(lic)}; acento final ${celda(leyFinal(x))} | ${x.silabas}, ${celda(x.nombre)}, ${x.arte} (confianza ${x.confianza}) | ${celda(x.rima)} ${celda(x.terminacion || "")} |`);
    }
    L.push("", "## B. Versificación", "");
    L.push(`- **Rima:** ${v.rima.tipo}; esquema ${v.rima.esquema} (confianza ${v.rima.confianza}).`);
    L.push(`- **Composición:** ${v.composicion.tipo} (confianza ${v.composicion.confianza}). ${v.composicion.justificacion}`);
    L.push(`- **Estrofas:**`);
    for (const e of v.estrofas) L.push(`    - ${e.numero}. ${e.tipo}: ${e.esquema} (confianza ${e.confianza})`);
    if (!i) {
      L.push("", "_Recursos, temas e interpretación no disponibles en este análisis._");
      return L.join("\n") + "\n";
    }
    L.push("", "## C. Recursos poéticos", "");
    for (const c of CATEGORIAS) {
      const rs = i.recursos.filter((r) => r.categoria === c);
      if (!rs.length) continue;
      L.push(`### ${capitalizar(c)}`, "");
      for (const r of rs) {
        const vv = r.verso === r.hasta_verso ? `v. ${r.verso}` : `vv. ${r.verso}–${r.hasta_verso}`;
        L.push(`- **${capitalizar(r.nombre)}** (${vv}, confianza ${r.confianza}): «${r.cita}». ${r.explicacion}`);
      }
      L.push("");
    }
    L.push("## D. Temas centrales", "", `- **Tema principal:** ${i.temas.principal}`);
    for (const s of i.temas.subtemas) L.push(`- ${s}`);
    L.push("", "## E. Posibles líneas de lectura e interpretación", "", i.interpretacion.texto, "");
    return L.join("\n");
  }

  $("#exportar-md").addEventListener("click", () => {
    if (!ultimo) return;
    const blob = new Blob([aMarkdown(ultimo)], { type: "text/markdown;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "analisis-poema.md";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });

  $("#exportar-pdf").addEventListener("click", () => {
    if (!ultimo) return;
    // Muestra todas las secciones y abre el diálogo de impresión («Guardar como PDF»).
    $$("details.alternativas").forEach((x) => (x.open = true));
    window.print();
  });

  // Exponer para pruebas manuales en la consola.
  window.__analizador = { aMarkdown };
})();
