import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
    HardDrives, DesktopTower, Warning,
    Info, MagnifyingGlass, ArrowsClockwise, X,
    Tag, ShieldCheck
} from '@phosphor-icons/react'
import api from '../services/api'

interface DiskInfo {
    Server: string
    OS: string
    Drive: string
    Label: string
    TotalGB: number
    FreeGB: number
    UsedGB: number
    PctUsed: number
    Status: string
    Error?: string
}

const ADStorage = () => {
    const [searchTerm, setSearchTerm] = useState('')
    const [selectedDisk, setSelectedDisk] = useState<DiskInfo | null>(null)
    const [position, setPosition] = useState({ x: 0, y: 0 })
    const [isDragging, setIsDragging] = useState(false)
    const dragStart = useRef({ x: 0, y: 0 })

    // Reset position when modal closes/opens
    useEffect(() => {
        if (!selectedDisk) {
            setPosition({ x: 0, y: 0 })
        }
    }, [selectedDisk])

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
        // Don't drag if clicking buttons
        if ((e.target as HTMLElement).closest('button')) return

        e.preventDefault()
        setIsDragging(true)
        dragStart.current = {
            x: e.clientX - position.x,
            y: e.clientY - position.y
        }
        document.body.style.cursor = 'grabbing'
    }

    const { data: disks, isLoading, error, refetch } = useQuery<DiskInfo[]>({
        queryKey: ['adShares'],
        queryFn: async () => {
            const response = await api.get('/api/ad/shares')
            return response.data
        },
    })

    const filteredDisks = disks?.filter(d =>
        d.Server.toLowerCase().includes(searchTerm.toLowerCase()) ||
        d.Label?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        d.Drive?.toLowerCase().includes(searchTerm.toLowerCase())
    )

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-2 border-dark-border border-t-primary rounded-full animate-spin"></div>
                    <span className="text-dark-muted text-sm font-medium">Acessando servidores...</span>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="bg-red-500/5 border border-red-500/20 p-8 rounded-xl text-center">
                <HardDrives size={32} className="text-red-500 mx-auto mb-4" />
                <h3 className="text-dark-text font-semibold text-lg mb-2">Erro de Comunicação</h3>
                <p className="text-dark-muted text-sm">Não foi possível conectar aos servidores.</p>
            </div>
        )
    }

    return (
        <div className="page-transition space-y-8 pb-20">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="space-y-1">
                    <h1 className="text-3xl font-bold text-dark-text tracking-tight flex items-center gap-3">
                        <HardDrives size={32} className="text-primary" weight="fill" />
                        Armazenamento
                    </h1>
                    <p className="text-dark-muted text-sm">Monitoramento de capacidade e integridade.</p>
                </div>

                <div className="flex items-center gap-3">
                    <div className="relative group">
                        <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-muted group-focus-within:text-primary transition-colors" size={16} />
                        <input
                            type="text"
                            placeholder="Buscar servidor..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="bg-dark-surface border border-dark-border rounded-xl pl-10 pr-4 py-2 text-sm text-dark-text focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all w-[300px]"
                        />
                    </div>
                    <button
                        onClick={() => refetch()}
                        className="bg-dark-surface hover:bg-dark-panel text-dark-text p-2 rounded-xl border border-dark-border transition-all flex items-center justify-center"
                        title="Atualizar"
                    >
                        <ArrowsClockwise size={20} />
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredDisks?.map((disk, idx) => (
                    <div
                        key={idx}
                        onClick={() => setSelectedDisk(disk)}
                        className="bg-white/[0.03] backdrop-blur-md p-6 rounded-[24px] border border-white/10 hover:border-primary/40 hover:bg-white/[0.05] transition-all group flex flex-col relative shadow-xl cursor-pointer active:scale-95"
                    >
                        <div
                            className={`absolute top-0 left-0 right-0 h-1 transition-all rounded-t-[24px] ${disk.Status !== 'Online' ? 'bg-zinc-600' :
                                disk.PctUsed > 90 ? 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]' :
                                    disk.PctUsed > 75 ? 'bg-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.5)]' :
                                        'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]'
                                }`}
                        ></div>

                        <div className="flex items-start justify-between mb-6 pt-2">
                            <div className="p-3 bg-white/5 rounded-2xl border border-white/5 group-hover:scale-110 transition-transform">
                                <DesktopTower size={24} className={disk.Status === 'Online' ? 'text-primary' : 'text-zinc-500'} />
                            </div>
                            <div className="flex flex-col items-end gap-1.5">
                                <span className={`text-[10px] font-black px-2.5 py-1 rounded-lg border uppercase tracking-widest ${disk.Status === 'Online'
                                    ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                                    : 'bg-zinc-500/10 text-zinc-500 border-zinc-500/20'
                                    }`}>
                                    {disk.Status}
                                </span>
                                {disk.Status === 'Online' && (
                                    <span className="text-[10px] text-zinc-500 font-black uppercase tracking-tighter">{disk.PctUsed}% em uso</span>
                                )}
                            </div>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <h3 className="text-lg font-black text-white flex items-center gap-2 tracking-tight">
                                    {disk.Server}
                                    <span className="text-[10px] font-black bg-primary/20 border border-primary/30 px-2 py-0.5 rounded-lg text-primary">{disk.Drive}</span>
                                </h3>
                                <p className="text-[10px] text-zinc-500 font-black uppercase tracking-widest mt-1">{disk.Label || 'Volume Local'}</p>
                            </div>

                            {disk.Status === 'Online' ? (
                                <div className="space-y-3">
                                    <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-zinc-400">
                                        <span>Livre: <span className="text-emerald-400">{disk.FreeGB} GB</span></span>
                                        <span>{disk.TotalGB} GB Total</span>
                                    </div>
                                    <div className="h-2 bg-white/5 rounded-full overflow-hidden border border-white/5 p-[1px]">
                                        <div
                                            className={`h-full rounded-full transition-all duration-700 ease-out shadow-sm ${disk.PctUsed > 90 ? 'bg-red-500' :
                                                disk.PctUsed > 75 ? 'bg-yellow-500' :
                                                    'bg-emerald-500'
                                                }`}
                                            style={{ width: `${disk.PctUsed}%` }}
                                        ></div>
                                    </div>
                                </div>
                            ) : (
                                <div className="bg-red-500/5 p-4 rounded-2xl border border-red-500/20 flex items-center gap-3 text-red-500 shadow-lg">
                                    <Warning size={18} weight="fill" />
                                    <span className="text-xs font-black uppercase tracking-tighter">
                                        {disk.Error || 'Sistema Offline'}
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {!filteredDisks?.length && (
                    <div className="col-span-full py-20 text-center opacity-50">
                        <Info size={32} className="mx-auto mb-2" />
                        <p className="font-medium text-sm">Nenhum disco encontrado</p>
                    </div>
                )}
            </div>

            {/* --- Disk Detail Modal - COMPACT PREMIUM GLASS --- */}
            {selectedDisk && (
                <div
                    className="fixed inset-0 bg-black/20 flex items-center justify-center z-[110] p-4"
                    onClick={() => setSelectedDisk(null)}
                >
                    <div
                        className={`relative bg-white/[0.04] backdrop-blur-[40px] backdrop-saturate-[150%] border border-white/20 rounded-[32px] max-w-xl w-full max-h-[90vh] shadow-[0_32px_128px_-20px_rgba(0,0,0,0.7)] flex flex-col overflow-hidden select-none transition-shadow ${isDragging ? 'shadow-white/10 ring-1 ring-white/20 z-50' : 'z-10'}`}
                        style={{
                            backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%)',
                            transform: `translate(${position.x}px, ${position.y}px)`,
                            transition: isDragging ? 'none' : 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), shadow 0.3s ease, opacity 0.3s ease',
                            opacity: selectedDisk ? 1 : 0
                        }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Header - Compact Crystal (Draggable Handle) */}
                        <div
                            onMouseDown={startDragging}
                            className="sticky top-0 bg-white/[0.02] backdrop-blur-xl border-b border-white/10 p-5 flex items-center justify-between z-10 cursor-grab active:cursor-grabbing"
                        >
                            <div className="flex items-center gap-3">
                                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br border flex items-center justify-center shadow-lg transition-all ${selectedDisk.Status === 'Online'
                                    ? 'from-primary/30 to-primary/5 border-primary/30 text-primary'
                                    : 'from-gray-600/30 to-gray-600/5 border-gray-600/30 text-gray-400'
                                    }`}>
                                    <HardDrives size={24} weight="fill" />
                                </div>
                                <div className="space-y-0.5">
                                    <h2 className="text-xl font-bold text-white tracking-tight leading-none">
                                        {selectedDisk.Server}
                                    </h2>
                                    <div className="flex items-center gap-2 pt-0.5">
                                        <span className="bg-primary/40 text-white px-1.5 py-0.5 rounded text-[9px] font-black uppercase tracking-widest border border-white/10">
                                            {selectedDisk.Drive}
                                        </span>
                                        <p className="text-xs text-zinc-400 font-medium opacity-80">@{selectedDisk.Label || 'Volume Local'}</p>
                                    </div>
                                </div>
                            </div>
                            <button
                                onClick={() => setSelectedDisk(null)}
                                className="w-8 h-8 flex items-center justify-center rounded-full bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 transition-all active:scale-90 shadow-[0_0_15px_rgba(239,68,68,0.1)] group"
                            >
                                <X size={14} weight="bold" className="group-hover:scale-110 transition-transform" />
                            </button>
                        </div>

                        {/* Content - Thinner spacing */}
                        <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar">
                            {/* Status Badge */}
                            <div className="flex items-center">
                                <span className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider flex items-center gap-2 border ${selectedDisk.Status === 'Online'
                                    ? 'bg-emerald-500/20 text-emerald-400 border-white/10'
                                    : 'bg-red-500/20 text-red-400 border-white/10'
                                    }`}>
                                    <div className={`w-1.5 h-1.5 rounded-full ${selectedDisk.Status === 'Online' ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,1)] animate-pulse' : 'bg-red-400'}`}></div>
                                    {selectedDisk.Status === 'Online' ? 'Active Volume' : 'Critical State'}
                                </span>
                            </div>

                            {/* Info Grid - Standardized but tighter */}
                            <div className="grid grid-cols-2 gap-6">
                                {/* Basic Info Section */}
                                <div className="space-y-3">
                                    <h3 className="text-[11px] font-bold text-primary uppercase tracking-wider flex items-center gap-2">
                                        <Info size={14} weight="fill" />
                                        Básico
                                    </h3>
                                    <div className="space-y-3">
                                        <InfoField label="Hostname" value={selectedDisk.Server} />
                                        <InfoField label="Drive" value={selectedDisk.Drive} />
                                    </div>
                                </div>

                                {/* Environment Section */}
                                <div className="space-y-3">
                                    <h3 className="text-[11px] font-bold text-primary uppercase tracking-wider flex items-center gap-2">
                                        <ShieldCheck size={14} weight="fill" />
                                        Sistema
                                    </h3>
                                    <div className="space-y-3">
                                        <InfoField label="OS" value={selectedDisk.OS ? (selectedDisk.OS.length > 20 ? selectedDisk.OS.substring(0, 20) + '...' : selectedDisk.OS) : 'Windows Server'} />
                                        <InfoField label="Status" value={selectedDisk.Status === 'Online' ? 'Stable' : 'Offline'} />
                                    </div>
                                </div>
                            </div>

                            {/* Capacity Metrics - More compact boxes */}
                            <div className="space-y-3">
                                <h3 className="text-[11px] font-bold text-primary uppercase tracking-wider flex items-center gap-2">
                                    <Tag size={14} weight="fill" />
                                    Capacidade
                                </h3>
                                <div className="grid grid-cols-3 gap-3">
                                    {[
                                        { l: 'TOTAL', v: selectedDisk.TotalGB, c: 'text-white' },
                                        { l: 'LIVRE', v: selectedDisk.FreeGB, c: 'text-emerald-400' },
                                        { l: 'USADO', v: selectedDisk.UsedGB, c: 'text-red-400' }
                                    ].map((it, i) => (
                                        <div key={i} className="bg-white/[0.03] border border-white/10 p-3.5 rounded-xl text-center shadow-inner">
                                            <div className="text-[9px] text-zinc-500 font-bold uppercase tracking-widest mb-0.5 opacity-60">{it.l}</div>
                                            <div className={`text-base font-black ${it.c} tracking-tighter`}>{it.v}<span className="text-[9px] ml-0.5 opacity-40">GB</span></div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Consumption Indicator - Refined */}
                            <div className="pt-5 border-t border-white/10 space-y-3">
                                <div className="flex justify-between items-end px-1">
                                    <div className="space-y-0.5">
                                        <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest">Analytics</p>
                                        <p className="text-sm font-bold text-white uppercase tracking-tight">Ocupação</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-xl font-black text-white tracking-tighter">{selectedDisk.PctUsed}%</p>
                                    </div>
                                </div>
                                <div className="h-3 bg-black/40 rounded-full border border-white/10 overflow-hidden p-0.5 relative">
                                    <div
                                        className={`h-full rounded-full transition-all duration-1000 ease-out relative ${selectedDisk.PctUsed > 90 ? 'bg-gradient-to-r from-red-600 to-red-400 shadow-[0_0_10px_rgba(239,68,68,0.5)]' :
                                            selectedDisk.PctUsed > 75 ? 'bg-gradient-to-r from-yellow-600 to-yellow-400' :
                                                'bg-gradient-to-r from-emerald-600 to-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.3)]'
                                            }`}
                                        style={{ width: `${selectedDisk.PctUsed}%` }}
                                    >
                                        <div className="absolute inset-0 bg-white/20 opacity-30 animation-shine"></div>
                                    </div>
                                </div>
                            </div>

                            {/* Footer - Compact Buttons */}
                            <div className="pt-2 flex gap-3">
                                <button
                                    onClick={() => setSelectedDisk(null)}
                                    className="flex-[1.5] bg-white hover:bg-zinc-200 text-black px-4 py-3 rounded-xl font-bold text-xs transition-all active:scale-95"
                                >
                                    Scan Unidade
                                </button>
                                <button
                                    onClick={() => setSelectedDisk(null)}
                                    className="flex-1 bg-white/5 hover:bg-white/10 text-white px-4 py-3 rounded-xl font-bold text-xs transition-all border border-white/10"
                                >
                                    Fechar
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
const InfoField = ({ label, value }: { label: string, value?: string }) => (
    <div>
        <div className="text-[10px] text-dark-muted uppercase tracking-wider font-bold mb-1">{label}</div>
        <div className="text-sm font-semibold text-white">{value || '-'}</div>
    </div>
)

export default ADStorage
