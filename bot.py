from discord.ext import commands
from datetime import datetime
from config import *
import requests
import psycopg2
import discord
import asyncio
import random
import uuid

intents = discord.Intents.all()

bot = commands.Bot('!', intents=intents)

# Подключение к базе данных
try:
    connection = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=db_name
    )

    cursor = connection.cursor()
    connection.autocommit = True
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS users (
        uuid TEXT PRIMARY KEY,
        user_id TEXT,
        points BIGINT DEFAULT 1,
        last_message_time TEXT,
        payment BIGINT DEFAULT 1,
        server_id BIGINT,
        server_name TEXT,
        server_icon TEXT,
        user_name TEXT,
        user_icon TEXT,
        exp BIGINT DEFAULT 1
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS assortment (
        uuid TEXT PRIMARY KEY,
        title TEXT, 
        upgrade INTEGER, 
        price INTEGER,
        server_id bigint
        )
        '''
    )

    # last_update - последнее время, когда вычислялось количество баллов на счету
    # current_points - сколько баллов накопилось на данный момент на счету
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS deposit (
        uuid TEXT PRIMARY KEY,
        investor TEXT REFERENCES users(uuid),
        points BIGINT, 
        created_add TEXT,
        last_update TEXT,
        current_points BIGINT 
        )
        '''
    )

except Exception as ex:
    print('POSTGRESQL: ', ex)


@bot.event
async def on_ready():
    while True:
        await asyncio.sleep(60)


@bot.event
async def on_disconnect():
    if connection:
        cursor.close()
        connection.close()
        print('PostgreSQL connection closed')


@bot.command(name='update_info')
async def update_user_info(ctx):
    try:
        cursor.execute(
            '''
            SELECT * FROM users WHERE user_id=%s AND server_id=%s LIMIT 1;
            ''', (str(ctx.author.id), str(ctx.guild.id))
        )
        user_data = cursor.fetchone()

        if user_data[8] != str(ctx.author):
            cursor.execute('UPDATE users SET user_name=%s WHERE user_id=%s',
                       (str(ctx.author), str(ctx.author.id)))
            connection.commit()

        if user_data[9] != str(ctx.author.avatar):
            cursor.execute('UPDATE users SET user_icon=%s WHERE user_id=%s',
                       (str(ctx.author.avatar), str(ctx.author.id)))
            connection.commit()
        await ctx.send('Данные обновлены!')
    except:
        await ctx.send('Произошла неизвестная ошибка')


@bot.command(name='update_server_info')
async def update_server_fields(ctx):
    try:
        if ctx.author.guild_permissions.administrator:
            cursor.execute('''
            SELECT * FROM users WHERE server_id=%s LIMIT 1;
            ''', (str(ctx.guild.id), ))
            server_data = cursor.fetchone()

            if server_data[6] != str(ctx.guild.name):
                cursor.execute('UPDATE users SET server_name=%s WHERE server_id=%s',
                       (str(ctx.guild.name), str(ctx.guild.id)))
                connection.commit()

            if server_data[7] != str(ctx.guild.icon):
                cursor.execute('UPDATE users SET server_icon=%s WHERE server_id=%s',
                       (str(ctx.guild.icon), str(ctx.guild.id)))
                connection.commit()
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
            requests.post(f'http://127.0.0.1:8000/authorize_user', data={'token': str(message.content), 'user': str(message.author.id), 'access_token': access_token})
            await message.channel.send('Ваш запрос отправлен на сервер')

        # Получение данных пользователя из базы данных
        cursor.execute("SELECT * FROM users WHERE user_id=%s AND server_id=%s", (str(message.author.id), message.guild.id))
        user_data = cursor.fetchone()

        if user_data is None:
            # Если пользователь не найден, добавляем его в базу данных
            cursor.execute("INSERT INTO users VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s, %s)",
                           (str(uuid.uuid4()), str(message.author.id), 0, int(datetime.utcnow().timestamp()),
                            message.guild.id, str(message.guild.name), str(message.guild.icon), str(message.author),
                            str(message.author.avatar)))
        else:
            # Если пользователь найден, проверяем время последнего сообщения
            last_message_time = user_data[3]
            current_time = int(datetime.utcnow().timestamp())
            time_difference = current_time - last_message_time

            # Если прошло больше минуты, добавляем баллы и обновляем время последнего сообщения
            if time_difference > 60:
                cursor.execute("UPDATE users SET points=%s, last_message_time=%s WHERE user_id=%s AND server_id=%s",
                               (user_data[2] + user_data[4], current_time, str(message.author.id), message.guild.id))

        connection.commit()
        await bot.process_commands(message)
    except Exception as ex:
        print(ex)
        print('text')
        pass


