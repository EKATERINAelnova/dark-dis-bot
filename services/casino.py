from typing import Literal

from config.economy import (
    CASINO_MIN_BET,
    CASINO_MAX_BET,
    REASON_CASINO_BET,
    REASON_CASINO_PAYOUT,
    REASON_CASINO_REFUND,
)
from database.economy import change_balance


CasinoGame = Literal[
    "roulette",
    "blackjack",
    "slots"
]


def validate_bet(bet: int) -> None:
    """
    Проверяет допустимый размер ставки.

    Выбрасывает ValueError,
    если ставка выходит за границы казино.
    """

    if bet < CASINO_MIN_BET:
        raise ValueError(
            f"Минимальная ставка: {CASINO_MIN_BET}"
        )

    if bet > CASINO_MAX_BET:
        raise ValueError(
            f"Максимальная ставка: {CASINO_MAX_BET}"
        )


async def place_bet(
    guild_id: int,
    user_id: int,
    bet: int,
    game: CasinoGame
) -> int | None:
    """
    Списывает ставку с баланса игрока.

    Возвращает новый баланс.

    Если средств недостаточно,
    change_balance() возвращает None.
    """

    validate_bet(bet)

    new_balance = await change_balance(
        guild_id=guild_id,
        user_id=user_id,
        amount=-bet,
        reason=REASON_CASINO_BET,
        description=f"{game}:bet",
        actor_id=user_id
    )

    return new_balance


async def payout(
    guild_id: int,
    user_id: int,
    amount: int,
    game: CasinoGame,
    result: str
) -> int:
    """
    Выплачивает игроку выигрыш.

    amount — полная сумма выплаты,
    а не только чистая прибыль.

    Например:

    ставка = 50
    коэффициент = x2

    amount = 100
    """

    if amount <= 0:
        raise ValueError(
            "Выплата должна быть больше 0"
        )

    new_balance = await change_balance(
        guild_id=guild_id,
        user_id=user_id,
        amount=amount,
        reason=REASON_CASINO_PAYOUT,
        description=f"{game}:{result}",
        actor_id=user_id
    )

    # При положительном amount это практически
    # не должно происходить, но защищаем тип.
    if new_balance is None:
        raise RuntimeError(
            "Не удалось выполнить выплату казино"
        )

    return new_balance


async def refund_bet(
    guild_id: int,
    user_id: int,
    bet: int,
    game: CasinoGame,
    reason: str = "refund"
) -> int:
    """
    Возвращает игроку ранее списанную ставку.

    Например используется при ничьей в Blackjack.
    """

    if bet <= 0:
        raise ValueError(
            "Возвращаемая ставка должна быть больше 0"
        )

    new_balance = await change_balance(
        guild_id=guild_id,
        user_id=user_id,
        amount=bet,
        reason=REASON_CASINO_REFUND,
        description=f"{game}:{reason}",
        actor_id=user_id
    )

    if new_balance is None:
        raise RuntimeError(
            "Не удалось вернуть ставку"
        )

    return new_balance

async def double_bet(
    guild_id: int,
    user_id: int,
    bet: int
) -> int | None:
    """
    Списывает дополнительную ставку
    при Double Down в Blackjack.

    Например:
    исходная ставка = 50
    double_bet() списывает ещё 50
    """

    validate_bet(bet)

    new_balance = await change_balance(
        guild_id=guild_id,
        user_id=user_id,
        amount=-bet,
        reason=REASON_CASINO_BET,
        description="blackjack:double",
        actor_id=user_id
    )

    return new_balance