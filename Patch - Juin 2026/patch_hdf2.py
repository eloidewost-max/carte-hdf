#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable →", SRC)
    sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bak3"))
print("Backup créé :", SRC.with_suffix(".html.bak3"))

html = SRC.read_text(encoding="utf-8")
original = html

# ─────────────────────────────────────────────────────────────────────────────
# 1. CSS : animation pulse pour surbrillance même jour
# ─────────────────────────────────────────────────────────────────────────────
OLD_CSS = "* { margin: 0; padding: 0; box-sizing: border-box; }"
NEW_CSS = """* { margin: 0; padding: 0; box-sizing: border-box; }
@keyframes rdv-pulse {
  0%   { opacity: 1; }
  50%  { opacity: 0.45; }
  100% { opacity: 1; }
}
.rdv-highlight-pulse {
  animation: rdv-pulse 1.2s ease-in-out infinite;
}"""
html = html.replace(OLD_CSS, NEW_CSS, 1)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Variables globales : remplacer routeFromCode par tableau multi-segments
# ─────────────────────────────────────────────────────────────────────────────
OLD_RDV_VAR = "  var communeRdv = {}; // dates de rdv par commune { code: \"YYYY-MM-DD\" }\n  var rdvHighlightDate = null; // date surbrillance mode C"
NEW_RDV_VAR = """  var communeRdv = {}; // dates de rdv par commune { code: "YYYY-MM-DD" }
  var rdvHighlightDate = null; // date surbrillance mode C
  var routeSegments = []; // liste des segments tracés [{fromCode, toCode, polyline}]
  var routeLastCode = null; // dernière commune sélectionnée pour chaîner les trajets"""
