#!/usr/bin/env python3
"""
Patch 2 v2 — basé sur l'état réel du fichier (patch 1 déjà appliqué).
Ancres vérifiées sur le contenu exact.
Idempotent et sûr : refuse d'écrire si tous les checks ne passent pas.
"""
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable →", SRC)
    sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bak4"))
print("Backup créé :", SRC.with_suffix(".html.bak4"))

html = SRC.read_text(encoding="utf-8")
original = html

def must_replace(old, new, label):
    """Remplace et signale si l'ancre est absente."""
    global html
    if old not in html:
        print(f"  ⚠️  ANCRE ABSENTE : {label}")
        return False
    html = html.replace(old, new, 1)
    return True

ok = True

# ─────────────────────────────────────────────────────────────────────────────
# 1. CSS pulse
# ─────────────────────────────────────────────────────────────────────────────
ok &= must_replace(
    "* { margin: 0; padding: 0; box-sizing: border-box; }",
    """* { margin: 0; padding: 0; box-sizing: border-box; }
@keyframes rdv-pulse { 0% { opacity: 1; } 50% { opacity: 0.45; } 100% { opacity: 1; } }
.rdv-highlight-pulse { animation: rdv-pulse 1.2s ease-in-out infinite; }""",
    "CSS pulse"
)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Variables multitrajets
# ─────────────────────────────────────────────────────────────────────────────
ok &= must_replace(
    '  var rdvHighlightDate = null; // date surbrillance mode C',
    """  var rdvHighlightDate = null; // date surbrillance mode C
  var routeSegments = []; // segments tracés
  var routeLastCode = null; // dernière commune pour chaîner les trajets""",
    "Variables multitrajets"
)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Click handler — multitrajets + déselection
# ─────────────────────────────────────────────────────────────────────────────
OLD_CLICK = """        click: function(e) {
          // CMD+Clic = calcul trajet depuis la commune précédemment sélectionnée
          if ((e.originalEvent.metaKey || e.originalEvent.ctrlKey) && window._routeFromCode && window._routeFromCode !== code) {
            calcRoute(window._routeFromCode, code, feature);
            return;
          }
          map.fitBounds(e.target.getBounds(), { maxZoom: 11 });
          if (window._selectedLayer) geoLayer.resetStyle(window._selectedLayer);
          window._selectedLayer = e.target;
          e.target.setStyle({ weight: 3, color: '#ffff00', opacity: 1 });
          window._routeFromCode = code; // mémorise pour CMD+Clic suivant
          openDetail(code);
        }"""
NEW_CLICK = """        click: function(e) {
          if (e.originalEvent.metaKey || e.originalEvent.ctrlKey) {
            if (routeLastCode === code) {
              clearAllRoutes(); routeLastCode = null;
              routeBanner.style.display = 'none';
              return;
            }
            if (routeLastCode && routeLastCode !== code) {
              calcRoute(routeLastCode, code, feature);
              routeLastCode = code;
              return;
            }
          }
          map.fitBounds(e.target.getBounds(), { maxZoom: 11 });
          if (window._selectedLayer) geoLayer.resetStyle(window._selectedLayer);
          window._selectedLayer = e.target;
          e.target.setStyle({ weight: 3, color: '#ffff00', opacity: 1 });
          routeLastCode = code;
          openDetail(code);
        }"""
ok &= must_replace(OLD_CLICK, NEW_CLICK, "Click handler multitrajets")

# ─────────────────────────────────────────────────────────────────────────────
# 4. Bloc fonctions utilitaires — remplacer l'ancienne version par la nouvelle
#    Ancre de début : "  // ─── Formatage date FR"
#    Ancre de fin : "  window.clearRdvHighlight = clearRdvHighlight;"
#    On remplace tout le bloc entre les deux (inclus).
# ─────────────────────────────────────────────────────────────────────────────
start_marker = "  // ─── Formatage date FR"
end_marker = "  window.clearRdvHighlight = clearRdvHighlight;"
si = html.find(start_marker)
ei = html.find(end_marker)
if si == -1 or ei == -1:
    print("  ⚠️  ANCRE ABSENTE : bloc fonctions utilitaires")
    ok = False
