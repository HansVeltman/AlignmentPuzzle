"""
Regenerate and (optionally) re-send the invoice + confirmation email for orders
whose confirmation email failed to go out (e.g. the July 17 orders).

It reuses the EXACT same invoice + email code as the live website
(backend/email_service.py), so the customer gets precisely what they would
normally have received.

SAFE 3-STAGE WORKFLOW
---------------------
  1. PREVIEW (default) : make the PDFs, save them to data/invoices/, send NOTHING.
  2. --test            : email the confirmation to YOURSELF (info@) to review it.
  3. --send            : email the REAL customers.

USAGE (run from the project root)
---------------------------------
  python resend_invoices.py AP09877 AP09878           # preview only, no email
  python resend_invoices.py --test AP09877 AP09878    # send a copy to info@
  python resend_invoices.py --send AP09877 AP09878    # send to the customers

The order IDs are the invoice numbers you saw in the CSV / on the order files.
Each order must exist as data/orders/<ORDER_ID>.json.
"""

import sys
import json
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from backend.email_service import (
    _generate_invoice_pdf,
    send_order_confirmation,
    NOTIFY_EMAIL,
)

ORDERS_DIR = BASE_DIR / "data" / "orders"
INVOICES_DIR = BASE_DIR / "data" / "invoices"


def load_order(order_id: str):
    f = ORDERS_DIR / f"{order_id}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def main():
    args = list(sys.argv[1:])
    mode = "preview"
    if "--send" in args:
        mode = "send"
        args.remove("--send")
    if "--test" in args:
        mode = "test"
        args.remove("--test")

    order_ids = args
    if not order_ids:
        print("Usage: python resend_invoices.py [--test|--send] ORDER_ID [ORDER_ID ...]")
        print("Example: python resend_invoices.py AP09877 AP09878")
        return

    INVOICES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print(f" Resend invoices - MODE: {mode.upper()}")
    if mode == "send":
        print(" >>> This will email the REAL customers. <<<")
    print("=" * 64)

    for oid in order_ids:
        order = load_order(oid)
        if not order:
            print(f"\n  [SKIP] {oid}: no file found at data/orders/{oid}.json")
            continue

        # Always regenerate and save a permanent PDF copy on disk.
        # If the file is currently open in a viewer it stays locked on Windows;
        # that must not stop the email, which builds its own fresh PDF anyway.
        pdf_bytes = _generate_invoice_pdf(order)
        out = INVOICES_DIR / f"Invoice-{order['order_id']}.pdf"
        try:
            out.write_bytes(pdf_bytes)
            saved_note = f"saved -> {out}"
        except PermissionError:
            saved_note = f"could NOT save (is {out.name} open? close it) - email unaffected"

        print(f"\n  Order {order['order_id']}")
        print(f"    Customer : {order['name']} <{order['email']}>")
        print(f"    Ship to  : {order['address']}, {order['postal_code']} "
              f"{order['city']}, {order['country']}")
        print(f"    Quantity : {order['quantity']}   Total: EUR {order['total']:.2f}")
        print(f"    Invoice  : {saved_note}")

        if mode == "preview":
            print("    Email    : (preview mode - nothing sent)")
        elif mode == "test":
            original = order["email"]
            order["email"] = NOTIFY_EMAIL          # send the copy to yourself
            send_order_confirmation(order)
            order["email"] = original
            print(f"    Email    : TEST copy sent to {NOTIFY_EMAIL}")
        elif mode == "send":
            send_order_confirmation(order)
            print(f"    Email    : confirmation + invoice sent to {order['email']}")

    print("\nDone.")
    if mode == "preview":
        print("Next: open the PDFs in data/invoices/ and check name, address, amount.")
        print("When correct, send a test copy to yourself:")
        print("   python resend_invoices.py --test " + " ".join(order_ids))


if __name__ == "__main__":
    main()
