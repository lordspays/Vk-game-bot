#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gym Legend - Игровой бот для ВК
Запуск на PythonAnywhere
"""

import json
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import sqlite3
import re

app = Flask(__name__)

# ==============================
# КОНСТАНТЫ ГАНТЕЛЕЙ
# ==============================

DUMBBELL_LEVELS = {
    1: {"name": "Гантеля 1кг", "price": 0, "weight": "1кг", "income_per_use": 1},
    2: {"name": "Гантеля 2кг", "price": 5, "weight": "2кг", "income_per_use": 2},
    3: {"name": "Гантеля 3кг", "price": 10, "weight": "3кг", "income_per_use": 3},
    4: {"name": "Гантеля 4кг", "price": 10, "weight": "4кг", "income_per_use": 4},
    5: {"name": "Гантеля 5кг", "price": 10, "weight": "5кг", "income_per_use": 5},
    6: {"name": "Гантеля 6кг", "price": 10, "weight": "6кг", "income_per_use": 6},
    7: {"name": "Гантеля 7кг", "price": 10, "weight": "7кг", "income_per_use": 7},
    8: {"name": "Гантеля 8кг", "price": 10, "weight": "8кг", "income_per_use": 8},
    9: {"name": "Гантеля 9кг", "price": 10, "weight": "9кг", "income_per_use": 9},
    10: {"name": "Гантеля 10кг", "price": 10, "weight": "10кг", "income_per_use": 10},
    11: {"name": "Гантеля 11кг", "price": 10, "weight": "11кг", "income_per_use": 11},
    12: {"name": "Гантеля 12.5кг", "price": 50, "weight": "12.5кг", "income_per_use": 15},
    13: {"name": "Гантеля 15кг", "price": 65, "weight": "15кг", "income_per_use": 20},
    14: {"name": "Гантеля 17.5кг", "price": 80, "weight": "17.5кг", "income_per_use": 25}
}

# ==============================
# АДМИН КОНСТАНТЫ
# ==============================

ADMIN_USERS = [1]  # ID администраторов по умолчанию
PENDING_DELETIONS = {}  # Ожидающие подтверждения удаления

# ==============================
# БАЗА ДАННЫХ И ХРАНИЛИЩЕ
# ==============================

class GameDatabase:
    def __init__(self):
        self.conn = sqlite3.connect('/home/LordSpays/gym_legend.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        # Таблица игроков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 1,
                last_dumbbell_use TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_new INTEGER DEFAULT 1,
                dumbbell_level INTEGER DEFAULT 1,
                dumbbell_name TEXT DEFAULT 'Гантеля 1кг',
                total_lifts INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0,
                custom_income INTEGER DEFAULT NULL,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                ban_until TIMESTAMP DEFAULT NULL
            )
        ''')
        
        # Таблица транзакций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount INTEGER,
                description TEXT,
                admin_id INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица использования гантелей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dumbbell_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                dumbbell_level INTEGER,
                income INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players (user_id)
            )
        ''')
        
        # Таблица административных действий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action_type TEXT,
                target_user_id INTEGER,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def get_player(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, username, balance, last_dumbbell_use, is_new,
                   dumbbell_level, dumbbell_name, total_lifts, total_earned,
                   custom_income, is_admin, is_banned, ban_reason, ban_until,
                   created_at
            FROM players WHERE user_id = ?
        ''', (user_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                'user_id': row[0],
                'username': row[1],
                'balance': row[2],
                'last_dumbbell_use': row[3],
                'is_new': row[4],
                'dumbbell_level': row[5],
                'dumbbell_name': row[6],
                'total_lifts': row[7],
                'total_earned': row[8],
                'custom_income': row[9],
                'is_admin': row[10],
                'is_banned': row[11],
                'ban_reason': row[12],
                'ban_until': row[13],
                'created_at': row[14]
            }
        return None
    
    def create_player(self, user_id, username):
        cursor = self.conn.cursor()
        cursor.execute(
            '''INSERT OR IGNORE INTO players 
               (user_id, username, dumbbell_level, dumbbell_name) 
               VALUES (?, ?, 1, 'Гантеля 1кг')''',
            (user_id, username)
        )
        self.conn.commit()
        return self.get_player(user_id)
    
    def update_username(self, user_id, new_username):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE players SET username = ? WHERE user_id = ?',
            (new_username, user_id)
        )
        self.conn.commit()
        return True
    
    def update_player_balance(self, user_id, amount, transaction_type, description, admin_id=None):
        cursor = self.conn.cursor()
        
        # Обновляем баланс
        cursor.execute(
            'UPDATE players SET balance = balance + ? WHERE user_id = ?',
            (amount, user_id)
        )
        
        # Добавляем транзакцию
        cursor.execute(
            'INSERT INTO transactions (user_id, type, amount, description, admin_id) VALUES (?, ?, ?, ?, ?)',
            (user_id, transaction_type, amount, description, admin_id)
        )
        
        # Если это доход, обновляем total_earned
        if amount > 0:
            cursor.execute(
                'UPDATE players SET total_earned = total_earned + ? WHERE user_id = ?',
                (amount, user_id)
            )
        
        self.conn.commit()
        return True
    
    def set_player_balance(self, user_id, new_balance, admin_id):
        cursor = self.conn.cursor()
        old_balance = self.get_player(user_id)['balance']
        difference = new_balance - old_balance
        
        cursor.execute(
            'UPDATE players SET balance = ? WHERE user_id = ?',
            (new_balance, user_id)
        )
        
        # Логируем действие
        cursor.execute(
            'INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) VALUES (?, ?, ?, ?)',
            (admin_id, 'set_balance', user_id, f'Изменение баланса: {old_balance} -> {new_balance}')
        )
        
        self.conn.commit()
        return True
    
    def update_dumbbell_level(self, user_id, new_level, dumbbell_name):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE players SET dumbbell_level = ?, dumbbell_name = ? WHERE user_id = ?',
            (new_level, dumbbell_name, user_id)
        )
        self.conn.commit()
        return True
    
    def set_dumbbell_level(self, user_id, new_level, admin_id):
        cursor = self.conn.cursor()
        
        if new_level in DUMBBELL_LEVELS:
            dumbbell_info = DUMBBELL_LEVELS[new_level]
            cursor.execute(
                'UPDATE players SET dumbbell_level = ?, dumbbell_name = ? WHERE user_id = ?',
                (new_level, dumbbell_info['name'], user_id)
            )
            
            # Логируем действие
            cursor.execute(
                'INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) VALUES (?, ?, ?, ?)',
                (admin_id, 'set_dumbbell_level', user_id, f'Установлен уровень гантели: {new_level}')
            )
            
            self.conn.commit()
            return True
        return False
    
    def update_dumbbell_use_time(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE players SET last_dumbbell_use = ? WHERE user_id = ?',
            (datetime.now().isoformat(), user_id)
        )
        self.conn.commit()
        return True
    
    def increment_total_lifts(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE players SET total_lifts = total_lifts + 1 WHERE user_id = ?',
            (user_id,)
        )
        self.conn.commit()
        return True
    
    def set_total_lifts(self, user_id, new_total, admin_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE players SET total_lifts = ? WHERE user_id = ?',
            (new_total, user_id)
        )
        
        # Логируем действие
        cursor.execute(
            'INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) VALUES (?, ?, ?, ?)',
            (admin_id, 'set_total_lifts', user_id, f'Установлено поднятий: {new_total}')
        )
        
        self.conn.commit()
        return True
    
    def set_custom_income(self, user_id, custom_income, admin_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE players SET custom_income = ? WHERE user_id = ?',
            (custom_income, user_id)
        )
        
        # Логируем действие
        cursor.execute(
            'INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) VALUES (?, ?, ?, ?)',
            (admin_id, 'set_custom_income', user_id, f'Установлен кастомный доход: {custom_income}')
        )
        
        self.conn.commit()
        return True
    
    def make_admin(self, user_id, admin_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE players SET is_admin = 1 WHERE user_id = ?',
            (user_id,)
        )
        
        # Логируем действие
        cursor.execute(
            'INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) VALUES (?, ?, ?, ?)',
            (admin_id, 'make_admin', user_id, 'Назначение администратора')
        )
        
        self.conn.commit()
        return True
    
    def ban_player(self, user_id, days, reason, admin_id):
        cursor = self.conn.cursor()
        
        if days == 0:  # Перманентный бан
            ban_until = None
            ban_type = 'permanent'
        else:
            ban_until = (datetime.now() + timedelta(days=days)).isoformat()
            ban_type = f'temporary_{days}_days'
        
        cursor.execute(
            'UPDATE players SET is_banned = 1, ban_reason = ?, ban_until = ? WHERE user_id = ?',
            (reason, ban_until, user_id)
        )
        
        # Логируем действие
        cursor.execute(
            'INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) VALUES (?, ?, ?, ?)',
            (admin_id, 'ban', user_id, f'Бан: {ban_type}, причина: {reason}')
        )
        
        self.conn.commit()
        return True
    
    def unban_player(self, user_id, admin_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE players SET is_banned = 0, ban_reason = NULL, ban_until = NULL WHERE user_id = ?',
            (user_id,)
        )
        
        # Логируем действие
        cursor.execute(
            'INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) VALUES (?, ?, ?, ?)',
            (admin_id, 'unban', user_id, 'Разбан игрока')
        )
        
        self.conn.commit()
        return True
    
    def delete_player(self, user_id, admin_id):
        cursor = self.conn.cursor()
        
        # Сохраняем данные для логов
        player_data = self.get_player(user_id)
        
        # Удаляем связанные записи
        cursor.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM dumbbell_uses WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM players WHERE user_id = ?', (user_id,))
        
        # Логируем действие
        cursor.execute(
            'INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) VALUES (?, ?, ?, ?)',
            (admin_id, 'delete_player', user_id, f'Удален игрок: {player_data["username"]}')
        )
        
        self.conn.commit()
        return True
    
    def find_player_by_username(self, username):
        cursor = self.conn.cursor()
        cursor.execute('SELECT user_id FROM players WHERE username LIKE ?', (f'%{username}%',))
        rows = cursor.fetchall()
        
        if rows:
            return [row[0] for row in rows]
        return []
    
    def log_dumbbell_use(self, user_id, dumbbell_level, income):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO dumbbell_uses (user_id, dumbbell_level, income) VALUES (?, ?, ?)',
            (user_id, dumbbell_level, income)
        )
        self.conn.commit()
        return True
    
    def get_top_balance(self, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT username, balance, dumbbell_name 
            FROM players 
            WHERE is_banned = 0
            ORDER BY balance DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def get_top_lifts(self, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT username, total_lifts, dumbbell_name 
            FROM players 
            WHERE is_banned = 0
            ORDER BY total_lifts DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def get_top_earners(self, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT username, dumbbell_name, dumbbell_level, total_earned
            FROM players 
            WHERE is_banned = 0
            ORDER BY total_earned DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

# ==============================
# ИГРОВАЯ ЛОГИКА
# ==============================

class GymLegendBot:
    def __init__(self):
        self.db = GameDatabase()
        self.starting_balance = 1
        self.dumbbell_levels = DUMBBELL_LEVELS
        self.dumbbell_cooldown = 60  # 1 минута в секундах
        self.admin_users = ADMIN_USERS
        self.pending_deletions = PENDING_DELETIONS
    
    def is_admin(self, user_id):
        """Проверка, является ли пользователь администратором"""
        if user_id in self.admin_users:
            return True
        
        player = self.db.get_player(user_id)
        return player and player.get('is_admin', 0) == 1
    
    def handle_command(self, user_id, username, command):
        """Обработка команд от пользователя"""
        
        # Проверяем бан
        player = self.db.get_player(user_id)
        if player and player.get('is_banned', 0) == 1:
            ban_reason = player.get('ban_reason', 'Не указана')
            ban_until = player.get('ban_until')
            
            if ban_until:
                try:
                    ban_until_date = datetime.fromisoformat(ban_until)
                    if datetime.now() > ban_until_date:
                        # Автоматический разбан если срок истек
                        self.db.unban_player(user_id, 0)
                    else:
                        days_left = (ban_until_date - datetime.now()).days
                        return jsonify({
                            'success': False,
                            'message': f'🚫 Вы заблокированы!\n📝 Причина: {ban_reason}\n⏳ Срок: {days_left} дней\n📅 До: {ban_until_date.strftime("%d.%m.%Y")}'
                        })
                except:
                    pass
            else:
                # Перманентный бан
                return jsonify({
                    'success': False,
                    'message': f'🚫 Вы заблокированы навсегда!\n📝 Причина: {ban_reason}'
                })
        
        if not player:
            player = self.db.create_player(user_id, username)
        
        command = command.lower().strip()
        
        # Разделяем команду и аргументы
        parts = command.split()
        cmd = parts[0] if parts else ""
        cmd_args = parts[1:] if len(parts) > 1 else []
        
        # Обработка обычных команд
        if cmd in ['начать', '/начать']:
            return self.welcome_message(user_id, username)
        
        elif cmd in ['профиль', '/профиль']:
            return self.get_profile(user_id)
        
        elif cmd in ['баланс', '/баланс']:
            return self.get_balance(user_id)
        
        elif cmd in ['помощь', '/помощь']:
            return self.get_help()
        
        elif cmd in ['гантеля', '/гантеля']:
            return self.get_dumbbell_info(user_id)
        
        elif cmd in ['поднять', '/поднять']:
            return self.use_dumbbell(user_id)
        
        elif cmd in ['прокачаться', '/прокачаться']:
            return self.upgrade_dumbbell(user_id)
        
        elif cmd in ['магазин', '/магазин']:
            return self.get_dumbbell_shop(user_id)
        
        elif cmd in ['топ', '/топ']:
            return self.get_top_list(user_id)
        
        elif cmd in ['топ', 'монет', '/топ', 'монет'] or command == '/топ монет':
            return self.get_top_balance()
        
        elif cmd in ['топ', 'поднятий', '/топ', 'поднятий'] or command == '/топ поднятий':
            return self.get_top_lifts()
        
        elif cmd in ['топ', 'заработка', '/топ', 'заработка'] or command == '/топ заработка':
            return self.get_top_earners()
        
        elif cmd in ['гник', '/гник']:
            return self.change_username(user_id, ' '.join(cmd_args) if cmd_args else None)
        
        # Админ команды
        elif self.is_admin(user_id):
            if cmd in ['назначить', '/назначить']:
                return self.make_admin_command(user_id, ' '.join(cmd_args) if cmd_args else None)
            
            elif cmd in ['лгантеля', '/лгантеля']:
                return self.set_dumbbell_command(user_id, ' '.join(cmd_args) if cmd_args else None)
            
            elif cmd in ['-баланс', '/-баланс']:
                return self.remove_balance_command(user_id, ' '.join(cmd_args) if cmd_args else None)
            
            elif cmd in ['+баланс', '/+баланс']:
                return self.add_balance_command(user_id, ' '.join(cmd_args) if cmd_args else None)
            
            elif cmd in ['бан', '/бан']:
                return self.ban_command(user_id, ' '.join(cmd_args) if cmd_args else None)
            
            elif cmd in ['пермбан', '/пермбан']:
                return self.permaban_command(user_id, ' '.join(cmd_args) if cmd_args else None)
            
            elif cmd in ['разбан', '/разбан']:
                return self.unban_command(user_id, ' '.join(cmd_args) if cmd_args else None)
            
            elif cmd in ['удалить', '/удалить']:
                return self.delete_player_command(user_id, ' '.join(cmd_args) if cmd_args else None)
            
            elif cmd == '/удалить+':
                return self.confirm_delete_command(user_id)
            
            elif cmd == '/удалить-':
                return self.cancel_delete_command(user_id)
            
            elif cmd in ['сгник', '/сгник']:
                return self.change_player_username_command(user_id, ' '.join(cmd_args) if cmd_args else None)
            
            elif cmd in ['поднятия', '/поднятия']:
                return self.set_lifts_command(user_id, ' '.join(cmd_args) if cmd_args else None)
            
            elif cmd in ['заработок', '/заработок']:
                return self.set_custom_income_command(user_id, ' '.join(cmd_args) if cmd_args else None)
            
            elif cmd in ['связь', '/связь']:
                return self.send_message_command(user_id, ' '.join(cmd_args) if cmd_args else None)
            
            elif cmd in ['админ', '/админ']:
                return self.admin_help()
        
        else:
            return jsonify({
                'success': False,
                'message': '❌ Неизвестная команда. Напишите /помощь для списка команд.'
            })
    
    # ======================
    # ОБЫЧНЫЕ КОМАНДЫ
    # ======================
    
    def welcome_message(self, user_id, username):
        """Приветственное сообщение"""
        player = self.db.get_player(user_id)
        
        welcome_text = (
            "🔥 <b>Привет! Ты попал в Gym Legend</b> 😩🤟\n\n"
            "💪 Здесь ты можешь стать легендой фитнес-индустрии!\n"
            f"👤 Твой ник: <b>{username}</b>\n"
            f"💰 Стартовый баланс: <b>{player['balance']} монет</b>\n"
            f"🏋️‍♂️ Стартовая гантеля: <b>{player['dumbbell_name']}</b>\n\n"
            "🏋️‍♂️ <b>Как играть:</b>\n"
            "1. Качайся с гантелями (/поднять)\n"
            "2. Прокачивай гантели (/прокачаться)\n"
            "3. Соревнуйся с другими (/топ)\n\n"
            "📝 Напиши команду <b>/помощь</b>, чтобы узнать все команды"
        )
        
        return jsonify({
            'success': True,
            'type': 'welcome',
            'message': welcome_text
        })
    
    def change_username(self, user_id, new_username):
        """Смена ника игрока"""
        if not new_username:
            return jsonify({
                'success': False,
                'message': '❌ Укажите новый ник!\n📝 Использование: /гник [новый_ник]'
            })
        
        if len(new_username) > 20:
            return jsonify({
                'success': False,
                'message': '❌ Ник не может быть длиннее 20 символов!'
            })
        
        if len(new_username) < 3:
            return jsonify({
                'success': False,
                'message': '❌ Ник должен быть не короче 3 символов!'
            })
        
        self.db.update_username(user_id, new_username)
        
        return jsonify({
            'success': True,
            'message': f'✅ Ваш ник изменен на: <b>{new_username}</b>'
        })
    
    def get_dumbbell_info(self, user_id):
        """Информация о гантеле игрока"""
        player = self.db.get_player(user_id)
        
        # Получаем доход (кастомный или стандартный)
        if player.get('custom_income') is not None:
            income_per_use = player['custom_income']
            custom_note = f"⚡ <i>Кастомный доход</i>\n"
        else:
            dumbbell_info = self.dumbbell_levels[player['dumbbell_level']]
            income_per_use = dumbbell_info['income_per_use']
            custom_note = ""
        
        next_level = player['dumbbell_level'] + 1
        
        # Проверяем, есть ли следующий уровень
        if next_level in self.dumbbell_levels:
            next_dumbbell = self.dumbbell_levels[next_level]
            upgrade_info = f"🔜 <b>Следующий уровень:</b> {next_dumbbell['name']}\n💵 Цена: {next_dumbbell['price']} монет\n💰 Доход за подход: {next_dumbbell['income_per_use']} монет"
        else:
            upgrade_info = "🏆 <b>Вы достигли максимального уровня гантели!</b>"
        
        info_text = (
            f"🏋️‍♂️ <b>Ваша гантеля:</b>\n\n"
            f"{custom_note}"
            f"⚖️ Вес: <b>{player['dumbbell_name']}</b>\n"
            f"⭐ Уровень: <b>{player['dumbbell_level']}</b>\n"
            f"💰 Доход за подход: <b>{income_per_use} монет</b>\n\n"
            f"{upgrade_info}"
        )
        
        return jsonify({
            'success': True,
            'type': 'dumbbell_info',
            'message': info_text,
            'dumbbell_level': player['dumbbell_level'],
            'dumbbell_name': player['dumbbell_name']
        })
    
    def use_dumbbell(self, user_id):
        """Использование гантели (подъем)"""
        player = self.db.get_player(user_id)
        
        # Проверяем кулдаун
        last_use = datetime.fromisoformat(player['last_dumbbell_use'])
        now = datetime.now()
        seconds_passed = (now - last_use).total_seconds()
        
        if seconds_passed < self.dumbbell_cooldown:
            seconds_left = int(self.dumbbell_cooldown - seconds_passed)
            return jsonify({
                'success': False,
                'message': f'⏳ Время отдыха! Подождите {seconds_left} секунд'
            })
        
        # Получаем доход (кастомный или стандартный)
        if player.get('custom_income') is not None:
            income = player['custom_income']
        else:
            dumbbell_info = self.dumbbell_levels[player['dumbbell_level']]
            income = dumbbell_info['income_per_use']
        
        # Начисляем доход
        self.db.update_player_balance(
            user_id,
            income,
            'dumbbell_income',
            f'Подъем гантели {player["dumbbell_name"]}'
        )
        
        # Обновляем время использования
        self.db.update_dumbbell_use_time(user_id)
        
        # Увеличиваем счетчик поднятий
        self.db.increment_total_lifts(user_id)
        
        # Логируем использование
        self.db.log_dumbbell_use(user_id, player['dumbbell_level'], income)
        
        return jsonify({
            'success': True,
            'message': f'💪 <b>Вы подняли гантелю {player["dumbbell_name"]}!</b>\n💰 Получено: <b>{income} монет</b>\n📈 Баланс: <b>{player["balance"] + income} монет</b>',
            'income': income,
            'new_balance': player['balance'] + income,
            'dumbbell_name': player['dumbbell_name']
        })
    
    def upgrade_dumbbell(self, user_id):
        """Улучшение гантели"""
        player = self.db.get_player(user_id)
        current_level = player['dumbbell_level']
        next_level = current_level + 1
        
        # Проверяем, есть ли следующий уровень
        if next_level not in self.dumbbell_levels:
            return jsonify({
                'success': False,
                'message': '🏆 Вы уже достигли максимального уровня гантели!'
            })
        
        next_dumbbell = self.dumbbell_levels[next_level]
        
        # Проверяем баланс
        if player['balance'] < next_dumbbell['price']:
            return jsonify({
                'success': False,
                'message': f'❌ Недостаточно монет. Нужно {next_dumbbell["price"]} 💰, у вас {player["balance"]} 💰'
            })
        
        # Списываем деньги
        self.db.update_player_balance(
            user_id,
            -next_dumbbell['price'],
            'dumbbell_upgrade',
            f'Прокачка гантели до уровня {next_level}'
        )
        
        # Обновляем уровень гантели
        self.db.update_dumbbell_level(user_id, next_level, next_dumbbell['name'])
        
        return jsonify({
            'success': True,
            'message': f'🎉 <b>Гантеля прокачана!</b>\n🏋️‍♂️ Новый уровень: <b>{next_dumbbell["name"]}</b>\n💰 Доход за подход: <b>{next_dumbbell["income_per_use"]} монет</b>\n💵 Потрачено: <b>{next_dumbbell["price"]} монет</b>',
            'new_level': next_level,
            'new_dumbbell_name': next_dumbbell['name'],
            'new_balance': player['balance'] - next_dumbbell['price']
        })
    
    def get_dumbbell_shop(self, user_id):
        """Магазин гантелей"""
        player = self.db.get_player(user_id)
        current_level = player['dumbbell_level']
        
        shop_items = []
        for level in range(1, 15):  # Все 14 уровней
            dumbbell = self.dumbbell_levels[level]
            
            if level == current_level:
                prefix = "✅ "
            elif level < current_level:
                prefix = "✔️ "
            else:
                prefix = "🔘 "
            
            if level == current_level:
                suffix = " (Ваш текущий)"
            elif player['balance'] >= dumbbell['price']:
                suffix = " 🔥"
            else:
                suffix = " ⏳"
            
            shop_items.append(
                f"{prefix}<b>Уровень {level}:</b> {dumbbell['name']}\n"
                f"   ⚖️ Вес: {dumbbell['weight']} | "
                f"💰 Доход: {dumbbell['income_per_use']} монет | "
                f"💵 Цена: {dumbbell['price']} монет{suffix}"
            )
        
        shop_text = (
            "🏪 <b>Магазин гантелей</b>\n\n"
            "💪 <b>Как прокачаться:</b>\n"
            "1. Накапливайте монеты (/поднять)\n"
            "2. Купите улучшение (/прокачаться)\n"
            "3. Получайте больше дохода!\n\n"
            "📊 <b>Доступные гантели:</b>\n" +
            "\n".join(shop_items) +
            f"\n\n💰 <b>Ваш баланс:</b> {player['balance']} монет\n"
            f"🏋️‍♂️ <b>Текущая гантеля:</b> {player['dumbbell_name']}"
        )
        
        return jsonify({
            'success': True,
            'type': 'dumbbell_shop',
            'message': shop_text
        })
    
    def get_profile(self, user_id):
        """Профиль игрока с датой регистрации и количеством поднятий"""
        player = self.db.get_player(user_id)
        if not player:
            return jsonify({'success': False, 'message': 'Игрок не найден'})
        
        # Получаем доход (кастомный или стандартный)
        if player.get('custom_income') is not None:
            income_per_use = player['custom_income']
            income_note = f"💰 Доход за подход: <b>{income_per_use} монет</b> ⚡\n"
        else:
            dumbbell_info = self.dumbbell_levels[player['dumbbell_level']]
            income_per_use = dumbbell_info['income_per_use']
            income_note = f"💰 Доход за подход: <b>{income_per_use} монет</b>\n"
        
        # Форматируем дату регистрации
        created_date = datetime.fromisoformat(player['created_at']).strftime("%d.%m.%Y")
        
        profile_text = (
            f"👤 <b>Профиль игрока #{player['user_id']}</b>\n\n"
            f"💪 Ник: <b>{player['username']}</b>\n"
            f"💰 Баланс: <b>{player['balance']} монет</b>\n"
            f"🏋️‍♂️ Гантеля: <b>{player['dumbbell_name']}</b>\n"
            f"⭐ Уровень гантели: <b>{player['dumbbell_level']}</b>\n"
            f"{income_note}"
            f"💪 Поднятий гантели: <b>{player['total_lifts']}</b>\n"
            f"📅 Дата регистрации: <b>{created_date}</b>"
        )
        
        return jsonify({
            'success': True,
            'type': 'profile',
            'message': profile_text,
            'data': {
                'username': player['username'],
                'user_id': player['user_id'],
                'balance': player['balance'],
                'dumbbell_level': player['dumbbell_level'],
                'dumbbell_name': player['dumbbell_name'],
                'dumbbell_income': income_per_use,
                'total_lifts': player['total_lifts'],
                'created_at': created_date
            }
        })
    
    def get_balance(self, user_id):
        player = self.db.get_player(user_id)
        return jsonify({
            'success': True,
            'message': f'💰 <b>Ваш баланс:</b> {player["balance"]} монет',
            'balance': player['balance']
        })
    
    def get_top_balance(self):
        """Топ по балансу"""
        top_players = self.db.get_top_balance(10)
        
        if not top_players:
            return jsonify({
                'success': True,
                'message': '🏆 Топ пока пуст. Будьте первым!'
            })
        
        top_text = "🏆 <b>ТОП по монетам:</b>\n\n"
        
        for i, (username, balance, dumbbell_name) in enumerate(top_players, 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
            top_text += f"{medal} <b>{i}.</b> {username}\n"
            top_text += f"   💰 {balance} монет | 🏋️‍♂️ {dumbbell_name}\n\n"
        
        return jsonify({
            'success': True,
            'type': 'top_balance',
            'message': top_text
        })
    
    def get_top_lifts(self):
        """Топ по количеству поднятий"""
        top_players = self.db.get_top_lifts(10)
        
        if not top_players:
            return jsonify({
                'success': True,
                'message': '🏆 Топ пока пуст. Будьте первым!'
            })
        
        top_text = "💪 <b>ТОП по поднятиям:</b>\n\n"
        
        for i, (username, total_lifts, dumbbell_name) in enumerate(top_players, 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
            top_text += f"{medal} <b>{i}.</b> {username}\n"
            top_text += f"   💪 {total_lifts} поднятий | 🏋️‍♂️ {dumbbell_name}\n\n"
        
        return jsonify({
            'success': True,
            'type': 'top_lifts',
            'message': top_text
        })
    
    def get_top_earners(self):
        """Топ по заработку (доход от гантели)"""
        top_players = self.db.get_top_earners(10)
        
        if not top_players:
            return jsonify({
                'success': True,
                'message': '🏆 Топ пока пуст. Будьте первым!'
            })
        
        top_text = "💰 <b>ТОП по заработку:</b>\n\n"
        
        for i, (username, dumbbell_name, dumbbell_level, total_earned) in enumerate(top_players, 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
            # Получаем доход за подход для этой гантели
            dumbbell_info = self.dumbbell_levels.get(dumbbell_level, {"income_per_use": 1})
            income_per_lift = dumbbell_info['income_per_use']
            
            top_text += f"{medal} <b>{i}.</b> {username}\n"
            top_text += f"   💰 {total_earned} монет | 🏋️‍♂️ {dumbbell_name}\n"
            top_text += f"   📈 {income_per_lift} монет/подход\n\n"
        
        return jsonify({
            'success': True,
            'type': 'top_earners',
            'message': top_text
        })
    
    def get_top_list(self, user_id):
        """Общий топ список"""
        player = self.db.get_player(user_id)
        
        top_text = (
            "🏆 <b>Система ТОПа Gym Legend</b>\n\n"
            "📊 <b>Доступные рейтинги:</b>\n\n"
            "💰 <b>/топ монет</b> - топ игроков по балансу\n"
            "💪 <b>/топ поднятий</b> - топ по количеству поднятий\n"
            "📈 <b>/топ заработка</b> - топ по общему заработку\n\n"
            f"💪 <b>Ваши показатели:</b>\n"
            f"💰 Баланс: {player['balance']} монет\n"
            f"💪 Поднятий: {player['total_lifts']}\n"
            f"🏋️‍♂️ Гантеля: {player['dumbbell_name']}\n\n"
            "Выберите нужный топ из списка выше!"
        )
        
        return jsonify({
            'success': True,
            'type': 'top_list',
            'message': top_text
        })
    
    def get_help(self):
        commands = [
            "🏋️‍♂️ <b>Gym Legend - Доступные команды:</b>\n",
            "📊 <b>Профиль и информация:</b>",
            "├── /профиль - ваш профиль",
            "├── /баланс - текущий баланс\n",
            "💪 <b>Гантели:</b>",
            "├── /гантеля - информация о гантеле",
            "├── /поднять - поднять гантелю",
            "├── /прокачаться - улучшить гантелю",
            "└── /магазин - магазин гантелей\n",
            "🏆 <b>Рейтинги:</b>",
            "├── /топ - общий список рейтингов",
            "├── /топ монет - топ по балансу",
            "├── /топ поднятий - топ по поднятиям",
            "└── /топ заработка - топ по заработку\n",
            "💡 <b>Особенности:</b>",
            "• Гантеля 1кг дается при регистрации",
            "• Кулдаун между подходами: 1 минута",
            "• Прокачка увеличивает доход",
            "• Соревнуйтесь с другими игроками!"
        ]
        
        return jsonify({
            'success': True,
            'message': '\n'.join(commands)
        })
    
    # ======================
    # АДМИН КОМАНДЫ
    # ======================
    
    def admin_help(self):
        commands = [
            "🏛️ <b>Административные команды Gym Legend</b>\n",
            "📝 <b>Основные команды:</b>",
            "├── /назначить [ник] - назначить администратора",
            "├── /лгантеля [ник] [уровень] - установить уровень гантели",
            "├── /-баланс [ник] [сумма] - убрать сумму с баланса игрока",
            "├── /+баланс [ник] [сумма] - добавить сумму на баланс игрока",
            "├── /бан [ник] [дни] [причина] - заблокировать игрока",
            "├── /пермбан [ник] [причина] - перманентный бан",
            "├── /разбан [ник] - разблокировать игрока",
            "├── /удалить [ник] [причина] - удалить профиль игрока",
            "├── /удалить+ - подтвердить удаление",
            "├── /удалить- - отменить удаление",
            "├── /сгник [старый_ник] [новый_ник] - сменить ник игроку",
            "├── /поднятия [ник] [количество] - установить поднятия",
            "├── /заработок [ник] [сумма] - установить кастомный доход",
            "└── /связь [ник] [сообщение] - отправить сообщение\n",
            "⚠️ <b>Внимание:</b>",
            "• При удалении нужно указать причину",
            "• Для подтверждения/отмены используйте /удалить+ или /удалить-",
            "• Ник можно указывать частично",
            "• Все действия логируются"
        ]
        
        return jsonify({
            'success': True,
            'message': '\n'.join(commands)
        })
    
    def make_admin_command(self, user_id, args):
        """Назначение администратора"""
        if not args:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник игрока!\n📝 Использование: /назначить [ник]'
            })
        
        target_ids = self.db.find_player_by_username(args)
        
        if not target_ids:
            return jsonify({
                'success': False,
                'message': f'❌ Игрок с ником "{args}" не найден!'
            })
        
        target_id = target_ids[0]
        target_player = self.db.get_player(target_id)
        
        self.db.make_admin(target_id, user_id)
        
        return jsonify({
            'success': True,
            'message': f'✅ Игрок назначен администратором!\n👤 Игрок: <b>{target_player["username"]}</b>\n👮 Назначил: <b>Администратор</b>'
        })
    
    def set_dumbbell_command(self, user_id, args):
        """Установка уровня гантели"""
        if not args:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и уровень!\n📝 Использование: /лгантеля [ник] [уровень]'
            })
        
        parts = args.split()
        if len(parts) < 2:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и уровень!\n📝 Использование: /лгантеля [ник] [уровень]'
            })
        
        username = ' '.join(parts[:-1])
        try:
            level = int(parts[-1])
        except:
            return jsonify({
                'success': False,
                'message': '❌ Уровень должен быть числом от 1 до 14!'
            })
        
        if level < 1 or level > 14:
            return jsonify({
                'success': False,
                'message': '❌ Уровень должен быть от 1 до 14!'
            })
        
        target_ids = self.db.find_player_by_username(username)
        
        if not target_ids:
            return jsonify({
                'success': False,
                'message': f'❌ Игрок с ником "{username}" не найден!'
            })
        
        target_id = target_ids[0]
        target_player = self.db.get_player(target_id)
        
        self.db.set_dumbbell_level(target_id, level, user_id)
        
        dumbbell_info = self.dumbbell_levels[level]
        
        return jsonify({
            'success': True,
            'message': f'✅ Уровень гантели изменен!\n👤 Игрок: <b>{target_player["username"]}</b>\n🏋️‍♂️ Новая гантеля: <b>{dumbbell_info["name"]}</b>\n⭐ Уровень: <b>{level}</b>\n👮 Изменил: <b>Администратор</b>'
        })
    
    def remove_balance_command(self, user_id, args):
        """Списание баланса"""
        if not args:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и сумму!\n📝 Использование: /-баланс [ник] [сумма]'
            })
        
        parts = args.split()
        if len(parts) < 2:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и сумму!\n📝 Использование: /-баланс [ник] [сумма]'
            })
        
        username = ' '.join(parts[:-1])
        try:
            amount = int(parts[-1])
        except:
            return jsonify({
                'success': False,
                'message': '❌ Сумма должна быть числом!'
            })
        
        if amount <= 0:
            return jsonify({
                'success': False,
                'message': '❌ Сумма должна быть положительной!'
            })
        
        target_ids = self.db.find_player_by_username(username)
        
        if not target_ids:
            return jsonify({
                'success': False,
                'message': f'❌ Игрок с ником "{username}" не найден!'
            })
        
        target_id = target_ids[0]
        target_player = self.db.get_player(target_id)
        
        if target_player['balance'] < amount:
            return jsonify({
                'success': False,
                'message': f'❌ У игрока недостаточно монет!\n💰 Баланс игрока: {target_player["balance"]} монет'
            })
        
        new_balance = target_player['balance'] - amount
        self.db.set_player_balance(target_id, new_balance, user_id)
        
        return jsonify({
            'success': True,
            'message': f'✅ Баланс изменен!\n👤 Игрок: <b>{target_player["username"]}</b>\n💰 Списано: <b>{amount} монет</b>\n💵 Новый баланс: <b>{new_balance} монет</b>\n👮 Изменил: <b>Администратор</b>'
        })
    
    def add_balance_command(self, user_id, args):
        """Добавление баланса"""
        if not args:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и сумму!\n📝 Использование: /+баланс [ник] [сумма]'
            })
        
        parts = args.split()
        if len(parts) < 2:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и сумму!\n📝 Использование: /+баланс [ник] [сумма]'
            })
        
        username = ' '.join(parts[:-1])
        try:
            amount = int(parts[-1])
        except:
            return jsonify({
                'success': False,
                'message': '❌ Сумма должна быть числом!'
            })
        
        if amount <= 0:
            return jsonify({
                'success': False,
                'message': '❌ Сумма должна быть положительной!'
            })
        
        target_ids = self.db.find_player_by_username(username)
        
        if not target_ids:
            return jsonify({
                'success': False,
                'message': f'❌ Игрок с ником "{username}" не найден!'
            })
        
        target_id = target_ids[0]
        target_player = self.db.get_player(target_id)
        
        new_balance = target_player['balance'] + amount
        self.db.set_player_balance(target_id, new_balance, user_id)
        
        return jsonify({
            'success': True,
            'message': f'✅ Баланс изменен!\n👤 Игрок: <b>{target_player["username"]}</b>\n💰 Добавлено: <b>{amount} монет</b>\n💵 Новый баланс: <b>{new_balance} монет</b>\n👮 Изменил: <b>Администратор</b>'
        })
    
    def ban_command(self, user_id, args):
        """Блокировка игрока"""
        if not args:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник, дни и причину!\n📝 Использование: /бан [ник] [дни] [причина]'
            })
        
        parts = args.split()
        if len(parts) < 3:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник, дни и причину!\n📝 Использование: /бан [ник] [дни] [причина]'
            })
        
        # Извлекаем дни (предпоследний элемент)
        try:
            days = int(parts[-2])
        except:
            return jsonify({
                'success': False,
                'message': '❌ Дни должны быть числом!'
            })
        
        if days <= 0:
            return jsonify({
                'success': False,
                'message': '❌ Дни должны быть положительным числом!'
            })
        
        username = ' '.join(parts[:-2])
        reason = parts[-1]
        
        target_ids = self.db.find_player_by_username(username)
        
        if not target_ids:
            return jsonify({
                'success': False,
                'message': f'❌ Игрок с ником "{username}" не найден!'
            })
        
        target_id = target_ids[0]
        target_player = self.db.get_player(target_id)
        
        self.db.ban_player(target_id, days, reason, user_id)
        
        ban_until = (datetime.now() + timedelta(days=days)).strftime("%d.%m.%Y")
        
        return jsonify({
            'success': True,
            'message': f'🚫 <b>Игрок заблокирован!</b>\n\n👤 Игрок: <b>{target_player["username"]}</b>\n⏳ Срок: <b>{days} дней</b>\n📝 Причина: <b>{reason}</b>\n👮 Администратор: <b>Админ</b>\n📅 Разблокировка: <b>{ban_until}</b>'
        })
    
    def permaban_command(self, user_id, args):
        """Перманентный бан"""
        if not args:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и причину!\n📝 Использование: /пермбан [ник] [причина]'
            })
        
        parts = args.split()
        if len(parts) < 2:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и причину!\n📝 Использование: /пермбан [ник] [причина]'
            })
        
        username = ' '.join(parts[:-1])
        reason = parts[-1]
        
        target_ids = self.db.find_player_by_username(username)
        
        if not target_ids:
            return jsonify({
                'success': False,
                'message': f'❌ Игрок с ником "{username}" не найден!'
            })
        
        target_id = target_ids[0]
        target_player = self.db.get_player(target_id)
        
        self.db.ban_player(target_id, 0, reason, user_id)
        
        return jsonify({
            'success': True,
            'message': f'🚫 <b>Игрок заблокирован навсегда!</b>\n\n👤 Игрок: <b>{target_player["username"]}</b>\n⏳ Срок: <b>Навсегда</b>\n📝 Причина: <b>{reason}</b>\n👮 Администратор: <b>Админ</b>\n⚠️ <b>Перманентная блокировка</b>'
        })
    
    def unban_command(self, user_id, args):
        """Разблокировка игрока"""
        if not args:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник игрока!\n📝 Использование: /разбан [ник]'
            })
        
        target_ids = self.db.find_player_by_username(args)
        
        if not target_ids:
            return jsonify({
                'success': False,
                'message': f'❌ Игрок с ником "{args}" не найден!'
            })
        
        target_id = target_ids[0]
        target_player = self.db.get_player(target_id)
        
        if not target_player['is_banned']:
            return jsonify({
                'success': False,
                'message': f'❌ Игрок <b>{target_player["username"]}</b> не заблокирован!'
            })
        
        self.db.unban_player(target_id, user_id)
        
        return jsonify({
            'success': True,
            'message': f'✅ <b>Игрок разблокирован!</b>\n\n👤 Игрок: <b>{target_player["username"]}</b>\n👮 Администратор: <b>Админ</b>\n🎉 <b>Теперь игрок может снова играть!</b>'
        })
    
    def delete_player_command(self, user_id, args):
        """Удаление профиля игрока"""
        if not args:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и причину!\n📝 Использование: /удалить [ник] [причина]'
            })
        
        parts = args.split()
        if len(parts) < 2:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и причину!\n📝 Использование: /удалить [ник] [причина]'
            })
        
        username = ' '.join(parts[:-1])
        reason = parts[-1]
        
        target_ids = self.db.find_player_by_username(username)
        
        if not target_ids:
            return jsonify({
                'success': False,
                'message': f'❌ Игрок с ником "{username}" не найден!'
            })
        
        target_id = target_ids[0]
        target_player = self.db.get_player(target_id)
        
        # Сохраняем данные для подтверждения
        self.pending_deletions[user_id] = {
            'target_id': target_id,
            'target_username': target_player['username'],
            'reason': reason,
            'target_balance': target_player['balance'],
            'target_dumbbell': target_player['dumbbell_name'],
            'target_lifts': target_player['total_lifts'],
            'timestamp': time.time()
        }
        
        return jsonify({
            'success': True,
            'message': f'⚠️ <b>Подтверждение удаления</b>\n\nВы собираетесь удалить игрока: <b>{target_player["username"]}</b>\n📝 Причина: <b>{reason}</b>\n\n📊 Статистика игрока:\n💰 Баланс: {target_player["balance"]} монет\n🏋️‍♂️ Гантеля: {target_player["dumbbell_name"]}\n💪 Поднятий: {target_player["total_lifts"]}\n\n<b>Для подтверждения введите:</b>\n<code>/удалить+</code>\n\n<b>Для отмены введите:</b>\n<code>/удалить-</code>\n\n<b>Действие отменится через 60 секунд</b>'
        })
    
    def confirm_delete_command(self, user_id):
        """Подтверждение удаления"""
        if user_id not in self.pending_deletions:
            return jsonify({
                'success': False,
                'message': '❌ Нет ожидающих удалений!'
            })
        
        pending = self.pending_deletions[user_id]
        
        # Проверяем не истекло ли время (60 секунд)
        if time.time() - pending['timestamp'] > 60:
            del self.pending_deletions[user_id]
            return jsonify({
                'success': False,
                'message': '❌ Время подтверждения истекло!'
            })
        
        target_id = pending['target_id']
        reason = pending['reason']
        
        # Удаляем игрока
        self.db.delete_player(target_id, user_id)
        
        # Удаляем из ожидающих
        del self.pending_deletions[user_id]
        
        return jsonify({
            'success': True,
            'message': f'✅ <b>Профиль удален!</b>\n\n👤 Игрок: <b>{pending["target_username"]}</b>\n📝 Причина: <b>{reason}</b>\n👮 Администратор: <b>Админ</b>\n🕒 Время: <b>{datetime.now().strftime("%d.%m.%Y %H:%M")}</b>\n\n⚠️ <b>Все данные игрока были удалены</b>'
        })
    
    def cancel_delete_command(self, user_id):
        """Отмена удаления"""
        if user_id not in self.pending_deletions:
            return jsonify({
                'success': False,
                'message': '❌ Нет ожидающих удалений!'
            })
        
        pending = self.pending_deletions[user_id]
        del self.pending_deletions[user_id]
        
        return jsonify({
            'success': True,
            'message': f'❌ <b>Удаление отменено</b>\n\nПрофиль игрока <b>{pending["target_username"]}</b> не был удален.\nДействие отменено администратором.'
        })
    
    def change_player_username_command(self, user_id, args):
        """Смена ника игроку"""
        if not args:
            return jsonify({
                'success': False,
                'message': '❌ Укажите старый и новый ник!\n📝 Использование: /сгник [старый_ник] [новый_ник]'
            })
        
        parts = args.split()
        if len(parts) < 2:
            return jsonify({
                'success': False,
                'message': '❌ Укажите старый и новый ник!\n📝 Использование: /сгник [старый_ник] [новый_ник]'
            })
        
        # Последнее слово - новый ник, все остальное - старый ник
        new_username = parts[-1]
        old_username = ' '.join(parts[:-1])
        
        if len(new_username) > 20:
            return jsonify({
                'success': False,
                'message': '❌ Новый ник не может быть длиннее 20 символов!'
            })
        
        if len(new_username) < 3:
            return jsonify({
                'success': False,
                'message': '❌ Новый ник должен быть не короче 3 символов!'
            })
        
        target_ids = self.db.find_player_by_username(old_username)
        
        if not target_ids:
            return jsonify({
                'success': False,
                'message': f'❌ Игрок с ником "{old_username}" не найден!'
            })
        
        target_id = target_ids[0]
        target_player = self.db.get_player(target_id)
        
        self.db.update_username(target_id, new_username)
        
        return jsonify({
            'success': True,
            'message': f'✅ Ник игрока изменен!\n👤 Игрок: <b>{target_player["username"]}</b>\n🆕 Новый ник: <b>{new_username}</b>\n👮 Изменил: <b>Администратор</b>'
        })
    
    def set_lifts_command(self, user_id, args):
        """Установка количества поднятий"""
        if not args:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и количество!\n📝 Использование: /поднятия [ник] [количество]'
            })
        
        parts = args.split()
        if len(parts) < 2:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и количество!\n📝 Использование: /поднятия [ник] [количество]'
            })
        
        username = ' '.join(parts[:-1])
        try:
            lifts = int(parts[-1])
        except:
            return jsonify({
                'success': False,
                'message': '❌ Количество должно быть числом!'
            })
        
        if lifts < 0:
            return jsonify({
                'success': False,
                'message': '❌ Количество не может быть отрицательным!'
            })
        
        target_ids = self.db.find_player_by_username(username)
        
        if not target_ids:
            return jsonify({
                'success': False,
                'message': f'❌ Игрок с ником "{username}" не найден!'
            })
        
        target_id = target_ids[0]
        target_player = self.db.get_player(target_id)
        
        self.db.set_total_lifts(target_id, lifts, user_id)
        
        return jsonify({
            'success': True,
            'message': f'✅ Количество поднятий изменено!\n👤 Игрок: <b>{target_player["username"]}</b>\n💪 Новое количество: <b>{lifts}</b>\n👮 Изменил: <b>Администратор</b>'
        })
    
    def set_custom_income_command(self, user_id, args):
        """Установка кастомного дохода"""
        if not args:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и сумму!\n📝 Использование: /заработок [ник] [сумма]'
            })
        
        parts = args.split()
        if len(parts) < 2:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и сумму!\n📝 Использование: /заработок [ник] [сумма]'
            })
        
        username = ' '.join(parts[:-1])
        try:
            income = int(parts[-1])
        except:
            return jsonify({
                'success': False,
                'message': '❌ Сумма должна быть числом!'
            })
        
        if income <= 0:
            return jsonify({
                'success': False,
                'message': '❌ Сумма должна быть положительной!'
            })
        
        target_ids = self.db.find_player_by_username(username)
        
        if not target_ids:
            return jsonify({
                'success': False,
                'message': f'❌ Игрок с ником "{username}" не найден!'
            })
        
        target_id = target_ids[0]
        target_player = self.db.get_player(target_id)
        
        self.db.set_custom_income(target_id, income, user_id)
        
        return jsonify({
            'success': True,
            'message': f'✅ Кастомный доход установлен!\n👤 Игрок: <b>{target_player["username"]}</b>\n💰 Новый доход за подход: <b>{income} монет</b>\n⚡ <i>Теперь игрок будет получать эту сумму при каждом поднятии</i>\n👮 Установил: <b>Администратор</b>'
        })
    
    def send_message_command(self, user_id, args):
        """Отправка сообщения игроку"""
        if not args:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и сообщение!\n📝 Использование: /связь [ник] [сообщение]'
            })
        
        parts = args.split()
        if len(parts) < 2:
            return jsonify({
                'success': False,
                'message': '❌ Укажите ник и сообщение!\n📝 Использование: /связь [ник] [сообщение]'
            })
        
        # Все кроме первого слова - сообщение
        username = parts[0]
        message = ' '.join(parts[1:])
        
        target_ids = self.db.find_player_by_username(username)
        
        if not target_ids:
            return jsonify({
                'success': False,
                'message': f'❌ Игрок с ником "{username}" не найден!'
            })
        
        # В реальном боте здесь была бы отправка в личные сообщения ВК
        # Здесь мы просто имитируем отправку
        
        admin_player = self.db.get_player(user_id) UK
        
        return jsonify({
            'success': True,
            'message': f'📨 <b>Сообщение отправлено!</b>\n\n👤 Игроку: <b>{username}</b>\n📝 Сообщение: <b>{message}</b>\n👮 Отправил: <b>{admin_player["username"]}</b>\n\n💡 <i>В реальном боте сообщение было бы отправлено в личные сообщения ВК</i>'
        })

# ==============================
# СОЗДАНИЕ И НАСТРОЙКА БОТА
# ==============================

bot = GymLegendBot()

# ==============================
# FLASK РОУТЫ
# ==============================

@app.route('/')
def index():
    return "Gym Legend Bot is running! 🏋️‍♂️"

@app.route('/api/command', methods=['GET', 'POST'])
def handle_command():
    if request.method == 'GET':
        user_id = request.args.get('user_id', default=1, type=int)
        username = request.args.get('username', default='Игрок', type=str)
        command = request.args.get('command', default='', type=str)
    else:
        data = request.get_json()
        user_id = data.get('user_id', 1)
        username = data.get('username', 'Игрок')
        command = data.get('command', '')
    
    if not command:
        return jsonify({'success': False, 'message': 'Команда не указана'})
    
    return bot.handle_command(user_id, username, command)

@app.route('/api/profile', methods=['GET'])
def get_profile():
    user_id = request.args.get('user_id', default=1, type=int)
    return bot.get_profile(user_id)

# Для Callback API ВК
@app.route('/api/callback', methods=['POST'])
def vk_callback():
    data = request.get_json()
    
    # Обработка событий от ВК
    if data.get('type') == 'confirmation':
        # Возвращаем строку подтверждения
        return 'ваша_строка_подтверждения'
    
    elif data.get('type') == 'message_new':
        # Обработка нового сообщения
        message = data.get('object', {}).get('message', {})
        user_id = message.get('from_id')
        text = message.get('text', '')
        
        # Получаем информацию о пользователе
        # В реальном боте здесь был бы запрос к API ВК
        username = f"Игрок_{user_id}"
        
        # Обрабатываем команду
        result = bot.handle_command(user_id, username, text)
        
        # В реальном боте здесь была бы отправка ответа через API ВК
        return 'ok'
    
    return 'ok'

# ==============================
# ЗАПУСК СЕРВЕРА
# ==============================

if __name__ == '__main__':
    # На PythonAnywhere это не запускается, управляется через WSGI
    print("Gym Legend Bot initialized!")
