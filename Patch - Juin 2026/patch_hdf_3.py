#!/usr/bin/env python3
import re, sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
DST = SRC

if not SRC.exists():
    print("ERREUR : fichier introuvable →", SRC)
    sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bak2"))
print("Backup créé :", SRC.with_suffix(".html.bak2"))

html = SRC.read_text(encoding="utf-8")
original = html

# ─────────────────────────────────────────────────────────────────────────────
# 1. Variable globale communeRdv + init Firebase rdv
#    On insère juste après la ligne qui déclare communeVisites
# ─────────────────────────────────────────────────────────────────────────────
OLD_VAR = "  var activeStatutFilters = []; // filtre multi-statuts en mode prospection"
NEW_VAR = """  var activeStatutFilters = []; // filtre multi-statuts en mode prospection
  var communeRdv = {}; // dates de rdv par commune { code: "YYYY-MM-DD" }
  var rdvHighlightDate = null; // date surbrillance mode C"""

html = html.replace(OLD_VAR, NEW_VAR, 1)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Firebase : saveRdv + onSnapshot rdv — insérer après saveVisites
# ─────────────────────────────────────────────────────────────────────────────
OLD_SAVE_VISITES = """  window.saveVisites = function() {
    db.collection("statuts").doc("visites").set(communeVisites);
  };
  db.collection("statuts").doc("communes").onSnapshot"""

NEW_SAVE_VISITES = """  window.saveVisites = function() {
    db.collection("statuts").doc("visites").set(communeVisites);
  };

  window.saveRdv = function() {
    db.collection("statuts").doc("rdv").set(communeRdv);
  };
  db.collection("statuts").doc("rdv").onSnapshot(function(docSnap) {
    if (docSnap.exists) {
      communeRdv = docSnap.data();
    }
  });

  db.collection("statuts").doc("communes").onSnapshot"""

html = html.replace(OLD_SAVE_VISITES, NEW_SAVE_VISITES, 1)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Sync Firebase : ajouter le chargement rdv dans _syncFirebase
# ─────────────────────────────────────────────────────────────────────────────
OLD_SYNC = """window._syncFirebase = function() {
  db.collection("statuts").doc("communes").get().then(function(docSnap) {"""

NEW_SYNC = """window._syncFirebase = function() {
  db.collection("statuts").doc("rdv").get().then(function(d) { if (d.exists) communeRdv = d.data(); });
  db.collection("statuts").doc("communes").get().then(function(docSnap) {"""

html = html.replace(OLD_SYNC, NEW_SYNC, 1)

# ─────────────────────────────────────────────────────────────────────────────
# 4. CMD+Clic dans le handler click sur les communes
# ─────────────────────────────────────────────────────────────────────────────
OLD_CLICK = """        click: function(e) {
          map.fitBounds(e.target.getBounds(), { maxZoom: 11 });
          if (window._selectedLayer) geoLayer.resetStyle(window._selectedLayer);
          window._selectedLayer = e.target;
          e.target.setStyle({ weight: 3, color: '#ffff00', opacity: 1 });
          openDetail(code);
        }"""

NEW_CLICK = """        click: function(e) {
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

html = html.replace(OLD_CLICK, NEW_CLICK, 1)

# ─────────────────────────────────────────────────────────────────────────────
# 5. Section DATE RDV dans openDetail — insérer après la section VISITE TERRAIN
#    (après content.appendChild(visiteSec))
# ─────────────────────────────────────────────────────────────────────────────
OLD_AFTER_VISITE = """    visiteSec.appendChild(visiteBtns);
    content.appendChild(visiteSec);

    // ── Statut commercial ──"""

NEW_AFTER_VISITE = """    visiteSec.appendChild(visiteBtns);
    content.appendChild(visiteSec);

    // ── Date RDV ──
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

html = html.replace(OLD_AFTER_VISITE, NEW_AFTER_VISITE, 1)

# ─────────────────────────────────────────────────────────────────────────────
# 6. Fonctions utilitaires : calcRoute, highlightSameDay, formatDate
#    Insérer juste avant la fermeture </script> finale du bloc principal
#    (avant "  var geoLayer = L.geoJSON")
# ─────────────────────────────────────────────────────────────────────────────
OLD_GEOLAYER = "  var geoLayer = L.geoJSON(communesGeo, {"

NEW_GEOLAYER = """  // ─── Formatage date FR ────────────────────────────────────────────────────
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
  window.clearRdvHighlight = clearRdvHighlight;

  var geoLayer = L.geoJSON(communesGeo, {"""

html = html.replace(OLD_GEOLAYER, NEW_GEOLAYER, 1)

# ─────────────────────────────────────────────────────────────────────────────
# Vérifications
# ─────────────────────────────────────────────────────────────────────────────
checks = [
    ("communeRdv = {}", "Variable communeRdv"),
    ("saveRdv", "Fonction saveRdv"),
    ("calcRoute", "Fonction calcRoute"),
    ("highlightSameDay", "Fonction highlightSameDay"),
    ("rdv-highlight-badge", "Badge surbrillance"),
    ("route-banner", "Bannière trajet"),
    ("formatDate", "Fonction formatDate"),
    ("DATE RDV", "Section DATE RDV"),
    ("CMD+Clic", "Hint CMD+Clic"),
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
    print("\n⚠️  Aucune modification détectée. Vérifie les ancres de remplacement.")
    sys.exit(1)

DST.write_text(html, encoding="utf-8")
print(f"\n✅ Patch appliqué → {DST}")
print(f"   Taille : {len(html):,} caractères")
