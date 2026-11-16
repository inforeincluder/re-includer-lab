(function () {
  "use strict";
  var KEY = "2elab-a11y-preferences";
  var defaults = { theme: "auto", scale: "100%", contrast: "normal", motion: "system" };
  var prefs = Object.assign({}, defaults);
  try { prefs = Object.assign(prefs, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) {}
  var allowed = {
    theme: ["auto", "light", "dark", "sepia"],
    scale: ["100%", "115%", "130%", "1", "1.15", "1.3"],
    contrast: ["normal", "high"],
    motion: ["system", "reduced", "full"]
  };
  Object.keys(allowed).forEach(function (key) {
    if (allowed[key].indexOf(prefs[key]) === -1) prefs[key] = defaults[key];
  });
  if (prefs.scale === "1") prefs.scale = "100%";
  else if (prefs.scale === "1.15") prefs.scale = "115%";
  else if (prefs.scale === "1.3") prefs.scale = "130%";
  var root = document.documentElement;

  function apply() {
    var theme = prefs.theme;
    if (theme === "auto") theme = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    root.setAttribute("data-theme", theme);
    root.style.setProperty("--a11y-scale", prefs.scale);
    root.setAttribute("data-contrast", prefs.contrast);
    if (prefs.motion === "reduced") root.setAttribute("data-motion", "reduced");
    else if (prefs.motion === "full") root.setAttribute("data-motion", "full");
    else root.removeAttribute("data-motion");
    try { localStorage.setItem(KEY, JSON.stringify(prefs)); } catch (e) {}
    document.querySelectorAll("[data-pref]").forEach(function (button) {
      button.setAttribute("aria-pressed", String(prefs[button.dataset.pref] === button.dataset.value));
    });
  }

  function button(label, pref, value) {
    var b = document.createElement("button");
    b.type = "button"; b.textContent = label; b.className = "a11y-control";
    b.dataset.pref = pref; b.dataset.value = value; b.setAttribute("aria-pressed", "false");
    b.addEventListener("click", function () { prefs[pref] = value; apply(); });
    return b;
  }

  function fieldset(legend, items) {
    var fs = document.createElement("fieldset"), lg = document.createElement("legend"), row = document.createElement("div");
    lg.textContent = legend; row.className = "a11y-options";
    items.forEach(function (item) { row.appendChild(button(item[0], item[1], item[2])); });
    fs.append(lg, row); return fs;
  }

  function addAccessibility() {
    if (document.querySelector(".a11y-widget")) return;
    var main = document.querySelector("#main-content") || document.querySelector("main") || document.querySelector(".page-content");
    if (main && !main.id) main.id = "main-content";
    if (main) {
      var skip = document.createElement("a");
      skip.className = "a11y-skip-link"; skip.href = "#main-content"; skip.textContent = "Pular para o conteúdo";
      document.body.insertBefore(skip, document.body.firstChild);
    }
    var aside = document.createElement("aside"); aside.className = "a11y-widget"; aside.setAttribute("aria-label", "Opções de acessibilidade");
    var details = document.createElement("details"), summary = document.createElement("summary");
    summary.textContent = "Acessibilidade"; details.appendChild(summary);
    var panel = document.createElement("div"); panel.className = "a11y-panel";
    panel.appendChild(fieldset("Aparência", [["Automático","theme","auto"],["Claro","theme","light"],["Escuro","theme","dark"],["Sépia","theme","sepia"]]));
    panel.appendChild(fieldset("Tamanho do texto", [["Padrão","scale","100%"],["Maior","scale","115%"],["Muito maior","scale","130%"]]));
    panel.appendChild(fieldset("Contraste", [["Padrão","contrast","normal"],["Alto contraste","contrast","high"]]));
    panel.appendChild(fieldset("Movimento", [["Padrão do aparelho","motion","system"],["Reduzir animações","motion","reduced"],["Permitir animações","motion","full"]]));
    var reset = document.createElement("button"); reset.type = "button"; reset.textContent = "Restaurar padrão";
    reset.addEventListener("click", function () { prefs = Object.assign({}, defaults); apply(); });
    var hint = document.createElement("p"); hint.className = "a11y-hint"; hint.textContent = "As preferências ficam salvas somente neste navegador.";
    panel.append(reset, hint); details.appendChild(panel); aside.appendChild(details); document.body.appendChild(aside);
    apply();
  }

  function addSharing() {
    var content = document.querySelector(".post-content") || document.querySelector(".e-content") || document.querySelector("article");
    if (!content || document.querySelector(".a11y-share")) return;
    var titleNode = document.querySelector(".post-title") || document.querySelector("h1");
    var title = titleNode ? titleNode.textContent.trim() : document.title;
    var url = window.location.href;
    var encTitle = encodeURIComponent(title), encUrl = encodeURIComponent(url);
    var section = document.createElement("section"); section.className = "a11y-share"; section.setAttribute("aria-labelledby", "share-title");
    var heading = document.createElement("h2"); heading.id = "share-title"; heading.textContent = "Compartilhe este artigo";
    var row = document.createElement("div"); row.className = "a11y-options";
    function link(label, href) {
      var a = document.createElement("a"); a.textContent = label; a.href = href; a.target = "_blank"; a.rel = "noopener noreferrer"; row.appendChild(a);
    }
    link("WhatsApp", "https://wa.me/?text=" + encTitle + "%20" + encUrl);
    link("Facebook", "https://www.facebook.com/sharer/sharer.php?u=" + encUrl);
    link("LinkedIn", "https://www.linkedin.com/sharing/share-offsite/?url=" + encUrl);
    link("X", "https://twitter.com/intent/tweet?text=" + encTitle + "&url=" + encUrl);
    var copy = document.createElement("button"); copy.type = "button"; copy.textContent = "Copiar link"; copy.className = "a11y-control";
    var status = document.createElement("p"); status.className = "a11y-status"; status.setAttribute("role", "status"); status.setAttribute("aria-live", "polite");
    copy.addEventListener("click", function () {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () { status.textContent = "Link copiado."; }).catch(function () { status.textContent = "Não foi possível copiar automaticamente. Copie o endereço do navegador."; });
      } else { status.textContent = "Copie o endereço diretamente na barra do navegador."; }
    });
    if (navigator.share) {
      var nativeShare = document.createElement("button"); nativeShare.type = "button"; nativeShare.textContent = "Compartilhar"; nativeShare.className = "a11y-control";
      nativeShare.addEventListener("click", function () { navigator.share({ title: title, url: url }).catch(function () {}); });
      row.appendChild(nativeShare);
    }
    row.appendChild(copy); section.append(heading, row, status); content.appendChild(section);
  }

  function makeTablesScrollable() {
    document.querySelectorAll("main table, .post-content table, .page-content table, article table").forEach(function (table) {
      if (table.closest(".table-scroll")) return;
      var firstRow = table.rows && table.rows.length ? table.rows[0] : null;
      if (firstRow && firstRow.cells.length >= 4) table.classList.add("table-wide");
      var headerRows = table.tHead ? table.tHead.rows : [];
      Array.prototype.forEach.call(headerRows, function (row) {
        Array.prototype.forEach.call(row.cells, function (cell) {
          if (cell.tagName === "TH" && !cell.hasAttribute("scope")) cell.setAttribute("scope", "col");
        });
      });
      var wrapper = document.createElement("div");
      wrapper.className = "table-scroll";
      wrapper.setAttribute("role", "region");
      wrapper.setAttribute("aria-label", "Tabela — role horizontalmente para consultar todas as colunas");
      wrapper.setAttribute("tabindex", "0");
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    });
  }

  function init() { makeTablesScrollable(); addAccessibility(); addSharing(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true }); else init();
  if (window.matchMedia) {
    var mq = window.matchMedia("(prefers-color-scheme: dark)");
    if (mq.addEventListener) mq.addEventListener("change", function () { if (prefs.theme === "auto") apply(); });
  }
}());
