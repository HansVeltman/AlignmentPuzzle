"""
The Alignment Puzzle - FastAPI Backend
Serves static pages, handles contact form and Mollie payments.
"""

import os
import json
import logging
import html as html_escape
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

# --- Configuration ---
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
ORDERS_DIR = DATA_DIR / "orders"
INVOICES_DIR = DATA_DIR / "invoices"
MOLLIE_API_KEY = os.getenv("MOLLIE_API_KEY", "")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "info@alignmentpuzzle.com")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

BOOK_PRICE = 1.00  # TEMPORARY: lowered for a live test order. REVERT to 45.00.
INVOICE_COUNTER_FILE = DATA_DIR / "invoice_counter.json"
INVOICE_PREFIX = "AP"
INVOICE_START = 9876

# Ensure data directories exist
ORDERS_DIR.mkdir(parents=True, exist_ok=True)
INVOICES_DIR.mkdir(parents=True, exist_ok=True)


def _next_invoice_number() -> str:
    """Get the next sequential invoice number (e.g. AP09876, AP09877, ...)."""
    import filelock
    lock = filelock.FileLock(str(INVOICE_COUNTER_FILE) + ".lock", timeout=10)
    with lock:
        if INVOICE_COUNTER_FILE.exists():
            counter_data = json.loads(INVOICE_COUNTER_FILE.read_text(encoding="utf-8"))
            current = counter_data.get("next", INVOICE_START)
        else:
            current = INVOICE_START
        next_num = current + 1
        INVOICE_COUNTER_FILE.write_text(
            json.dumps({"next": next_num}, indent=2), encoding="utf-8"
        )
    return f"{INVOICE_PREFIX}{current:05d}"

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alignmentpuzzle")

# --- Rate Limiting ---
_rate_limit_store = defaultdict(list)
RATE_LIMIT_WINDOW = 300  # 5 minutes
RATE_LIMIT_MAX_CONTACT = 5  # max contact submissions per window
RATE_LIMIT_MAX_ORDER = 10  # max order submissions per window


def _check_rate_limit(client_ip: str, action: str, max_requests: int) -> bool:
    """Return True if request is allowed, False if rate limited."""
    key = f"{action}:{client_ip}"
    now = time.time()
    _rate_limit_store[key] = [t for t in _rate_limit_store[key] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit_store[key]) >= max_requests:
        return False
    _rate_limit_store[key].append(now)
    return True


# --- App ---
app = FastAPI(title="The Alignment Puzzle", docs_url=None, redoc_url=None)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- Helper: serve template ---
def serve_template(name: str) -> HTMLResponse:
    template_path = TEMPLATES_DIR / name
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Page not found")
    return HTMLResponse(content=template_path.read_text(encoding="utf-8"))


# --- Page Routes ---
@app.get("/sitemap.xml")
async def sitemap():
    sitemap_path = STATIC_DIR / "sitemap.xml"
    return HTMLResponse(content=sitemap_path.read_text(encoding="utf-8"), media_type="application/xml")


@app.get("/", response_class=HTMLResponse)
async def home():
    return serve_template("index.html")


@app.get("/movies", response_class=HTMLResponse)
async def movies():
    return serve_template("movies.html")


@app.get("/whitepapers", response_class=HTMLResponse)
async def whitepapers():
    return serve_template("whitepapers.html")


@app.get("/contact", response_class=HTMLResponse)
async def contact():
    return serve_template("contact.html")


@app.get("/order", response_class=HTMLResponse)
async def order():
    return serve_template("order.html")


# --- Payment success/failure pages ---
@app.get("/order/success", response_class=HTMLResponse)
async def order_success():
    return serve_template("order_success.html")


@app.get("/order/cancelled", response_class=HTMLResponse)
async def order_cancelled():
    return RedirectResponse(url="/order")


# --- API Models ---
class ContactMessage(BaseModel):
    name: str
    email: EmailStr
    subject: str = ""
    message: str
    website: str = ""  # honeypot - must be empty
    human_answer: str = ""  # simple math answer


class OrderRequest(BaseModel):
    name: str
    email: EmailStr
    address: str
    postal_code: str
    city: str
    country: str
    quantity: int = 1


