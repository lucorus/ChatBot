import uuid
from datetime import datetime
import config
import base


# Вычисляет сколько баллов получил пользователь по депозиту с процентом contribution_coefficient
def calculate_percent(points, time_delta):
    points = points * (config.contribution_coefficient/100) + points
    time_delta -= 1
    if time_delta > 0:
        return calculate_percent(points, time_delta)
    else:
        return round(points)


# Изменяет кол-во баллов пользователя по его вкладу (возвращает True если было изменение, а иначе False)
async def calculate_deposit(deposit_uuid: str, points: int, deposit_last_update_time_time: str) -> bool:
    try:
        # находим кол-во дней со дня создания счёта
        time_delta = datetime.strptime(base.time_now(), "%Y/%m/%d/%H/%M")\
                    - datetime.strptime(deposit_last_update_time_time, "%Y/%m/%d/%H/%M")
        time_delta = time_delta.total_seconds() // 86400

        # если прошло больше дня с даты создания, то вычисляем сколько пользователь получил баллов
        if time_delta >= 1:
            points = calculate_percent(points, time_delta)
            conn = await base.create_connect()
            await conn.execute(
                '''
                UPDATE deposit SET current_points=$1, last_update=$2 WHERE uuid=$3
                ''', points, base.time_now(), deposit_uuid)
            return True
        else:
            return False
    except Exception as ex:
        print(ex)
        return False


async def get_deposit_info(user_id: int, guild_id: int) -> list:
    try:
        conn = await base.create_connect()
        user_data = await base.get_user(user_id, guild_id)
        deposit = await conn.fetch(
            '''
            SELECT * FROM deposit WHERE investor=$1
            ''', user_data[0]
        )

        change = await calculate_deposit(deposit[0][0], deposit[0][5], deposit[0][4])
        if change:
            deposit = await conn.fetch(
                '''
                SELECT * FROM deposit WHERE investor=$1
                ''', user_data[0]
            )
        return deposit[0]
    except Exception as ex:
        print(ex)
        return []


async def create_deposit(ctx, user: list, points: int) -> None:
    try:
        # если депозит уже существует, то информируем об этом
        deposit_data = await get_deposit_info(user_id=ctx.author.id, guild_id=ctx.guild.id)
        if deposit_data != []:
            await ctx.reply('У вас уже есть депозит!')
            return

        conn = await base.create_connect()
        if user[2] >= points >= 10:
            await conn.fetch(
                '''
                INSERT INTO deposit VALUES($1, $2, $3, $4, $5, $6)
                ''', str(uuid.uuid4()), user[0], points, base.time_now(), base.time_now(), points
            )
            await base.change_count_points(user[1], user[5], -points)
            await ctx.reply('Счёт создан!')
        else:
            await ctx.reply('У вас недостаточно баллов!')
    except Exception as ex:
        print(ex)
        await ctx.reply('Произошла неизвестная ошибка')


async def delete_deposit(ctx, user_id: int, guild_id: int):
    try:
        conn = await base.create_connect()
        deposit_data = await get_deposit_info(user_id, guild_id)

        await conn.execute(
            '''
            DELETE FROM deposit WHERE uuid=$1
            ''', deposit_data[0]
        )

        await base.change_count_points(user_id, guild_id, deposit_data[5])
        await ctx.reply('Действие выполнено успешно!')
    except IndexError:
        await ctx.reply('У вас нет депозита')
    except Exception as ex:
        print(ex)
        await ctx.reply('Произошла неизвестная ошибка')
