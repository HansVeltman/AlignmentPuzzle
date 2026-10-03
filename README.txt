========================================
 The Alignment Puzzle - Website Project
========================================

Website voor www.alignmentpuzzle.com
Gebouwd met Python (FastAPI) en JavaScript.


VEREISTEN
---------
- Python 3.10 of hoger (https://www.python.org/downloads/)
- pip (wordt meegeleverd met Python)


INSTALLATIE
-----------
1. Open een terminal/command prompt in deze projectmap.

2. (Aanbevolen) Maak een virtuele omgeving aan:

       python -m venv venv

3. Activeer de virtuele omgeving:

   Windows (Command Prompt):
       venv\Scripts\activate

   Windows (PowerShell):
       venv\Scripts\Activate.ps1

   Linux/Mac:
       source venv/bin/activate

4. Installeer de benodigde packages:

       pip install -r requirements.txt

5. Maak een .env bestand aan op basis van het voorbeeld:

       copy .env.example .env

   Pas daarna de waarden in .env aan met je eigen gegevens
   (Mollie API key, SMTP-instellingen, etc.).


STARTEN
-------
Start de website met:

    python run.py

De website draait nu op:

    http://127.0.0.1:8000

Open dit adres in je browser om het resultaat te bekijken.
De server herlaadt automatisch bij codewijzigingen (hot reload).
Stoppen doe je met Ctrl+C in de terminal.


PAGINA'S
--------
- http://127.0.0.1:8000/            Home pagina
- http://127.0.0.1:8000/movies      Video's
- http://127.0.0.1:8000/whitepapers Whitepapers en downloads
- http://127.0.0.1:8000/contact     Contactformulier
- http://127.0.0.1:8000/order       Boek bestellen

Elke pagina bestaat ook in het Nederlands, met /nl ervoor:
- http://127.0.0.1:8000/nl          Home (Nederlands)
- http://127.0.0.1:8000/nl/movies   enzovoort
Een bezoeker met een Nederlandstalige browser gaat automatisch naar /nl;
met de taalknop rechtsboven wissel je (de keuze wordt onthouden).


PROJECTSTRUCTUUR
----------------
backend/
    app.py              Hoofdapplicatie (FastAPI)
    i18n.py             Talen + korte vaste teksten (menu, voet, meldingen)
    email_service.py    E-mails en factuur (teksten per taal bovenin)
templates/
    base.html           Gedeelde kop, menu met taalknop en voet
    en/                 Engelse pagina's
    nl/                 Nederlandse pagina's (zelfde bestandsnamen)
        index.html          Home pagina
        movies.html         Video's pagina
        whitepapers.html    Whitepapers pagina
        contact.html        Contactformulier
        order.html          Bestelpagina
        order_success.html  Bevestigingspagina na betaling
    Een tekst aanpassen? Pas hem aan in en/ EN in nl/.
content/
    en/movies.json      Video's op de Engelse site (titel + YouTube-link)
    nl/movies.json      Video's op de Nederlandse site
    Video toevoegen/wijzigen: alleen dit bestand aanpassen. Elke YouTube-link
    werkt (youtube.com/watch?v=..., youtu.be/..., shorts/...).
static/
    css/style.css       Stijlen
    js/main.js          Client-side JavaScript
    images/             Gedeelde afbeeldingen (logo, auteurs, icoontjes)
    images/en/          Afbeeldingen met Engelse tekst
    images/nl/          Dezelfde afbeeldingen in het Nederlands (zelfde bestandsnaam)
    pdfs/en/            Engelse whitepapers
    pdfs/nl/            Nederlandse whitepapers
    Oude links naar /static/pdfs/<bestand> worden automatisch doorgestuurd.
data/
    messages/           Opgeslagen contactberichten (JSON)
    orders/             Opgeslagen bestellingen (JSON)
run.py                  Startscript
requirements.txt        Python dependencies
.env                    Configuratie (niet in git)
.env.example            Voorbeeld configuratie
