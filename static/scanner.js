let timer = null;
let scanResults = [];

document.addEventListener('DOMContentLoaded', function () {
    const ctx = document.getElementById('goalsChart');
    if (ctx) {
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Complete', 'In Progress', 'Pending'],
                datasets: [{
                    data: [65, 25, 10],
                    backgroundColor: ['#10B981', '#F59E0B', '#E5E7EB'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '70%',
                plugins: { legend: { display: false } }
            }
        });
    }

    // Carregar configuração do schedule ao iniciar
    loadScheduleConfig();
});

async function loadScheduleConfig() {
    try {
        const res = await fetch('/api/schedule');
        const config = await res.json();

        document.getElementById('schedEnabled').checked = config.enabled || false;
        document.getElementById('schedInterval').value = config.interval || 60;
        document.getElementById('schedUnit').value = config.unit || 'minutes';
        document.getElementById('schedSubnet').value = config.subnet || '';
    } catch (e) {
        console.error('[SCHEDULE] Erro ao carregar configuração:', e);
    }
}

async function toggleSchedule() {
    const enabled = document.getElementById('schedEnabled').checked;

    if (enabled) {
        const subnet = document.getElementById('schedSubnet').value.trim();
        if (!subnet) {
            alert('Por favor, informe a subnet no campo acima antes de ativar o scan automático!');
            document.getElementById('schedEnabled').checked = false;
            document.getElementById('schedSubnet').focus();
            return;
        }
    }

    await saveScheduleConfig();
}

async function saveScheduleConfig() {
    const enabled = document.getElementById('schedEnabled').checked;
    const interval = parseInt(document.getElementById('schedInterval').value);
    const unit = document.getElementById('schedUnit').value;
    const subnet = document.getElementById('schedSubnet').value.trim();

    try {
        const res = await fetch('/api/schedule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled, interval, unit, subnet })
        });

        const data = await res.json();
        if (data.success) {
            console.log('[SCHEDULE] Configuração salva:', data.config);
            if (enabled && subnet) {
                console.log(`[SCHEDULE] Scan automático ativado: ${interval} ${unit} na subnet ${subnet}`);
            }
        }
    } catch (e) {
        console.error('[SCHEDULE] Erro ao salvar:', e);
        alert('Erro ao salvar configuração do scan automático!');
    }
}

