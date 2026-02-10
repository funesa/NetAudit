import { useState } from 'react'
import { SignIn, Lock, User, Brain } from '@phosphor-icons/react'
import api from '../services/api'

interface LoginProps {
    onLogin: () => void
}

const Login = ({ onLogin }: LoginProps) => {
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        setError('')

        try {
            const response = await api.post('/api/login', {
                username,
                password,
            })

            if (response.data.success) {
                localStorage.setItem('token', 'authenticated')
                localStorage.setItem('username', username)
                localStorage.setItem('permissions', JSON.stringify(response.data.permissions || {}))
                localStorage.setItem('is_master', response.data.is_master ? 'true' : 'false')
                onLogin()
            } else {
                setError(response.data.message || 'Credenciais inválidas')
            }
        } catch (err: any) {
            setError(err.response?.data?.message || 'Erro ao conectar com o servidor')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-dark-bg font-sans selection:bg-primary/20 selection:text-primary">

            <div className="w-full max-w-sm animate-in zoom-in-95 duration-500">
                {/* Minimalist Brand Header */}
                <div className="text-center mb-8 space-y-4">
                    <div className="inline-flex items-center justify-center w-12 h-12 bg-dark-panel border border-dark-border rounded-xl shadow-sm mb-4">
                        <Brain size={24} weight="fill" className="text-primary" />
                    </div>
                    <div className="space-y-1">
                        <h1 className="text-2xl font-semibold tracking-tight text-white">
                            Bem-vindo de volta
                        </h1>
                        <p className="text-sm text-dark-muted">
                            Acesse sua conta para continuar
                        </p>
                    </div>
                </div>

                {/* Ethereal Card Form */}
                <div className="ethereal-card p-6 md:p-8 hover:border-dark-border hover:shadow-clean transition-none">
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-1.5">
                            <label className="text-[13px] font-medium text-white">Usuário</label>
                            <div className="relative group">
                                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-muted group-focus-within:text-white transition-colors">
                                    <User size={18} />
                                </div>
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    className="w-full pl-10 pr-3 py-2.5 bg-dark-surface border border-dark-border rounded-lg text-sm text-white focus:outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500 transition-all placeholder:text-dark-muted font-normal"
                                    placeholder="ex: admin"
                                    autoComplete="username"
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-1.5">
                            <div className="flex items-center justify-between">
                                <label className="text-[13px] font-medium text-white">Senha</label>
                            </div>
                            <div className="relative group">
                                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-muted group-focus-within:text-white transition-colors">
                                    <Lock size={18} />
                                </div>
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="w-full pl-10 pr-3 py-2.5 bg-dark-surface border border-dark-border rounded-lg text-sm text-white focus:outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500 transition-all placeholder:text-dark-muted font-normal"
                                    placeholder="••••••••"
                                    autoComplete="current-password"
                                    required
                                />
                            </div>
                        </div>

                        {error && (
                            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-2 animate-in fade-in slide-in-from-top-1">
                                <div className="mt-0.5 text-red-500 shrink-0">
                                    <ShieldCheck size={14} weight="fill" />
                                </div>
                                <p className="text-[12px] text-red-400 font-medium leading-tight">{error}</p>
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full btn-primary flex items-center justify-center gap-2 py-2.5 text-[14px] shadow-none"
                        >
                            {loading ? (
                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                            ) : (
                                <>
                                    <span>Entrar</span>
                                    <SignIn size={16} weight="bold" />
                                </>
                            )}
                        </button>
                    </form>
                </div>

                {/* Footer */}
                <div className="mt-8 text-center">
                    <p className="text-[11px] text-dark-muted font-medium">
                        &copy; 2026 NetAudit Systems.
                    </p>
                </div>
            </div>
        </div>
    )
}

// Icon helper needed for error state
import { ShieldCheck } from '@phosphor-icons/react'

export default Login
