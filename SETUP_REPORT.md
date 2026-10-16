# C! Dungeons & Dragons — Setup Report

**Project:** C! Dungeons & Dragons (C! RAS — Rules & Announcements System)
**Course:** Midterm Python Project
**Target Institution:** Egypt-Japan KOSEN (EJ-KOSEN)
**Class:** C1
**Stack:** Python 3 · Flask · SQLite · NES.css (pixel UI) · HTML5 · vanilla JS

---

## 1. Summary

This is the complete offline-ready guide for the **C! RAS Hub**. Everything has
been created, installed, **and tested** on this machine. **No internet is
required** at the demo — the framework, font, and all images are stored locally.

| Item | Status |
|------|--------|
| Python virtual environment (`.venv`) | ✅ Created |
| Flask installed | ✅ Flask 3.0.3 |
| SQLite database (`database.db`) | ✅ Created & seeded |
| NES.css pixel UI + Press Start 2P font | ✅ Vendored locally (offline) |
| TED thumbnails + meme images | ✅ Downloaded & optimized locally |
| KOSEN Spotlight (random TED + meme) | ✅ Built & tested |
| Community Events calendar + "Ask to go" | ✅ Built & tested |
| Directory with links + "Add yourself" form | ✅ Built & tested |
| Student profile page (links between directory & events) | ✅ Built & tested |
| New color palette applied | ✅ Applied (#BE1A1A #D0311E #F7D87F #F8EBAB) |
| All routes tested | ✅ HTTP 200 on every page |
| Code comments | ✅ Every file commented |

---

## 2. Where everything lives

```text
/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub/
```

> ⚠️ **The folder name contains `!` and `&`.** In the terminal you **must**
> wrap the path in double quotes: `cd "/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub"`

### Directory tree

```text
c1_ras_hub/
├── .venv/
├── app.py
├── database.py
├── schema.sql
├── seed.py
├── database.db
├── requirements.txt
├── SETUP_REPORT.md
├── static/
│   ├── nes/nes.min.css + fonts/press-start-2p.woff2
│   ├── css/style.css
│   ├── js/app.js
│   └── img/ (ted + memes)
└── templates/
    ├── base.html
    ├── index.html
    ├── lhr.html
    ├── game_detail.html
    ├── directory.html
    ├── profile.html
    └── schedule.html
```

---

## 3. How to run it (offline)

```bash
cd "/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub"
source .venv/bin/activate
python app.py
```

Open `http://127.0.0.1:5000`. Stop with `Ctrl + C`.

### Test on your phone (same Wi-Fi / hotspot)

`app.py` binds to `0.0.0.0`. Find IP (`hostname -I`) and open `http://<that-ip>:5000`.

---

## 4. Community Events Calendar + "Ask to go with them"

`/schedule` is a **calendar view** (Date/Day column + Events column). 
- **Post an event**: organizer (dropdown from directory), event name, link, date, location, details.
- **Ask to go with them**: on each event, fill in name (optional message). Requests shown under the event.
- **Organizer name** links to `/student/<id>`.
- **"Open link"** opens the event link (needs internet only if external).

---

## 5. Directory + Profile + Linking

`/directory` shows cards with avatar, name (links to profile), role, about, contact links (Website/Facebook/Instagram if present), phone (`tel:`), email (`mailto:`), "View profile". Includes **"Add yourself"** form.

`/student/<id>` shows profile and lists events by that student, linking back to calendar.

---

## 6. Database

Seven tables: `announcements`, `lhr_games`, `students` (+website/facebook/instagram/phone/email), `ted_talks`, `memes`, `events` (organizer_id FK), `event_requests` (event_id FK, user_id reserved for future login).

Seeded: 3/3/5/3/9/4/3.

---

## 7. Resetting

```bash
cd "/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub"
source .venv/bin/activate
python seed.py
```

---

## 8. Routes

| URL | Template | What it shows |
|-----|----------|---------------|
| `/` | `index.html` | Spotlight + bulletin + campus rules |
| `/lhr` | `lhr.html` | Games list |
| `/lhr/game/<id>` | `game_detail.html` | Game detail |
| `/directory` | `directory.html` | Directory + "Add yourself" |
| `/student/<id>` | `profile.html` | Profile + events |
| `/schedule` | `schedule.html` | Events calendar + "Add event" + "Ask to go" |

---

## 9. UI

**NES.css** (vendored, offline) + new color palette: `#BE1A1A`, `#D0311E`, `#F7D87F`, `#F8EBAB`. Press Start 2P font vendored. Theme in `static/css/style.css`.

---

## 10. Quick start from scratch

```bash
cd "/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed.py
python app.py
```

*Pillow was used only for image resizing (not in requirements.txt).*