else:
    ei_end = ei + len(end_marker)
    NEW_UTILS = """  // ─── Formatage date FR ────────────────────────────────────────────────────
  function formatDate(isoStr) {
    if (!isoStr) return '';
    var p = isoStr.split('-');
    return p[2] + '/' + p[1] + '/' + p[0];
  }

  // ─── Bannière trajet OSRM (multi-segments) ────────────────────────────────
  var routeBanner = document.createElement('div');
  routeBanner.id = 'route-banner';
  routeBanner.style.cssText = 'position:fixed;bottom:40px;left:50%;transform:translateX(-50%);'
    + 'background:#1e2025;color:#fff;padding:10px 18px;border-radius:10px;font-size:13px;'
    + 'font-weight:600;z-index:9999;display:none;box-shadow:0 4px 16px rgba(0,0,0,0.3);'
    + 'align-items:center;gap:12px;max-width:90vw;flex-wrap:wrap;';
  var routeText = document.createElement('span');
  var routeClose = document.createElement('button');
  routeClose.textContent = '\\u2715 Effacer';
  routeClose.style.cssText = 'background:rgba(255,255,255,0.15);border:none;color:#fff;'
    + 'cursor:pointer;font-size:12px;padding:3px 8px;border-radius:5px;white-space:nowrap;';
  routeClose.onclick = function() { clearAllRoutes(); routeBanner.style.display = 'none'; routeLastCode = null; };
  routeBanner.appendChild(routeText);
  routeBanner.appendChild(routeClose);
  document.body.appendChild(routeBanner);

  var cmdHint = document.createElement('div');
  cmdHint.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);'
    + 'background:#f97316;color:#fff;padding:6px 14px;border-radius:8px;font-size:11px;'
    + 'font-weight:600;z-index:9999;display:none;pointer-events:none;';
  cmdHint.textContent = '\\u2318 CMD+Clic pour ajouter un trajet \\u00b7 CMD+Clic sur la m\\u00eame commune pour effacer';
  document.body.appendChild(cmdHint);

  document.addEventListener('keydown', function(e) { if (e.metaKey || e.ctrlKey) cmdHint.style.display = 'block'; });
  document.addEventListener('keyup', function(e) { if (!e.metaKey && !e.ctrlKey) cmdHint.style.display = 'none'; });

  function getCentroid(code) {
    var layer = layerByCode[code];
    if (!layer) return null;
    var b = layer.getBounds();
    return [b.getCenter().lat, b.getCenter().lng];
  }

  function clearAllRoutes() {
    routeSegments.forEach(function(seg) { if (seg.polyline) map.removeLayer(seg.polyline); });
    routeSegments = [];
  }

  function decodePolyline(str) {
    var index = 0, lat = 0, lng = 0, coordinates = [];
    while (index < str.length) {
      var b, shift = 0, result = 0;
      do { b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
      var dlat = (result & 1) ? ~(result >> 1) : (result >> 1); lat += dlat;
      shift = 0; result = 0;
      do { b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
      var dlng = (result & 1) ? ~(result >> 1) : (result >> 1); lng += dlng;
      coordinates.push([lat / 1e5, lng / 1e5]);
    }
    return coordinates;
  }

  async function calcRoute(fromCode, toCode, toFeature) {
    var fromLatLng = getCentroid(fromCode);
    var toLatLng   = getCentroid(toCode);
    if (!fromLatLng || !toLatLng) { alert("Impossible de localiser une commune."); return; }
    routeText.textContent = '\\u23f3 Calcul du trajet\\u2026';
    routeBanner.style.display = 'flex';
    var url = 'https://router.project-osrm.org/route/v1/driving/'
      + fromLatLng[1] + ',' + fromLatLng[0] + ';' + toLatLng[1] + ',' + toLatLng[0]
      + '?overview=full&geometries=polyline';
    try {
      var resp = await fetch(url);
      var data = await resp.json();
      if (data.code !== 'Ok') throw new Error('OSRM error');
      var route = data.routes[0];
      var leg = route.legs[0];
      var dist = (leg.distance / 1000).toFixed(0) + ' km';
      var secs = leg.duration;
      var h = Math.floor(secs / 3600);
      var m = Math.round((secs % 3600) / 60);
      var dur = h > 0 ? h + 'h' + String(m).padStart(2,'0') : m + ' min';
      var fromName = layerByCode[fromCode] ? (layerByCode[fromCode].feature.properties.libgeo || fromCode) : fromCode;
      var toName   = toFeature ? (toFeature.properties.libgeo || toCode) : toCode;
      var coords = decodePolyline(route.geometry);
      var poly = L.polyline(coords, { color: '#ef4444', weight: 4, opacity: 0.85 }).addTo(map);
      var midPoint = coords[Math.floor(coords.length / 2)];
      L.popup({ closeButton: false })
        .setLatLng(midPoint)
        .setContent('<div style="font-size:12px;font-weight:700;color:#ef4444;">\\ud83d\\ude97 ' + dur + ' \\u00b7 ' + dist + '</div>')
        .openOn(map);
      routeSegments.push({ polyline: poly, dur: dur, dist: dist, fromName: fromName, toName: toName });
      updateRouteBanner();
    } catch(err) {
      routeText.textContent = '\\u26a0\\ufe0f Erreur calcul trajet (r\\u00e9seau ?)';
    }
  }

  function updateRouteBanner() {
    if (routeSegments.length === 0) { routeBanner.style.display = 'none'; return; }
    var parts = routeSegments.map(function(seg) {
      return '\\ud83d\\ude97 ' + seg.fromName + ' \\u2192 ' + seg.toName + ' : ' + seg.dur + ' (' + seg.dist + ')';
    });
    routeText.textContent = parts.join('   |   ');
    routeBanner.style.display = 'flex';
  }

  // ─── Surbrillance même date — pulse + bordure épaisse ─────────────────────
  var rdvHighlightLayers = [];

  function clearRdvHighlight() {
    rdvHighlightDate = null;
    rdvHighlightLayers.forEach(function(info) {
      geoLayer.resetStyle(info.layer);
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
    codes.forEach(function(c) {
      var layer = layerByCode[c];
      if (layer) {
        layer.setStyle({ weight: 5, color: '#f97316', opacity: 1, fillColor: '#fbbf24', fillOpacity: 0.75 });
        var elem = layer.getElement ? layer.getElement() : null;
        if (elem) elem.classList.add('rdv-highlight-pulse');
        rdvHighlightLayers.push({ layer: layer, elem: elem });
      }
    });
    var badge = document.createElement('div');
    badge.id = 'rdv-highlight-badge';
    badge.style.cssText = 'position:fixed;top:52px;left:50%;transform:translateX(-50%);'
      + 'background:#f97316;color:#fff;padding:8px 20px;border-radius:10px;font-size:13px;'
      + 'font-weight:700;z-index:9999;display:flex;align-items:center;gap:12px;'
      + 'box-shadow:0 4px 16px rgba(249,115,22,0.4);';
    badge.innerHTML = '\\ud83d\\udcc5 ' + codes.length + ' rdv le ' + formatDate(dateVal)
      + ' <button onclick="clearRdvHighlight()" style="background:rgba(255,255,255,0.25);border:none;color:#fff;'
      + 'cursor:pointer;font-size:12px;padding:3px 8px;border-radius:5px;">\\u2715 Fermer</button>';
    document.body.appendChild(badge);
    if (listContainer) {
      listContainer.innerHTML = '';
      var communes = [];
      codes.forEach(function(c) {
        var layer = layerByCode[c];
        var name = layer ? (layer.feature.properties.libgeo || c) : c;
        communes.push({ code: c, name: name });
      });
      communes.sort(function(a, b) { return a.name.localeCompare(b.name); });
      communes.forEach(function(com) {
        var li = document.createElement('div');
        li.style.cssText = 'padding:5px 8px;border-radius:5px;cursor:pointer;font-size:12px;'
          + 'color:#1e2025;background:rgba(249,115,22,0.08);margin-bottom:3px;'
          + 'border:1px solid rgba(249,115,22,0.2);font-weight:500;';
        li.textContent = '\\ud83d\\udccd ' + com.name;
        li.addEventListener('mouseenter', function() { this.style.background = 'rgba(249,115,22,0.18)'; });
        li.addEventListener('mouseleave', function() { this.style.background = 'rgba(249,115,22,0.08)'; });
        li.addEventListener('click', function() {
          var layer = layerByCode[com.code];
          if (layer) { map.fitBounds(layer.getBounds(), { maxZoom: 11 }); openDetail(com.code); }
        });
        listContainer.appendChild(li);
      });
    }
  }
  window.clearRdvHighlight = clearRdvHighlight;"""
    html = html[:si] + NEW_UTILS + html[ei_end:]

