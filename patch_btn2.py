#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bakbtn2"))
print("Backup cree :", SRC.with_suffix(".html.bakbtn2"))

html = SRC.read_text(encoding="utf-8")
original = html
ok = True

def must_replace(old, new, label):
    global html, ok
    if old not in html:
        print("  [X] ANCRE ABSENTE :", label); ok = False; return
    html = html.replace(old, new, 1)
    print("  [OK]", label)

# 1. Reecrire le bloc HTML des boutons : bouton date = vrai bouton + input cache (pas par-dessus)
old_html = (
    '      <label id="global-rdv-btn" style="position:relative;display:inline-flex;align-items:center;gap:6px;padding:9px 16px;border-radius:9px;background:#7e22ce;color:#fff;font-size:14px;font-weight:700;cursor:pointer;white-space:nowrap;box-shadow:0 2px 6px rgba(126,34,206,0.35);">\n'
    '        \U0001f4c5 Choisir une date\n'
    '        <input type="date" id="global-rdv-date" style="position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;">\n'
    '      </label>'
)
new_html = (
    '      <button type="button" id="global-rdv-btn" style="display:inline-flex;align-items:center;gap:6px;padding:9px 16px;border-radius:9px;border:none;background:#7e22ce;color:#fff;font-size:14px;font-weight:700;cursor:pointer;white-space:nowrap;box-shadow:0 2px 6px rgba(126,34,206,0.35);">\U0001f4c5 Choisir une date</button>\n'
    '      <input type="date" id="global-rdv-date" style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0;">'
)
must_replace(old_html, new_html, "Bouton date = vrai bouton + input cache")

# 2. Cote JS : faire ouvrir le calendrier au clic du bouton date.
#    On insere au tout debut de initGlobalRdvDate, juste apres "if (!input) return;"
must_replace(
    "    var input = document.getElementById('global-rdv-date');\n"
    "    var clearBtn = document.getElementById('global-rdv-clear');\n"
    "    if (!input) return;",
    "    var input = document.getElementById('global-rdv-date');\n"
    "    var clearBtn = document.getElementById('global-rdv-clear');\n"
    "    var dateBtn = document.getElementById('global-rdv-btn');\n"
    "    if (!input) return;\n"
    "    if (dateBtn) dateBtn.addEventListener('click', function() {\n"
    "      if (typeof input.showPicker === 'function') { try { input.showPicker(); return; } catch(e) {} }\n"
    "      input.focus(); input.click();\n"
    "    });",
    "Clic bouton date -> ouvre calendrier")

# 3. Retirer le listener global document.click qui pouvait poser souci -> version ciblee
must_replace(
    "    document.addEventListener('click', function(e) {\n"
    "      if (!listMenu.contains(e.target) && e.target !== listBtn) listMenu.style.display = 'none';\n"
    "    });",
    "    document.addEventListener('click', function(e) {\n"
    "      if (listMenu.style.display !== 'block') return;\n"
    "      if (!listMenu.contains(e.target) && !listBtn.contains(e.target)) listMenu.style.display = 'none';\n"
    "    });",
    "Listener fermeture menu plus sur")

# 4. Bug survol : ne pas ecraser la bordure violette des communes du jour.
#    Dans mouseover, si la commune A un rdv ce jour (== rdvHighlightDate), ne pas resetStyle.
must_replace(
    "          if (rdvHighlightDate && communeRdv[code] !== rdvHighlightDate) {\n"
    "            return;\n"
    "          }\n"
    "          e.target.setStyle({ weight: 2, color: '#fff', opacity: 1 });\n"
    "          e.target.bringToFront();",
    "          if (rdvHighlightDate && communeRdv[code] !== rdvHighlightDate) {\n"
    "            return;\n"
    "          }\n"
    "          if (rdvHighlightDate && communeRdv[code] === rdvHighlightDate) {\n"
    "            e.target.bringToFront();\n"
    "            return;\n"
    "          }\n"
    "          e.target.setStyle({ weight: 2, color: '#fff', opacity: 1 });\n"
    "          e.target.bringToFront();",
    "Survol ne casse plus la bordure violette (mouseover)")

# 5. Idem dans mouseout : si commune du jour, re-appliquer la bordure violette au lieu de resetStyle.
must_replace(
    "          if (rdvHighlightDate && communeRdv[code] !== rdvHighlightDate) {\n"
    "            e.target.setStyle({ fillOpacity: 0.08, opacity: 0.15 });\n"
    "            return;\n"
    "          }\n"
    "          geoLayer.resetStyle(e.target);",
    "          if (rdvHighlightDate && communeRdv[code] !== rdvHighlightDate) {\n"
    "            e.target.setStyle({ fillOpacity: 0.08, opacity: 0.15 });\n"
    "            return;\n"
    "          }\n"
    "          if (rdvHighlightDate && communeRdv[code] === rdvHighlightDate) {\n"
    "            e.target.setStyle({ weight: 4, color: '#7e22ce', opacity: 1 });\n"
    "            return;\n"
    "          }\n"
    "          geoLayer.resetStyle(e.target);",
    "Survol re-applique bordure violette (mouseout)")

# Checks
for needle, label in [
    ('type="button" id="global-rdv-btn"', "Bouton date type button"),
    ("showPicker", "Logique ouverture calendrier"),
    ("weight: 4, color: '#7e22ce'", "Bordure violette preservee au survol"),
]:
    print(("  [OK] " if needle in html else "  [X] MANQUANT : ") + label)
    if needle not in html: ok = False

if not ok:
    print("\\n[!] Patch incomplet. Fichier NON ecrase. (backup .bakbtn2)"); sys.exit(1)
if html == original:
    print("\\n[!] Aucune modification."); sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print("\\n[OK] Patch boutons v2 applique ->", SRC)
print("   Taille :", "{:,}".format(len(html)), "caracteres")