function openModal(index) {
    const data = scanResults[index];
    if (!data) return;

    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = val || 'N/A';
    };

    const setHtml = (id, html) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = html;
    };

    setVal('mIpText', data.ip);
    setVal('mHostname', data.hostname);

    const heroIcon = document.getElementById('mHeroIcon');
    if (heroIcon) {
        let iconClass = 'ph-monitor';
        if (data.device_type.includes('printer')) iconClass = 'ph-printer';
        else if (data.device_type.includes('windows')) iconClass = 'ph-windows-logo';
        else if (data.device_type.includes('linux')) iconClass = 'ph-linux-logo';
        else if (data.device_type.includes('camera')) iconClass = 'ph-video-camera';
        else if (data.device_type.includes('router') || data.device_type.includes('switch')) iconClass = 'ph-network-base';
        heroIcon.innerHTML = `<i class="ph-fill ${iconClass}"></i>`;
        if (data.device_type.includes('printer')) heroIcon.style.color = 'var(--clr-printer)';
        else if (data.device_type.includes('windows')) heroIcon.style.color = 'var(--clr-windows)';
        else if (data.device_type.includes('linux')) heroIcon.style.color = 'var(--clr-linux)';
        else heroIcon.style.color = 'var(--primary)';
    }

    setVal('mVendor', data.vendor);
    setVal('mMac', data.mac);
    setVal('mType', data.device_type);
    setVal('mOs', data.os_detail);
    setVal('mModel', data.model);
    setVal('mUser', data.user);
    setVal('mRam', data.ram);
    setVal('mCpu', data.cpu);
    setVal('mUptime', data.uptime);
    setVal('mBios', data.bios);

    // New Fields
    setVal('mLocation', data.custom_location);
    setVal('mNotes', data.custom_notes);

    if (data.nics && data.nics.length > 0) {
        setHtml('mNics', data.nics.map(n => `
            <div class="nic-row-premium">
                <div class="nic-main">
                    <span class="nic-name">${n.description || 'Interface'}</span>
                    <span class="nic-meta">IP: ${n.ip || '-'} | Mask: ${n.subnet || '-'}</span>
                </div>
                <div class="nic-badge">GW: ${n.gateway || '-'}</div>
            </div>
        `).join(''));
    } else {
        setHtml('mNics', '<span style="color: var(--text-muted); font-size: 0.9rem;">Nenhuma interface detectada</span>');
    }

    if (data.services && data.services.length > 0) {
        setHtml('mServices', data.services.map(s => `<div>• ${s}</div>`).join(''));
    } else {
        setHtml('mServices', '<span style="font-size: 0.9rem;">Nenhum serviço parado encontrado</span>');
    }

    const printerSection = document.getElementById('mPrinterSection');
    if (printerSection) {
        if (data.printer_data) {
            printerSection.style.display = 'block';
            setVal('mPrinterSerial', data.printer_data.serial);
            const suppliesDiv = document.getElementById('mPrinterSupplies');
            if (suppliesDiv) {
                const validSupplies = (data.printer_data.supplies || []).filter(s =>
                    s.name && !s.name.includes("No Such Instance") && s.name !== "N/A"
                );
                if (validSupplies.length > 0) {
                    suppliesDiv.innerHTML = `<div class="supplies-grid-premium">` +
                        validSupplies.map(s => {
                            const level = parseInt(s.level);
                            let colorClass = '';
                            if (level < 15) colorClass = 'low';
                            else if (level < 40) colorClass = 'medium';
                            const isNumeric = !isNaN(level) && level >= 0;
                            const displayLevel = isNumeric ? `${level}%` : 'OK';
                            const barWidth = isNumeric ? level : 100;
                            return `
                            <div class="supply-item-premium">
                                <div class="supply-info">
                                    <span class="supply-name">${s.name}</span>
                                    <span>${displayLevel}</span>
                                </div>
                                <div class="supply-track">
                                    <div class="supply-bar ${colorClass}" style="width: ${barWidth}%"></div>
                                </div>
                            </div>`;
                        }).join('') + `</div>`;
                } else {
                    suppliesDiv.innerHTML = '<div class="no-data">Nenhum dado de suprimento disponível</div>';
                }
            }
        } else {
            printerSection.style.display = 'none';
        }
    }

    const errCont = document.getElementById('mErrorContainer');
    if (errCont) {
        if (data.errors && data.errors.length > 0) {
            errCont.style.display = 'flex';
            setHtml('mErrors', data.errors.map(e => `<div>${e}</div>`).join(''));
        } else {
            errCont.style.display = 'none';
        }
    }

    if (data.shares && data.shares.length > 0) {
        setHtml('mShares', data.shares.map(s => `<div class="pill-premium"><i class="ph ph-folder-open"></i> ${s}</div>`).join(''));
    } else {
        setHtml('mShares', '<span style="color: var(--text-muted); font-size: 0.9rem;">Nenhuma pasta compartilhada</span>');
    }

    if (data.disks && data.disks.length > 0) {
        setHtml('mDisks', data.disks.map(d => `<div class="pill-premium"><i class="ph ph-hard-drive"></i> ${d}</div>`).join(''));
    } else {
        setHtml('mDisks', '<span style="color: var(--text-muted); font-size: 0.9rem;">Nenhum disco detectado</span>');
    }

    const btnRdp = document.getElementById('btnRdp');
    if (btnRdp) {
        if (data.device_type && data.device_type.toLowerCase().includes('windows')) {
            btnRdp.style.display = 'flex';
        } else {
            btnRdp.style.display = 'none';
        }
    }

    // Reset Edit Mode on Open
    document.querySelectorAll('.edit-mode').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.view-mode').forEach(el => el.style.display = 'block');
    document.getElementById('btnEditDevice').style.display = 'flex';
    document.getElementById('btnSaveDevice').style.display = 'none';

    const overlay = document.getElementById('detailModal');
    if (!overlay) return;
    overlay.style.display = 'flex';
    setTimeout(() => overlay.classList.add('open'), 10);

    // Global ref to current
    window.currentDeviceIndex = index;
}

