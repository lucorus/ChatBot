from datetime import datetime
from config import *
import deposit
import requests
import asyncpg
import discord
import asyncio
import logging
import random
import pytz
import uuid

intents = discord.Intents.all()
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
    except Exception as ex:
        print(ex)


async def add_guild_to_database(guild) -> None:
    conn = await create_connect()
    server_id = guild.id
    server_name = str(guild.name)
    server_icon = str(guild.icon)

    await conn.fetch(
        '''
        INSERT INTO guilds VALUES ($1, $2, $3) ON CONFLICT (guild_id) DO NOTHING;;
        ''', server_id, server_name, server_icon
    )


async def add_user_to_database(author_id: int, guild_id: int, author_name: str, author_avatar: str) -> None:
    try:
        conn = await create_connect()
        await conn.execute(
            '''
            INSERT INTO users VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ''', str(uuid.uuid4()), author_id, 1, time_now(), 1, guild_id, author_name, author_avatar, 1
        )
    except Exception as ex:
        print(ex)


async def change_last_message_time(user_id: int, guild_id: int) -> None:
    try:
        conn = await create_connect()
        await conn.execute(
            '''
            UPDATE users SET last_message_time=$1 WHERE user_id=$2 AND guild=$3
            ''', time_now(), user_id, guild_id
        )
    except Exception as ex:
        print(ex)


async def change_count_points(user_id: int, guild_id: int, points: int) -> None:
    try:
        conn = await create_connect()
        await conn.execute(
            '''
            UPDATE users SET points = points + $1 WHERE user_id=$2 AND guild=$3
            ''', points, user_id, guild_id
        )
    except Exception as ex:
        print(ex)


async def change_count_exp(user_id: int, guild_id: int) -> None:
    try:
        conn = await create_connect()
        await conn.execute(
            '''
            UPDATE users SET exp = exp + 1 WHERE user_id=$1 AND guild=$2
            ''', user_id, guild_id
        )
    except Exception as ex:
        print(ex)


async def get_guild(guild_id: int) -> list:
    try:
        conn = await create_connect()

        server = await conn.fetch(
            '''
            SELECT * FROM guilds WHERE guild_id=$1
            ''', guild_id)

        return server[0]
    except Exception as ex:
        print(ex)
        return []


async def get_user(user_id: int, guild_id: int) -> list:
    try:
        conn = await create_connect()

        user_data = await conn.fetch(
            '''
            SELECT * FROM users WHERE user_id=$1 AND guild=$2
            ''', user_id, guild_id)
        return user_data[0]
    except Exception as ex:
        print(ex)
        return []


# получаем данные, которые находятся в переданном поле в таблице users
async def get_field(user_id: int, guild_id: int, field: str) -> int:
    try:
        conn = await create_connect()

        user_data = await conn.fetch(
            f'''
            SELECT { field } FROM users WHERE user_id=$1 AND guild=$2
            ''', user_id, guild_id)
        if user_data == []:
            return 1
        else:
            return user_data[0][0]
    except Exception as ex:
        print(ex)
        return 1


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
