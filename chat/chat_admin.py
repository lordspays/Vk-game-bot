import logging
from aiogram import types
from aiogram.dispatcher import Dispatcher
from Config import bot
from datetime import datetime, timedelta
import re

# ==================== ХРАНИЛИЩЕ (ТОЛЬКО ПАМЯТЬ) ====================

chat_admins = {}          # {chat_id: [user_id]}
banned_users = {}         # {chat_id: {user_id: время_разблокировки}}
restricted_mode = {}      # {chat_id: bool}

logger = logging.getLogger(__name__)

# ==================== ПАРСЕР ВРЕМЕНИ ====================

def parse_time(time_str: str):
    """
    Парсит: 30сек, 5мин, 2ч, 7д, 3мес, 1год, навсегда
    """
    time_str = time_str.lower().replace(' ', '')
    
    if time_str in ['навсегда', 'forever', '0', 'перманент']:
        return None, 'навсегда'
    
    units = {
        'сек': ('секунд', 1),
        'с': ('секунд', 1),
        'мин': ('минут', 60),
        'м': ('минут', 60),
        'ч': ('часов', 3600),
        'час': ('часов', 3600),
        'д': ('дней', 86400),
        'дн': ('дней', 86400),
        'день': ('дней', 86400),
        'мес': ('месяцев', 2592000),
        'месяц': ('месяцев', 2592000),
        'год': ('лет', 31536000),
        'г': ('лет', 31536000)
    }
    
    match = re.match(r'(\d+)\s*([а-яa-z]+)', time_str)
    if not match:
        return timedelta(minutes=5), '5 минут'
    
    value = int(match.group(1))
    unit = match.group(2)
    
    for key, (text, seconds) in units.items():
        if unit.startswith(key):
            delta = timedelta(seconds=value * seconds)
            return delta, f'{value} {text}'
    
    return timedelta(minutes=5), '5 минут'

# ==================== ПОЛУЧЕНИЕ ЦЕЛИ ====================

async def get_target_user(message: types.Message):
    """
    Определяет целевого пользователя из:
    1. Ответа на сообщение
    2. Упоминания @username
    3. ID в тексте
    Возвращает (user_id, full_name, username_mention)
    """
    chat_id = message.chat.id
    
    # 1. Ответ на сообщение
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        mention = f"@{user.username}" if user.username else f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
        return user.id, user.full_name, mention
    
    # 2. Разбираем аргументы
    args = message.text.split()
    if len(args) < 2:
        return None, None, None
    
    target_arg = args[1]
    
    # 3. Упоминание @username
    if target_arg.startswith('@'):
        try:
            chat_member = await bot.get_chat_member(chat_id, target_arg)
            user = chat_member.user
            mention = f"@{user.username}" if user.username else f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
            return user.id, user.full_name, mention
        except:
            return None, None, None
    
    # 4. ID
    try:
        user_id = int(target_arg)
        chat_member = await bot.get_chat_member(chat_id, user_id)
        user = chat_member.user
        mention = f"@{user.username}" if user.username else f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
        return user.id, user.full_name, mention
    except:
        return None, None, None

# ==================== ПРОВЕРКА ПРАВ ====================

