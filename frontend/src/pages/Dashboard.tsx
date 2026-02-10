import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
    Devices, Users, Warning, ClockCounterClockwise, Binoculars, CaretRight,
    ChartLine, Cpu, Memory, HardDrive, BellRinging, WarningOctagon
} from '@phosphor-icons/react'
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import api from '../services/api'

interface DashboardStats {
    total_users: number
    active_users: number
    online_count: number
    total_devices: number
    global_alerts: number
}

interface MonitoringOverview {
    total_devices: number
    healthy_devices: number
    warning_devices: number
    active_alerts: number
    rankings: {
        cpu: { hostname: string; value: number; ip: string }[]
        ram: { hostname: string; value: number; ip: string }[]
        disk: { hostname: string; value: number; ip: string }[]
        latency: { hostname: string; value: number; ip: string }[]
    }
}

const Dashboard = () => {
    const navigate = useNavigate()

    // 1. Fetch Stats Gerais
    const { data: stats, isLoading: isLoadingStats } = useQuery<DashboardStats>({
        queryKey: ['dashboardStats'],
        queryFn: async () => {
            const response = await api.get('/api/dashboard/stats')
            return response.data
        },
        refetchInterval: 60000,
        staleTime: 10000,
    })

    // 2. Fetch Sentinel Data
    const { data: monitoring, isLoading: isLoadingMonitoring } = useQuery<MonitoringOverview>({
        queryKey: ['monitoringOverview'],
        queryFn: async () => {
            const response = await api.get('/api/monitoring/overview')
            return response.data
        },
        refetchInterval: 30000
    })

    // 3. Fetch Real Active Alerts
    const { data: activeAlerts, isLoading: isLoadingAlerts } = useQuery<any[]>({
        queryKey: ['activeAlerts'],
        queryFn: async () => {
            const response = await api.get('/api/alerts/active')
            return Array.isArray(response.data) ? response.data : response.data.alerts || []
        },
        refetchInterval: 15000
    })

    // 4. Fetch Performance History
    const { data: performanceHistory } = useQuery<any[]>({
        queryKey: ['metricsHistory'],
        queryFn: async () => {
            const response = await api.get('/api/metrics/history')
            return response.data.success ? response.data.data : []
        },
        refetchInterval: 60000
    })

    const isLoading = isLoadingStats || isLoadingMonitoring || isLoadingAlerts

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-[calc(100vh-200px)]">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-2 border-dark-border border-t-primary rounded-full animate-spin"></div>
                    <span className="text-dark-muted text-sm font-medium">Carregando dados unificados...</span>
                </div>
            </div>
        )
    }

    // --- Data Preparation ---

    const kpiCards = [
        {
            title: 'Usuários do AD',
            value: stats?.total_users || 0,
            subtitle: `${stats?.active_users || 0} ativos no domínio`,
            icon: Users,
            colorClass: 'text-blue-500',
            bgClass: 'bg-blue-500/10',
            borderClass: 'border-blue-500/20',
        },
        {
            title: 'Dispositivos Online',
            value: stats?.online_count || 0,
            subtitle: `De um total de ${stats?.total_devices || 0}`,
            icon: Devices,
            colorClass: 'text-indigo-500',
            bgClass: 'bg-indigo-500/10',
            borderClass: 'border-indigo-500/20',
        },
        {
            title: 'Com Alertas',
            value: monitoring?.warning_devices || 0,
            subtitle: 'Detectados pelo Sentinel',
            icon: Warning,
            colorClass: 'text-amber-500',
            bgClass: 'bg-amber-500/10',
            borderClass: 'border-amber-500/20',
        },
        {
            title: 'Alertas Críticos',
            value: stats?.global_alerts || 0,
            subtitle: 'Detectados nas últimas 24h',
            icon: BellRinging,
            colorClass: 'text-rose-500',
            bgClass: 'bg-rose-500/10',
            borderClass: 'border-rose-500/20',
        },
    ]

    const RankingSection = ({ title, icon: Icon, data, unit, color }: any) => (
        <div className="bg-dark-panel p-5 rounded-2xl border border-dark-border shadow-sm hover:shadow-md transition-all">
            <h3 className="text-[11px] font-bold text-dark-muted uppercase tracking-wider flex items-center gap-2 mb-4">
                <Icon size={14} className={color} weight="fill" />
                {title}
            </h3>
            <div className="space-y-3">
                {data?.length > 0 ? data.slice(0, 3).map((item: any, idx: number) => (
                    <div key={idx} className="space-y-1">
                        <div className="flex justify-between text-xs font-medium">
                            <span className="text-dark-text truncate max-w-[120px]" title={item.hostname}>{item.hostname}</span>
                            <span className={color}>{item.value}{unit}</span>
                        </div>
                        <div className="h-1 bg-dark-bg rounded-full overflow-hidden border border-dark-border">
                            <div
                                className={`h-full opacity-80 rounded-full transition-all duration-1000 ${color.replace('text-', 'bg-')}`}
                                style={{ width: `${Math.min(item.value, 100)}%` }}
                            ></div>
                        </div>
                    </div>
                )) : (
                    <div className="py-4 text-center text-dark-muted italic text-[10px]">Sem dados recentes</div>
                )}
            </div>
        </div>
    )

    return (
        <div className="page-transition space-y-8">
            {/* Header - Corporate Clean */}
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
                <div className="space-y-1">
                    <h1 className="text-3xl font-bold text-dark-text tracking-tight">
                        Visão Geral
                    </h1>
                    <p className="text-sm text-dark-muted">Monitoramento unificado de rede e infraestrutura.</p>
                </div>

                <div className="flex items-center gap-4 p-1.5 pl-4 rounded-lg bg-dark-panel border border-dark-border shadow-sm">
                    <div className="text-right">
                        <div className="text-[10px] uppercase font-bold text-dark-muted tracking-wider">Sync</div>
                        <div className="text-xs font-medium text-dark-text">{new Date().toLocaleTimeString()}</div>
                    </div>
                    <div className="p-2 bg-dark-surface rounded-md border border-dark-border text-dark-muted">
                        <ClockCounterClockwise size={16} weight="bold" />
                    </div>
                </div>
            </div>

            {/* KPI Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {kpiCards.map((card, index) => {
                    const Icon = card.icon
                    return (
                        <div
                            key={index}
                            className="ethereal-card p-6 relative overflow-hidden group hover:border-dark-border-hover transition-all"
                        >
                            <div className="flex flex-col gap-4 relative z-10">
                                <div className="flex justify-between items-start">
                                    <div className={`w-10 h-10 rounded-lg ${card.bgClass} border ${card.borderClass} flex items-center justify-center ${card.colorClass} transition-colors`}>
                                        <Icon size={20} weight="fill" />
                                    </div>
                                </div>

                                <div className="space-y-1">
                                    <div className="text-[13px] font-medium text-dark-muted">{card.title}</div>
                                    <div className="text-3xl font-bold text-dark-text tracking-tight">{card.value}</div>
                                    <div className="text-[12px] text-dark-muted">{card.subtitle}</div>
                                </div>
                            </div>
                        </div>
                    )
                })}
            </div>

            {/* Sentinel Rankings - Top 3 per Category */}
            <div className="space-y-4">
                <div className="flex items-center gap-2 mb-2">
                    <ChartLine size={18} className="text-primary" />
                    <h2 className="text-sm font-semibold text-dark-text">Sentinel - Top Consumo</h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <RankingSection title="CPU" icon={Cpu} data={monitoring?.rankings.cpu} unit="%" color="text-blue-500" />
                    <RankingSection title="RAM" icon={Memory} data={monitoring?.rankings.ram} unit="%" color="text-emerald-500" />
                    <RankingSection title="Disco" icon={HardDrive} data={monitoring?.rankings.disk} unit="%" color="text-amber-500" />
                    <RankingSection title="Latência" icon={ChartLine} data={monitoring?.rankings.latency} unit="ms" color="text-violet-500" />
                </div>
            </div>

            {/* Main Content Area: Charts & Actions */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Performance Chart */}
                <div className="lg:col-span-2 ethereal-card p-8 border-dark-border relative overflow-hidden group min-h-[400px]">
                    <div className="space-y-6 relative z-10 h-full flex flex-col">
                        <div className="flex items-center justify-between">
                            <div className="space-y-1">
                                <h2 className="text-lg font-semibold text-dark-text flex items-center gap-2">
                                    Histórico de Performance
                                </h2>
                                <p className="text-sm text-dark-muted">Métricas Globais da Rede (24h)</p>
                            </div>
                        </div>

                        <div className="flex-1 w-full min-h-[300px] relative">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={performanceHistory || []}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                                    <XAxis dataKey="time" stroke="#52525b" fontSize={10} axisLine={false} tickLine={false} />
                                    <YAxis stroke="#52525b" fontSize={10} axisLine={false} tickLine={false} unit="%" />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                                        itemStyle={{ fontSize: '12px', fontWeight: '500' }}
                                    />
                                    <Line name="CPU" type="monotone" dataKey="cpu" stroke="#3b82f6" strokeWidth={2} dot={false} animationDuration={2000} />
                                    <Line name="RAM" type="monotone" dataKey="ram" stroke="#10b981" strokeWidth={2} dot={false} animationDuration={2000} />
                                </LineChart>
                            </ResponsiveContainer>
                            {(!performanceHistory || performanceHistory.length === 0) && (
                                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                                    <p className="text-dark-muted text-xs font-medium uppercase tracking-wider bg-dark-panel/80 px-4 py-2 rounded-full border border-dark-border backdrop-blur-sm">
                                        Coletando métricas...
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Quick Actions Panel */}
                <div className="space-y-6">
                    {/* Alerts Section */}
                    <div className="ethereal-card p-6 border-dark-border">
                        <h2 className="text-sm font-semibold text-dark-text mb-4 flex items-center gap-2">
                            <WarningOctagon size={16} className="text-rose-500" /> Alertes Recentes
                        </h2>
                        <div className="space-y-3 max-h-[300px] overflow-y-auto section-scroll pr-2">
                            {activeAlerts && activeAlerts.length > 0 ? (
                                activeAlerts.slice(0, 5).map((alert) => {
                                    const isCritical = ['disaster', 'critical', 'high'].includes(alert.severity?.toLowerCase())
                                    const borderColor = isCritical ? 'border-rose-500' : 'border-amber-500'
                                    const bgGradient = isCritical ? 'from-rose-500/10' : 'from-amber-500/10'

                                    return (
                                        <div
                                            key={alert.id}
                                            className={`flex flex-col gap-1 p-3 bg-gradient-to-r ${bgGradient} to-transparent rounded-xl border border-white/5 border-l-2 ${borderColor} transition-all hover:bg-white/5`}
                                        >
                                            <div className="flex justify-between items-start gap-2">
                                                <p className="text-xs font-bold text-dark-text truncate" title={alert.title}>
                                                    {alert.title}
                                                </p>
                                                <span className="text-[9px] font-medium text-dark-muted whitespace-nowrap">
                                                    {alert.triggered_at ? new Date(alert.triggered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--'}
                                                </span>
                                            </div>
                                            <p className="text-[10px] text-dark-muted line-clamp-2">
                                                {alert.hostname ? `[${alert.hostname}] ` : ''}{alert.message}
                                            </p>
                                        </div>
                                    )
                                })
                            ) : (
                                <div className="flex flex-col items-center justify-center py-8 text-center bg-dark-bg/30 rounded-xl border border-dashed border-dark-border">
                                    <BellRinging size={24} className="text-dark-muted mb-2 opacity-20" />
                                    <p className="text-[11px] text-dark-muted">Nenhum alerta ativo no momento</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Shortcuts */}
                    <div className="ethereal-card p-6 border-dark-border space-y-4">
                        <h2 className="text-sm font-semibold text-dark-text">Ações Rápidas</h2>
                        <div className="grid grid-cols-1 gap-3">
                            <button
                                onClick={() => navigate('/scanner')}
                                className="group flex items-center justify-between p-3 bg-dark-surface hover:bg-dark-surface/80 rounded-xl border border-dark-border hover:border-primary/30 transition-all duration-200"
                            >
                                <div className="flex items-center gap-3">
                                    <div className="p-1.5 bg-primary/10 text-primary rounded-lg">
                                        <Binoculars size={18} weight="fill" />
                                    </div>
                                    <div className="text-left">
                                        <div className="font-medium text-xs text-dark-text">Nova Varredura</div>
                                    </div>
                                </div>
                                <CaretRight size={12} className="text-dark-muted group-hover:text-primary transition-colors" />
                            </button>

                            <button
                                onClick={() => navigate('/ad-users')}
                                className="group flex items-center justify-between p-3 bg-dark-surface hover:bg-dark-surface/80 rounded-xl border border-dark-border hover:border-indigo-500/30 transition-all duration-200"
                            >
                                <div className="flex items-center gap-3">
                                    <div className="p-1.5 bg-indigo-500/10 text-indigo-500 rounded-lg">
                                        <Users size={18} weight="fill" />
                                    </div>
                                    <div className="text-left">
                                        <div className="font-medium text-xs text-dark-text">Gestão AD</div>
                                    </div>
                                </div>
                                <CaretRight size={12} className="text-dark-muted group-hover:text-indigo-500 transition-colors" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Dashboard
