import itertools
import random

from simpleeval import simple_eval

from core.builtins import Bot
from core.component import module
from core.petal import gained_petal, lost_petal

no_solution = ['无解', '無解', 'none', 'n/a']


def calc(expr):
    expr = expr.replace("\\", "")
    try:
        return round(simple_eval(expr))
    except BaseException:
        return None


def is_valid(expr):
    operators = ['+', '-', '*', '/', '(', ')', '\\']
    numbers = [str(i) for i in range(1, 14)]
    valid_chars = numbers + operators
    valid_chars_set = set(valid_chars)

    i = 0
    num_numbers = 0
    while i < len(expr):
        char = expr[i]
        if char.isdigit():
            while i < len(expr) and expr[i].isdigit():
                i += 1
            num_numbers += 1
        elif char in valid_chars_set:
            i += 1
            if i < len(expr) and expr[i] == ' ':
                i += 1
                if i < len(expr) and expr[i] == ' ':
                    return False
            continue
        elif char == ' ':
            i += 1
            if i < len(expr):
                return False
        else:
            return False
    if num_numbers > 9:
        return False
    return True


async def find_solution(numbers):
    perms = list(itertools.permutations(numbers))
    operators = ['+', '-', '*', '/']
    exprs = list(itertools.product(operators, repeat=4))

    for perm in perms:
        for expr in exprs:  # 穷举就完事了
            exp = '(({}{}{}){}{}){}{}'.format(perm[0], expr[0], perm[1], expr[1], perm[2], expr[2], perm[3])
            if calc(exp) == 24:
                return exp
            exp = '({}{}{}){}({}{}{})'.format(perm[0], expr[0], perm[1], expr[1], perm[2], expr[2], perm[3])
            if calc(exp) == 24:
                return exp
            exp = '{}{}({}{}({}{}{}))'.format(perm[0], expr[0], perm[1], expr[1], perm[2], expr[2], perm[3])
            if calc(exp) == 24:
                return exp
            exp = '{}{}({}{}{}){}{}'.format(perm[0], expr[0], perm[1], expr[1], perm[2], expr[2], perm[3])
            if calc(exp) == 24:
                return exp
    return False


def contains_all_numbers(expr, numbers):
    used_numbers = [str(num) for num in numbers]
    i = 0
    while i < len(expr):
        char = expr[i]
        if char.isdigit():
            number = char
            while i + 1 < len(expr) and expr[i + 1].isdigit():
                number += expr[i + 1]
                i += 1
            if number in used_numbers:
                used_numbers.remove(number)
        i += 1

    return len(used_numbers) == 0


tf = module('twenty_four', alias=['twentyfour', '24'],
            desc='{twenty_four.help.desc}', developers=['DoroWolf'])
play_state = {}


@tf.command('{{twenty_four.help}}')
async def _(msg: Bot.MessageSession):
    use_markdown = False
    if msg.target.sender_from in ['Discord|Client', 'Kook|User']:
        use_markdown = True
    if msg.target.target_id in play_state and play_state[msg.target.target_id]['active']:
        await msg.finish(msg.locale.t('game.message.running'))
    play_state.update({msg.target.target_id: {'active': True}})

    numbers = [random.randint(1, 13) for _ in range(4)]
    solution = await find_solution(numbers)

    answer = await msg.wait_next_message(msg.locale.t('twenty_four.message', numbers=numbers), timeout=3600, append_instruction=False)
    expr = answer.as_display(text_only=True)
    if play_state[msg.target.target_id]['active']:
        play_state[msg.target.target_id]['active'] = False
        if expr.lower() in no_solution:
            if solution:
                send = msg.locale.t('twenty_four.message.incorrect.have_solution', solution=solution)
                if g_msg := (g_msg := await lost_petal(msg, 1)):
                    send += '\n' + g_msg
            else:
                send = msg.locale.t('twenty_four.message.correct')
                if (g_msg := await gained_petal(msg, 2)):
                    send += '\n' + g_msg
            if use_markdown:
                send.replace('*', '\*')
            await answer.finish(send)
        elif is_valid(expr):
            result = calc(expr)
            if result == 24 and contains_all_numbers(expr, numbers):
                send = msg.locale.t('twenty_four.message.correct')
                if (g_msg := await gained_petal(msg, 2)):
                    send += '\n' + g_msg
                await answer.finish(send)
            else:
                await answer.finish(msg.locale.t('twenty_four.message.incorrect'))
        else:
            await answer.finish(msg.locale.t('twenty_four.message.incorrect.error'))


@tf.command('stop {{game.help.stop}}')
async def s(msg: Bot.MessageSession):
    state = play_state.get(msg.target.target_id, False)
    if state:
        if state['active']:
            play_state[msg.target.target_id]['active'] = False
            await msg.finish(msg.locale.t('game.message.stop'))
        else:
            await msg.finish(msg.locale.t('game.message.stop.none'))
    else:
        await msg.finish(msg.locale.t('game.message.stop.none'))
