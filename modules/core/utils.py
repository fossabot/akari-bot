import platform
from datetime import datetime, timedelta

import jwt
import psutil
from cpuinfo import get_cpu_info

from config import Config
from core.builtins import Bot, Plain, Url
from core.component import module
from core.utils.i18n import get_available_locales, Locale, load_locale_file
from core.utils.info import Info
from core.utils.web_render import WebRender
from database import BotDBUtil

import subprocess

jwt_secret = Config('jwt_secret', cfg_type = str)

ver = module('version', base=True)


@ver.command('{{core.help.version}}')
async def bot_version(msg: Bot.MessageSession):
    if Info.version:
        commit = Info.version[0:6]
        repo_url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url']).decode().strip()
        repo_url = repo_url.replace('.git', '')  # Remove .git from the repo URL
        commit_url = f"{repo_url}/commit/{commit}"
        await msg.finish([Plain(msg.locale.t('core.message.version', commit=commit)), Url(commit_url)])
    else:
        await msg.finish(msg.locale.t('core.message.version.unknown'))


ping = module('ping', base=True)

started_time = datetime.now()


@ping.command('{{core.help.ping}}')
async def _(msg: Bot.MessageSession):
    result = "Pong!"
    if msg.check_super_user():
        timediff = str(datetime.now() - started_time)
        boot_start = msg.ts2strftime(psutil.boot_time())
        web_render_status = str(WebRender.status)
        cpu_usage = psutil.cpu_percent()
        ram = int(psutil.virtual_memory().total / (1024 * 1024))
        ram_percent = psutil.virtual_memory().percent
        swap = int(psutil.swap_memory().total / (1024 * 1024))
        swap_percent = psutil.swap_memory().percent
        disk = int(psutil.disk_usage('/').used / (1024 * 1024 * 1024))
        disk_total = int(psutil.disk_usage('/').total / (1024 * 1024 * 1024))
        result += '\n' + msg.locale.t("core.message.ping.detail",
                                      system_boot_time=boot_start,
                                      bot_running_time=timediff,
                                      python_version=platform.python_version(),
                                      web_render_status=web_render_status,
                                      cpu_brand=get_cpu_info()['brand_raw'],
                                      cpu_usage=cpu_usage,
                                      ram=ram,
                                      ram_percent=ram_percent,
                                      swap=swap,
                                      swap_percent=swap_percent,
                                      disk_space=disk,
                                      disk_space_total=disk_total)
    await msg.finish(result)


admin = module('admin',
               base=True,
               required_admin=True,
               alias={'ban': 'admin ban',
                      'unban': 'admin unban',
                      'ban list': 'admin ban list'},
               desc='{core.help.admin.desc}')


@admin.command([
    'add <user> {{core.help.admin.add}}',
    'remove <user> {{core.help.admin.remove}}',
    'list {{core.help.admin.list}}'])
async def config_gu(msg: Bot.MessageSession):
    if 'list' in msg.parsed_msg:
        if msg.custom_admins:
            await msg.finish(msg.locale.t("core.message.admin.list") + '\n'.join(msg.custom_admins))
        else:
            await msg.finish(msg.locale.t("core.message.admin.list.none"))
    user = msg.parsed_msg['<user>']
    if not user.startswith(f'{msg.target.sender_from}|'):
        await msg.finish(msg.locale.t('core.message.admin.invalid', sender=msg.target.sender_from, prefix=msg.prefixes[0]))
    if 'add' in msg.parsed_msg:
        if user and user not in msg.custom_admins:
            if msg.data.add_custom_admin(user):
                await msg.finish(msg.locale.t("core.message.admin.add.success", user=user))
        else:
            await msg.finish(msg.locale.t("core.message.admin.already"))
    if 'remove' in msg.parsed_msg:
        if user == msg.target.sender_id:
            confirm = await msg.wait_confirm(msg.locale.t("core.message.admin.remove.confirm"))
            if not confirm:
                await msg.finish()
        if user:
            if msg.data.remove_custom_admin(user):
                await msg.finish(msg.locale.t("core.message.admin.remove.success", user=user))


@admin.command('ban <user> {{core.help.admin.ban}}',
               'unban <user> {{core.help.admin.unban}}',
               'ban list {{core.help.admin.ban.list}}')
async def config_ban(msg: Bot.MessageSession):
    admin_ban_list = msg.options.get('ban', [])
    if 'list' in msg.parsed_msg:
        if admin_ban_list:
            await msg.finish(msg.locale.t("core.message.admin.ban.list") + '\n'.join(admin_ban_list))
        else:
            await msg.finish(msg.locale.t("core.message.admin.ban.list.none"))
    user = msg.parsed_msg['<user>']
    if not user.startswith(f'{msg.target.sender_from}|'):
        await msg.finish(msg.locale.t('core.message.admin.invalid', sender=msg.target.sender_from, prefix=msg.prefixes[0]))
    if user == msg.target.sender_id:
        await msg.finish(msg.locale.t("core.message.admin.ban.self"))
    if 'ban' in msg.parsed_msg:
        if user not in admin_ban_list:
            msg.data.edit_option('ban', admin_ban_list + [user])
            await msg.finish(msg.locale.t('success'))
        else:
            await msg.finish(msg.locale.t("core.message.admin.ban.already"))
    if 'unban' in msg.parsed_msg:
        if user in (banlist := admin_ban_list):
            banlist.remove(user)
            msg.data.edit_option('ban', banlist)
            await msg.finish(msg.locale.t('success'))
        else:
            await msg.finish(msg.locale.t("core.message.admin.ban.not_yet"))


