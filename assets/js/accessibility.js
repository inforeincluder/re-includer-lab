(function () {
  "use strict";
  var KEY = "2elab-accessibility-v1";
  var defaults = { theme: "light", scale: 100, spacing: "normal", font: "default", width: "normal", links: false, contrast: false, motion: false };
  var state = Object.assign({}, defaults);
  try { state = Object.assign(state, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) {}
  var root = document.documentElement;
  function apply() {
    root.dataset.a11yTheme = state.theme;
    root.dataset.a11yFont = state.font;
    root.dataset.a11yWidth = state.width;
    root.dataset.a11yLinks = state.links ? "on" : "off";
    root.dataset.a11yContrast = state.contrast ? "high" : "normal";
    root.dataset.a11yMotion = state.motion ? "reduce" : "normal";
    root.style.fontSize = state.scale + "%";
    root.style.lineHeight = state.spacing === "loose" ? "1.85" : state.spacing === "wide" ? "2.05" : "";
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
    document.querySelectorAll("[data-a11y-control]").forEach(function (el) {
      var key = el.dataset.a11yControl;
      if (el.type === "checkbox") el.checked = !!state[key];
      else el.value = String(state[key]);
    });
  }
  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    if (text) node.textContent = text;
    return node;
  }
  function init() {
    if (document.getElementById("a11y-launcher")) return;
    var launcher = el("button", { id: "a11y-launcher", class: "a11y-launcher", type: "button", "aria-expanded": "false", "aria-controls": "a11y-panel" }, "Acessibilidade");
    var panel = el("section", { id: "a11y-panel", class: "a11y-panel", role: "region", "aria-labelledby": "a11y-title", hidden: "" });
    var close = el("button", { type: "button", class: "a11y-close", "aria-label": "Fechar opções de acessibilidade" }, "Fechar");
    var title = el("h2", { id: "a11y-title" }, "Personalizar leitura");
    panel.append(close, title);
    function selectGroup(labelText, key, options) {
      var fs = el("fieldset"), legend = el("legend", {}, labelText), select = el("select", { "data-a11y-control": key, "aria-label": labelText });
      options.forEach(function (o) { select.appendChild(el("option", { value: o[0] }, o[1])); });
      fs.append(legend, select); panel.appendChild(fs);
      select.addEventListener("change", function () { state[key] = key === "scale" ? Number(select.value) : select.value; apply(); });
    }
    selectGroup("Cores", "theme", [["light","Claro"],["dark","Escuro"],["sepia","Sépia"]]);
    selectGroup("Tamanho do texto", "scale", [["90","90%"],["100","100%"],["110","110%"],["120","120%"],["130","130%"],["140","140%"]]);
    selectGroup("Espaçamento entre linhas", "spacing", [["normal","Padrão"],["loose","Amplo"],["wide","Muito amplo"]]);
    selectGroup("Tipo de fonte", "font", [["default","Fonte do site"],["sans","Sem serifa"]]);
    selectGroup("Largura do texto", "width", [["normal","Padrão"],["wide","Ampla"]]);
    function check(labelText, key) {
      var fs = el("fieldset"), label = el("label"), input = el("input", { type: "checkbox", "data-a11y-control": key });
      label.append(input, document.createTextNode(" " + labelText)); fs.appendChild(label); panel.appendChild(fs);
      input.addEventListener("change", function () { state[key] = input.checked; apply(); });
    }
    check("Sublinhar links", "links");
    check("Aumentar contraste", "contrast");
    check("Reduzir animações", "motion");
    var actions = el("div", { class: "a11y-actions" });
    var reset = el("button", { type: "button" }, "Restaurar padrão");
    reset.addEventListener("click", function () { state = Object.assign({}, defaults); apply(); });
    actions.appendChild(reset); panel.appendChild(actions);
    close.addEventListener("click", function () { panel.hidden = true; launcher.setAttribute("aria-expanded", "false"); launcher.focus(); });
    launcher.addEventListener("click", function () {
      panel.hidden = !panel.hidden;
      launcher.setAttribute("aria-expanded", String(!panel.hidden));
      if (!panel.hidden) close.focus();
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !panel.hidden) { panel.hidden = true; launcher.setAttribute("aria-expanded", "false"); launcher.focus(); }
    });
    document.body.append(launcher, panel);
    apply();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
}());
