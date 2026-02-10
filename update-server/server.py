"""
NetAudit Update Server
======================
Servidor HTTP simples para servir atualizações do NetAudit

Endpoints:
- GET /updates/version.json - Informações da versão atual
- GET /updates/releases/NetAudit-Setup.exe - Download do instalador

Porta: 8080
"""

from flask import Flask, send_file, jsonify, request
from flask_cors import CORS
import os
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('update-server.log'),
        logging.StreamHandler()
    ]
)

# Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RELEASES_DIR = os.path.join(BASE_DIR, 'releases')
VERSION_FILE = os.path.join(BASE_DIR, 'version.json')

# Criar diretório de releases se não existir
os.makedirs(RELEASES_DIR, exist_ok=True)

@app.route('/updates/version.json', methods=['GET'])
def get_version():
    """Retorna informações da versão atual"""
    try:
        client_ip = request.remote_addr
        logging.info(f"[VERSION CHECK] Cliente: {client_ip}")
        
        if not os.path.exists(VERSION_FILE):
            logging.error("version.json não encontrado!")
            return jsonify({"error": "version.json não encontrado"}), 404
        
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            import json
            version_data = json.load(f)
        
        logging.info(f"[VERSION CHECK] Versão atual: {version_data.get('latest_version')}")
        return jsonify(version_data)
    
    except Exception as e:
        logging.error(f"[VERSION CHECK] Erro: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/updates/releases/<filename>', methods=['GET'])
def download_release(filename):
    """Download do instalador"""
    try:
        client_ip = request.remote_addr
        logging.info(f"[DOWNLOAD] Cliente: {client_ip} | Arquivo: {filename}")
        
        file_path = os.path.join(RELEASES_DIR, filename)
        
        if not os.path.exists(file_path):
            logging.error(f"[DOWNLOAD] Arquivo não encontrado: {filename}")
            return jsonify({"error": "Arquivo não encontrado"}), 404
        
        file_size = os.path.getsize(file_path)
        logging.info(f"[DOWNLOAD] Enviando {filename} ({file_size:,} bytes)")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    
    except Exception as e:
        logging.error(f"[DOWNLOAD] Erro: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/updates/stats', methods=['GET'])
def get_stats():
    """Estatísticas do servidor de updates"""
    try:
        stats = {
            "server_status": "online",
            "timestamp": datetime.now().isoformat(),
            "releases_available": []
        }
        
        # Listar releases disponíveis
        if os.path.exists(RELEASES_DIR):
            for filename in os.listdir(RELEASES_DIR):
                file_path = os.path.join(RELEASES_DIR, filename)
                if os.path.isfile(file_path):
                    stats["releases_available"].append({
                        "filename": filename,
                        "size_bytes": os.path.getsize(file_path),
                        "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    })
        
        return jsonify(stats)
    
    except Exception as e:
        logging.error(f"[STATS] Erro: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """Página inicial"""
    return """
    <html>
    <head>
        <title>NetAudit Update Server</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #2563eb; }
            .status { color: #10b981; font-weight: bold; }
            .endpoint { background: #f3f4f6; padding: 10px; margin: 10px 0; border-radius: 5px; }
            code { background: #e5e7eb; padding: 2px 6px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>🚀 NetAudit Update Server</h1>
        <p class="status">✓ Servidor Online</p>
        
        <h2>Endpoints Disponíveis:</h2>
        <div class="endpoint">
            <strong>GET</strong> <code>/updates/version.json</code><br>
            Retorna informações da versão atual
        </div>
        <div class="endpoint">
            <strong>GET</strong> <code>/updates/releases/&lt;filename&gt;</code><br>
            Download do instalador
        </div>
        <div class="endpoint">
            <strong>GET</strong> <code>/updates/stats</code><br>
            Estatísticas do servidor
        </div>
        
        <hr>
        <p><small>NetAudit Update Server v1.0 | FUNESA</small></p>
    </body>
    </html>
    """

if __name__ == '__main__':
    print("=" * 60)
    print("NetAudit Update Server")
    print("=" * 60)
    print(f"Diretório base: {BASE_DIR}")
    print(f"Diretório releases: {RELEASES_DIR}")
    print(f"Arquivo version: {VERSION_FILE}")
    print("=" * 60)
    print("Servidor iniciando em http://0.0.0.0:8080")
    print("Pressione CTRL+C para parar")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8080, debug=False)
