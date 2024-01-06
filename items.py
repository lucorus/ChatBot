import uuid
import discord
import base


# получаем данные о товарах, которые находятся на переданном сервере
async def get_assortment(guild_id: int) -> list:
    try:
        conn = await base.create_connect()
        assortment = await conn.fetch(
            '''
            SELECT * FROM assortment WHERE guild=$1;
            ''', guild_id
        )
        return assortment
    except Exception as ex:
        print(ex)
        return []


async def get_item(title: str, guild_id: int) -> list:
    try:
        conn = await base.create_connect()
        item = await conn.fetch(
            '''
            SELECT * FROM assortment WHERE title=$1 AND guild=$2
            ''', title, guild_id
        )
        return item[0]
    except Exception as ex:
        print(ex)
        return []


# покупка предмета
async def buying_item(ctx, buyer: list, member: discord.Member, item: list) -> None:
    try:
        conn = await base.create_connect()
        # если у покупающего баллов больше, чем нужно (или ровно столько), то он может купить
        if int(buyer[2]) >= item[3]:
            # забираем баллы у купившего

            if await base.get_user(user_id=member.id, guild_id=ctx.guild.id) == []:
                raise Exception('Пользователя нет в базе данных')

            await conn.execute(
                '''
                UPDATE users SET points = points - $1 WHERE user_id=$2 AND guild=$3;
                ''', item[3], ctx.author.id, ctx.guild.id
            )

            # изменяем кол-во баллов за сообщение пользователю
            await conn.execute(
                '''
                UPDATE users SET payment = payment + $1 WHERE user_id=$2 AND guild=$3;
                ''', item[2], member.id, ctx.guild.id
            )
            await ctx.send('Действие выполнено успешно!')
        else:
            await ctx.send('У вас нет нужного количества баллов')
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')


async def delete_item(title: str, guild_id: int) -> None:
    try:
        conn = await base.create_connect()
        await conn.execute(
            '''
            DELETE FROM assortment WHERE guild=$1 AND title=$2;
            ''', guild_id, title
        )
    except Exception as ex:
        print(ex)


async def add_item_to_assortment(title: str, payment: int, price: int, guild_id: int) -> None:
    try:
        assortment = await get_assortment(guild_id)
        if title in str(assortment):
            # если предмет с переданным названием уже есть в ассортименте сервера, то удаляем его и создаём новый
            await delete_item(title, guild_id)

        conn = await base.create_connect()
        await conn.execute(
            '''
            INSERT INTO assortment VALUES ($1, $2, $3, $4, $5);
            ''', str(uuid.uuid4()), title, payment, price, guild_id
        )
    except Exception as ex:
        print(ex)