# --- API: Contact Form ---
@app.post("/api/contact")
async def api_contact(msg: ContactMessage, request: Request):
    """Save contact message and optionally send email."""
    client_ip = request.client.host if request.client else "unknown"

    # Rate limiting
    if not _check_rate_limit(client_ip, "contact", RATE_LIMIT_MAX_CONTACT):
        raise HTTPException(status_code=429, detail="Too many messages. Please try again later.")

    # Honeypot check - bots fill in hidden fields
    if msg.website:
        logger.warning(f"Honeypot triggered from {client_ip}")
        return {"success": True, "message": "Message received"}  # fake success

    # Human test - answer must be "7"
    if msg.human_answer.strip() != "7":
        raise HTTPException(status_code=400, detail="Incorrect answer to the verification question. Please try again.")

    logger.info(f"Contact form from {msg.name} <{msg.email}>: {msg.subject}")

    # Escape user input for safe HTML rendering
    safe_name = html_escape.escape(msg.name)
    safe_email = html_escape.escape(msg.email)
    safe_subject = html_escape.escape(msg.subject)
    safe_message = html_escape.escape(msg.message).replace("\n", "<br>")

    # Save to file
    messages_dir = DATA_DIR / "messages"
    messages_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    msg_file = messages_dir / f"{timestamp}_{msg.email}.json"
    msg_file.write_text(json.dumps({
        "name": msg.name,
        "email": msg.email,
        "subject": msg.subject,
        "message": msg.message,
        "timestamp": datetime.now().isoformat()
    }, indent=2), encoding="utf-8")

    try:
        from backend.email_service import _send_email, NOTIFY_EMAIL
        _send_email(
            NOTIFY_EMAIL,
            f"Contact form: {safe_subject or 'No subject'} - from {safe_name}",
            f"""<div style="font-family: Arial, sans-serif; max-width: 600px;">
                <h2 style="color: #1a3a5c;">New Contact Message</h2>
                <p><strong>From:</strong> {safe_name} &lt;{safe_email}&gt;</p>
                <p><strong>Subject:</strong> {safe_subject or 'N/A'}</p>
                <hr style="border-top: 1px solid #ddd;">
                <p>{safe_message}</p>
            </div>"""
        )
    except Exception as e:
        logger.error(f"Failed to send contact notification: {e}")

    return {"success": True, "message": "Message received"}


