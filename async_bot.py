from discord.ext import commands
from datetime import datetime
from config import *
import requests
import asyncpg
import discord
import asyncio
import random
import uuid

intents = discord.Intents.all()

bot = commands.Bot('!', intents=intents)


async def create_connect():
    try:
        conn = await asyncpg.connect(
            user=user, password=password,
            database=db_name, host=host
        )
        return conn
    except:
        print('Проблема с подключением к бд')


@bot.event
async def on_ready():
    while True:
        await asyncio.sleep(60)


@bot.command(name='update_info')
async def update_user_info(ctx):
    try:
        conn = await create_connect()
        user_data = await conn.fetch(
            '''
            SELECT * FROM users WHERE user_id=$1 AND server_id=$2 LIMIT 1;
            ''', str(ctx.author.id), str(ctx.guild.id)
        )
        user_data = user_data[0]

        if user_data[8] != str(ctx.author):
            await conn.execute('UPDATE users SET user_name=$1 WHERE user_id=$2',
                       str(ctx.author), str(ctx.author.id))

        if user_data[9] != str(ctx.author.avatar):
            conn.execute('UPDATE users SET user_icon=$1 WHERE user_id=$2',
                       str(ctx.author.avatar), str(ctx.author.id))
        await ctx.send('Данные обновлены!')
    except:
        await ctx.send('Произошла неизвестная ошибка')


@bot.command(name='update_server_info')
async def update_server_fields(ctx):
    try:
        if ctx.author.guild_permissions.administrator:
            conn = await create_connect()
            server_data = await conn.fetch('''
            SELECT * FROM users WHERE server_id=$1 LIMIT 1;
            ''', str(ctx.guild.id))
            server_data = server_data[0]

            if server_data[6] != str(ctx.guild.name):
                print('имя сервера изменено')
                await conn.execute('UPDATE users SET server_name=$1 WHERE server_id=$2',
                       str(ctx.guild.name), str(ctx.guild.id))
            if server_data[7] != str(ctx.guild.icon):
                print('аватар сервера изменён')
                await conn.execute('UPDATE users SET server_icon=$1 WHERE server_id=$2',
                       str(ctx.guild.icon), str(ctx.guild.id))
            await ctx.send('Данные сервера успешно обновлены!')
        else:
            await ctx.send('У вас нет прав для этого действия')
    except:
        await ctx.send('Произошла неизвестная ошибка')


@bot.event
async def on_message(message):
    try:
        if message.author.bot:
            return

        '''
        Если пользователь отправит боту токен из своего личного аккаунта, то бот отправит запрос на апи сервера
        и тогда аккаунт на сервере станет привязан к записи дискорд
        '''
        if message.channel.type == discord.ChannelType.private:
            requests.post(f'http://127.0.0.1:8000/authorize_user', headers={'token': str(message.content), 'user': str(message.author.id), 'access': str(access_token)})
            await message.channel.send('Ваш запрос отправлен на сервер')

        # Получение данных пользователя из базы данных
        conn = await create_connect()
        user_data = await conn.fetch("SELECT * FROM users WHERE user_id=$1 AND server_id=$2", str(message.author.id), message.guild.id)
        user_data = user_data[0]

        if user_data is None:
            # Если пользователь не найден, добавляем его в базу данных
            await conn.execute("INSERT INTO users VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
                           str(uuid.uuid4()), str(message.author.id), 0, int(datetime.utcnow().timestamp()), 1,
                            message.guild.id, str(message.guild.name), str(message.guild.icon), str(message.author),
                            str(message.author.avatar))
        else:
            # Если пользователь найден, проверяем время последнего сообщения
            last_message_time = user_data[3]
            current_time = int(datetime.utcnow().timestamp())
            time_difference = current_time - last_message_time

            # Если прошло больше минуты, добавляем баллы и обновляем время последнего сообщения
            if time_difference > 60:
                await conn.execute("UPDATE users SET points=$1, last_message_time=$2 WHERE user_id=$3 AND server_id=$4",
                             (user_data[2] + user_data[4]), current_time, str(message.author.id), message.guild.id)
        await bot.process_commands(message)
    except Exception as ex:
        print(ex)
        pass


@bot.command(name='points')
async def get_user_points(ctx, user: discord.Member = None):
    try:
        conn = await create_connect()
        if not user:
            user = ctx.author
        result = await conn.fetch("SELECT points FROM users WHERE user_id=$1 AND server_id=$2", str(user.id), ctx.guild.id)
        result = result[0]
        if result:
            await ctx.send(f"Количество баллов у {user.mention}: {result[0]}")
        else:
            await ctx.send(f"Количество баллов у {user.mention}: 0")
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')