let isDeviceEditMode = false;
function toggleDeviceEdit() {
    isDeviceEditMode = !isDeviceEditMode;
    const viewEls = document.querySelectorAll('.view-mode');
    const editEls = document.querySelectorAll('.edit-mode');

    viewEls.forEach(el => el.style.display = isDeviceEditMode ? 'none' : 'block');
    editEls.forEach(el => el.style.display = isDeviceEditMode ? 'block' : 'none');

    document.getElementById('btnEditDevice').style.display = isDeviceEditMode ? 'none' : 'flex';
    document.getElementById('btnSaveDevice').style.display = isDeviceEditMode ? 'flex' : 'none';

    if (isDeviceEditMode) {
        const data = scanResults[window.currentDeviceIndex];
        document.getElementById('mEditHostname').value = data.hostname || '';
        document.getElementById('mEditLocation').value = data.custom_location || '';
        document.getElementById('mEditNotes').value = data.custom_notes || '';
        document.getElementById('mEditType').value = (data.device_type || 'network').split('_')[0]; // Simple matching
    }
}

async function saveDevice() {
    const data = scanResults[window.currentDeviceIndex];
    const updates = {
        ip: data.ip,
        hostname: document.getElementById('mEditHostname').value,
        device_type: document.getElementById('mEditType').value,
        custom_location: document.getElementById('mEditLocation').value,
        custom_notes: document.getElementById('mEditNotes').value
    };

    try {
        const res = await fetch('/api/scan/update-device', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });
        const respData = await res.json();

        if (respData.success) {
            alert('Dados atualizados!');
            // Update local state
            Object.assign(data, updates);
            // Refresh view
            toggleDeviceEdit();
            renderTable(scanResults);
            openModal(window.currentDeviceIndex);
        } else {
            alert('Erro: ' + respData.message);
        }
    } catch (e) { alert('Erro ao salvar'); }

}

document.addEventListener('DOMContentLoaded', () => {
    const tb = document.getElementById('tbResult');
    if (tb) {
        tb.addEventListener('click', (e) => {
            const tr = e.target.closest('tr');
            if (tr && tr.hasAttribute('data-index')) {
                const idx = parseInt(tr.getAttribute('data-index'));
                if (!isNaN(idx)) openModal(idx);
            }
        });
    }
});

function closeModal() {
    const overlay = document.getElementById('detailModal');
    overlay.classList.remove('open');
    setTimeout(() => { overlay.style.display = 'none'; }, 300);
}


let startTime = null;

async function startScan() {
    const sub = document.getElementById('subnet').value;
    const btn = document.getElementById('btnScan');
    if (btn) btn.disabled = true;

    // Resetar apenas o timer de métrica, mas MANTER os dados visuais na tela
    startTime = Date.now();

    // Não chamamos updateMetrics(0) aqui para não zerar os contadores visualmente antes da hora

    try {
        await fetch('/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subnet: sub })
        });
        if (timer) clearInterval(timer);
        timer = setInterval(poll, 1000);
    } catch (e) {
        console.error("Erro ao iniciar scan:", e);
        if (btn) btn.disabled = false;
        if (window.Notifier) window.Notifier.error('Erro de Inicialização', 'Não foi possível iniciar o scan. Verifique a conexão.', 5000);
    }
}

