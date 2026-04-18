from telethon import TelegramClient
from .config import config



async def fetch_telegram_data(channels: list[str]):
    """Fetch messages from specified Telegram channels"""
    result = {}

    async with TelegramClient('session_name', config.api_id, config.api_hash) as client:
        await client.start(phone=config.phone)

        for channel in channels:
            print(f"Fetching messages from {channel}...")
            try:
                messages = []

                async for message in client.iter_messages(channel, limit=100):
                    sender_info = {
                        "id": None,
                        "username": None,
                        "first_name": None,
                        "last_name": None,
                        "type": None
                    }

                    if message.sender:
                        sender_info["id"] = message.sender.id
                        sender_info["username"] = getattr(message.sender, 'username', None)
                        sender_info["first_name"] = getattr(message.sender, 'first_name', None)
                        sender_info["last_name"] = getattr(message.sender, 'last_name', None)
                        sender_info["type"] = type(message.sender).__name__
                    elif message.sender_id:
                        sender_info["id"] = message.sender_id
                        sender_info["type"] = "Unknown"

                    message_data = {
                        "message_id": message.id,
                        "date": message.date.isoformat() if message.date else None,
                        "text": message.text or "",
                        "sender": sender_info,
                        "views": message.views,
                        "replies": message.replies.replies if message.replies else 0,
                        "forwards": message.forwards,
                        "has_media": bool(message.media),
                        "media_type": type(message.media).__name__ if message.media else None
                    }
                    messages.append(message_data)

                result[channel] = {
                    "status": "success",
                    "count": len(messages),
                    "messages": messages
                }
                print(f"✓ {len(messages)} messages from {channel}")

            except Exception as e:
                print(f"✗ Error fetching {channel}: {e}")
                result[channel] = {
                    "status": "error",
                    "error": str(e)
                }

    return result