#Получаем количество получаемых баллов за сообщение пользователя
@bot.command(name='payment')
async def get_user_payment(ctx, user: discord.Member = None):
    try:
        conn = await create_connect()
        if not user:
            user = ctx.author
        result = await conn.fetch("SELECT payment FROM users WHERE user_id=$1 AND server_id=$2", str(user.id), ctx.guild.id)
        result = result[0]
        if result:
            await ctx.send(f"Количество баллов за сообщение у {user.mention}: {result[0]}")
        else:
            await ctx.send(f"Количество баллов за сообщение у {user.mention}: 1")
    except:
        await ctx.send('Произошла неизвестная ошибка')


# пользователь может купить предмет, увеличивающий кол-во баллов за сообщение (себе или другому человеку)
@bot.command(name='buy')
async def buy(ctx, user: discord.Member, title: str):
    try:
        conn = await create_connect()
        if not user:
            user = ctx.author

        # берём данные пользователя, которому будут покупать товар, чтобы проверить его наличие
        user_data = await conn.fetch("SELECT * FROM users WHERE user_id=$1 AND server_id=$2", str(user.id), ctx.guild.id)
        user_data = user_data[0]
        print('user_data - ', user_data)
        if user_data == None:
            raise Exception('Данного пользователя нет в базе данных')

        # берём данные покупающего пользователя
        buyer = await conn.fetch("SELECT * FROM users WHERE user_id=$1 AND server_id=$2", str(ctx.author.id), ctx.guild.id)
        buyer = buyer[0]
        # берём данные товара
        item = await conn.fetch('SELECT * FROM assortment WHERE title=$1 AND server_id=$2', title, ctx.guild.id)
        item = item[0]

        # если такой товар существует, то забираем его стоимость и увеличиваем кол-во баллов за сообщение
        if item != None:
            # если у покупающего баллов больше, чем нужно (или ровно столько), то он может купить
            if int(buyer[2]) >= item[3]:
                # забираем баллы у купившего
                await conn.execute("UPDATE users SET points=$1 WHERE user_id=$2 AND server_id=$3",
                               int(buyer[2]) - int(item[3]), str(ctx.author.id), ctx.guild.id)

                # изменяем кол-во баллов за сообщение пользователю
                await conn.execute("UPDATE users SET payment=$1 WHERE user_id=$2 AND server_id=$3",
                               int(user_data[4]) + int(item[2]), str(user.id), ctx.guild.id)
                await ctx.send(f'{user.name} теперь получает больше баллов за сообщение!')
            else:
                await ctx.send('У вас нет нужного количества баллов')
        else:
            await ctx.send('Товар не найден')
    except IndexError:
        # возникает если таблица assortment для данного дискорд сервера пуста
        await ctx.send('Предметы данного дискорд сервера не найдены в базе данных')
    except Exception as ex:
        await ctx.send('Произошла ошибка')
        print(ex)


# добавляет товар в ассортимент сервера
@bot.command(name='add_item')
async def add_item(ctx, title: str, upgrade: int, price: int):
    try:
        if ctx.author.guild_permissions.administrator:
            conn = await create_connect()
            await conn.execute("INSERT INTO assortment VALUES ($1, $2, $3, $4, $5)",
                           str(uuid.uuid4()), title, upgrade, price, ctx.guild.id)
            await ctx.send(f'Товар с названием {title} был добавлен, его цена = {price}, '
                           f'он добавляет к получаемым баллам за сообщение {upgrade} баллов ')
        else:
            await ctx.send('У вас недостаточно прав для этого действия')
    except:
        await ctx.send('Произошла неизвестная ошибка')


# отображает список товаров (почему-то первый товар не отображается)
@bot.command(name='assortment')
async def see_assortment(ctx):
    try:
        conn = await create_connect()
        assortment = await conn.fetch("SELECT * FROM assortment WHERE server_id=$1", ctx.guild.id,)
        if assortment == None or len(assortment) == 0:
            await ctx.send('Товаров нет')
        else:
            assort = 'Список товаров: \n'
            for item in assortment:
                assort += f'{item[1]} имеет цену {item[3]} и добавляет {item[2]} баллов за сообщение \n'
            await ctx.send(assort)
    except Exception as ex:
        await ctx.send(ex)


@bot.command(name='delete_item')
async def delete_item(ctx, title):
    try:
        conn = await create_connect()
        if ctx.author.guild_permissions.administrator:
            await conn.execute("DELETE FROM assortment WHERE title=$1 AND server_id=$2", title, ctx.guild.id)
            #connection.commit()
            await ctx.send('Товар успешно удалён')
        else:
            await ctx.send('У вас недостаточно прав для этого действия')
    except:
        await ctx.send('Произошла неизвестная ошибка')