async function poll() {
    try {
        const req = await fetch('/status');
        const data = await req.json();
        const btn = document.getElementById('btnScan');
        const progressContainer = document.getElementById('scanProgressContainer');

        // Atualizar botão e visibilidade do progresso
        if (data.running) {
            if (btn) {
                btn.innerHTML = '<i class="ph-bold ph-spinner-gap anim-spin"></i> SCAN...';
                btn.classList.add('scanning');
                btn.disabled = true; // Botão travado durante scan
            }
            if (progressContainer) progressContainer.style.display = 'flex';
        } else {
            if (btn) {
                btn.innerHTML = '<i class="ph-bold ph-lightning"></i> SCAN';
                btn.classList.remove('scanning');
                btn.disabled = false;
            }
        }

        // Atualizar NOVA Barra de Progresso
        const progBar = document.getElementById('scanProgressBar');
        const progPercent = document.getElementById('progPercent');
        const progStatusText = document.getElementById('progStatusText');
        const progDetailText = document.getElementById('progDetailText');

        if (progBar) progBar.style.width = data.progress + "%";
        if (progPercent) progPercent.innerText = Math.round(data.progress) + "%";
        if (progStatusText) progStatusText.innerText = data.running ? "Mapeando rede..." : "Finalizado";
        if (progDetailText) progDetailText.innerText = `${data.results.length} dispositivos encontrados`;

        // Atualizar Métricas dos Cards
        updateMetrics(data.results.length, data.progress, data.running);

        // Atualizar Lista/Grid
        scanResults = data.results;
        applyCurrentSort();
        const searchVal = document.getElementById('smartSearch') ? document.getElementById('smartSearch').value : '';

        // Se não estiver digitando busca, atualiza a tabela
        if (!searchVal) renderTable(scanResults);

        // Parar timer se acabou e mostrar Toast
        if (!data.running && timer) {
            clearInterval(timer);
            timer = null;

            // Esconder barra após 1s
            setTimeout(() => {
                if (progressContainer) progressContainer.style.display = 'none';
            }, 1000);

            // Mostrar Notificação Robusta
            if (window.Notifier) {
                window.Notifier.success('Scan Finalizado', `Encontrados ${data.results.length} dispositivos na rede.`, 6000);
            }
        }
    } catch (e) {
        console.error("Erro no poll:", e);
    }
}

// Função showToast antiga removida em favor do Notifier System robusto

function updateMetrics(count, progress, isRunning) {
    // 1. Dispositivos Encontrados
    const stFound = document.getElementById('stFound');
    const stFoundChange = document.getElementById('stFoundChange');
    if (stFound) stFound.innerText = count;
    if (stFoundChange) {
        stFoundChange.innerText = isRunning ? "Buscando..." : `${count} total`;
        stFoundChange.className = isRunning ? "metric-change" : "metric-change positive";
    }

    // Cálculos de Tempo e Velocidade
    if (!startTime) return;
    const now = Date.now();
    const elapsedSeconds = (now - startTime) / 1000;

    // 2. Velocidade (IPs/s)
    const stSpeed = document.getElementById('stSpeed');
    if (stSpeed) {
        // Evitar divisão por zero e picos iniciais
        const speed = elapsedSeconds > 1 ? (count / elapsedSeconds).toFixed(1) : "0.0";
        stSpeed.innerText = speed;
    }

    // 3. Tempo Restante (ETR) e Decorrido
    const stEtr = document.getElementById('stEtr');
    const stElapsed = document.getElementById('stElapsed');

    if (stElapsed) {
        stElapsed.innerText = `Decorrido: ${formatTime(elapsedSeconds)}`;
    }

    if (stEtr) {
        if (progress > 0 && progress < 100) {
            const totalEstimatedTime = (elapsedSeconds * 100) / progress;
            const remaining = totalEstimatedTime - elapsedSeconds;
            stEtr.innerText = formatTime(remaining);
        } else if (progress >= 100) {
            stEtr.innerText = "0s";
        } else {
            stEtr.innerText = "--";
        }
    }

    // 4. Tempo Total / Status
    const stTotal = document.getElementById('stTotal');
    const stStatusBadge = document.getElementById('stStatusBadge');

    if (stTotal) stTotal.innerText = formatTime(elapsedSeconds);

    if (stStatusBadge) {
        if (isRunning) {
            stStatusBadge.innerText = "EM ANDAMENTO";
            stStatusBadge.className = "metric-status warning";
            stStatusBadge.style.background = "rgba(210, 153, 34, 0.1)";
            stStatusBadge.style.color = "#d29922";
        } else {
            stStatusBadge.innerText = "CONCLUÍDO";
            stStatusBadge.className = "metric-status success";
            stStatusBadge.style.background = "rgba(63, 185, 80, 0.1)";
            stStatusBadge.style.color = "#3fb950";
        }
    }
}

