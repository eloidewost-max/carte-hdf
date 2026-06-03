#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bakbtn"))
print("Backup cree :", SRC.with_suffix(".html.bakbtn"))

html = SRC.read_text(encoding="utf-8")
original = html
ok = True

def must_replace(old, new, label):
    global html, ok
    if old not in html:
        print("  [X] ANCRE ABSENTE :", label); ok = False; return
    html = html.replace(old, new, 1)
    print("  [OK]", label)

# 1. Remplacer le bloc span+input+clear par deux gros boutons.
old_block = (
    '      <span style="font-size:13px;color:#7e22ce;font-weight:700;white-space:nowrap;">\U0001f4c5 RDV du</span>\n'
    '      <input type="date" id="global-rdv-date" style="padding:8px 10px;border:2px solid #a855f7;border-radius:8px;font-size:14px;font-weight:600;color:#7e22ce;cursor:pointer;background:#faf5ff;">\n'
    '      <button id="global-rdv-clear" style="padding:8px 12px;border:1px solid rgba(0,0,0,0.15);border-radius:8px;background:#fff;font-size:14px;font-weight:700;cursor:pointer;color:#9ca3af;display:none;">\u2715</button>'
)

new_block = (
    '      <label id="global-rdv-btn" style="position:relative;display:inline-flex;align-items:center;gap:6px;padding:9px 16px;border-radius:9px;background:#7e22ce;color:#fff;font-size:14px;font-weight:700;cursor:pointer;white-space:nowrap;box-shadow:0 2px 6px rgba(126,34,206,0.35);">\n'
    '        \U0001f4c5 Choisir une date\n'
    '        <input type="date" id="global-rdv-date" style="position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;">\n'
    '      </label>\n'
    '      <div style="position:relative;display:inline-block;">\n'
    '        <button id="global-rdv-list-btn" style="padding:9px 16px;border-radius:9px;border:2px solid #a855f7;background:#faf5ff;color:#7e22ce;font-size:14px;font-weight:700;cursor:pointer;white-space:nowrap;">\U0001f4cb RDV programm\u00e9s \u25be</button>\n'
    '        <div id="global-rdv-list-menu" style="display:none;position:absolute;top:110%;left:0;z-index:99999;background:#fff;border:1px solid rgba(0,0,0,0.15);border-radius:10px;box-shadow:0 6px 24px rgba(0,0,0,0.18);min-width:230px;max-height:340px;overflow-y:auto;padding:6px;"></div>\n'
    '      </div>\n'
    '      <button id="global-rdv-clear" style="padding:9px 14px;border:1px solid rgba(0,0,0,0.15);border-radius:9px;background:#fff;font-size:14px;font-weight:700;cursor:pointer;color:#9ca3af;display:none;">\u2715</button>'
)
must_replace(old_block, new_block, "Remplacement par 2 gros boutons")

# 2. Etendre le initGlobalRdvDate pour gerer le menu deroulant des dates.
old_init = (
    "    clearBtn.addEventListener('click', function() {\n"
    "      input.value = '';\n"
    "      clearRdvHighlight();\n"
    "      clearBtn.style.display = 'none';\n"
    "    });"
)
new_init = (
    "    clearBtn.addEventListener('click', function() {\n"
    "      input.value = '';\n"
    "      clearRdvHighlight();\n"
    "      clearBtn.style.display = 'none';\n"
    "    });\n"
    "    // --- Menu deroulant des dates de RDV programmes ---\n"
    "    var listBtn = document.getElementById('global-rdv-list-btn');\n"
    "    var listMenu = document.getElementById('global-rdv-list-menu');\n"
    "    function frDate(iso) { var p = iso.split('-'); return p[2] + '/' + p[1] + '/' + p[0]; }\n"
    "    function buildRdvMenu() {\n"
    "      listMenu.innerHTML = '';\n"
    "      var counts = {};\n"
    "      Object.keys(communeRdv).forEach(function(c) { var dt = communeRdv[c]; if (dt) counts[dt] = (counts[dt]||0)+1; });\n"
    "      var dates = Object.keys(counts).sort();\n"
    "      if (dates.length === 0) {\n"
    "        var empty = document.createElement('div');\n"
    "        empty.style.cssText = 'padding:12px;color:#9ca3af;font-size:13px;text-align:center;';\n"
    "        empty.textContent = 'Aucun RDV programme';\n"
    "        listMenu.appendChild(empty);\n"
    "        return;\n"
    "      }\n"
    "      dates.forEach(function(dt) {\n"
    "        var item = document.createElement('button');\n"
    "        item.style.cssText = 'display:flex;justify-content:space-between;align-items:center;gap:10px;width:100%;padding:9px 12px;border:none;background:transparent;border-radius:7px;cursor:pointer;font-size:13px;font-weight:600;color:#374151;text-align:left;';\n"
    "        item.onmouseover = function() { item.style.background = '#f3e8ff'; };\n"
    "        item.onmouseout = function() { item.style.background = 'transparent'; };\n"
    "        item.innerHTML = '<span>\\ud83d\\udcc5 ' + frDate(dt) + '</span>'\n"
    "          + '<span style=\"background:#7e22ce;color:#fff;border-radius:10px;padding:2px 9px;font-size:12px;\">' + counts[dt] + '</span>';\n"
    "        item.addEventListener('click', function() {\n"
    "          input.value = dt;\n"
    "          highlightSameDay(dt, null);\n"
    "          clearBtn.style.display = 'inline-block';\n"
    "          listMenu.style.display = 'none';\n"
    "        });\n"
    "        listMenu.appendChild(item);\n"
    "      });\n"
    "    }\n"
    "    listBtn.addEventListener('click', function(e) {\n"
    "      e.stopPropagation();\n"
    "      if (listMenu.style.display === 'block') { listMenu.style.display = 'none'; return; }\n"
    "      buildRdvMenu();\n"
    "      listMenu.style.display = 'block';\n"
    "    });\n"
    "    document.addEventListener('click', function(e) {\n"
    "      if (!listMenu.contains(e.target) && e.target !== listBtn) listMenu.style.display = 'none';\n"
    "    });"
)
must_replace(old_init, new_init, "Logique menu deroulant des dates")

# Checks
for needle, label in [
    ("global-rdv-btn", "Gros bouton date"),
    ("global-rdv-list-btn", "Bouton RDV programmes"),
    ("buildRdvMenu", "Fonction menu"),
    ("Choisir une date", "Libelle bouton date"),
]:
    print(("  [OK] " if needle in html else "  [X] MANQUANT : ") + label)
    if needle not in html: ok = False

if not ok:
    print("\\n[!] Patch incomplet. Fichier NON ecrase. (backup .bakbtn)"); sys.exit(1)
if html == original:
    print("\\n[!] Aucune modification."); sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print("\\n[OK] Patch boutons applique ->", SRC)
print("   Taille :", "{:,}".format(len(html)), "caracteres")
