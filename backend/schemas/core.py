from pydantic import BaseModel


class ChannelsRequest(BaseModel):
    channels: list[str]