@bot.command(name='points')
async def get_user_points(ctx, user: discord.Member = None):
    try:
        if not user:
            user = ctx.author
        cursor.execute("SELECT points FROM users WHERE user_id=%s AND server_id=%s", (str(user.id), ctx.guild.id))
        result = cursor.fetchone()
        if result:
            await ctx.send(f"Количество баллов у {user.mention}: {result[0]}")
        else:
            await ctx.send(f"Количество баллов у {user.mention}: 0")
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')


# Получаем количество получаемых баллов за сообщение пользователя
@bot.command(name='payment')
async def get_user_payment(ctx, user: discord.Member = None):
    try:
        if not user:
            user = ctx.author
        cursor.execute("SELECT payment FROM users WHERE user_id=%s AND server_id=%s", (str(user.id), ctx.guild.id))
        result = cursor.fetchone()
        if result:
            await ctx.send(f"Количество баллов за сообщение у {user.mention}: {result[0]}")
        else:
            await ctx.send(f"Количество баллов за сообщение у {user.mention}: 1")
    except:
        await ctx.send('Произошла неизвестная ошибка')


@bot.command(name='exp')
async def get_user_exp(ctx, user: discord.Member = None):
    try:
        if not user:
            user = ctx.author
        cursor.execute("SELECT exp FROM users WHERE user_id=%s AND server_id=%s", (str(user.id), ctx.guild.id))
        result = cursor.fetchone()
        if result:
            await ctx.send(f"Количество exp у {user.mention}: {result[0]}")
        else:
            await ctx.send(f"Количество exp у {user.mention}: 1")
    except:
        await ctx.send('Произошла неизвестная ошибка')


# пользователь может купить предмет, увеличивающий кол-во баллов за сообщение (себе или другому человеку)
@bot.command(name='buy')
async def buy(ctx, user: discord.Member, title: str):
    try:
        if not user:
            user = ctx.author

        # берём данные пользователя, которому будут покупать товар, чтобы проверить его наличие
        cursor.execute("SELECT * FROM users WHERE user_id=%s AND server_id=%s", (str(user.id), ctx.guild.id))
        if cursor.fetchone() == None:
            raise Exception('Данного пользователя нет в базе данных')

        # берём данные покупающего пользователя
        cursor.execute("SELECT * FROM users WHERE user_id=%s AND server_id=%s", (str(ctx.author.id), ctx.guild.id))
        buyer = cursor.fetchone()
        # берём данные товара
        cursor.execute('SELECT * FROM assortment WHERE title=%s AND server_id=%s', (title, ctx.guild.id))
        item = cursor.fetchone()

        # если такой товар существует, то забираем его стоимость и увеличиваем кол-во баллов за сообщение
        if item != None:
            # если у покупающего баллов больше, чем нужно (или ровно столько), то он может купить
            if int(buyer[2]) >= int(item[3]):

                # забираем баллы у купившего
                cursor.execute("UPDATE users SET points=%s WHERE user_id=%s AND server_id=%s",
                               (int(buyer[2]) - int(item[3]), str(ctx.author.id), ctx.guild.id))

                # изменяем кол-во баллов за сообщение пользователю
                cursor.execute("SELECT * FROM users WHERE user_id=%s AND server_id=%s", (str(user.id), ctx.guild.id))
                user_data = cursor.fetchone()

                cursor.execute("UPDATE users SET payment=%s WHERE user_id=%s AND server_id=%s",
                               (int(user_data[4]) + int(item[2]), str(user.id), ctx.guild.id))
                connection.commit()
                await ctx.send(f'{user.name} теперь получает больше баллов за сообщение!')
            else:
                await ctx.send('У вас нет нужного количества баллов')
        else:
            await ctx.send('Товар не найден')
    except Exception as ex:
        await ctx.send('Произошла ошибка')
        print(ex)


