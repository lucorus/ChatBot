import discord
import requests
from config import access_token


'''
Если пользователь отправит боту токен из своего личного аккаунта, то бот отправит запрос на апи сервера
и тогда аккаунт на сервере станет привязан к аккаунту в дискорд,
но если пользователь хочет отвязать свой аккаунт от сайта, то он может написать delete боту
'''
async def private_message(message):
    if message.channel.type == discord.ChannelType.private and message.content != 'delete':
        requests.post(f'http://127.0.0.1:8000/authorize_user',
                      headers={'token': str(message.content),
                               'user': str(message.author.id),
                               'access': str(access_token)
                               })
        await message.channel.send('Ваш запрос отправлен на сервер')
    elif message.channel.type == discord.ChannelType.private and message.content == 'delete':
        requests.post(f'http://127.0.0.1:8000/anauthorizeuser',
                      headers={
                          'user': str(message.author.id),
                          'access': str(access_token)
                      })
    await message.channel.send('Ваш запрос отправлен на сервер')
