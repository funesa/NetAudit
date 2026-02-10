import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Users, MagnifyingGlass, Key, LockOpen, UserCircle, ShieldCheck, Warning, List, SquaresFour, X } from '@phosphor-icons/react'
import api from '../services/api'
import type { ADUser } from '../types'

const ADUsers = () => {
    const [searchTerm, setSearchTerm] = useState('')
    const [viewMode, setViewMode] = useState<'list' | 'cards'>(() => {
        const saved = localStorage.getItem('adUsersViewMode')
        return (saved === 'cards' || saved === 'list') ? saved : 'list'
    })
    const [selectedUser, setSelectedUser] = useState<ADUser | null>(null)
    const [showModal, setShowModal] = useState(false)
    const [position, setPosition] = useState({ x: 0, y: 0 })
    const [isDragging, setIsDragging] = useState(false)
    const dragStart = useRef({ x: 0, y: 0 })

    // Reset position when modal closes/opens
    useEffect(() => {
        if (!showModal) {
            setPosition({ x: 0, y: 0 })
        }
    }, [showModal])

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

    // Save view mode preference to localStorage
    useEffect(() => {
        localStorage.setItem('adUsersViewMode', viewMode)
    }, [viewMode])

    const { data: users, isLoading, error } = useQuery<ADUser[]>({
        queryKey: ['adUsers'],
        queryFn: async () => {
            const response = await api.get('/api/ad/users')
            return response.data
        },
    })

    const resetPassword = useMutation({
        mutationFn: async ({ username, password }: { username: string, password: string }) => {
            const response = await api.post('/api/ad/reset-password', { username, password })
            return response.data
        },
        onSuccess: (data) => {
            if (data.success) {
                alert('Senha alterada com sucesso!')
            } else {
                alert('Erro ao alterar senha: ' + data.message)
            }
        },
    })

    const filteredUsers = users?.filter(user =>
        (user.name?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
        (user.samaccountname?.toLowerCase() || '').includes(searchTerm.toLowerCase())
    )

    const handleResetPassword = (username: string) => {
        const newPass = prompt('Digite a nova senha para ' + username)
        if (newPass) {
            resetPassword.mutate({ username, password: newPass })
        }
    }

    const handleUserClick = (user: ADUser) => {
        setSelectedUser(user)
        setShowModal(true)
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-2 border-dark-border border-t-primary rounded-full animate-spin"></div>
                    <span className="text-dark-muted text-sm font-medium">Carregando usuários...</span>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="bg-red-500/5 border border-red-500/20 p-8 rounded-xl text-center">
                <Warning size={32} className="text-red-500 mx-auto mb-4" />
                <h3 className="text-dark-text font-semibold text-lg mb-2">Erro ao carregar AD</h3>
                <p className="text-dark-muted text-sm">Verifique conexões e permissões do Active Directory.</p>
            </div>
        )
    }

    return (
        <div className="page-transition space-y-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="space-y-1">
                    <h1 className="text-3xl font-bold text-dark-text tracking-tight flex items-center gap-3">
                        <Users size={32} className="text-primary" weight="fill" />
                        Usuários AD
                    </h1>
                    <p className="text-dark-muted text-sm">Gerenciamento de identidades do domínio.</p>
                </div>

                <div className="flex items-center gap-3">
                    {/* View Toggle */}
                    <div className="bg-dark-surface p-1 rounded-full border border-dark-border flex items-center gap-1">
                        <button
                            onClick={() => setViewMode('list')}
                            className={`p-2.5 rounded-full transition-all ${viewMode === 'list' ? 'bg-primary text-white' : 'text-dark-muted hover:text-white'}`}
                            title="Visualização em Lista"
                        >
                            <List size={18} weight={viewMode === 'list' ? 'fill' : 'regular'} />
                        </button>
                        <button
                            onClick={() => setViewMode('cards')}
                            className={`p-2.5 rounded-full transition-all ${viewMode === 'cards' ? 'bg-primary text-white' : 'text-dark-muted hover:text-white'}`}
                            title="Visualização em Cards"
                        >
                            <SquaresFour size={18} weight={viewMode === 'cards' ? 'fill' : 'regular'} />
                        </button>
                    </div>

                    {/* Search Bar */}
                    <div className="bg-dark-surface p-1 rounded-full border border-dark-border shadow-sm flex items-center gap-2 min-w-[300px]">
                        <div className="flex-1 flex items-center gap-3 px-4 py-2 bg-transparent">
                            <MagnifyingGlass size={16} className="text-dark-muted" />
                            <input
                                type="text"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                placeholder="Buscar usuário..."
                                className="bg-transparent border-none text-dark-text text-sm focus:ring-0 w-full placeholder:text-dark-muted font-normal"
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* List View */}
            {viewMode === 'list' && (
                <div className="ethereal-card overflow-hidden min-h-[400px]">
                    <div className="p-5 border-b border-dark-border bg-dark-panel/50 flex justify-between items-center group">
                        <h2 className="text-sm font-semibold text-dark-text flex items-center gap-2">
                            <ShieldCheck size={18} className="text-primary" />
                            Usuários Identificados
                        </h2>
                        <span className="bg-dark-surface px-3 py-1 rounded-md text-[11px] font-medium text-dark-muted border border-dark-border">
                            {filteredUsers?.length || 0} de {users?.length || 0}
                        </span>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-dark-panel/30 text-[12px] font-medium text-dark-muted border-b border-dark-border">
                                    <th className="px-6 py-4 font-medium">Usuário</th>
                                    <th className="px-6 py-4 font-medium">Nome</th>
                                    <th className="px-6 py-4 font-medium">Departamento</th>
                                    <th className="px-6 py-4 font-medium text-center">Status</th>
                                    <th className="px-6 py-4 font-medium text-right">Ações</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-dark-border">
                                {filteredUsers?.map((user, idx) => (
                                    <tr
                                        key={idx}
                                        onClick={() => handleUserClick(user)}
                                        className="hover:bg-dark-panel/40 transition-colors group cursor-pointer"
                                    >
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded-lg bg-dark-surface border border-dark-border flex items-center justify-center text-dark-muted group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                                                    <UserCircle size={20} weight="fill" className={user.enabled ? "opacity-100" : "opacity-50"} />
                                                </div>
                                                <div className="min-w-0">
                                                    <div className="text-sm font-medium text-dark-text truncate">
                                                        {user.samaccountname}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-dark-muted">
                                            {user.name}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="text-sm text-dark-text">{user.department || '-'}</div>
                                            <div className="text-[11px] text-dark-muted">{user.title || ''}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex justify-center">
                                                <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${user.enabled
                                                    ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                                                    : 'bg-red-500/10 text-red-500 border-red-500/20'
                                                    }`}>
                                                    {user.enabled ? 'Ativo' : 'Inativo'}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex justify-end gap-2 opacity-60 group-hover:opacity-100 transition-opacity">
                                                <button
                                                    onClick={() => handleResetPassword(user.samaccountname)}
                                                    className="p-2 hover:bg-dark-surface rounded-lg text-dark-muted hover:text-primary transition-colors"
                                                    title="Resetar Senha"
                                                >
                                                    <Key size={16} />
                                                </button>
                                                <button
                                                    className="p-2 hover:bg-dark-surface rounded-lg text-dark-muted hover:text-indigo-400 transition-colors"
                                                    title="Desbloquear Conta"
                                                >
                                                    <LockOpen size={16} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Card View */}
            {viewMode === 'cards' && (
                <div className="space-y-6">
                    <div className="flex items-center justify-between px-2">
                        <h2 className="text-sm font-semibold text-dark-text flex items-center gap-2">
                            <ShieldCheck size={18} className="text-primary" />
                            Usuários Identificados
                        </h2>
                        <span className="bg-dark-surface px-3 py-1 rounded-md text-[11px] font-medium text-dark-muted border border-dark-border">
                            {filteredUsers?.length || 0} de {users?.length || 0}
                        </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                        {filteredUsers?.map((user, idx) => (
                            <div
                                key={idx}
                                onClick={() => handleUserClick(user)}
                                className="ethereal-card p-6 hover:border-primary/30 transition-all group relative overflow-hidden cursor-pointer rounded-3xl"
                            >
                                {/* Actions (top-right) */}
                                <div className="absolute top-3 right-3 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            handleResetPassword(user.samaccountname)
                                        }}
                                        className="p-2 hover:bg-dark-surface rounded-full text-dark-muted hover:text-primary transition-all shadow-sm"
                                        title="Resetar Senha"
                                    >
                                        <Key size={16} weight="bold" />
                                    </button>
                                    <button
                                        onClick={(e) => e.stopPropagation()}
                                        className="p-2 hover:bg-dark-surface rounded-full text-dark-muted hover:text-indigo-400 transition-all shadow-sm"
                                        title="Desbloquear Conta"
                                    >
                                        <LockOpen size={16} weight="bold" />
                                    </button>
                                </div>

                                {/* Card Content */}
                                <div className="flex flex-col items-center text-center space-y-5">
                                    {/* Avatar */}
                                    <div className={`w-24 h-24 rounded-3xl bg-gradient-to-br border-2 flex items-center justify-center text-3xl font-black shadow-lg transition-transform group-hover:scale-105 ${user.enabled
                                        ? 'from-primary/20 to-primary/5 border-primary/30 text-primary'
                                        : 'from-gray-600/20 to-gray-600/5 border-gray-600/30 text-gray-500'
                                        }`}>
                                        {user.samaccountname.substring(0, 2).toUpperCase()}
                                    </div>

                                    {/* User Info */}
                                    <div className="space-y-2 w-full min-h-[60px]">
                                        <h3 className="font-bold text-white text-base leading-tight line-clamp-2">
                                            {user.name || user.samaccountname}
                                        </h3>
                                        <p className="text-xs text-dark-muted font-medium">@{user.samaccountname}</p>
                                    </div>

                                    {/* Status Badge */}
                                    <div className={`w-full px-4 py-2.5 rounded-full text-xs font-bold uppercase tracking-wider transition-colors ${user.enabled
                                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                        : 'bg-red-500/10 text-red-400 border border-red-500/20'
                                        }`}>
                                        {user.enabled ? '● Ativo' : '● Inativo'}
                                    </div>

                                    {/* Additional Info */}
                                    <div className="w-full pt-4 border-t border-dark-border space-y-3">
                                        {(user.department || user.title) ? (
                                            <>
                                                {user.department && (
                                                    <div className="text-left">
                                                        <div className="text-[10px] text-dark-muted uppercase tracking-wider font-bold mb-1.5">Departamento</div>
                                                        <div className="text-sm font-semibold text-white line-clamp-1">{user.department}</div>
                                                    </div>
                                                )}
                                                {user.title && (
                                                    <div className="text-left">
                                                        <div className="text-[10px] text-dark-muted uppercase tracking-wider font-bold mb-1.5">Cargo</div>
                                                        <div className="text-sm font-semibold text-white line-clamp-1">{user.title}</div>
                                                    </div>
                                                )}
                                            </>
                                        ) : (
                                            <div className="text-center text-xs text-dark-muted/50 italic py-3">
                                                Sem informações adicionais
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* User Details Modal - COMPACT APPLE GLASS */}
            {showModal && selectedUser && (
                <div
                    className="fixed inset-0 bg-black/20 flex items-center justify-center z-[110] p-4"
                    onClick={() => setShowModal(false)}
                >
                    <div
                        className={`relative bg-white/[0.04] backdrop-blur-[40px] backdrop-saturate-[150%] border border-white/20 rounded-[32px] max-w-xl w-full max-h-[90vh] shadow-[0_32px_128px_-20px_rgba(0,0,0,0.7)] flex flex-col overflow-hidden select-none transition-shadow ${isDragging ? 'shadow-white/10 ring-1 ring-white/20 z-50' : 'z-10'}`}
                        style={{
                            backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%)',
                            transform: `translate(${position.x}px, ${position.y}px)`,
                            transition: isDragging ? 'none' : 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), shadow 0.3s ease, opacity 0.3s ease'
                        }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Header - Compact Crystal */}
                        <div
                            onMouseDown={startDragging}
                            className="sticky top-0 bg-white/[0.02] backdrop-blur-xl border-b border-white/10 p-5 flex items-center justify-between z-10 cursor-grab active:cursor-grabbing"
                        >
                            <div className="flex items-center gap-3">
                                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br border flex items-center justify-center text-xl font-black shadow-lg transition-transform ${selectedUser.enabled
                                    ? 'from-primary/30 to-primary/5 border-primary/30 text-primary'
                                    : 'from-gray-600/30 to-gray-600/5 border-gray-600/30 text-gray-500'
                                    }`}>
                                    {selectedUser.samaccountname.substring(0, 2).toUpperCase()}
                                </div>
                                <div className="space-y-0.5">
                                    <h2 className="text-lg font-bold text-white tracking-tight leading-none truncate max-w-[200px]">
                                        {selectedUser.name || selectedUser.samaccountname}
                                    </h2>
                                    <p className="text-xs text-zinc-400 font-medium opacity-80 pt-0.5">@{selectedUser.samaccountname}</p>
                                </div>
                            </div>
                            <button
                                onClick={() => setShowModal(false)}
                                className="w-8 h-8 flex items-center justify-center rounded-full bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 transition-all active:scale-90 shadow-[0_0_15px_rgba(239,68,68,0.1)] group"
                            >
                                <X size={14} weight="bold" className="group-hover:scale-110 transition-transform" />
                            </button>
                        </div>

                        {/* Content - Thinner spacing */}
                        <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar">
                            {/* Status Badges */}
                            <div className="flex items-center gap-2">
                                <span className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider flex items-center gap-2 border ${selectedUser.enabled
                                    ? 'bg-emerald-500/20 text-emerald-400 border-white/10'
                                    : 'bg-red-500/20 text-red-400 border-white/10'
                                    }`}>
                                    <div className={`w-1.5 h-1.5 rounded-full ${selectedUser.enabled ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,1)] animate-pulse' : 'bg-red-400'}`}></div>
                                    {selectedUser.enabled ? 'Conta Ativa' : 'Conta Inativa'}
                                </span>
                                {selectedUser.locked && (
                                    <span className="px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider bg-orange-500/20 text-orange-400 border border-white/10 flex items-center gap-2">
                                        🔒 Bloqueado
                                    </span>
                                )}
                            </div>

                            {/* Info Grid - Standardized tighter */}
                            <div className="grid grid-cols-2 gap-6">
                                {/* Basic Info Section */}
                                <div className="space-y-3">
                                    <h3 className="text-[11px] font-bold text-primary uppercase tracking-wider flex items-center gap-2">
                                        <UserCircle size={14} weight="fill" />
                                        Identidade
                                    </h3>
                                    <div className="space-y-3">
                                        <InfoRow label="Nome" value={selectedUser.name} />
                                        <InfoRow label="Email" value={selectedUser.mail} />
                                    </div>
                                </div>

                                {/* Organization Section */}
                                <div className="space-y-3">
                                    <h3 className="text-[11px] font-bold text-primary uppercase tracking-wider flex items-center gap-2">
                                        <ShieldCheck size={14} weight="fill" />
                                        Domínio
                                    </h3>
                                    <div className="space-y-3">
                                        <InfoRow label="Departamento" value={selectedUser.department} />
                                        <InfoRow label="Último Login" value={selectedUser.lastlogon} />
                                    </div>
                                </div>
                            </div>

                            {/* Distinguished Name - Compact Box */}
                            <div className="space-y-2 pt-2">
                                <h3 className="text-[11px] font-bold text-primary uppercase tracking-wider">Caminho LDAP</h3>
                                <div className="bg-white/[0.03] border border-white/5 rounded-xl p-3 shadow-inner">
                                    <code className="text-[10px] text-zinc-500 font-mono break-all leading-relaxed whitespace-pre-wrap">
                                        {selectedUser.distinguishedname}
                                    </code>
                                </div>
                            </div>

                            {/* Groups Section */}
                            {selectedUser.groups && selectedUser.groups.length > 0 && (
                                <div className="space-y-3">
                                    <h3 className="text-[11px] font-bold text-primary uppercase tracking-wider flex items-center gap-2">
                                        <SquaresFour size={14} weight="fill" />
                                        Membro de ({selectedUser.groups.length})
                                    </h3>
                                    <div className="flex flex-wrap gap-2 max-h-[120px] overflow-y-auto pr-2 custom-scrollbar">
                                        {selectedUser.groups.map((group, idx) => (
                                            <span
                                                key={idx}
                                                className="px-2.5 py-1.5 bg-white/[0.03] border border-white/10 rounded-lg text-[10px] text-zinc-300 font-bold tracking-tight"
                                            >
                                                {group}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Action Footer standadized */}
                            <div className="pt-2 flex gap-3">
                                <button
                                    onClick={() => {
                                        handleResetPassword(selectedUser.samaccountname)
                                        setShowModal(false)
                                    }}
                                    className="flex-[1.5] bg-white hover:bg-zinc-200 text-black px-4 py-3 rounded-xl font-bold text-xs transition-all active:scale-95 flex items-center justify-center gap-2"
                                >
                                    <Key size={16} weight="bold" />
                                    Resetar Senha
                                </button>
                                <button
                                    onClick={() => setShowModal(false)}
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

// Helper component for info rows
const InfoRow = ({ label, value }: { label: string, value?: string }) => (
    <div>
        <div className="text-[10px] text-dark-muted uppercase tracking-wider font-bold mb-1">{label}</div>
        <div className="text-sm font-semibold text-white">{value || '-'}</div>
    </div>
)

export default ADUsers
