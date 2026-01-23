"""
WMI Helper - Coleta de métricas de dispositivos Windows remotos
Suporta: CPU, RAM, Disco, Processos, Versão do Windows, Status de Updates
"""
import wmi
import logging
from datetime import datetime

logger = logging.getLogger("WMIHelper")

class WMICollector:
    """Coletor de métricas via WMI para Windows remotos"""
    
    def __init__(self, ip, username=None, password=None, domain=None):
        """
        Inicializa conexão WMI
        
        Args:
            ip: IP do dispositivo Windows
            username: Usuário com permissão WMI (opcional para localhost)
            password: Senha do usuário
            domain: Domínio (opcional)
        """
        self.ip = ip
        self.username = username
        self.password = password
        self.domain = domain
        self.connection = None
        
    def connect(self):
        """Estabelece conexão WMI"""
        try:
            if self.username and self.password:
                # Conexão remota autenticada
                connection_string = f"\\\\{self.ip}\\root\\cimv2"
                if self.domain:
                    user = f"{self.domain}\\{self.username}"
                else:
                    user = self.username
                    
                self.connection = wmi.WMI(
                    computer=self.ip,
                    user=user,
                    password=self.password
                )
            else:
                # Conexão local
                self.connection = wmi.WMI()
                
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar WMI em {self.ip}: {e}")
            return False
    
    def get_cpu_usage(self):
        """
        Retorna uso de CPU em percentual
        
        Returns:
            float: Percentual de uso de CPU (0-100)
        """
        try:
            if not self.connection:
                if not self.connect():
                    return None
                    
            cpu_info = self.connection.Win32_Processor()[0]
            return float(cpu_info.LoadPercentage)
        except Exception as e:
            logger.error(f"Erro ao coletar CPU de {self.ip}: {e}")
            return None
    
    def get_memory_usage(self):
        """
        Retorna uso de memória RAM em percentual
        
        Returns:
            dict: {'percent': float, 'total_gb': float, 'available_gb': float}
        """
        try:
            if not self.connection:
                if not self.connect():
                    return None
                    
            os_info = self.connection.Win32_OperatingSystem()[0]
            total_memory = int(os_info.TotalVisibleMemorySize)
            free_memory = int(os_info.FreePhysicalMemory)
            used_memory = total_memory - free_memory
            
            percent = (used_memory / total_memory) * 100
            total_gb = total_memory / (1024 * 1024)
            available_gb = free_memory / (1024 * 1024)
            
            return {
                'percent': round(percent, 2),
                'total_gb': round(total_gb, 2),
                'available_gb': round(available_gb, 2)
            }
        except Exception as e:
            logger.error(f"Erro ao coletar RAM de {self.ip}: {e}")
            return None
    
    def get_disk_usage(self):
        """
        Retorna uso de todos os discos
        
        Returns:
            list: [{'drive': 'C:', 'percent': 45.2, 'free_gb': 100, 'total_gb': 500}, ...]
        """
        try:
            if not self.connection:
                if not self.connect():
                    return None
                    
            disks = []
            for disk in self.connection.Win32_LogicalDisk(DriveType=3):  # DriveType 3 = Local Disk
                if disk.Size:
                    total_gb = int(disk.Size) / (1024**3)
                    free_gb = int(disk.FreeSpace) / (1024**3)
                    used_gb = total_gb - free_gb
                    percent = (used_gb / total_gb) * 100
                    
                    disks.append({
                        'drive': disk.DeviceID,
                        'percent': round(percent, 2),
                        'free_gb': round(free_gb, 2),
                        'total_gb': round(total_gb, 2)
                    })
            
            return disks
        except Exception as e:
            logger.error(f"Erro ao coletar discos de {self.ip}: {e}")
            return None
    
    def get_running_processes(self, top_n=10):
        """
        Retorna processos em execução ordenados por uso de memória
        
        Args:
            top_n: Número de processos a retornar
            
        Returns:
            list: [{'name': 'chrome.exe', 'memory_mb': 512, 'cpu_percent': 5}, ...]
        """
        try:
            if not self.connection:
                if not self.connect():
                    return None
                    
            processes = []
            for process in self.connection.Win32_Process():
                try:
                    # WorkingSetSize está em bytes
                    memory_mb = int(process.WorkingSetSize or 0) / (1024 * 1024)
                    
                    processes.append({
                        'name': process.Name,
                        'memory_mb': round(memory_mb, 2),
                        'pid': process.ProcessId
                    })
                except:
                    continue
            
            # Ordenar por uso de memória
            processes.sort(key=lambda x: x['memory_mb'], reverse=True)
            return processes[:top_n]
        except Exception as e:
            logger.error(f"Erro ao coletar processos de {self.ip}: {e}")
            return None
    
    def get_windows_version(self):
        """
        Retorna informações sobre a versão do Windows
        
        Returns:
            dict: {'version': 'Windows 10', 'build': '19045', 'is_obsolete': False}
        """
        try:
            if not self.connection:
                if not self.connect():
                    return None
                    
            os_info = self.connection.Win32_OperatingSystem()[0]
            version_string = os_info.Caption
            build_number = os_info.BuildNumber
            
            # Detectar se é obsoleto
            is_obsolete = self._is_windows_obsolete(version_string)
            
            return {
                'version': version_string,
                'build': build_number,
                'is_obsolete': is_obsolete,
                'service_pack': os_info.ServicePackMajorVersion or 0
            }
        except Exception as e:
            logger.error(f"Erro ao coletar versão do Windows de {self.ip}: {e}")
            return None
    
    def _is_windows_obsolete(self, version_string):
        """
        Verifica se a versão do Windows está obsoleta
        
        Args:
            version_string: String da versão (ex: "Microsoft Windows 7 Professional")
            
        Returns:
            bool: True se obsoleto
        """
        obsolete_versions = [
            'Windows XP',
            'Windows Vista',
            'Windows 7',
            'Windows 8',
            'Server 2003',
            'Server 2008',
            'Server 2012'
        ]
        
        for obsolete in obsolete_versions:
            if obsolete.lower() in version_string.lower():
                return True
        
        return False
    
    def get_uptime(self):
        """
        Retorna uptime do sistema em segundos
        
        Returns:
            int: Uptime em segundos
        """
        try:
            if not self.connection:
                if not self.connect():
                    return None
                    
            os_info = self.connection.Win32_OperatingSystem()[0]
            boot_time = os_info.LastBootUpTime
            
            # Converter formato WMI para datetime
            boot_dt = datetime.strptime(boot_time.split('.')[0], '%Y%m%d%H%M%S')
            uptime_seconds = int((datetime.now() - boot_dt).total_seconds())
            
            return uptime_seconds
        except Exception as e:
            logger.error(f"Erro ao coletar uptime de {self.ip}: {e}")
            return None
    
    def get_all_metrics(self):
        """
        Coleta todas as métricas de uma vez
        
        Returns:
            dict: Dicionário com todas as métricas
        """
        if not self.connection:
            if not self.connect():
                return None
        
        return {
            'cpu_percent': self.get_cpu_usage(),
            'memory': self.get_memory_usage(),
            'disks': self.get_disk_usage(),
            'processes': self.get_running_processes(),
            'windows_version': self.get_windows_version(),
            'uptime_seconds': self.get_uptime(),
            'timestamp': datetime.now().isoformat()
        }
    
    def close(self):
        """Fecha conexão WMI"""
        try:
            if self.connection:
                self.connection = None
        except:
            pass


# Função helper para uso rápido
def get_windows_metrics(ip, username=None, password=None, domain=None):
    """
    Função wrapper para coletar métricas rapidamente
    
    Args:
        ip: IP do dispositivo
        username: Usuário (opcional)
        password: Senha (opcional)
        domain: Domínio (opcional)
        
    Returns:
        dict: Métricas coletadas ou None em caso de erro
    """
    collector = WMICollector(ip, username, password, domain)
    metrics = collector.get_all_metrics()
    collector.close()
    return metrics