function formatTime(seconds) {
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}m ${s}s`;
}

function handleSearch() {
    const query = document.getElementById('smartSearch').value.toLowerCase().trim();
    if (!query) {
        renderTable(scanResults);
        return;
    }
    const tokens = query.split(/\s+/);
    const filtered = scanResults.filter(item => {
        const searchString = [
            item.ip, item.hostname, item.user, item.vendor,
            item.os_detail, item.model, item.device_type, item.mac
        ].join(' ').toLowerCase();
        return tokens.every(token => searchString.includes(token));
    });
    renderTable(filtered);
}

function getTypeInfo(type) {
    const t = (type || '').toLowerCase();
    if (t.includes('windows')) return { icon: 'ph-windows-logo', class: 'type-windows-pastel' };
    if (t.includes('linux')) return { icon: 'ph-linux-logo', class: 'type-linux-pastel' };
    if (t.includes('printer')) return { icon: 'ph-printer', class: 'type-printer-pastel' };
    if (t.includes('camera')) return { icon: 'ph-camera', class: 'type-camera-pastel' };
    if (t.includes('router') || t.includes('switch')) return { icon: 'ph-arrows-left-right', class: 'type-network-pastel' };
    return { icon: 'ph-question', class: 'type-unknown-pastel' };
}

function renderTable(results) {
    const listContainer = document.getElementById('resultsList');
    const gridContainer = document.getElementById('devicesGrid');

    if (!results || results.length === 0) {
        const emptyMsg = `<div style="grid-column: 1/-1; text-align:center; padding: 40px; color: #64748b;">Aguardando dados...</div>`;
        if (listContainer) listContainer.innerHTML = emptyMsg;
        if (gridContainer) gridContainer.innerHTML = emptyMsg;
        return;
    }

    // 1. Renderizar Lista
    if (listContainer) {
        let listHtml = '';
        results.forEach((d) => {
            const originalIndex = scanResults.findIndex(item => item.ip === d.ip);
            const typeInfo = getTypeInfo(d.device_type);
            const confidenceColor = d.confidence.includes('Alta') ? '#3fb950' : (d.confidence.toLowerCase().includes('méd') || d.confidence.toLowerCase().includes('med')) ? '#d29922' : '#f85149';

            listHtml += `
            <div class="list-card grid-scanner" onclick="openModal(${originalIndex})">
                <div class="scn-ip">${d.ip}</div>
                <div class="scn-host">${d.hostname || '-'}</div>
                <div class="scn-user">
                    ${d.user ? `<i class="ph-bold ph-user" style="font-size:0.8rem; margin-right:4px;"></i> ${d.user}` : '-'}
                </div>
                <div class="scn-oui">${d.vendor || '-'}</div>
                <div class="scn-sys" style="color: var(--text-main);">${d.os_detail || '-'} <small style="display:block; color: var(--text-muted); font-size:0.75rem;">${d.model || ''}</small></div>
                <div class="scn-type">
                    <span class="type-badge-pastel ${typeInfo.class}"><i class="ph-fill ${typeInfo.icon}"></i></span>
                </div>
                <div class="scn-trust">
                    <span class="conf-badge" style="font-weight:700; color:${confidenceColor}">${d.confidence}</span>
                </div>
                <div class="scn-last" style="font-size:0.75rem; color:#64748b;">${formatDate(d.last_updated_at)}</div>
            </div>`;
        });
        listContainer.innerHTML = listHtml;
    }

    // 2. Renderizar Cards (Grid - Unificado com style.css)
    if (gridContainer) {
        let gridHtml = '';
        results.forEach((d) => {
            const originalIndex = scanResults.findIndex(item => item.ip === d.ip);
            const deviceTypeClass = getDeviceTypeClass(d.device_type);
            const iconClass = getDeviceIcon(d.device_type);
            const confidenceBadge = getConfidenceBadge(d.confidence);
            const timestamp = formatTimestamp(d.last_updated_at);

            gridHtml += `
            <div class="device-card ${deviceTypeClass}" onclick="openModal(${originalIndex})">
                <span class="device-timestamp">${timestamp}</span>
                
                <div class="device-card-header">
                    <div class="device-icon">
                        <i class="${iconClass}"></i>
                    </div>
                    <div class="device-info">
                        <div class="device-ip">${d.ip}</div>
                        <div class="device-hostname">${d.hostname || 'N/A'}</div>
                    </div>
                </div>
                
                <div class="device-details">
                    ${d.user && d.user !== 'N/A' ? `
                    <div class="device-detail-row">
                        <i class="ph-fill ph-user"></i>
                        <span class="device-detail-label">Usuário:</span>
                        <span class="device-detail-value">${d.user}</span>
                    </div>
                    ` : ''}
                    
                    ${d.vendor && d.vendor !== '-' ? `
                    <div class="device-detail-row">
                        <i class="ph-fill ph-factory"></i>
                        <span class="device-detail-label">Fabricante:</span>
                        <span class="device-detail-value">${d.vendor}</span>
                    </div>
                    ` : ''}
                    
                    ${d.os_detail && d.os_detail !== 'N/A' ? `
                    <div class="device-detail-row">
                        <i class="ph-fill ph-desktop-tower"></i>
                        <span class="device-detail-label">Sistema:</span>
                        <span class="device-detail-value">${d.os_detail}</span>
                    </div>
                    ` : ''}
                    
                    <div class="device-detail-row">
                        <i class="ph-fill ph-shield-check"></i>
                        <span class="device-detail-label">Confiança:</span>
                        ${confidenceBadge}
                    </div>
                </div>
            </div>`;
        });
        gridContainer.innerHTML = gridHtml;
    }
}

function formatDate(isoString) {
    if (!isoString || isoString === 'N/A') return '-';
    // Tenta criar data, se falhar retorna '-'
    try {
        const d = new Date(isoString);
        if (isNaN(d.getTime())) return '-';
        return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
    } catch { return '-'; }
}

function getDeviceTypeClass(type) {
    if (!type) return 'network';
    if (type.includes('windows')) return 'windows';
    if (type.includes('printer')) return 'printer';
    if (type.includes('linux')) return 'linux';
    return 'network';
}

function getDeviceIcon(deviceType) {
    if (!deviceType) return 'ph-fill ph-devices';
    const type = deviceType.toLowerCase();
    if (type.includes('windows')) return 'ph-fill ph-windows-logo';
    if (type.includes('printer')) return 'ph-fill ph-printer';
    if (type.includes('linux')) return 'ph-fill ph-linux-logo';
    if (type.includes('server')) return 'ph-fill ph-hard-drives';
    if (type.includes('router') || type.includes('switch')) return 'ph-fill ph-router';
    if (type.includes('mobile') || type.includes('phone')) return 'ph-fill ph-device-mobile';
    return 'ph-fill ph-devices';
}

function getConfidenceBadge(confidence) {
    if (!confidence) return '<span class="device-badge low">Baixa</span>';
    const conf = confidence.toLowerCase();
    if (conf.includes('alta') || conf.includes('wmi')) {
        return '<span class="device-badge high">Alta</span>';
    } else if (conf.includes('méd') || conf.includes('media')) {
        return '<span class="device-badge medium">Média</span>';
    }
    return '<span class="device-badge low">Baixa</span>';
}

function formatTimestamp(timestamp) {
    if (!timestamp) return '--';
    try {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        if (diffMins < 1) return 'Agora';
        if (diffMins < 60) return `${diffMins}m atrás`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h atrás`;
        return date.toLocaleDateString('pt-BR');
    } catch {
        return '--';
    }
}

function applyCurrentSort() {
    // Placeholder function if sort logic is needed
}

let rdpSocket = null;
let currentRdpIp = null;

function startSeamlessRdp() {

    const ip = document.getElementById('mIpText').innerText;
    if (!ip || ip === '--') return;
    currentRdpIp = ip;

    // Carregar credenciais salvas se existirem
    const savedCreds = localStorage.getItem('rdp_credentials');
    if (savedCreds) {
        try {
            const creds = JSON.parse(savedCreds);
            document.getElementById('rdpUser').value = creds.username || '';
            document.getElementById('rdpPass').value = creds.password || '';
            document.getElementById('rdpDomain').value = creds.domain || '';
            document.getElementById('rdpSaveCreds').checked = true;
        } catch (e) {
            console.error('[RDP] Erro ao carregar credenciais salvas:', e);
        }
    }

    document.getElementById('rdpCredentialsModal').classList.add('active');
    document.getElementById('rdpUser').focus();
}

function closeRdpCreds() {
    document.getElementById('rdpCredentialsModal').classList.remove('active');
}

function confirmRdpCreds() {
    const user = document.getElementById('rdpUser').value;
    const pass = document.getElementById('rdpPass').value;
    const domain = document.getElementById('rdpDomain').value;
    const saveCreds = document.getElementById('rdpSaveCreds').checked;

    if (!user || !pass) return alert('Usuário e senha obrigatórios.');

    // Salvar credenciais se checkbox estiver marcado
    if (saveCreds) {
        const creds = {
            username: user,
            password: pass,
            domain: domain
        };
        localStorage.setItem('rdp_credentials', JSON.stringify(creds));
        console.log('[RDP] Credenciais salvas no navegador');
    } else {
        // Remover credenciais salvas se checkbox estiver desmarcado
        localStorage.removeItem('rdp_credentials');
        console.log('[RDP] Credenciais removidas do navegador');
    }

    closeRdpCreds();
    initiateRdpSession(currentRdpIp, user, pass, domain);
}

function initiateRdpSession(ip, user, pass, domain) {
    document.getElementById('modalMainBody').style.display = 'none';
    document.getElementById('rdpTheater').style.display = 'flex';
    document.getElementById('modalContainer').classList.add('rdp-active');
    document.getElementById('rdpStatusText').innerText = 'Conectando ao gateway...';

    const canvas = document.getElementById('rdpCanvas');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (rdpSocket) rdpSocket.disconnect();

    const gatewayUrl = `http://${window.location.hostname}:33890`;
    console.log('[RDP] Tentando conectar ao gateway em:', gatewayUrl);

    rdpSocket = io(gatewayUrl, {
        reconnection: true,
        reconnectionAttempts: 3,
        reconnectionDelay: 1000,
        transports: ['polling', 'websocket'], // Polling primeiro para estabilidade
        timeout: 10000,
        forceNew: true
    });

    rdpSocket.on('connect', () => {
        console.log('[RDP] ✓ Conectado ao gateway Socket.IO');
        document.getElementById('rdpStatusText').innerText = 'Negociando NLA...';
        rdpSocket.emit('init', { ip, username: user, password: pass, domain, width: 1280, height: 720 });
    });

    rdpSocket.on('rdp-connect', () => {
        console.log('[RDP] ✓ Sessão RDP estabelecida');
        document.getElementById('rdpStatusText').innerText = 'Ativo: ' + ip;
        canvas.width = 1280;
        canvas.height = 720;
    });

    rdpSocket.on('bitmap', (data) => {
        // Otimização: willReadFrequently para melhor performance
        const ctx = canvas.getContext('2d', { alpha: false, willReadFrequently: false });
        const pixels = new Uint8ClampedArray(data.data);

        try {
            const imageData = new ImageData(pixels, data.width, data.height);
            ctx.putImageData(imageData, data.x, data.y);
        } catch (e) {
            console.error('[RDP] Erro render:', e);
        }
    });

    rdpSocket.on('rdp-error', (msg) => {
        console.error('[RDP] ✗ Erro RDP:', msg);
        document.getElementById('rdpStatusText').innerText = 'Erro: ' + msg;
        alert('Erro RDP: ' + msg);
    });

    rdpSocket.on('rdp-closed', () => {
        console.log('[RDP] Sessão encerrada');
        document.getElementById('rdpStatusText').innerText = 'Sessão Encerrada';
    });

    rdpSocket.on('connect_error', (err) => {
        console.error('[RDP] ✗ Erro ao conectar no gateway:', err);
        document.getElementById('rdpStatusText').innerText = 'Falha: Gateway inacessível';
        alert('Não foi possível conectar ao gateway RDP na porta 33890.\n\nVerifique se o serviço está rodando:\nnode rdp-gateway.js');
    });

    rdpSocket.on('connect_timeout', () => {
        console.error('[RDP] ✗ Timeout ao conectar');
        document.getElementById('rdpStatusText').innerText = 'Timeout';
        alert('Timeout ao conectar no gateway RDP.');
    });

    // Otimização: Mouse throttle reduzido para 16ms (60 FPS) para melhor responsividade
    let lastMouseMove = 0;
    canvas.onmousedown = canvas.onmouseup = canvas.onmousemove = (e) => {
        if (!rdpSocket || !rdpSocket.connected) return;
        const now = Date.now();
        if (e.type === 'mousemove' && (now - lastMouseMove < 16)) return; // 60 FPS
        if (e.type === 'mousemove') lastMouseMove = now;

        const rect = canvas.getBoundingClientRect();
        const x = Math.round(e.offsetX * (1280 / rect.width));
        const y = Math.round(e.offsetY * (720 / rect.height));

        let button = 0;
        if (e.button === 0) button = 1;
        else if (e.button === 2) button = 2;

        rdpSocket.emit('mouse', { x, y, button, isDown: e.type !== 'mouseup' });
    };

    canvas.oncontextmenu = (e) => e.preventDefault();
}

