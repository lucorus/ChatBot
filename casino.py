import random
from typing import Union

import base


# максимальное количество одинаковых цифр в числе
def max_count_figure(number: Union[str, int]) -> int:
    number = str(number)
    if number[0] == number[1] == number[2]:
        return 3
    elif (number[0] == number[1]) or (number[0] == number[2]) or (number[1] == number[2]):
        return 2
    else:
        return 1


# делаем ставку валидной (False если ставка не корректная, int если ставка валидна)
def validate_bet(bet: str) -> Union[int, bool]:
    try:
        bet = int(bet)

        if bet < 10:
            return False

        return bet
    except:
        return False


# создаёт случайное трёхзначное число, если 2 цифры одинаковые - выигрыш 1.5Х, если 3 одинаковые, то выигрыш = 3Х
async def casino(ctx, bet: str) -> None:
    try:
        # делаем ставку валидной
        bet = validate_bet(bet)

        # если ставка не валидная, то возвращаем ошибку
        if type(bet) == bool:
            raise Exception('Ставка не валидна')

        if await base.get_field(user_id=ctx.author.id, guild_id=ctx.guild.id, field='points') >= bet:
            number = random.randint(100, 999)
            # считаем количество одинаковых цифр
            count_figure = max_count_figure(number)

            if count_figure == 1:
                await base.change_count_points(user_id=ctx.author.id, guild_id=ctx.guild.id, points=-bet)
                if bet >= 1000:
                    await ctx.reply(f'Выпало число {number} \nВы проиграли {bet} баллов ))))')
                else:
                    await ctx.reply(f'Выпало число {number} \nВы проиграли {bet} баллов')

            elif count_figure == 2:
                await base.change_count_points(user_id=ctx.author.id, guild_id=ctx.guild.id, points=bet*2)
                await ctx.reply(f'Выпало число {number} \nВы выиграли {int((bet * 2) // 1)} баллов!')

            elif count_figure == 3:
                await base.change_count_points(user_id=ctx.author.id, guild_id=ctx.guild.id, points=bet*4)
                await ctx.reply(f'Выпало число {number} \nВы выиграли {bet * 4} баллов!')
        else:
            await ctx.reply('У вас не хватает баллов для этой ставки')
    except Exception as ex:
        await ctx.reply('Вы ввели некорректную ставку')
        print(ex)