# изменяет количество баллов у пользователя (может как увеличить, так и уменьшить)
@bot.command(name='add_points')
async def add_points(ctx, user: discord.Member, num):
    try:
        if ctx.author.guild_permissions.administrator:
            conn = await create_connect()
            num = int(num)
            user_data = await conn.fetch("SELECT * FROM users WHERE user_id=$1 AND server_id=$2", str(user.id), ctx.guild.id)
            user_data = user_data[0]
            await conn.execute("UPDATE users SET points=$1 WHERE user_id=$2 AND server_id=$3",
                           (user_data[2] + num), str(user.id), ctx.guild.id)
            await ctx.send('Действие успешно выполнено!')
        else:
            await ctx.send('У вас недостаточно прав для этого действия')
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')


@bot.command(name='add_payment')
async def add_payment(ctx, user: discord.Member, num):
    try:
        if ctx.author.guild_permissions.administrator:
            conn = await create_connect()
            num = int(num)
            user_data = await conn.fetch("SELECT * FROM users WHERE user_id=$1 AND server_id=$2", str(user.id), ctx.guild.id)
            user_data = user_data[0]
            await conn.execute("UPDATE users SET payment=$1 WHERE user_id=$2 AND server_id=$3",
                               (int(user_data[4]) + num), str(user.id), ctx.guild.id)
            await ctx.send('Действие успешно выполнено!')
        else:
            await ctx.send('У вас недостаточно прав для этого действия')
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')


# максимальное количество одинаковых цифр в числе
def max_count_figure(number):
    number = str(number)
    max_count = 1
    for i in range(0, 10):
        count_number = number.count(str(i))
        if count_number > max_count:
            max_count = count_number
    return max_count


# делаем ставку валидной (False если ставка не корректная, int если ставка валидна)
def validate_bet(bet):
    try:
        # если ставка не является числом, то будет исключение
        bet = int(bet)

        # если ставка = 0, то будет исключение
        if bet == 0:
            return False

        # если ставка отрицательная, то делаем её положительной
        if bet < 0:
            bet = bet * -1

        # если ставка меньше 50, то делаем исключение
        if bet < 50:
            return False

        return bet
    except:
        return False


# создаёт случайное трёхзначное число, если 2 цифры одинаковые - выигрыш 1.5Х, если 3 одинаковые, то выигрыш = 3Х
@bot.command(name='casino')
async def casino(ctx, bet):
    try:
        # делаем ставку валидной
        bet = validate_bet(bet)

        # если ставка не валидная, то возвращаем ошибку
        if type(bet) == bool:
            raise Exception('Ставка не валидна')

        conn = await create_connect()
        user_data = await conn.fetch('SELECT * FROM users WHERE user_id=$1 AND server_id=$2', str(ctx.author.id), ctx.guild.id)
        user_data = user_data[0]

        # проверяем количество баллов пользователя
        if user_data[2] >= bet:
            number = random.randint(100, 999)
            # считаем количество одинаковых цифр
            count_figure = max_count_figure(number)

            if count_figure == 1:
                await conn.execute("UPDATE users SET points=$1 WHERE user_id=$2 AND server_id=$3",
                               user_data[2] - bet, str(ctx.author.id), ctx.guild.id)
                if bet >= 1000:
                    await ctx.reply(f'Выпало число {number} \nВы проиграли {bet} баллов ))))')
                else:
                    await ctx.reply(f'Выпало число {number} \nВы проиграли {bet} баллов')

            elif count_figure == 2:
                await conn.execute("UPDATE users SET points=$1 WHERE user_id=$2 AND server_id=$3",
                               user_data[2] + ((bet * 2) // 1), str(ctx.author.id), ctx.guild.id)
                await ctx.reply(f'Выпало число {number} \nВы выиграли {int((bet * 2) // 1)} баллов!')

            elif count_figure == 3:
                await conn.execute("UPDATE users SET points=$1 WHERE user_id=$2 AND server_id=$3",
                               user_data[2] + (bet * 4), str(ctx.author.id), ctx.guild.id)
                await ctx.reply(f'Выпало число {number} \nВы выиграли {bet * 4} баллов!')

        else:
            await ctx.reply('У вас не хватает баллов для этой ставки')
    except Exception as ex:
        await ctx.reply('Вы ввели некорректную ставку')
        print(ex)


# Запуск бота
bot.run(token)