# ─────────────────────────────────────────────────────────────────────────────
# 5. Supprimer l'ancienne section DATE RDV de sa position (après VISITE TERRAIN)
#    Ancre EXACTE du fichier réel : de "    // ── Date RDV ──" jusqu'à
#    "    content.appendChild(rdvSec);\n" qui précède "    // ── Statut commercial ──"
# ─────────────────────────────────────────────────────────────────────────────
rdv_start = html.find("    // ── Date RDV ──")
# le content.appendChild(rdvSec) qui suit cette section
if rdv_start != -1:
    rdv_end = html.find("    content.appendChild(rdvSec);", rdv_start)
    if rdv_end != -1:
        rdv_end_full = rdv_end + len("    content.appendChild(rdvSec);\n")
        html = html[:rdv_start] + html[rdv_end_full:]
        print("  ✅ Ancienne section DATE RDV retirée de sa position")
    else:
        print("  ⚠️  Fin ancienne section DATE RDV introuvable")
        ok = False
else:
    print("  ⚠️  Ancienne section DATE RDV introuvable")
    ok = False

# ─────────────────────────────────────────────────────────────────────────────
# 6. Ajouter DATE RDV (grand format + liste) en bas, avant panel.classList.add
#    On cible le DERNIER content.appendChild(ecoSec) + panel.classList.add('open')
# ─────────────────────────────────────────────────────────────────────────────
END_ANCHOR = "    content.appendChild(ecoSec);\n\n    panel.classList.add('open');\n  }"
NEW_END = """    content.appendChild(ecoSec);

    // ── Date RDV (en bas) ──
    var rdvSec = document.createElement('div');
    rdvSec.className = 'detail-section';
    rdvSec.style.cssText = 'border-top:2px solid rgba(249,115,22,0.25);padding-top:14px;margin-top:4px;';
    var rdvTitle = document.createElement('div');
    rdvTitle.className = 'cmd-section-title';
    rdvTitle.style.marginBottom = '10px';
    rdvTitle.textContent = 'DATE RDV PHYSIQUE';
    rdvSec.appendChild(rdvTitle);
    var rdvRow = document.createElement('div');
    rdvRow.style.cssText = 'display:flex;gap:8px;align-items:center;';
    var rdvInput = document.createElement('input');
    rdvInput.type = 'date';
    rdvInput.value = communeRdv[code] || '';
    rdvInput.style.cssText = 'flex:1;padding:9px 10px;border-radius:7px;font-size:13px;font-weight:500;'
      + 'border:1px solid rgba(0,0,0,0.18);background:#fff;color:#1e2025;cursor:pointer;';
    rdvInput.addEventListener('change', function() {
      var val = rdvInput.value;
      if (val) { communeRdv[code] = val; } else { delete communeRdv[code]; }
      window.saveRdv(); renderRdvBtn();
    });
    rdvRow.appendChild(rdvInput);
    var rdvClearBtn = document.createElement('button');
    rdvClearBtn.textContent = '\\u2715';
    rdvClearBtn.title = 'Supprimer la date';
    rdvClearBtn.style.cssText = 'padding:9px 12px;border-radius:7px;font-size:13px;font-weight:700;cursor:pointer;'
      + 'background:rgba(0,0,0,0.04);border:1px solid rgba(0,0,0,0.12);color:#9ca3af;';
    rdvClearBtn.addEventListener('click', function() {
      rdvInput.value = ''; delete communeRdv[code]; window.saveRdv(); renderRdvBtn();
    });
    rdvRow.appendChild(rdvClearBtn);
    rdvSec.appendChild(rdvRow);
    var rdvSameDayBtn = document.createElement('button');
    rdvSameDayBtn.style.cssText = 'margin-top:10px;width:100%;padding:10px 14px;border-radius:7px;'
      + 'font-size:13px;font-weight:700;cursor:pointer;display:none;'
      + 'background:#fff7ed;border:2px solid #f97316;color:#c2410c;transition:all 0.15s;';
    rdvSameDayBtn.addEventListener('mouseenter', function() { this.style.background='#f97316'; this.style.color='#fff'; });
    rdvSameDayBtn.addEventListener('mouseleave', function() { this.style.background='#fff7ed'; this.style.color='#c2410c'; });
    var rdvListTitle = document.createElement('div');
    rdvListTitle.style.cssText = 'font-size:11px;font-weight:700;color:#9ca3af;letter-spacing:0.5px;'
      + 'text-transform:uppercase;margin-top:10px;margin-bottom:6px;display:none;';
    rdvListTitle.textContent = 'COMMUNES CE JOUR-L\\u00c0';
    var rdvList = document.createElement('div');
    rdvList.style.cssText = 'display:none;';
    function renderRdvBtn() {
      var dateVal = communeRdv[code];
      if (dateVal) {
        var count = Object.values(communeRdv).filter(function(d) { return d === dateVal; }).length;
        rdvSameDayBtn.textContent = '\\ud83d\\udcc5 Voir les ' + count + ' rdv du ' + formatDate(dateVal);
        rdvSameDayBtn.style.display = 'block';
        rdvSameDayBtn.onclick = function() {
          rdvListTitle.style.display = 'block'; rdvList.style.display = 'block';
          highlightSameDay(dateVal, rdvList);
        };
      } else {
        rdvSameDayBtn.style.display = 'none';
        rdvListTitle.style.display = 'none'; rdvList.style.display = 'none';
        if (rdvHighlightDate) clearRdvHighlight();
      }
    }
    renderRdvBtn();
    rdvSec.appendChild(rdvSameDayBtn);
    rdvSec.appendChild(rdvListTitle);
    rdvSec.appendChild(rdvList);
    content.appendChild(rdvSec);
    panel.classList.add('open');
  }"""

