#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bak6"))
print("Backup cree :", SRC.with_suffix(".html.bak6"))

html = SRC.read_text(encoding="utf-8")
original = html
ok = True

# Remplacer le bloc clearRdvHighlight + highlightSameDay complet.
# Ancre debut : "  function clearRdvHighlight() {"
# Ancre fin    : "  window.clearRdvHighlight = clearRdvHighlight;"
start_marker = "  function clearRdvHighlight() {"
end_marker = "  window.clearRdvHighlight = clearRdvHighlight;"
si = html.find(start_marker)
ei = html.find(end_marker)
if si == -1 or ei == -1:
    print("  [X] ANCRE ABSENTE : bloc fonctions surbrillance"); sys.exit(1)
ei_end = ei + len(end_marker)

NEW_BLOCK = """  function clearRdvHighlight() {
    rdvHighlightDate = null;
    // Restaure le style normal de TOUTES les communes estompees
    rdvHighlightLayers.forEach(function(info) {
      if (info.layer) geoLayer.resetStyle(info.layer);
      if (info.elem) info.elem.classList.remove('rdv-highlight-pulse');
    });
    rdvHighlightLayers = [];
    var badge = document.getElementById('rdv-highlight-badge');
    if (badge) badge.remove();
  }

  function highlightSameDay(dateVal, listContainer) {
    clearRdvHighlight();
    rdvHighlightDate = dateVal;
    var codes = Object.keys(communeRdv).filter(function(c) { return communeRdv[c] === dateVal; });
    var codeSet = {};
    codes.forEach(function(c) { codeSet[c] = true; });

    // Estompe toutes les communes SANS rdv ce jour-la (les communes du jour restent intactes)
    var bounds = null;
    Object.keys(layerByCode).forEach(function(c) {
      var layer = layerByCode[c];
      if (!layer) return;
      if (codeSet[c]) {
        // Commune du jour : on ne touche pas a son style, on l'ajoute juste au cadrage
        rdvHighlightLayers.push({ layer: layer, elem: null });
        if (bounds) { bounds.extend(layer.getBounds()); } else { bounds = L.latLngBounds(layer.getBounds()); }
      } else {
        // Autre commune : estompee
        layer.setStyle({ fillOpacity: 0.08, opacity: 0.15 });
        rdvHighlightLayers.push({ layer: layer, elem: null });
      }
    });

    // Zoom auto sur l'ensemble des communes du jour
    if (bounds && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [60, 60], maxZoom: 12 });
    }

    var badge = document.createElement('div');
    badge.id = 'rdv-highlight-badge';
    badge.style.cssText = 'position:fixed;top:52px;left:50%;transform:translateX(-50%);'
      + 'background:#a855f7;color:#fff;padding:8px 20px;border-radius:10px;font-size:13px;'
      + 'font-weight:700;z-index:9999;display:flex;align-items:center;gap:12px;'
      + 'box-shadow:0 4px 16px rgba(168,85,247,0.4);';
    badge.innerHTML = '\\ud83d\\udcc5 ' + codes.length + ' rdv le ' + formatDate(dateVal)
      + ' <button onclick="clearRdvHighlight()" style="background:rgba(255,255,255,0.25);border:none;color:#fff;'
      + 'cursor:pointer;font-size:12px;padding:3px 8px;border-radius:5px;">\\u2715 Fermer</button>';
    document.body.appendChild(badge);

    if (listContainer) {
      listContainer.innerHTML = '';
      var communes = [];
      codes.forEach(function(c) {
        var name = (hdf[c] && hdf[c].n) ? hdf[c].n : c;
        communes.push({ code: c, name: name });
      });
      communes.sort(function(a, b) { return a.name.localeCompare(b.name); });
      communes.forEach(function(com) {
        var li = document.createElement('div');
        li.style.cssText = 'padding:5px 8px;border-radius:5px;cursor:pointer;font-size:12px;'
          + 'color:#1e2025;background:rgba(168,85,247,0.08);margin-bottom:3px;'
          + 'border:1px solid rgba(168,85,247,0.25);font-weight:500;';
        li.textContent = '\\ud83d\\udccd ' + com.name;
        li.addEventListener('mouseenter', function() { this.style.background = 'rgba(168,85,247,0.18)'; });
        li.addEventListener('mouseleave', function() { this.style.background = 'rgba(168,85,247,0.08)'; });
        li.addEventListener('click', function() {
          var layer = layerByCode[com.code];
          if (layer) { map.fitBounds(layer.getBounds(), { maxZoom: 11 }); openDetail(com.code); }
        });
        listContainer.appendChild(li);
      });
    }
  }
  window.clearRdvHighlight = clearRdvHighlight;"""

html = html[:si] + NEW_BLOCK + html[ei_end:]
print("  [OK] Bloc surbrillance reecrit (estompage + zoom, zero violet)")

# Checks
for needle, label in [
    ("fillOpacity: 0.08, opacity: 0.15", "Estompage des autres communes"),
    ("map.fitBounds(bounds, { padding: [60, 60]", "Zoom auto sur le groupe"),
    ("L.latLngBounds", "Calcul des bounds"),
]:
    print(("  [OK] " if needle in html else "  [X] MANQUANT : ") + label)
    if needle not in html: ok = False

# Verifier qu'on n'a plus le repeint violet des communes du jour
if "fillColor: '#a855f7', fillOpacity: 0.8" in html:
    print("  [X] Le repeint violet des communes du jour est encore present"); ok = False
else:
    print("  [OK] Plus de repeint violet sur les communes du jour")

if not ok:
    print("\\n[!] Patch incomplet. Fichier NON ecrase. (backup .bak6 dispo)"); sys.exit(1)
if html == original:
    print("\\n[!] Aucune modification."); sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print("\\n[OK] Patch 4 applique ->", SRC)
print("   Taille :", "{:,}".format(len(html)), "caracteres")
