import logging
import os

import discord

from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from database.connection import init_db
from utils.embeds import error_embed


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "lost_eden"
)


# =========================================================
# ENV
# =========================================================

load_dotenv()


def require_env(
    name: str,
) -> str:
    """
    Возвращает обязательную переменную окружения.

    Если она отсутствует,
    бот завершается сразу с понятной ошибкой.
    """

    value = os.getenv(
        name
    )

    if value is None:
        raise RuntimeError(
            f"Переменная окружения "
            f"{name} не задана"
        )

    value = value.strip()

    if not value:
        raise RuntimeError(
            f"Переменная окружения "
            f"{name} пуста"
        )

    return value


def require_int_env(
    name: str,
) -> int:
    """
    Возвращает обязательную числовую
    переменную окружения.
    """

    raw_value = require_env(
        name
    )

    try:
        value = int(
            raw_value
        )

    except ValueError as error:
        raise RuntimeError(
            f"Переменная окружения "
            f"{name} должна быть числом"
        ) from error

    if value <= 0:
        raise RuntimeError(
            f"Переменная окружения "
            f"{name} должна быть "
            f"положительным числом"
        )

    return value


TOKEN = require_env(
    "DIS_TOKEN"
)

GUILD_ID = require_int_env(
    "GUILD_ID"
)


# =========================================================
# EXTENSIONS
# =========================================================

EXTENSIONS = [
    "cogs.general.general",
    "cogs.fun.fun",
    "cogs.activity",
    "cogs.welcome.banner",
    "cogs.welcome.welcome",
    "cogs.moderation.economy_admin",
    "cogs.rituals.achievements",
    "cogs.rituals.rituals",
    "cogs.events.events",
]


# =========================================================
# BOT
# =========================================================

class BotClient(
    commands.Bot
):
    def __init__(
        self,
    ):
        intents = (
            discord.Intents.default()
        )

        intents.members = True
        intents.presences = True
        intents.voice_states = True

        super().__init__(
            command_prefix="!",
            intents=intents,
        )

    # =====================================================
    # SETUP
    # =====================================================

    async def setup_hook(
        self,
    ) -> None:
        logger.info(
            "Инициализация базы данных"
        )

        await init_db()

        # =============================================
        # COGS
        # =============================================

        for extension in EXTENSIONS:
            try:
                await self.load_extension(
                    extension
                )

                logger.info(
                    "Загружено расширение: %s",
                    extension,
                )

            except Exception:
                logger.exception(
                    "Не удалось загрузить "
                    "расширение: %s",
                    extension,
                )

                # Не запускаем частично
                # работающего бота.
                raise

        # =============================================
        # COMMAND SYNC
        # =============================================

        guild = discord.Object(
            id=GUILD_ID
        )

        self.tree.copy_global_to(
            guild=guild
        )

        try:
            synced = (
                await self.tree.sync(
                    guild=guild
                )
            )

        except Exception:
            logger.exception(
                "Не удалось "
                "синхронизировать команды"
            )

            raise

        logger.info(
            "Синхронизировано команд: %s",
            len(synced),
        )


# =========================================================
# CLIENT
# =========================================================

client = BotClient()


# =========================================================
# READY
# =========================================================

@client.event
async def on_ready(
) -> None:
    if client.user is None:
        logger.warning(
            "on_ready вызван без client.user"
        )

        return

    logger.info(
        "Бот запущен: %s (%s)",
        client.user,
        client.user.id,
    )

    logger.info(
        "Подключено серверов: %s",
        len(client.guilds),
    )


# =========================================================
# GLOBAL SLASH ERROR HANDLER
# =========================================================

@client.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    """
    Общий обработчик ошибок slash-команд.

    Пользователь получает понятное сообщение,
    а полная техническая ошибка остаётся в логах.
    """

    # =====================================================
    # USER DOES NOT HAVE PERMISSIONS
    # =====================================================

    if isinstance(
        error,
        app_commands.MissingPermissions,
    ):
        embed = error_embed(
            title="Недостаточно прав",
            description=(
                "У тебя нет прав "
                "для выполнения этой команды."
            ),
        )

    # =====================================================
    # BOT DOES NOT HAVE PERMISSIONS
    # =====================================================

    elif isinstance(
        error,
        app_commands.BotMissingPermissions,
    ):
        embed = error_embed(
            title="Недостаточно прав",
            description=(
                "У бота недостаточно прав "
                "для выполнения этого действия."
            ),
        )

    # =====================================================
    # SERVER ONLY
    # =====================================================

    elif isinstance(
        error,
        app_commands.NoPrivateMessage,
    ):
        embed = error_embed(
            title="Команда недоступна",
            description=(
                "Эту команду можно использовать "
                "только внутри сервера."
            ),
        )

    # =====================================================
    # COOLDOWN
    # =====================================================

    elif isinstance(
        error,
        app_commands.CommandOnCooldown,
    ):
        retry_after = max(
            1,
            round(
                error.retry_after
            ),
        )

        embed = error_embed(
            title="Слишком рано",
            description=(
                "Эту команду пока нельзя "
                "использовать повторно.\n\n"
                f"Попробуй через "
                f"**{retry_after} сек.**"
            ),
        )

    # =====================================================
    # CHECK FAILED
    # =====================================================

    elif isinstance(
        error,
        app_commands.CheckFailure,
    ):
        embed = error_embed(
            title="Действие недоступно",
            description=(
                "Эта команда сейчас "
                "для тебя недоступна."
            ),
        )

    # =====================================================
    # UNKNOWN ERROR
    # =====================================================

    else:
        embed = error_embed(
            title="Что-то пошло не так",
            description=(
                "Не удалось выполнить команду.\n"
                "Попробуй ещё раз."
            ),
        )

        # CommandInvokeError хранит
        # исходную ошибку в .original.
        original_error = getattr(
            error,
            "original",
            error,
        )

        logger.error(
            (
                "Ошибка slash-команды "
                "%s | user=%s | guild=%s"
            ),
            getattr(
                interaction.command,
                "qualified_name",
                "unknown",
            ),
            interaction.user.id,
            (
                interaction.guild.id
                if interaction.guild
                else None
            ),
            exc_info=(
                type(original_error),
                original_error,
                original_error.__traceback__,
            ),
        )

    # =====================================================
    # RESPONSE
    # =====================================================

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                embed=embed,
                ephemeral=True,
            )

        else:
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

    except discord.HTTPException:
        logger.exception(
            "Не удалось отправить "
            "сообщение об ошибке пользователю"
        )


# =========================================================
# RUN
# =========================================================

client.run(
    TOKEN
)