if END_ANCHOR in html:
    html = html.replace(END_ANCHOR, NEW_END, 1)
    print("  ✅ Nouvelle section DATE RDV ajoutée en bas")
else:
    print("  ⚠️  ANCRE ABSENTE : fin openDetail (ecoSec + panel.open)")
    ok = False

# ─────────────────────────────────────────────────────────────────────────────
# Checks finaux
# ─────────────────────────────────────────────────────────────────────────────
checks = [
    ("rdv-pulse", "Animation CSS pulse"),
    ("routeSegments", "Variable multitrajets"),
    ("clearAllRoutes", "Fonction clearAllRoutes"),
    ("decodePolyline", "Décodage polyline"),
    ("rdv-highlight-pulse", "Classe pulse"),
    ("#fbbf24", "Couleur surbrillance"),
    ("COMMUNES CE JOUR", "Liste communes même jour"),
    ("DATE RDV PHYSIQUE", "Section DATE RDV en bas"),
    ("routeLastCode === code", "Déselection CMD+Clic"),
]
for needle, label in checks:
    if needle in html:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ MANQUANT : {label}")
        ok = False

# Vérifier qu'il ne reste qu'UNE section DATE RDV
n_rdv = html.count("DATE RDV")
print(f"  ℹ️  Occurrences 'DATE RDV' dans le fichier : {n_rdv} (attendu : 1)")
if n_rdv != 1:
    print("  ❌ Doublon de section DATE RDV détecté")
    ok = False

if not ok:
    print("\n⚠️  Patch incomplet. Fichier NON écrasé. (backup .bak4 dispo)")
    sys.exit(1)
if html == original:
    print("\n⚠️  Aucune modification.")
    sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print(f"\n✅ Patch 2 v2 appliqué → {SRC}")
print(f"   Taille : {len(html):,} caractères")
