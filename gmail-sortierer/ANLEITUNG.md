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

## Schritt 5: Übersichtsseite einrichten
1. Klicke im Skript oben rechts auf **Bereitstellen → Neue Bereitstellung**.
2. Klicke beim Zahnrad neben „Typ auswählen“ auf **Web-App**.
3. Stell die Felder so ein:
   - Beschreibung: `Jarvis`
   - **Ausführen als: Ich**
   - **Zugriff: Nur ich**
4. Klicke auf **Bereitstellen** und kopiere die **Web-App-URL**.
5. Öffne die URL am Handy und speichere sie als Lesezeichen oder auf dem Startbildschirm. Das ist deine **Jarvis Übersicht**.

In der Übersicht siehst du alle Mails nach Gruppen sortiert: Dringend, Wichtig, Marken, Normal und Löschvorschläge. Zu jeder Mail gibt es eine kurze Zusammenfassung und diese Knöpfe:
- **Löschen**
- **Erledigt** (archivieren)
- **Abbestellen**
- **Öffnen**

Für eine ganze Gruppe gibt es außerdem **„Alle löschen“**.

Jarvis prüft **alle** Mails im Posteingang. Ältere Mails arbeitet er nach und nach im Hintergrund ab, etwa 100–300 pro 10 Minuten. Bis dahin zeigt die Übersicht oben, wie viele noch warten.

Jeden Abend um 19 Uhr kommt der **Jarvis Tagesbericht** mit einem Link zur Übersicht.

## Schritt 6: Testmodus ausschalten (wenn alles passt)
- **Im Testmodus** löscht Jarvis nichts von selbst. Du löschst per Knopf in der Übersicht.
- **Mit `TESTMODUS: false`** landen Spam, Werbung und Newsletter automatisch im Papierkorb. Für 7 Tage kannst du sie in der Übersicht unter „Von Jarvis gelöscht“ wiederherstellen.

## Code aktualisieren
Wenn es eine neue Version gibt:
1. Kopiere den neuen Code aus `Code.gs`, ersetze damit den alten Code im Editor und speichere.
2. Führe **installieren** einmal aus.
3. Hast du die Web-App schon eingerichtet, wähle **Bereitstellen → Bereitstellungen verwalten**, klicke auf den **Stift**, stell die **Version** auf **„Neue Version“** und klicke auf **Bereitstellen**. Die URL bleibt dabei gleich.

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
