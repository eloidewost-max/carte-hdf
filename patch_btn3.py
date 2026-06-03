#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bakbtn3"))
print("Backup cree :", SRC.with_suffix(".html.bakbtn3"))

html = SRC.read_text(encoding="utf-8")
original = html
ok = True

# Transformer l'IIFE en fonction nommee + appel garanti apres chargement du DOM.
# Debut : "(function initGlobalRdvDate() {" -> "function initGlobalRdvDate() {"
old_start = "  (function initGlobalRdvDate() {"
new_start = "  function initGlobalRdvDate() {"
if old_start not in html:
    print("  [X] debut IIFE introuvable"); ok = False
else:
    html = html.replace(old_start, new_start, 1)
    print("  [OK] IIFE transformee en fonction nommee (debut)")

# Fin : "  })();" -> "  }\n  if (document.readyState === 'loading') {...} else initGlobalRdvDate();"
# On cible le })(); qui suit le document.addEventListener du menu (le plus proche apres notre code).
# Pour eviter toute ambiguite, on remplace la sequence unique de fermeture de CETTE IIFE.
old_end = (
    "    document.addEventListener('click', function(e) {\n"
    "      if (listMenu.style.display !== 'block') return;\n"
    "      if (!listMenu.contains(e.target) && !listBtn.contains(e.target)) listMenu.style.display = 'none';\n"
    "    });\n"
    "  })();"
)
new_end = (
    "    document.addEventListener('click', function(e) {\n"
    "      if (listMenu.style.display !== 'block') return;\n"
    "      if (!listMenu.contains(e.target) && !listBtn.contains(e.target)) listMenu.style.display = 'none';\n"
    "    });\n"
    "  }\n"
    "  if (document.readyState === 'loading') {\n"
    "    document.addEventListener('DOMContentLoaded', initGlobalRdvDate);\n"
    "  } else {\n"
    "    initGlobalRdvDate();\n"
    "  }"
)
if old_end not in html:
    print("  [X] fin IIFE introuvable"); ok = False
else:
    html = html.replace(old_end, new_end, 1)
    print("  [OK] Appel garanti apres DOMContentLoaded (fin)")

# Checks
for needle, label in [
    ("function initGlobalRdvDate() {", "Fonction nommee"),
    ("document.addEventListener('DOMContentLoaded', initGlobalRdvDate)", "Appel sur DOMContentLoaded"),
]:
    print(("  [OK] " if needle in html else "  [X] MANQUANT : ") + label)
    if needle not in html: ok = False

# Verifier qu'il ne reste pas l'ancien })(); orphelin juste apres notre code
if "    });\n  })();" in html:
    print("  [!] reste un })(); a verifier")

if not ok:
    print("\\n[!] Patch incomplet. Fichier NON ecrase. (backup .bakbtn3)"); sys.exit(1)
if html == original:
    print("\\n[!] Aucune modification."); sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print("\\n[OK] Patch btn3 applique ->", SRC)
print("   Taille :", "{:,}".format(len(html)), "caracteres")
