#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bak7"))
print("Backup cree :", SRC.with_suffix(".html.bak7"))

html = SRC.read_text(encoding="utf-8")
original = html
ok = True

def must_replace(old, new, label):
    global html, ok
    if old not in html:
        print("  [X] ANCRE ABSENTE :", label); ok = False; return
    if html.count(old) > 1:
        print("  [!] ANCRE MULTIPLE (", html.count(old), ") :", label, "- on prend la 1ere")
    html = html.replace(old, new, 1)
    print("  [OK]", label)

# mouseover : ne pas re-styler si la commune est estompee (pas de rdv au jour actif)
must_replace(
    """        mouseover: function(e) {
          showInfo(feature);
          positionInfo(e.originalEvent);
          e.target.setStyle({ weight: 2, color: '#fff', opacity: 1 });
          e.target.bringToFront();
        },""",
    """        mouseover: function(e) {
          showInfo(feature);
          positionInfo(e.originalEvent);
          // Si une date est active et que cette commune n'a pas de rdv ce jour, garder l'estompage
          if (rdvHighlightDate && communeRdv[code] !== rdvHighlightDate) {
            return;
          }
          e.target.setStyle({ weight: 2, color: '#fff', opacity: 1 });
          e.target.bringToFront();
        },""",
    "mouseover respecte l'estompage")

# mouseout : si estompage actif et commune sans rdv ce jour, re-estomper au lieu de resetStyle
must_replace(
    """     mouseout: function(e) {
          infoPanel.style.display = 'none';
          if (window._selectedLayer !== e.target) geoLayer.resetStyle(e.target);
        },""",
    """     mouseout: function(e) {
          infoPanel.style.display = 'none';
          if (window._selectedLayer === e.target) return;
          // Si une date est active et que cette commune n'a pas de rdv ce jour, re-estomper
          if (rdvHighlightDate && communeRdv[code] !== rdvHighlightDate) {
            e.target.setStyle({ fillOpacity: 0.08, opacity: 0.15 });
            return;
          }
          geoLayer.resetStyle(e.target);
        },""",
    "mouseout respecte l'estompage")

# Checks
for needle, label in [
    ("if (rdvHighlightDate && communeRdv[code] !== rdvHighlightDate) {\n            return;", "Garde estompage au survol"),
    ("e.target.setStyle({ fillOpacity: 0.08, opacity: 0.15 });", "Re-estompe a la sortie"),
]:
    print(("  [OK] " if needle in html else "  [X] MANQUANT : ") + label)
    if needle not in html: ok = False

if not ok:
    print("\\n[!] Patch incomplet. Fichier NON ecrase. (backup .bak7 dispo)"); sys.exit(1)
if html == original:
    print("\\n[!] Aucune modification."); sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print("\\n[OK] Patch 5 applique ->", SRC)
print("   Taille :", "{:,}".format(len(html)), "caracteres")
