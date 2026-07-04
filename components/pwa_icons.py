"""
🐺 Wolf Wallet — PWA / Ícone do atalho mobile

Sobrescreve o ícone padrão do Streamlit Cloud (a "coroa") quando o usuário
adiciona o app à tela de início no celular.

Como funciona:
    - O ícone do atalho vem do <link rel="apple-touch-icon"> (iOS) e do
      web manifest (Android). O st.set_page_config(page_icon=...) só troca o
      favicon da aba, não o atalho.
    - No Streamlit Community Cloud o app roda dentro de um iframe aninhado:
          documento externo (wolf-wallet.streamlit.app)   <- Chrome lê o manifest AQUI
            └─ iframe do app (/~/+/)                       <- mesma origem que o topo
                 └─ iframe do st.components.html           <- onde este script roda
      Por isso é preciso injetar no `window.top.document` (o externo), e não no
      `window.parent` (que é só o documento do app, no meio). Os dois são
      mesma origem, então o acesso é permitido.
    - Os arquivos são servidos pela pasta static/ (enableStaticServing = true).
      Na Cloud a URL do app tem prefixo (/~/+/), então a base dos assets é
      derivada em runtime a partir do location do documento do app.

Usage:
    from components.pwa_icons import inject_pwa_icons
    inject_pwa_icons()
"""

from __future__ import annotations

import streamlit.components.v1 as components

# Versão para "cache-busting" — incremente ao trocar os arquivos de ícone
_ICON_VERSION = "2"


def inject_pwa_icons(app_title: str = "Wolf Wallet") -> None:
    """Injeta apple-touch-icon, manifest e metas de PWA no <head> externo."""
    components.html(
        f"""
        <script>
        (function () {{
          const V = "?v={_ICON_VERSION}";
          const TITLE = "{app_title}";

          function appStaticBase() {{
            // window.parent = documento do app (tem o base path correto, ex.: /~/+/ na Cloud)
            const loc = window.parent.location;
            let path = loc.pathname;
            if (!path.endsWith("/")) path += "/";
            return loc.origin + path + "app/static/";
          }}

          function inject(doc, base) {{
            const head = doc.head;

            function upsertLink(rel, href, sizes) {{
              doc.querySelectorAll("link[rel='" + rel + "']").forEach(function (el) {{
                el.parentNode.removeChild(el);
              }});
              const l = doc.createElement("link");
              l.setAttribute("rel", rel);
              if (sizes) l.setAttribute("sizes", sizes);
              l.setAttribute("href", href + V);
              head.appendChild(l);
            }}

            function upsertMeta(name, content) {{
              let m = doc.querySelector("meta[name='" + name + "']");
              if (!m) {{
                m = doc.createElement("meta");
                m.setAttribute("name", name);
                head.appendChild(m);
              }}
              m.setAttribute("content", content);
            }}

            upsertLink("apple-touch-icon", base + "apple-touch-icon.png", "180x180");
            upsertLink("icon", base + "icon-192.png", "192x192");
            upsertLink("manifest", base + "manifest.json");

            upsertMeta("apple-mobile-web-app-title", TITLE);
            upsertMeta("apple-mobile-web-app-capable", "yes");
            upsertMeta("apple-mobile-web-app-status-bar-style", "black-translucent");
            upsertMeta("theme-color", "#0E1117");

            // pwacompat: gera as apple-touch-startup-image (splash do iOS) a partir
            // do manifest — elimina a tela branca ao abrir a PWA no iPhone.
            // O Streamlit serve .js como text/plain (o browser recusa <script src>),
            // então buscamos o código via fetch e injetamos inline (executa e roda
            // uma única vez por documento).
            try {{
              if (!window.top.__wolfPwacompat) {{
                window.top.__wolfPwacompat = true;
                fetch(base + "pwacompat.min.js" + V)
                  .then(function (r) {{ return r.text(); }})
                  .then(function (code) {{
                    const s = doc.createElement("script");
                    s.textContent = code;
                    doc.head.appendChild(s);
                  }})
                  .catch(function () {{}});
              }}
            }} catch (e) {{ /* ignora */ }}
          }}

          function run() {{
            try {{
              const base = appStaticBase();
              // Injeta no documento MAIS EXTERNO (onde o Chrome lê o manifest).
              // Fallback para o documento do app se window.top não for acessível.
              let doc;
              try {{ doc = window.top.document; doc.head; }} catch (e) {{ doc = window.parent.document; }}
              inject(doc, base);
            }} catch (e) {{ /* origem cruzada ou head indisponível — ignora */ }}
          }}

          run();
          // Reaplica: o wrapper do Streamlit Cloud pode reescrever o <head> após o load
          setTimeout(run, 1500);
          setTimeout(run, 4000);
        }})();
        </script>
        """,
        height=0,
    )