html = html.replace(OLD_RDV_VAR, NEW_RDV_VAR, 1)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Click handler : multitrajets + déselection CMD+Clic même commune
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
            // CMD+Clic sur la même commune = déselectionner / effacer tous les trajets
            if (routeLastCode === code) {
              clearAllRoutes();
              routeLastCode = null;
              routeBanner.style.display = 'none';
              return;
            }
            // CMD+Clic sur une autre commune = ajouter un segment
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
          routeLastCode = code; // mémorise pour chaîner les trajets
          openDetail(code);
        }"""
html = html.replace(OLD_CLICK, NEW_CLICK, 1)

# ─────────────────────────────────────────────────────────────────────────────
# 4. Fonctions calcRoute / surbrillance — remplacer l'ancienne version complète
# ─────────────────────────────────────────────────────────────────────────────
OLD_UTILS = """  // ─── Formatage date FR ────────────────────────────────────────────────────
  function formatDate(isoStr) {
    if (!isoStr) return '';
    var parts = isoStr.split('-');
    return parts[2] + '/' + parts[1] + '/' + parts[0];
  }

  // ─── Bannière trajet OSRM ──────────────────────────────────────────────────
  var routeBanner = document.createElement('div');
  routeBanner.id = 'route-banner';
  routeBanner.style.cssText = 'position:fixed;bottom:40px;left:50%;transform:translateX(-50%);'
    + 'background:#1e2025;color:#fff;padding:10px 18px;border-radius:10px;font-size:13px;'
    + 'font-weight:600;z-index:9999;display:none;box-shadow:0 4px 16px rgba(0,0,0,0.3);'
    + 'display:none;align-items:center;gap:12px;';
  var routeText = document.createElement('span');
  var routeClose = document.createElement('button');
  routeClose.textContent = '✕';
  routeClose.style.cssText = 'background:none;border:none;color:#9ca3af;cursor:pointer;font-size:14px;padding:0;';
  routeClose.onclick = function() { routeBanner.style.display = 'none'; };
  routeBanner.appendChild(routeText);
  routeBanner.appendChild(routeClose);
  document.body.appendChild(routeBanner);

  // Indicateur mode CMD+Clic
  var cmdHint = document.createElement('div');
  cmdHint.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);'
    + 'background:#f97316;color:#fff;padding:6px 14px;border-radius:8px;font-size:11px;'
    + 'font-weight:600;z-index:9999;display:none;pointer-events:none;';
  cmdHint.textContent = '⌘ CMD+Clic sur une commune pour calculer le trajet';
  document.body.appendChild(cmdHint);

  // Affiche/masque le hint CMD au survol de la carte
  document.addEventListener('keydown', function(e) {
    if (e.metaKey || e.ctrlKey) cmdHint.style.display = 'block';
  });
  document.addEventListener('keyup', function(e) {
    if (!e.metaKey && !e.ctrlKey) cmdHint.style.display = 'none';
  });

  function getCentroid(code) {
    // Cherche dans le geoJSON déjà libéré — on utilise le layer à la place
    var layer = layerByCode[code];
    if (!layer) return null;
    var b = layer.getBounds();
    return [b.getCenter().lat, b.getCenter().lng];
  }

  async function calcRoute(fromCode, toCode, toFeature) {
    var fromLatLng = getCentroid(fromCode);
    var toLatLng   = getCentroid(toCode);
    if (!fromLatLng || !toLatLng) { alert("Impossible de localiser une commune."); return; }

    routeText.textContent = '⏳ Calcul du trajet…';
    routeBanner.style.display = 'flex';

    var url = 'https://router.project-osrm.org/route/v1/driving/'
      + fromLatLng[1] + ',' + fromLatLng[0] + ';'
      + toLatLng[1]   + ',' + toLatLng[0]
      + '?overview=false';

    try {
      var resp = await fetch(url);
      var data = await resp.json();
      if (data.code !== 'Ok') throw new Error('OSRM error');
      var leg = data.routes[0].legs[0];
      var dist = (leg.distance / 1000).toFixed(0) + ' km';
      var secs = leg.duration;
      var h = Math.floor(secs / 3600);
      var m = Math.round((secs % 3600) / 60);
      var dur = h > 0 ? h + 'h' + String(m).padStart(2,'0') : m + ' min';

      // Noms communes
      var fromName = layerByCode[fromCode] ? (layerByCode[fromCode].feature.properties.libgeo || fromCode) : fromCode;
      var toName   = toFeature ? (toFeature.properties.libgeo || toCode) : toCode;

      routeText.textContent = '🚗 ' + fromName + ' → ' + toName + ' : ' + dur + ' (' + dist + ')';
    } catch(err) {
      routeText.textContent = '⚠️ Erreur calcul trajet (réseau ?)';
    }
  }

  // ─── Surbrillance même date (option C) ────────────────────────────────────
  var rdvHighlightLayers = [];

  function clearRdvHighlight() {
    rdvHighlightDate = null;
    rdvHighlightLayers.forEach(function(l) { geoLayer.resetStyle(l); });
    rdvHighlightLayers = [];
    var badge = document.getElementById('rdv-highlight-badge');
    if (badge) badge.remove();
  }

  function highlightSameDay(dateVal) {
    clearRdvHighlight();
    rdvHighlightDate = dateVal;
    var codes = Object.keys(communeRdv).filter(function(c) { return communeRdv[c] === dateVal; });
    codes.forEach(function(c) {
      var layer = layerByCode[c];
      if (layer) {
        layer.setStyle({ weight: 3, color: '#f97316', opacity: 1, fillOpacity: 0.7 });
        rdvHighlightLayers.push(layer);
      }
    });
    // Badge info en haut de carte
    var badge = document.createElement('div');
    badge.id = 'rdv-highlight-badge';
    badge.style.cssText = 'position:fixed;top:52px;left:50%;transform:translateX(-50%);'
      + 'background:#f97316;color:#fff;padding:6px 16px;border-radius:8px;font-size:12px;'
      + 'font-weight:700;z-index:9999;display:flex;align-items:center;gap:10px;';
    badge.innerHTML = '📅 ' + codes.length + ' rdv le ' + formatDate(dateVal)
      + ' <button onclick="clearRdvHighlight()" style="background:none;border:none;color:#fff;'
      + 'cursor:pointer;font-size:14px;padding:0;margin-left:4px;">✕</button>';
    document.body.appendChild(badge);
  }
  window.clearRdvHighlight = clearRdvHighlight;"""

NEW_UTILS = """  // ─── Formatage date FR ────────────────────────────────────────────────────
  function formatDate(isoStr) {
    if (!isoStr) return '';
    var parts = isoStr.split('-');
    return parts[2] + '/' + parts[1] + '/' + parts[0];
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
  routeClose.textContent = '✕ Effacer';
  routeClose.style.cssText = 'background:rgba(255,255,255,0.15);border:none;color:#fff;'
    + 'cursor:pointer;font-size:12px;padding:3px 8px;border-radius:5px;white-space:nowrap;';
  routeClose.onclick = function() { clearAllRoutes(); routeBanner.style.display = 'none'; routeLastCode = null; };
  routeBanner.appendChild(routeText);
  routeBanner.appendChild(routeClose);
  document.body.appendChild(routeBanner);

  // Indicateur mode CMD+Clic
  var cmdHint = document.createElement('div');
  cmdHint.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);'
    + 'background:#f97316;color:#fff;padding:6px 14px;border-radius:8px;font-size:11px;'
    + 'font-weight:600;z-index:9999;display:none;pointer-events:none;';
  cmdHint.textContent = '⌘ CMD+Clic pour ajouter un trajet · CMD+Clic sur la même commune pour effacer';
  document.body.appendChild(cmdHint);

  document.addEventListener('keydown', function(e) {
    if (e.metaKey || e.ctrlKey) cmdHint.style.display = 'block';
  });
  document.addEventListener('keyup', function(e) {
    if (!e.metaKey && !e.ctrlKey) cmdHint.style.display = 'none';
  });

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
    // Decode Google encoded polyline format used by OSRM
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

    routeText.textContent = '⏳ Calcul du trajet…';
    routeBanner.style.display = 'flex';

    var url = 'https://router.project-osrm.org/route/v1/driving/'
      + fromLatLng[1] + ',' + fromLatLng[0] + ';'
      + toLatLng[1]   + ',' + toLatLng[0]
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

      // Tracer le trait rouge sur la carte
      var coords = decodePolyline(route.geometry);
      var poly = L.polyline(coords, {
        color: '#ef4444', weight: 4, opacity: 0.85, dashArray: null
      }).addTo(map);

      // Popup au milieu du trait
      var midIdx = Math.floor(coords.length / 2);
      var midPoint = coords[midIdx];
      L.popup({ closeButton: false, className: 'route-popup' })
        .setLatLng(midPoint)
        .setContent('<div style="font-size:12px;font-weight:700;color:#ef4444;">'
          + '🚗 ' + dur + ' · ' + dist + '</div>')
        .openOn(map);

      routeSegments.push({ fromCode: fromCode, toCode: toCode, polyline: poly, dur: dur, dist: dist, fromName: fromName, toName: toName });

      // Mettre à jour le texte bannière avec tous les segments
      updateRouteBanner();

    } catch(err) {
      routeText.textContent = '⚠️ Erreur calcul trajet (réseau ?)';
    }
  }

  function updateRouteBanner() {
    if (routeSegments.length === 0) { routeBanner.style.display = 'none'; return; }
    var totalDist = 0, totalSecs = 0;
    var parts = routeSegments.map(function(seg) {
      return '🚗 ' + seg.fromName + ' → ' + seg.toName + ' : ' + seg.dur + ' (' + seg.dist + ')';
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
        // Bordure épaisse orange vif + remplissage jaune semi-transparent
        layer.setStyle({ weight: 5, color: '#f97316', opacity: 1, fillColor: '#fbbf24', fillOpacity: 0.75 });
        // Classe CSS pour l'animation pulse
        var elem = layer.getElement ? layer.getElement() : null;
        if (elem) elem.classList.add('rdv-highlight-pulse');
        rdvHighlightLayers.push({ layer: layer, elem: elem });
      }
    });

    // Badge info en haut de carte
    var badge = document.createElement('div');
    badge.id = 'rdv-highlight-badge';
    badge.style.cssText = 'position:fixed;top:52px;left:50%;transform:translateX(-50%);'
      + 'background:#f97316;color:#fff;padding:8px 20px;border-radius:10px;font-size:13px;'
      + 'font-weight:700;z-index:9999;display:flex;align-items:center;gap:12px;'
      + 'box-shadow:0 4px 16px rgba(249,115,22,0.4);';
    badge.innerHTML = '📅 ' + codes.length + ' rdv le ' + formatDate(dateVal)
      + ' <button onclick="clearRdvHighlight()" style="background:rgba(255,255,255,0.25);border:none;color:#fff;'
      + 'cursor:pointer;font-size:12px;padding:3px 8px;border-radius:5px;">✕ Fermer</button>';
    document.body.appendChild(badge);

    // Remplir la liste dans le panneau si fournie
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
        li.textContent = '📍 ' + com.name;
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