# --- API: Create Order & Mollie Payment ---
@app.post("/api/order")
async def api_order(order: OrderRequest, request: Request):
    """Create order and redirect to Mollie payment."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip, "order", RATE_LIMIT_MAX_ORDER):
        raise HTTPException(status_code=429, detail="Too many orders. Please try again later.")

    if order.quantity < 1 or order.quantity > 99:
        raise HTTPException(status_code=400, detail="Invalid quantity")

    total = round(BOOK_PRICE * order.quantity, 2)
    order_id = _next_invoice_number()

    # Save order to file
    order_data = {
        "order_id": order_id,
        "name": order.name,
        "email": order.email,
        "address": order.address,
        "postal_code": order.postal_code,
        "city": order.city,
        "country": order.country,
        "quantity": order.quantity,
        "total": total,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }

    order_file = ORDERS_DIR / f"{order_id}.json"
    order_file.write_text(json.dumps(order_data, indent=2), encoding="utf-8")

    # Create Mollie payment
    if not MOLLIE_API_KEY:
        logger.warning("MOLLIE_API_KEY not set - returning test URL")
        return {
            "checkout_url": f"/order/success?order_id={order_id}",
            "order_id": order_id
        }

    try:
        from mollie.api.client import Client as MollieClient

        mollie = MollieClient()
        mollie.set_api_key(MOLLIE_API_KEY)

        payment_data = {
            "amount": {
                "currency": "EUR",
                "value": f"{total:.2f}"
            },
            "description": f"The Alignment Puzzle x{order.quantity} ({order_id})",
            "redirectUrl": f"{BASE_URL}/order/success?order_id={order_id}",
            "metadata": {
                "order_id": order_id
            }
        }

        # Only include webhookUrl when running on a public URL
        if not BASE_URL.startswith("http://localhost"):
            payment_data["webhookUrl"] = f"{BASE_URL}/api/mollie/webhook"

        payment = mollie.payments.create(payment_data)

        # Save Mollie payment ID
        order_data["mollie_payment_id"] = payment.id
        order_file.write_text(json.dumps(order_data, indent=2), encoding="utf-8")

        return {
            "checkout_url": payment.checkout_url,
            "order_id": order_id
        }

    except Exception as e:
        logger.error(f"Mollie payment error: {e}")
        raise HTTPException(status_code=500, detail="Payment service unavailable. Please try again later.")


# --- API: Mollie Webhook ---
@app.post("/api/mollie/webhook")
async def mollie_webhook(request: Request):
    """Handle Mollie payment status updates."""
    form = await request.form()
    payment_id = form.get("id")

    if not payment_id or not MOLLIE_API_KEY:
        return JSONResponse({"status": "ignored"})

    try:
        from mollie.api.client import Client as MollieClient

        mollie = MollieClient()
        mollie.set_api_key(MOLLIE_API_KEY)

        payment = mollie.payments.get(payment_id)
        order_id = payment.metadata.get("order_id") if payment.metadata else None

        if order_id:
            order_file = ORDERS_DIR / f"{order_id}.json"
            if order_file.exists():
                order_data = json.loads(order_file.read_text(encoding="utf-8"))
                order_data["status"] = payment.status
                order_data["paid_at"] = payment.paid_at if payment.is_paid() else None
                order_file.write_text(json.dumps(order_data, indent=2), encoding="utf-8")

                logger.info(f"Order {order_id} status updated to: {payment.status}")

                if payment.is_paid():
                    from backend.email_service import (
                        send_order_notification,
                        send_order_confirmation,
                        _generate_invoice_pdf,
                    )

                    # Always keep a permanent invoice copy on disk, independent of
                    # whether the emails succeed. This is our safety net.
                    try:
                        pdf_bytes = _generate_invoice_pdf(order_data)
                        (INVOICES_DIR / f"Invoice-{order_id}.pdf").write_bytes(pdf_bytes)
                    except Exception as pdf_err:
                        logger.error(f"Could not save invoice PDF for {order_id}: {pdf_err}", exc_info=True)

                    # Send owner notification + customer confirmation, and record
                    # whether each actually went out so a failure is never silent.
                    owner_ok = customer_ok = False
                    try:
                        owner_ok = send_order_notification(order_data)
                        customer_ok = send_order_confirmation(order_data)
                    except Exception as email_err:
                        logger.error(f"Email error for {order_id}: {email_err}", exc_info=True)

                    order_data["owner_email_sent"] = bool(owner_ok)
                    order_data["customer_email_sent"] = bool(customer_ok)
                    order_file.write_text(json.dumps(order_data, indent=2), encoding="utf-8")

                    if not (owner_ok and customer_ok):
                        logger.error(
                            f"EMAIL DELIVERY FAILED for paid order {order_id}: "
                            f"owner_sent={owner_ok}, customer_sent={customer_ok}, "
                            f"customer={order_data.get('email')}. "
                            f"Invoice saved to disk; resend with resend_invoices.py."
                        )

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)

    return JSONResponse({"status": "ok"})


# --- API: Export Orders as CSV via email ---
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")


@app.get("/api/admin/export-orders")
async def export_orders(secret: str = ""):
    """Export all orders as CSV and email to admin."""
    if not ADMIN_SECRET or secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    import csv
    import io

    orders = []
    if ORDERS_DIR.exists():
        for f in sorted(ORDERS_DIR.glob("*.json")):
            try:
                orders.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue

    if not orders:
        return JSONResponse({"message": "No orders found"})

    # Calculate VAT fields
    VAT_RATE = 0.09
    for order in orders:
        total_incl = order.get("total", 0)
        total_excl = round(total_incl / (1 + VAT_RATE), 2)
        order["total_excl_vat"] = total_excl
        order["vat_amount"] = round(total_incl - total_excl, 2)
        order["total_incl_vat"] = total_incl

    # Build CSV
    output = io.StringIO()
    fields = ["order_id", "name", "email", "address", "postal_code", "city",
              "country", "quantity", "total_excl_vat", "vat_amount", "total_incl_vat",
              "status", "created_at", "paid_at", "owner_email_sent", "customer_email_sent"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for order in orders:
        writer.writerow(order)

    csv_bytes = output.getvalue().encode("utf-8")

    from backend.email_service import _send_email
    _send_email(
        CONTACT_EMAIL,
        f"Order Export - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"""<div style="font-family: Arial, sans-serif;">
            <h2 style="color: #1a3a5c;">Order Export</h2>
            <p>Attached is a CSV export of all {len(orders)} orders.</p>
        </div>""",
        attachments=[(f"orders-{datetime.now().strftime('%Y%m%d')}.csv", csv_bytes)]
    )

    return JSONResponse({"message": f"CSV with {len(orders)} orders emailed to {CONTACT_EMAIL}"})


# --- Run ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
