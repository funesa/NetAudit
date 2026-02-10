import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MapPin, MagnifyingGlass, Clock, Info, ArrowCircleRight, ShieldCheck, X } from '@phosphor-icons/react'
import api from '../services/api'

interface IPStatus {
    ip: string
    status: 'online' | 'free' | 'in_use' | 'probably_free'
    hostname?: string
    last_seen?: string
    last_seen_days?: number
}

interface IPDataResponse {
    ips: IPStatus[]
    stats: {
        total: number
        free: number
        online: number
        in_use: number
        subnet: string
    }
}

const IPMap = () => {
    const [subnet, setSubnet] = useState('172.23.51.0/24')
    const [selectedIP, setSelectedIP] = useState<IPStatus | null>(null)

    const { data: ipData, isLoading } = useQuery<IPDataResponse>({
        queryKey: ['ipMap', subnet],
        queryFn: async () => {
            const response = await api.get('/api/ip-map', { params: { subnet } })
            return response.data
        },
    })

    const { data: suggestion } = useQuery<{ ip: string; subnet: string }>({
        queryKey: ['ipSuggest', subnet],
        queryFn: async () => {
            const response = await api.get('/api/ip-map/suggest', { params: { subnet } })
            return response.data
        },
    })

    const getStatusColor = (status: string, isSelected: boolean) => {
        if (isSelected) return 'bg-white border-2 border-primary shadow-[0_0_15px_rgba(129,140,248,0.8)] z-10 scale-125'
        switch (status) {
            case 'online': return 'bg-status-success/80 border border-status-success/30 hover:bg-status-success'
            case 'in_use': return 'bg-yellow-500/40 border border-yellow-500/20 hover:bg-yellow-500/60'
            case 'free': return 'bg-white/5 border border-white/5 hover:bg-white/10'
            default: return 'bg-white/5 border border-white/5'
        }
    }

    const ipsToRender = ipData?.ips || []

    return (
        <div className="page-transition space-y-6 flex flex-col h-[calc(100vh-140px)]">
            {/* Header section with search and metrics combined */}
            <div className="flex flex-col xl:flex-row gap-6 items-start xl:items-center justify-between">
                <div className="space-y-1">
                    <h1 className="text-2xl font-black text-white tracking-tighter flex items-center gap-2">
                        <MapPin size={28} className="text-primary" weight="fill" />
                        MAPA DE ENDEREÇOS IP
                    </h1>
                    <div className="flex items-center gap-4">
                        <span className="text-[10px] font-black text-dark-muted uppercase tracking-[0.2em]">Subnet Monitorada:</span>
                        <div className="flex items-center gap-2 bg-dark-panel px-3 py-1 rounded-full border border-dark-border group focus-within:border-primary/50 transition-all">
                            <MagnifyingGlass size={12} className="text-primary" />
                            <input
                                type="text"
                                value={subnet}
                                onChange={(e) => setSubnet(e.target.value)}
                                className="bg-transparent border-none text-[11px] text-white font-bold focus:ring-0 w-32 p-0 placeholder:text-gray-700"
                            />
                        </div>
                    </div>
                </div>

                {/* Compact Metrics Bar */}
                <div className="flex items-center gap-1 bg-dark-panel p-1 rounded-2xl border border-dark-border shadow-inner">
                    <div className="px-4 py-2 flex flex-col items-center border-r border-white/5">
                        <span className="text-[9px] font-black text-status-success uppercase tracking-widest leading-none mb-1">Online</span>
                        <span className="text-lg font-black text-white leading-none">{ipData?.stats?.online || 0}</span>
                    </div>
                    <div className="px-4 py-2 flex flex-col items-center border-r border-white/5">
                        <span className="text-[9px] font-black text-yellow-500 uppercase tracking-widest leading-none mb-1">Offline</span>
                        <span className="text-lg font-black text-white leading-none">{ipData?.stats?.in_use || 0}</span>
                    </div>
                    <div className="px-4 py-2 flex flex-col items-center border-r border-white/5">
                        <span className="text-[9px] font-black text-gray-500 uppercase tracking-widest leading-none mb-1">Livres</span>
                        <span className="text-lg font-black text-white leading-none">{ipData?.stats?.free || 0}</span>
                    </div>
                    <div className="px-4 py-2 flex flex-col items-center">
                        <span className="text-[9px] font-black text-primary uppercase tracking-widest leading-none mb-1">Total</span>
                        <span className="text-lg font-black text-white leading-none">{ipData?.stats?.total || 0}</span>
                    </div>
                </div>
            </div>

            <div className="flex-1 flex flex-col lg:flex-row gap-6 overflow-hidden">
                {/* Visual Grid Container */}
                <div className="flex-1 bg-dark-panel/30 border border-dark-border rounded-[32px] p-6 overflow-y-auto custom-scrollbar flex flex-col gap-4 shadow-2xl relative">
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-[0.3em] flex items-center gap-2">
                            <ShieldCheck size={14} className="text-primary" />
                            Matriz de Ocupação da Rede
                        </h3>
                        <div className="flex items-center gap-3">
                            <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-status-success"></div>
                                <span className="text-[9px] font-bold text-gray-500 uppercase">Ativo</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-yellow-500/50"></div>
                                <span className="text-[9px] font-bold text-gray-500 uppercase">Inativo</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-white/10"></div>
                                <span className="text-[9px] font-bold text-gray-500 uppercase">Livre</span>
                            </div>
                        </div>
                    </div>

                    {isLoading ? (
                        <div className="flex-1 flex flex-col items-center justify-center gap-4 opacity-50">
                            <div className="w-12 h-12 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                            <span className="text-[10px] font-black uppercase tracking-widest">Mapeando Matriz...</span>
                        </div>
                    ) : (
                        <div className="grid grid-cols-8 sm:grid-cols-16 gap-2 place-content-start">
                            {ipsToRender.map((ip, idx) => {
                                const isSelected = selectedIP?.ip === ip.ip
                                return (
                                    <div
                                        key={idx}
                                        onClick={() => setSelectedIP(ip)}
                                        className={`
                                            aspect-square rounded-lg flex items-center justify-center cursor-pointer transition-all duration-300
                                            ${getStatusColor(ip.status, isSelected)}
                                            ${ip.status === 'free' ? 'group' : ''}
                                        `}
                                    >
                                        <span className={`text-[9px] font-black ${isSelected ? 'text-primary' : 'text-white/20 group-hover:text-white/40'}`}>
                                            {ip.ip.split('.').pop()}
                                        </span>
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>

                {/* Info Panel / Suggestion */}
                <div className="w-full lg:w-[320px] shrink-0 flex flex-col gap-4 h-full overflow-y-auto section-scroll pb-4">
                    {/* Next IP Suggestion */}
                    {suggestion && (
                        <div className="bg-primary/10 border border-primary/20 rounded-3xl p-5 flex flex-col gap-4 shadow-xl">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 bg-primary text-white rounded-xl flex items-center justify-center shadow-lg shadow-primary/20">
                                    <ArrowCircleRight size={24} weight="fill" />
                                </div>
                                <div>
                                    <h4 className="text-[9px] font-black text-primary uppercase tracking-widest leading-tight">Sugestão de Próximo IP</h4>
                                    <div className="text-lg font-black text-white">{typeof suggestion === 'string' ? suggestion : suggestion.ip}</div>
                                </div>
                            </div>
                            <button className="w-full py-3 bg-primary hover:bg-primary-dark text-white rounded-2xl font-black text-[10px] tracking-widest transition-all active:scale-95 shadow-lg">
                                RESERVAR ESTE IP
                            </button>
                        </div>
                    )}

                    {/* IP Details Sidebar Card */}
                    {selectedIP ? (
                        <div className="bg-dark-panel border-2 border-primary/30 rounded-[32px] p-6 shadow-2xl relative animate-in fade-in slide-in-from-right-4">
                            <button
                                onClick={() => setSelectedIP(null)}
                                className="absolute top-4 right-4 p-2 bg-white/5 hover:bg-white/10 rounded-full transition-colors"
                            >
                                <X size={16} className="text-gray-500" />
                            </button>

                            <div className="flex flex-col items-center text-center mb-6">
                                <div className={`w-16 h-16 rounded-[24px] flex items-center justify-center mb-4 shadow-2xl border ${selectedIP.status === 'online' ? 'bg-status-success/20 border-status-success text-status-success' :
                                    selectedIP.status === 'in_use' ? 'bg-yellow-500/20 border-yellow-500 text-yellow-500' :
                                        'bg-white/5 border-white/10 text-gray-500'
                                    }`}>
                                    <Info size={32} weight="fill" />
                                </div>
                                <h2 className="text-2xl font-black text-white tracking-tighter">{selectedIP.ip}</h2>
                                <span className={`text-[10px] font-black uppercase tracking-[0.2em] px-3 py-1 rounded-full mt-2 border ${selectedIP.status === 'online' ? 'bg-status-success/10 border-status-success/20 text-status-success' :
                                    selectedIP.status === 'in_use' ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-500' :
                                        'bg-white/5 border-white/10 text-gray-500'
                                    }`}>
                                    {selectedIP.status === 'online' ? 'Dispositivo Online' :
                                        selectedIP.status === 'in_use' ? 'Ocupado / Offline' : 'Endereço Livre'}
                                </span>
                            </div>

                            <div className="space-y-4">
                                <div className="p-4 bg-dark-bg/50 border border-white/5 rounded-2xl">
                                    <div className="text-[9px] font-black text-gray-500 uppercase tracking-widest mb-1">Hostname / Identificação</div>
                                    <div className="text-xs font-bold text-white truncate">{selectedIP.hostname || 'Não Identificado'}</div>
                                </div>
                                <div className="p-4 bg-dark-bg/50 border border-white/5 rounded-2xl">
                                    <div className="text-[9px] font-black text-gray-500 uppercase tracking-widest mb-1">Visto por último</div>
                                    <div className="flex items-center gap-2 text-xs font-bold text-white">
                                        <Clock size={14} className="text-primary" />
                                        {selectedIP.last_seen || 'Nunca monitorado'}
                                    </div>
                                    {selectedIP.last_seen_days !== undefined && (
                                        <div className="text-[9px] text-primary/60 font-medium mt-1 italic">Há aprox. {selectedIP.last_seen_days} dias</div>
                                    )}
                                </div>
                            </div>

                            <div className="mt-8 pt-6 border-t border-white/5">
                                <button className="w-full py-3 bg-white/5 hover:bg-white text-gray-300 hover:text-black rounded-2xl font-black text-[10px] tracking-widest transition-all uppercase">
                                    Ver Detalhes do Scanner
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col items-center justify-center text-center p-8 bg-dark-panel/20 border border-dashed border-dark-border rounded-[32px] opacity-60">
                            <Info size={40} className="text-dark-muted mb-4" />
                            <h4 className="text-xs font-bold text-white uppercase tracking-tighter mb-2">Selecione um IP</h4>
                            <p className="text-[10px] text-dark-muted leading-relaxed uppercase font-medium">Clique em qualquer bloco da matriz para ver detalhes técnicos do endereço.</p>
                        </div>
                    )}
                </div>
            </div>

            <style>{`
                .grid-cols-16 {
                    grid-template-columns: repeat(16, minmax(0, 1fr));
                }
                @media (max-width: 640px) {
                    .sm\\:grid-cols-16 {
                        grid-template-columns: repeat(8, minmax(0, 1fr));
                    }
                }
            `}</style>
        </div>
    )
}

export default IPMap
