"""OneDrive integration via Make.com webhook.

Sends generated PDFs (Reports / Timesheets) to a Make.com Custom Webhook
which then uploads the file to the user's personal OneDrive.

Payload: multipart/form-data with fields:
  - file: the PDF (binary)
  - filename: target filename
  - os_number: OS reference (used for folder grouping in Make.com)
  - kind: "report" | "timesheet"
"""
import logging
import os
import httpx

logger = logging.getLogger(__name__)


async def send_pdf_to_onedrive(
    pdf_bytes: bytes,
    filename: str,
    os_number: str,
    kind: str,
) -> bool:
    """Fire-and-forget upload of a PDF to OneDrive via Make.com webhook.

    Returns True on success, False otherwise. Never raises (safe to call from
    background tasks)."""
    env_key_map = {
        "report": "MAKE_WEBHOOK_REPORTS_URL",
        "timesheet": "MAKE_WEBHOOK_TIMESHEETS_URL",
        "project": "MAKE_WEBHOOK_PROJECTS_URL",
    }
    env_key = env_key_map.get(kind, "MAKE_WEBHOOK_REPORTS_URL")
    webhook_url = os.environ.get(env_key, "").strip()
    if not webhook_url:
        logger.info(f"OneDrive webhook ({kind}) not configured; skipping upload")
        return False

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {
                "file": (filename, pdf_bytes, "application/pdf"),
            }
            data = {
                "filename": filename,
                "os_number": os_number or "",
                "kind": kind,
            }
            resp = await client.post(webhook_url, files=files, data=data)
            if 200 <= resp.status_code < 300:
                logger.info(f"OneDrive upload OK [{kind}] {filename} -> {resp.status_code}")
                return True
            logger.warning(
                f"OneDrive upload failed [{kind}] {filename}: "
                f"status={resp.status_code} body={resp.text[:300]}"
            )
            return False
    except Exception as e:
        logger.exception(f"OneDrive upload exception [{kind}] {filename}: {e}")
        return False
