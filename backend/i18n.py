"""
Languages of the website.

The page texts live in templates/<lang>/*.html (one folder per language).
This file only holds the short texts that are shared by all pages: menu,
footer, messages shown by the JavaScript, and API error messages.

English is the default language and lives at the root (/, /movies, ...);
every other language gets its own prefix (/nl, /nl/movies, ...).
"""

LANGUAGES = ("en", "nl")
DEFAULT_LANG = "en"

# Shown in the language switch, in the language itself.
LANGUAGE_NAMES = {"en": "English", "nl": "Nederlands"}

# Flag shown in the language switch: static/images/flags/<code>.png
LANGUAGE_FLAGS = {"en": "gb", "nl": "nl"}

UI = {
    "en": {
        "site_name": "The Alignment Puzzle",
        "nav_home": "Home",
        "nav_movies": "Movies",
        "nav_whitepapers": "Whitepapers",
        "nav_contact": "Contact",
        "nav_order": "Order Book",
        "menu_toggle": "Toggle navigation",
        "footer_rights": "All rights reserved.",
        "err_too_many_messages": "Too many messages. Please try again later.",
        "err_wrong_answer": "Incorrect answer to the verification question. Please try again.",
        "err_too_many_orders": "Too many orders. Please try again later.",
        "err_quantity": "Invalid quantity",
        "err_payment": "Payment service unavailable. Please try again later.",
    },
    "nl": {
        "site_name": "De AlignmentPuzzel",
        "nav_home": "Home",
        "nav_movies": "Video's",
        "nav_whitepapers": "Whitepapers",
        "nav_contact": "Contact",
        "nav_order": "Boek bestellen",
        "menu_toggle": "Menu openen of sluiten",
        "footer_rights": "Alle rechten voorbehouden.",
        "err_too_many_messages": "Te veel berichten. Probeer het later opnieuw.",
        "err_wrong_answer": "Onjuist antwoord op de controlevraag. Probeer het opnieuw.",
        "err_too_many_orders": "Te veel bestellingen. Probeer het later opnieuw.",
        "err_quantity": "Ongeldig aantal",
        "err_payment": "De betaaldienst is niet beschikbaar. Probeer het later opnieuw.",
    },
}

# Texts used by static/js/main.js (handed to the page as window.I18N).
JS = {
    "en": {
        "more": "more...",
        "less": "less",
        "sending": "Sending...",
        "contact_ok": "Thank you! Your message has been sent successfully.",
        "contact_error": "Something went wrong. Please try again or email us directly.",
        "contact_failed": "Could not send message. Please try again later.",
        "processing": "Processing...",
        "order_error": "Something went wrong. Please try again.",
        "order_failed": "Could not process order. Please try again later.",
    },
    "nl": {
        "more": "meer...",
        "less": "minder",
        "sending": "Bezig met versturen...",
        "contact_ok": "Bedankt! Je bericht is verstuurd.",
        "contact_error": "Er ging iets mis. Probeer het opnieuw of mail ons rechtstreeks.",
        "contact_failed": "Het bericht kon niet worden verstuurd. Probeer het later opnieuw.",
        "processing": "Bezig...",
        "order_error": "Er ging iets mis. Probeer het opnieuw.",
        "order_failed": "De bestelling kon niet worden verwerkt. Probeer het later opnieuw.",
    },
}


def normalize_lang(lang) -> str:
    """Return lang if we support it, else the default language."""
    return lang if lang in LANGUAGES else DEFAULT_LANG


def lang_url(lang: str, path: str) -> str:
    """URL of a page in the given language, e.g. ("nl", "/movies") -> "/nl/movies"."""
    if lang == DEFAULT_LANG:
        return path
    return f"/{lang}" if path == "/" else f"/{lang}{path}"


def preferred_lang(cookie_lang, accept_language: str):
    """The language the visitor prefers, or None if we can't tell.

    An explicit choice (the "lang" cookie set by the language switch) wins;
    otherwise the browser's language list (Accept-Language header) decides.
    """
    if cookie_lang in LANGUAGES:
        return cookie_lang
    choices = []
    for i, part in enumerate((accept_language or "").split(",")):
        code, _, params = part.strip().partition(";")
        q = 1.0
        if params.strip().startswith("q="):
            try:
                q = float(params.strip()[2:])
            except ValueError:
                q = 0.0
        if code and q > 0:
            choices.append((-q, i, code.split("-")[0].lower()))
    for _, _, code in sorted(choices):
        if code in LANGUAGES:
            return code
    return None
