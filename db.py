from config import *
import psycopg2



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
        CREATE TABLE IF NOT EXISTS guilds (
        guild_id BIGINT PRIMARY KEY,
        guild_name TEXT,
        guild_icon TEXT
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS users (
        uuid TEXT PRIMARY KEY,
        user_id BIGINT,
        points BIGINT DEFAULT 1,
        last_message_time TEXT,
        payment BIGINT DEFAULT 1,
        guild BIGINT REFERENCES guilds(guild_id),
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
        guild BIGINT REFERENCES guilds(guild_id)
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
