import { useQuery } from '@tanstack/react-query'
import { ShieldWarning, Warning, Clock, MapPin, User, Fingerprint } from '@phosphor-icons/react'
import api from '../services/api'
import type { FailedLogin } from '../types'

const Security = () => {
    const { data, isLoading } = useQuery<{ success: boolean; count: number; logins: FailedLogin[] }>({
        queryKey: ['failedLogins'],
        queryFn: async () => {
            const response = await api.get('/api/security/failed-logins?hours=72')
            return response.data
        },
        refetchInterval: 60000,
    })

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="flex flex-col items-center gap-4">
                    <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
                    <span className="text-gray-400 font-bold animate-pulse uppercase tracking-widest text-xs">Analisando Logs de Segurança...</span>
                </div>
            </div>
        )
    }

    return (
        <div className="page-transition space-y-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="space-y-1">
                    <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
                        <ShieldWarning size={32} className="text-status-error" />
                        Logins Falhados
                    </h1>
                    <p className="text-gray-400 font-medium">Tentativas de acesso negadas no domínio (Últimas 72h)</p>
                </div>

                <div className="bg-dark-panel px-6 py-4 rounded-3xl border border-dark-border shadow-xl flex items-center gap-4">
                    <div className="text-right">
                        <div className="text-[10px] uppercase font-black text-gray-500 tracking-widest">Total de Incidentes</div>
                        <div className="text-2xl font-black text-status-error">{data?.count || 0}</div>
                    </div>
                    <div className="p-3 bg-red-500/10 rounded-2xl">
                        <Warning size={24} className="text-red-500" weight="fill" />
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {data?.logins?.map((login, idx) => (
                    <div key={idx} className="bg-dark-panel p-6 rounded-3xl border border-dark-border shadow-xl hover:border-red-500/30 transition-all group">
                        <div className="flex items-start justify-between mb-6">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-dark-bg rounded-2xl border border-white/5 group-hover:bg-red-500/10 group-hover:text-red-500 transition-all">
                                    <User size={24} weight="fill" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-bold text-white group-hover:text-red-500 transition-colors">{login.user}</h3>
                                    <p className="text-xs text-gray-500 font-black uppercase tracking-widest">Usuário de Domínio</p>
                                </div>
                            </div>
                            <div className="flex flex-col items-end">
                                <span className="text-2xl font-black text-white">{login.count}</span>
                                <span className="text-[10px] text-gray-500 font-black uppercase tracking-tighter">Tentativas</span>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="bg-dark-bg/50 p-4 rounded-2xl border border-white/5 space-y-1">
                                <div className="flex items-center gap-2 text-[10px] font-black text-gray-500 uppercase tracking-widest">
                                    <MapPin size={12} className="text-primary" /> Origem
                                </div>
                                <div className="text-sm font-mono font-bold text-gray-300">{login.source_ip || 'Desconhecida'}</div>
                            </div>
                            <div className="bg-dark-bg/50 p-4 rounded-2xl border border-white/5 space-y-1">
                                <div className="flex items-center gap-2 text-[10px] font-black text-gray-500 uppercase tracking-widest">
                                    <Clock size={12} className="text-primary" /> Última Vez
                                </div>
                                <div className="text-sm font-bold text-gray-300">{login.timestamp}</div>
                            </div>
                        </div>

                        <div className="mt-4 flex items-center justify-between">
                            <div className="flex items-center gap-2 opacity-30">
                                <Fingerprint size={16} />
                                <span className="text-[10px] font-mono leading-none">Security ID: 4625</span>
                            </div>
                            <button className="text-[10px] font-black text-primary uppercase tracking-widest hover:underline">
                                Ver Detalhes →
                            </button>
                        </div>
                    </div>
                ))}

                {!data?.logins?.length && (
                    <div className="col-span-full py-20 bg-dark-panel rounded-3xl border border-dark-border border-dashed text-center">
                        <div className="flex flex-col items-center gap-4 opacity-30">
                            <ShieldWarning size={64} weight="thin" />
                            <p className="font-bold text-sm uppercase tracking-[0.2em] italic">Nenhum login falhado detectado recentemente</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

export default Security
