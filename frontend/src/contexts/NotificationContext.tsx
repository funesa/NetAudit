import { createContext, useContext, useState, useEffect, type ReactNode, useRef } from 'react'
import api from '../services/api'

// Define Toast interface locally since ToastContainer is deprecated
export interface Toast {
    id: number | string
    title: string
    message: string
    type: 'info' | 'success' | 'warning' | 'critical' | 'process'
    duration?: number
    startTime?: number // Track when it started for countdown
    progress?: number
}

interface NotificationContextType {
    addToast: (toast: Omit<Toast, 'id'> & { id?: number | string }) => void
    removeToast: (id: number | string) => void
    acknowledgeToast: (id: string) => Promise<void>
    snoozeToast: (id: string) => void
    setPaused: (paused: boolean) => void
    toasts: Toast[]
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined)

export const NotificationProvider = ({ children }: { children: ReactNode }) => {
    const [toasts, setToasts] = useState<Toast[]>([])
    const [isPaused, setPaused] = useState(false)
    const lastStatsRef = useRef<any>(null)

    const addToast = (toast: Omit<Toast, 'id'> & { id?: number | string }) => {
        const id = toast.id || Date.now()

        // Enforce User-requested active durations
        let duration = toast.duration
        if (!duration && toast.type !== 'process') {
            switch (toast.type) {
                case 'critical': duration = 15000; break;
                case 'warning': duration = 9000; break;
                case 'success': duration = 5000; break;
                default: duration = 5000;
            }
        }

        const exists = toasts.find(t => t.id === id)

        setToasts(prev => {
            const prevExists = prev.find(t => t.id === id)
            if (prevExists) {
                // Return updated toast without playing sound or resetting timeout
                return prev.map(t => t.id === id ? { ...t, ...toast, id, duration } : t)
            }
            return [...prev, { ...toast, id, duration, startTime: Date.now() }]
        })

        // Play sound ONLY if it's a NEW toast
        if (!exists) {
            if (toast.type === 'critical') {
                const audio = new Audio('/sounds/critical.mp3')
                audio.play().catch(e => console.log('Audio autoplay blocked', e))
            } else if (toast.type === 'warning') {
                const audio = new Audio('/sounds/warning.mp3')
                audio.play().catch(e => console.log('Audio autoplay blocked', e))
            }
        }

        // Auto remove - ONLY if duration is set AND it's not a System/AI persistent alert (which relies on polling)
        const isPersistent = typeof id === 'string' && (id.startsWith('sys-') || id.startsWith('ai-'))

        if (duration && !exists && !isPersistent) {
            setTimeout(() => {
                removeToast(id)
            }, duration)
        }
    }

    const removeToast = (id: number | string) => {
        setToasts(prev => prev.filter(t => t.id !== id))
    }

    const acknowledgeToast = async (id: string) => {
        // 1. Remove from UI immediately
        removeToast(id)

        // 2. Determine if it's a system alert (has "sys-" prefix)
        if (id.startsWith('sys-')) {
            const dbId = id.replace('sys-', '')
            try {
                await api.post(`/api/alerts/${dbId}/ack`)
            } catch (e) {
                console.error("Failed to ack alert", e)
            }
        }
    }

    const snoozeToast = (id: string) => {
        // 1. Remove from UI
        removeToast(id)

        // 2. Save to localStorage with expiration (1 hour)
        const snoozed = JSON.parse(localStorage.getItem('snoozed_alerts') || '{}')
        snoozed[id] = Date.now() + (60 * 60 * 1000) // Now + 1h
        localStorage.setItem('snoozed_alerts', JSON.stringify(snoozed))
    }

    const isSnoozed = (id: string) => {
        const snoozed = JSON.parse(localStorage.getItem('snoozed_alerts') || '{}')
        const expireTime = snoozed[id]
        if (!expireTime) return false

        if (Date.now() > expireTime) {
            // Expired, clean up
            delete snoozed[id]
            localStorage.setItem('snoozed_alerts', JSON.stringify(snoozed))
            return false
        }
        return true
    }

    // --- SYSTEM MONITORING LOGIC (Zabbix-Style) ---
    useEffect(() => {
        let timeoutId: any = null

        const checkSystemHealth = async () => {
            // SKIP IF PAUSED (User interaction)
            if (isPaused) {
                // Just Loop quickly until unpaused
                timeoutId = setTimeout(checkSystemHealth, 500)
                return
            }

            try {
                // --- REAL SYSTEM MONITORING ---

                // 1. Intelligence / Critical Alerts
                try {
                    const resIntel = await api.get('/api/ai/intelligence')
                    const aiAlerts = resIntel.data
                    if (aiAlerts && aiAlerts.length > 0) {
                        const latestAlert = aiAlerts[0]
                        if (latestAlert.priority === 'high' || latestAlert.type === 'critical') {
                            addToast({
                                id: `ai-${latestAlert.id}`,
                                title: latestAlert.title || 'Alerta Crítico (AI)',
                                message: latestAlert.message || 'Detectada anomalia severa no sistema.',
                                type: 'critical'
                            })
                        }
                    }
                } catch (e) { /* ignore */ }

                // --- NEW: SYSTEM ALERTS (Zabbix-Style) ---
                try {
                    const resAlerts = await api.get('/api/alerts/active')
                    const realAlerts = resAlerts.data

                    if (Array.isArray(realAlerts)) {
                        realAlerts.forEach((alert: any) => {
                            const toastId = `sys-${alert.id}`

                            // FILTER: Skip if acknowledged or snoozed
                            if (alert.acknowledged) return
                            if (isSnoozed(toastId)) return

                            // Map severity to toast type
                            let type: Toast['type'] = 'info'
                            if (alert.severity === 'disaster' || alert.severity === 'high') type = 'critical'
                            else if (alert.severity === 'average' || alert.severity === 'warning') type = 'warning'

                            addToast({
                                id: toastId, // Unique ID based on DB ID
                                title: alert.title,
                                message: alert.message,
                                type: type,
                                // Persistent for ALL system alerts (Zabbix-style) logic relies on polling removal
                                // We provide a duration for visual progress bar urgency, but auto-removal is disabled in addToast
                                duration: 60000, // 1 minute visual countdown (resets on update)
                            })
                        })

                        // Remove resolved alerts from toasts (if they were system alerts)
                        setToasts(prevToasts => {
                            // Keep non-system toasts OR system toasts that are still active
                            return prevToasts.filter(t => {
                                if (typeof t.id === 'string' && t.id.startsWith('sys-')) {
                                    const alertId = parseInt(t.id.replace('sys-', ''))
                                    return realAlerts.some((a: any) => a.id === alertId)
                                }
                                return true
                            })
                        })
                    }
                } catch (e) {
                    console.error("Failed to fetch system alerts", e)
                }

                // 2. GLPI Stats Monitoring
                const resStats = await api.get('/api/glpi/stats')
                const newStats = resStats.data
                const lastStats = lastStatsRef.current

                if (lastStats) {
                    if (newStats.new > lastStats.new) {
                        const diff = newStats.new - lastStats.new
                        addToast({
                            title: 'Novo Chamado',
                            message: `${diff} novo(s) chamado(s) aberto(s) recentemente.`,
                            type: 'info'
                        })
                    }
                    if (newStats.solved > lastStats.solved) {
                        addToast({
                            title: 'Chamado Resolvido',
                            message: 'Um incidente foi marcado como solucionado.',
                            type: 'success'
                        })
                    }
                }
                lastStatsRef.current = newStats

                // 3. SCANNER MONITORING (Smart Pill Integration)
                const resScan = await api.get('/api/scanner/status')
                const scanStatus = resScan.data

                if (scanStatus.running) {
                    addToast({
                        id: 'scanner-active', // Persistent ID
                        title: 'Escaneamento em Progresso',
                        message: `Analisando rede... ${scanStatus.progress}%`,
                        type: 'process',
                        progress: scanStatus.progress,
                        // No duration, so it stays until updated/removed
                    })
                } else {
                    // Check if we just finished (was running previously?)
                    removeToast('scanner-active')
                }

            } catch (e) {
                console.error("Monitor Error:", e)
            } finally {
                timeoutId = setTimeout(checkSystemHealth, 2000) // Poll faster (2s) for smoother progress
            }
        }

        checkSystemHealth()

        return () => {
            if (timeoutId) clearTimeout(timeoutId)
        }
    }, [isPaused]) // Re-bind effect if pause state changes

    return (
        <NotificationContext.Provider value={{ addToast, removeToast, acknowledgeToast, snoozeToast, setPaused, toasts }}>
            {children}
        </NotificationContext.Provider>
    )
}

export const useNotification = () => {
    const context = useContext(NotificationContext)
    if (context === undefined) {
        throw new Error('useNotification must be used within a NotificationProvider')
    }
    return context
}
