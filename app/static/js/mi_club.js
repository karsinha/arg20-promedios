/* "Mi club" sin cuentas: el slug vive en localStorage; la tarjeta la arma el servidor (/parcial/club/<slug>). */
(function () {
  var KEY = "mi_club";

  function leer() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function guardar(slug) {
    try { if (slug) localStorage.setItem(KEY, slug); else localStorage.removeItem(KEY); } catch (e) {}
  }

  function pintar() {
    var actual = leer();
    document.querySelectorAll("[data-mi-club]").forEach(function (b) {
      var es = b.getAttribute("data-mi-club") === actual;
      b.classList.toggle("on", es);
      b.textContent = es ? "★ Mi club" : "☆ Hacer mi club";
      b.setAttribute("aria-pressed", es ? "true" : "false");
    });
  }

  function cargar() {
    var el = document.getElementById("mi-club");
    if (!el) return;
    var slug = leer();
    if (!slug) { el.innerHTML = ""; return; }
    if (!window.htmx) return;
    htmx.ajax("GET", "/parcial/club/" + encodeURIComponent(slug), { target: "#mi-club", swap: "innerHTML" });
  }

  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-mi-club], [data-mi-club-quitar]");
    if (!t) return;
    if (t.hasAttribute("data-mi-club-quitar")) {
      guardar(null);
    } else {
      var slug = t.getAttribute("data-mi-club");
      guardar(leer() === slug ? null : slug);
    }
    pintar();
    cargar();
  });

  // Si el club guardado ya no existe, se limpia solo.
  document.body.addEventListener("htmx:responseError", function (e) {
    var d = e.detail || {};
    if (d.target && d.target.id === "mi-club") { guardar(null); d.target.innerHTML = ""; pintar(); }
  });

  pintar();
  cargar();
})();
