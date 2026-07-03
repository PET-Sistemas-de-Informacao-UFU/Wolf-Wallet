"""
🐺 Wolf Wallet — PWA / Ícone do atalho mobile

Sobrescreve o ícone padrão do Streamlit Cloud (a "coroa") quando o usuário
adiciona o app à tela de início no celular.

Como funciona:
    - O ícone do atalho vem do <link rel="apple-touch-icon"> (iOS) e do
      web manifest (Android). O st.set_page_config(page_icon=...) só troca o
      favicon da aba, não o atalho.
    - O componente injeta esses links no <head> do documento pai (o iframe do
      st.components.html é same-origin, então acessa window.parent.document).
    - Os arquivos são servidos pela pasta static/ (enableStaticServing = true).

Usage:
    from components.pwa_icons import inject_pwa_icons
    inject_pwa_icons()
"""

from __future__ import annotations

import streamlit.components.v1 as components

# Caminho onde o Streamlit expõe a pasta ./static/ (enableStaticServing = true)
_STATIC_URL_PATH = "/app/static"

# Versão para "cache-busting" — incremente ao trocar os arquivos de ícone
_ICON_VERSION = "1"


def inject_pwa_icons(app_title: str = "Wolf Wallet") -> None:
    """Injeta apple-touch-icon, manifest e metas de PWA no <head> da página."""
    components.html(
        f"""
        <script>
        (function () {{
          try {{
            const doc = window.parent.document;
            const head = doc.head;
            const base = window.parent.location.origin + "{_STATIC_URL_PATH}/";
            const v = "?v={_ICON_VERSION}";

            function upsertLink(rel, href, sizes) {{
              doc.querySelectorAll("link[rel='" + rel + "']").forEach(function (el) {{
                el.parentNode.removeChild(el);
              }});
              const l = doc.createElement("link");
              l.setAttribute("rel", rel);
              if (sizes) l.setAttribute("sizes", sizes);
              l.setAttribute("href", href + v);
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

            // Ícone do atalho no iOS
            upsertLink("apple-touch-icon", base + "apple-touch-icon.png", "180x180");
            // Favicon da aba (sobrescreve o emoji por consistência)
            upsertLink("icon", base + "icon-192.png", "192x192");
            // Manifest (Android / Chrome)
            upsertLink("manifest", base + "manifest.json");

            // Metadados do atalho
            upsertMeta("apple-mobile-web-app-title", "{app_title}");
            upsertMeta("apple-mobile-web-app-capable", "yes");
            upsertMeta("apple-mobile-web-app-status-bar-style", "black-translucent");
            upsertMeta("theme-color", "#0E1117");
          }} catch (e) {{
            /* origem cruzada ou head indisponível — ignora silenciosamente */
          }}
        }})();
        </script>
        """,
        height=0,
    )
