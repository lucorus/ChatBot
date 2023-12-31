from discord.ext import commands
from datetime import datetime
from config import *
import requests
import asyncpg
import discord
import asyncio
import random
import pytz
import uuid

intents = discord.Intents.all()
bot = commands.Bot('!', intents=intents)
timezone = pytz.timezone('Europe/Moscow')


def time_now() -> str:
    moscow_time = datetime.now(timezone)
    formatted_time = moscow_time.strftime('%Y/%m/%d/%H/%M')
    return formatted_time


async def create_connect():
    try:
        conn = await asyncpg.connect(
            user=user, password=password,
            database=db_name, host=host
        )
        return conn
    except:
        print('Проблема с подключением к бд')


async def get_user(user_id: str, server_id: int) -> list:
    conn = await create_connect()

    user_data = await conn.fetch(
        '''
        SELECT * FROM users WHERE user_id=$1 AND server_id=$2
        ''', user_id, server_id)
    #print(type(user_data), type(user_data[0]))
    return user_data[0]


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

        # обновление имени пользователя
        if user_data[8] != str(ctx.author):
            await conn.execute('UPDATE users SET user_name=$1 WHERE user_id=$2',
                       str(ctx.author), str(ctx.author.id))

        # обновление иконки пользователя
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

            # Изменение названия сервера
            if server_data[6] != str(ctx.guild.name):
                await conn.execute('UPDATE users SET server_name=$1 WHERE server_id=$2',
                       str(ctx.guild.name), str(ctx.guild.id))

            # Изменение картинки сервера
            if server_data[7] != str(ctx.guild.icon):
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
        и тогда аккаунт на сервере станет привязан к записи дискорд,
        но если пользователь хочет отвязать свой аккаунт от сайта, то он может написать delete боту
        '''
        if message.channel.type == discord.ChannelType.private and message.content != 'delete':
            requests.post(f'http://127.0.0.1:8000/authorize_user',
                          headers={'token': str(message.content),
                                   'user': str(message.author.id),
                                   'access': str(access_token)
                                   }
                          )
            await message.channel.send('Ваш запрос отправлен на сервер')
        elif message.channel.type == discord.ChannelType.private and message.content == 'delete':
            requests.post(f'http://127.0.0.1:8000/anauthorizeuser',
                          headers={
                                   'user': str(message.author.id),
                                   'access': str(access_token)
                                   }
                          )
            await message.channel.send('Ваш запрос отправлен на сервер')


        # Получение данных пользователя из базы данных
        conn = await create_connect()
        user_data = await conn.fetch("SELECT * FROM users WHERE user_id=$1 AND server_id=$2", str(message.author.id), message.guild.id)
        if user_data == []:
            # Если пользователь не найден, добавляем его в базу данных
            await conn.execute("INSERT INTO users VALUES ($1, $2, $3, $4, 1, $5, $6, $7, $8, $9, 1)",
                           str(uuid.uuid4()), str(message.author.id), 1, time_now(),
                            message.guild.id, str(message.guild.name), str(message.guild.icon), str(message.author),
                            str(message.author.avatar))
        else:
            user_data = user_data[0]

            # Если пользователь найден, проверяем время последнего сообщения
            #last_message_time = int(user_data[3][-2::])
            #current_time = int(time_now()[-2::])
            time_difference = datetime.strptime(time_now(), "%Y/%m/%d/%H/%M") - datetime.strptime(str(user_data[3]), "%Y/%m/%d/%H/%M")
            # Если прошло больше минуты, добавляем баллы и обновляем время последнего сообщения
            if time_difference.total_seconds() >= 60:
                await conn.execute("UPDATE users SET points=$1, exp=$2, last_message_time=$3 WHERE user_id=$4 AND server_id=$5",
                             int(user_data[2] + user_data[4]), int(user_data[10] + 1), time_now(), str(message.author.id), message.guild.id)
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
    except IndexError:
        # если пользователь не отправлял сообщений с тех пор как бота добавили на сервер / такого пользователя нет
        await ctx.send('Пользователь не найден')
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')


# Получаем количество получаемых баллов за сообщение пользователя
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
    except IndexError:
        # если пользователь не отправлял сообщений с тех пор как бота добавили на сервер / такого пользователя нет
        await ctx.send('Пользователь не найден')
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')


@bot.command(name='exp')
async def get_user_exp(ctx, user: discord.Member = None):
    try:
        conn = await create_connect()
        if not user:
            user = ctx.author
        result = await conn.fetch("SELECT exp FROM users WHERE user_id=$1 AND server_id=$2", str(user.id), ctx.guild.id)
        result = result[0]
        if result:
            await ctx.send(f"Количество exp у {user.mention}: {result[0]}")
        else:
            await ctx.send(f"Количество exp у {user.mention}: 1")
    except IndexError:
        # если пользователь не отправлял сообщений с тех пор как бота добавили на сервер / такого пользователя нет
        await ctx.send('Пользователь не найден')
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')


# покупка предмета
async def buying_item(ctx, author_id, user_id, guild_id, user_data, buyer, item, conn, user_name):
    # если у покупающего баллов больше, чем нужно (или ровно столько), то он может купить
    if int(buyer[2]) >= item[3]:
        # забираем баллы у купившего
        await conn.execute("UPDATE users SET points=$1 WHERE user_id=$2 AND server_id=$3",
                           int(buyer[2]) - int(item[3]), author_id, guild_id)

        # изменяем кол-во баллов за сообщение пользователю
        await conn.execute("UPDATE users SET payment=$1 WHERE user_id=$2 AND server_id=$3",
                           int(user_data[4]) + int(item[2]), user_id, guild_id)
        await ctx.send(f'{user_name} теперь получает больше баллов за сообщение!')
    else:
        await ctx.send('У вас нет нужного количества баллов')


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
            await buying_item(ctx, str(ctx.author.id), str(user.id), ctx.guild.id, user_data, buyer, item, conn, user.name)
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
            await ctx.send('Товар успешно удалён')
        else:
            await ctx.send('У вас недостаточно прав для этого действия')
    except:
        await ctx.send('Произошла неизвестная ошибка')


async def change_count_points(user_id, guild_id, conn, points: int):
    user_data = await get_user(user_id, guild_id)
    await conn.execute(
        '''
        UPDATE users SET points=$1 WHERE user_id=$2 AND server_id=$3
        ''', (user_data[2] + points), user_id, guild_id)


# изменяет количество баллов у пользователя (может как увеличить, так и уменьшить)
@bot.command(name='add_points')
async def add_points(ctx, user: discord.Member, points):
    try:
        if str(ctx.author.id) == '854253015862607872':
            conn = await create_connect()
            await change_count_points(str(user.id), int(ctx.guild.id), conn, int(points))
        else:
            await ctx.send('У вас недостаточно прав для этого действия')
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')


@bot.command(name='add_payment')
async def add_payment(ctx, user: discord.Member, num):
    try:
        if str(ctx.author.id) == '854253015862607872':
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
                await change_count_points(str(ctx.author.id), int(ctx.guild.id), conn, -bet)
                if bet >= 1000:
                    await ctx.reply(f'Выпало число {number} \nВы проиграли {bet} баллов ))))')
                else:
                    await ctx.reply(f'Выпало число {number} \nВы проиграли {bet} баллов')

            elif count_figure == 2:
                await change_count_points(str(ctx.author.id), int(ctx.guild.id), conn, -(bet * 2))
                await ctx.reply(f'Выпало число {number} \nВы выиграли {int((bet * 2) // 1)} баллов!')

            elif count_figure == 3:
                await change_count_points(str(ctx.author.id), int(ctx.guild.id), conn, -(bet * 4))
                await ctx.reply(f'Выпало число {number} \nВы выиграли {bet * 4} баллов!')

        else:
            await ctx.reply('У вас не хватает баллов для этой ставки')
    except Exception as ex:
        await ctx.reply('Вы ввели некорректную ставку')
        print(ex)


# Вычисляет сколько баллов получил пользователь по депозиту с процентом contribution_coefficient
def calculate_percent(points, time_delta):
    points = points * (contribution_coefficient/100) + points
    time_delta -= 1
    if time_delta > 0:
        return calculate_percent(points, time_delta)
    else:
        return round(points)


# Изменяет кол-во баллов пользователя по его вкладу (возвращает True если было изменение, а иначе False)
async def calculate_deposit(deposit_uuid: str, points: int, deposit_last_update_time_time: str) -> bool:
    # находим кол-во дней со дня создания счёта
    time_delta = datetime.strptime(time_now(), "%Y/%m/%d/%H/%M")\
                 - datetime.strptime(deposit_last_update_time_time, "%Y/%m/%d/%H/%M")
    time_delta = time_delta.total_seconds() // 86400
    if time_delta >= 1:
        points = calculate_percent(points, time_delta)
        conn = await create_connect()
        await conn.execute(
            '''
            UPDATE deposit SET current_points=$1 AND last_update=$2 WHERE uuid=$3
            ''', points, time_now(), deposit_uuid)
        return True
    return False


# Возвращает информацию о депозите определённого пользователя
async def get_deposit_info(user_id: str, guild_id: int):
    try:
        conn = await create_connect()
        user_data = await get_user(user_id, guild_id)
        deposit = await conn.fetch(
            '''
            SELECT * FROM deposit WHERE investor=$1
            ''', user_data[0])
        change = await calculate_deposit(deposit[0][0], deposit[0][5], deposit[0][4])
        if change:
            deposit = await conn.fetch(
                '''
                SELECT * FROM deposit WHERE investor=$1
                ''', user_data)
        return deposit[0]
    except Exception as ex:
        print(ex)


def validate_time(number: str):
    if int(number) < 10:
        return number[1:]
    return number


# Получает время в формате %Y/%m/%d/%H/%M и возвращает в читабельном виде
def time(time: str) -> str:
    months = {'01': 'января', '02': 'февраля', '03': 'марта', '04': 'апреля', '05': 'мая', '06': 'июня', '07': 'июля',
              '08': 'августа', '09': 'сентября', '10': 'октября', '11': 'ноября', '12': 'декабря'}
    return(f'{ time[-5:-3] }:{ time[-2:] } {validate_time(time[-8:-6])}'
           f' {months[time[-11:-9]]} {time[:4]} года')


@bot.command(name='deposit_info')
async def deposit_info(ctx):
    deposit = await get_deposit_info(str(ctx.author.id), int(ctx.guild.id))

    if not deposit:
        await ctx.send('Депозита не существует')
    else:
        await ctx.send(f' ## Информация о вашем счёте: ##'
                       f'\n **Дата создания:** { time(deposit[3]) }'
                       #f'\n **Последнее обновление:** { time(deposit[4]) }'
                       f'\n **Изначальный размер депозита:** { deposit[2] }'
                       f'\n **Доступно для вывода:** { deposit[5] }')


# проверяем валидность суммы, которую пользователь хочет внести на счёт
def is_valid_deposit(points: int) -> bool:
    try:
        if points <= 10:
            return False
    except:
        return False


# создаёт депозит
async def create(ctx, conn, user, points: int):
    try:
        if user[2] >= points:
            await conn.fetch(
                '''
                INSERT INTO deposit VALUES($1, $2, $3, $4, $5, $6)
                ''', str(uuid.uuid4()), user[0], points, time_now(), time_now(), points
            )
            await change_count_points(user[1], user[5], conn, -points)
            await ctx.send('Счёт создан!')
        else:
            await ctx.send('У вас недостаточно баллов!')
    except:
        await ctx.send('Произошла неизвестная ошибка')


@bot.command(name='create_deposit')
async def create_deposit(ctx, points: int):
    try:
        if not is_valid_deposit(points):
            assert 'Невалидный депозит'
        user_id = str(ctx.author.id)
        guild_id = int(ctx.guild.id)
        deposit = await get_deposit_info(user_id, guild_id)

        if deposit:
            await ctx.send('Депозит уже существует')
        else:
            user_data = await get_user(user_id, guild_id)
            conn = await create_connect()
            await create(ctx, conn, user_data, points)
    except Exception as ex:
        print(ex)
        await ctx.send('Вы ввели некорректный размер депозита')


@bot.command(name='delete_deposit')
async def delete_deposit(ctx):
    try:
        user_id = str(ctx.author.id)
        guild_id = int(ctx.guild.id)
        deposit = await get_deposit_info(user_id, guild_id)
        if deposit != []:
            conn = await create_connect()
            await change_count_points(str(ctx.author.id), int(ctx.guild.id), conn, deposit[5])
            await conn.execute(
                '''
                DELETE FROM deposit WHERE uuid=$1
                ''', deposit[0]
            )
            await ctx.send('Депозит удалён')
        else:
            await ctx.send('Депозит не существует')
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')


bot.run(token)
