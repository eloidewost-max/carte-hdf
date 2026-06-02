#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bak5"))
print("Backup cree :", SRC.with_suffix(".html.bak5"))

html = SRC.read_text(encoding="utf-8")
original = html
ok = True

def must_replace(old, new, label):
    global html, ok
    if old not in html:
        print("  [X] ANCRE ABSENTE :", label); ok = False; return
    html = html.replace(old, new, 1)
    print("  [OK]", label)

# 1. Noms communes dans calcRoute
must_replace(
    "      var fromName = layerByCode[fromCode] ? (layerByCode[fromCode].feature.properties.libgeo || fromCode) : fromCode;\n"
    "      var toName   = toFeature ? (toFeature.properties.libgeo || toCode) : toCode;",
    "      var fromName = (hdf[fromCode] && hdf[fromCode].n) ? hdf[fromCode].n : fromCode;\n"
    "      var toName   = (hdf[toCode] && hdf[toCode].n) ? hdf[toCode].n : toCode;",
    "Noms communes dans les trajets")

# 2. Nom commune dans la liste meme jour
must_replace(
    "        var name = layer ? (layer.feature.properties.libgeo || c) : c;",
    "        var name = (hdf[c] && hdf[c].n) ? hdf[c].n : c;",
    "Noms communes dans la liste meme jour")

# 3. Couleur surbrillance jaune -> violet
must_replace(
    "        layer.setStyle({ weight: 5, color: '#f97316', opacity: 1, fillColor: '#fbbf24', fillOpacity: 0.75 });",
    "        layer.setStyle({ weight: 5, color: '#7e22ce', opacity: 1, fillColor: '#a855f7', fillOpacity: 0.8 });",
    "Couleur surbrillance violette")

must_replace(
    "      + 'background:#f97316;color:#fff;padding:8px 20px;border-radius:10px;font-size:13px;'\n"
    "      + 'font-weight:700;z-index:9999;display:flex;align-items:center;gap:12px;'\n"
    "      + 'box-shadow:0 4px 16px rgba(249,115,22,0.4);';",
    "      + 'background:#a855f7;color:#fff;padding:8px 20px;border-radius:10px;font-size:13px;'\n"
    "      + 'font-weight:700;z-index:9999;display:flex;align-items:center;gap:12px;'\n"
    "      + 'box-shadow:0 4px 16px rgba(168,85,247,0.4);';",
    "Badge surbrillance violet")

must_replace(
    "        li.style.cssText = 'padding:5px 8px;border-radius:5px;cursor:pointer;font-size:12px;'\n"
    "          + 'color:#1e2025;background:rgba(249,115,22,0.08);margin-bottom:3px;'\n"
    "          + 'border:1px solid rgba(249,115,22,0.2);font-weight:500;';",
    "        li.style.cssText = 'padding:5px 8px;border-radius:5px;cursor:pointer;font-size:12px;'\n"
    "          + 'color:#1e2025;background:rgba(168,85,247,0.08);margin-bottom:3px;'\n"
    "          + 'border:1px solid rgba(168,85,247,0.25);font-weight:500;';",
    "Liste communes teinte violette")

must_replace(
    "        li.addEventListener('mouseenter', function() { this.style.background = 'rgba(249,115,22,0.18)'; });\n"
    "        li.addEventListener('mouseleave', function() { this.style.background = 'rgba(249,115,22,0.08)'; });",
    "        li.addEventListener('mouseenter', function() { this.style.background = 'rgba(168,85,247,0.18)'; });\n"
    "        li.addEventListener('mouseleave', function() { this.style.background = 'rgba(168,85,247,0.08)'; });",
    "Hover liste violet")

must_replace(
    "    rdvSameDayBtn.style.cssText = 'margin-top:10px;width:100%;padding:10px 14px;border-radius:7px;'\n"
    "      + 'font-size:13px;font-weight:700;cursor:pointer;display:none;'\n"
    "      + 'background:#fff7ed;border:2px solid #f97316;color:#c2410c;transition:all 0.15s;';",
    "    rdvSameDayBtn.style.cssText = 'margin-top:10px;width:100%;padding:10px 14px;border-radius:7px;'\n"
    "      + 'font-size:13px;font-weight:700;cursor:pointer;display:none;'\n"
    "      + 'background:#faf5ff;border:2px solid #a855f7;color:#7e22ce;transition:all 0.15s;';",
    "Bouton Voir rdv violet")