async def is_owner(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status == 'creator'
    except:
        return False

async def is_chat_admin(chat_id: int, user_id: int) -> bool:
    if await is_owner(chat_id, user_id):
        return True
    return user_id in chat_admins.get(chat_id, [])

async def require_chat_admin(message: types.Message):
    if not await is_chat_admin(message.chat.id, message.from_user.id):
        await message.reply("⛔ Только администраторы чата могут использовать эту команду.")
        return False
    return True

# ==================== НАЗНАЧЕНИЕ / СНЯТИЕ АДМИНОВ ====================

async def cmd_chat_assign(message: types.Message):
    """Чат назначить — через ответ или ID"""
    if not await require_chat_admin(message):
        return
    
    target_id, target_name, target_mention = await get_target_user(message)
    
    if not target_id:
        await message.reply("❌ Укажите пользователя: ответьте на сообщение, укажите @username или ID.")
        return
    
    chat_id = message.chat.id
    
    if await is_owner(chat_id, target_id):
        await message.reply("👑 Владелец чата уже имеет все права.")
        return
    
    if chat_id not in chat_admins:
        chat_admins[chat_id] = []
    
    if target_id not in chat_admins[chat_id]:
        chat_admins[chat_id].append(target_id)
        await message.reply(f"✅ {target_mention} назначен(а) администратором чата.")
    else:
        await message.reply(f"ℹ️ {target_mention} уже администратор.")

async def cmd_chat_remove(message: types.Message):
    """чат снять — через ответ или ID"""
    if not await require_chat_admin(message):
        return
    
    target_id, target_name, target_mention = await get_target_user(message)
    
    if not target_id:
        await message.reply("❌ Укажите пользователя: ответьте на сообщение, укажите @username или ID.")
        return
    
    chat_id = message.chat.id
    
    if await is_owner(chat_id, target_id):
        await message.reply("👑 Нельзя снять права у владельца чата.")
        return
    
    if chat_id in chat_admins and target_id in chat_admins[chat_id]:
        chat_admins[chat_id].remove(target_id)
        await message.reply(f"✅ У {target_mention} сняты права администратора.")
    else:
        await message.reply(f"ℹ️ {target_mention} не является администратором.")

# ==================== МУТ ====================

async def cmd_mute(message: types.Message):
    """Мут [время] — через ответ или ID"""
    if not await require_chat_admin(message):
        return
    
    target_id, target_name, target_mention = await get_target_user(message)
    
    if not target_id:
        await message.reply("❌ Укажите пользователя: ответьте на сообщение, укажите @username или ID.")
        return
    
    chat_id = message.chat.id
    
    if await is_chat_admin(chat_id, target_id):
        await message.reply("⛔ Нельзя замутить администратора чата.")
        return
    
    # Парсим время
    args = message.text.split()
    if len(args) >= 3 and not message.reply_to_message:
        time_arg = ' '.join(args[2:])
    elif message.reply_to_message and len(args) >= 2:
        time_arg = ' '.join(args[1:])
    else:
        time_arg = '5мин'
    
    duration_delta, duration_text = parse_time(time_arg)
    
    try:
        if duration_delta is None:
            await bot.restrict_chat_member(
                chat_id,
                target_id,
                can_send_messages=False
            )
        else:
            await bot.restrict_chat_member(
                chat_id,
                target_id,
                can_send_messages=False,
                until_date=datetime.now() + duration_delta
            )
        
        await message.reply(f"🔇 Игрок {target_mention} ограничен(а) в чате на {duration_text}.")
        
    except Exception as e:
        await message.reply(f"❌ Ошибка: {str(e)}")

async def cmd_unmute(message: types.Message):
    """анмут — через ответ или ID"""
    if not await require_chat_admin(message):
        return
    
    target_id, target_name, target_mention = await get_target_user(message)
    
    if not target_id:
        await message.reply("❌ Укажите пользователя: ответьте на сообщение, укажите @username или ID.")
        return
    
    chat_id = message.chat.id
    
    try:
        await bot.restrict_chat_member(
            chat_id,
            target_id,
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        
        await message.reply(f"✅ {target_mention} снова может писать в чат.")
        
    except Exception as e:
        await message.reply(f"❌ Ошибка: {str(e)}")

# ==================== БАН ====================

async def cmd_block(message: types.Message):
    """Блок [время] — через ответ или ID"""
    if not await require_chat_admin(message):
        return
    
    target_id, target_name, target_mention = await get_target_user(message)
    
    if not target_id:
        await message.reply("❌ Укажите пользователя: ответьте на сообщение, укажите @username или ID.")
        return
    
    chat_id = message.chat.id
    
    if await is_chat_admin(chat_id, target_id):
        await message.reply("⛔ Нельзя заблокировать администратора чата.")
        return
    
    # Парсим время
    args = message.text.split()
    if len(args) >= 3 and not message.reply_to_message:
        time_arg = ' '.join(args[2:])
    elif message.reply_to_message and len(args) >= 2:
        time_arg = ' '.join(args[1:])
    else:
        time_arg = '5мин'
    
    duration_delta, duration_text = parse_time(time_arg)
    
    try:
        if duration_delta is None:
            await bot.ban_chat_member(chat_id, target_id)
            unban_time = None
        else:
            until_date = datetime.now() + duration_delta
            await bot.ban_chat_member(chat_id, target_id, until_date=until_date)
            unban_time = until_date
        
        # Сохраняем в память
        if chat_id not in banned_users:
            banned_users[chat_id] = {}
        
        if unban_time:
            banned_users[chat_id][target_id] = unban_time
        else:
            banned_users[chat_id][target_id] = datetime.now() + timedelta(days=3650)
        
        await message.reply(f"🔨 Игрок {target_mention} заблокирован(а) в чате на {duration_text}.")
        
    except Exception as e:
        await message.reply(f"❌ Ошибка: {str(e)}")

async def cmd_unblock(message: types.Message):
    """анблок — через ответ или ID"""
    if not await require_chat_admin(message):
        return
    
    target_id, target_name, target_mention = await get_target_user(message)
    
    if not target_id:
        await message.reply("❌ Укажите пользователя: ответьте на сообщение, укажите @username или ID.")
        return
    
    chat_id = message.chat.id
    
    try:
        await bot.unban_chat_member(chat_id, target_id)
        
        if chat_id in banned_users and target_id in banned_users[chat_id]:
            del banned_users[chat_id][target_id]
        
        await message.reply(f"✅ {target_mention} разблокирован(а).")
        
    except Exception as e:
        await message.reply(f"❌ Ошибка: {str(e)}")

# ==================== КИК ====================

async def cmd_kick(message: types.Message):
    """Кик — через ответ или ID"""
    if not await require_chat_admin(message):
        return
    
    target_id, target_name, target_mention = await get_target_user(message)
    
    if not target_id:
        await message.reply("❌ Укажите пользователя: ответьте на сообщение, укажите @username или ID.")
        return
    
    chat_id = message.chat.id
    
    if await is_chat_admin(chat_id, target_id):
        await message.reply("⛔ Нельзя кикнуть администратора чата.")
        return
    
    try:
        await bot.ban_chat_member(chat_id, target_id)
        await bot.unban_chat_member(chat_id, target_id)
        
        await message.reply(f"👢 Игрок {target_mention} кикнут(а) из чата.")
        
    except Exception as e:
        await message.reply(f"❌ Ошибка: {str(e)}")

# ==================== РЕЖИМ ЧАТА ====================

async def cmd_chat_restrict(message: types.Message):
    """-Чат"""
    if not await require_chat_admin(message):
        return
    
    chat_id = message.chat.id
    restricted_mode[chat_id] = True
    
    await bot.set_chat_permissions(
        chat_id,
        types.ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False
        )
    )
    
    await message.reply("🔒 Чат переведён в режим «только для администраторов».")

async def cmd_chat_open(message: types.Message):
    """+чат"""
    if not await require_chat_admin(message):
        return
    
    chat_id = message.chat.id
    restricted_mode[chat_id] = False
    
    await bot.set_chat_permissions(
        chat_id,
        types.ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
    )
    
    await message.reply("🔓 Чат снова доступен для всех пользователей.")

# ==================== УПРАВЛЕНИЕ СООБЩЕНИЯМИ ====================

async def cmd_delete_user_message(message: types.Message):
    """-смс (ответом)"""
    if not await require_chat_admin(message):
        return
    
    if not message.reply_to_message:
        await message.reply("❌ Ответьте этой командой на сообщение, которое нужно удалить.")
        return
    
    try:
        await message.reply_to_message.delete()
        await message.reply("✅ Сообщение удалено.")
    except:
        await message.reply("❌ Не удалось удалить сообщение.")

async def cmd_delete_bot_message(message: types.Message):
    """-гсмс (ответом)"""
    if not await require_chat_admin(message):
        return
    
    if not message.reply_to_message or not message.reply_to_message.from_user.is_bot:
        await message.reply("❌ Ответьте этой командой на сообщение бота.")
        return
    
    try:
        await message.reply_to_message.delete()
        await message.reply("✅ Сообщение бота удалено.")
    except:
        await message.reply("❌ Не удалось удалить сообщение.")

async def cmd_edit_bot_message(message: types.Message):
    """Ред (ответом + новый текст)"""
    if not await require_chat_admin(message):
        return
    
    if not message.reply_to_message or not message.reply_to_message.from_user.is_bot:
        await message.reply("❌ Ответьте этой командой на сообщение бота.")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("❌ Укажите новый текст сообщения.")
        return
    
    try:
        await message.reply_to_message.edit_text(args[1])
        await message.reply("✅ Сообщение бота отредактировано.")
    except:
        await message.reply("❌ Не удалось отредактировать сообщение.")

# ==================== ПОМОЩЬ ПО ЧАТУ ====================

async def cmd_chat_help(message: types.Message):
    """Чат помощь — отображает справочную информацию"""
    
    help_text = (
        "📖 Помощь по функционалу [https://vk.ru/spaysexbot|𝐆𝐘𝐌 𝐋𝐄𝐆𝐄𝐍𝐃 𝐁𝐎𝐓]\n"
        "Список всех команд в статье: vk.com/@spaysexbot-chat-help\n\n"
        "👨‍💻 АГЕНТЫ ПОДДЕРЖКИ: (им можно задать вопросы)\n"
        "@spaysex — Поддержка 𝐆𝐘𝐌 𝐋𝐄𝐆𝐄𝐍𝐃 𝐁𝐎Т\n"
        "@bananyc — Администрация 𝐆𝐘𝐌 𝐋𝐄𝐆𝐄𝐍𝐃 𝐁𝐎Т\n\n"
        "🔗 Также за помощью Вы можете обратиться в официальную группу тех.поддержки\n"
        "vk.com/spaysex_helpbot"
    )
    
    await message.reply(help_text, disable_web_page_preview=False)

# ==================== РЕГИСТРАЦИЯ ====================

def register_chat_admin_system(dp: Dispatcher):
    """Регистрация всех команд"""
    
    dp.register_message_handler(cmd_chat_assign, lambda msg: msg.text and msg.text.lower().startswith('чат назначить'))
    dp.register_message_handler(cmd_chat_remove, lambda msg: msg.text and msg.text.lower().startswith('чат снять'))
    
    dp.register_message_handler(cmd_mute, lambda msg: msg.text and msg.text.lower().startswith('мут'))
    dp.register_message_handler(cmd_unmute, lambda msg: msg.text and msg.text.lower().startswith('анмут'))
    dp.register_message_handler(cmd_kick, lambda msg: msg.text and msg.text.lower().startswith('кик'))
    dp.register_message_handler(cmd_block, lambda msg: msg.text and msg.text.lower().startswith('блок'))
    dp.register_message_handler(cmd_unblock, lambda msg: msg.text and msg.text.lower().startswith('анблок'))
    
    dp.register_message_handler(cmd_chat_restrict, lambda msg: msg.text and msg.text.strip() == '-Чат')
    dp.register_message_handler(cmd_chat_open, lambda msg: msg.text and msg.text.strip() == '+чат')
    
    dp.register_message_handler(cmd_delete_user_message, lambda msg: msg.text and msg.text.strip() == '-смс')
    dp.register_message_handler(cmd_delete_bot_message, lambda msg: msg.text and msg.text.strip() == '-гсмс')
    dp.register_message_handler(cmd_edit_bot_message, lambda msg: msg.text and msg.text.lower().startswith('ред'))
    
    # КОМАНДА ПОМОЩИ - ДОСТУПНА ВСЕМ
    dp.register_message_handler(cmd_chat_help, lambda msg: msg.text and msg.text.lower() == 'чат помощь')
