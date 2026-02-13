import re
import random
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text

from bot.core.config import settings
from bot.db import get_player, update_player_balance
from bot.utils import format_number, parse_amount_string

casino_labeler = BotLabeler()
casino_labeler.vbml_ignore_case = True

# Хранилище временных данных игроков для букмекерской конторы
# Структура: {user_id: {"game": int, "choice": any, "stage": str}}
betting_sessions = {}


def get_main_betting_keyboard():
    """Главное меню букмекерской конторы"""
    keyboard = Keyboard(inline=True)
    # Первый ряд - две кнопки
    keyboard.add(Text("🥊 Подвальные соревнования"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🏆 Всероссийские соревнования"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    # Второй ряд - большая кнопка во всю ширину
    keyboard.add(Text("⚔️ Ставки на команду"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    # Третий ряд - большая кнопка назад
    keyboard.add(Text("◀️ Назад"), color=KeyboardButtonColor.SECONDARY)
    return keyboard


def get_back_keyboard():
    """Клавиатура с кнопкой назад в букмекерскую контору"""
    keyboard = Keyboard(inline=True)
    keyboard.add(Text("◀️ Назад в Букмекерскую контору"), color=KeyboardButtonColor.SECONDARY)
    return keyboard


@casino_labeler.message(text=["ставки", "/ставки"])
async def betting_menu_handler(message: Message):
    """Главное меню букмекерской конторы"""
    user_id = message.from_id
    
    # Очищаем предыдущую сессию игрока
    if user_id in betting_sessions:
        del betting_sessions[user_id]
    
    player = await get_player(user_id)
    
    menu_text = (
        "🎰 Добро пожаловать в букмекерскую контору 𝐆𝐘𝐌 𝐋𝐄𝐆𝐄𝐍𝐃! 🎰\n\n"
        "🥊 Подвальные соревнования - ставки на спортсменов.\n\n"
        "🏆 Всероссийские соревнования - угадай сколько пожмет атлет.\n\n"
        "⚔️ Ставки на команду - Угадай какая команда выиграет.\n\n"
        f"💰 Ваш баланс: {format_number(player['balance'])}\n\n"
        "Выберите игру 👇"
    )
    
    await message.answer(menu_text, keyboard=get_main_betting_keyboard())


# ======================
# ИГРА 1: ПОДВАЛЬНЫЕ СОРЕВНОВАНИЯ
# ======================

@casino_labeler.message(text="🥊 Подвальные соревнования")
async def basement_game_start(message: Message):
    """Начало игры в подвальные соревнования"""
    user_id = message.from_id
    
    betting_sessions[user_id] = {
        "game": 1,
        "stage": "choose_side"
    }
    
    keyboard = Keyboard(inline=True)
    keyboard.add(Text("🔴 Красный атлет"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🔵 Синий атлет"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("◀️ Назад в Букмекерскую контору"), color=KeyboardButtonColor.SECONDARY)
    
    await message.answer(
        "🥊 **Подвальные соревнования**\n\n"
        "Выберите атлета, на которого ставите:\n"
        "🔴 Красный атлет\n"
        "🔵 Синий атлет\n\n"
        "Кто победит?",
        keyboard=keyboard
    )


@casino_labeler.message(text=["🔴 Красный атлет", "🔵 Синий атлет"])
async def basement_game_choice(message: Message):
    """Выбор стороны в подвальных соревнованиях"""
    user_id = message.from_id
    
    if user_id not in betting_sessions or betting_sessions[user_id].get("game") != 1 or betting_sessions[user_id].get("stage") != "choose_side":
        return "❌ Сессия игры устарела. Начните заново через меню 'Ставки'."
    
    # Сохраняем выбор игрока
    side = "красный" if message.text == "🔴 Красный атлет" else "синий"
    betting_sessions[user_id]["choice"] = side
    betting_sessions[user_id]["stage"] = "enter_bet"
    
    keyboard = get_back_keyboard()
    
    player = await get_player(user_id)
    
    await message.answer(
        f"🥊 Вы выбрали: **{side.upper()} атлета**\n\n"
        f"💰 Ваш баланс: {format_number(player['balance'])}\n\n"
        f"💬 Напишите сумму ставки (например: 100, 1к, 2.5кк)\n"
        f"❌ Минимальная ставка: 10 монет",
        keyboard=keyboard
    )


# ======================
# ИГРА 2: ВСЕРОССИЙСКИЕ СОРЕВНОВАНИЯ
# ======================

@casino_labeler.message(text="🏆 Всероссийские соревнования")
async def russian_game_start(message: Message):
    """Начало всероссийских соревнований"""
    user_id = message.from_id
    
    # Генерируем 3 случайных веса для кнопок
    weights = sorted([random.randint(40, 110) for _ in range(3)])
    
    betting_sessions[user_id] = {
        "game": 2,
        "stage": "choose_weight",
        "weights": weights  # Сохраняем сгенерированные веса для проверки
    }
    
    keyboard = Keyboard(inline=True)
    for weight in weights:
        keyboard.add(Text(f"{weight} кг"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("◀️ Назад в Букмекерскую контору"), color=KeyboardButtonColor.SECONDARY)
    
    weights_text = ", ".join(map(str, weights))
    
    await message.answer(
        "🏆 **Всероссийские соревнования**\n\n"
        "Выберите вес штанги, который, по вашему мнению, поднимет атлет:\n"
        "• Если угадаете - выиграете.\n"
        f"📊 Доступные варианты: {weights_text} кг\n\n"
        "Ваш выбор?",
        keyboard=keyboard
    )


@casino_labeler.message(text=re.compile(r"^(\d+) кг$"))
async def russian_game_weight_choice(message: Message, weight: int):
    """Выбор веса во всероссийских соревнованиях"""
    user_id = message.from_id
    
    if user_id not in betting_sessions or betting_sessions[user_id].get("game") != 2 or betting_sessions[user_id].get("stage") != "choose_weight":
        return "❌ Сессия игры устарела. Начните заново через меню 'Ставки'."
    
    # Проверяем, что выбранный вес был в предложенных
    if weight not in betting_sessions[user_id]["weights"]:
        return "❌ Выберите вес из предложенных вариантов!"
    
    betting_sessions[user_id]["choice"] = weight
    betting_sessions[user_id]["stage"] = "enter_bet"
    
    keyboard = get_back_keyboard()
    player = await get_player(user_id)
    
    await message.answer(
        f"🏆 Вы выбрали вес: **{weight} кг**\n\n"
        f"💰 Ваш баланс: {format_number(player['balance'])}\n\n"
        f"💬 Напишите сумму ставки (например: 100, 1к, 2.5кк)\n"
        f"❌ Минимальная ставка: 10 монет",
        keyboard=keyboard
    )


# ======================
# ИГРА 3: СТАВКИ НА КОМАНДУ
# ======================

@casino_labeler.message(text="⚔️ Ставки на команду")
async def double_game_start(message: Message):
    """Начало игры в ставки на команду"""
    user_id = message.from_id
    
    betting_sessions[user_id] = {
        "game": 3,
        "stage": "choose_team"
    }
    
    keyboard = Keyboard(inline=True)
    keyboard.add(Text("⚔️ Команда 2 (x2)"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("⚔️ Команда 3 (x3)"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("⚔️ Команда 5 (x3)"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("◀️ Назад в Букмекерскую контору"), color=KeyboardButtonColor.SECONDARY)
    
    await message.answer(
        "⚔️ **Ставки на команду**\n\n"
        "Выберите команду для ставки:\n"
        "• Команда 2 - при выигрыше x2\n"
        "• Команда 3 - при выигрыше x3\n"
        "• Команда 5 - при выигрыше x3\n\n"
        "Угадай какая команда выиграет!",
        keyboard=keyboard
    )


@casino_labeler.message(text=["⚔️ Команда 2 (x2)", "⚔️ Команда 3 (x3)", "⚔️ Команда 5 (x3)"])
async def double_game_team_choice(message: Message):
    """Выбор команды в ставках на команду"""
    user_id = message.from_id
    
    if user_id not in betting_sessions or betting_sessions[user_id].get("game") != 3 or betting_sessions[user_id].get("stage") != "choose_team":
        return "❌ Сессия игры устарела. Начните заново через меню 'Ставки'."
    
    # Определяем выбранную команду и множитель
    if message.text == "⚔️ Команда 2 (x2)":
        team = 2
        multiplier = 2
    elif message.text == "⚔️ Команда 3 (x3)":
        team = 3
        multiplier = 3
    else:  # Команда 5 (x3)
        team = 5
        multiplier = 3
    
    betting_sessions[user_id]["choice"] = team
    betting_sessions[user_id]["multiplier"] = multiplier
    betting_sessions[user_id]["stage"] = "enter_bet"
    
    keyboard = get_back_keyboard()
    player = await get_player(user_id)
    
    await message.answer(
        f"⚔️ Вы выбрали: **Команду {team} (x{multiplier})**\n\n"
        f"💰 Ваш баланс: {format_number(player['balance'])}\n\n"
        f"💬 Напишите сумму ставки (например: 100, 1к, 2.5кк)\n"
        f"❌ Минимальная ставка: 10 монет",
        keyboard=keyboard
    )


# ======================
# ОБРАБОТКА СТАВОК (ОБЩИЙ МЕТОД)
# ======================

@casino_labeler.message(text=re.compile(r"^(\d+|\d+\.?\d*[кК]|\d+[кК][кК]?)$"))
async def betting_bet_handler(message: Message):
    """Обработка ввода суммы ставки для всех игр (просто число)"""
    user_id = message.from_id
    
    if user_id not in betting_sessions or betting_sessions[user_id].get("stage") != "enter_bet":
        return
    
    amount_str = message.text
    
    try:
        bet_amount = parse_amount_string(amount_str)
        if bet_amount < 10:
            return "❌ Минимальная ставка - 10 монет!"
    except ValueError as e:
        return f"❌ Ошибка в сумме: {str(e)}"
    
    player = await get_player(user_id)
    
    if player["balance"] < bet_amount:
        return f"❌ Недостаточно средств! Ваш баланс: {format_number(player['balance'])}"
    
    # Получаем данные сессии
    session = betting_sessions[user_id]
    game_type = session["game"]
    player_choice = session["choice"]
    
    # Определяем результат игры
    win = False
    result_multiplier = 0
    result_text = ""
    
    if game_type == 1:  # Подвальные соревнования
        # Рандомный победитель
        winner = random.choice(["красный", "синий"])
        win = (player_choice == winner)
        result_multiplier = 2 if win else 0
        
        result_text = f"🥊 Победил **{winner.upper()} атлет**!\n\n"
        
    elif game_type == 2:  # Всероссийские соревнования
        # Рандомный вес, который поднял атлет (в диапазоне предложенных)
        actual_weight = random.choice(session["weights"])
        win = (player_choice == actual_weight)
        result_multiplier = 2 if win else 0
        
        result_text = f"🏆 Атлет поднял **{actual_weight} кг**!\n\n"
        
    elif game_type == 3:  # Ставки на команду
        # Возможные выигрышные команды: 1, 2, 3, 4, 5
        winning_team = random.randint(1, 5)
        
        # Проверяем выигрыш в зависимости от выбранной команды
        if player_choice == 2:
            # Команда 2 выигрывает если выпала 2
            win = (winning_team == 2)
            result_multiplier = session.get("multiplier", 2) if win else 0
        elif player_choice == 3:
            # Команда 3 выигрывает если выпала 3
            win = (winning_team == 3)
            result_multiplier = session.get("multiplier", 3) if win else 0
        elif player_choice == 5:
            # Команда 5 выигрывает если выпала 5
            win = (winning_team == 5)
            result_multiplier = session.get("multiplier", 3) if win else 0
        
        result_text = f"⚔️ Выигрышная команда: **{winning_team}**\n\n"
    
    # Расчет выигрыша/проигрыша
    if win:
        winnings = bet_amount * result_multiplier
        
        await update_player_balance(
            user_id,
            winnings,
            "betting_win",
            f"Выигрыш в букмекерской конторе (игра {game_type}) x{result_multiplier}",
            None,
            None
        )
        
        final_text = (
            f"{result_text}"
            f"🎉 **ВЫ ВЫИГРАЛИ!** 🎉\n\n"
            f"💰 Ставка: {format_number(bet_amount)}\n"
            f"💎 Множитель: x{result_multiplier}\n"
            f"💵 Выигрыш: {format_number(winnings)}\n\n"
            f"💳 Новый баланс: {format_number(player['balance'] + winnings)}"
        )
    else:
        await update_player_balance(
            user_id,
            -bet_amount,
            "betting_loss",
            f"Проигрыш в букмекерской конторе (игра {game_type})",
            None,
            None
        )
        
        final_text = (
            f"{result_text}"
            f"😢 **ВЫ ПРОИГРАЛИ** 😢\n\n"
            f"💰 Ставка: {format_number(bet_amount)}\n"
            f"📉 Потеряно: -{format_number(bet_amount)}\n\n"
            f"💳 Новый баланс: {format_number(player['balance'] - bet_amount)}"
        )
    
    # Очищаем сессию
    del betting_sessions[user_id]
    
    # Добавляем кнопку возврата в букмекерскую контору
    keyboard = Keyboard(inline=True)
    keyboard.add(Text("🎰 В букмекерскую контору"), color=KeyboardButtonColor.PRIMARY)
    
    await message.answer(final_text, keyboard=keyboard)


@casino_labeler.message(text=["🎰 В букмекерскую контору", "◀️ Назад в Букмекерскую контору"])
async def back_to_betting_handler(message: Message):
    """Возврат в главное меню букмекерской конторы"""
    await betting_menu_handler(message)


@casino_labeler.message(text="◀️ Назад")
async def back_handler(message: Message):
    """Обработка кнопки Назад (возврат в главное меню)"""
    await betting_menu_handler(message)
