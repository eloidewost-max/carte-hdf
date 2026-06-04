#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bakpanel3"))
print("Backup cree :", SRC.with_suffix(".html.bakpanel3"))

html = SRC.read_text(encoding="utf-8")
original = html
ok = True

def must_replace(old, new, label):
    global html, ok
    if old not in html:
        print("  [X] ANCRE ABSENTE :", label); ok = False; return
    html = html.replace(old, new, 1)
    print("  [OK]", label)

# 1. Supprimer le bouton "Choisir une date" : tout le bloc pickWrap/pickBtn/pickInput.
must_replace(
    "    var pickWrap = document.createElement('div');\n"
    "    pickWrap.style.cssText = 'position:relative;width:100%;margin-bottom:6px;';\n"
    "    var pickBtn = document.createElement('button');\n"
    "    pickBtn.textContent = '\\ud83d\\udcc5 Choisir une date';\n"
    "    pickBtn.style.cssText = 'width:100%;padding:9px 10px;background:#7e22ce;border:none;border-radius:7px;color:#fff;font-size:13px;font-weight:700;cursor:pointer;';\n"
    "    var pickInput = document.createElement('input');\n"
    "    pickInput.type = 'date';\n"
    "    pickInput.style.cssText = 'position:absolute;left:-9999px;width:1px;height:1px;opacity:0;';\n"
    "    pickInput.addEventListener('change', function() {\n"
    "      if (pickInput.value) { highlightSameDay(pickInput.value, null); clearRdvBtn.style.display = 'block'; }\n"
    "      else { clearRdvHighlight(); clearRdvBtn.style.display = 'none'; }\n"
    "    });\n"
    "    pickBtn.addEventListener('click', function() {\n"
    "      if (typeof pickInput.showPicker === 'function') { try { pickInput.showPicker(); return; } catch(e) {} }\n"
    "      pickInput.focus(); pickInput.click();\n"
    "    });\n"
    "    pickWrap.appendChild(pickBtn);\n"
    "    pickWrap.appendChild(pickInput);\n"
    "    rdvSec.appendChild(pickWrap);\n",
    "    // input date cache, pilote par le menu RDV programmes et le clic sur une date\n"
    "    var pickInput = document.createElement('input');\n"
    "    pickInput.type = 'date';\n"
    "    pickInput.style.cssText = 'display:none;';\n"
    "    rdvSec.appendChild(pickInput);\n",
    "Suppression du bouton Choisir une date")

# 2. Toggle sur les sous-sections visites terrain.
must_replace(
    "        var titleV = document.createElement('div');\n"
    "        titleV.className = 'cmd-section-title';\n"
    "        titleV.style.color = vtype.color;\n"
    "        titleV.textContent = vtype.label + ' (' + vtype.count + ')';\n"
    "        secV.appendChild(titleV);\n"
    "\n"
    "        var ul = document.createElement('ul');\n"
    "        ul.className = 'prospect-list';",
    "        var titleV = document.createElement('div');\n"
    "        titleV.className = 'cmd-section-title';\n"
    "        titleV.style.color = vtype.color;\n"
    "        titleV.style.cursor = 'pointer';\n"
    "        titleV.style.userSelect = 'none';\n"
    "        var chevronV = document.createElement('span');\n"
    "        chevronV.textContent = '\\u25be ';\n"
    "        chevronV.style.cssText = 'display:inline-block;width:14px;';\n"
    "        titleV.appendChild(chevronV);\n"
    "        var titleVtxt = document.createElement('span');\n"
    "        titleVtxt.textContent = vtype.label + ' (' + vtype.count + ')';\n"
    "        titleV.appendChild(titleVtxt);\n"
    "        secV.appendChild(titleV);\n"
    "\n"
    "        var ul = document.createElement('ul');\n"
    "        ul.className = 'prospect-list';\n"
    "        var vKey = 'visite_' + vtype.key;\n"
    "        if (collapsedStatuts[vKey]) { ul.style.display = 'none'; chevronV.textContent = '\\u25b8 '; }\n"
    "        (function(k, ulRef, chevRef){\n"
    "          titleV.addEventListener('click', function() {\n"
    "            var hidden = ulRef.style.display === 'none';\n"
    "            ulRef.style.display = hidden ? '' : 'none';\n"
    "            chevRef.textContent = hidden ? '\\u25be ' : '\\u25b8 ';\n"
    "            collapsedStatuts[k] = !hidden;\n"
    "          });\n"
    "        })(vKey, ul, chevronV);",
    "Toggle sur visites terrain")

# Checks
for needle, label in [
    ("input date cache, pilote par le menu", "Bouton date supprime"),
    ("var vKey = 'visite_'", "Toggle visites terrain"),
    ("collapsedStatuts[k] = !hidden", "Memorisation toggle visites"),
]:
    print(("  [OK] " if needle in html else "  [X] MANQUANT : ") + label)
    if needle not in html: ok = False

# Verifier qu'on n'a pas casse les references a pickInput ailleurs (le menu l'utilise)
if "pickInput.value=dt" in html or "pickInput.value = dt" in html or "pickInput.value='';" in html or "pickInput.value=''" in html:
    print("  [OK] pickInput toujours reference par le menu/clear (coherent)")

if not ok:
    print("\\n[!] Patch incomplet. Fichier NON ecrase. (backup .bakpanel3)"); sys.exit(1)
if html == original:
    print("\\n[!] Aucune modification."); sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print("\\n[OK] Patch panel3 applique ->", SRC)
print("   Taille :", "{:,}".format(len(html)), "caracteres")
