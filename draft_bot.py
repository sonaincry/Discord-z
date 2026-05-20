import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


# ======================================
# MATCH DATA
# ======================================

players = []

team1 = []
team2 = []

captain1 = None
captain2 = None

current_picker = None

match_started = False


# ======================================
# JOIN VIEW
# ======================================

class JoinView(discord.ui.View):

    @discord.ui.button(
        label="CHƠI",
        style=discord.ButtonStyle.green
    )
    async def join_button(
            self,
            interaction: discord.Interaction,
            button: discord.ui.Button
    ):

        global players
        global match_started

        user = interaction.user

        if match_started:
            await interaction.response.send_message(
                "Match đã bắt đầu.",
                ephemeral=True
            )
            return

        if user in players:
            await interaction.response.send_message(
                "Bạn đã join rồi.",
                ephemeral=True
            )
            return

        if len(players) >= 10:
            await interaction.response.send_message(
                "Match đã full.",
                ephemeral=True
            )
            return

        players.append(user)

        player_text = "\n".join(
            [f"• {p.display_name}" for p in players]
        )

        msg = (
            f"🎮 MATCH LOBBY ({len(players)}/10)\n\n"
            f"{player_text}"
        )

        if len(players) == 10:
            msg += "\n\n✅ Đã đủ 10 người.\nGõ !doitruong để chọn đội trưởng."

        await interaction.response.edit_message(
            content=msg,
            view=self
        )


# ======================================
# DRAFT VIEW
# ======================================

class DraftView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        remaining = [
            p for p in players
            if p not in team1 and p not in team2
        ]

        for player in remaining:

            button = discord.ui.Button(
                label=player.display_name,
                style=discord.ButtonStyle.blurple
            )

            async def callback(interaction, p=player):

                global current_picker

                if interaction.user != current_picker:
                    await interaction.response.send_message(
                        f"Chưa tới lượt bạn pick.",
                        ephemeral=True
                    )
                    return

                if p in team1 or p in team2:
                    await interaction.response.send_message(
                        "Player đã được pick.",
                        ephemeral=True
                    )
                    return

                # ADD PLAYER
                if current_picker == captain1:
                    team1.append(p)
                    current_picker = captain2
                else:
                    team2.append(p)
                    current_picker = captain1

                # REMAINING
                remaining_players = [
                    x for x in players
                    if x not in team1 and x not in team2
                ]

                # AUTO ADD LAST PLAYER
                if len(remaining_players) == 1:

                    last_player = remaining_players[0]

                    if len(team1) < 5:
                        team1.append(last_player)
                    else:
                        team2.append(last_player)

                    remaining_players = []

                # TEAM TEXT
                t1 = "\n".join(
                    [m.display_name for m in team1]
                )

                t2 = "\n".join(
                    [m.display_name for m in team2]
                )

                msg = (
                    f"🔵 TEAM 1\n{t1}\n\n"
                    f"🔴 TEAM 2\n{t2}\n\n"
                )

                # FINISHED
                if len(remaining_players) == 0:

                    msg += (
                        "🎉 CHIA TEAM HOÀN TẤT\n\n"
                        "Captain gõ !team1 để move voice."
                    )

                    await interaction.response.edit_message(
                        content=msg,
                        view=None
                    )

                    return

                # SHOW NEXT TURN
                msg += (
                    f"👉 Lượt tiếp theo: {current_picker.display_name}\n\n"
                    f"Available Players:\n"
                )

                for rp in remaining_players:
                    msg += f"• {rp.display_name}\n"

                await interaction.response.edit_message(
                    content=msg,
                    view=DraftView()
                )

            button.callback = callback

            self.add_item(button)


# ======================================
# START MATCH
# ======================================

@bot.command()
async def chiateam(ctx):

    global players
    global team1
    global team2
    global captain1
    global captain2
    global current_picker
    global match_started

    # RESET
    players = []

    team1 = []
    team2 = []

    captain1 = None
    captain2 = None

    current_picker = None

    match_started = False

    await ctx.send(
        "🎮 SOLO ?",
        view=JoinView()
    )


# ======================================
# CAPTAIN PICK
# ======================================

