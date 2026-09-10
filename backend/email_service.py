"""
Email service for The Alignment Puzzle.
Sends order notifications and customer confirmations via SMTP,
with PDF invoice attachment.
"""

import os
import io
import time
import logging
import smtplib
import threading
import html as html_escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from pathlib import Path
from fpdf import FPDF

logger = logging.getLogger("alignmentpuzzle")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.hostnet.nl")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "info@alignmentpuzzle.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = "info@alignmentpuzzle.com"
NOTIFY_EMAIL = os.getenv("CONTACT_EMAIL", "info@alignmentpuzzle.com")

VAT_RATE = 0.09

# The invoice uses Open Sans (bundled, free OFL licence) instead of the PDF
# built-in Helvetica. Helvetica only knows Western European letters, so a
# customer name or address with e.g. ł, ř, ő, ’, – or € made the invoice crash.
# Open Sans also covers Greek and Cyrillic (we ship to GR, CY and BG).
FONTS_DIR = Path(__file__).resolve().parent / "fonts"
INVOICE_FONT = "OpenSans"


def _send_email(to_email: str, subject: str, html_body: str, attachments=None):
    """Send an email via SMTP with optional attachments."""
    if not SMTP_PASSWORD:
        logger.error(
            "SMTP_PASSWORD not set - CANNOT SEND EMAIL. "
            "Set the SMTP_PASSWORD environment variable (see render.yaml)."
        )
        return False

    msg = MIMEMultipart("mixed")
    msg["From"] = f"The Alignment Puzzle <{FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    html_part = MIMEMultipart("alternative")
    html_part.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(html_part)

    if attachments:
        for filename, data in attachments:
            part = MIMEApplication(data, Name=filename)
            part["Content-Disposition"] = f'attachment; filename="{filename}"'
            msg.attach(part)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        request_mail_check()  # re-test the mail server now, so the banner appears quickly
        return False


# --- Mail server monitor ---
# A background thread regularly tests that we can LOG IN to the SMTP server
# (no email is sent). While that fails, the website shows a red warning banner
# (see serve_template in app.py), so a broken mail setup such as an expired
# password is visible on the site instead of failing silently.
MAIL_CHECK_INTERVAL_OK = 30 * 60     # re-test every 30 minutes while mail works
MAIL_CHECK_INTERVAL_ERROR = 5 * 60   # re-test every 5 minutes while it is broken
MAIL_CHECK_RETRY_DELAY = 30          # a failed test is repeated once before we call it broken

_mail_ok = True
_mail_check_now = threading.Event()


def _smtp_login_works() -> bool:
    """Try to log in to the SMTP server without sending anything."""
    if not SMTP_PASSWORD:
        logger.error("Mail server check: SMTP_PASSWORD not set")
        return False
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
        return True
    except Exception as e:
        logger.error(f"Mail server check: login failed: {e}")
        return False


def _mail_monitor_loop():
    global _mail_ok
    while True:
        ok = _smtp_login_works()
        if not ok:
            # Test once more, so a single network hiccup doesn't show the banner.
            time.sleep(MAIL_CHECK_RETRY_DELAY)
            ok = _smtp_login_works()

        if ok and not _mail_ok:
            logger.info("Mail server check: OK again - warning banner removed")
        elif not ok and _mail_ok:
            logger.error("MAIL SERVER DOWN - warning banner is now shown on the website")
        _mail_ok = ok

        _mail_check_now.wait(MAIL_CHECK_INTERVAL_OK if ok else MAIL_CHECK_INTERVAL_ERROR)
        _mail_check_now.clear()


def start_mail_monitor():
    """Start the background mail server check (call once at app startup)."""
    threading.Thread(target=_mail_monitor_loop, name="mail-monitor", daemon=True).start()


def mail_server_ok() -> bool:
    """Result of the most recent mail server check."""
    return _mail_ok


def request_mail_check():
    """Ask the monitor to re-test the mail server right away."""
    _mail_check_now.set()


def _safe(value) -> str:
    """Escape a value for safe HTML rendering."""
    return html_escape.escape(str(value))


