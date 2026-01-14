from flask import Flask, request, jsonify
import os

# Создаем Flask приложение (ВАЖНО!)
app = Flask(__name__)

# Главная страница
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎮 VK Game Bot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                padding: 30px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
                max-width: 600px;
                margin: 0 auto;
            }
            h1 { font-size: 2.5em; margin-bottom: 20px; }
            .status {
                color: #4CAF50;
                font-weight: bold;
                font-size: 1.5em;
                margin: 20px 0;
            }
            .url-box {
                width: 100%;
                padding: 15px;
                margin: 20px 0;
                font-size: 16px;
                border: none;
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.9);
            }
            .btn {
                background: #4CAF50;
                color: white;
                padding: 15px 30px;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                cursor: pointer;
                margin-top: 20px;
                text-decoration: none;
                display: inline-block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎮 VK Game Bot</h1>
            <p class="status">✅ БОТ УСПЕШНО ЗАПУЩЕН</p>
            <p>Скопируйте этот URL в настройках Callback API ВКонтакте:</p>
            <input class="url-box" type="text" 
                   value="https://vk-game-bot.vercel.app/api/callback" 
                   readonly id="url">
            <button class="btn" onclick="copyUrl()">📋 Копировать URL</button>
            <p style="margin-top: 30px;">
                <a href="https://vk.com/dev/bots" style="color: #FFD700; text-decoration: none;">
                    📖 Инструкция по настройке ВК
                </a>
            </p>
        </div>
        
        <script>
            function copyUrl() {
                const url = document.getElementById('url');
                url.select();
                document.execCommand('copy');
                alert('URL скопирован!');
            }
        </script>
    </body>
    </html>
    """

# Эндпоинт для Callback API ВК
@app.route('/api/callback', methods=['POST'])
def callback():
    try:
        data = request.json
        
        # Проверка от ВК
        if data.get('type') == 'confirmation':
            # Возвращаем строку подтверждения
            # Получите её в настройках Callback API ВК
            return os.environ.get('CONFIRMATION_CODE', '123456')
        
        # Обработка сообщений
        elif data.get('type') == 'message_new':
            message = data['object']['message']
            user_id = message['from_id']
            text = message['text'].lower()
            
            # Простая игровая логика
            response = "🎮 Добро пожаловать в игру!\n\n"
            response += "Доступные команды:\n"
            response += "• играть - начать игру\n"
            response += "• баланс - проверить баланс\n"
            response += "• бонус - получить бонус"
            
            if "играть" in text:
                import random
                win = random.choice([True, False])
                if win:
                    response = "🎉 Поздравляем! Вы выиграли 100 монет!"
                else:
                    response = "😢 К сожалению, вы проиграли. Попробуйте ещё раз!"
            
            elif "баланс" in text:
                response = "💰 Ваш баланс: 500 монет"
            
            elif "бонус" in text:
                response = "🎁 Вы получили ежедневный бонус: 50 монет!"
            
            # Возвращаем ответ ВК
            return jsonify({
                'response': response
            })
        
        return 'ok'
    
    except Exception as e:
        print(f"Error: {e}")
        return 'ok'

# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True)
