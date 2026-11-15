# 🎯 ThrowLab for Autodarts – Lokale Dart-Trainings-Suite

Eine schnelle, moderne und komplett lokal laufende **Trainings-Suite für [Autodarts](https://autodarts.io)** Kamera-Systeme (Windows, macOS & Linux). Verbindet sich direkt mit deinem lokalen Autodarts-Board (`http://localhost:3180`) oder lässt sich per Klick auf dem interaktiven Live-Dartboard bedienen.

![ThrowLab for Autodarts Logo](appicon.svg)

---

## ✨ Enthaltene Trainingsprogramme

1. **🎯 Zielfeld-Training (Segment-Fokus)** – Konzentration auf ein wählbares Feld (`1–20` oder `Bull`)
2. **🌍 Around the World (Doppel)** – `D1 → D20 + Bull` (Vorwärts, Im Uhrzeigersinn, Rückwärts oder Zufällig)
3. **🪜 Checkout-Leiter (Up & Down)** – Start bei `41` oder beliebigem Wert (`2–170`): Checkout = `+10`, Fehlwurf = `-1`
4. **⚔️ Bob's 27** – Der Darts-Klassiker: Start mit 27 Punkten auf `D1 → D20 + Bull`
5. **✂️ Halve It** – 7 Runden (`20 → 16 → Beliebiges Doppel → 19 → 15 → Beliebiges Triple → Bull`)

---

## 🚀 Features für Autodarts-Spieler

- **Echtzeit-Kamera-Koordinaten:** Zeigt jeden geworfenen Dart exakt an den von Autodarts gemessenen `(x, y)`-Koordinaten auf dem Live-Board an (inkl. Live-Koordinaten-Leiste unter dem Board).
- **Smart-Zoom auf das Zielsegment:** Zoomt automatisch auf das aktuelle Ziel (und schaltet bei *Checkout-Leiter* sowie bei *Halve It – Beliebiges Doppel/Triple* automatisch auf die Vollansicht um).
- **Board-Steuerung im Header:** Zeigt klar an, ob das Board **Aktiv**, im **Takeout (Darts ziehen)**, **Gestoppt** (inkl. Direkt-Start-Button `▶️ Board jetzt starten`) oder **Offline** ist. Inklusive **Board Reset** direkt oben in der Leiste.
- **Plattformübergreifender 1-Klick-Updater:** Funktioniert unter **Windows, macOS & Linux** direkt über den Browser (via Git **oder** automatischem GitHub-ZIP-Download – ganz ohne `.sh`-Skripte).

---

## 🛠️ Schnellstart (Windows, macOS & Linux)

```bash
python3 server.py
```
*(Unter Windows ggf. `python server.py`)* — danach im Browser **`http://localhost:8075`** öffnen.

---

## 🔄 Updates (Windows, macOS & Linux)

Klicke oben in der App neben dem Titel auf **`v1.2.0`** → **„🔄 Auf Updates prüfen“** → **„⬇️ Update jetzt installieren“**.
Der integrierte Updater lädt neue Versionen automatisch (per `git pull` falls über Git geklont, oder direkt als ZIP von GitHub – ganz ohne Plattform-Abhängigkeiten).
