import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
    Binoculars, Play, Stop, Desktop, Printer, Globe, Camera, HardDrives,
    ChartLineUp, Clock, MagnifyingGlass, List, SquaresFour, X,
    Broadcast, IdentificationCard, Terminal, Pulse,
    PlusCircle, ArrowsClockwise, TerminalWindow
} from '@phosphor-icons/react'
import api from '../services/api'
import type { ScanStatus, Device } from '../types'

// Helper component for info rows to match ADUsers style
const InfoRow = ({ label, value }: { label: string, value?: string }) => (
    <div>
        <div className="text-[10px] text-dark-muted uppercase tracking-wider font-bold mb-1">{label}</div>
        <div className="text-sm font-semibold text-white">{value || '-'}</div>
    </div>
)

const Scanner = () => {
    const [subnet, setSubnet] = useState('172.23.51.0/24')
    const [selectedDevice, setSelectedDevice] = useState<Device | null>(null)
    const [position, setPosition] = useState({ x: 0, y: 0 })
    const [isDragging, setIsDragging] = useState(false)
    const dragStart = useRef({ x: 0, y: 0 })
    const queryClient = useQueryClient()

    const [activeModalTab, setActiveModalTab] = useState<'info' | 'diag'>('info')
    const [pingResult, setPingResult] = useState<string>('')
    const [searchQuery, setSearchQuery] = useState('')

    // Monitoring State
    const [showMonitorMenu, setShowMonitorMenu] = useState(false)
    const [isMonitoring, setIsMonitoring] = useState(false)
    const [monitorConfig, setMonitorConfig] = useState({ h: 0, m: 0, s: 10 })
    const [monitorTimeLeft, setMonitorTimeLeft] = useState(0)

    // Monitoring Effect
    useEffect(() => {
        let interval: any = null
        if (isMonitoring && selectedDevice) {
            interval = setInterval(() => {
                setMonitorTimeLeft(prev => {
                    if (prev <= 1) {
                        refreshDeviceMutation.mutate(selectedDevice.ip)
                        const totalSec = (Number(monitorConfig.h) * 3600) + (Number(monitorConfig.m) * 60) + Number(monitorConfig.s)
                        return totalSec > 5 ? totalSec : 5
                    }
                    return prev - 1
                })
            }, 1000)
        }
        return () => clearInterval(interval)
    }, [isMonitoring, monitorConfig]) // Removed selectedDevice/timeLeft to avoid re-subscription loop

    // Reset monitoring when closing modal
    useEffect(() => {
        if (!selectedDevice) {
            setIsMonitoring(false)
            setShowMonitorMenu(false)
        }
    }, [selectedDevice])

    const pingMutation = useMutation({
        mutationFn: (ip: string) => api.post('/api/scanner/diagnostics/ping', { ip }),
        onSuccess: (res) => {
            if (res.data.success) {
                setPingResult(res.data.output || 'Resposta OK (Sem output)')
            } else {
                setPingResult(`Erro: ${res.data.message} `)
            }
        },
        onError: (err: any) => {
            setPingResult(`Falha na requisição: ${err.message} `)
        }
    })

    const refreshDeviceMutation = useMutation({
        mutationFn: (ip: string) => api.post('/api/scan/individual', { ip }),
        onSuccess: (res) => {
            if (res.data.success) {
                // Update selected device immediately with fresh data
                setSelectedDevice(res.data.data)
                // Also refresh main list
                queryClient.invalidateQueries({ queryKey: ['scanner-results'] })
            }
        }
    })

    // Reset position when modal closes/opens
    useEffect(() => {
        if (!selectedDevice) {
            setPosition({ x: 0, y: 0 })
            setActiveModalTab('info')
            setPingResult('')
        }
    }, [selectedDevice])

    useEffect(() => {
        if (!isDragging) return

        const handleMouseMove = (e: MouseEvent) => {
            const dx = e.clientX - dragStart.current.x
            const dy = e.clientY - dragStart.current.y
            setPosition({ x: dx, y: dy })
        }

        const handleMouseUp = () => {
            setIsDragging(false)
            document.body.style.cursor = 'default'
        }

        window.addEventListener('mousemove', handleMouseMove)
        window.addEventListener('mouseup', handleMouseUp)
        return () => {
            window.removeEventListener('mousemove', handleMouseMove)
            window.removeEventListener('mouseup', handleMouseUp)
        }
    }, [isDragging])

    const startDragging = (e: React.MouseEvent) => {
        if ((e.target as HTMLElement).closest('button')) return
        e.preventDefault()
        setIsDragging(true)
        dragStart.current = {
            x: e.clientX - position.x,
            y: e.clientY - position.y
        }
        document.body.style.cursor = 'grabbing'
    }

    // Status do Scan
    const [viewMode, setViewMode] = useState<'list' | 'cards'>(() => {
        return (localStorage.getItem('scannerViewMode') as 'list' | 'cards') || 'list'
    })

    const toggleViewMode = (mode: 'list' | 'cards') => {
        setViewMode(mode)
        localStorage.setItem('scannerViewMode', mode)
    }

    const { data: status } = useQuery<ScanStatus>({
        queryKey: ['scanner-status'],
        queryFn: async () => {
            const response = await api.get('/api/scanner/status')
            return response.data
        },
        refetchInterval: 1000,
    })

    // Resultados do Scan
    const { data: devices } = useQuery<Device[]>({
        queryKey: ['scanner-results'],
        queryFn: async () => {
            const response = await api.get('/api/scanner/results')
            return response.data
        },
        refetchInterval: 2000,
    })

    const startScan = useMutation({
        mutationFn: () => api.post('/api/scanner/start', { subnet }),
        onSuccess: () => {
            // Optimistic update to show dashboard immediately
            queryClient.setQueryData(['scanner-status'], (old: any) => ({
                ...old,
                running: true,
                logs: [{ msg: "Iniciando Sentinel Engine...", time: new Date().toLocaleTimeString() }],
                results: []
            }))
            queryClient.invalidateQueries({ queryKey: ['scanner-status'] })
            queryClient.invalidateQueries({ queryKey: ['scanner-results'] })
        },
    })

    const stopScan = useMutation({
        mutationFn: () => api.post('/api/scanner/stop'),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scanner-status'] }),
    })

    const isRecent = (lastSeen?: string) => {
        if (!lastSeen) return false;
        try {
            const lastSeenDate = new Date(lastSeen);
            const now = new Date();
            const diffInHours = (now.getTime() - lastSeenDate.getTime()) / (1000 * 60 * 60);
            return diffInHours < 2;
        } catch (e) {
            return false;
        }
    }

    const getDeviceIcon = (type: string) => {
        switch (type?.toLowerCase()) {
            case 'windows': return <Desktop size={24} weight="fill" className="text-status-info" />
            case 'printer': return <Printer size={24} weight="fill" className="text-status-success" />
            case 'network': return <Globe size={24} weight="fill" className="text-status-update" />
            case 'camera': return <Camera size={24} weight="fill" className="text-status-error" />
            case 'server': return <HardDrives size={24} weight="fill" className="text-indigo-400" />
            default: return <Desktop size={24} weight="fill" className="text-gray-400" />
        }
    }

    // Awareness of scan completion
    useEffect(() => {
        if (!status?.running && status?.etr === "Concluído") {
            queryClient.invalidateQueries({ queryKey: ['scanner-results'] })
        }
    }, [status?.running, status?.etr])

    // Auto-scroll console with a slight delay for DOM sync
    useEffect(() => {
        if (status?.running || status?.etr === "Concluído") {
            const timer = setTimeout(() => {
                const bottom = document.getElementById('scan-console-bottom')
                if (bottom) {
                    bottom.scrollIntoView({ behavior: 'smooth', block: 'end' })
                }
            }, 100)
            return () => clearTimeout(timer)
        }
    }, [status?.logs?.length, status?.running, status?.etr])

    const getDeviceTypeLabel = (type?: string) => {
        if (!type) return ''
        const t = type.toLowerCase()
        if (t === 'printer') return 'impressora'
        if (t === 'windows' || t === 'desktop') return 'computador pc windows'
        if (t === 'server') return 'servidor'
        if (t === 'camera') return 'chat câmera ip'
        if (t === 'network') return 'rede switch roteador'
        return t
    }

    // Filter devices based on search query
    const filteredDevices = devices?.filter(device => {
        if (!searchQuery) return true
        const q = searchQuery.toLowerCase()

        // Search in raw fields
        if (device.hostname?.toLowerCase().includes(q)) return true
        if (device.ip?.includes(q)) return true
        if (device.vendor?.toLowerCase().includes(q)) return true
        if (device.os_detail?.toLowerCase().includes(q)) return true
        if (device.device_type?.toLowerCase().includes(q)) return true
        if (device.printer_data?.model?.toLowerCase().includes(q)) return true

        // Search in translated/smart type
        if (getDeviceTypeLabel(device.device_type).includes(q)) return true

        return false
    })

    return (
        <div className="page-transition space-y-8 pb-10">
            {/* Page Header */}
            <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-6">
                <div className="space-y-1">
                    <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
                        <Binoculars size={32} className="text-primary" />
                        Scanner de Rede
                    </h1>
                    <p className="text-gray-400 font-medium text-sm md:text-base">Escaneie e identifique ativos na sua rede local</p>
                </div>

                {/* Pill Control Bar */}
                <div className="bg-dark-panel p-2 rounded-2xl md:rounded-full border border-dark-border shadow-2xl flex flex-col md:flex-row items-stretch md:items-center gap-2 w-full xl:w-auto xl:min-w-[400px]">
                    <div className="flex-1 flex items-center gap-3 px-4 py-3 md:py-2 bg-dark-bg rounded-xl md:rounded-full border border-white/5 focus-within:border-primary/50 transition-all">
                        <Globe size={18} className="text-primary" />
                        <input
                            type="text"
                            value={subnet}
                            onChange={(e) => setSubnet(e.target.value)}
                            placeholder="Ex: 192.168.1.0/24"
                            className="bg-transparent border-none text-white font-bold text-sm focus:ring-0 w-full placeholder:text-gray-600"
                        />
                    </div>
                    {status?.running ? (
                        <button
                            onClick={() => stopScan.mutate()}
                            className="bg-red-500 hover:bg-red-600 text-white p-3 rounded-xl md:rounded-full transition-all shadow-lg shadow-red-500/20 active:scale-95 flex justify-center items-center"
                        >
                            <Stop size={20} weight="fill" />
                            <span className="md:hidden ml-2 font-bold text-xs uppercase">Parar</span>
                        </button>
                    ) : (
                        <button
                            onClick={() => startScan.mutate()}
                            disabled={!subnet}
                            className="bg-primary hover:bg-primary-dark text-white px-6 py-3 md:py-2.5 rounded-xl md:rounded-full font-bold text-sm transition-all shadow-lg shadow-primary/20 flex items-center justify-center gap-2 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                        >
                            <Play size={18} weight="fill" />
                            SCAN
                        </button>
                    )}
                </div>
            </div>

            {/* Scan Progress Dashboard - Mission Control Style */}
            {(status?.running || status?.etr === "Concluído") && (
                <div className={`bg - dark - panel p - 8 rounded - 3xl border ${status?.etr === 'Concluído' ? 'border-status-success/30' : 'border-dark-border'} shadow - 2xl animate -in zoom -in duration - 300 relative overflow - hidden flex flex - col gap - 8`}>
                    <div className={`absolute top - 0 left - 0 w - full h - 1 bg - gradient - to - r ${status?.etr === 'Concluído' ? 'from-status-success via-emerald-400 to-status-success' : 'from-primary via-indigo-500 to-primary animate-pulse'} `}></div>

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                        {/* Stats & Progress */}
                        <div className="lg:col-span-5 space-y-6">
                            <div className="flex items-center gap-5">
                                <div className="p-5 bg-primary rounded-[24px] text-white shadow-2xl shadow-primary/30">
                                    <ChartLineUp size={40} weight="fill" />
                                </div>
                                <div>
                                    <h3 className="text-4xl font-black text-white tracking-tighter">{status.progress}%</h3>
                                    <p className="text-[10px] uppercase font-black text-gray-500 tracking-[0.2em]">Processamento Sentinel</p>
                                </div>
                            </div>

                            <div className="space-y-3">
                                <div className="flex justify-between text-[10px] font-black uppercase text-gray-500 tracking-widest px-1">
                                    <span className="flex items-center gap-2">
                                        <div className="w-1.5 h-1.5 rounded-full bg-primary animate-ping"></div>
                                        Fase: Auditoria de Ativos
                                    </span>
                                    <span>{status.scanned_ips} / {status.total_ips} IPs</span>
                                </div>
                                <div className="h-4 bg-dark-bg rounded-full border border-white/5 overflow-hidden p-0.5">
                                    <div
                                        className="h-full bg-gradient-to-r from-primary via-indigo-400 to-primary shadow-[0_0_20px_rgba(129,140,248,0.4)] transition-all duration-700 rounded-full relative"
                                        style={{ width: `${status.progress}% ` }}
                                    >
                                        <div className="absolute inset-0 bg-[linear-gradient(45deg,rgba(255,255,255,0.2)_25%,transparent_25%,transparent_50%,rgba(255,255,255,0.2)_50%,rgba(255,255,255,0.2)_75%,transparent_75%,transparent)] bg-[length:20px_20px] animate-[progress-stripe_1s_linear_infinite]"></div>
                                    </div>
                                </div>
                            </div>

                            <div className="grid grid-cols-3 gap-4 pt-4">
                                <div className="bg-dark-bg/40 p-3 rounded-2xl border border-white/5">
                                    <div className="text-[9px] font-black text-gray-500 uppercase mb-1">E.T.R</div>
                                    <div className="text-sm font-bold text-white flex items-center gap-1.5">
                                        <Clock size={14} className="text-primary" />
                                        {status.etr}
                                    </div>
                                </div>
                                <div className="bg-dark-bg/40 p-3 rounded-2xl border border-white/5">
                                    <div className="text-[9px] font-black text-status-success uppercase mb-1">Novos</div>
                                    <div className="text-sm font-bold text-white flex items-center gap-1.5">
                                        <PlusCircle size={14} />
                                        {status.last_results?.added || 0}
                                    </div>
                                </div>
                                <div className="bg-dark-bg/40 p-3 rounded-2xl border border-white/5">
                                    <div className="text-[9px] font-black text-status-info uppercase mb-1">Atualizados</div>
                                    <div className="text-sm font-bold text-white flex items-center gap-1.5">
                                        <ArrowsClockwise size={14} />
                                        {status.last_results?.updated || 0}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Live Terminal Console */}
                        <div className="lg:col-span-7 bg-black/40 rounded-[24px] border border-white/10 p-5 flex flex-col gap-3 font-mono shadow-inner min-h-[220px]">
                            <div className="flex items-center justify-between border-b border-white/5 pb-2">
                                <div className="flex items-center gap-2">
                                    <Terminal size={14} className="text-gray-500" />
                                    <span className="text-[10px] uppercase font-black text-gray-500 tracking-widest">Live Scan Console</span>
                                </div>
                                <div className="flex gap-1.5">
                                    <div className="w-2 h-2 rounded-full bg-red-500/20"></div>
                                    <div className="w-2 h-2 rounded-full bg-amber-500/20"></div>
                                    <div className="w-2 h-2 rounded-full bg-emerald-500/20"></div>
                                </div>
                            </div>

                            <div className="flex-1 overflow-y-auto custom-scrollbar space-y-1.5 max-h-[140px] text-[11px]">
                                {status.logs?.map((log, i) => {
                                    const msg = String(log.msg || '');
                                    const isNew = msg.includes('Novo') || msg.includes('mapeado');
                                    const isError = msg.includes('Falha') || msg.includes('Nenhum') || msg.includes('ERRO') || msg.includes('CRITICAL');
                                    const isAudit = msg.startsWith('Auditado');

                                    return (
                                        <div key={i} className="flex gap-3 animate-in slide-in-from-left-2 fade-in duration-300">
                                            <span className="text-gray-600 shrink-0 select-none">[{log.time || '--:--:--'}]</span>
                                            <span className={
                                                isNew ? 'text-emerald-400 font-bold' :
                                                    isError ? 'text-red-400' :
                                                        isAudit ? 'text-zinc-300' : 'text-zinc-400'
                                            }>
                                                {isAudit ? '> ' : isNew ? '+ ' : ''}{msg}
                                            </span>
                                        </div>
                                    );
                                })}
                                {(!status.logs || status.logs.length === 0) && (
                                    <div className="flex flex-col gap-2 py-4 animate-pulse">
                                        <div className="flex items-center gap-2 text-zinc-600 italic">
                                            <div className="w-1.5 h-1.5 rounded-full bg-primary animate-ping"></div>
                                            Sincronizando com Sentinel Engine...
                                        </div>
                                        <p className="text-[10px] text-zinc-700 ml-4 font-mono">
                                            [Status: {status.etr || 'Aguardando'}] - Conectando ao subsistema de Auditoria
                                        </p>
                                    </div>
                                )}
                                <div id="scan-console-bottom"></div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Results Header & View Toggle */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pt-4 border-t border-dark-border/30">
                <div className="flex-1 flex items-center gap-4">
                    <div className="relative group w-full md:max-w-md">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <MagnifyingGlass size={16} className="text-gray-500 group-focus-within:text-primary transition-colors" />
                        </div>
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Buscar por nome, IP, fabricante..."
                            className="bg-dark-surface/50 backdrop-blur-md border border-white/10 text-white text-sm rounded-full focus:ring-2 focus:ring-primary/50 focus:border-primary/50 block w-full pl-10 p-2.5 placeholder:text-gray-500 transition-all shadow-lg hover:bg-dark-surface/80"
                        />
                    </div>
                    <div className="hidden md:block">
                        <div className="text-[10px] text-gray-500 uppercase font-black tracking-widest bg-dark-surface/50 px-4 py-2 rounded-full border border-white/5">
                            {filteredDevices?.length || 0} de {devices?.length || 0} Ativos
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className="bg-dark-surface p-1 rounded-xl border border-dark-border flex items-center gap-1 shadow-inner">
                        <button
                            onClick={() => toggleViewMode('list')}
                            className={`p - 2 rounded - lg transition - all ${viewMode === 'list' ? 'bg-primary text-white shadow-lg' : 'text-dark-muted hover:text-white'} `}
                            title="Lista Detalhada"
                        >
                            <List size={18} weight={viewMode === 'list' ? 'fill' : 'regular'} />
                        </button>
                        <button
                            onClick={() => toggleViewMode('cards')}
                            className={`p - 2 rounded - lg transition - all ${viewMode === 'cards' ? 'bg-primary text-white shadow-lg' : 'text-dark-muted hover:text-white'} `}
                            title="Grade de Cards"
                        >
                            <SquaresFour size={18} weight={viewMode === 'cards' ? 'fill' : 'regular'} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Results Display */}
            {viewMode === 'list' ? (
                <div className="bg-dark-panel rounded-3xl border border-dark-border shadow-2xl min-h-[400px]">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-dark-bg/50 text-[11px] uppercase font-black text-gray-500 tracking-widest border-b border-dark-border">
                                    <th className="px-8 py-5 min-w-[200px]">Dispositivo</th>
                                    <th className="px-6 py-5 min-w-[140px]">Endereço IP</th>
                                    <th className="px-6 py-5 min-w-[180px]">Fabricante / MAC</th>
                                    <th className="px-6 py-5 min-w-[180px]">Sistema / SO</th>
                                    <th className="px-6 py-5 text-center min-w-[130px]">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-dark-border/40">
                                {filteredDevices?.map((device, idx) => (
                                    <tr
                                        key={idx}
                                        onClick={() => setSelectedDevice(device)}
                                        className="hover:bg-white/5 transition-all group cursor-pointer active:bg-white/10"
                                    >
                                        <td className="px-8 py-6">
                                            <div className="flex items-center gap-4">
                                                <div className="p-3 bg-dark-bg rounded-xl border border-white/5 group-hover:border-primary/20 transition-all">
                                                    {getDeviceIcon(device.device_type)}
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <div className="flex items-center gap-2">
                                                        <div className="text-sm font-bold text-gray-100 truncate group-hover:text-primary transition-colors">
                                                            {device.hostname || 'Unknown Host'}
                                                        </div>
                                                        {device.scan_type === 'new' && (
                                                            <span className="shrink-0 bg-emerald-500 text-white text-[8px] font-black px-2 py-0.5 rounded shadow-[0_2px_10px_rgba(16,185,129,0.4)]">
                                                                NOVO
                                                            </span>
                                                        )}
                                                        {device.scan_type === 'updated' && (
                                                            <span className="shrink-0 bg-blue-500 text-white text-[8px] font-black px-2 py-0.5 rounded shadow-[0_2px_10px_rgba(59,130,246,0.4)] text-nowrap">
                                                                ATUALIZADO
                                                            </span>
                                                        )}
                                                        {isRecent(device.last_seen) && (
                                                            <span className="shrink-0 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[9px] font-black px-1.5 py-0.5 rounded-md shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                                                                2H
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-tighter">
                                                        {device.device_type || 'Dispositivo de Rede'}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-6">
                                            <span className="text-sm font-mono font-bold text-primary bg-primary/5 px-2 py-1 rounded">
                                                {device.ip}
                                            </span>
                                        </td>
                                        <td className="px-6 py-6 font-medium text-gray-300">
                                            <div className="text-sm">{device.vendor || 'Generic'}</div>
                                            <div className="text-[10px] text-gray-500 font-mono tracking-tighter">{device.mac || '-'}</div>
                                        </td>
                                        <td className="px-6 py-6 font-medium text-gray-400 text-xs">
                                            {device.os_detail || 'N/A'}
                                        </td>
                                        <td className="px-6 py-6">
                                            <div className="flex justify-center">
                                                <span className={`px-4 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest border transition-all duration-300 ${device.status_code === 'ONLINE'
                                                    ? 'bg-status-success/20 text-status-success border-status-success/40 shadow-[0_0_15px_rgba(16,185,129,0.15)]'
                                                    : 'bg-status-error/20 text-status-error border-status-error/40 shadow-[0_0_15px_rgba(239,68,68,0.15)]'
                                                    }`}>
                                                    {device.status_code}
                                                </span>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 animate-in fade-in duration-500">
                    {filteredDevices?.map((device, idx) => (
                        <div
                            key={idx}
                            onClick={() => setSelectedDevice(device)}
                            className="relative bg-white/[0.03] backdrop-blur-md p-6 rounded-[24px] border border-white/10 hover:border-primary/40 hover:bg-white/[0.05] transition-all group flex flex-col items-center text-center space-y-4 shadow-xl cursor-pointer active:scale-95"
                        >
                            {/* NEW/UPDATE Status Badge */}
                            {device.scan_type && (
                                <div className="absolute top-4 right-4 z-20">
                                    <span className={`text-[9px] font-black px-3 py-1 rounded-full uppercase tracking-tighter shadow-[0_4px_12px_rgba(0,0,0,0.5)] border border-white/10 ${device.scan_type === 'new'
                                        ? 'bg-emerald-500 text-white shadow-emerald-500/40 animate-in zoom-in duration-300'
                                        : 'bg-blue-500 text-white shadow-blue-500/40 animate-in zoom-in duration-300'
                                        }`}>
                                        {device.scan_type === 'new' ? 'NEW' : 'UPDATED'}
                                    </span>
                                </div>
                            )}
                            {/* Icon & Status */}
                            <div className="relative">
                                <div className="w-16 h-16 rounded-2xl bg-dark-bg border border-white/5 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform">
                                    {getDeviceIcon(device.device_type)}
                                </div>
                                <div className={`absolute -top-1 -right-1 w-4 h-4 rounded-full border-2 border-dark-panel ${device.status_code === 'ONLINE' ? 'bg-status-success animate-pulse' : 'bg-status-error'
                                    }`}></div>
                            </div>

                            {/* Info */}
                            <div className="space-y-1 w-full overflow-hidden">
                                <h3 className="font-bold text-gray-100 truncate text-sm" title={device.hostname || 'Unknown Host'}>
                                    {device.hostname || 'Unknown Host'}
                                </h3>
                                <p className="text-[10px] text-gray-500 font-black uppercase tracking-widest">
                                    {device.device_type || 'Dispositivo'}
                                </p>
                            </div>

                            {/* IP Badge */}
                            <div className="w-full bg-dark-bg/60 p-3 rounded-2xl border border-white/5 flex items-center justify-between gap-2 overflow-hidden">
                                <span className="text-xs font-mono font-bold text-primary truncate">{device.ip}</span>
                                {isRecent(device.last_seen) && (
                                    <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[7px] font-black px-1.5 py-0.5 rounded shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                                        2H
                                    </span>
                                )}
                            </div>

                            {/* Secondary Info */}
                            <div className="w-full pt-4 border-t border-white/5 grid grid-cols-1 gap-2">
                                <div className="text-[10px] text-gray-500 font-medium truncate">
                                    {device.vendor || 'Fabricante Genérico'}
                                </div>
                                <div className="text-[9px] text-gray-600 font-mono italic">
                                    {device.mac || 'MAC Indisponível'}
                                </div>
                            </div>

                            {/* OS Pill (Conditional) */}
                            {device.os_detail && (
                                <div className="text-[9px] bg-white/5 px-3 py-1 rounded-full text-gray-400 font-bold truncate w-full">
                                    {device.os_detail}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {!filteredDevices?.length && (
                <div className="bg-dark-panel rounded-3xl border border-dark-border p-20 text-center flex flex-col items-center gap-6">
                    <div className="p-6 bg-dark-bg rounded-3xl opacity-20">
                        <Binoculars size={80} weight="thin" className="text-gray-500" />
                    </div>
                    <div className="space-y-1">
                        <p className="font-black text-sm uppercase tracking-[0.3em] text-gray-500 italic">
                            {searchQuery ? 'Nenhum resultado encontrado' : 'Rede em silêncio'}
                        </p>
                        <p className="text-[10px] text-gray-600 uppercase font-black">
                            {searchQuery ? `Não encontramos nada para "${searchQuery}"` : 'Nenhum dispositivo encontrado nesta varredura'}
                        </p>
                    </div>
                </div>
            )}

            {/* --- Device Details Modal - COMPACT APPLE GLASS --- */}
            {selectedDevice && (
                <div
                    className="fixed inset-0 bg-black/20 flex items-center justify-center z-[110] p-4"
                    onClick={() => setSelectedDevice(null)}
                >
                    <div
                        className={`relative bg-zinc-950/85 backdrop-blur-2xl backdrop-saturate-[150%] border border-white/10 rounded-[32px] max-w-xl w-full max-h-[90vh] shadow-[0_32px_128px_-20px_rgba(0,0,0,0.7)] flex flex-col overflow-hidden select-none transition-shadow ${isDragging ? 'shadow-white/5 ring-1 ring-white/10' : ''}`}
                        style={{
                            backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0) 100%)',
                            transform: `translate(${position.x}px, ${position.y}px)`,
                            transition: isDragging ? 'none' : 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), shadow 0.3s ease, opacity 0.3s ease'
                        }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Header - Advanced Apple Glass */}
                        <div
                            onMouseDown={startDragging}
                            className="sticky top-0 bg-white/[0.04] backdrop-blur-3xl border-b border-white/5 px-8 py-8 flex items-center justify-between z-20 cursor-grab active:cursor-grabbing"
                        >
                            <div className="flex items-center gap-6">
                                <div className={`w-16 h-16 rounded-[20px] bg-gradient-to-br border flex items-center justify-center shadow-2xl transition-all ${selectedDevice.status_code === 'ONLINE'
                                    ? 'from-primary/40 to-primary/10 border-primary/40 text-primary shadow-primary/20'
                                    : 'from-zinc-600/40 to-zinc-600/10 border-zinc-600/40 text-zinc-400'
                                    }`}>
                                    {getDeviceIcon(selectedDevice.device_type)}
                                </div>
                                <div className="space-y-2">
                                    <h2 className="text-2xl font-black text-white tracking-tight leading-tight flex items-center gap-4">
                                        {selectedDevice.hostname || 'Ativo Desconhecido'}
                                        <div className="flex gap-2">
                                            {selectedDevice.scan_type === 'new' && (
                                                <span className="bg-emerald-500 text-white text-[9px] font-black px-2.5 py-0.5 rounded-md shadow-lg uppercase tracking-widest">
                                                    NOVO
                                                </span>
                                            )}
                                            {selectedDevice.scan_type === 'updated' && (
                                                <span className="bg-blue-500 text-white text-[9px] font-black px-2.5 py-0.5 rounded-md shadow-lg uppercase tracking-widest">
                                                    UPDATE
                                                </span>
                                            )}
                                        </div>
                                    </h2>
                                    <div className="flex items-center gap-4">
                                        <span className="bg-primary/20 text-primary-light px-2.5 py-1 rounded-lg text-[10px] font-mono font-black border border-primary/20 tracking-wider">
                                            {selectedDevice.ip}
                                        </span>
                                        <div className="w-1 h-1 rounded-full bg-zinc-700"></div>
                                        <p className="text-[11px] text-zinc-500 font-black uppercase tracking-[0.2em] opacity-80">
                                            {selectedDevice.device_type || 'Internal Node'}
                                        </p>
                                    </div>
                                </div>
                            </div>
                            <button
                                onClick={() => setSelectedDevice(null)}
                                className="w-10 h-10 flex items-center justify-center rounded-full bg-white/5 hover:bg-red-500/20 text-zinc-500 hover:text-red-500 border border-white/10 hover:border-red-500/30 transition-all active:scale-90 group"
                            >
                                <X size={18} weight="bold" className="group-hover:rotate-90 transition-transform duration-300" />
                            </button>
                        </div>

                        {/* Multi-Tab Navigation - Center Weighted */}
                        <div className="flex justify-center border-b border-white/5 bg-white/[0.01]">
                            <div className="flex gap-20">
                                <button
                                    onClick={() => setActiveModalTab('info')}
                                    className={`py-6 text-[11px] font-black uppercase tracking-[0.3em] transition-all relative group ${activeModalTab === 'info' ? 'text-primary' : 'text-zinc-500 hover:text-zinc-300'}`}
                                >
                                    Informações
                                    <div className={`absolute bottom-0 left-0 h-[2px] transition-all duration-500 rounded-full ${activeModalTab === 'info' ? 'w-full bg-primary shadow-[0_0_20px_rgba(129,140,248,1)] opacity-100' : 'w-0 bg-zinc-600 opacity-0 group-hover:w-1/2 group-hover:opacity-50'}`}></div>
                                </button>
                                <button
                                    onClick={() => setActiveModalTab('diag')}
                                    className={`py-6 text-[11px] font-black uppercase tracking-[0.3em] transition-all relative group ${activeModalTab === 'diag' ? 'text-primary' : 'text-zinc-500 hover:text-zinc-300'}`}
                                >
                                    Diagnóstico
                                    <div className={`absolute bottom-0 left-0 h-[2px] transition-all duration-500 rounded-full ${activeModalTab === 'diag' ? 'w-full bg-primary shadow-[0_0_20px_rgba(129,140,248,1)] opacity-100' : 'w-0 bg-zinc-600 opacity-0 group-hover:w-1/2 group-hover:opacity-50'}`}></div>
                                </button>
                            </div>
                        </div>

                        {/* Content area - Expanded Luxury Padding */}
                        <div className="p-12 space-y-12 overflow-y-auto custom-scrollbar flex-1 max-h-[60vh]">
                            {activeModalTab === 'info' ? (
                                <div className="space-y-10 animate-in fade-in duration-500">
                                    {/* Status Section */}
                                    <div className="flex items-center">
                                        <span className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-[0.1em] flex items-center gap-3 border ${selectedDevice.status_code === 'ONLINE'
                                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.1)]'
                                            : 'bg-red-500/10 text-red-400 border-red-500/20 shadow-[0_0_20px_rgba(239,68,68,0.1)]'
                                            }`}>
                                            <div className={`w-2 h-2 rounded-full ${selectedDevice.status_code === 'ONLINE' ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,1)] animate-pulse' : 'bg-red-400'}`}></div>
                                            {selectedDevice.status_code === 'ONLINE' ? 'Conexão Estabelecida' : 'Dispositivo Offline'}
                                        </span>
                                    </div>

                                    {/* Info Grid - Reorganized for Better Hierarchy */}
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                        {/* Left Column: Network */}
                                        <div className="bg-white/[0.02] p-6 rounded-2xl border border-white/5 space-y-6 h-full flex flex-col">
                                            <h3 className="text-[10px] font-black text-primary uppercase tracking-[0.2em] flex items-center gap-2 opacity-80 mb-2">
                                                <Broadcast size={14} weight="fill" />
                                                Rede & Conectividade
                                            </h3>
                                            <div className="space-y-5 flex-1">
                                                <InfoRow label="Endereço IPv4" value={selectedDevice.ip} />
                                                <InfoRow label="MAC Address" value={selectedDevice.mac} />
                                                {selectedDevice.device_type === 'printer' && selectedDevice.printer_data && (
                                                    <InfoRow label="Status SNMP" value={selectedDevice.printer_data.status} />
                                                )}
                                            </div>
                                        </div>

                                        {/* Right Column: Asset Info */}
                                        <div className="bg-white/[0.02] p-6 rounded-2xl border border-white/5 space-y-6 h-full flex flex-col">
                                            <h3 className="text-[10px] font-black text-primary uppercase tracking-[0.2em] flex items-center gap-2 opacity-80 mb-2">
                                                <IdentificationCard size={14} weight="fill" />
                                                Sistema & Patrimônio
                                            </h3>
                                            <div className="space-y-5 flex-1">
                                                <InfoRow label="Fabricante" value={selectedDevice.vendor} />
                                                <InfoRow label="Tipo de Ativo" value={selectedDevice.device_type} />
                                                <InfoRow label="Sistema Operacional" value={selectedDevice.os_detail || 'Genérico / Desconhecido'} />
                                            </div>
                                        </div>
                                    </div>

                                    {/* PRINTER MODULE - Special Dedicated Section */}
                                    {selectedDevice.device_type === 'printer' && selectedDevice.printer_data && (
                                        <div className="bg-black/20 rounded-2xl border border-white/10 overflow-hidden">
                                            <div className="bg-white/5 px-6 py-4 border-b border-white/5 flex justify-between items-center">
                                                <h3 className="text-[10px] font-black uppercase tracking-widest text-emerald-400 flex items-center gap-2">
                                                    <Printer size={14} weight="fill" /> Diagnóstico de Impressão
                                                </h3>
                                                <div className="flex gap-2">
                                                    {selectedDevice.printer_data.error_state && selectedDevice.printer_data.error_state !== '0' && (
                                                        <span className="text-[9px] bg-red-500/20 text-red-400 px-2.5 py-1 rounded border border-red-500/30 font-bold animate-pulse">ERRO DETECTADO</span>
                                                    )}
                                                    <span className="text-[9px] text-zinc-600 font-mono border border-white/5 px-2 py-0.5 rounded uppercase">{selectedDevice.printer_data.status}</span>
                                                </div>
                                            </div>

                                            <div className="p-8 grid grid-cols-1 lg:grid-cols-2 gap-12">
                                                {/* Metrics */}
                                                <div className="space-y-6">
                                                    <div>
                                                        <div className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider mb-2">Display do Painel</div>
                                                        <div className="p-3 bg-black/40 border border-white/10 rounded-lg text-[10px] font-mono text-emerald-400/80 break-words">
                                                            {selectedDevice.printer_data.console_display && selectedDevice.printer_data.console_display !== 'N/A' ? selectedDevice.printer_data.console_display : 'Sem mensagem no display'}
                                                        </div>
                                                    </div>

                                                    <div className="grid grid-cols-2 gap-6">
                                                        <InfoRow label="Total Páginas" value={selectedDevice.printer_data.pages} />
                                                        <InfoRow label="Uptime" value={selectedDevice.uptime} />
                                                    </div>
                                                    <div className="grid grid-cols-2 gap-6">
                                                        <InfoRow label="Localização" value={selectedDevice.location} />
                                                        <InfoRow label="Contato Admin" value={selectedDevice.printer_data.contact} />
                                                    </div>
                                                </div>

                                                {/* Supplies (Bars) */}
                                                <div>
                                                    <h4 className="text-[9px] uppercase tracking-widest text-zinc-500 font-bold mb-4 flex items-center gap-2">
                                                        <List size={14} /> Níveis de Suprimento
                                                    </h4>
                                                    <div className="space-y-4 max-h-[160px] overflow-y-auto pr-2 custom-scrollbar">
                                                        {selectedDevice.printer_data.supplies?.map((supply: any, idx: number) => {
                                                            const level = parseInt(supply.level) || 0
                                                            // Determine color based on name
                                                            let colorClass = "bg-zinc-500"
                                                            const name = supply.name.toLowerCase()
                                                            if (name.includes('cyan') || name.includes('ciano') || name.includes(' c ')) colorClass = "bg-cyan-400"
                                                            else if (name.includes('magenta') || name.includes(' m ')) colorClass = "bg-pink-500"
                                                            else if (name.includes('yellow') || name.includes('amarelo') || name.includes(' y ')) colorClass = "bg-yellow-400"
                                                            else if (name.includes('black') || name.includes('preto') || name.includes(' k ')) colorClass = "bg-zinc-100"

                                                            return (
                                                                <div key={idx} className="space-y-1.5">
                                                                    <div className="flex justify-between text-[9px] font-bold uppercase tracking-wider text-zinc-400">
                                                                        <span className="truncate max-w-[200px]" title={supply.name}>{supply.name}</span>
                                                                        <span className={level < 10 && level >= 0 ? "text-red-400 animate-pulse font-black" : "text-white font-mono"}>{supply.status_msg || `${level}% `}</span>
                                                                    </div>
                                                                    <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                                                                        <div
                                                                            className={`h-full ${colorClass} transition-all duration-1000 ease-out`}
                                                                            style={{ width: `${level < 0 ? 0 : level}%` }}
                                                                        ></div>
                                                                    </div>
                                                                </div>
                                                            )
                                                        })}
                                                        {(!selectedDevice.printer_data?.supplies || selectedDevice.printer_data.supplies.length === 0) && (
                                                            <div className="text-[10px] text-zinc-600 italic py-4 text-center border border-dashed border-white/5 rounded">Nenhum dado de suprimento disponível via SNMP.</div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Trays & Covers Section */}
                                            {((selectedDevice.printer_data?.trays?.length ?? 0) > 0 || (selectedDevice.printer_data?.covers?.length ?? 0) > 0) && (
                                                <div className="px-8 py-6 bg-white/[0.02] border-t border-white/5 grid grid-cols-1 md:grid-cols-2 gap-8">
                                                    {/* Paper Trays */}
                                                    {selectedDevice.printer_data.trays && selectedDevice.printer_data.trays.length > 0 && (
                                                        <div className="space-y-3">
                                                            <h4 className="text-[9px] uppercase tracking-widest text-zinc-500 font-bold flex items-center gap-2">
                                                                <div className="w-1.5 h-1.5 rounded-full bg-zinc-600"></div>
                                                                Bandejas de Papel
                                                            </h4>
                                                            <div className="space-y-2">
                                                                {selectedDevice.printer_data.trays.map((tray: any, idx: number) => (
                                                                    <div key={idx} className="bg-white/[0.03] p-3 rounded-lg border border-white/5">
                                                                        <div className="flex justify-between items-center mb-1.5">
                                                                            <span className="text-[10px] font-bold text-zinc-300 truncate max-w-[150px]" title={tray.name}>
                                                                                {tray.name}
                                                                            </span>
                                                                            <span className={`text-[9px] font-mono font-bold ${tray.status === 'Vazia' ? 'text-red-400 animate-pulse' : 'text-zinc-400'}`}>
                                                                                {tray.status}
                                                                            </span>
                                                                        </div>
                                                                        {tray.capacity > 0 && tray.level >= 0 && (
                                                                            <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                                                                                <div
                                                                                    className={`h-full ${tray.pct < 10 ? 'bg-red-500' : 'bg-primary'} transition-all duration-1000`}
                                                                                    style={{ width: `${tray.pct}%` }}
                                                                                ></div>
                                                                            </div>
                                                                        )}
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}

                                                    {/* Covers & Doors */}
                                                    {selectedDevice.printer_data.covers && selectedDevice.printer_data.covers.length > 0 && (
                                                        <div className="space-y-3">
                                                            <h4 className="text-[9px] uppercase tracking-widest text-zinc-500 font-bold flex items-center gap-2">
                                                                <div className="w-1.5 h-1.5 rounded-full bg-zinc-600"></div>
                                                                Status Físico (Tampas)
                                                            </h4>
                                                            <div className="grid grid-cols-1 gap-2">
                                                                {selectedDevice.printer_data?.covers?.map((cover: any, idx: number) => (
                                                                    <div key={idx} className={`p-2.5 rounded-lg border flex justify-between items-center ${cover.is_open
                                                                        ? 'bg-red-500/10 border-red-500/30'
                                                                        : 'bg-white/[0.03] border-white/5'
                                                                        }`}>
                                                                        <span className={`text-[10px] font-bold ${cover.is_open ? 'text-red-400' : 'text-zinc-400'}`}>
                                                                            {cover.name}
                                                                        </span>
                                                                        {cover.is_open ? (
                                                                            <span className="text-[8px] bg-red-500 text-white px-2 py-0.5 rounded font-black uppercase animate-pulse">ABERTA</span>
                                                                        ) : (
                                                                            <span className="text-[9px] text-emerald-500 font-bold flex items-center gap-1">
                                                                                <div className="w-1 h-1 bg-emerald-500 rounded-full"></div> OK
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            {/* Advanced Logs Section - History & Jobs */}
                                            {/* ... (Kept existing logs section below) */}
                                            {((selectedDevice.printer_data?.alerts?.length ?? 0) > 0 || (selectedDevice.printer_data?.job_history?.length ?? 0) > 0) && (
                                                <div className="px-8 py-6 bg-black/40 border-t border-white/5 grid grid-cols-1 md:grid-cols-2 gap-8">
                                                    {/* Alerts History */}
                                                    <div className="space-y-3">
                                                        <h4 className="text-[9px] uppercase tracking-widest text-red-400 font-bold flex items-center gap-2">
                                                            <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></div>
                                                            Histórico de Alertas
                                                        </h4>
                                                        <div className="space-y-2 max-h-[120px] overflow-y-auto custom-scrollbar pr-2">
                                                            {selectedDevice.printer_data.alerts && selectedDevice.printer_data.alerts.length > 0 ? (
                                                                selectedDevice.printer_data.alerts.map((alert: string, idx: number) => (
                                                                    <div key={idx} className="text-[10px] text-zinc-400 font-mono bg-white/[0.02] p-2 rounded border border-white/5 flex gap-2">
                                                                        <span className="text-red-500/50 select-none">!</span>
                                                                        {alert}
                                                                    </div>
                                                                ))
                                                            ) : (
                                                                <div className="text-[10px] text-zinc-600 italic">Nenhum alerta recente registrado via SNMP.</div>
                                                            )}
                                                        </div>
                                                    </div>

                                                    {/* Job History / Top Hosts */}
                                                    <div className="space-y-3">
                                                        <h4 className="text-[9px] uppercase tracking-widest text-primary font-bold flex items-center gap-2">
                                                            <div className="w-1.5 h-1.5 rounded-full bg-primary"></div>
                                                            Top Usuários (Jobs Recentes)
                                                        </h4>
                                                        <div className="space-y-2 max-h-[120px] overflow-y-auto custom-scrollbar pr-2">
                                                            {selectedDevice.printer_data.job_history && selectedDevice.printer_data.job_history.length > 0 ? (
                                                                selectedDevice.printer_data.job_history.map((job: any, idx: number) => (
                                                                    <div key={idx} className="flex justify-between items-center text-[10px] text-zinc-300 font-medium bg-white/[0.02] p-2 rounded border border-white/5 hover:bg-white/5 transition-colors">
                                                                        <span className="truncate max-w-[150px]" title={job.user}>{job.user || 'Desconhecido'}</span>
                                                                        <span className="bg-primary/20 text-primary-light px-1.5 py-0.5 rounded text-[9px] font-mono">{job.count}x</span>
                                                                    </div>
                                                                ))
                                                            ) : (
                                                                <div className="text-[10px] text-zinc-600 italic">Histórico de jobs indisponível (Job MIB não suportado).</div>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Ports Section - Cleaner Look */}
                                    {selectedDevice.ports && selectedDevice.ports.length > 0 && (
                                        <div className="space-y-3 pt-2 border-t border-white/5">
                                            <h3 className="text-[10px] font-bold text-primary uppercase tracking-wider mt-4">Portas TCP Abertas ({selectedDevice.ports.length})</h3>
                                            <div className="flex flex-wrap gap-2">
                                                {selectedDevice.ports.map((port, idx) => (
                                                    <span
                                                        key={idx}
                                                        className="px-2.5 py-1.5 bg-white/[0.03] border border-white/10 rounded-lg text-[10px] text-primary font-mono font-bold"
                                                    >
                                                        {port}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Actions Footer */}
                                    <div className="pt-2 flex gap-3">
                                        <button
                                            onClick={() => setSelectedDevice(null)}
                                            className="flex-[1.5] bg-white hover:bg-zinc-200 text-black px-4 py-3 rounded-xl font-bold text-xs transition-all active:scale-95 flex items-center justify-center gap-2"
                                        >
                                            <Globe size={16} weight="bold" />
                                            Localizar Ativo
                                        </button>
                                        <div className="flex items-center gap-3 relative">
                                            {/* Monitoring Button */}
                                            <button
                                                onClick={() => setShowMonitorMenu(!showMonitorMenu)}
                                                className={`bg-white/5 hover:bg-white/10 p-2 rounded-lg border border-white/10 transition-all flex items-center gap-2 ${isMonitoring ? 'text-green-400 border-green-500/30 bg-green-500/10' : 'text-zinc-400'}`}
                                                title="Configurar Monitoramento Automático"
                                            >
                                                <Pulse size={18} weight={isMonitoring ? "fill" : "regular"} className={isMonitoring ? "animate-pulse" : ""} />
                                                {isMonitoring && <span className="text-xs font-mono font-bold w-[40px] text-center">{monitorTimeLeft}s</span>}
                                            </button>

                                            {/* Monitoring Menu Popover */}
                                            {showMonitorMenu && (
                                                <div className="absolute top-full mt-2 right-0 bg-[#0f1014] border border-white/10 rounded-xl p-4 w-[280px] z-[100] shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-200 ring-1 ring-white/10">
                                                    <h4 className="text-xs font-bold text-white mb-3 flex items-center gap-2">
                                                        <Clock size={14} className="text-primary" />
                                                        Intervalo de Monitoramento
                                                    </h4>

                                                    <div className="flex items-center justify-center gap-2 mb-4 bg-black/20 p-2 rounded-lg">
                                                        <div className="flex flex-col gap-1 items-center">
                                                            <input
                                                                type="number" min="0" max="23"
                                                                className="w-10 h-8 bg-white/5 border border-white/10 rounded text-center text-sm text-white focus:border-primary focus:outline-none"
                                                                value={monitorConfig.h}
                                                                onChange={(e) => setMonitorConfig({ ...monitorConfig, h: parseInt(e.target.value) || 0 })}
                                                                disabled={isMonitoring}
                                                            />
                                                            <span className="text-[9px] text-zinc-500 uppercase font-black">H</span>
                                                        </div>
                                                        <span className="text-zinc-600 font-bold self-center pb-4">:</span>
                                                        <div className="flex flex-col gap-1 items-center">
                                                            <input
                                                                type="number" min="0" max="59"
                                                                className="w-10 h-8 bg-white/5 border border-white/10 rounded text-center text-sm text-white focus:border-primary focus:outline-none"
                                                                value={monitorConfig.m}
                                                                onChange={(e) => setMonitorConfig({ ...monitorConfig, m: parseInt(e.target.value) || 0 })}
                                                                disabled={isMonitoring}
                                                            />
                                                            <span className="text-[9px] text-zinc-500 uppercase font-black">M</span>
                                                        </div>
                                                        <span className="text-zinc-600 font-bold self-center pb-4">:</span>
                                                        <div className="flex flex-col gap-1 items-center">
                                                            <input
                                                                type="number" min="5" max="59"
                                                                className="w-10 h-8 bg-white/5 border border-white/10 rounded text-center text-sm text-white focus:border-primary focus:outline-none"
                                                                value={monitorConfig.s}
                                                                onChange={(e) => setMonitorConfig({ ...monitorConfig, s: parseInt(e.target.value) || 0 })}
                                                                disabled={isMonitoring}
                                                            />
                                                            <span className="text-[9px] text-zinc-500 uppercase font-black">S</span>
                                                        </div>
                                                    </div>

                                                    <button
                                                        onClick={() => {
                                                            if (isMonitoring) {
                                                                setIsMonitoring(false)
                                                            } else {
                                                                const total = (monitorConfig.h * 3600) + (monitorConfig.m * 60) + monitorConfig.s
                                                                if (total < 5) {
                                                                    alert("O intervalo mínimo é de 5 segundos.")
                                                                    return
                                                                }
                                                                setMonitorTimeLeft(total)
                                                                setIsMonitoring(true)
                                                                setShowMonitorMenu(false)
                                                            }
                                                        }}
                                                        className={`w-full py-2.5 rounded-lg font-bold text-xs transition-all flex items-center justify-center gap-2 ${isMonitoring
                                                            ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30'
                                                            : 'bg-primary text-white hover:bg-primary-dark shadow-lg shadow-primary/20 hover:scale-[1.02]'
                                                            }`}
                                                    >
                                                        {isMonitoring ? (
                                                            <>
                                                                <Stop size={14} weight="fill" /> Parar Monitoramento
                                                            </>
                                                        ) : (
                                                            <>
                                                                <Play size={14} weight="fill" /> Iniciar
                                                            </>
                                                        )}
                                                    </button>
                                                </div>
                                            )}

                                            {/* Refresh Button */}
                                            <button
                                                onClick={() => refreshDeviceMutation.mutate(selectedDevice.ip)}
                                                disabled={refreshDeviceMutation.isPending}
                                                className="bg-white/5 hover:bg-white/10 text-white p-2 rounded-lg border border-white/10 transition-colors flex items-center gap-2"
                                                title="Recarregar dados deste ativo manualmente"
                                            >
                                                <ArrowsClockwise size={18} className={`${refreshDeviceMutation.isPending ? 'animate-spin' : ''} `} />
                                                {/* <span className="text-xs font-bold hidden sm:inline">Recarregar</span> */}
                                            </button>

                                            <button
                                                onClick={() => setSelectedDevice(null)}
                                                className="bg-white/5 hover:bg-red-500/20 text-gray-400 hover:text-red-400 p-2 rounded-full transition-colors"
                                            >
                                                <X size={20} weight="bold" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-8 animate-in slide-in-from-right-4 duration-300">
                                    <div className="flex items-center justify-between bg-white/[0.02] p-4 rounded-2xl border border-white/5">
                                        <div className="space-y-1">
                                            <h3 className="text-sm font-bold text-white tracking-tight leading-none">Teste de Conectividade ICMP</h3>
                                            <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-[0.1em]">Enviando 5 pacotes para {selectedDevice.ip}</p>
                                        </div>
                                        <button
                                            onClick={() => pingMutation.mutate(selectedDevice.ip)}
                                            disabled={pingMutation.isPending}
                                            className={`px-5 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center gap-2 ${pingMutation.isPending
                                                ? 'bg-primary/20 text-primary border border-primary/30 cursor-wait'
                                                : 'bg-primary text-white hover:bg-primary-dark shadow-lg shadow-primary/20 active:scale-95'
                                                }`}
                                        >
                                            {pingMutation.isPending ? (
                                                <>
                                                    <div className="w-2 h-2 rounded-full bg-white animate-ping"></div>
                                                    Pingando...
                                                </>
                                            ) : (
                                                <>
                                                    <TerminalWindow size={16} weight="bold" />
                                                    Testar Conexão
                                                </>
                                            )}
                                        </button>
                                    </div>

                                    <div className="bg-black/40 border border-white/10 rounded-2xl p-6 min-h-[220px] font-mono text-[11px] text-emerald-400 overflow-hidden relative shadow-inner">
                                        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-emerald-500/20 to-transparent"></div>
                                        {pingMutation.isPending ? (
                                            <div className="flex flex-col gap-2 opacity-60">
                                                <div className="flex gap-2">
                                                    <span className="text-zinc-600">[{new Date().toLocaleTimeString()}]</span>
                                                    <span>Iniciando diagnóstico para {selectedDevice.ip}...</span>
                                                </div>
                                                <div className="animate-pulse flex gap-2">
                                                    <span className="text-zinc-600">[{new Date().toLocaleTimeString()}]</span>
                                                    <span>Aguardando resposta do alvo...</span>
                                                </div>
                                            </div>
                                        ) : pingResult ? (
                                            <div className={`whitespace - pre - wrap leading - relaxed ${pingResult.startsWith('Erro') || pingResult.startsWith('Timeout') || pingResult.includes('falhou') ? 'text-red-400 font-bold' : 'text-emerald-400'} `}>
                                                {pingResult}
                                            </div>
                                        ) : (
                                            <div className="h-full flex flex-col items-center justify-center opacity-40 gap-4">
                                                <div className="p-4 bg-white/5 rounded-full">
                                                    <TerminalWindow size={32} />
                                                </div>
                                                <p className="tracking-widest font-black uppercase text-xs">Console Inativo</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default Scanner