html = html.replace(OLD_UTILS, NEW_UTILS, 1)

# ─────────────────────────────────────────────────────────────────────────────
# 5. Section DATE RDV : déplacer en bas (après données économiques)
#    + boutons plus grands + liste communes
#    D'abord on supprime la section rdv de sa position actuelle
# ─────────────────────────────────────────────────────────────────────────────
OLD_RDV_SECTION = """    // ── Date RDV ──
    var rdvSec = document.createElement('div');
    rdvSec.className = 'detail-section';
    var rdvTitle = document.createElement('div');
    rdvTitle.className = 'cmd-section-title';
    rdvTitle.style.marginBottom = '8px';
    rdvTitle.textContent = 'DATE RDV';
    rdvSec.appendChild(rdvTitle);

    var rdvRow = document.createElement('div');
    rdvRow.style.cssText = 'display:flex;gap:6px;align-items:center;';

    var rdvInput = document.createElement('input');
    rdvInput.type = 'date';
    rdvInput.value = communeRdv[code] || '';
    rdvInput.style.cssText = 'flex:1;padding:6px 8px;border-radius:5px;font-size:12px;'
      + 'border:1px solid rgba(0,0,0,0.15);background:#fff;color:#1e2025;cursor:pointer;';
    rdvInput.addEventListener('change', function() {
      var val = rdvInput.value;
      if (val) {
        communeRdv[code] = val;
      } else {
        delete communeRdv[code];
      }
      window.saveRdv();
      renderRdvBtn();
    });
    rdvRow.appendChild(rdvInput);

    var rdvClearBtn = document.createElement('button');
    rdvClearBtn.textContent = '✕';
    rdvClearBtn.title = 'Supprimer la date';
    rdvClearBtn.style.cssText = 'padding:6px 8px;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer;'
      + 'background:rgba(0,0,0,0.04);border:1px solid rgba(0,0,0,0.12);color:#9ca3af;';
    rdvClearBtn.addEventListener('click', function() {
      rdvInput.value = '';
      delete communeRdv[code];
      window.saveRdv();
      renderRdvBtn();
    });
    rdvRow.appendChild(rdvClearBtn);
    rdvSec.appendChild(rdvRow);

    // Bouton "Voir rdv du même jour" (option C)
    var rdvSameDayBtn = document.createElement('button');
    rdvSameDayBtn.style.cssText = 'margin-top:6px;width:100%;padding:6px 10px;border-radius:5px;'
      + 'font-size:11px;font-weight:600;cursor:pointer;display:none;'
      + 'background:#f0fdf4;border:1px solid #86efac;color:#166534;';
    function renderRdvBtn() {
      var dateVal = communeRdv[code];
      if (dateVal) {
        var count = Object.values(communeRdv).filter(function(d) { return d === dateVal; }).length;
        rdvSameDayBtn.textContent = '📅 Voir les ' + count + ' rdv du ' + formatDate(dateVal);
        rdvSameDayBtn.style.display = 'block';
        rdvSameDayBtn.onclick = function() { highlightSameDay(dateVal); };
      } else {
        rdvSameDayBtn.style.display = 'none';
        if (rdvHighlightDate) clearRdvHighlight();
      }
    }
    renderRdvBtn();
    rdvSec.appendChild(rdvSameDayBtn);
    content.appendChild(rdvSec);

    // ── Statut commercial ──"""

