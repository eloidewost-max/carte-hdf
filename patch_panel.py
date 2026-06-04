#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bakpanel"))
print("Backup cree :", SRC.with_suffix(".html.bakpanel"))

html = SRC.read_text(encoding="utf-8")
original = html
ok = True

def must_replace(old, new, label):
    global html, ok
    if old not in html:
        print("  [X] ANCRE ABSENTE :", label); ok = False; return
    html = html.replace(old, new, 1)
    print("  [OK]", label)

# 1. Supprimer les anciens boutons casses du top-bar (tout le bloc <div ...> ... </div>
#    qui contient global-rdv-btn etc.). On retire le bloc et on garde juste le sync.
old_topbar = (
    '      <button type="button" id="global-rdv-btn" style="display:inline-flex;align-items:center;gap:6px;padding:9px 16px;border-radius:9px;border:none;background:#7e22ce;color:#fff;font-size:14px;font-weight:700;cursor:pointer;white-space:nowrap;box-shadow:0 2px 6px rgba(126,34,206,0.35);">\U0001f4c5 Choisir une date</button>\n'
    '      <input type="date" id="global-rdv-date" style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0;">\n'
    '      <div style="position:relative;display:inline-block;">\n'
)
# On ne sait pas exactement les lignes suivantes (tronquees), donc on retire de maniere ciblee
# le bouton date + input ; le reste (menu) sera neutralise car deplacé. Pour rester sur, on
# laisse le menu en place mais cache.
# --> Approche plus sure : on cache tout le conteneur via l'ancre du label de depart si elle existe.

# En realite, on remplace juste le bouton date + input par rien (vide), et on cache le bloc menu.
if old_topbar in html:
    html = html.replace(old_topbar,
        '      <div style="display:none;position:relative;display:inline-block;">\n', 1)
    print("  [OK] Anciens boutons top-bar retires (bouton date + input)")
else:
    print("  [!] Ancre top-bar exacte non trouvee - on continue (les boutons gauche primeront)")

# 2. Inserer les 2 boutons date dans renderCmdProspection, juste apres le bouton sauvegarde.
must_replace(
    "    saveBtn.addEventListener('click', exportJSON);\n"
    "    saveSec.appendChild(saveBtn);\n"
    "    container.appendChild(saveSec);",
    "    saveBtn.addEventListener('click', exportJSON);\n"
    "    saveSec.appendChild(saveBtn);\n"
    "    container.appendChild(saveSec);\n"
    "\n"
    "    // --- Boutons RDV (date + liste des dates) ---\n"
    "    var rdvSec = document.createElement('div');\n"
    "    rdvSec.className = 'cmd-section';\n"
    "    var pickWrap = document.createElement('div');\n"
    "    pickWrap.style.cssText = 'position:relative;width:100%;margin-bottom:6px;';\n"
    "    var pickBtn = document.createElement('button');\n"
    "    pickBtn.textContent = '\\ud83d\\udcc5 Choisir une date';\n"
    "    pickBtn.style.cssText = 'width:100%;padding:9px 10px;background:#7e22ce;border:none;border-radius:7px;color:#fff;font-size:13px;font-weight:700;cursor:pointer;';\n"
    "    var pickInput = document.createElement('input');\n"
    "    pickInput.type = 'date';\n"
    "    pickInput.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;';\n"
    "    pickInput.addEventListener('change', function() {\n"
    "      if (pickInput.value) { highlightSameDay(pickInput.value, null); clearRdvBtn.style.display = 'block'; }\n"
    "      else { clearRdvHighlight(); clearRdvBtn.style.display = 'none'; }\n"
    "    });\n"
    "    pickWrap.appendChild(pickBtn);\n"
    "    pickWrap.appendChild(pickInput);\n"
    "    rdvSec.appendChild(pickWrap);\n"
    "\n"
    "    var listWrap = document.createElement('div');\n"
    "    listWrap.style.cssText = 'position:relative;width:100%;margin-bottom:6px;';\n"
    "    var listBtn2 = document.createElement('button');\n"
    "    listBtn2.textContent = '\\ud83d\\udccb RDV programm\\u00e9s \\u25be';\n"
    "    listBtn2.style.cssText = 'width:100%;padding:9px 10px;background:#faf5ff;border:2px solid #a855f7;border-radius:7px;color:#7e22ce;font-size:13px;font-weight:700;cursor:pointer;';\n"
    "    var listMenu2 = document.createElement('div');\n"
    "    listMenu2.style.cssText = 'display:none;margin-top:4px;background:#fff;border:1px solid rgba(0,0,0,0.12);border-radius:8px;max-height:260px;overflow-y:auto;padding:4px;';\n"
    "    function frD(iso){ var p=iso.split('-'); return p[2]+'/'+p[1]+'/'+p[0]; }\n"
    "    listBtn2.addEventListener('click', function() {\n"
    "      if (listMenu2.style.display === 'block') { listMenu2.style.display='none'; return; }\n"
    "      listMenu2.innerHTML='';\n"
    "      var counts={};\n"
    "      Object.keys(communeRdv).forEach(function(c){ var dt=communeRdv[c]; if(dt) counts[dt]=(counts[dt]||0)+1; });\n"
    "      var dates=Object.keys(counts).sort();\n"
    "      if (dates.length===0){ var e=document.createElement('div'); e.style.cssText='padding:10px;color:#9ca3af;font-size:12px;text-align:center;'; e.textContent='Aucun RDV programm\\u00e9'; listMenu2.appendChild(e); }\n"
    "      else dates.forEach(function(dt){\n"
    "        var it=document.createElement('button');\n"
    "        it.style.cssText='display:flex;justify-content:space-between;align-items:center;gap:8px;width:100%;padding:8px 10px;border:none;background:transparent;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;color:#374151;text-align:left;';\n"
    "        it.onmouseover=function(){ it.style.background='#f3e8ff'; };\n"
    "        it.onmouseout=function(){ it.style.background='transparent'; };\n"
    "        it.innerHTML='<span>\\ud83d\\udcc5 '+frD(dt)+'</span><span style=\"background:#7e22ce;color:#fff;border-radius:10px;padding:2px 8px;font-size:11px;\">'+counts[dt]+'</span>';\n"
    "        it.addEventListener('click', function(){ pickInput.value=dt; highlightSameDay(dt,null); clearRdvBtn.style.display='block'; listMenu2.style.display='none'; });\n"
    "        listMenu2.appendChild(it);\n"
    "      });\n"
    "      listMenu2.style.display='block';\n"
    "    });\n"
    "    listWrap.appendChild(listBtn2);\n"
    "    rdvSec.appendChild(listWrap);\n"
    "    rdvSec.appendChild(listMenu2);\n"
    "\n"
    "    var clearRdvBtn = document.createElement('button');\n"
    "    clearRdvBtn.textContent = '\\u2715 Effacer la date';\n"
    "    clearRdvBtn.style.cssText = 'display:none;width:100%;padding:7px 10px;background:#fff;border:1px solid rgba(0,0,0,0.15);border-radius:7px;color:#6b7280;font-size:12px;font-weight:600;cursor:pointer;';\n"
    "    clearRdvBtn.addEventListener('click', function(){ pickInput.value=''; clearRdvHighlight(); clearRdvBtn.style.display='none'; });\n"
    "    rdvSec.appendChild(clearRdvBtn);\n"
    "    container.appendChild(rdvSec);",
    "Insertion des 2 boutons RDV dans le panneau gauche")