def _generate_invoice_pdf(order_data: dict) -> bytes:
    """Generate a PDF invoice and return as bytes."""
    quantity = order_data["quantity"]
    total_incl = order_data["total"]
    total_excl = round(total_incl / (1 + VAT_RATE), 2)
    total_vat = round(VAT_RATE / (1 + VAT_RATE) * total_incl, 2)
    unit_price_incl = round(total_incl / quantity, 2)
    unit_excl = round(unit_price_incl / (1 + VAT_RATE), 2)
    order_date = datetime.fromisoformat(order_data["created_at"]).strftime("%d %B %Y")

    header_path = Path(__file__).resolve().parent.parent / "static" / "images" / "logo_02.jpg"

    pdf = FPDF()
    pdf.add_font(INVOICE_FONT, "", str(FONTS_DIR / "OpenSans-Regular.ttf"))
    pdf.add_font(INVOICE_FONT, "B", str(FONTS_DIR / "OpenSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Header logo, placed at a natural letterhead size (top-left).
    # NOTE: we deliberately do NOT stretch the logo across the full page width.
    # The source logo is low-resolution; blowing it up to 210mm magnifies it
    # and makes it look blurry/pixelated. Placing it small keeps it crisp.
    # We also trim any surrounding white border so the logo sits neatly.
    header_bottom = 12
    if header_path.exists():
        from PIL import Image as PILImage, ImageChops
        logo_img = PILImage.open(header_path).convert("RGB")
        bg = PILImage.new("RGB", logo_img.size, (255, 255, 255))
        bbox = ImageChops.difference(logo_img, bg).getbbox()
        if bbox:
            logo_img = logo_img.crop(bbox)
        img_w, img_h = logo_img.size

        logo_height_mm = 13          # letterhead-sized logo
        logo_width_mm = (img_w / img_h) * logo_height_mm
        if logo_width_mm > 120:      # safety cap so a wide logo never overflows
            logo_width_mm = 120
            logo_height_mm = (img_h / img_w) * logo_width_mm

        pdf.image(logo_img, x=10, y=12, w=logo_width_mm, h=logo_height_mm)
        header_bottom = 12 + logo_height_mm + 6

    # Sender address below header
    pdf.set_y(header_bottom)
    pdf.set_font(INVOICE_FONT, "", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 4, "The Alignment Puzzle | Posthoornstraat 11 | 3011 WD Rotterdam | Holland",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # Invoice title
    pdf.ln(2)
    pdf.set_font(INVOICE_FONT, "B", 16)
    pdf.cell(0, 10, "INVOICE", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Invoice details
    pdf.set_font(INVOICE_FONT, "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(40, 6, "Invoice number:")
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, order_data["order_id"], new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(100, 100, 100)
    pdf.cell(40, 6, "Date:")
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, order_date, new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(100, 100, 100)
    pdf.cell(40, 6, "Payment status:")
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, "Paid", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Ship to
    pdf.set_font(INVOICE_FONT, "B", 11)
    pdf.set_text_color(26, 58, 92)
    pdf.cell(0, 8, "Ship to:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(INVOICE_FONT, "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, order_data["name"], new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, order_data["address"], new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"{order_data['postal_code']} {order_data['city']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, order_data["country"], new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # Line separator
    pdf.set_draw_color(26, 58, 92)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # Table header
    pdf.set_font(INVOICE_FONT, "B", 10)
    pdf.set_fill_color(245, 247, 250)
    col_desc = 90
    col_qty = 25
    col_unit = 35
    col_amount = 35
    pdf.cell(col_desc, 8, "Description", border=0, fill=True)
    pdf.cell(col_qty, 8, "Qty", border=0, align="C", fill=True)
    pdf.cell(col_unit, 8, "Unit price", border=0, align="R", fill=True)
    pdf.cell(col_amount, 8, "Amount", border=0, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")

    # Table row
    pdf.set_font(INVOICE_FONT, "", 10)
    pdf.cell(col_desc, 7, "The Alignment Puzzle")
    pdf.cell(col_qty, 7, str(quantity), align="C")
    pdf.cell(col_unit, 7, f"EUR {unit_excl:.2f}", align="R")
    pdf.cell(col_amount, 7, f"EUR {total_excl:.2f}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(INVOICE_FONT, "", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(col_desc, 5, "Business Engineering for Aligned Organizations (2nd ed.)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    # Separator
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.2)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # Totals
    pdf.set_font(INVOICE_FONT, "", 10)
    x_label = 120
    x_value = 165

    pdf.set_x(x_label)
    pdf.cell(45, 7, "Subtotal (excl. VAT):")
    pdf.cell(35, 7, f"EUR {total_excl:.2f}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x_label)
    pdf.cell(45, 7, "VAT (9%):")
    pdf.cell(35, 7, f"EUR {total_vat:.2f}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x_label)
    pdf.cell(45, 7, "Shipping:")
    pdf.cell(35, 7, "Included", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.set_draw_color(26, 58, 92)
    pdf.set_line_width(0.5)
    pdf.line(x_label, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    pdf.set_font(INVOICE_FONT, "B", 13)
    pdf.set_x(x_label)
    pdf.cell(45, 10, "Total:")
    pdf.cell(35, 10, f"EUR {total_incl:.2f}", align="R", new_x="LMARGIN", new_y="NEXT")

    # Footer
    pdf.ln(20)
    pdf.set_font(INVOICE_FONT, "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "The Alignment Puzzle | info@alignmentpuzzle.com | www.alignmentpuzzle.com", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Thank you for your order!", align="C", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


def _invoice_attachments(order_data: dict, invoice_pdf):
    if invoice_pdf is None:
        return None
    return [(f"Invoice-{order_data['order_id']}.pdf", invoice_pdf)]


def send_order_notification(order_data: dict, invoice_pdf):
    """Send order notification to the shop owner with the PDF invoice.

    invoice_pdf is None when the invoice could not be generated; the owner is
    then still notified, with a warning to send the invoice manually.
    """
    subject = f"New order {order_data['order_id']} - {order_data['quantity']}x The Alignment Puzzle"
    warning = ""
    if invoice_pdf is None:
        subject += " - FACTUUR ONTBREEKT"
        warning = """
        <div style="background: #c62828; color: #fff; padding: 12px 16px; border-radius: 6px;">
            <strong>Let op: de factuur kon niet worden gemaakt, stuur hem handmatig.</strong><br>
            De klant heeft de bevestiging gekregen met de melding dat de factuur apart volgt.
        </div>"""

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        {warning}
        <h2 style="color: #1a3a5c;">New Order Received</h2>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Order ID</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{_safe(order_data['order_id'])}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Customer</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{_safe(order_data['name'])}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Email</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{_safe(order_data['email'])}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Address</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{_safe(order_data['address'])}<br>
                    {_safe(order_data['postal_code'])} {_safe(order_data['city'])}<br>
                    {_safe(order_data['country'])}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Quantity</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{order_data['quantity']}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Total</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">&euro; {order_data['total']:.2f}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Paid at</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{_safe(order_data.get('paid_at', 'N/A'))}</td></tr>
        </table>
        <p style="color: #666;">{"The invoice PDF is attached. " if invoice_pdf is not None else ""}Please ship the order to the address above.</p>
    </div>
    """

    return _send_email(NOTIFY_EMAIL, subject, html,
                       attachments=_invoice_attachments(order_data, invoice_pdf))


def send_order_confirmation(order_data: dict, invoice_pdf):
    """Send order confirmation with the PDF invoice to the customer.

    invoice_pdf is None when the invoice could not be generated; the customer
    then still gets the confirmation, saying the invoice will follow separately.
    """
    quantity = order_data['quantity']
    total_incl = order_data['total']
    total_excl = round(total_incl / (1 + VAT_RATE), 2)
    total_vat = round(VAT_RATE / (1 + VAT_RATE) * total_incl, 2)
    unit_price_incl = round(total_incl / quantity, 2)
    unit_excl = round(unit_price_incl / (1 + VAT_RATE), 2)
    order_date = datetime.fromisoformat(order_data['created_at']).strftime("%d %B %Y")

    subject = f"Order Confirmation - {order_data['order_id']}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
        <div style="background: #1a3a5c; padding: 24px; text-align: center;">
            <h1 style="color: #fff; margin: 0; font-size: 22px;">The Alignment Puzzle</h1>
        </div>

        <div style="padding: 32px 24px;">
            <p>Dear {_safe(order_data['name'])},</p>
            <p>Thank you for your order! Your payment has been received. {"Your invoice is attached as a PDF." if invoice_pdf is not None else "Your invoice will follow separately."}</p>

            <div style="background: #f5f7fa; border-radius: 8px; padding: 24px; margin: 24px 0;">
                <h2 style="color: #1a3a5c; margin-top: 0; font-size: 18px;">Order Summary</h2>
                <table style="width: 100%; font-size: 14px;">
                    <tr><td style="color: #666; padding: 4px 0;">Order number:</td>
                        <td style="text-align: right; padding: 4px 0;">{order_data['order_id']}</td></tr>
                    <tr><td style="color: #666; padding: 4px 0;">Date:</td>
                        <td style="text-align: right; padding: 4px 0;">{order_date}</td></tr>
                    <tr><td style="color: #666; padding: 4px 0;">Quantity:</td>
                        <td style="text-align: right; padding: 4px 0;">{quantity}x The Alignment Puzzle</td></tr>
                    <tr style="font-weight: bold; border-top: 1px solid #ddd;">
                        <td style="padding: 8px 0;">Total:</td>
                        <td style="text-align: right; padding: 8px 0;">&euro; {total_incl:.2f}</td></tr>
                </table>
            </div>

            <p>Your book will be shipped to:</p>
            <p style="background: #f5f7fa; padding: 16px; border-radius: 8px;">
                {_safe(order_data['name'])}<br>
                {_safe(order_data['address'])}<br>
                {_safe(order_data['postal_code'])} {_safe(order_data['city'])}<br>
                {_safe(order_data['country'])}
            </p>

            <p>You will receive a separate email when your order has been dispatched.</p>

            <p style="margin-top: 32px;">Kind regards,<br>
            <strong>The Alignment Puzzle Team</strong><br>
            Hans Veltman, Jacques Adriaansen, Peter Morren &amp; Rob Kwikkers</p>
        </div>

        <div style="background: #f5f7fa; padding: 16px 24px; text-align: center; font-size: 12px; color: #999;">
            <p>&copy; 2026 The Alignment Puzzle | info@alignmentpuzzle.com | www.alignmentpuzzle.com</p>
        </div>
    </div>
    """

    return _send_email(order_data['email'], subject, html,
                       attachments=_invoice_attachments(order_data, invoice_pdf))
