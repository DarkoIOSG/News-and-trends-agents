import email
import imaplib
import os
import re
from datetime import timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from news_agent.models import Article


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = []
    for chunk, encoding in decode_header(value):
        parts.append(chunk.decode(encoding or "utf-8", errors="replace") if isinstance(chunk, bytes) else chunk)
    return "".join(parts)


class IMAPNewsletterAdapter:
    """Read matching newsletter messages from an IMAP mailbox."""

    def __init__(self, config: dict):
        self.config = config

    def fetch(self) -> list[Article]:
        host = self.config.get("host") or os.getenv("NEWSLETTER_IMAP_HOST")
        user = self.config.get("user") or os.getenv("NEWSLETTER_IMAP_USER")
        password = self.config.get("password") or os.getenv("NEWSLETTER_IMAP_PASSWORD")
        if not all((host, user, password)):
            raise ValueError("Set NEWSLETTER_IMAP_HOST, NEWSLETTER_IMAP_USER, and NEWSLETTER_IMAP_PASSWORD")
        mailbox = self.config.get("mailbox", "INBOX")
        client = imaplib.IMAP4_SSL(host)
        try:
            client.login(user, password)
            status, _ = client.select(mailbox, readonly=True)
            if status != "OK":
                raise ValueError(f"Could not open IMAP mailbox {mailbox}")
            criteria = ["UNSEEN"]
            if self.config.get("sender"):
                criteria.extend(["FROM", f'"{self.config["sender"]}"'])
            status, response = client.search(None, *criteria)
            if status != "OK":
                raise ValueError("IMAP search failed")
            ids = response[0].split()[-int(self.config.get("max_items", 10)):]
            result = []
            for msg_id in ids:
                _, data = client.fetch(msg_id, "(RFC822)")
                message = email.message_from_bytes(data[0][1])
                subject = _decode(message.get("Subject")) or "Newsletter"
                if self.config.get("subject_contains", "").lower() not in subject.lower():
                    continue
                body = ""
                parts = message.walk() if message.is_multipart() else [message]
                for part in parts:
                    if part.get_content_type() in ("text/plain", "text/html") and not part.get_filename():
                        raw = part.get_payload(decode=True) or b""
                        body = raw.decode(part.get_content_charset() or "utf-8", errors="replace")
                        if part.get_content_type() == "text/html":
                            body = BeautifulSoup(body, "html.parser").get_text(" ", strip=True)
                        if body:
                            break
                message_id = message.get("Message-ID", msg_id.decode())
                published_at = None
                if message.get("Date"):
                    try:
                        published_at = parsedate_to_datetime(message["Date"])
                        if published_at.tzinfo is None:
                            published_at = published_at.replace(tzinfo=timezone.utc)
                    except (TypeError, ValueError, OverflowError):
                        pass
                result.append(Article(
                    id=f"{self.config['id']}:{message_id}",
                    source_id=self.config["id"],
                    source_name=self.config.get("name", self.config["id"]),
                    title=subject,
                    url=_first_url(body),
                    text=BeautifulSoup(body, "html.parser").get_text(" ", strip=True)[:30_000],
                    published_at=published_at,
                ))
            return result
        finally:
            try:
                client.logout()
            except (imaplib.IMAP4.error, OSError):
                pass


def _first_url(text: str) -> str:
    match = re.search(r"https?://[^\s<>\"']+", text)
    return match.group(0).rstrip(".,)") if match else ""

