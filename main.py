import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")

app = FastAPI(title="Telegram Channel Scraper API")

class ChannelsRequest(BaseModel):
    channels: list[str]

async def fetch_telegram_data(channels: list[str]):
    """Fetch messages from specified Telegram channels"""
    result = {}

    async with TelegramClient('session_name', API_ID, API_HASH) as client:
        await client.start(phone=PHONE)

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

@app.get("/")
async def root():
    return {"message": "Telegram Channel Scraper API", "endpoint": "POST /channels"}

@app.post("/channels")
async def get_channels(request: ChannelsRequest):
    """Fetch messages from specified Telegram channels"""
    if not request.channels:
        raise HTTPException(status_code=400, detail="Channels list cannot be empty")

    try:
        data = await fetch_telegram_data(request.channels)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
