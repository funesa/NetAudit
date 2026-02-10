import type { ReactNode } from 'react';
import { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
    ChartPie, Users, Gear, SignOut, Binoculars, Brain,
    HardDrives, ShieldWarning, Headset, Globe, IdentificationCard, List, X, ShareNetwork
} from '@phosphor-icons/react';
import TopHeader from './TopHeader';
import AtenaAI from './AtenaAI';
import api from '../services/api';
import { NotificationProvider } from '../contexts/NotificationContext';

interface LayoutProps {
    children: ReactNode;
}

const LayoutContent = ({ children }: LayoutProps) => {
    const location = useLocation();
    const username = localStorage.getItem('username') || 'Usuário';
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [isAtenaOpen, setIsAtenaOpen] = useState(false);

    // Fecha o menu mobile ao navegar
    useEffect(() => {
        setIsMobileMenuOpen(false);
    }, [location]);

    // Aggressive RBAC Sync: If critical data is missing but token exists, fetch from backend
    useEffect(() => {
        const token = localStorage.getItem('token');
        const permsStr = localStorage.getItem('permissions');
        const masterStatus = localStorage.getItem('is_master');

        // Triggers recovery if permissions are null, undefined, '{}' or if master status is unknown
        const isMissingRBAC = !permsStr || permsStr === '{}' || permsStr === 'null' || masterStatus === null;

        if (token && isMissingRBAC) {
            console.log("RBAC Aggressive Sync: Sincronizando segurança no primeiro acesso...");
            api.get('/api/auth/me')
                .then(res => {
                    if (res.data.permissions || res.data.is_master !== undefined) {
                        localStorage.setItem('permissions', JSON.stringify(res.data.permissions || { view_all: true }));
                        localStorage.setItem('is_master', res.data.is_master ? 'true' : 'false');
                        // Reload only once to initialize the new RBAC state
                        window.location.reload();
                    }
                })
                .catch(err => console.error("Erro na sincronização de segurança:", err));
        }
    }, [location.pathname]);

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.removeItem('permissions');
        localStorage.removeItem('is_master');
        window.location.href = '/login';
    };

    const permissions = JSON.parse(localStorage.getItem('permissions') || '{}');
    const isMaster = localStorage.getItem('is_master') === 'true';

    const can = (permission: string) => {
        if (isMaster) return true;
        const p = permissions as any;

        // Fail-safe: Se não houver permissões carregadas ainda, permite ver o básico
        // para não "sumir" com o menu enquanto sincroniza.
        if (!p || Object.keys(p).length === 0) return true;

        if (p.all) return true;
        return !!p[permission];
    };

    const NavItem = ({ to, name, icon: Icon, badge }: { to: string, name: string, icon: any, badge?: string | number }) => {
        const isActive = location.pathname === to;
        return (
            <NavLink
                to={to}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 group relative ${isActive
                    ? 'bg-dark-surface text-white font-medium shadow-sm border border-dark-border'
                    : 'text-dark-muted hover:text-dark-text hover:bg-dark-surface/50'
                    }`
                }
            >
                <Icon size={18} weight={isActive ? 'fill' : 'regular'} className={isActive ? 'text-primary' : 'text-gray-500 group-hover:text-gray-300'} />
                <span className="text-[13px] tracking-tight">{name}</span>
                {badge && (
                    <span className="ml-auto bg-primary/10 text-primary text-[10px] font-bold px-2 py-0.5 rounded-full">
                        {badge}
                    </span>
                )}
            </NavLink>
        );
    };

    return (
        <div className="flex h-screen bg-dark-bg text-dark-text font-sans overflow-hidden">
            {/* Mobile Menu Toggle */}
            <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-dark-panel border border-dark-border text-white shadow-sm"
            >
                {isMobileMenuOpen ? <X size={20} /> : <List size={20} />}
            </button>

            {/* Mobile Overlay */}
            {isMobileMenuOpen && (
                <div
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden animate-in fade-in duration-200"
                />
            )}

            {/* Sidebar - Docked & Bordered (Ethereal Style) */}
            <aside className={`
                fixed lg:relative inset-y-0 left-0 z-50 flex flex-col w-[260px] bg-dark-panel border-r border-dark-border transition-transform duration-300
                ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
            `}>
                {/* Brand Header */}
                <div className="h-16 flex items-center px-6 border-b border-dark-border">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 flex items-center justify-center rounded-lg bg-primary text-white shadow-sm">
                            <Brain size={18} weight="fill" />
                        </div>
                        <span className="text-[15px] font-semibold text-white tracking-tight">NetAudit</span>
                    </div>
                </div>

                {/* Navigation Scroll Area */}
                <nav className="flex-1 px-4 py-6 space-y-8 overflow-y-auto section-scroll">
                    {/* Main Section */}
                    <div className="space-y-1">
                        <div className="px-3 pb-2 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Geral</div>
                        <NavItem to="/dashboard" name="Dashboard" icon={ChartPie} />
                    </div>

                    {/* Directory Section */}
                    {can('view_all') && (
                        <div className="space-y-1">
                            <div className="px-3 pb-2 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Diretório</div>
                            <NavItem to="/ad-users" name="Usuários" icon={Users} />
                            <NavItem to="/ad-shares" name="Arquivos" icon={HardDrives} />
                            <NavItem to="/security" name="Segurança" icon={ShieldWarning} />
                        </div>
                    )}

                    {/* Network Section */}
                    <div className="space-y-1">
                        <div className="px-3 pb-2 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Rede</div>
                        <NavItem to="/scanner" name="Scanner" icon={Binoculars} />
                        <NavItem to="/ip-map" name="Mapa IP" icon={Globe} />
                        <NavItem to="/topology" name="Topologia" icon={ShareNetwork} />
                    </div>

                    {/* Support Section */}
                    {can('view_all') && (
                        <div className="space-y-1">
                            <div className="px-3 pb-2 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Suporte</div>
                            <NavItem to="/tickets" name="Chamados" icon={Headset} />
                        </div>
                    )}
                </nav>

                {/* Footer / User Profile */}
                <div className="p-4 border-t border-dark-border bg-dark-panel">
                    <div className="space-y-1 mb-4">
                        <NavItem to="/license" name="Licença" icon={IdentificationCard} />
                        {can('manage_settings') && <NavItem to="/settings" name="Ajustes" icon={Gear} />}
                    </div>

                    <div className="pt-4 border-t border-dark-border flex items-center gap-3 px-2">
                        <div className="w-8 h-8 rounded-full bg-dark-surface border border-dark-border flex items-center justify-center text-gray-300 text-xs font-semibold">
                            {username.charAt(0).toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-[13px] font-medium text-white truncate">{username}</p>
                            <p className="text-[11px] text-gray-500">{isMaster ? 'Master Admin' : 'Usuário do Sistema'}</p>
                        </div>
                        <button
                            onClick={handleLogout}
                            className="p-1.5 rounded-lg hover:bg-red-500/10 hover:text-red-500 text-gray-500 transition-colors"
                            title="Desconectar"
                        >
                            <SignOut size={16} />
                        </button>
                    </div>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 h-screen overflow-hidden flex flex-col bg-dark-bg relative">
                <div className="flex-1 overflow-y-auto section-scroll">
                    {/* TopBar Container within Main */}
                    <div className="sticky top-0 z-30 bg-dark-bg/80 backdrop-blur-md border-b border-dark-border px-8 py-3">
                        <TopHeader onOpenAtena={() => setIsAtenaOpen(true)} />
                    </div>

                    <div className="p-8 max-w-[1600px] mx-auto page-transition">
                        {children}
                    </div>
                </div>
            </main>

            {/* Atena AI Overlay - Global */}
            <AtenaAI isOpen={isAtenaOpen} onClose={() => setIsAtenaOpen(false)} />
        </div>
    );
};

const Layout = ({ children }: LayoutProps) => (
    <NotificationProvider>
        <LayoutContent>{children}</LayoutContent>
    </NotificationProvider>
);

export default Layout;
