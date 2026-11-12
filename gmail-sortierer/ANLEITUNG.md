# Jarvis Mail-Sortierer für Gmail – Anleitung

Der Sortierer läuft kostenlos in deinem Google-Konto. Du brauchst dafür keinen Server und kein Gerät. Kosten entstehen nur für die KI, je nach Modell ein paar Euro oder ein paar Cent im Monat.

## Schritt 1: Claude-API-Schlüssel holen
1. Öffne **https://console.anthropic.com** und registriere dich.
2. Lade unter **Billing** ein Guthaben auf, z. B. 5 €.
3. Wähle **API Keys → Create Key**, Name `Jarvis`, und kopiere den Schlüssel. Er beginnt mit `sk-ant-`.
   Bewahr den Schlüssel gut auf, er wird nur einmal angezeigt.

## Schritt 2: Skript anlegen
1. Öffne **https://script.google.com** und melde dich mit deinem Gmail-Konto an.
2. Klicke **Neues Projekt**.
3. Klicke oben auf „Unbenanntes Projekt“ und nenn es **Jarvis**.
4. Lösche den vorhandenen Text im Editor vollständig.
5. Öffne die Datei [`Code.gs`](Code.gs) hier auf GitHub und klicke oben rechts auf das **Kopieren-Symbol**.
6. Füge den Text in den Editor ein und klicke auf **Speichern** (Diskettensymbol).

## Schritt 3: Schlüssel hinterlegen
1. Klicke links auf das **Zahnrad (Projekteinstellungen)**.
2. Scroll ganz nach unten zu **Skripteigenschaften** und klicke auf **Skripteigenschaft hinzufügen**.
3. Trag als Eigenschaft `ANTHROPIC_API_KEY` ein und als Wert deinen Schlüssel aus Schritt 1.
4. Klicke auf **Skripteigenschaften speichern**.

## Schritt 4: Einschalten
1. Klicke links auf **< > (Editor)**.
2. Wähle oben in der Auswahlliste neben „Ausführen“ die Funktion **installieren** und klicke auf **Ausführen**.
3. Google fragt nach Berechtigungen:
   1. Klicke **Berechtigungen prüfen** und wähle dein Konto.
   2. Es erscheint „Google hat diese App nicht überprüft“. Das ist normal, weil es dein eigenes Skript ist. Klicke auf **Erweitert → Zu Jarvis wechseln (unsicher)** und dann auf **Zulassen**.
4. Unten im Protokoll steht dann für jede Mail eine Zeile und am Ende **„Fertig!“**.

## Schritt 5: Ein paar Tage beobachten
- In Gmail siehst du links die neuen Labels unter **Jarvis**: Dringend, Wichtig, Marken und Würde löschen.
- **Marken:** Hier landen Newsletter und Werbung bekannter Marken wie Rituals. Die kannst du selbst durchsehen und abbestellen. Alle anderen Newsletter, Werbung und Spam löscht Jarvis.
- Jeden Abend um 19 Uhr kommt der **Jarvis Tagesbericht**.
- **Testmodus:** Am Anfang löscht Jarvis nichts. Er setzt nur das Label „Würde löschen“.
- Wenn alles passt, öffne das Skript und ändere oben `TESTMODUS: true` in `TESTMODUS: false`. Danach speichern.

## Anpassen
Oben im Skript unter `EINSTELLUNGEN` kannst du Folgendes ändern:
- `MARKEN`: Marken, die immer im Label „Marken“ landen statt im Papierkorb, z. B. `'rituals.com'`.
- `NIE_LOESCHEN`: Absender oder Domains, die nie aussortiert werden, z. B. `'mama@gmail.com'`.
- `IMMER_DRINGEND`: Absender, die immer als dringend markiert werden.
- `EIGENE_REGELN`: Regeln in Alltagssprache.
- `MODELL`: Mit `'claude-haiku-5-5'` wird es deutlich günstiger.

Nach jeder Änderung auf **Speichern** klicken.

## Ausschalten
Wähle die Funktion **deinstallieren** und klicke auf **Ausführen**.
