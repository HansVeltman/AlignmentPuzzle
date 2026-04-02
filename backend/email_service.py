"""
Email service for The Alignment Puzzle.
Sends order notifications and customer confirmations via SMTP.
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger("alignmentpuzzle")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.hostnet.nl")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "info@alignmentpuzzle.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = "info@alignmentpuzzle.com"
NOTIFY_EMAIL = os.getenv("CONTACT_EMAIL", "info@alignmentpuzzle.com")

VAT_RATE = 0.21
BOOK_PRICE_INCL = 45.00
BOOK_PRICE_EXCL = round(BOOK_PRICE_INCL / (1 + VAT_RATE), 2)


def _send_email(to_email: str, subject: str, html_body: str):
    """Send an email via SMTP."""
    if not SMTP_PASSWORD:
        logger.warning("SMTP_PASSWORD not set - skipping email")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"The Alignment Puzzle <{FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_order_notification(order_data: dict):
    """Send order notification to the shop owner."""
    subject = f"New order {order_data['order_id']} - {order_data['quantity']}x The Alignment Puzzle"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1a3a5c;">New Order Received</h2>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Order ID</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{order_data['order_id']}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Customer</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{order_data['name']}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Email</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{order_data['email']}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Address</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{order_data['address']}<br>
                    {order_data['postal_code']} {order_data['city']}<br>
                    {order_data['country']}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Quantity</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{order_data['quantity']}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Total</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">&euro; {order_data['total']:.2f}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Paid at</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{order_data.get('paid_at', 'N/A')}</td></tr>
        </table>
        <p style="color: #666;">Please ship the order to the address above.</p>
    </div>
    """

    _send_email(NOTIFY_EMAIL, subject, html)


def send_order_confirmation(order_data: dict):
    """Send order confirmation with invoice to the customer."""
    quantity = order_data['quantity']
    total_incl = order_data['total']
    total_excl = round(BOOK_PRICE_EXCL * quantity, 2)
    total_vat = round(total_incl - total_excl, 2)
    unit_excl = BOOK_PRICE_EXCL
    order_date = datetime.fromisoformat(order_data['created_at']).strftime("%d %B %Y")

    subject = f"Order Confirmation - {order_data['order_id']}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
        <div style="background: #1a3a5c; padding: 24px; text-align: center;">
            <h1 style="color: #fff; margin: 0; font-size: 22px;">The Alignment Puzzle</h1>
        </div>

        <div style="padding: 32px 24px;">
            <p>Dear {order_data['name']},</p>
            <p>Thank you for your order! Your payment has been received. Below you will find your invoice.</p>

            <div style="background: #f5f7fa; border-radius: 8px; padding: 24px; margin: 24px 0;">
                <h2 style="color: #1a3a5c; margin-top: 0; font-size: 18px;">Invoice</h2>
                <table style="width: 100%; font-size: 14px; margin-bottom: 12px;">
                    <tr><td style="color: #666;">Invoice number:</td>
                        <td style="text-align: right;">{order_data['order_id']}</td></tr>
                    <tr><td style="color: #666;">Date:</td>
                        <td style="text-align: right;">{order_date}</td></tr>
                </table>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 16px 0;">

                <h3 style="color: #1a3a5c; font-size: 15px; margin-bottom: 8px;">Ship to:</h3>
                <p style="margin: 0; font-size: 14px;">
                    {order_data['name']}<br>
                    {order_data['address']}<br>
                    {order_data['postal_code']} {order_data['city']}<br>
                    {order_data['country']}
                </p>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 16px 0;">

                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="border-bottom: 2px solid #1a3a5c;">
                            <th style="text-align: left; padding: 8px 0;">Description</th>
                            <th style="text-align: center; padding: 8px 0;">Qty</th>
                            <th style="text-align: right; padding: 8px 0;">Unit price</th>
                            <th style="text-align: right; padding: 8px 0;">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 8px 0;">The Alignment Puzzle<br>
                                <span style="font-size: 12px; color: #666;">Business Engineering for Aligned Organizations (2nd ed.)</span></td>
                            <td style="text-align: center; padding: 8px 0;">{quantity}</td>
                            <td style="text-align: right; padding: 8px 0;">&euro; {unit_excl:.2f}</td>
                            <td style="text-align: right; padding: 8px 0;">&euro; {total_excl:.2f}</td>
                        </tr>
                    </tbody>
                </table>

                <table style="width: 100%; font-size: 14px; margin-top: 12px;">
                    <tr><td style="padding: 4px 0;">Subtotal (excl. VAT):</td>
                        <td style="text-align: right; padding: 4px 0;">&euro; {total_excl:.2f}</td></tr>
                    <tr><td style="padding: 4px 0;">VAT (21%):</td>
                        <td style="text-align: right; padding: 4px 0;">&euro; {total_vat:.2f}</td></tr>
                    <tr><td style="padding: 4px 0;">Shipping:</td>
                        <td style="text-align: right; padding: 4px 0;">Included</td></tr>
                    <tr style="font-weight: bold; font-size: 16px; border-top: 2px solid #1a3a5c;">
                        <td style="padding: 12px 0;">Total:</td>
                        <td style="text-align: right; padding: 12px 0;">&euro; {total_incl:.2f}</td></tr>
                </table>
            </div>

            <p>Your book will be shipped to the address above. You will receive a separate email when your order has been dispatched.</p>

            <p style="margin-top: 32px;">Kind regards,<br>
            <strong>The Alignment Puzzle Team</strong><br>
            Hans Veltman, Jacques Adriaansen, Peter Morren &amp; Rob Kwikkers</p>
        </div>

        <div style="background: #f5f7fa; padding: 16px 24px; text-align: center; font-size: 12px; color: #999;">
            <p>&copy; 2026 The Alignment Puzzle | info@alignmentpuzzle.com | www.alignmentpuzzle.com</p>
        </div>
    </div>
    """

    _send_email(order_data['email'], subject, html)
