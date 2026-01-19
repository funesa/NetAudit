import hashlib
import json
import base64
from datetime import datetime, timedelta
import os
import subprocess
import sys

class LicenseManager:
    def __init__(self, secret_salt="NETAUDIT-SECURE-SALT-2026"):
        self.secret_salt = secret_salt
        self.license_file = "license.json"
        self.blacklist_file = "license_blacklist.json"
        self.trial_file = ".sys_meta_trial.dat" # Arquivo oculto de trial
        self._hwid_cache = None

    def get_hwid(self):
        """Captura Identificador Único de Hardware (UUID da BIOS/Placa-mãe)"""
        if self._hwid_cache:
            return self._hwid_cache
        
        try:
            # Método 1: PowerShell (UUID - Mais estável e único)
            cmd = "Get-CimInstance Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID"
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            uuid = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", cmd], 
                startupinfo=startupinfo
            ).decode().strip()
            
            if uuid:
                self._hwid_cache = hashlib.sha256(uuid.encode()).hexdigest()
                return self._hwid_cache
        except:
            pass
            
        try:
            # Método 2: WMIC (Fallback Legacy)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            bios_serial = subprocess.check_output(
                "wmic bios get serialnumber", 
                startupinfo=startupinfo, 
                shell=True
            ).decode().split('\n')[1].strip()
            
            baseboard_serial = subprocess.check_output(
                "wmic baseboard get serialnumber", 
                startupinfo=startupinfo, 
                shell=True
            ).decode().split('\n')[1].strip()
            
            raw_id = f"NET-{bios_serial}-{baseboard_serial}"
            self._hwid_cache = hashlib.sha256(raw_id.encode()).hexdigest()
        except:
            # Método 3: Hostname (Último recurso)
            self._hwid_cache = hashlib.sha256(os.environ.get('COMPUTERNAME', 'UNKNOWN').encode()).hexdigest()
            
        return self._hwid_cache

    def _get_trial_data(self):
        """Lê os dados do trial de forma segura"""
        if not os.path.exists(self.trial_file):
            return None
        
        try:
            with open(self.trial_file, "r") as f:
                enc_data = f.read()
                # Decriptação simples baseada no HWID para evitar cópia entre máquinas
                raw_data = base64.b64decode(enc_data).decode()
                data = json.loads(raw_data)
                
                # Verifica se o HWID no arquivo bate com a máquina atual
                if data.get("hwid") != self.get_hwid():
                    return None
                return data
        except:
            return None

    def _init_trial(self):
        """Inicia um novo trial de 7 dias para este hardware"""
        start_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "hwid": self.get_hwid(),
            "start_date": start_date,
            "version": "1.0"
        }
        
        try:
            json_str = json.dumps(data)
            enc_data = base64.b64encode(json_str.encode()).decode()
            with open(self.trial_file, "w") as f:
                f.write(enc_data)
                # Ocultar arquivo no Windows
                if sys.platform == "win32":
                    subprocess.run(["attrib", "+h", self.trial_file], capture_output=True)
            return data
        except:
            return data

    def get_trial_status(self):
        """Retorna dias restantes do trial ou None se expirado/inexistente"""
        data = self._get_trial_data()
        if not data:
            data = self._init_trial()
            
        try:
            start_date = datetime.strptime(data["start_date"], "%Y-%m-%d %H:%M:%S")
            days_elapsed = (datetime.now() - start_date).days
            days_left = max(0, 7 - days_elapsed)
            return days_left
        except:
            return 0

    def generate_key(self, customer_name, months=1, tier="premium"):
        """Gera uma chave assinada (Para uso do POFJunior)"""
        expiry_date = (datetime.now() + timedelta(days=30 * months)).strftime("%Y-%m-%d")
        data = {
            "customer": customer_name,
            "expiry": expiry_date,
            "tier": tier,
            "issued_at": datetime.now().strftime("%Y-%m-%d")
        }
        
        # Criar assinatura baseada nos dados + salt
        json_str = json.dumps(data, sort_keys=True)
        signature = hashlib.sha256((json_str + self.secret_salt).encode()).hexdigest()
        
        # Payload final em base64
        payload = {
            "data": data,
            "sig": signature,
            "license_id": hashlib.md5(customer_name.encode()).hexdigest()  # ID único
        }
        return base64.b64encode(json.dumps(payload).encode()).decode()

    def validate_license(self, key_b64):
        """Valida se a chave é autêntica e não expirou"""
        try:
            raw_payload = base64.b64decode(key_b64).decode()
            payload = json.loads(raw_payload)
            data = payload["data"]
            sig = payload["sig"]
            
            # Verificar assinatura
            expected_sig = hashlib.sha256((json.dumps(data, sort_keys=True) + self.secret_salt).encode()).hexdigest()
            if sig != expected_sig:
                return False, "Assinatura inválida"
            
            # Verificar se está na blacklist
            if self.is_blacklisted(payload.get("license_id")):
                return False, "Licença revogada pelo vendedor"
            
            # Verificar expiração
            expiry = datetime.strptime(data["expiry"], "%Y-%m-%d")
            if datetime.now() > expiry:
                return False, "Licença expirada"
            
            return True, data
        except Exception as e:
            return False, f"Erro na validação: {str(e)}"
    
    def is_blacklisted(self, license_id):
        """Verifica se a licença foi revogada"""
        if not license_id:
            return False
        if not os.path.exists(self.blacklist_file):
            return False
        try:
            with open(self.blacklist_file, "r") as f:
                blacklist = json.load(f)
                return license_id in blacklist
        except:
            return False
    
    def save_license(self, key):
        with open(self.license_file, "w") as f:
            json.dump({"key": key}, f)

    def get_current_license(self):
        if not os.path.exists(self.license_file):
            return None
        with open(self.license_file, "r") as f:
            lic = json.load(f)
            valid, data = self.validate_license(lic["key"])
            return data if valid else None

    def is_premium(self):
        """Verifica se possui licença Premium Ativa"""
        lic = self.get_current_license()
        return lic is not None and lic.get("tier") == "premium"

    def has_pro_access(self):
        """Verifica se tem acesso aos recursos PRO (Premium OU Trial Ativo)"""
        if self.is_premium():
            return True
        
        # Se não for premium, verifica trial
        days_left = self.get_trial_status()
        return days_left > 0

    def get_user_limit(self):
        """Define o limite de usuários baseado na licença"""
        # Trial também deve liberar usuários ilimitados
        if self.has_pro_access():
            return 9999 # Infinito para Premium ou Trial
        return 3 # Limite rigoroso para Free sem trial

# Singleton para o app
lic_manager = LicenseManager()
