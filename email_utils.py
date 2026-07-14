"""Temporary-password generation and email notification for user accounts."""

from __future__ import annotations

import secrets
import smtplib
import string
from email.message import EmailMessage

from config import (
    get_smtp_from_address,
    get_smtp_host,
    get_smtp_password,
    get_smtp_port,
    get_smtp_username,
)

_AMBIGUOUS = set("0O1lI")
_UPPER = [c for c in string.ascii_uppercase if c not in _AMBIGUOUS]
_LOWER = [c for c in string.ascii_lowercase if c not in _AMBIGUOUS]
_DIGITS = [c for c in string.digits if c not in _AMBIGUOUS]
_SYMBOLS = list("!@#$%^&*")
_ALL_CHARS = _UPPER + _LOWER + _DIGITS + _SYMBOLS


def generate_temp_password(length: int = 12) -> str:
    """Generates a random temporary password guaranteed to contain at least
    one uppercase letter, one lowercase letter, one digit, and one symbol,
    excluding visually ambiguous characters (0/O/1/l/I)."""
    if length < 4:
        raise ValueError("length must be at least 4 to include all character classes")

    required = [
        secrets.choice(_UPPER),
        secrets.choice(_LOWER),
        secrets.choice(_DIGITS),
        secrets.choice(_SYMBOLS),
    ]
    remaining = [secrets.choice(_ALL_CHARS) for _ in range(length - len(required))]
    password_chars = required + remaining
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


_BM_SUBJECT = "Notifikasi Penetapan Semula Kata Laluan"
_BM_BODY = """Assalamualaikum dan Salam Sejahtera,

Tuan/Puan,

Dimaklumkan bahawa pihak pentadbir telah menetapkan semula kata laluan akaun tuan/puan susulan permohonan berkaitan kata laluan baharu.

Kata laluan sementara/default adalah seperti berikut:

Kata laluan sementara: {temp_password}

Tuan/puan dimohon untuk log masuk menggunakan kata laluan tersebut dan menukarnya kepada kata laluan baharu dengan segera bagi menjaga keselamatan akaun.

Sekiranya tuan/puan masih menghadapi masalah untuk log masuk, sila hubungi pihak pentadbir sistem untuk bantuan selanjutnya.

Sekian, terima kasih.

Yang menjalankan amanah,
Pentadbir Sistem
Sistem Simulasi Dasar Tenaga Kerja Pendidikan
"""

_EN_SUBJECT = "Password Reset Notification"
_EN_BODY = """Dear User,

Please be informed that the administrator has reset your account password following your request regarding a forgotten password.

Your temporary/default password is as follows:

Temporary Password: {temp_password}

Please log in using the temporary password and change it immediately to ensure the security of your account.

Should you continue to experience any issues accessing your account, please contact the system administrator for further assistance.

Thank you.

Best regards,
System Administrator
Education Workforce Policy Simulation System
"""


def send_temp_password_email(to_email: str, username: str, temp_password: str, lang: str = "bm") -> bool:
    """Sends the temporary-password notification email. Returns True on success,
    False on any failure (never raises — a mail-server outage must not break
    user creation or password reset)."""
    subject = _BM_SUBJECT if lang == "bm" else _EN_SUBJECT
    body = (_BM_BODY if lang == "bm" else _EN_BODY).format(temp_password=temp_password)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = get_smtp_from_address()
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(get_smtp_host(), get_smtp_port(), timeout=10) as server:
            server.starttls()
            server.login(get_smtp_username(), get_smtp_password())
            server.send_message(message)
        return True
    except Exception:
        return False
