from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎮 VK Game Bot</title>
        <style>
            body { font-family: Arial; padding: 40px; text-align: center; }
            .success { color: green; font-size: 24px; }
            input { width: 80%; padding: 12px; margin: 20px; }
        </style>
    </head>
    <body>
        <h1>🎮 Игровой бот для ВКонтакте</h1>
        <p class="success">✅ БОТ УСПЕШНО ЗАПУЩЕН</p>
        <p>URL для Callback API ВК:</p>
        <input type="text" value="https://YOUR-DOMAIN.vercel.app/api/callback" readonly>
        <p>Скопируйте этот URL в настройках сообщества ВК</p>
    </body>
    </html>
    """

@app.route('/api/callback', methods=['POST'])
def callback():
    # Принимаем запросы от ВК
    data = request.json
    
    # Простая проверка
    if data.get('type') == 'confirmation':
        # Возвращаем строку подтверждения из настроек ВК
        return '123456'  # Замените на ваш код из настроек ВК
    
    # Обработка сообщений
    if data.get('type') == 'message_new':
        user_id = data['object']['message']['from_id']
        text = data['object']['message']['text']
        
        # Простая игровая логика
        response = "Привет! 🎮\nКоманды:\n/играть\n/баланс\n/бонус"
        
        if "играть" in text.lower():
            response = "🎰 Вы выиграли 100 монет!"
        elif "баланс" in text.lower():
            response =
