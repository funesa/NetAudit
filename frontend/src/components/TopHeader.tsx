import { useState, useEffect, useMemo } from 'react'
import { Sparkle, ClockCounterClockwise, WarningOctagon, Info, CheckCircle, Warning, X } from '@phosphor-icons/react'
import { NavLink } from 'react-router-dom'
import api from '../services/api'
import { useNotification } from '../contexts/NotificationContext'

const TopHeader = ({ onOpenAtena }: { onOpenAtena: () => void }) => {
    const [isPremium, setIsPremium] = useState(false)
    const [trialDays, setTrialDays] = useState(0)
    const [showPopover, setShowPopover] = useState(false)
    const { toasts, acknowledgeToast, snoozeToast, setPaused } = useNotification()

    // Sync Pause state with Popover
    useEffect(() => {
        setPaused(showPopover)
    }, [showPopover, setPaused])



    // Get the Active Toast (Head of FIFO Queue)
    const activeNotification = useMemo(() => {
        if (toasts.length === 0) return null
        return toasts[0]
    }, [toasts])

    // Helper to format elapsed time
    const getTimeAgo = (startTime?: number) => {
        if (!startTime) return ''
        const seconds = Math.floor((Date.now() - startTime) / 1000)

        if (seconds < 60) return `Há ${seconds} seg`
        const minutes = Math.floor(seconds / 60)
        if (minutes < 60) return `Há ${minutes} min`
        const hours = Math.floor(minutes / 60)
        return `Há ${hours} h`
    }

    // Force re-render every second to update time strings
    const [, setTick] = useState(0)
    useEffect(() => {
        if (!activeNotification) return
        const interval = setInterval(() => setTick(t => t + 1), 1000)
        return () => clearInterval(interval)
    }, [activeNotification])

    useEffect(() => {
        const fetchLicense = async () => {
            try {
                const res = await api.get('/api/license/info')
                setIsPremium(res.data.is_premium)
                setTrialDays(res.data.trial_days_left)
            } catch (e) {
                console.error("Erro ao buscar info da licença:", e)
            }
        }
        fetchLicense()
    }, [])

    // --- SMART PILL STYLES ---
    const getPillStyles = () => {
        if (!activeNotification) {
            return "bg-white text-zinc-900 border-zinc-200 hover:bg-zinc-50 dark:bg-dark-surface dark:text-dark-text dark:border-dark-border dark:hover:bg-zinc-800 w-[140px]"
        }
        switch (activeNotification.type) {
            case 'critical': return "bg-red-500 text-white border-red-400 w-[450px] shadow-[0_0_15px_rgba(239,68,68,0.5)] animate-pulse-slow active-notification"
            case 'warning': return "bg-amber-500 text-white border-amber-400 w-[450px] active-notification"
            case 'success': return "bg-emerald-500 text-white border-emerald-400 w-[450px] active-notification"
            case 'process': return "bg-indigo-600 text-white border-indigo-500 w-[450px] shadow-[0_0_15px_rgba(99,102,241,0.5)] active-notification"
            default: return "bg-blue-500 text-white border-blue-400 w-[450px] active-notification"
        }
    }

    const getIcon = () => {
        if (!activeNotification) return <Sparkle size={16} weight="fill" className="text-primary" />
        switch (activeNotification.type) {
            case 'critical': return <WarningOctagon size={18} weight="fill" className="text-white animate-bounce" />
            case 'warning': return <Warning size={18} weight="fill" className="text-white" />
            case 'success': return <CheckCircle size={18} weight="fill" className="text-white" />
            case 'process': return <ClockCounterClockwise size={18} weight="fill" className="text-white animate-spin-slow" />
            default: return <Info size={18} weight="fill" className="text-white" />
        }
    }

    return (
        <header className="flex items-center justify-between w-full h-10 relative">
            {/* Left side: Empty space for balance */}
            <div className="flex items-center gap-2">
            </div>

            {/* Right side tools */}
            <div className="flex items-center gap-3">
                {/* License Badge */}
                {!isPremium && (
                    <NavLink to="/license" className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-yellow-500/10 text-yellow-500 hover:bg-yellow-500/20 transition-all text-[11px] font-medium border border-yellow-500/20">
                        <ClockCounterClockwise size={14} weight="fill" />
                        <span>Trial: {trialDays}d</span>
                    </NavLink>
                )}

                {/* SMART PILL: Atena AI / Notification Banner */}
                <div className="relative h-[38px] flex items-center justify-end z-[50]">
                    <button
                        onClick={() => {
                            if (activeNotification) {
                                if (activeNotification.type === 'process') {
                                    // Process notifications usually don't need acknowledgement
                                } else {
                                    // Toggle Popover
                                    setShowPopover(!showPopover)
                                }
                            } else {
                                onOpenAtena()
                            }
                        }}
                        className={`
                            relative flex items-center gap-3 px-1 py-1 pr-5 h-full rounded-full border shadow-lg transition-all duration-700 ease-spring
                            overflow-hidden backdrop-blur-md
                            ${getPillStyles()}
                        `}
                    >
                        {/* PROGRESS BAR BACKGROUND */}
                        {activeNotification && (
                            <>
                                {/* Countdown Bar (Shrinking) for normal alerts */}
                                {activeNotification.type !== 'process' && activeNotification.duration && (
                                    <div
                                        key={`shrink-${activeNotification.id}`}
                                        className="absolute bottom-0 left-0 h-[3px] bg-white/40 z-0 progress-bar-shrink rounded-full"
                                        style={{
                                            animationDuration: `${activeNotification.duration}ms`,
                                            width: '100%'
                                        }}
                                    />
                                )}

                                {/* Actual Progress Bar (Growing) for 'process' alerts */}
                                {activeNotification.type === 'process' && (
                                    <div
                                        className="absolute bottom-0 left-0 h-1 bg-white/40 z-0 transition-all duration-300 ease-linear"
                                        style={{
                                            width: `${activeNotification.progress || 0}%`
                                        }}
                                    />
                                )}
                            </>
                        )}

                        {/* Icon Container */}
                        <div className={`
                            w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-colors duration-300 relative z-10
                            ${activeNotification ? 'bg-white/20' : 'bg-transparent'}
                        `}>
                            {getIcon()}
                        </div>

                        {/* Content Switcher */}
                        <div className="flex flex-col items-start justify-center min-w-0 flex-1 h-full overflow-hidden relative z-10">
                            {/* Normal State Text */}
                            <div className={`
                                absolute left-0 transition-all duration-300 flex items-center
                                ${activeNotification ? '-translate-y-10 opacity-0' : 'translate-y-0 opacity-100'}
                            `}>
                                <span className="text-[13px] font-medium whitespace-nowrap">Atena AI</span>
                            </div>

                            {/* Notification State Text */}
                            <div className={`
                                absolute left-0 transition-all duration-300 flex flex-col justify-center w-full
                                ${activeNotification ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}
                            `}>
                                <div className="flex justify-between items-center w-full pr-1">
                                    <span className="text-[12px] font-bold leading-none truncate flex-1 text-left">
                                        {activeNotification?.title}
                                    </span>
                                </div>
                                <span className="text-[10px] font-medium opacity-90 truncate w-full text-left">
                                    {activeNotification?.message}
                                </span>
                            </div>
                        </div>

                        {/* Close X (Visual only now, triggers popover) */}
                        {activeNotification && (
                            <div className="shrink-0 animate-in fade-in zoom-in duration-300 z-10">
                                <X size={14} className="opacity-80 hover:opacity-100" />
                            </div>
                        )}
                    </button>

                    {/* POPOVER UI - Integrated Banner Look ('Bandeira Deitada') */}
                    {activeNotification && showPopover && (
                        <div className="absolute top-[44px] right-0 w-[450px] bg-white/80 dark:bg-dark-surface/90 backdrop-blur-2xl border border-zinc-200 dark:border-white/10 rounded-2xl shadow-[0_20px_40px_rgba(0,0,0,0.4)] overflow-hidden animate-in fade-in slide-in-from-top-4 z-[60] origin-top">
                            {/* Banner Header/Body - Slimmer horizontal layout */}
                            <div className={`flex items-center gap-4 p-4 ${activeNotification.type === 'critical' ? 'bg-red-500/10' :
                                    activeNotification.type === 'warning' ? 'bg-amber-500/10' :
                                        'bg-blue-500/10'
                                }`}>
                                <div className={`w-10 h-10 rounded-xl shrink-0 flex items-center justify-center shadow-lg ${activeNotification.type === 'critical' ? 'bg-red-500 text-white' :
                                        activeNotification.type === 'warning' ? 'bg-amber-500 text-white' :
                                            'bg-blue-500 text-white'
                                    }`}>
                                    {getIcon()}
                                </div>

                                <div className="flex-1 min-w-0">
                                    <h3 className="font-bold text-zinc-900 dark:text-white text-[14px] leading-tight flex justify-between items-center">
                                        <span className="truncate">{activeNotification.title}</span>
                                        <span className="text-[9px] font-bold text-zinc-400 dark:text-dark-muted ml-2 shrink-0">
                                            {getTimeAgo(activeNotification.startTime)}
                                        </span>
                                    </h3>
                                    <p className="text-[12px] text-zinc-500 dark:text-dark-muted mt-1 leading-snug line-clamp-2">
                                        {activeNotification.message}
                                    </p>
                                </div>
                            </div>

                            {/* Banner Actions - Horizontal slim bar */}
                            <div className="flex h-11 border-t border-zinc-100 dark:border-white/5 divide-x divide-zinc-100 dark:divide-white/5 bg-white/50 dark:bg-black/20">
                                <button
                                    onClick={() => {
                                        acknowledgeToast(String(activeNotification.id))
                                        setShowPopover(false)
                                    }}
                                    className="flex-1 flex items-center justify-center gap-2 hover:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold text-[11px] transition-all active:bg-emerald-500/20"
                                >
                                    <CheckCircle size={16} weight="bold" />
                                    Reconhecer
                                </button>
                                <button
                                    onClick={() => {
                                        snoozeToast(String(activeNotification.id))
                                        setShowPopover(false)
                                    }}
                                    className="flex-1 flex items-center justify-center gap-2 hover:bg-zinc-500/10 text-zinc-500 dark:text-dark-muted font-bold text-[11px] transition-all active:bg-zinc-500/20"
                                >
                                    <ClockCounterClockwise size={16} weight="bold" />
                                    Adiar Alerta
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </header >
    )
}

export default TopHeader
