import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { ShieldCheck, Key, Copy, CheckCircle, XCircle, SpinnerGap } from '@phosphor-icons/react'
import api from '../services/api'

interface LicenseInfo {
    hwid: string
    is_premium: boolean
    customer: string
    trial_days_left: number
}

const License = () => {
    const [licenseKey, setLicenseKey] = useState('')
    const [message, setMessage] = useState<{ success: boolean; text: string } | null>(null)

    const { data: info, isLoading } = useQuery<LicenseInfo>({
        queryKey: ['licenseInfo'],
        queryFn: async () => {
            const response = await api.get('/api/license/info')
            return response.data
        }
    })

    const activateMutation = useMutation({
        mutationFn: async (key: string) => {
            const response = await api.post('/api/license/activate', { key })
            return response.data
        },
        onSuccess: (data) => {
            setMessage({ success: data.success, text: data.message })
            if (data.success) {
                setTimeout(() => window.location.href = '/', 2000)
            }
        }
    })

    const copyHWID = () => {
        if (info?.hwid) {
            navigator.clipboard.writeText(info.hwid)
            alert('Hardware ID copiado!')
        }
    }

    if (isLoading) return null

    return (
        <div className="page-transition flex items-center justify-center min-h-[calc(100vh-150px)] px-4">
            <div className="max-w-md w-full glass-card p-10 space-y-8 relative overflow-hidden">
                {/* Decoration */}
                <div className="absolute -top-24 -right-24 w-48 h-48 bg-primary/10 rounded-full blur-3xl"></div>

                <div className="text-center space-y-4">
                    <div className="inline-flex p-4 rounded-3xl bg-primary/10 text-primary shadow-inner">
                        <ShieldCheck size={48} weight="duotone" />
                    </div>
                    <div className="space-y-2">
                        <h1 className="text-3xl font-black text-white tracking-tight">Ativar NetAudit PRO</h1>
                        <p className="text-gray-400 text-sm font-medium">Libere recursos avançados de AD, IA e Monitoramento</p>
                    </div>
                </div>

                <div className="bg-dark-bg/50 p-6 rounded-2xl border border-white/5 space-y-3">
                    <div className="flex justify-between items-center text-[10px] font-black text-gray-500 uppercase tracking-widest">
                        <span>Hardware ID</span>
                        <button onClick={copyHWID} className="text-primary hover:text-white transition-colors flex items-center gap-1">
                            <Copy size={14} /> COPIAR
                        </button>
                    </div>
                    <code className="block bg-dark-panel p-3 rounded-lg text-xs font-mono text-gray-300 border border-white/5 break-all">
                        {info?.hwid}
                    </code>
                    <p className="text-[10px] text-gray-500 italic text-center">Envie este ID para seu fornecedor para gerar sua licença.</p>
                </div>

                <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); activateMutation.mutate(licenseKey) }}>
                    <div className="space-y-2">
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-widest px-1">Chave de Licença</label>
                        <div className="flex items-center gap-3 px-4 py-3 bg-dark-bg rounded-2xl border border-white/5 focus-within:border-primary/50 transition-all">
                            <Key size={20} className="text-primary" />
                            <input
                                type="text"
                                value={licenseKey}
                                onChange={(e) => setLicenseKey(e.target.value)}
                                placeholder="XXXXX-XXXXX-XXXXX-XXXXX"
                                className="bg-transparent border-none text-white text-sm focus:ring-0 w-full font-bold placeholder:text-gray-700"
                                required
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={activateMutation.isPending}
                        className="w-full bg-primary hover:bg-primary-dark text-white py-4 rounded-2xl font-black text-sm shadow-xl shadow-primary/20 transition-all flex items-center justify-center gap-3 transform active:scale-95 disabled:opacity-50"
                    >
                        {activateMutation.isPending ? (
                            <SpinnerGap size={20} className="animate-spin" />
                        ) : (
                            <CheckCircle size={20} weight="bold" />
                        )}
                        {activateMutation.isPending ? 'VALIDANDO...' : 'ATIVAR AGORA'}
                    </button>
                </form>

                {message && (
                    <div className={`p-4 rounded-2xl border flex items-center gap-3 animate-in fade-in slide-in-from-top-4 ${message.success
                            ? 'bg-status-new/10 border-status-new/20 text-status-new'
                            : 'bg-status-error/10 border-status-error/20 text-status-error'
                        }`}>
                        {message.success ? <CheckCircle size={20} weight="fill" /> : <XCircle size={20} weight="fill" />}
                        <span className="text-xs font-bold">{message.text}</span>
                    </div>
                )}
            </div>
        </div>
    )
}

export default License