# добавляет товар в ассортимент сервера
@bot.command(name='add_item')
async def add_item(ctx, title: str, upgrade: int, price: int):
    try:
        if ctx.author.guild_permissions.administrator:
            cursor.execute("INSERT INTO assortment VALUES (%s, %s, %s, %s, %s)",
                           (str(uuid.uuid4()), title, upgrade, price, ctx.guild.id))
            connection.commit()
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
        cursor.execute("SELECT * FROM assortment WHERE server_id=%s", (ctx.guild.id,))
        if cursor.fetchone() == None or len(cursor.fetchall()) == 0:
            await ctx.send('Товаров нет')
        else:
            assort = 'Список товаров: \n'
            for item in cursor.fetchall():
                assort += f'{item[1]} имеет цену {item[3]} и добавляет {item[2]} баллов за сообщение \n'
            await ctx.send(assort)
    except Exception as ex:
        await ctx.send(ex)


@bot.command(name='delete_item')
async def delete_item(ctx, title):
    try:
        if ctx.author.guild_permissions.administrator:
            cursor.execute("DELETE FROM assortment WHERE title=%s AND server_id=%s", (title, ctx.guild.id))
            connection.commit()
            await ctx.send('Товар успешно удалён')
        else:
            await ctx.send('У вас недостаточно прав для этого действия')
    except:
        await ctx.send('Произошла неизвестная ошибка')


# изменяет количество баллов у пользователя (может как увеличить, так и уменьшить)
@bot.command(name='add_points')
async def add_points(ctx, user: discord.Member, num):
    try:
        if str(ctx.author.id) == '854253015862607872':
            num = int(num)
            cursor.execute("SELECT * FROM users WHERE user_id=%s AND server_id=%s", (str(user.id), ctx.guild.id))
            user_data = cursor.fetchone()
            cursor.execute("UPDATE users SET points=%s WHERE user_id=%s AND server_id=%s",
                           ((user_data[2] + num), str(user.id), ctx.guild.id))
            connection.commit()
            await ctx.send('Действие успешно выполнено!')
        else:
            await ctx.send('У вас недостаточно прав для этого действия')
    except:
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

        cursor.execute('SELECT * FROM users WHERE user_id=%s AND server_id=%s', (str(ctx.author.id), ctx.guild.id))
        user_data = cursor.fetchone()

        # проверяем количество баллов пользователя
        if user_data[2] >= bet:
            number = random.randint(100, 999)
            # считаем количество одинаковых цифр
            count_figure = max_count_figure(number)

            if count_figure == 1:
                cursor.execute("UPDATE users SET points=%s WHERE user_id=%s AND server_id=%s",
                               (user_data[2] - bet, str(ctx.author.id), ctx.guild.id))
                if bet >= 1000:
                    await ctx.reply(f'Выпало число {number} \nВы проиграли {bet} баллов ))))')
                else:
                    await ctx.reply(f'Выпало число {number} \nВы проиграли {bet} баллов')

            elif count_figure == 2:
                cursor.execute("UPDATE users SET points=%s WHERE user_id=%s AND server_id=%s",
                               (user_data[2] + ((bet * 2) // 1), str(ctx.author.id), ctx.guild.id))
                await ctx.reply(f'Выпало число {number} \nВы выиграли {int((bet * 1.5) // 1)} баллов!')

            elif count_figure == 3:
                cursor.execute("UPDATE users SET points=%s WHERE user_id=%s AND server_id=%s",
                               (user_data[2] + (bet * 4), str(ctx.author.id), ctx.guild.id))
                await ctx.reply(f'Выпало число {number} \nВы выиграли {bet * 3} баллов!')

            connection.commit()

        else:
            await ctx.reply('У вас не хватает баллов для этой ставки')
    except Exception as ex:
        await ctx.reply('Вы ввели некорректную ставку')
        print(ex)


@bot.command(name='text')
async def text(ctx):
    await ctx.reply('text')


# Запуск бота
bot.run(token)

