import discord

from config.theme import (
    EDEN_GOLD,
    EDEN_GREEN,
    EDEN_ASH,
)


class ServerInfoView(discord.ui.View):
    def __init__(
        self,
        guild: discord.Guild,
        user_id: int
    ):
        super().__init__(timeout=120)

        self.guild = guild
        self.user_id = user_id
        self.message = None

        self._activate_button("serverinfo:home")


    # -----------------------------
    # Общие вспомогательные методы
    # -----------------------------

    def _activate_button(self, custom_id: str):
        """
        Подсвечивает текущую страницу
        и блокирует её кнопку.
        """

        for item in self.children:
            if not isinstance(item, discord.ui.Button):
                continue

            item.disabled = False
            item.style = discord.ButtonStyle.secondary

            if item.custom_id == custom_id:
                item.disabled = True
                item.style = discord.ButtonStyle.success


    def _channel(self, name: str) -> str:
        """
        Возвращает упоминание канала.

        Если канал не найден, показывает его
        предполагаемое название.
        """

        channel = discord.utils.get(
            self.guild.channels,
            name=name
        )

        if channel is None:
            return f"`#{name}`"

        member = self.guild.get_member(self.user_id)

        if member is not None:
            permissions = channel.permissions_for(member)

            if not permissions.view_channel:
                return "🔒 `закрытая тропа`"

        return channel.mention


    # -----------------------------
    # Главная страница
    # -----------------------------

    def main_embed(self) -> discord.Embed:
        guild = self.guild

        if guild.owner is None:
            owner_text = f"<@{guild.owner_id}>"
        else:
            owner_text = guild.owner.mention

        if guild.member_count is None:
            member_count = len(guild.members)
        else:
            member_count = guild.member_count

        created_timestamp = int(
            guild.created_at.timestamp()
        )

        embed = discord.Embed(
            title="LOST EDEN · RIMAY",
            description=(
                "### The gates are open.\n"
                "*The garden is not the same.*\n\n"
                "> Мы не возвращаемся в старый сад.\n"
                "> Мы выращиваем новый.\n\n"
                "Место для тех, кто потерял что-то своё, "
                "но всё ещё способен посадить новое."
            ),
            colour=EDEN_GOLD
        )

        embed.add_field(
            name="🌿 Путники",
            value=f"**{member_count}**",
            inline=True
        )

        embed.add_field(
            name="🕊 Хранитель",
            value=owner_text,
            inline=True
        )

        embed.add_field(
            name="🕯 Сад зажжён",
            value=(
                f"<t:{created_timestamp}:D>\n"
                f"<t:{created_timestamp}:R>"
            ),
            inline=True
        )

        embed.add_field(
            name="🍃 Пространства",
            value=(
                f"**{len(guild.text_channels)}** текстовых троп\n"
                f"**{len(guild.voice_channels)}** голосовых пространств"
            ),
            inline=True
        )

        role_count = max(len(guild.roles) - 1, 0)

        embed.add_field(
            name="🌱 Корни",
            value=f"**{role_count}** ролей сада",
            inline=True
        )

        embed.add_field(
            name="🍎 Завет",
            value="*We don't return. We rebuild.*",
            inline=True
        )

        if guild.icon is not None:
            embed.set_thumbnail(
                url=guild.icon.url
            )

        if guild.banner is not None:
            embed.set_image(
                url=guild.banner.url
            )

        embed.set_footer(
            text=(
                f"LOST EDEN · RIMAY  •  "
                f"Garden ID {guild.id}"
            )
        )

        return embed


    # -----------------------------
    # Правила
    # -----------------------------

    def rules_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="📜 Перед воротами",
            description=(
                "*Рай не возвращают. Его создают заново.*\n\n"
                "Свобода здесь начинается с уважения "
                "к свободе другого."
            ),
            colour=EDEN_ASH
        )

        embed.add_field(
            name="I · Береги пространство",
            value=(
                "Не выращивай здесь травлю, оскорбления, "
                "ненависть и намеренные провокации."
            ),
            inline=False
        )

        embed.add_field(
            name="II · Не ломай чужие ветви",
            value=(
                "Уважай личные границы. Не публикуй "
                "чужие переписки и личную информацию "
                "без разрешения."
            ),
            inline=False
        )

        embed.add_field(
            name="III · У каждой тропы своё назначение",
            value=(
                "Старайся выбирать подходящий канал "
                "для разговора и не превращать пространство "
                "в поток спама."
            ),
            inline=False
        )

        embed.add_field(
            name="IV · Внутренний сад хранит доверие",
            value=(
                "То, чем люди делятся в "
                "`the-hidden-garden` и `the-fallen`, "
                "не должно покидать эти пространства."
            ),
            inline=False
        )

        embed.add_field(
            name="V · Хранители ухаживают, а не властвуют",
            value=(
                "🕊 **The Keeper** существует для защиты "
                "пространства и его участников, "
                "а не для власти над ними."
            ),
            inline=False
        )

        embed.set_footer(
            text=(
                "Теряй, чтобы найти. "
                "Помни, чтобы пересоздать."
            )
        )

        return embed


    # -----------------------------
    # Навигация
    # -----------------------------

    def navigation_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🧭 Тропы сада",
            description=(
                "У каждой части сада свой голос.\n"
                "*Выбирай тропу по тому, что тебе нужно сейчас.*"
            ),
            colour=EDEN_GREEN
        )

        embed.add_field(
            name="🍃 Вход в сад",
            value=(
                f"{self._channel('before-the-gate')} "
                "· правила и манифест\n"
                f"{self._channel('the-gardeners')} "
                "· знакомство\n"
                f"{self._channel('first-roots')} "
                "· помощь и вопросы"
            ),
            inline=False
        )

        embed.add_field(
            name="🌳 Общий сад",
            value=(
                f"{self._channel('orchard')} "
                "· основной разговор\n"
                f"{self._channel('the-well')} "
                "· философия и рефлексия\n"
                f"{self._channel('the-glow')} "
                "· события и активности\n"
                f"{self._channel('the-seeds')} "
                "· творчество и идеи"
            ),
            inline=False
        )

        embed.add_field(
            name="🌿 Внутренний сад",
            value=(
                f"{self._channel('the-hidden-garden')} "
                "· доверительные разговоры\n"
                f"{self._channel('the-fallen')} "
                "· боль, утрата и ошибки"
            ),
            inline=False
        )

        embed.add_field(
            name="✨ Свет и движение",
            value=(
                f"{self._channel('the-sunlit-glade')} "
                "· игры, квизы, киновечера\n"
                f"{self._channel('the-echoing-grove')} "
                "· спокойные голосовые разговоры\n"
                f"{self._channel('the-dancing-fire')} "
                "· активные голосовые встречи"
            ),
            inline=False
        )

        embed.add_field(
            name="🌒 За стеной",
            value=(
                f"{self._channel('beyond-the-wall')} "
                "· IRL, внешние события и соцсети"
            ),
            inline=False
        )

        embed.set_footer(
            text="Не каждая тропа должна вести назад."
        )

        return embed


    # -----------------------------
    # Проверка пользователя
    # -----------------------------

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if interaction.user.id == self.user_id:
            return True

        await interaction.response.send_message(
            "Эту карту сада сейчас изучает другой путник. "
            "Открой свою через `/serverinfo`.",
            ephemeral=True
        )

        return False


    # -----------------------------
    # Кнопки
    # -----------------------------

    @discord.ui.button(
        label="О саде",
        emoji="🌳",
        style=discord.ButtonStyle.success,
        custom_id="serverinfo:home"
    )
    async def home(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        self._activate_button("serverinfo:home")

        await interaction.response.edit_message(
            embed=self.main_embed(),
            view=self
        )


    @discord.ui.button(
        label="Правила",
        emoji="📜",
        style=discord.ButtonStyle.secondary,
        custom_id="serverinfo:rules"
    )
    async def rules(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        self._activate_button("serverinfo:rules")

        await interaction.response.edit_message(
            embed=self.rules_embed(),
            view=self
        )


    @discord.ui.button(
        label="Навигация",
        emoji="🧭",
        style=discord.ButtonStyle.secondary,
        custom_id="serverinfo:navigation"
    )
    async def navigation(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        self._activate_button("serverinfo:navigation")

        await interaction.response.edit_message(
            embed=self.navigation_embed(),
            view=self
        )


    # -----------------------------
    # Истечение времени
    # -----------------------------

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.message is None:
            return

        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass