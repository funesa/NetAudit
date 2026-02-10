import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from datetime import datetime
import psutil

# Importar banco de dados e modelos
from database import get_session
from models import Device, Metric, Alert, Trigger

# Importar alert manager
from alert_manager import alert_manager

# Configuração de Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MetricsCollector")

class MetricsCollector:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.process_cache = {} # Cache de processos em tempo real {device_id: [processes]}
        
    def start(self):
        """Inicia o agendador com proteção total contra shutdown/restart"""
        if self.is_running:
            try:
                # Verifica se o agendador ainda está 'vivo'
                if self.scheduler.running:
                    return
            except:
                pass
            
        logger.info("[Sentinel] Iniciando motor de monitoramento isolado...")
        
        # Garantir limpeza total antes de iniciar
        self.stop()
        
        # Recriar agendador fresco (Garante que os executores/threadpools sejam novos)
        self.scheduler = BackgroundScheduler(daemon=True)
        
        try:
            self.scheduler.add_job(
                self.collect_all_metrics,
                trigger=IntervalTrigger(seconds=60),
                id='collect_metrics',
                name='Coleta de Métricas Global',
                replace_existing=True,
                misfire_grace_time=30 # Tolerância para atrasos
            )
            self.scheduler.start()
            self.is_running = True
            logger.info("✅ Sentinel engine (Re-Born) ativa. Intervalo: 60s")
        except Exception as e:
            logger.error(f"❌ Erro ao subir engine Sentinel: {e}")

    def stop(self):
        """Para o agendador de forma limpa e libera recursos"""
        try:
            if self.scheduler and self.scheduler.running:
                # wait=False para não travar o shutdown se houver algo rodando
                self.scheduler.shutdown(wait=False)
                logger.info("[Sentinel] Motor parado e executores liberados.")
        except Exception:
            pass
        finally:
            self.is_running = False
            self.scheduler = None 

    def collect_all_metrics(self):
        """Função principal otimizada com processamento paralelo e inteligência de rede"""
        import pythoncom
        from concurrent.futures import ThreadPoolExecutor
        
        session = get_session()
        try:
            logger.info(">>> [Sentinel] Iniciando ciclo de monitoramento inteligente...")
            
            # Buscar apenas dispositivos mapeados pelo scan (já existentes na base)
            devices = session.query(Device).all()
            if not devices:
                logger.warning("Nenhum ativo mapeado para monitoramento.")
                return

            # Inicializar COM para a thread principal do job
            pythoncom.CoInitialize()
            
            # Usar pool de THREADS para melhor performance com SQLite e WAL mode
            from concurrent.futures import ThreadPoolExecutor
            
            # Coletar IDs para processar
            device_ids = [d.id for d in devices]
            
            # Aumentar workers para lidar com 217 ativos em 60s
            max_workers = 25 
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit tasks
                futures = {executor.submit(worker_thread_task, dev_id): dev_id for dev_id in device_ids}
                
                # Wait for completion with GLOBAL TIMEOUT (e.g. 50s so it finishes before next 60s job)
                from concurrent.futures import wait, FIRST_EXCEPTION
                done, not_done = wait(futures.keys(), timeout=50)
                
                for future in not_done:
                    # Tentar cancelar tasks que não terminaram
                    future.cancel()
                    logger.warning(f"Timeout forcado na coleta do device {futures[future]}")
            
            logger.info(f">>> [Sentinel] Ciclo finalizado. {len(done)} concluídos, {len(not_done)} timeouts.")
            
        except Exception as e:
            logger.error(f"Erro crítico no motor Sentinel (ProcessPool): {e}")
        finally:
            pythoncom.CoUninitialize()
            session.close()

    def collect_device_metrics(self, session: Session, device: Device):
        """Coleta métricas de um único dispositivo com inteligência de skip"""
        
        # Monitoramento de Latência e Pre-Check (Ping)
        # Se for remoto, verificamos se responde antes de tentar coletas pesadas
        is_online = True
        if device.ip not in ['127.0.0.1', 'localhost', '0.0.0.0']:
            is_online = self._collect_latency(session, device)

        if not is_online:
            # Ativo offline: não perdemos tempo tentando WMI (que demora timeout) ou SNMP
            logger.debug(f"[Sentinel] Skip {device.ip}: Ativo offline.")
            return

        # 1. Monitoramento Local (Auto-monitoramento do Servidor)
        if device.ip in ['127.0.0.1', 'localhost', '0.0.0.0']:
            self._collect_local_metrics(session, device)
            return

        # 2. Monitoramento de Impressoras via SNMP
        if device.device_type == 'printer':
            self._collect_printer_metrics(session, device)
            return

        # 3. Monitoramento de Windows via WMI
        if device.device_type in ['windows', 'server']:
            self._collect_windows_metrics(session, device)
            return

        # 4. Monitoramento de Dispositivos de Rede via SNMP
        if device.device_type == 'network':
            self._collect_network_metrics(session, device)
            return

    def _collect_latency(self, session: Session, device: Device):
        """Mede a latência (ping) do dispositivo e retorna status online"""
        try:
            import subprocess
            import platform
            
            # Comando de ping ultra-rápido (1 pacote, 500ms timeout)
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            command = ['ping', param, '1', '-w', '500', device.ip]
            
            start_time = time.time()
            res = subprocess.run(command, capture_output=True, text=True, timeout=1.5, creationflags=0x08000000) # CREATE_NO_WINDOW
            latency = (time.time() - start_time) * 1000 # em ms
            
            if res.returncode == 0:
                metric = Metric(
                    device_id=device.id,
                    metric_type='latency',
                    value=round(latency, 2),
                    unit='ms'
                )
                session.add(metric)
                device.last_seen = datetime.now()
                return True
            return False
        except Exception:
            return False

    def _collect_local_metrics(self, session: Session, device: Device):
        """Coleta métricas da própria máquina usando psutil"""
        cpu_percent = psutil.cpu_percent(interval=1)
        ram_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        # Salvar CPU
        metric_cpu = Metric(
            device_id=device.id,
            metric_type='cpu_usage',
            value=cpu_percent,
            unit='%'
        )
        session.add(metric_cpu)
        
        # Salvar RAM
        metric_ram = Metric(
            device_id=device.id,
            metric_type='ram_usage',
            value=ram_percent,
            unit='%'
        )
        session.add(metric_ram)

        # Salvar Disk
        metric_disk = Metric(
            device_id=device.id,
            metric_type='disk_usage',
            value=disk_percent,
            unit='%'
        )
        session.add(metric_disk)
        
        # Verificar Triggers
        self._check_triggers(session, device, 'cpu_usage', cpu_percent)
        self._check_triggers(session, device, 'ram_usage', ram_percent)
        self._check_triggers(session, device, 'disk_usage', disk_percent)
        
        # Auto-resolver alertas se condições normalizaram
        alert_manager.auto_resolve_alerts(device.id, 'cpu_usage', cpu_percent, session)
        alert_manager.auto_resolve_alerts(device.id, 'ram_usage', ram_percent, session)
        alert_manager.auto_resolve_alerts(device.id, 'disk_usage', disk_percent, session)

        # Coletar processos (Top 10 por Memória)
        try:
            procs = []
            for p in psutil.process_iter(['name', 'memory_percent']):
                try:
                    procs.append({
                        'name': p.info['name'],
                        'memory_percent': round(p.info['memory_percent'], 2)
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort and take top 10
            self.process_cache[device.id] = sorted(procs, key=lambda x: x['memory_percent'], reverse=True)[:10]
        except Exception as e:
            logger.error(f"Erro ao coletar processos locais: {e}")

    def _collect_windows_metrics(self, session: Session, device: Device):
        """Coleta métricas de Windows remoto via WMI"""
        try:
            from wmi_helper import get_windows_metrics
            from utils import load_general_settings
            
            # Carregar credenciais AD (ou específicas do dispositivo)
            settings = load_general_settings()
            ad_config = settings.get('ad_config', {})
            username = ad_config.get('username')
            password = ad_config.get('password')
            domain = ad_config.get('domain')
            
            if not username or not password:
                logger.warning(f"Credenciais WMI não configuradas para {device.ip}")
                return
            
            # Coletar métricas
            metrics = get_windows_metrics(device.ip, username, password, domain)
            
            if not metrics:
                logger.warning(f"Falha ao coletar métricas WMI de {device.ip}")
                return
            
            # Salvar CPU
            if metrics.get('cpu_percent') is not None:
                metric = Metric(
                    device_id=device.id,
                    metric_type='cpu_usage',
                    value=metrics['cpu_percent'],
                    unit='%'
                )
                session.add(metric)
                self._check_triggers(session, device, 'cpu_usage', metrics['cpu_percent'])
                alert_manager.auto_resolve_alerts(device.id, 'cpu_usage', metrics['cpu_percent'], session)
            
            # Salvar RAM
            if metrics.get('memory'):
                ram_percent = metrics['memory'].get('percent', 0)
                metric = Metric(
                    device_id=device.id,
                    metric_type='ram_usage',
                    value=ram_percent,
                    unit='%'
                )
                session.add(metric)
                self._check_triggers(session, device, 'ram_usage', ram_percent)
                alert_manager.auto_resolve_alerts(device.id, 'ram_usage', ram_percent, session)
            
            # Salvar Disco (maior disco)
            if metrics.get('disks'):
                for disk in metrics['disks']:
                    metric = Metric(
                        device_id=device.id,
                        metric_type=f'disk_usage_{disk["drive"]}',
                        value=disk['percent'],
                        unit='%'
                    )
                    session.add(metric)
                    self._check_triggers(session, device, 'disk_usage', disk['percent'])
                    alert_manager.auto_resolve_alerts(device.id, 'disk_usage', disk['percent'], session)
            
            # Salvar Processos no Cache
            if metrics.get('processes'):
                # WMI already returns top processes, let's just format if needed
                self.process_cache[device.id] = metrics['processes']
            
            # Verificar Windows Obsoleto
            if metrics.get('windows_version'):
                version_info = metrics['windows_version']
                if version_info.get('is_obsolete'):
                    self._create_obsolete_windows_alert(session, device, version_info['version'])
            
            logger.info(f"✅ Métricas WMI coletadas de {device.hostname} ({device.ip})")
            
        except Exception as e:
            logger.error(f"Erro ao coletar métricas WMI de {device.ip}: {e}")

    def _collect_printer_metrics(self, session: Session, device: Device):
        """Coleta métricas de impressora via SNMP"""
        try:
            from snmp_helper import get_printer_metrics_for_monitoring
            
            metrics = get_printer_metrics_for_monitoring(device.ip)
            
            if not metrics:
                logger.warning(f"Falha ao coletar métricas SNMP de impressora {device.ip}")
                return
            
            # Salvar contador de páginas
            if metrics.get('page_count'):
                metric = Metric(
                    device_id=device.id,
                    metric_type='page_count',
                    value=int(metrics['page_count']),
                    unit='pages'
                )
                session.add(metric)
            
            # Salvar níveis de toner
            for color in ['black', 'cyan', 'magenta', 'yellow']:
                level = metrics.get(f'toner_{color}')
                if level is not None and level != -1:
                    metric = Metric(
                        device_id=device.id,
                        metric_type=f'toner_{color}',
                        value=level,
                        unit='%'
                    )
                    session.add(metric)
                    
                    # Verificar triggers de toner baixo
                    self._check_triggers(session, device, f'toner_{color}', level)
                    alert_manager.auto_resolve_alerts(device.id, f'toner_{color}', level, session)
            
            # Alertas especiais para toner < 10%
            if metrics.get('low_toner_supplies'):
                for supply_name in metrics['low_toner_supplies']:
                    self._create_low_toner_alert(session, device, supply_name)
            
            logger.info(f"✅ Métricas SNMP coletadas de impressora {device.hostname} ({device.ip})")
            
        except Exception as e:
            logger.error(f"Erro ao coletar métricas SNMP de impressora {device.ip}: {e}")

    def _collect_network_metrics(self, session: Session, device: Device):
        """Coleta métricas de dispositivo de rede via SNMP (placeholder)"""
        # TODO: Implementar coleta de interfaces, latência, etc.
        pass

    def _check_triggers(self, session: Session, device: Device, metric_type: str, value: float):
        """Verifica se alguma regra (trigger) foi violada"""
        try:
            # Buscar triggers ativos para este tipo de métrica
            triggers = session.query(Trigger).filter(
                Trigger.metric_type == metric_type,
                Trigger.enabled == True
            ).all()
            
            for trigger in triggers:
                # Filtrar por tipo de dispositivo se configurado
                if trigger.device_type_filter:
                    if device.device_type != trigger.device_type_filter:
                        continue
                
                # Verificar se trigger foi violado (considerando duração)
                should_alert = alert_manager.check_trigger_violation(
                    device.id,
                    trigger,
                    value,
                    session
                )
                
                if should_alert:
                    # Criar alerta
                    alert_manager.create_alert(device.id, trigger, value, session)
                    
        except Exception as e:
            logger.error(f"Erro ao verificar triggers: {e}")

    def _create_obsolete_windows_alert(self, session: Session, device: Device, version_string: str):
        """Cria alerta para Windows obsoleto"""
        # Verificar se já existe alerta ativo
        existing = session.query(Alert).filter(
            Alert.device_id == device.id,
            Alert.title == "Windows Obsoleto",
            Alert.resolved_at == None
        ).first()
        
        if not existing:
            alert = Alert(
                device_id=device.id,
                severity='warning',
                title="Windows Obsoleto",
                message=f"Dispositivo {device.hostname} está executando {version_string}, que não recebe mais atualizações de segurança.",
                triggered_at=datetime.now()
            )
            session.add(alert)
            logger.warning(f"⚠️ Windows obsoleto detectado: {device.hostname} - {version_string}")

    def _create_low_toner_alert(self, session: Session, device: Device, supply_name: str):
        """Cria alerta para toner baixo (< 10%)"""
        alert_title = f"Toner Baixo: {supply_name}"
        
        # Verificar se já existe
        existing = session.query(Alert).filter(
            Alert.device_id == device.id,
            Alert.title == alert_title,
            Alert.resolved_at == None
        ).first()
        
        if not existing:
            alert = Alert(
                device_id=device.id,
                severity='warning',
                title=alert_title,
                message=f"Impressora {device.hostname} ({device.ip}) está com {supply_name} abaixo de 10%. Solicite reposição.",
                triggered_at=datetime.now()
            )
            session.add(alert)
            logger.warning(f"⚠️ Toner baixo: {device.hostname} - {supply_name}")


# Instância global
collector = MetricsCollector()

# Função Global para o Worker de Thread
def worker_thread_task(device_id):
    """Tarefa executada em uma thread do pool"""
    import pythoncom
    from database import get_session
    from models import Device
    
    # Inicializa COM para esta thread
    pythoncom.CoInitialize()
    session = get_session()
    try:
        # Instancia localmente para evitar problemas de thread safety
        from metrics_collector import MetricsCollector
        temp_collector = MetricsCollector()
        
        dev = session.query(Device).filter(Device.id == device_id).first()
        if dev:
            # Executa a coleta no contexto desta thread
            temp_collector.collect_device_metrics(session, dev)
            session.commit()
    except Exception as e:
        import logging
        logging.getLogger("MetricsWorker").error(f"Erro na thread worker ({device_id}): {e}")
    finally:
        session.close()
        pythoncom.CoUninitialize()
