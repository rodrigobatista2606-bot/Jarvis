# Jarvis

Dein persönlicher Assistent als Home-Assistant-Add-on.

**Was er heute kann (Version 0.1):**
- Er liest **Gmail** und **Outlook** alle 10 Minuten.
- **Spam und Werbung** verschiebt er in den Papierkorb, **Newsletter** in den Ordner „Newsletter“.
- **Wichtige Mails** fasst er dir per **WhatsApp** zusammen.
- Bei **dringenden Mails von Behörden oder offiziellen Stellen** schreibt er sofort und **ruft dich an**. In der Ruhezeit (22–7 Uhr) holt er den Anruf morgens nach.
- **Jeden Abend um 19 Uhr** ruft er an und gibt dir ein Update. Dasselbe Update kommt zusätzlich per WhatsApp.

**Sicherheit:**
- Beim ersten Start läuft Jarvis im **Testmodus**: Er sortiert nur zum Schein. Was er getan hätte, siehst du im Abend-Update. Wenn du zufrieden bist, schaltest du den Testmodus aus.
- Gelöschte Mails landen im **Papierkorb**. Dort bleiben sie 30 Tage und lassen sich wiederherstellen.
- Der Teil, der Mails liest, kann **nichts steuern**. Eine Mail mit versteckten Anweisungen kann also nichts anrichten.

---

## Einrichtung Schritt für Schritt

### 1. Home Assistant
1. Stell den Home Assistant Green auf und folge der Einrichtung unter `http://homeassistant.local:8123`.
2. Gehe zu **Einstellungen → Add-ons → Add-on Store**. Wähle oben rechts **⋮ → Repositories** und füge die Adresse dieses GitHub-Repositorys hinzu.
   *Ist das Repository privat, gibt es eine Besonderheit. Claude hilft dir dabei.*
3. Wähle **Jarvis → Installieren**. Die Einstellungen kommen noch nicht hier rein, sondern im nächsten Schritt.

### 2. Claude (das Gehirn)
1. Registriere dich auf **console.anthropic.com** und lade ein Guthaben auf, z. B. 10 €.
2. Wähle **API Keys → Create Key** und kopiere den Schlüssel.
3. Trag ihn im Add-on unter **Konfiguration** bei *Claude-API-Schlüssel* ein.

> Kosten: Mit dem Standardmodell (`claude-opus-5-5`) kostet eine Mail ungefähr 1 Cent. Bei 50 Mails am Tag sind das rund 10–15 € im Monat.
> Mit `claude-haiku-5-5` sind es nur Cent-Beträge im Monat. Haiku ist dafür etwas weniger treffsicher.

### 3. Gmail
1. Schalte die **Bestätigung in zwei Schritten** im Google-Konto ein, falls sie noch aus ist.
2. Öffne **myaccount.google.com/apppasswords** und lege ein App-Passwort mit dem Namen „Jarvis“ an.
3. Trag deine Gmail-Adresse und das 16-stellige Passwort im Add-on ein.

### 4. Outlook
Microsoft verlangt dafür eine kleine „App-Registrierung“. Das ist kostenlos und dauert etwa 10 Minuten:
1. Öffne **portal.azure.com** und melde dich mit deinem Outlook-Konto an. Microsoft fragt dabei eventuell nach einem kostenlosen Azure-Konto.
2. Wähle **App-Registrierungen → Neue Registrierung**. Name: `Jarvis`. Kontotyp: **„Nur persönliche Microsoft-Konten“**. Dann auf **Registrieren**.
3. Kopiere die **Anwendungs-ID (Client-ID)**.
4. Stelle unter **Authentifizierung** den Punkt **„Öffentliche Clientflows zulassen“** auf **Ja** und speichere.
5. Wähle **API-Berechtigungen → Berechtigung hinzufügen → Microsoft Graph → Delegierte Berechtigungen** und setze einen Haken bei **Mail.ReadWrite**.
6. Schalte im Add-on *Outlook verwenden* ein und trag die Client-ID ein.
7. Nach dem Start schickt dir Jarvis per WhatsApp einen Code. Öffne **microsoft.com/devicelogin**, gib den Code ein und bestätige. Das ist nur einmal nötig.

### 5. Twilio (WhatsApp + Anrufe)
1. Registriere dich auf **twilio.com** und wechsle auf ein bezahltes Konto. Ein Testkonto kann nur eingeschränkt anrufen.
2. Kaufe eine **Telefonnummer**. Für eine deutsche Nummer will Twilio einen Adressnachweis, das ist einmalig.
3. Kopiere **Account SID** und **Auth Token** aus der Twilio-Konsole ins Add-on.
4. Trag diese Nummer bei *Anruf-Nummer von Jarvis* ein.
5. **WhatsApp:** Wähle unter **Messaging → Senders → WhatsApp Senders** die Nummer und verbinde sie mit einem Meta-Business-Konto. Twilio führt dich durch die Schritte. Die Freigabe durch Meta kann ein paar Tage dauern.
6. **Vorlage**, damit Jarvis dir jederzeit schreiben darf: Lege unter **Messaging → Content Template Builder** eine Vorlage an.
   - Typ: Text
   - Kategorie: *Utility*
   - Inhalt: `Nachricht von Jarvis: {{1}}`
   - Nach der Genehmigung die **Content SID** (beginnt mit `HX…`) im Add-on eintragen.
7. Trag deine eigene Handynummer mit `+49…` bei *Deine Handynummer* ein.

### 6. Starten
1. Klicke auf **Starten** und schau in den Reiter **Protokoll**. Dort steht, was Jarvis gerade macht.
2. Es kommt eine WhatsApp: „Hallo, hier ist Jarvis“.
3. Prüfe ein paar Tage lang die Abend-Updates. Wenn alles passt, schalte den **Testmodus** aus.

## Anpassen
- **Nie löschen:** Adressen oder Domains, die nie aussortiert werden, z. B. `mama@gmail.com` oder `meinverein.de`.
- **Immer dringend:** Bei diesen Absendern ruft Jarvis immer an.
- **Eigene Regeln:** In Alltagssprache, z. B. *„Mails von meinem Vermieter sind wichtig“* oder *„Paketbenachrichtigungen sind normal“*.

## Für Entwickler
```bash
cd jarvis && pip install -r requirements.txt pytest && python -m pytest
```
