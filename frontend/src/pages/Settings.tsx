import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import {
    Gear, UsersThree, Shield, Sliders, HardDrive, Bell, Palette,
    Robot, DesktopTower, Globe, TreeStructure, UserGear, Lock,
    Plug, Check, Trash, Plus, Pencil, WarningCircle, Headset, Key, IdentificationCard,
    List, SquaresFour, X
} from '@phosphor-icons/react'
import api from '../services/api'

interface GeneralSettings {
    ai_enabled: boolean
    ad_enabled: boolean
    tickets_enabled: boolean
    dashboard_refresh_interval: number
}

interface ADConfigStatus {
    configured: boolean
    enabled: boolean
    lastConnection: string
    config?: {
        server: string
        domain: string
        baseDN: string
        adminUser: string
    }
}

interface SystemUser {
    username: string
    role: string
    full_name: string
    is_active: boolean
    is_master: boolean
    last_login?: string
    permissions?: Record<string, boolean>
}

const Settings = () => {
    const queryClient = useQueryClient()
    const [activeTab, setActiveTab] = useState('general')
    const [userViewMode, setUserViewMode] = useState<'list' | 'cards'>(() => {
        const saved = localStorage.getItem('systemUsersViewMode')
        return (saved === 'cards' || saved === 'list') ? saved : 'list'
    })

    // --- User Modal State ---
    const [isUserModalOpen, setIsUserModalOpen] = useState(false)
    const [editingUser, setEditingUser] = useState<SystemUser | null>(null)
    const [userForm, setUserForm] = useState({
        username: '',
        password: '',
        full_name: '',
        role: 'user',
        is_active: true,
        permissions: {
            view_all: true,
            run_scan: false,
            manage_ad: false,
            manage_settings: false,
            manage_system_users: false
        } as Record<string, boolean>
    })

    const handleOpenUserModal = (user?: SystemUser) => {
        if (user) {
            setEditingUser(user)
            setUserForm({
                username: user.username,
                password: '', // Não carrega senha
                full_name: user.full_name,
                role: user.role,
                is_active: user.is_active,
                permissions: user.permissions || { view_all: true }
            })
        } else {
            setEditingUser(null)
            setUserForm({
                username: '',
                password: '',
                full_name: '',
                role: 'user',
                is_active: true,
                permissions: { view_all: true }
            })
        }
        setIsUserModalOpen(true)
    }

    // --- AD Form State ---
    const [adForm, setAdForm] = useState({
        server: '',
        domain: '',
        baseDN: '',
        adminUser: '',
        adminPass: ''
    })
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

    // --- GLPI Form State ---
    const [glpiForm, setGlpiForm] = useState({
        url: '',
        app_token: '',
        user_token: '',
        login: '',
        password: ''
    })

    // --- Queries ---
    const { data: generalSettings } = useQuery<GeneralSettings>({
        queryKey: ['generalSettings'],
        queryFn: async () => {
            const response = await api.get('/api/settings/general')
            return response.data
        }
    })

    const { data: glpiConfig } = useQuery({
        queryKey: ['glpiConfig'],
        queryFn: async () => {
            const response = await api.get('/api/glpi/config')
            return response.data
        }
    })

    useEffect(() => {
        if (glpiConfig) {
            setGlpiForm(prev => ({
                ...prev,
                url: glpiConfig.url || '',
                app_token: glpiConfig.app_token || '',
                user_token: glpiConfig.user_token || '',
                login: glpiConfig.login || ''
            }))
        }
    }, [glpiConfig])

    const { data: adStatus } = useQuery<ADConfigStatus>({
        queryKey: ['adStatus'],
        queryFn: async () => {
            const response = await api.get('/api/ad/status')
            return response.data
        }
    })

    // Populate form when AD status loads
    useEffect(() => {
        if (adStatus?.config) {
            setAdForm(prev => ({
                ...prev,
                server: adStatus.config?.server || '',
                domain: adStatus.config?.domain || '',
                baseDN: adStatus.config?.baseDN || '',
                adminUser: adStatus.config?.adminUser || ''
            }))
        }
    }, [adStatus])

    const { data: systemUsers } = useQuery<SystemUser[]>({
        queryKey: ['systemUsers'],
        queryFn: async () => {
            const response = await api.get('/api/system/users')
            return response.data
        }
    })

    // --- Mutations ---
    const updateGeneralMutation = useMutation({
        mutationFn: (newSettings: Partial<GeneralSettings>) => api.post('/api/settings/general', newSettings),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['generalSettings'] }),
        onError: (err: any) => alert('Erro ao atualizar configurações: ' + (err.response?.data?.message || err.message))
    })

    const saveGLPIConfigMutation = useMutation({
        mutationFn: (config: typeof glpiForm) => api.post('/api/glpi/config', config),
        onSuccess: (res) => {
            if (res.data.success) {
                queryClient.invalidateQueries({ queryKey: ['glpiConfig'] })
                alert('Configuração do GLPI salva e testada com sucesso!')
            } else {
                alert('Erro ao conectar GLPI: ' + res.data.message)
            }
        },
        onError: (err: any) => alert('Erro crítico ao salvar GLPI: ' + (err.response?.data?.message || err.message))
    })

    const saveADConfigMutation = useMutation({
        mutationFn: (config: typeof adForm) => api.post('/api/ad/save-config', config),
        onSuccess: (res) => {
            if (res.data.success) {
                queryClient.invalidateQueries({ queryKey: ['adStatus'] })
                alert('Configuração do AD salva com sucesso!')
            } else {
                alert('Erro ao salvar: ' + res.data.message)
            }
        },
        onError: (err: any) => alert('Erro crítico ao salvar: ' + (err.response?.data?.message || err.message))
    })

    const testADConnectionMutation = useMutation({
        mutationFn: (config: typeof adForm) => api.post('/api/ad/test-connection', config),
        onSuccess: (res) => setTestResult(res.data),
        onError: (err: any) => setTestResult({
            success: false,
            message: 'Erro na requisição: ' + (err.response?.data?.message || err.message)
        })
    })

    const saveUserMutation = useMutation({
        mutationFn: (data: any) => {
            if (editingUser) {
                return api.put(`/api/system/users/${editingUser.username}`, data)
            }
            return api.post('/api/system/users', data)
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['systemUsers'] })
            setIsUserModalOpen(false)
            alert(editingUser ? 'Usuário atualizado!' : 'Usuário criado!')
        },
        onError: (err: any) => alert('Erro ao salvar usuário: ' + (err.response?.data?.message || err.message))
    })

    const deleteUserMutation = useMutation({
        mutationFn: (username: string) => api.delete(`/api/system/users/${username}`),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['systemUsers'] })
            alert('Usuário removido.')
        },
        onError: (err: any) => alert('Erro ao remover usuário: ' + (err.response?.data?.message || err.message))
    })

    const tabs = [
        { id: 'general', name: 'Geral', icon: Sliders },
        { id: 'ad', name: 'Diretório Ativo', icon: Shield },
        { id: 'glpi', name: 'Helpdesk / GLPI', icon: Headset },
        { id: 'users', name: 'Usuários do Sistema', icon: UsersThree },
        { id: 'ai', name: 'Atena IA', icon: Robot },
        { id: 'storage', name: 'Banco de Dados', icon: HardDrive },
        { id: 'notifications', name: 'Notificações', icon: Bell },
        { id: 'appearance', name: 'Aparência', icon: Palette },
    ]

    return (
        <div className="page-transition space-y-8">
            <div className="space-y-1">
                <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
                    <Gear size={28} className="text-primary" />
                    Configurações
                </h1>
                <p className="text-dark-muted font-medium text-sm">Ajuste as preferências do Sentinel Engine</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                {/* Sidebar Navigation */}
                <div className="lg:col-span-1 space-y-1">
                    {tabs.map((tab) => {
                        const Icon = tab.icon
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 text-left font-medium text-sm border ${activeTab === tab.id
                                    ? 'bg-white text-zinc-900 border-zinc-200 shadow-sm'
                                    : 'bg-transparent text-dark-muted hover:text-dark-text hover:bg-dark-surface border-transparent'
                                    }`}
                            >
                                <Icon size={18} weight={activeTab === tab.id ? 'fill' : 'regular'} />
                                {tab.name}
                            </button>
                        )
                    })}
                </div>

                {/* Content Area */}
                <div className="lg:col-span-3 ethereal-card p-6 min-h-[600px]">

                    {/* --- GENERAL SETTINGS --- */}
                    {activeTab === 'general' && (
                        <div className="space-y-6 animate-in">
                            <div>
                                <h2 className="text-lg font-semibold text-white mb-1">Preferências Gerais</h2>
                                <p className="text-sm text-dark-muted">Configurações globais de comportamento do sistema</p>
                            </div>

                            <div className="space-y-4">
                                <div className="flex items-center justify-between p-4 bg-dark-surface rounded-xl border border-dark-border">
                                    <div className="space-y-0.5">
                                        <div className="text-sm font-medium text-white">Integração com Active Directory</div>
                                        <div className="text-xs text-dark-muted">Habilita autenticação e busca de usuários no domínio</div>
                                    </div>
                                    <button
                                        onClick={() => updateGeneralMutation.mutate({ ad_enabled: !generalSettings?.ad_enabled })}
                                        className={`w-10 h-6 rounded-full relative transition-all ${generalSettings?.ad_enabled ? 'bg-primary' : 'bg-zinc-700'}`}
                                    >
                                        <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${generalSettings?.ad_enabled ? 'right-1' : 'left-1'}`}></div>
                                    </button>
                                </div>

                                <div className="flex items-center justify-between p-4 bg-dark-surface rounded-xl border border-dark-border">
                                    <div className="space-y-0.5">
                                        <div className="text-sm font-medium text-white">Integração com GLPI</div>
                                        <div className="text-xs text-dark-muted">Habilita o módulo de Helpdesk e chamados</div>
                                    </div>
                                    <button
                                        onClick={() => updateGeneralMutation.mutate({ tickets_enabled: !generalSettings?.tickets_enabled })}
                                        className={`w-10 h-6 rounded-full relative transition-all ${generalSettings?.tickets_enabled ? 'bg-primary' : 'bg-zinc-700'}`}
                                    >
                                        <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${generalSettings?.tickets_enabled ? 'right-1' : 'left-1'}`}></div>
                                    </button>
                                </div>

                                <div className="flex items-center justify-between p-4 bg-dark-surface rounded-xl border border-dark-border">
                                    <div className="space-y-0.5">
                                        <div className="text-sm font-medium text-white">IA Atena</div>
                                        <div className="text-xs text-dark-muted">Habilita assistente virtual para análise de rede</div>
                                    </div>
                                    <button
                                        onClick={() => updateGeneralMutation.mutate({ ai_enabled: !generalSettings?.ai_enabled })}
                                        className={`w-10 h-6 rounded-full relative transition-all ${generalSettings?.ai_enabled ? 'bg-primary' : 'bg-zinc-700'}`}
                                    >
                                        <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${generalSettings?.ai_enabled ? 'right-1' : 'left-1'}`}></div>
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* --- GLPI SETTINGS --- */}
                    {activeTab === 'glpi' && (
                        <div className="space-y-8 animate-in fade-in duration-300">
                            <div className="flex items-center justify-between">
                                <div>
                                    <h2 className="text-xl font-bold text-white mb-2">Conexão GLPI Helpdesk</h2>
                                    <p className="text-sm text-gray-500">Integre com seu sistema de chamados GLPI ( &ge; v9.5 )</p>
                                </div>
                                <div className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest border ${glpiConfig?.configured ? 'bg-status-success/10 text-status-success border-status-success/20' : 'bg-gray-500/10 text-gray-500 border-white/5'
                                    }`}>
                                    <div className={`w-2 h-2 rounded-full ${glpiConfig?.configured ? 'bg-status-success animate-pulse' : 'bg-gray-500'}`}></div>
                                    {glpiConfig?.configured ? 'Conectado' : 'Desconectado'}
                                </div>
                            </div>

                            <div className="grid grid-cols-1 gap-6 max-w-2xl">
                                <div className="form-group">
                                    <label className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 block">URL da API REST do GLPI</label>
                                    <div className="flex items-center gap-3 px-4 py-3 bg-dark-bg rounded-2xl border border-white/5 focus-within:border-primary/50 transition-all">
                                        <Globe size={18} className="text-primary" />
                                        <input
                                            type="text"
                                            value={glpiForm.url}
                                            onChange={(e) => setGlpiForm({ ...glpiForm, url: e.target.value })}
                                            placeholder="https://suporte.empresa.com/apirest.php"
                                            className="bg-transparent border-none text-white text-sm focus:ring-0 w-full font-bold"
                                        />
                                    </div>
                                    <p className="text-[10px] text-gray-600 mt-2 font-bold ml-1">Certifique-se de habilitar a API REST no GLPI e permitir acesso via App-Token.</p>
                                </div>

                                <div className="form-group">
                                    <label className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 block">App Token (Chave de API)</label>
                                    <div className="flex items-center gap-3 px-4 py-3 bg-dark-bg rounded-2xl border border-white/5 focus-within:border-primary/50 transition-all">
                                        <Key size={18} className="text-primary" />
                                        <input
                                            type="text"
                                            value={glpiForm.app_token}
                                            onChange={(e) => setGlpiForm({ ...glpiForm, app_token: e.target.value })}
                                            placeholder="Ex: NO7s8..."
                                            className="bg-transparent border-none text-white text-sm focus:ring-0 w-full font-bold"
                                        />
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="form-group">
                                        <label className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 block text-primary">Método 1: User Token</label>
                                        <div className="flex items-center gap-3 px-4 py-3 bg-dark-bg rounded-2xl border border-white/5 focus-within:border-primary/50 transition-all">
                                            <IdentificationCard size={18} className="text-primary" />
                                            <input
                                                type="text"
                                                value={glpiForm.user_token}
                                                onChange={(e) => setGlpiForm({ ...glpiForm, user_token: e.target.value })}
                                                placeholder="Token pessoal do usuário"
                                                className="bg-transparent border-none text-white text-sm focus:ring-0 w-full font-bold"
                                            />
                                        </div>
                                    </div>

                                    <div className="form-group opacity-50">
                                        <label className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 block">Método 2: Login & Senha</label>
                                        <div className="flex items-center gap-3 px-4 py-3 bg-dark-bg rounded-2xl border border-white/5 focus-within:border-primary/50 transition-all mb-2">
                                            <UserGear size={18} className="text-gray-500" />
                                            <input
                                                type="text"
                                                value={glpiForm.login}
                                                onChange={(e) => setGlpiForm({ ...glpiForm, login: e.target.value })}
                                                placeholder="Usuário"
                                                className="bg-transparent border-none text-white text-sm focus:ring-0 w-full font-bold placeholder:text-gray-700"
                                            />
                                        </div>
                                        <div className="flex items-center gap-3 px-4 py-3 bg-dark-bg rounded-2xl border border-white/5 focus-within:border-primary/50 transition-all">
                                            <Lock size={18} className="text-gray-500" />
                                            <input
                                                type="password"
                                                value={glpiForm.password}
                                                onChange={(e) => setGlpiForm({ ...glpiForm, password: e.target.value })}
                                                placeholder="Senha"
                                                className="bg-transparent border-none text-white text-sm focus:ring-0 w-full font-bold placeholder:text-gray-700"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <button
                                    onClick={() => saveGLPIConfigMutation.mutate(glpiForm)}
                                    disabled={saveGLPIConfigMutation.isPending}
                                    className="w-full bg-primary hover:bg-primary-dark text-white px-6 py-4 rounded-2xl font-bold text-sm shadow-xl transition-all flex items-center justify-center gap-2 mt-4"
                                >
                                    {saveGLPIConfigMutation.isPending ? (
                                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                                    ) : (
                                        <Check size={20} weight="bold" />
                                    )}
                                    {saveGLPIConfigMutation.isPending ? 'Testando Conexão...' : 'SALVAR & CONECTAR'}
                                </button>
                            </div>
                        </div>
                    )}

                    {/* --- AD SETTINGS --- */}
                    {activeTab === 'ad' && (
                        <div className="space-y-8 animate-in fade-in duration-300">
                            <div className="flex items-center justify-between">
                                <div>
                                    <h2 className="text-xl font-bold text-white mb-2">Conexão Active Directory</h2>
                                    <p className="text-sm text-gray-500">Configure o servidor de domínio para integração total</p>
                                </div>
                                <div className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest border ${adStatus?.configured ? 'bg-status-success/10 text-status-success border-status-success/20' : 'bg-gray-500/10 text-gray-500 border-white/5'
                                    }`}>
                                    <div className={`w-2 h-2 rounded-full ${adStatus?.configured ? 'bg-status-success animate-pulse' : 'bg-gray-500'}`}></div>
                                    {adStatus?.configured ? 'Configurado' : 'Não Configurado'}
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-4">
                                    <div className="form-group">
                                        <label className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 block">Servidor AD (IP ou Hostname)</label>
                                        <div className="flex items-center gap-3 px-4 py-3 bg-dark-bg rounded-2xl border border-white/5 focus-within:border-primary/50 transition-all">
                                            <DesktopTower size={18} className="text-primary" />
                                            <input
                                                type="text"
                                                value={adForm.server}
                                                onChange={(e) => setAdForm({ ...adForm, server: e.target.value })}
                                                placeholder="192.168.1.10"
                                                className="bg-transparent border-none text-white text-sm focus:ring-0 w-full font-bold"
                                            />
                                        </div>
                                    </div>

                                    <div className="form-group">
                                        <label className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 block">Domínio</label>
                                        <div className="flex items-center gap-3 px-4 py-3 bg-dark-bg rounded-2xl border border-white/5 focus-within:border-primary/50 transition-all">
                                            <Globe size={18} className="text-primary" />
                                            <input
                                                type="text"
                                                value={adForm.domain}
                                                onChange={(e) => setAdForm({ ...adForm, domain: e.target.value })}
                                                placeholder="EMPRESA.LOCAL"
                                                className="bg-transparent border-none text-white text-sm focus:ring-0 w-full font-bold"
                                            />
                                        </div>
                                    </div>

                                    <div className="form-group">
                                        <label className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 block">Base DN</label>
                                        <div className="flex items-center gap-3 px-4 py-3 bg-dark-bg rounded-2xl border border-white/5 focus-within:border-primary/50 transition-all">
                                            <TreeStructure size={18} className="text-primary" />
                                            <input
                                                type="text"
                                                value={adForm.baseDN}
                                                onChange={(e) => setAdForm({ ...adForm, baseDN: e.target.value })}
                                                placeholder="DC=empresa,DC=local"
                                                className="bg-transparent border-none text-white text-sm focus:ring-0 w-full font-bold"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-4">
                                    <div className="form-group">
                                        <label className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 block">Usuário Administrador</label>
                                        <div className="flex items-center gap-3 px-4 py-3 bg-dark-bg rounded-2xl border border-white/5 focus-within:border-primary/50 transition-all">
                                            <UserGear size={18} className="text-primary" />
                                            <input
                                                type="text"
                                                value={adForm.adminUser}
                                                onChange={(e) => setAdForm({ ...adForm, adminUser: e.target.value })}
                                                placeholder="administrador"
                                                className="bg-transparent border-none text-white text-sm focus:ring-0 w-full font-bold"
                                            />
                                        </div>
                                    </div>

                                    <div className="form-group">
                                        <label className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 block">Senha do Administrador</label>
                                        <div className="flex items-center gap-3 px-4 py-3 bg-dark-bg rounded-2xl border border-white/5 focus-within:border-primary/50 transition-all">
                                            <Lock size={18} className="text-primary" />
                                            <input
                                                type="password"
                                                value={adForm.adminPass}
                                                onChange={(e) => setAdForm({ ...adForm, adminPass: e.target.value })}
                                                placeholder="••••••••"
                                                className="bg-transparent border-none text-white text-sm focus:ring-0 w-full font-bold"
                                            />
                                        </div>
                                    </div>

                                    <div className="pt-2">
                                        <div className="bg-dark-bg/30 p-4 rounded-2xl border border-white/5 space-y-2">
                                            <div className="flex justify-between text-[10px] font-black text-gray-500 uppercase tracking-widest">
                                                <span>Última Conexão OK</span>
                                                <span className="text-white">{adStatus?.lastConnection || 'Nunca'}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {testResult && (
                                <div className={`p-4 rounded-2xl border flex items-center gap-4 animate-in slide-in-from-top-2 ${testResult.success
                                    ? 'bg-status-success/10 border-status-success/20 text-status-success'
                                    : 'bg-status-error/10 border-status-error/20 text-status-error'
                                    }`}>
                                    {testResult.success ? <Check size={20} weight="fill" /> : <WarningCircle size={20} weight="fill" />}
                                    <span className="text-sm font-bold">{testResult.message}</span>
                                </div>
                            )}

                            <div className="flex gap-4 mt-6">
                                <button
                                    onClick={() => testADConnectionMutation.mutate(adForm)}
                                    disabled={testADConnectionMutation.isPending}
                                    className="flex-1 bg-dark-bg hover:bg-dark-hover text-white px-6 py-3 rounded-xl font-bold text-sm border border-white/10 transition-all flex items-center justify-center gap-2"
                                >
                                    <Plug size={18} /> {testADConnectionMutation.isPending ? 'Testando...' : 'Testar Conexão'}
                                </button>
                                <button
                                    onClick={() => saveADConfigMutation.mutate(adForm)}
                                    disabled={saveADConfigMutation.isPending}
                                    className="flex-1 bg-primary hover:bg-primary-dark text-white px-6 py-3 rounded-xl font-bold text-sm shadow-xl transition-all flex items-center justify-center gap-2"
                                >
                                    <Check size={18} weight="bold" /> {saveADConfigMutation.isPending ? 'Salvando...' : 'Salvar Configuração'}
                                </button>
                            </div>
                        </div>
                    )}

                    {/* --- SYSTEM USERS --- */}
                    {activeTab === 'users' && (
                        <div className="space-y-8 animate-in fade-in duration-300">
                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                                <div>
                                    <h2 className="text-xl font-bold text-white mb-2">Usuários do Sistema</h2>
                                    <p className="text-sm text-gray-500">Gerencie quem tem acesso ao painel do NetAudit</p>
                                </div>
                                <div className="flex items-center gap-3">
                                    {/* View Toggle */}
                                    <div className="bg-dark-surface p-1 rounded-lg border border-dark-border flex items-center gap-1">
                                        <button
                                            onClick={() => setUserViewMode('list')}
                                            className={`p-2 rounded transition-all ${userViewMode === 'list' ? 'bg-primary text-white' : 'text-dark-muted hover:text-white'}`}
                                            title="Visualização em Lista"
                                        >
                                            <List size={18} weight={userViewMode === 'list' ? 'fill' : 'regular'} />
                                        </button>
                                        <button
                                            onClick={() => setUserViewMode('cards')}
                                            className={`p-2 rounded transition-all ${userViewMode === 'cards' ? 'bg-primary text-white' : 'text-dark-muted hover:text-white'}`}
                                            title="Visualização em Cards"
                                        >
                                            <SquaresFour size={18} weight={userViewMode === 'cards' ? 'fill' : 'regular'} />
                                        </button>
                                    </div>
                                    <button
                                        onClick={() => handleOpenUserModal()}
                                        className="bg-primary hover:bg-primary-dark text-white px-5 py-2.5 rounded-full font-bold text-xs shadow-lg transition-all flex items-center gap-2 active:scale-95"
                                    >
                                        <Plus size={16} weight="bold" /> NOVO USUÁRIO
                                    </button>
                                </div>
                            </div>

                            {/* List View */}
                            {userViewMode === 'list' && (
                                <div className="space-y-4">
                                    {systemUsers?.map((user, idx) => (
                                        <div key={idx} className="flex items-center justify-between p-5 bg-dark-bg/50 rounded-2xl border border-white/5 hover:border-primary/20 transition-all group">
                                            <div className="flex items-center gap-4">
                                                <div className="w-12 h-12 rounded-xl bg-dark-panel border border-white/5 flex items-center justify-center text-sm font-black text-primary shadow-inner">
                                                    {user.username.substring(0, 2).toUpperCase()}
                                                </div>
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <span className="font-bold text-white">{user.full_name || user.username}</span>
                                                        {user.is_master && (
                                                            <span className="bg-indigo-500/10 text-indigo-400 text-[9px] font-black px-2 py-0.5 rounded border border-indigo-500/20 uppercase tracking-widest">Master</span>
                                                        )}
                                                    </div>
                                                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest flex items-center gap-2 mt-1">
                                                        <span>{user.username}</span>
                                                        <span className="w-1 h-1 bg-gray-600 rounded-full"></span>
                                                        <span className={user.role === 'admin' ? 'text-primary' : ''}>{user.role}</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button
                                                    onClick={() => handleOpenUserModal(user)}
                                                    className="p-2.5 hover:bg-white/5 rounded-xl text-dark-muted hover:text-white transition-all"
                                                >
                                                    <Pencil size={18} />
                                                </button>
                                                {!user.is_master && (
                                                    <button
                                                        onClick={() => {
                                                            if (confirm(`Remover usuário ${user.username}?`)) {
                                                                deleteUserMutation.mutate(user.username)
                                                            }
                                                        }}
                                                        className="p-2.5 hover:bg-red-500/10 rounded-xl text-dark-muted hover:text-red-500 transition-all"
                                                    >
                                                        <Trash size={18} />
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Card View */}
                            {userViewMode === 'cards' && (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {systemUsers?.map((user, idx) => (
                                        <div key={idx} className="ethereal-card p-6 hover:border-primary/30 transition-all group relative">
                                            {/* Actions (top-right) */}
                                            <div className="absolute top-4 right-4 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button
                                                    onClick={() => handleOpenUserModal(user)}
                                                    className="p-2 hover:bg-white/5 rounded-lg text-dark-muted hover:text-white transition-all"
                                                >
                                                    <Pencil size={16} />
                                                </button>
                                                {!user.is_master && (
                                                    <button
                                                        onClick={() => {
                                                            if (confirm(`Remover usuário ${user.username}?`)) {
                                                                deleteUserMutation.mutate(user.username)
                                                            }
                                                        }}
                                                        className="p-2 hover:bg-red-500/10 rounded-lg text-dark-muted hover:text-red-500 transition-all"
                                                    >
                                                        <Trash size={16} />
                                                    </button>
                                                )}
                                            </div>

                                            {/* Avatar */}
                                            <div className="flex flex-col items-center text-center space-y-4">
                                                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/20 flex items-center justify-center text-2xl font-black text-primary shadow-lg">
                                                    {user.username.substring(0, 2).toUpperCase()}
                                                </div>

                                                {/* User Info */}
                                                <div className="space-y-2">
                                                    <div className="flex items-center justify-center gap-2">
                                                        <h3 className="font-bold text-white text-lg">{user.full_name || user.username}</h3>
                                                        {user.is_master && (
                                                            <span className="bg-indigo-500/10 text-indigo-400 text-[9px] font-black px-2 py-0.5 rounded border border-indigo-500/20 uppercase tracking-widest">Master</span>
                                                        )}
                                                    </div>
                                                    <p className="text-sm text-dark-muted">@{user.username}</p>
                                                </div>

                                                {/* Role Badge */}
                                                <div className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider ${user.role === 'admin'
                                                    ? 'bg-primary/10 text-primary border border-primary/20'
                                                    : 'bg-dark-surface text-dark-muted border border-dark-border'
                                                    }`}>
                                                    {user.role}
                                                </div>

                                                {/* Stats */}
                                                <div className="w-full pt-4 border-t border-dark-border grid grid-cols-2 gap-4 text-center">
                                                    <div>
                                                        <div className="text-xs text-dark-muted uppercase tracking-wider mb-1">Status</div>
                                                        <div className="flex items-center justify-center gap-1.5">
                                                            <div className={`w-2 h-2 rounded-full ${user.is_active ? 'bg-green-500' : 'bg-gray-500'}`}></div>
                                                            <span className="text-sm font-semibold text-white">{user.is_active ? 'Ativo' : 'Inativo'}</span>
                                                        </div>
                                                    </div>
                                                    <div>
                                                        <div className="text-xs text-dark-muted uppercase tracking-wider mb-1">Último Login</div>
                                                        <div className="text-sm font-semibold text-white">{user.last_login ? new Date(user.last_login).toLocaleDateString('pt-BR') : 'Nunca'}</div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* --- OTHER TABS (STUBS) --- */}
                    {!['general', 'ad', 'users'].includes(activeTab) && (
                        <div className="flex flex-col items-center justify-center h-full py-20 opacity-30">
                            <Gear size={64} className="mb-4 animate-spin-slow" />
                            <p className="font-bold uppercase tracking-[0.2em] italic">Módulo em desenvolvimento</p>
                        </div>
                    )}
                </div>
            </div>

            {/* --- USER MODAL --- */}
            {isUserModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="ethereal-card w-full max-w-xl p-8 space-y-6 shadow-2xl animate-in zoom-in-95 duration-200">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xl font-bold text-white flex items-center gap-3">
                                {editingUser ? <Pencil size={24} className="text-primary" /> : <Plus size={24} className="text-primary" />}
                                {editingUser ? 'Editar Usuário' : 'Novo Usuário de Acesso'}
                            </h3>
                            <button onClick={() => setIsUserModalOpen(false)} className="text-dark-muted hover:text-white">
                                <X size={24} />
                            </button>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Username</label>
                                <input
                                    type="text"
                                    value={userForm.username}
                                    disabled={!!editingUser}
                                    onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
                                    className="w-full bg-dark-surface border border-dark-border rounded-xl px-4 py-3 text-white text-sm focus:border-primary/50 transition-all disabled:opacity-50"
                                    placeholder="ex: joao.silva"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Senha {editingUser && '(Deixe vazio para manter)'}</label>
                                <input
                                    type="password"
                                    value={userForm.password}
                                    onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                                    className="w-full bg-dark-surface border border-dark-border rounded-xl px-4 py-3 text-white text-sm focus:border-primary/50 transition-all"
                                    placeholder="••••••••"
                                />
                            </div>
                            <div className="col-span-2 space-y-2">
                                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Nome Completo</label>
                                <input
                                    type="text"
                                    value={userForm.full_name}
                                    onChange={(e) => setUserForm({ ...userForm, full_name: e.target.value })}
                                    className="w-full bg-dark-surface border border-dark-border rounded-xl px-4 py-3 text-white text-sm focus:border-primary/50 transition-all"
                                    placeholder="João da Silva"
                                />
                            </div>
                        </div>

                        {/* Permissions Section */}
                        <div className="space-y-4 pt-4 border-t border-dark-border">
                            <h4 className="text-xs font-black text-primary uppercase tracking-widest">Permissões de Acesso</h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {[
                                    { id: 'view_all', name: 'Visualizar Dashboard', desc: 'Acesso total a leitura de dados' },
                                    { id: 'run_scan', name: 'Executar Scanner', desc: 'Pode iniciar/parar varreduras de rede' },
                                    { id: 'manage_ad', name: 'Gerenciar AD', desc: 'Resetar senhas e destravar contas' },
                                    { id: 'manage_settings', name: 'Ajustes do Sistema', desc: 'Configurar AD, GLPI e Licença' },
                                    { id: 'manage_system_users', name: 'Gerenciar Usuários', desc: 'Criar outros acessos ao NetAudit' }
                                ].map((perm) => (
                                    <label key={perm.id} className="flex items-start gap-3 p-3 bg-dark-surface/50 rounded-xl border border-dark-border cursor-pointer hover:bg-dark-surface transition-all">
                                        <input
                                            type="checkbox"
                                            checked={userForm.permissions[perm.id] || false}
                                            onChange={(e) => setUserForm({
                                                ...userForm,
                                                permissions: { ...userForm.permissions, [perm.id]: e.target.checked }
                                            })}
                                            className="mt-1 w-4 h-4 rounded border-dark-border text-primary focus:ring-primary/20 bg-dark-bg"
                                        />
                                        <div>
                                            <div className="text-xs font-bold text-white">{perm.name}</div>
                                            <div className="text-[10px] text-dark-muted">{perm.desc}</div>
                                        </div>
                                    </label>
                                ))}
                            </div>
                        </div>

                        <div className="flex gap-3 pt-4">
                            <button
                                onClick={() => setIsUserModalOpen(false)}
                                className="flex-1 px-6 py-3 rounded-xl border border-dark-border text-dark-muted font-bold text-sm hover:bg-dark-surface transition-all"
                            >
                                CANCELAR
                            </button>
                            <button
                                onClick={() => saveUserMutation.mutate(userForm)}
                                disabled={saveUserMutation.isPending}
                                className="flex-2 bg-primary hover:bg-primary-dark text-white px-8 py-3 rounded-xl font-bold text-sm shadow-xl transition-all flex items-center justify-center gap-2"
                            >
                                {saveUserMutation.isPending ? 'SALVANDO...' : 'SALVAR ACESSO'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default Settings