locale = module('locale', base=True, desc='{core.help.locale.desc}', alias='lang')


@locale.command()
async def _(msg: Bot.MessageSession):
    avaliable_lang = msg.locale.t("message.delimiter").join(get_available_locales())
    res = msg.locale.t("core.message.locale", lang=msg.locale.t("language")) + '\n' + \
        msg.locale.t("core.message.locale.set.prompt", prefix=msg.prefixes[0]) + '\n' + \
        msg.locale.t("core.message.locale.langlist", langlist=avaliable_lang)
    if Config('locale_url', cfg_type = str):
        res += '\n' + msg.locale.t("core.message.locale.contribute", url=Config('locale_url', cfg_type = str))
    await msg.finish(res)


@locale.command('[<lang>] {{core.help.locale.set}}', required_admin=True)
async def config_gu(msg: Bot.MessageSession, lang: str):
    if lang in get_available_locales() and BotDBUtil.TargetInfo(msg.target.target_id).edit('locale', lang):
        await msg.finish(Locale(lang).t("success"))
    else:
        avaliable_lang = msg.locale.t("message.delimiter").join(get_available_locales())
        res = msg.locale.t("core.message.locale.set.invalid") + '\n' + \
            msg.locale.t("core.message.locale.langlist", langlist=avaliable_lang)
        await msg.finish(res)


@locale.command('reload', required_superuser=True)
async def reload_locale(msg: Bot.MessageSession):
    err = load_locale_file()
    if len(err) == 0:
        await msg.finish(msg.locale.t("success"))
    else:
        await msg.finish(msg.locale.t("core.message.locale.reload.failed", detail='\n'.join(err)))


whoami = module('whoami', base=True)


@whoami.command('{{core.help.whoami}}')
async def _(msg: Bot.MessageSession):
    perm = ''
    if await msg.check_native_permission():
        perm += '\n' + msg.locale.t("core.message.whoami.admin")
    elif await msg.check_permission():
        perm += '\n' + msg.locale.t("core.message.whoami.botadmin")
    if msg.check_super_user():
        perm += '\n' + msg.locale.t("core.message.whoami.superuser")
    await msg.finish(
        msg.locale.t('core.message.whoami', sender=msg.target.sender_id, target=msg.target.target_id) + perm)


setup = module('setup', base=True, desc='{core.help.setup.desc}', alias='toggle')


@setup.command('typing {{core.help.setup.typing}}')
async def _(msg: Bot.MessageSession):
    target = BotDBUtil.SenderInfo(msg.target.sender_id)
    state = target.query.disable_typing
    if not state:
        target.edit('disable_typing', True)
        await msg.finish(msg.locale.t('core.message.setup.typing.disable'))
    else:
        target.edit('disable_typing', False)
        await msg.finish(msg.locale.t('core.message.setup.typing.enable'))

'''
@setup.command('check {{core.help.setup.check}}', required_admin=True)
async def _(msg: Bot.MessageSession):
    state = msg.options.get('typo_check')
    if state:
        msg.data.edit_option('typo_check', False)
        await msg.finish(msg.locale.t('core.message.setup.check.enable'))
    else:
        msg.data.edit_option('typo_check', True)
        await msg.finish(msg.locale.t('core.message.setup.check.disable'))
'''


@setup.command('timeoffset <offset> {{core.help.setup.timeoffset}}', required_admin=True)
async def _(msg: Bot.MessageSession, offset: str):
    try:
        tstr_split = [int(part) for part in offset.split(':')]
        hour = tstr_split[0]
        minute = tstr_split[1] if len(tstr_split) > 1 else 0
        if minute == 0:
            offset = f"{'+' if hour >= 0 else '-'}{abs(hour)}"
        else:
            symbol = offset[0] if offset.startswith(("+", "-")) else "+"
            offset = f"{symbol}{abs(hour)}:{abs(minute):02d}"
        if hour > 12 or minute >= 60:
            raise ValueError
    except ValueError:
        await msg.finish(msg.locale.t('core.message.setup.timeoffset.invalid'))
    msg.data.edit_option('timezone_offset', offset)
    await msg.finish(msg.locale.t('core.message.setup.timeoffset.success',
                                  offset='' if offset == '+0' else offset))


mute = module('mute', base=True, required_admin=True)


@mute.command('{{core.help.mute}}')
async def _(msg: Bot.MessageSession):
    state = msg.data.switch_mute()
    if state:
        await msg.finish(msg.locale.t('core.message.mute.enable'))
    else:
        await msg.finish(msg.locale.t('core.message.mute.disable'))


leave = module('leave', base=True, required_admin=True, available_for=['QQ|Group'], alias='dismiss')


@leave.command('{{core.help.leave}}')
async def _(msg: Bot.MessageSession):
    confirm = await msg.wait_confirm(msg.locale.t('core.message.leave.confirm'))
    if confirm:
        await msg.send_message(msg.locale.t('core.message.leave.success'))
        await msg.call_api('set_group_leave', group_id=msg.session.target)
    else:
        await msg.finish()


token = module('token', base=True, hide=True)


@token.command('<code> {{core.help.token}}')
async def _(msg: Bot.MessageSession, code: str):
    await msg.finish(jwt.encode({
        'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24 * 7),  # 7 days
        'iat': datetime.utcnow(),
        'senderId': msg.target.sender_id,
        'code': code
    }, bytes(jwt_secret, 'utf-8'), algorithm='HS256'))
