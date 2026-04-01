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


PROJECTSTRUCTUUR
----------------
backend/
    app.py              Hoofdapplicatie (FastAPI)
templates/
    index.html          Home pagina
    movies.html         Video's pagina
    whitepapers.html    Whitepapers pagina
    contact.html        Contactformulier
    order.html          Bestelpagina
    order_success.html  Bevestigingspagina na betaling
static/
    css/style.css       Stijlen
    js/main.js          Client-side JavaScript
    images/             Afbeeldingen
    pdfs/               Downloadbare PDF's
data/
    messages/           Opgeslagen contactberichten (JSON)
    orders/             Opgeslagen bestellingen (JSON)
run.py                  Startscript
requirements.txt        Python dependencies
.env                    Configuratie (niet in git)
.env.example            Voorbeeld configuratie
