import sys
import os
import multiprocessing
import queue
import webbrowser
import socket
import customtkinter as ctk
from PIL import Image, ImageDraw
import threading
import pystray
import time
import requests
import json
import ctypes
import subprocess
import updater

# Prevenir abertura de janelas em subprocessos
CREATE_NO_WINDOW = 0x08000000

# Fix para carregamento de DLLs no Windows (Python 3.8+)
if getattr(sys, 'frozen', False) and hasattr(os, 'add_dll_directory'):
    # Adiciona o diretório temporário do PyInstaller ao path de busca de DLLs
    os.add_dll_directory(sys._MEIPASS)
    # Também garante que o diretório atual e o do EXE estejam lá
    os.add_dll_directory(os.path.dirname(sys.executable))
    
VERSION = "2.0.3"

# Configuração para PyInstaller
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Enable High DPI
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

def run_server_process(log_queue, host="127.0.0.1"):
    # REDIRECT STDOUT/STDERR TO QUEUE
    class QueueWriter:
        def __init__(self, q): self.q = q
        def write(self, msg):
            if msg.strip(): self.q.put(msg.strip())
        def flush(self): pass
    
    sys.stdout = QueueWriter(log_queue)
    sys.stderr = QueueWriter(log_queue)
    
    try:
        print(">>> [SECURITY] Inicializando módulo de encriptação...")
        from security import get_key
        _ = get_key()
        
        print(">>> [CORE] Carregando NetAudit Enterprise...")
        from app import app, start_background_services
        from waitress import serve
        
        start_background_services()
        
        print(f">>> [NETWORK] Servidor vinculando ao host: {host}")
        print(f">>> [NETWORK] Servidor disponível em http://{host}:5000")
        print(">>> [SYSTEM] Serviço pronto para uso.")
        
        serve(app, host=host, port=5000, threads=12)
        
    except Exception as e:
        sys.stderr.write(f"FATAL ERROR: {e}")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("NetAudit Server Controller")
        self.geometry("900x600")
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        
        # Variáveis
        self.process = None
        self.log_queue = multiprocessing.Queue()
        self.settings_file = os.path.join(os.environ.get('APPDATA'), 'NetAudit Enterprise', 'launcher_settings.json')
        self.load_settings()
        
        # Ícone
        icon_path = resource_path("netaudit.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
            
        # Layout Grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # === SIDEBAR ===
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)
        
        # Logo Text
        self.logo_label = ctk.CTkLabel(self.sidebar, text="NetAudit\nEnterprise", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Status Indicator
        self.status_label = ctk.CTkLabel(self.sidebar, text="● OFF", text_color="gray", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # === NETWORK CONFIG ===
        self.network_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.network_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.net_mode_label = ctk.CTkLabel(self.network_frame, text="Modo de Rede:", anchor="w")
        self.net_mode_label.pack(fill="x")
        
        self.net_mode_var = ctk.StringVar(value="Localhost")
        self.net_mode_menu = ctk.CTkOptionMenu(
            self.network_frame, 
            values=["Localhost", "Host (Rede)"],
            variable=self.net_mode_var,
            command=self.update_network_ui
        )
        self.net_mode_menu.pack(fill="x", pady=(0, 10))
        
        self.ip_selection_label = ctk.CTkLabel(self.network_frame, text="IP do Servidor:", anchor="w")
        self.ip_selection_var = ctk.StringVar(value=self.saved_ip)
        self.ip_selection_menu = ctk.CTkComboBox(
            self.network_frame,
            values=["0.0.0.0", "127.0.0.1"],
            variable=self.ip_selection_var,
            width=180
        )
        self.ip_selection_menu.set(self.saved_ip)
        
        self.btn_unlock_fw = ctk.CTkButton(
            self.network_frame, 
            text="LIBERAR FIREWALL", 
            command=self.unlock_firewall,
            fg_color="#f59e0b",
            hover_color="#d97706",
            height=24,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        
        self.update_network_ui(self.saved_mode)

        # Sidebar Buttons
        self.sidebar_btn_start = ctk.CTkButton(self.sidebar, text="INICIAR SERVIDOR", command=self.start_server, fg_color="#22c55e", hover_color="#16a34a")
        self.sidebar_btn_start.grid(row=3, column=0, padx=20, pady=10)
        
        self.sidebar_btn_stop = ctk.CTkButton(self.sidebar, text="PARAR SERVIDOR", command=self.stop_server, fg_color="#ef4444", hover_color="#dc2626", state="disabled")
        self.sidebar_btn_stop.grid(row=4, column=0, padx=20, pady=10)
        
        self.sidebar_btn_dash = ctk.CTkButton(self.sidebar, text="ABRIR DASHBOARD", command=self.open_browser, fg_color="#6366f1", hover_color="#4f46e5")
        self.sidebar_btn_dash.grid(row=5, column=0, padx=20, pady=10, sticky="n")

        # Maintenance Buttons (Bottom)
        self.btn_reset = ctk.CTkButton(self.sidebar, text="Reset Admin", command=self.reset_users, fg_color="transparent", border_width=1, text_color="gray90")
        self.btn_reset.grid(row=6, column=0, padx=20, pady=(10, 5))

        self.btn_uninstall = ctk.CTkButton(self.sidebar, text="DESINSTALAR TUDO", command=self.full_uninstall, fg_color="#450a0a", hover_color="#7f1d1d", text_color="#fca5a5", height=24, font=ctk.CTkFont(size=11, weight="bold"))
        self.btn_uninstall.grid(row=7, column=0, padx=20, pady=(0, 10))
        
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar, text="Tema:", anchor="w")
        self.appearance_mode_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar, values=["Dark", "Light", "System"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=8, column=0, padx=20, pady=(0, 20))

        # === MAIN CONTENT (LOGS) ===
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Header
        self.header_label = ctk.CTkLabel(self.main_frame, text="LOGS DO SISTEMA", font=ctk.CTkFont(size=16, weight="bold"))
        self.header_label.grid(row=0, column=0, sticky="w", pady=(0,10))
        
        # Clear Button
        self.btn_clear = ctk.CTkButton(self.main_frame, text="Limpar", width=60, height=24, command=self.clear_logs, fg_color="#334155")
        self.btn_clear.grid(row=0, column=0, sticky="e", pady=(0,10))
        
        # Log Box
        self.textbox = ctk.CTkTextbox(self.main_frame, width=250, font=("Consolas", 12))
        self.textbox.grid(row=1, column=0, sticky="nsew")
        self.textbox.configure(state="disabled", fg_color="#020617", text_color="#22c55e") # Matrix style

        # === INFO PANEL ===
        self.info_frame = ctk.CTkFrame(self.main_frame, fg_color="#1e293b", corner_radius=10)
        self.info_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0), padx=0)
        
        self.url_info_label = ctk.CTkLabel(
            self.info_frame, 
            text="Aguardando inicialização...", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8",
            wraplength=250
        )
        self.url_info_label.pack(pady=10, padx=20)
        
        self.vm_warning_label = ctk.CTkLabel(
            self.main_frame,
            text="DICA: Se for uma VM, certifique-se que a rede está em modo 'BRIDGED' para acesso externo.",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color="#64748b"
        )
        self.vm_warning_label.grid(row=3, column=0, pady=5)
        
        self.create_tray_icon()
        
        # Iniciar verificação de logs
        self.check_logs()
        
        # Verificar Atualizações em Background (apenas se for EXE)
        if getattr(sys, 'frozen', False):
            threading.Thread(target=self.check_updates_silent, daemon=True).start()
            
    def check_updates_silent(self):
        """Verifica se há versão nova e pergunta ao usuário."""
        has_new, latest, url, sha256 = updater.check_for_updates(VERSION)
        if has_new:
            # Pergunta via thread-safe call
            self.after(0, lambda: self.prompt_update(latest, url, sha256))

    def prompt_update(self, latest, url, sha256):
        import tkinter as tk
        from tkinter import messagebox
        if messagebox.askyesno("Nova Versão Disponível", 
                                f"Uma nova versão ({latest}) foi encontrada!\n"
                                f"Sua versão atual: {VERSION}\n\n"
                                "Deseja baixar e instalar agora?"):
            if updater.run_update(url, latest, sha256):
                self.stop_server()
                if hasattr(self, 'tray_icon'):
                    self.tray_icon.stop()
                self.destroy()
                sys.exit(0)

    def update_network_ui(self, mode):
        if mode == "Localhost":
            self.ip_selection_label.pack_forget()
            self.ip_selection_menu.pack_forget()
            self.btn_unlock_fw.pack_forget()
            self.ip_selection_var.set("127.0.0.1")
        else:
            self.ip_selection_label.pack(fill="x")
            self.ip_selection_menu.pack(fill="x", pady=(0, 10))
            self.btn_unlock_fw.pack(fill="x")
            ips = self.get_local_ips()
            self.ip_selection_menu.configure(values=ips)
            # Apenas reseta se o IP atual for 127.0.0.1
            if self.ip_selection_var.get() == "127.0.0.1" and ips:
                self.ip_selection_var.set(ips[0])

    def get_local_ips(self):
        try:
            hostname = socket.gethostname()
            # Pega todos os IPs da máquina
            ips = socket.gethostbyname_ex(hostname)[2]
            # Filtra e garante que temos 0.0.0.0
            unique_ips = ["0.0.0.0"]
            for ip in ips:
                if not ip.startswith("127.") and ip not in unique_ips:
                    unique_ips.append(ip)
            return unique_ips
        except:
            return ["0.0.0.0", "127.0.0.1"]

    def load_settings(self):
        self.saved_ip = "127.0.0.1"
        self.saved_mode = "Localhost"
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    self.saved_ip = data.get('ip', "127.0.0.1")
                    self.saved_mode = data.get('mode', "Localhost")
        except:
            pass

    def save_settings(self):
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump({'ip': self.ip_selection_var.get(), 'mode': self.net_mode_var.get()}, f)
        except:
            pass

    def unlock_firewall(self):
        self.log(">>> [SECURITY] Solicitando liberação de Firewall (Netsh)...")
        try:
            # Comandos netsh (mais robustos para Windows Server)
            # 1. Remove regras antigas
            # 2. Adiciona nova regra TCP 5000 Inbound
            cmds = [
                'netsh advfirewall firewall delete rule name="NetAudit Enterprise"',
                'netsh advfirewall firewall add rule name="NetAudit Enterprise" dir=in action=allow protocol=TCP localport=5000 profile=any edge=yes'
            ]
            
            full_cmd = " & ".join(cmds)
            
            if ctypes.windll.shell32.IsUserAnAdmin():
                subprocess.run(["cmd", "/c", full_cmd], capture_output=True, creationflags=CREATE_NO_WINDOW)
                self.log(">>> [SUCCESS] Firewall liberado via Netsh (Porta 5000).")
                tk.messagebox.showinfo("Sucesso", "Regras de Firewall aplicadas com Netsh!")
            else:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd", f"/c {full_cmd}", None, 1)
                self.log(">>> [INFO] Solicitando permissão de Admin para Firewall.")
        except Exception as e:
            self.log(f">>> [ERROR] Falha ao liberar firewall: {e}")
            tk.messagebox.showerror("Erro", f"Erro no Firewall: {e}")
        
    def log(self, message):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear_logs(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("0.0", "end")
        self.textbox.configure(state="disabled")

    def check_logs(self):
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.log(msg)
            except queue.Empty:
                break
        self.after(100, self.check_logs)
        
    def start_server(self):
        if self.process and self.process.is_alive(): return
        
        self.save_settings()
        host = self.ip_selection_var.get()
        self.log(f">>> [INIT] Iniciando servidor em {host}...")
        self.process = multiprocessing.Process(target=run_server_process, args=(self.log_queue, host))
        self.process.start()
        
        self.status_label.configure(text="● ONLINE", text_color="#22c55e")
        self.sidebar_btn_start.configure(state="disabled", fg_color="#334155")
        self.sidebar_btn_stop.configure(state="normal", fg_color="#ef4444")
        
        # Aguarda um pouco para o servidor subir antes de abrir o browser
        self.after(3000, self.open_browser)
        
        # Atualizar Info de Acesso
        self.update_access_info(host)

    def update_access_info(self, host):
        if host == "0.0.0.0":
            ips = self.get_local_ips()
            external_ip = ips[1] if len(ips) > 1 else "SEU-IP-REDE"
            txt = f"ACESSO EXTERNO: http://{external_ip}:5000/home"
        elif host == "127.0.0.1":
            txt = "ACESSO LOCAL: http://127.0.0.1:5000/home"
        else:
            txt = f"ACESSO EM: http://{host}:5000/home"
        
        self.url_info_label.configure(text=txt, text_color="#22c55e")

    def stop_server(self):
        if self.process:
            self.log(">>> [STOP] Parando serviços...")
            self.process.terminate()
            self.process.join(timeout=1)
            if self.process.is_alive(): self.process.kill()
            self.process = None
            self.log(">>> [STOP] Sistema parado.")
            
        self.status_label.configure(text="● OFF", text_color="gray")
        self.sidebar_btn_start.configure(state="normal", fg_color="#22c55e")
        self.sidebar_btn_stop.configure(state="disabled", fg_color="#334155")
        
    def open_browser(self):
        host = self.ip_selection_var.get()
        # Se for 0.0.0.0 (todas interfaces), abre via localhost para o usuário atual
        url_host = "127.0.0.1" if host == "0.0.0.0" else host
        webbrowser.open(f"http://{url_host}:5000/home")
        
    def reset_users(self):
        # Dialog is standard tkinter unfortunately as CTk doesn't have modal dialogs yet
        if tk.messagebox.askyesno("Factory Reset", "TEM CERTEZA? Isso fará um WIPE em todos os usuários.\nO sistema voltará ao estado de fábrica.\n\nContinuar?"):
            data_dir = os.path.join(os.environ.get('APPDATA'), 'NetAudit Enterprise')
            users_file = os.path.join(data_dir, "users.json")
            if os.path.exists(users_file):
                try:
                    os.remove(users_file)
                    self.log(">>> [RESET] Usuários deletados com sucesso.")
                    tk.messagebox.showinfo("Sucesso", "Sistema resetado. Reinicie o aplicativo.")
                except Exception as e:
                    self.log(f"Erro: {e}")

    def full_uninstall(self):
        """Inicia processo de desinstalação total pelo launcher"""
        if tk.messagebox.askyesno("DESINSTALAÇÃO TOTAL", "ATENÇÃO MÁXIMA!\n\nIsso irá apagar TODOS os seus dados, configurações, bancos de dados e logs do PC.\n\nEsta ação é IRREVERSÍVEL. Deseja continuar?"):
            
            # Segunda confirmação para evitar cliques acidentais
            confirm = tk.messagebox.askyesno("CONFIRMAÇÃO FINAL", "Você tem certeza absoluta?\nO sistema será encerrado e os dados apagados.")
            if not confirm: return

            try:
                # 1. Pega caminhos
                data_dir = os.path.join(os.environ.get('APPDATA'), 'NetAudit Enterprise')
                temp_dir = os.environ.get('TEMP')
                cleanup_script = os.path.join(temp_dir, 'netaudit_cleanup.bat')

                # 2. Cria script de limpeza
                with open(cleanup_script, 'w') as f:
                    f.write(f'''@echo off
timeout /t 3 /nobreak > nul
echo Limpando dados do NetAudit...
rd /s /q "{data_dir}"
echo Limpeza concluída.
del "%~f0"
''')

                # 3. Executa script invisível
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen(['cmd.exe', '/c', cleanup_script], creationflags=CREATE_NO_WINDOW)

                # 4. Encerra tudo
                self.stop_server()
                self.destroy()
                sys.exit(0)
            except Exception as e:
                tk.messagebox.showerror("Erro", f"Erro ao desinstalar: {e}")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def minimize_to_tray(self):
        self.withdraw()
        self.log("Minimizado para a bandeja.")

    def create_tray_icon(self):
        icon_path = resource_path("netaudit.ico")
        if os.path.exists(icon_path):
            image = Image.open(icon_path)
        else:
            image = Image.new('RGB', (64, 64), color=(99, 102, 241))
            d = ImageDraw.Draw(image)
            d.rectangle([16, 16, 48, 48], fill="white")
            
        def show(icon, item): self.after(0, self.deiconify)
        def exit_app(icon, item):
            self.stop_server()
            icon.stop()
            self.destroy()
            sys.exit(0)
            
        menu = pystray.Menu(
            pystray.MenuItem('Abrir Painel', show, default=True),
            pystray.MenuItem('Dashboard', lambda: self.open_browser()),
            pystray.MenuItem('Encerrar', exit_app)
        )
        self.tray_icon = pystray.Icon("NetAudit", image, "NetAudit", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

# Variável global para manter o socket aberto e evitar que outro processo abra
instance_lock = None

def check_single_instance():
    global instance_lock
    try:
        # Tenta criar um socket local em uma porta específica para agir como trava
        instance_lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        instance_lock.bind(('127.0.0.1', 19876))  # Porta arbitrária para trava
    except socket.error:
        # Se falhar, já existe outra instância rodando
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning("NetAudit Já Iniciado", "O NetAudit já está em execução no seu computador.\nProcure pelo ícone azul na bandeja do sistema (perto do relógio).")
        root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    # Migração de dados para pasta persistente (AppData)
    try:
        from utils import migrate_legacy_data
        migrate_legacy_data()
    except Exception as e:
        print(f"Erro na migração de dados: {e}")
        
    check_single_instance()
    app = App()
    app.mainloop()