@bot.command()
async def doitruong(ctx):

    global captain1
    global captain2
    global current_picker
    global match_started

    if ctx.author not in players:
        await ctx.send(
            "Bạn không nằm trong match."
        )
        return

    if captain1 == ctx.author or captain2 == ctx.author:
        await ctx.send(
            "Bạn đã là đội trưởng."
        )
        return

    # TEAM 1 CAPTAIN
    if captain1 is None:

        captain1 = ctx.author
        team1.append(ctx.author)

        await ctx.send(
            f"🔵 Team 1 Captain: {captain1.display_name}"
        )

        return

    # TEAM 2 CAPTAIN
    if captain2 is None:

        captain2 = ctx.author
        team2.append(ctx.author)

        current_picker = captain1

        match_started = True

        remaining = [
            p.display_name
            for p in players
            if p not in team1 and p not in team2
        ]

        remain_text = "\n".join(
            [f"• {x}" for x in remaining]
        )

        await ctx.send(
            f"🔴 Team 2 Captain: {captain2.display_name}\n\n"
            f"🎮 Draft bắt đầu!\n"
            f"👉 Lượt đầu tiên: {current_picker.display_name}\n\n"
            f"Available Players:\n"
            f"{remain_text}",
            view=DraftView()
        )

        return

    await ctx.send("Đã đủ đội trưởng.")


# ======================================
# SHOW TEAMS
# ======================================

@bot.command()
async def teams(ctx):

    if len(team1) == 0 and len(team2) == 0:
        await ctx.send("Chưa có team.")
        return

    t1 = "\n".join(
        [m.display_name for m in team1]
    )

    t2 = "\n".join(
        [m.display_name for m in team2]
    )

    await ctx.send(
        f"🔵 TEAM 1\n{t1}\n\n"
        f"🔴 TEAM 2\n{t2}"
    )


# ======================================
# MOVE TEAMS TO VOICE
# ======================================

@bot.command()
async def team1(ctx):

    if ctx.author != captain1 and ctx.author != captain2:
        await ctx.send(
            "Chỉ đội trưởng mới được start match."
        )
        return

    voice_team1 = discord.utils.get(
        ctx.guild.voice_channels,
        name="Team 1"
    )

    voice_team2 = discord.utils.get(
        ctx.guild.voice_channels,
        name="Team 2"
    )

    if voice_team1 is None or voice_team2 is None:
        await ctx.send(
            "Không tìm thấy voice channels."
        )
        return

    # MOVE TEAM 1
    for member in team1:

        if member.voice is not None:
            await member.move_to(voice_team1)

    # MOVE TEAM 2
    for member in team2:

        if member.voice is not None:
            await member.move_to(voice_team2)

    await ctx.send(
        "🎮 Đã move tất cả players."
    )


# ======================================
# TEAM 1 WIN
# ======================================

@bot.command()
async def team1win(ctx):

    if ctx.author != captain1 and ctx.author != captain2:
        await ctx.send(
            "Chỉ đội trưởng mới được report."
        )
        return

    winners = "\n".join(
        [f"{p.display_name}: +1" for p in team1]
    )

    losers = "\n".join(
        [f"{p.display_name}: -1" for p in team2]
    )

    await ctx.send(
        f"🏆 TEAM 1 WIN\n\n"
        f"{winners}\n\n"
        f"💀 LOSERS\n"
        f"{losers}"
    )


# ======================================
# TEAM 2 WIN
# ======================================

@bot.command()
async def team2win(ctx):

    if ctx.author != captain1 and ctx.author != captain2:
        await ctx.send(
            "Chỉ đội trưởng mới được report."
        )
        return

    winners = "\n".join(
        [f"{p.display_name}: +1" for p in team2]
    )

    losers = "\n".join(
        [f"{p.display_name}: -1" for p in team1]
    )

    await ctx.send(
        f"🏆 TEAM 2 WIN\n\n"
        f"{winners}\n\n"
        f"💀 LOSERS\n"
        f"{losers}"
    )


# ======================================
# END MATCH
# ======================================

@bot.command()
async def end(ctx):

    global players
    global team1
    global team2
    global captain1
    global captain2
    global current_picker
    global match_started

    if ctx.author != captain1 and ctx.author != captain2:
        await ctx.send(
            "Chỉ đội trưởng mới được end match."
        )
        return

    players = []

    team1 = []
    team2 = []

    captain1 = None
    captain2 = None

    current_picker = None

    match_started = False

    await ctx.send(
        "🛑 Match ended and reset."
    )


bot.run(TOKEN)