# database/models.py

from dataclasses import dataclass


@dataclass
class MemberStats:
    guild_id: int
    user_id: int
    messages: int
    voice_seconds: int
    xp: int
    currency: int
    eden_cases: int