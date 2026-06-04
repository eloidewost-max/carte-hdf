#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bakpanel2"))
print("Backup cree :", SRC.with_suffix(".html.bakpanel2"))

html = SRC.read_text(encoding="utf-8")
original = html
ok = True

def must_replace(old, new, label):
    global html, ok
    if old not in html:
        print("  [X] ANCRE ABSENTE :", label); ok = False; return
    html = html.replace(old, new, 1)
    print("  [OK]", label)

# 1. Declarer collapsedStatuts en global, a cote de activeStatutFilters
must_replace(
    "  var activeStatutFilters = []; // filtre multi-statuts en mode prospection",
    "  var activeStatutFilters = []; // filtre multi-statuts en mode prospection\n"
    "  var collapsedStatuts = {}; // memorise les categories repliees dans le panneau gauche",
    "Declaration collapsedStatuts")

# 2. Bouton date : clic ouvre le calendrier via showPicker (vrai geste). On ajoute un onclick au pickBtn.
must_replace(
    "    pickWrap.appendChild(pickBtn);\n"
    "    pickWrap.appendChild(pickInput);",
    "    pickBtn.addEventListener('click', function() {\n"
    "      if (typeof pickInput.showPicker === 'function') { try { pickInput.showPicker(); return; } catch(e) {} }\n"
    "      pickInput.focus(); pickInput.click();\n"
    "    });\n"
    "    pickWrap.appendChild(pickBtn);\n"
    "    pickWrap.appendChild(pickInput);",
    "Bouton date : ouvre le calendrier au clic")

# 2b. L'input ne doit plus etre par-dessus le bouton (sinon il intercepte). On le sort du flux.
must_replace(
    "    pickInput.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;';",
    "    pickInput.style.cssText = 'position:absolute;left:-9999px;width:1px;height:1px;opacity:0;';",
    "Input date sorti du flux (ne bloque plus le bouton)")

# 3. Toggle persistant : a la creation, appliquer l'etat memorise + le sauvegarder au clic.
must_replace(
    "      var ul = document.createElement('ul');\n"
    "      ul.className = 'prospect-list';\n"
    "      secTitle.addEventListener('click', function() {\n"
    "        var hidden = ul.style.display === 'none';\n"
    "        ul.style.display = hidden ? '' : 'none';\n"
    "        chevron.textContent = hidden ? '\\u25be ' : '\\u25b8 ';\n"
    "      });",
    "      var ul = document.createElement('ul');\n"
    "      ul.className = 'prospect-list';\n"
    "      // Restaurer l'etat repli/deplie memorise\n"
    "      if (collapsedStatuts[st.key]) {\n"
    "        ul.style.display = 'none';\n"
    "        chevron.textContent = '\\u25b8 ';\n"
    "      }\n"
    "      (function(stKey){\n"
    "        secTitle.addEventListener('click', function() {\n"
    "          var hidden = ul.style.display === 'none';\n"
    "          ul.style.display = hidden ? '' : 'none';\n"
    "          chevron.textContent = hidden ? '\\u25be ' : '\\u25b8 ';\n"
    "          collapsedStatuts[stKey] = !hidden;\n"
    "        });\n"
    "      })(st.key);",
    "Toggle persistant (memorise l'etat)")

# Checks
for needle, label in [
    ("var collapsedStatuts", "Variable collapsedStatuts"),
    ("pickInput.showPicker", "Bouton date ouvre calendrier"),
    ("left:-9999px", "Input date hors flux"),
    ("collapsedStatuts[stKey] = !hidden", "Memorisation toggle"),
]:
    print(("  [OK] " if needle in html else "  [X] MANQUANT : ") + label)
    if needle not in html: ok = False

if not ok:
    print("\\n[!] Patch incomplet. Fichier NON ecrase. (backup .bakpanel2)"); sys.exit(1)
if html == original:
    print("\\n[!] Aucune modification."); sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print("\\n[OK] Patch panel2 applique ->", SRC)
print("   Taille :", "{:,}".format(len(html)), "caracteres")
