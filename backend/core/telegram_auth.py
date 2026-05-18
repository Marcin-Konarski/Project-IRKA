import hashlib
import shutil
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import SQLiteSession
from telethon.errors import SessionPasswordNeededError

from .config import config

_SESSION_DIR = Path(__file__).resolve().parent.parent / "telegram_auth_sessions"
_BASE_DIR = Path(__file__).resolve().parent.parent
_BACKFILL_SESSION_FILE = _BASE_DIR / "session_backfill.session"
_MONITOR_SESSION_FILE = _BASE_DIR / "session_monitor.session"


def _session_path(phone: str) -> Path:
    _SESSION_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = hashlib.sha256(phone.strip().encode("utf-8")).hexdigest()
    return _SESSION_DIR / f"{safe_name}.session"


async def request_telegram_code(phone: str) -> str:
    """
    Request Telegram verification code for a phone number.
    Returns the phone number hash for later verification.
    """
    session_path = _session_path(phone)

    async def _send_code() -> str:
        client = TelegramClient(
            SQLiteSession(str(session_path)),
            config.api_id,
            config.api_hash,
            connection_retries=3,
        )

        await client.connect()

        try:
            result = await client.send_code_request(phone)
            return result.phone_code_hash
        finally:
            await client.disconnect()

    try:
        return await _send_code()
    except Exception as e:
        # Telethon occasionally asks to restart auth flow; reset local auth session once and retry.
        if "AuthRestartError" in str(e):
            if session_path.exists():
                session_path.unlink()
            try:
                return await _send_code()
            except Exception as retry_e:
                raise ValueError(f"Failed to request code: {str(retry_e)}")
        raise ValueError(f"Failed to request code: {str(e)}")


async def verify_telegram_code(phone: str, code: str, phone_code_hash: str) -> bool:
    """
    Verify Telegram code and sign in.
    """
    session_path = _session_path(phone)
    if not session_path.exists():
        raise ValueError("No active authentication session for this phone. Request code first.")

    client = TelegramClient(
        SQLiteSession(str(session_path)),
        config.api_id,
        config.api_hash,
        connection_retries=3,
    )
    await client.connect()
    verified = False
    
    try:
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        verified = True
        return True
    except SessionPasswordNeededError:
        raise ValueError("2FA is enabled. Not supported yet.")
    except Exception as e:
        raise ValueError(f"Invalid code: {str(e)}")
    finally:
        await client.disconnect()
        if verified:
            # Copy only after disconnect so SQLite session is fully flushed.
            shutil.copy2(session_path, _BACKFILL_SESSION_FILE)
            shutil.copy2(session_path, _MONITOR_SESSION_FILE)


async def disconnect_telegram(phone: str) -> None:
    """Disconnect a Telegram session."""
    session_path = _session_path(phone)
    if session_path.exists():
        session_path.unlink()