# 3. Toggle accordeon sur chaque section de statut.
must_replace(
    "      var secTitle = document.createElement('div');\n"
    "      secTitle.className = 'cmd-section-title';\n"
    "      secTitle.style.color = st.color;\n"
    "      secTitle.textContent = st.label.toUpperCase() + ' (' + items.length + ')';\n"
    "      sec.appendChild(secTitle);\n"
    "\n"
    "      var ul = document.createElement('ul');\n"
    "      ul.className = 'prospect-list';",
    "      var secTitle = document.createElement('div');\n"
    "      secTitle.className = 'cmd-section-title';\n"
    "      secTitle.style.color = st.color;\n"
    "      secTitle.style.cursor = 'pointer';\n"
    "      secTitle.style.userSelect = 'none';\n"
    "      var chevron = document.createElement('span');\n"
    "      chevron.textContent = '\\u25be ';\n"
    "      chevron.style.cssText = 'display:inline-block;width:14px;transition:transform 0.15s;';\n"
    "      secTitle.appendChild(chevron);\n"
    "      var titleTxt = document.createElement('span');\n"
    "      titleTxt.textContent = st.label.toUpperCase() + ' (' + items.length + ')';\n"
    "      secTitle.appendChild(titleTxt);\n"
    "      sec.appendChild(secTitle);\n"
    "\n"
    "      var ul = document.createElement('ul');\n"
    "      ul.className = 'prospect-list';\n"
    "      secTitle.addEventListener('click', function() {\n"
    "        var hidden = ul.style.display === 'none';\n"
    "        ul.style.display = hidden ? '' : 'none';\n"
    "        chevron.textContent = hidden ? '\\u25be ' : '\\u25b8 ';\n"
    "      });",
    "Toggle accordeon sur sections de statut")

# Checks
for needle, label in [
    ("Boutons RDV (date + liste des dates)", "Boutons RDV inseres"),
    ("pickBtn.textContent", "Bouton choisir date"),
    ("Toggle accordeon", "(commentaire absent ok)"),
    ("chevron.textContent = hidden", "Toggle accordeon actif"),
]:
    if needle == "Toggle accordeon":
        continue
    print(("  [OK] " if needle in html else "  [X] MANQUANT : ") + label)
    if needle not in html: ok = False

if not ok:
    print("\\n[!] Patch incomplet. Fichier NON ecrase. (backup .bakpanel)"); sys.exit(1)
if html == original:
    print("\\n[!] Aucune modification."); sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print("\\n[OK] Patch panel applique ->", SRC)
print("   Taille :", "{:,}".format(len(html)), "caracteres")
