import wolframalpha
import asyncio

from core.builtins import Bot, Image
from core.component import module
from config import Config

client = wolframalpha.Client(Config('wolfram_alpha_appid'))

w = module(
    'wolframalpha',
    alias={
        'wolfram': 'wolframalpha'},
    developers=['Dianliang233'],
    desc='{wolframalpha.help.desc}',
    support_languages=['en'])


@w.handle('<query> {{wolframalpha.help.query}}')
async def _(msg: Bot.MessageSession):
    query = msg.parsed_msg['<query>']
    res = await asyncio.get_event_loop().run_in_executor(None, client.query, query)
    details = res.details
    answer = []
    images = []
    for title, detail in details.items():
        if title == 'Plot':
            continue
        answer.append(f'{title}: {detail}')
    # Parse out all images that don't have a plaintext counterpart
    for pod in res.pods:
        if pod.text is None and 'img' in pod.subpod:
            images.append(pod.subpod['img']['@src'])
    bot_images = [Image(image) for image in images]
    await msg.finish(['\n'.join(answer), *bot_images])