NEW_RDV_REMOVED = "    // ── Statut commercial ──"
html = html.replace(OLD_RDV_SECTION, NEW_RDV_REMOVED, 1)

# ─────────────────────────────────────────────────────────────────────────────
# 6. Ajouter DATE RDV en bas, après les données économiques
#    On cherche la fin de la section éco (content.appendChild(ecoSec) ou similaire)
#    On va insérer avant la fermeture de openDetail
# ─────────────────────────────────────────────────────────────────────────────
# Trouver la fin du panneau détail — chercher content.appendChild(ecoSec)
OLD_END_DETAIL = """    content.appendChild(ecoSec);
  }"""

NEW_END_DETAIL = """    content.appendChild(ecoSec);

    // ── Date RDV (en bas du panneau) ──
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
      window.saveRdv();
      renderRdvBtn();
    });
    rdvRow.appendChild(rdvInput);

    var rdvClearBtn = document.createElement('button');
    rdvClearBtn.textContent = '✕';
    rdvClearBtn.title = 'Supprimer la date';
    rdvClearBtn.style.cssText = 'padding:9px 12px;border-radius:7px;font-size:13px;font-weight:700;cursor:pointer;'
      + 'background:rgba(0,0,0,0.04);border:1px solid rgba(0,0,0,0.12);color:#9ca3af;';
    rdvClearBtn.addEventListener('click', function() {
      rdvInput.value = '';
      delete communeRdv[code];
      window.saveRdv();
      renderRdvBtn();
    });
    rdvRow.appendChild(rdvClearBtn);
    rdvSec.appendChild(rdvRow);

    // Bouton "Voir rdv du même jour"
    var rdvSameDayBtn = document.createElement('button');
    rdvSameDayBtn.style.cssText = 'margin-top:10px;width:100%;padding:10px 14px;border-radius:7px;'
      + 'font-size:13px;font-weight:700;cursor:pointer;display:none;'
      + 'background:#fff7ed;border:2px solid #f97316;color:#c2410c;transition:all 0.15s;';
    rdvSameDayBtn.addEventListener('mouseenter', function() {
      this.style.background = '#f97316'; this.style.color = '#fff';
    });
    rdvSameDayBtn.addEventListener('mouseleave', function() {
      this.style.background = '#fff7ed'; this.style.color = '#c2410c';
    });

    // Liste des communes même jour
    var rdvListTitle = document.createElement('div');
    rdvListTitle.style.cssText = 'font-size:11px;font-weight:700;color:#9ca3af;letter-spacing:0.5px;'
      + 'text-transform:uppercase;margin-top:10px;margin-bottom:6px;display:none;';
    rdvListTitle.textContent = 'COMMUNES CE JOUR-LÀ';
    var rdvList = document.createElement('div');
    rdvList.style.cssText = 'display:none;';

    function renderRdvBtn() {
      var dateVal = communeRdv[code];
      if (dateVal) {
        var count = Object.values(communeRdv).filter(function(d) { return d === dateVal; }).length;
        rdvSameDayBtn.textContent = '📅 Voir les ' + count + ' rdv du ' + formatDate(dateVal);
        rdvSameDayBtn.style.display = 'block';
        rdvSameDayBtn.onclick = function() {
          rdvListTitle.style.display = 'block';
          rdvList.style.display = 'block';
          highlightSameDay(dateVal, rdvList);
        };
      } else {
        rdvSameDayBtn.style.display = 'none';
        rdvListTitle.style.display = 'none';
        rdvList.style.display = 'none';
        if (rdvHighlightDate) clearRdvHighlight();
      }
    }
    renderRdvBtn();
    rdvSec.appendChild(rdvSameDayBtn);
    rdvSec.appendChild(rdvListTitle);
    rdvSec.appendChild(rdvList);
    content.appendChild(rdvSec);
  }"""

