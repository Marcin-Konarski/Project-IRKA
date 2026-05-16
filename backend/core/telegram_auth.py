import asyncio
from telethon import TelegramClient
from telethon.sessions import MemorySession
from telethon.errors import SessionPasswordNeededError

from .config import config

# Store ongoing authentication sessions
_auth_sessions: dict[str, TelegramClient] = {}


async def request_telegram_code(phone: str) -> str:
    """
    Request Telegram verification code for a phone number.
    Returns the phone number hash for later verification.
    """
    client = TelegramClient(
        MemorySession(),
        config.api_id,
        config.api_hash,
        connection_retries=3,
    )
    
    await client.connect()
    
    try:
        result = await client.send_code_request(phone)
        # Store the client for later verification
        _auth_sessions[phone] = client
        return result.phone_code_hash
    except Exception as e:
        await client.disconnect()
        raise ValueError(f"Failed to request code: {str(e)}")


async def verify_telegram_code(phone: str, code: str, phone_code_hash: str) -> bool:
    """
    Verify Telegram code and sign in.
    """
    if phone not in _auth_sessions:
        raise ValueError("No active authentication session for this phone. Request code first.")
    
    client = _auth_sessions[phone]
    
    try:
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        # Keep client connected after authentication
        return True
    except SessionPasswordNeededError:
        raise ValueError("2FA is enabled. Not supported yet.")
    except Exception as e:
        raise ValueError(f"Invalid code: {str(e)}")
    finally:
        # Clean up the session
        _auth_sessions.pop(phone, None)


async def disconnect_telegram(phone: str) -> None:
    """Disconnect a Telegram session."""
    if phone in _auth_sessions:
        client = _auth_sessions[phone]
        await client.disconnect()
        _auth_sessions.pop(phone, None)
