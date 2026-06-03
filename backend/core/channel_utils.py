from urllib.parse import urlparse

from sqlalchemy import or_
from sqlmodel import select

from ..models import Channel as DBChannel


def normalize_telegram_channel_reference(channel: str) -> str:
    value = channel.strip()

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        if parsed.netloc.endswith("t.me"):
            value = parsed.path.lstrip("/")

    if "t.me/" in value:
        value = value.split("t.me/", 1)[1]

    if value.startswith("@"):
        value = value[1:]

    value = value.strip().strip("/")
    if not value:
        raise ValueError("Channel reference cannot be empty")

    return value


def _matches_channel_title(candidate: str, reference: str) -> bool:
    return candidate.strip().casefold() == reference.strip().casefold()


def resolve_channel_from_db(session, channel: str) -> DBChannel | None:
    reference = normalize_telegram_channel_reference(channel)

    return session.exec(
        select(DBChannel).where(
            or_(
                DBChannel.channel_name == reference,
                DBChannel.title == reference,
            )
        )
    ).first()


async def resolve_telegram_channel(client, channel: str):
    reference = normalize_telegram_channel_reference(channel)

    try:
        return await client.get_entity(reference)
    except Exception:
        pass

    matches = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        title = getattr(entity, "title", None) or getattr(dialog, "name", None)
        if title and _matches_channel_title(title, reference):
            matches.append(entity)

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        raise ValueError(
            f"Multiple Telegram dialogs match '{channel}'. Use a public username or t.me link instead."
        )

    raise ValueError(
        f"Could not resolve '{channel}'. Use a public username, a t.me link, or the exact channel title visible in your dialogs."
    )


def _entity_id_for_tme_c_link(entity_id: int) -> str:
    raw = str(entity_id)
    if raw.startswith("-100"):
        return raw[4:]
    return raw.lstrip("-") if entity_id < 0 else raw


def build_telegram_message_url(message_id: int, entity) -> str | None:
    """Public message permalink on t.me (works for text and media messages)."""
    username = getattr(entity, "username", None)
    if username:
        return f"https://t.me/{username}/{message_id}"

    entity_id = getattr(entity, "id", None)
    if entity_id is not None:
        link_id = _entity_id_for_tme_c_link(entity_id)
        return f"https://t.me/c/{link_id}/{message_id}"

    return None


def build_telegram_message_url_from_channel(message_id: int, channel: DBChannel) -> str | None:
    """Build a t.me link from stored channel metadata (for backfill of old rows)."""
    name = (channel.channel_name or "").strip()
    if name and not name.lstrip("-").isdigit():
        return f"https://t.me/{name.lstrip('@')}/{message_id}"

    return f"https://t.me/c/{_entity_id_for_tme_c_link(channel.id)}/{message_id}"