from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "🎮 VK Game Bot is LIVE!"

if __name__ == '__main__':
    app.run()