function exitRdp() {
    if (rdpSocket) {
        rdpSocket.disconnect();
        rdpSocket = null;
    }
    document.getElementById('modalMainBody').style.display = 'block';
    document.getElementById('rdpTheater').style.display = 'none';
    document.getElementById('modalContainer').classList.remove('rdp-active');
}

function sendCtrlAltDel() {
    if (rdpSocket) {
        rdpSocket.emit('key', { scancode: 0x1d, isDown: true });
        rdpSocket.emit('key', { scancode: 0x38, isDown: true });
        rdpSocket.emit('key', { scancode: 0x53, isDown: true });
        setTimeout(() => {
            rdpSocket.emit('key', { scancode: 0x53, isDown: false });
            rdpSocket.emit('key', { scancode: 0x38, isDown: false });
            rdpSocket.emit('key', { scancode: 0x1d, isDown: false });
        }, 100);
    }
}

function toggleScale() {
    const canvas = document.getElementById('rdpCanvas');
    const btn = event.currentTarget;
    canvas.classList.toggle('scaled');
    btn.classList.toggle('active');
}

window.addEventListener('DOMContentLoaded', poll);

// === SORTING LOGIC ===
let currentSort = { field: 'ip', direction: 'asc' };

function ipToNum(ip) {
    if (!ip) return 0;
    return ip.split('.').reduce((acc, octet) => (acc << 8) + parseInt(octet, 10), 0) >>> 0;
}

function sortScanResults(field, toggle = true) {
    // 1. Update State
    if (toggle) {
        if (currentSort.field === field) {
            currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            currentSort.field = field;
            currentSort.direction = 'asc';
        }
    }

    // 2. Sort
    scanResults.sort((a, b) => {
        let valA, valB;
        switch (field) {
            case 'ip': valA = ipToNum(a.ip); valB = ipToNum(b.ip); break;
            case 'hostname': valA = (a.hostname || '').toLowerCase(); valB = (b.hostname || '').toLowerCase(); break;
            case 'user': valA = (a.user || '').toLowerCase(); valB = (b.user || '').toLowerCase(); break;
            case 'vendor': valA = (a.vendor || '').toLowerCase(); valB = (b.vendor || '').toLowerCase(); break;
            case 'os': valA = (a.os_detail || '').toLowerCase(); valB = (b.os_detail || '').toLowerCase(); break;
            case 'type': valA = (a.device_type || '').toLowerCase(); valB = (b.device_type || '').toLowerCase(); break;
            case 'confidence': valA = (a.confidence || '').toLowerCase(); valB = (b.confidence || '').toLowerCase(); break;
            case 'date': valA = new Date(a.last_updated_at || 0); valB = new Date(b.last_updated_at || 0); break;
            default: return 0;
        }

        if (valA < valB) return currentSort.direction === 'asc' ? -1 : 1;
        if (valA > valB) return currentSort.direction === 'asc' ? 1 : -1;
        return 0;
    });

    // 3. UI Helper
    updateSortIcons();

    // 4. Render
    renderTable(scanResults);
}

function applyCurrentSort() {
    sortScanResults(currentSort.field, false);
}

function updateSortIcons() {
    document.querySelectorAll('.list-header-item.sortable').forEach(el => {
        el.classList.remove('active');
        const icon = el.querySelector('i');
        if (icon) icon.className = 'ph-bold ph-caret-up-down';
    });

    const activeHeader = document.querySelector(`.list-header-item[onclick*="'${currentSort.field}'"]`);
    if (activeHeader) {
        activeHeader.classList.add('active');
        const icon = activeHeader.querySelector('i');
        if (icon) icon.className = currentSort.direction === 'asc' ? 'ph-bold ph-caret-down' : 'ph-bold ph-caret-up';
    }
}