must_replace(
    "    rdvSameDayBtn.addEventListener('mouseenter', function() { this.style.background='#f97316'; this.style.color='#fff'; });\n"
    "    rdvSameDayBtn.addEventListener('mouseleave', function() { this.style.background='#fff7ed'; this.style.color='#c2410c'; });",
    "    rdvSameDayBtn.addEventListener('mouseenter', function() { this.style.background='#a855f7'; this.style.color='#fff'; });\n"
    "    rdvSameDayBtn.addEventListener('mouseleave', function() { this.style.background='#faf5ff'; this.style.color='#7e22ce'; });",
    "Hover bouton violet")

must_replace(
    "    rdvSec.style.cssText = 'border-top:2px solid rgba(249,115,22,0.25);padding-top:14px;margin-top:4px;';",
    "    rdvSec.style.cssText = 'border-top:2px solid rgba(168,85,247,0.25);padding-top:14px;margin-top:4px;';",
    "Separateur DATE RDV violet")

# 4. Selecteur date global dans top-bar
must_replace(
    '    <button onclick="window._syncFirebase()" style="padding:6px 12px;border:1px solid rgba(0,0,0,0.15);border-radius:6px;background:#fff;font-size:12px;cursor:pointer;color:#374151;margin-left:8px;">\u27f3 Sync</button>',
    '    <div style="display:flex;align-items:center;gap:6px;margin-left:8px;">\n'
    '      <span style="font-size:11px;color:#7e22ce;font-weight:700;white-space:nowrap;">\U0001f4c5 RDV du</span>\n'
    '      <input type="date" id="global-rdv-date" style="padding:5px 8px;border:1px solid #a855f7;border-radius:6px;font-size:12px;color:#374151;cursor:pointer;">\n'
    '      <button id="global-rdv-clear" style="padding:5px 8px;border:1px solid rgba(0,0,0,0.15);border-radius:6px;background:#fff;font-size:11px;cursor:pointer;color:#9ca3af;display:none;">\u2715</button>\n'
    '    </div>\n'
    '    <button onclick="window._syncFirebase()" style="padding:6px 12px;border:1px solid rgba(0,0,0,0.15);border-radius:6px;background:#fff;font-size:12px;cursor:pointer;color:#374151;margin-left:8px;">\u27f3 Sync</button>',
    "Selecteur date global (HTML top-bar)")

# 5. Logique du selecteur global
must_replace(
    "  }).addTo(map);\n  communesGeo = null;",
    "  }).addTo(map);\n  communesGeo = null;\n\n"
    "  // Selecteur de date global (top-bar)\n"
    "  (function initGlobalRdvDate() {\n"
    "    var input = document.getElementById('global-rdv-date');\n"
    "    var clearBtn = document.getElementById('global-rdv-clear');\n"
    "    if (!input) return;\n"
    "    input.addEventListener('change', function() {\n"
    "      if (input.value) {\n"
    "        highlightSameDay(input.value, null);\n"
    "        clearBtn.style.display = 'inline-block';\n"
    "      } else {\n"
    "        clearRdvHighlight();\n"
    "        clearBtn.style.display = 'none';\n"
    "      }\n"
    "    });\n"
    "    clearBtn.addEventListener('click', function() {\n"
    "      input.value = '';\n"
    "      clearRdvHighlight();\n"
    "      clearBtn.style.display = 'none';\n"
    "    });\n"
    "  })();",
    "Logique selecteur date global (JS)")

print()
for needle, label in [
    ("hdf[fromCode].n", "Noms trajets"),
    ("hdf[c].n", "Noms liste"),
    ("fillColor: '#a855f7'", "Surbrillance violette"),
    ("global-rdv-date", "Input date global"),
    ("initGlobalRdvDate", "Logique date globale"),
]:
    print(("  [OK] " if needle in html else "  [X] MANQUANT : ") + label)
    if needle not in html: ok = False

if not ok:
    print("\n[!] Patch incomplet. Fichier NON ecrase. (backup .bak5 dispo)"); sys.exit(1)
if html == original:
    print("\n[!] Aucune modification."); sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print("\n[OK] Patch 3 applique ->", SRC)
print("   Taille :", "{:,}".format(len(html)), "caracteres")