html = html.replace(OLD_END_DETAIL, NEW_END_DETAIL, 1)

# ─────────────────────────────────────────────────────────────────────────────
# Vérifications
# ─────────────────────────────────────────────────────────────────────────────
checks = [
    ("rdv-pulse", "Animation CSS pulse"),
    ("routeSegments", "Variable multitrajets"),
    ("clearAllRoutes", "Fonction clearAllRoutes"),
    ("decodePolyline", "Décodage polyline OSRM"),
    ("rdv-highlight-pulse", "Classe CSS pulse sur layer"),
    ("fillColor: '#fbbf24'", "Couleur jaune surbrillance"),
    ("COMMUNES CE JOUR-LÀ", "Liste communes même jour"),
    ("DATE RDV PHYSIQUE", "Section DATE RDV en bas"),
    ("CMD+Clic sur la même commune pour effacer", "Hint multitrajets"),
    ("routeLastCode === code", "Déselection CMD+Clic"),
]

all_ok = True
for needle, label in checks:
    if needle in html:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ MANQUANT : {label}")
        all_ok = False

if not all_ok:
    print("\n⚠️  Certains patches n'ont pas été appliqués. Fichier NON écrasé.")
    sys.exit(1)

if html == original:
    print("\n⚠️  Aucune modification détectée.")
    sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print(f"\n✅ Patch 2 appliqué → {SRC}")
print(f"   Taille : {len(html):,} caractères")
