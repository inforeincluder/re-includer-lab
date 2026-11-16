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
    // Compartilhamento é exclusivo de artigos publicados; não inserir em páginas institucionais.
    var content = document.querySelector(".post-content") || document.querySelector("article .e-content") || document.querySelector(".e-content");
    if (!content || !document.querySelector(".post-header, .post-title, article .post-title")) return;
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


  function addBackToTop() {
    if (document.querySelector(".back-to-top")) return;
    var button = document.createElement("button");
    button.type = "button";
    button.className = "back-to-top";
    button.textContent = "↑ Voltar ao topo";
    button.setAttribute("aria-label", "Voltar ao início da página");
    button.hidden = true;
    button.addEventListener("click", function () {
      var reduce = prefs.motion === "reduced" ||
        (prefs.motion === "system" && window.matchMedia &&
         window.matchMedia("(prefers-reduced-motion: reduce)").matches);
      window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
    });
    document.body.appendChild(button);
    var ticking = false;
    function updateVisibility() {
      button.hidden = window.scrollY < 450;
      ticking = false;
    }
    window.addEventListener("scroll", function () {
      if (!ticking) {
        window.requestAnimationFrame(updateVisibility);
        ticking = true;
      }
    }, { passive: true });
    updateVisibility();
  }

  function addRelatedArticles() {
    var content = document.querySelector(".post-content") ||
      document.querySelector("article .e-content") ||
      document.querySelector(".e-content");
    if (!content || !document.querySelector(".post-header, .post-title, article .post-title") ||
        document.querySelector(".related-articles")) return;

    var dataNode = document.getElementById("site-related-posts-data");
    var posts = [];
    if (dataNode) {
      try { posts = JSON.parse(dataNode.textContent || "[]"); } catch (e) {}
    }
    var currentUrl = window.location.pathname.replace(/\/$/, "");
    var current = posts.find(function (post) {
      return (post.url || "").replace(/\/$/, "") === currentUrl;
    });
    var currentCategories = current && current.categories ? current.categories : [];
    var currentTags = current && current.tags ? current.tags : [];
    var related = posts.filter(function (post) {
      return (post.url || "").replace(/\/$/, "") !== currentUrl;
    }).map(function (post) {
      var categories = post.categories || [];
      var tags = post.tags || [];
      var score = categories.filter(function (x) { return currentCategories.indexOf(x) !== -1; }).length * 5 +
        tags.filter(function (x) { return currentTags.indexOf(x) !== -1; }).length;
      return { post: post, score: score };
    }).sort(function (a, b) { return b.score - a.score; })
      .slice(0, 4).map(function (item) { return item.post; });

    var section = document.createElement("section");
    section.className = "related-articles";
    section.setAttribute("aria-labelledby", "related-articles-title");
    var heading = document.createElement("h2");
    heading.id = "related-articles-title";
    heading.textContent = related.length ? "Continue a leitura" : "Continue explorando";
    section.appendChild(heading);

    var list = document.createElement("ul");
    if (related.length) {
      related.forEach(function (post) {
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.href = post.url;
        a.textContent = post.title || "Ler artigo";
        li.appendChild(a);
        if (post.description) {
          var description = document.createElement("p");
          description.textContent = post.description;
          li.appendChild(description);
        }
        list.appendChild(li);
      });
    } else {
      [
        { title: "Ferramentas práticas", url: "/re-includer-lab/ferramentas/" },
        { title: "Metodologia de pesquisa", url: "/re-includer-lab/pesquisa/" },
        { title: "Fontes e metodologia editorial", url: "/re-includer-lab/fontes-e-metodologia/" }
      ].forEach(function (item) {
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.href = item.url;
        a.textContent = item.title;
        li.appendChild(a);
        list.appendChild(li);
      });
    }
    section.appendChild(list);
    content.appendChild(section);
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


  // Fecha o menu móvel do Minima ao clicar fora, selecionar um link ou pressionar Escape.
  function initMobileMenuDismiss() {
    var nav = document.querySelector(".site-nav");
    var trigger = nav && nav.querySelector("#nav-trigger");
    if (!nav || !trigger || nav.dataset.dismissReady === "true") return;
    nav.dataset.dismissReady = "true";

    function closeMenu() {
      if (trigger.checked) {
        trigger.checked = false;
        trigger.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }

    document.addEventListener("click", function (event) {
      if (trigger.checked && !nav.contains(event.target)) closeMenu();
    });

    nav.querySelectorAll(".trigger a").forEach(function (link) {
      link.addEventListener("click", closeMenu);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && trigger.checked) {
        closeMenu();
        var menuButton = nav.querySelector("label[for='nav-trigger']");
        if (menuButton) menuButton.focus();
      }
    });
  }

  function init() { makeTablesScrollable(); addAccessibility(); addSharing(); addRelatedArticles(); addBackToTop(); initMobileMenuDismiss(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true }); else init();
  if (window.matchMedia) {
    var mq = window.matchMedia("(prefers-color-scheme: dark)");
    if (mq.addEventListener) mq.addEventListener("change", function () { if (prefs.theme === "auto") apply(); });
  }
}());
