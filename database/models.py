# database/models.py

from dataclasses import dataclass


@dataclass
class MemberStats:
    guild_id: int
    user_id: int
    messages: int = 0
    voice_seconds: int = 0
    xp: int = 0
    currency: int = 0
    eden_cases: int = 0