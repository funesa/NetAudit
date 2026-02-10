import { useState, useRef, useEffect } from 'react'
import { Sparkle, X, PaperPlaneRight, Robot, Warning } from '@phosphor-icons/react'
import api from '../services/api'

interface Message {
    id: string
    text: string
    sender: 'user' | 'ai'
    timestamp: Date
    intent?: string
    params?: any
    confirmation_text?: string
    dangerous?: boolean
}

const AtenaAI = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            text: 'Olá! Sou a Atena. Posso ajudar a gerenciar usuários do AD, verificar IPs, diagnosticar erros ou buscar ativos na rede. Como posso ajudar?',
            sender: 'ai',
            timestamp: new Date()
        }
    ])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const chatEndRef = useRef<HTMLDivElement>(null)

    const scrollToBottom = () => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    useEffect(() => {
        (window as any).atenaMessage = (text: string) => {
            setInput(text)
            setTimeout(() => {
                const btn = document.getElementById('atena-send-btn')
                btn?.click()
            }, 50)
        }

        (window as any).printAtenaReport = (elementId: string) => {
            const el = document.getElementById(elementId)
            if (!el) {
                console.error('Report element not found:', elementId)
                return
            }

            const win = window.open('', '_blank', 'width=900,height=800')
            if (win) {
                win.document.write('<html><head><title>Relatório Atena</title>')
                win.document.write('<style>')
                win.document.write(`
                    body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 40px; color: #333; }
                    h2 { margin-bottom: 5px; color: #111; }
                    p { color: #666; font-size: 14px; margin-top: 0; }
                    table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }
                    th { background-color: #f3f4f6; text-align: left; padding: 10px; border: 1px solid #e5e7eb; font-weight: 700; text-transform: uppercase; color: #374151; }
                    td { border: 1px solid #e5e7eb; padding: 10px; vertical-align: middle; }
                    tr:nth-child(even) { background-color: #f9fafb; }
                    .footer { margin-top: 30px; text-align: center; color: #9ca3af; font-size: 10px; border-top: 1px solid #e5e7eb; padding-top: 20px; }
                `)
                win.document.write('</style></head><body>')
                win.document.write(el.innerHTML)
                win.document.write('<div class="footer">Gerado via Atena AI • SCAN 2026 Systems</div>')
                win.document.write('</body></html>')
                win.document.close()
                win.focus()
                setTimeout(() => {
                    win.print()
                    // win.close() // Opcional: manter aberto pro user confirmar
                }, 500)
            }
        }
    }, [])

    const handleSend = async () => {
        if (!input.trim()) return

        const userMsg: Message = {
            id: Date.now().toString(),
            text: input,
            sender: 'user',
            timestamp: new Date()
        }

        setMessages(prev => [...prev, userMsg])
        setInput('')
        setIsLoading(true)

        try {
            const response = await api.post('/api/ai/process', { command: input })
            const data = response.data

            const aiMsg: Message = {
                id: (Date.now() + 1).toString(),
                text: data.description || data.message || 'Desculpe, não entendi o comando.',
                sender: 'ai',
                timestamp: new Date(),
                intent: data.intent,
                params: data.params,
                confirmation_text: data.confirmation_text,
                dangerous: data.dangerous
            }

            setMessages(prev => [...prev, aiMsg])
        } catch (error: any) {
            const errorMsg: Message = {
                id: (Date.now() + 1).toString(),
                text: error.response?.data?.description || 'Opa, tive um erro ao processar sua solicitação.',
                sender: 'ai',
                timestamp: new Date()
            }
            setMessages(prev => [...prev, errorMsg])
        } finally {
            setIsLoading(false)
        }
    }

    const handleAction = async (msg: Message) => {
        setIsLoading(true)
        try {
            const response = await api.post('/api/ai/execute', {
                intent: msg.intent,
                params: msg.params
            })

            const data = response.data
            const resultMsg: Message = {
                id: Date.now().toString(),
                text: data.description || data.message || 'Ação concluída.',
                sender: 'ai',
                timestamp: new Date(),
                intent: data.intent,
                params: data.params,
                dangerous: data.dangerous
            }
            setMessages(prev => [...prev, resultMsg])
        } catch (error: any) {
            const errorMsg: Message = {
                id: Date.now().toString(),
                text: error.response?.data?.message || 'Erro ao executar ação.',
                sender: 'ai',
                timestamp: new Date()
            }
            setMessages(prev => [...prev, errorMsg])
        } finally {
            setIsLoading(false)
        }
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-[100] flex justify-end overflow-hidden">
            {/* Overlay */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-[2px] animate-in fade-in duration-300"
                onClick={onClose}
            />

            {/* AI Side Panel - Ethereal Matte */}
            <div className="relative w-full max-w-[480px] h-full bg-dark-panel border-l border-dark-border shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
                {/* Header */}
                <div className="p-5 border-b border-dark-border flex items-center justify-between bg-dark-panel">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-white shadow-sm">
                            <Sparkle size={20} weight="fill" />
                        </div>
                        <div className="space-y-0.5">
                            <h2 className="text-[16px] font-semibold text-dark-text tracking-tight">Atena Intelligence</h2>
                            <p className="text-[11px] text-dark-muted font-medium">Assistant Active</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-dark-surface text-dark-muted hover:text-dark-text transition-all active:scale-95"
                    >
                        <X size={20} weight="bold" />
                    </button>
                </div>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-5 space-y-6 section-scroll bg-dark-bg/50">
                    {messages.map((msg) => (
                        <div key={msg.id} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                            <div className={`flex gap-3 max-w-[90%] ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}>
                                {msg.sender === 'ai' && (
                                    <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center flex-shrink-0 mt-1 shadow-sm">
                                        <Robot size={16} weight="fill" className="text-white" />
                                    </div>
                                )}

                                <div className={`relative px-4 py-3 rounded-xl text-[14px] leading-relaxed shadow-sm ${msg.sender === 'ai'
                                    ? 'bg-dark-surface text-dark-text border border-dark-border rounded-tl-none'
                                    : 'bg-primary text-white rounded-tr-none'
                                    }`}>
                                    <div dangerouslySetInnerHTML={{ __html: msg.text }} className="atena-rich-text" />

                                    {/* Confirmation Interaction */}
                                    {msg.sender === 'ai' && msg.intent && msg.intent !== 'show_info' && (
                                        <div className="mt-3 pt-3 border-t border-dark-border space-y-3">
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => handleAction(msg)}
                                                    className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-[13px] font-medium transition-all shadow-sm ${msg.dangerous
                                                        ? 'bg-red-500 hover:bg-red-600 text-white'
                                                        : 'bg-primary hover:bg-primary-dark text-white'
                                                        }`}
                                                >
                                                    {msg.dangerous && <Warning size={16} weight="bold" />}
                                                    {msg.intent === 'authorize_ticket_reset' ? 'Autorizar' : 'Confirmar'}
                                                </button>
                                                <button
                                                    onClick={async () => {
                                                        await api.post('/api/ai/cancel');
                                                        setMessages(prev => [...prev, { id: Date.now().toString(), text: 'Cancelado.', sender: 'ai', timestamp: new Date() }]);
                                                    }}
                                                    className="px-4 py-2 bg-dark-bg hover:bg-dark-surface border border-dark-border text-dark-text rounded-lg text-[13px] font-medium transition-all"
                                                >
                                                    Descartar
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                            <span className="text-[10px] text-dark-muted mt-1.5 px-12">
                                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        </div>
                    ))}

                    {isLoading && (
                        <div className="flex gap-3">
                            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center flex-shrink-0 shadow-sm">
                                <Robot size={16} weight="fill" className="text-white" />
                            </div>
                            <div className="bg-dark-surface border border-dark-border p-4 rounded-xl rounded-tl-none flex items-center gap-1.5 shadow-sm">
                                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-75"></div>
                                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-150"></div>
                            </div>
                        </div>
                    )}
                    <div ref={chatEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-5 border-t border-dark-border bg-dark-panel">
                    <div className="flex items-center gap-2 p-1.5 pl-4 rounded-xl bg-dark-surface border border-dark-border focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20 transition-all duration-200">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            placeholder="Como posso ajudar?"
                            className="flex-1 bg-transparent border-none text-dark-text text-[14px] focus:ring-0 focus:outline-none placeholder:text-dark-muted font-normal"
                        />
                        <button
                            id="atena-send-btn"
                            onClick={handleSend}
                            disabled={!input.trim() || isLoading}
                            className="w-8 h-8 bg-primary hover:bg-primary-dark text-white rounded-lg flex items-center justify-center transition-all disabled:opacity-50 disabled:grayscale active:scale-95"
                        >
                            <PaperPlaneRight size={16} weight="fill" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default AtenaAI
