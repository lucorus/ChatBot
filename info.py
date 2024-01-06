import base


async def update_user_info(ctx):
    try:
        conn = await base.create_connect()
        await conn.execute(
            '''
            UPDATE users SET user_name=$1, user_icon=$2 WHERE user_id=$3;
            ''', str(ctx.author), str(ctx.author.avatar), ctx.author.id
        )
        await ctx.reply('Данные обновлены!')
    except Exception as ex:
        print(ex)
        await ctx.reply('Произошла неизвестная ошибка')


async def update_guild_info(ctx):
    try:
        if ctx.author.guild_permissions.administrator:
            conn = await base.create_connect()
            await conn.execute(
                '''
                UPDATE guilds SET guild_name=$1, guild_icon=$2 WHERE guild_id=$3;
                ''', str(ctx.guild.name), str(ctx.guild.icon), ctx.guild.id
            )
            await ctx.send('Данные сервера успешно обновлены!')
        else:
            await ctx.send('У вас нет прав для этого действия')
    except Exception as ex:
        print(ex)
        await ctx.send('Произошла неизвестная ошибка')
