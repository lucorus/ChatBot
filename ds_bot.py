from discord.ext import commands
from datetime import datetime
import private_messages
from config import *
import deposit
import discord
import asyncio
import casino
import items
import pytz
import base
import info


intents = discord.Intents.all()
bot = commands.Bot('!', intents=intents)
timezone = pytz.timezone('Europe/Moscow')


@bot.event
async def on_ready():
    while True:
        await asyncio.sleep(60)


@bot.event
async def on_guild_join(guild):
    await base.add_guild_to_database(guild)


@bot.event
async def on_message(message):
    try:
        if message.author.bot:
            return

        if message.channel.type == discord.ChannelType.private:
            await private_messages.private_message(message)

        # Получение данных пользователя из базы данных
        user_data = await base.get_user(user_id=message.author.id, guild_id=message.guild.id)
        if user_data == []:
            await base.add_user_to_database(author_id=message.author.id, guild_id=message.guild.id,
                                            author_name=str(message.author),
                                            author_avatar=str(message.author.avatar))
        else:
            # Если пользователь найден, проверяем время последнего сообщения
            time_difference = datetime.strptime(base.time_now(), "%Y/%m/%d/%H/%M") - datetime.strptime(
                str(user_data[3]), "%Y/%m/%d/%H/%M")
            # Если прошло больше минуты, добавляем баллы и обновляем время последнего сообщения

            if time_difference.total_seconds() >= 60:
                await asyncio.gather(
                    base.change_count_points(user_id=message.author.id, guild_id=message.guild.id, points=user_data[4]),
                    base.change_last_message_time(user_id=message.author.id, guild_id=message.guild.id),
                    base.change_count_exp(user_id=message.author.id, guild_id=message.guild.id)
                )
        await bot.process_commands(message)
    except AttributeError:
        # если сервер на котором есть бот ещё не добавлен в бд, то добавляем его
        await base.add_guild_to_database(message.guild)
    except Exception as ex:
        print(ex)


@bot.command(name='points')
async def get_user_points(ctx, user: discord.Member = None):
    try:
        if not user:
            user = ctx.author
        await ctx.send(f"Количество баллов у {user.mention}: { await base.get_field(user.id, ctx.guild.id, 'points') }")
    except Exception as ex:
        print(ex)


@bot.command(name='payment')
async def get_user_payment(ctx, user: discord.Member = None):
    try:
        if not user:
            user = ctx.author
        await ctx.send(f"Количество баллов за сообщение у {user.mention}: { await base.get_field(user.id, ctx.guild.id, 'payment') }")
    except Exception as ex:
        print(ex)


@bot.command(name='exp')
async def get_user_exp(ctx, user: discord.Member = None):
    try:
        if not user:
            user = ctx.author
        await ctx.send(f"Количество опыта у {user.mention}: { await base.get_field(user.id, ctx.guild.id, 'exp') }")
    except Exception as ex:
        print(ex)


@bot.command(name='add_points')
async def add_points(ctx, member: discord.Member, points: int):
    try:
        if ctx.author.id == 854253015862607872:
            await base.change_count_points(user_id=member.id, guild_id=ctx.guild.id, points=int(points))
    except Exception as ex:
        print(ex)


@bot.command(name='update_user_info')
async def update_user_info(ctx):
    await info.update_user_info(ctx)


@bot.command(name='update_server_info')
async def update_guild_info(ctx):
    await info.update_guild_info(ctx)


@bot.command(name='assortment')
async def see_assortment(ctx):
    try:
        assortment = await items.get_assortment(ctx.guild.id)
        if assortment == []:
            await ctx.send('Товаров нет')
        else:
            assort = 'Список товаров: \n'
            for item in assortment:
                assort += f' - {item[1]} имеет цену {item[3]} и добавляет {item[2]} баллов за сообщение \n'
            await ctx.send(assort)
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')


@bot.command(name='add_item')
async def add_item(ctx, title: str, payment: int, price: int):
    try:
        if ctx.author.guild_permissions.administrator:
            if price < 100 or payment < 1:
                await ctx.send('Некорректные данные')
                return
            await items.add_item_to_assortment(title, payment, price, ctx.guild.id)
            await ctx.send('Действие выполнено успешно')
        else:
            await ctx.send('У вас недостаточно прав')
    except Exception as ex:
        print(ex)
        ctx.send('Произошла неизвестная ошибка')


@bot.command(name='delete_item')
async def delete_item(ctx, title: str):
    try:
        if ctx.author.guild_permissions.administrator:
            await items.delete_item(title, ctx.guild.id)
            await ctx.send('Действие выполнено успешно')
        else:
            await ctx.send('У вас недостаточно прав')
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')


@bot.command(name='buy')
async def buy_item(ctx, member: discord.Member, title: str):
    try:
        await items.buying_item(
            ctx=ctx, member=member,
            buyer=await base.get_user(user_id=ctx.author.id, guild_id=ctx.guild.id),
            item=await items.get_item(title=title, guild_id=ctx.guild.id)
        )
    except Exception as ex:
        print(ex)


@bot.command(name='casino')
async def play_casino(ctx, bet: str):
    try:
        await casino.casino(ctx, bet)
    except Exception as ex:
        print(ex)


@bot.command(name='create_deposit')
async def create_deposit(ctx, points: int):
    try:
        await deposit.create_deposit(ctx=ctx, points=points,
                                     user=await base.get_user(user_id=ctx.author.id, guild_id=ctx.guild.id)
                                     )
    except Exception as ex:
        print(ex)


@bot.command(name='deposit')
async def deposit_info(ctx, user: discord.Member=None):
    try:
        if user == None:
            user = ctx.author
        deposit_data = await deposit.get_deposit_info(user_id=user.id, guild_id=ctx.guild.id)

        await ctx.send(f" ** Информация о счёте **{ user.mention }: "
                        f'\n **Дата создания:** { base.time(deposit_data[3]) }'
                        f'\n **Изначальный размер депозита:** { deposit_data[2] }'
                        f'\n **Доступно для вывода:** { deposit_data[5] }')
    except IndexError:
        await ctx.send('Депозита не существует')
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')


@bot.command(name='delete_deposit')
async def delete_deposit(ctx):
    try:
        await deposit.delete_deposit(ctx, user_id=ctx.author.id, guild_id=ctx.guild.id)
    except Exception as ex:
        print(ex)


bot.run(token)
