from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>🎮 VK Game Bot</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial; padding: 20px; max-width: 600px; margin: 0 auto; }
                .status { color: green; font-weight: bold; }
                input { width: 100%; padding: 10px; margin: 10px 0; }
            </style>
        </head>
        <body>
            <h1>🎮 Игровой бот для ВКонтакте</h1>
            <p>✅ <span class="status">БОТ АКТИВЕН</span></p>
            <p>Скопируйте этот URL в настройках ВК:</p>
            <input type="text" value="https://YOUR-DOMAIN.vercel.app/api/callback" readonly>
            <p>🔧 <a href="https://vk.com/dev/bots">Инструкция по настройке ВК</a></p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def do_POST(self):
        # Для Callback API ВК
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {"ok": True}
        self.wfile.write(json.dumps(response).encode())
