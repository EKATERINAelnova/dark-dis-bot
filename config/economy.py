CURRENCY_NAME = "Средства"
CURRENCY_SYMBOL = "🍎"


# =========================================================
# ACTIVITY REWARDS
# =========================================================

# Старые пресеты оставлены для уже созданных EVENT.
EVENT_REWARD_PRESETS = {
    "small": {
        "currency": 20,
        "xp": 15,
        "case": 0,
    },
    "standard": {
        "currency": 40,
        "xp": 30,
        "case": 0,
    },
    "major": {
        "currency": 75,
        "xp": 50,
        "case": 1,
    },
}

EVENT_REWARD_PRESET_NAMES = {
    "small": "SMALL EVENT",
    "standard": "EVENT",
    "major": "MAJOR EVENT",
}

EVENT_MAX_CURRENCY_REWARD = 500
EVENT_MAX_XP_REWARD = 500
EVENT_MAX_CASE_REWARD = 5

DUEL_WIN_REWARD = {
    "currency": 8,
    "xp": 5,
    "case": 0,
}

DUEL_REWARD_DAILY_LIMIT = 3
DUEL_REWARD_WINDOW_SECONDS = 24 * 60 * 60
DUEL_PAIR_REWARD_COOLDOWN_SECONDS = 6 * 60 * 60
DUEL_MIN_DURATION_SECONDS = 2 * 60

# CLOSE: участие получают все, победители получают бонус сверху.
CLOSE_PARTICIPATION_XP = 5
CLOSE_WIN_BONUS_XP = 10
CLOSE_WIN_BONUS_CURRENCY = 10
CLOSE_REWARD_DAILY_LIMIT = 5
CLOSE_REWARD_WINDOW_SECONDS = 24 * 60 * 60

MESSAGE_FUNDS = 1
MESSAGE_FUNDS_COOLDOWN = 180
MESSAGE_FUNDS_DAILY_LIMIT = 20

VOICE_FUNDS = 1
VOICE_FUNDS_INTERVAL_MINUTES = 10
VOICE_FUNDS_DAILY_LIMIT = 12


# =========================================================
# CASINO
# =========================================================

CASINO_MIN_BET = 10
CASINO_MAX_BET = 100


# =========================================================
# TRANSACTION REASONS
# =========================================================

REASON_CASINO_BET = "casino_bet"
REASON_LEVEL = "level_reward"
REASON_EVENT = "event_reward"
REASON_SHOP = "shop_purchase"
REASON_ADMIN = "admin_adjustment"
REASON_CASINO_PAYOUT = "casino_payout"
REASON_CASINO_REFUND = "casino_refund"
REASON_CASE = "case_reward"
REASON_ACHIEVEMENT = "achievement_reward"
REASON_RITUAL = "ritual_reward"
