import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
    Ticket, Clock, CheckCircle, Plus,
    Funnel, X, ClipboardText, ChatTeardropText, Tag, User,
    MapPin, PaperPlaneRight, Info, FileArrowUp, File, Download,
    Image as ImageIcon, Trash
} from '@phosphor-icons/react'
import api from '../services/api'
import type { Ticket as TicketType } from '../types'

const Tickets = () => {
    const queryClient = useQueryClient()
    const [filter, setFilter] = useState('not_solved')
    const [selectedTicketId, setSelectedTicketId] = useState<number | null>(null)
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
    const [replyContent, setReplyContent] = useState('')
    const [position, setPosition] = useState({ x: 0, y: 0 })
    const [isDragging, setIsDragging] = useState(false)
    const dragStart = useRef({ x: 0, y: 0 })
    const fileInputRef = useRef<HTMLInputElement>(null)
    const [selectedFile, setSelectedFile] = useState<File | null>(null)

    // Reset position when modal closes/opens
    useEffect(() => {
        if (!selectedTicketId) {
            setPosition({ x: 0, y: 0 })
        }
    }, [selectedTicketId])

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
        if ((e.target as HTMLElement).closest('button') || (e.target as HTMLElement).closest('a')) return
        e.preventDefault()
        setIsDragging(true)
        dragStart.current = {
            x: e.clientX - position.x,
            y: e.clientY - position.y
        }
        document.body.style.cursor = 'grabbing'
    }

    // Form para novo chamado
    const [newTicketForm, setNewTicketForm] = useState({
        title: '',
        content: '',
        category: '',
        location: '',
        urgency: 3
    })

    // --- Queries ---
    const { data: ticketsData, isLoading } = useQuery<{ success: boolean; tickets: TicketType[]; error?: string }>({
        queryKey: ['tickets', filter],
        queryFn: async () => {
            const response = await api.get(`/api/glpi/tickets?status=${filter}`)
            return response.data
        },
        refetchInterval: 30000,
    })

    const { data: ticketDetail, isLoading: isLoadingDetail } = useQuery({
        queryKey: ['ticketDetail', selectedTicketId],
        queryFn: async () => {
            if (!selectedTicketId) return null
            const response = await api.get(`/api/glpi/ticket/${selectedTicketId}`)
            return response.data
        },
        enabled: !!selectedTicketId
    })

    const { data: stats } = useQuery({
        queryKey: ['glpiStats'],
        queryFn: async () => {
            const response = await api.get('/api/glpi/stats')
            return response.data
        }
    })

    const { data: categories } = useQuery({
        queryKey: ['glpiCategories'],
        queryFn: async () => {
            const response = await api.get('/api/glpi/categories')
            return response.data
        },
        enabled: isCreateModalOpen
    })

    const { data: locations } = useQuery({
        queryKey: ['glpiLocations'],
        queryFn: async () => {
            const response = await api.get('/api/glpi/locations')
            return response.data
        },
        enabled: isCreateModalOpen
    })

    // --- Mutations ---
    const uploadDocumentMutation = useMutation({
        mutationFn: async ({ file, itemtype, items_id }: { file: File, itemtype: string, items_id: number }) => {
            const formData = new FormData()
            formData.append('file', file)
            formData.append('itemtype', itemtype)
            formData.append('items_id', items_id.toString())
            const response = await api.post('/api/glpi/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            return response.data
        }
    })

    const addFollowupMutation = useMutation({
        mutationFn: async ({ id, content, file }: { id: number; content: string; file?: File | null }) => {
            // Primeiro envia o followup
            const response = await api.post(`/api/glpi/ticket/${id}/followup`, { content })

            // Se tiver arquivo, envia vinculado ao ticket (o GLPI as vezes é chato vinculando direto ao followup via API se o itemtype não bater)
            // Vinculamos ao Ticket por padrão para visibilidade
            if (file && response.data.success) {
                await uploadDocumentMutation.mutateAsync({ file, itemtype: 'Ticket', items_id: id })
            }
            return response.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['ticketDetail', selectedTicketId] })
            setReplyContent('')
            setSelectedFile(null)
        }
    })

    const createTicketMutation = useMutation({
        mutationFn: async (data: typeof newTicketForm) => {
            const response = await api.post('/api/glpi/ticket/create', data)
            // Nota: Se quisermos anexar no create, precisaríamos do ID retornado
            return response.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['tickets'] })
            setIsCreateModalOpen(false)
            setNewTicketForm({ title: '', content: '', category: '', location: '', urgency: 3 })
        }
    })

    // --- Helpers ---
    const getStatusInfo = (status: number) => {
        switch (status) {
            case 1: return { text: 'Novo', color: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' }
            case 2: case 3: case 4: return { text: 'Em Processamento', color: 'bg-status-info/10 text-status-info border-status-info/20' }
            case 5: return { text: 'Solucionado', color: 'bg-status-success/10 text-status-success border-status-success/20' }
            case 6: return { text: 'Fechado', color: 'bg-gray-500/10 text-gray-400 border-gray-500/20' }
            default: return { text: 'Desconhecido', color: 'bg-dark-border/10 text-gray-500 border-white/5' }
        }
    }

    const cleanGlpiText = (html: string) => {
        if (!html) return 'Sem descrição.'
        const doc = new DOMParser().parseFromString(html, 'text/html')
        let text = doc.body.textContent || ""
        text = text.replace(/<[^>]*>?/gm, ' ')
        return text.replace(/\s\s+/g, ' ').trim()
    }

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setSelectedFile(e.target.files[0])
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="flex flex-col items-center gap-4">
                    <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
                    <span className="text-gray-400 font-bold animate-pulse uppercase tracking-widest text-xs">Sincronizando com GLPI...</span>
                </div>
            </div>
        )
    }

    return (
        <div className="page-transition space-y-8 pb-10">
            {/* Header Section */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="space-y-1">
                    <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
                        <Ticket size={28} className="text-primary" />
                        Helpdesk
                    </h1>
                    <p className="text-dark-muted font-medium text-sm">Gerencie seus chamados de suporte</p>
                </div>

                <div className="flex items-center gap-3">
                    <div className="flex bg-dark-surface p-1 rounded-xl border border-dark-border">
                        {[
                            { id: 'not_solved', name: 'Abertos', icon: Clock },
                            { id: 'solved', name: 'Resolvidos', icon: CheckCircle },
                            { id: 'all', name: 'Todos', icon: Funnel }
                        ].map(t => (
                            <button
                                key={t.id}
                                onClick={() => setFilter(t.id)}
                                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all ${filter === t.id ? 'bg-white text-zinc-900 shadow-sm' : 'text-dark-muted hover:text-white'
                                    }`}
                            >
                                <t.icon size={14} weight={filter === t.id ? 'fill' : 'regular'} />
                                {t.name}
                            </button>
                        ))}
                    </div>

                    <button
                        onClick={() => setIsCreateModalOpen(true)}
                        className="btn-primary flex items-center gap-2 ml-2"
                    >
                        <Plus size={16} weight="bold" />
                        Novo Chamado
                    </button>
                </div>
            </div>

            {/* Quick Stats Bar */}
            {stats && !stats.error && (
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                    {[
                        { label: 'Total', count: stats.total, color: 'text-white' },
                        { label: 'Novos', count: stats.new, color: 'text-indigo-400' },
                        { label: 'Em curso', count: stats.processing, color: 'text-blue-400' },
                        { label: 'Pendente', count: stats.pending, color: 'text-amber-400' },
                        { label: 'Solucionado', count: stats.solved, color: 'text-emerald-400' },
                        { label: 'Fechado', count: stats.closed, color: 'text-zinc-500' }
                    ].map((s, i) => (
                        <div key={i} className="bg-dark-surface/50 border border-dark-border p-3 rounded-xl flex flex-col items-center text-center">
                            <span className="text-[10px] font-semibold text-dark-muted uppercase tracking-wide mb-0.5">{s.label}</span>
                            <span className={`text-lg font-bold ${s.color}`}>{s.count}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Tickets Grid */}
            {ticketsData?.success && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pb-20">
                    {ticketsData?.tickets?.map((ticket, idx) => {
                        const status = getStatusInfo(ticket.status)
                        const location = ticket.location || ticket.location_name || 'Geral'
                        const requester = ticket.requester_name || ticket._users_id_recipient?.name || 'Não identificado'

                        return (
                            <div key={idx} className="ethereal-card p-5 hover:border-zinc-600 transition-colors group flex flex-col h-full animate-in" style={{ animationDelay: `${idx * 50}ms` }}>
                                <div className="flex items-start justify-between mb-4">
                                    <div className="space-y-1.5">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-mono font-medium text-primary bg-primary/10 px-2 py-0.5 rounded">#{ticket.id}</span>
                                            <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${status.color}`}>
                                                {status.text}
                                            </span>
                                        </div>
                                        <h2 className="text-base font-semibold text-white group-hover:text-primary transition-colors line-clamp-1">{ticket.name}</h2>
                                    </div>
                                    <div className="p-2 bg-dark-bg rounded-lg border border-dark-border text-dark-muted">
                                        <Clock size={18} />
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-2 mb-4">
                                    <div className="flex items-center gap-2 text-[11px] text-dark-muted bg-dark-bg/50 px-3 py-1.5 rounded-lg border border-dark-border">
                                        <MapPin size={14} className="text-primary" />
                                        <span className="truncate">Setor: <strong className="text-dark-text font-medium">{location}</strong></span>
                                    </div>
                                    <div className="flex items-center gap-2 text-[11px] text-dark-muted bg-dark-bg/50 px-3 py-1.5 rounded-lg border border-dark-border">
                                        <User size={14} className="text-primary" />
                                        <span className="truncate">Usuário: <strong className="text-dark-text font-medium">{requester}</strong></span>
                                    </div>
                                </div>

                                <div className="bg-dark-surface/50 p-4 rounded-xl border border-dark-border mb-6 flex-grow">
                                    <p className="text-dark-muted text-sm line-clamp-2">
                                        {cleanGlpiText(ticket.content)}
                                    </p>
                                </div>

                                <div className="flex items-center justify-between mt-auto">
                                    <div className="flex items-center gap-2 text-[11px] text-dark-muted font-medium">
                                        <Clock size={14} />
                                        {new Date(ticket.date).toLocaleDateString()}
                                    </div>
                                    <button
                                        onClick={() => setSelectedTicketId(ticket.id)}
                                        className="text-xs font-semibold text-primary hover:text-primary-dark transition-colors flex items-center gap-1"
                                    >
                                        Ver Detalhes <PaperPlaneRight size={14} />
                                    </button>
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}

            {/* --- Detail & Reply Modal - APPLE GLASS DRAGGABLE --- */}
            {selectedTicketId && (
                <div
                    className="fixed inset-0 bg-black/20 flex items-center justify-center z-[110] p-4"
                    onClick={() => setSelectedTicketId(null)}
                >
                    <div
                        className={`relative bg-white/[0.04] backdrop-blur-[40px] backdrop-saturate-[150%] border border-white/20 rounded-[32px] w-full max-w-4xl max-h-[90vh] shadow-[0_32px_128px_-20px_rgba(0,0,0,0.7)] flex flex-col overflow-hidden select-none transition-shadow ${isDragging ? 'shadow-white/10 ring-1 ring-white/20 z-50' : 'z-10'}`}
                        style={{
                            backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%)',
                            transform: `translate(${position.x}px, ${position.y}px)`,
                            transition: isDragging ? 'none' : 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), shadow 0.3s ease, opacity 0.3s ease'
                        }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Modal Header - Draggable Handle */}
                        <div
                            onMouseDown={startDragging}
                            className="sticky top-0 bg-white/[0.02] backdrop-blur-xl border-b border-white/10 p-6 flex items-center justify-between z-10 cursor-grab active:cursor-grabbing"
                        >
                            <div className="flex items-center gap-4">
                                <span className="text-xs font-mono font-black text-primary bg-primary/10 px-3 py-1.5 rounded-xl border border-primary/20">#{selectedTicketId}</span>
                                {ticketDetail && (
                                    <span className={`px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-widest border ${getStatusInfo(ticketDetail.status).color}`}>
                                        {getStatusInfo(ticketDetail.status).text}
                                    </span>
                                )}
                                <h2 className="text-xl font-bold text-white tracking-tight truncate max-w-[300px]">
                                    {ticketDetail?.name || 'Carregando...'}
                                </h2>
                            </div>
                            <button
                                onClick={() => setSelectedTicketId(null)}
                                className="w-8 h-8 flex items-center justify-center rounded-full bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 transition-all active:scale-90 shadow-[0_0_15px_rgba(239,68,68,0.1)] group"
                            >
                                <X size={14} weight="bold" className="group-hover:scale-110 transition-transform" />
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 custom-scrollbar">
                            {isLoadingDetail ? (
                                <div className="flex flex-col items-center justify-center py-20 gap-4">
                                    <div className="animate-spin rounded-full h-10 w-10 border-4 border-primary border-t-transparent shadow-[0_0_15px_rgba(37,99,235,0.2)]"></div>
                                    <span className="text-xs font-bold text-zinc-500 uppercase tracking-[0.2em] animate-pulse">Sincronizando com GLPI...</span>
                                </div>
                            ) : ticketDetail && (
                                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                                    <div className="lg:col-span-8 space-y-8">
                                        {/* Description */}
                                        <div className="space-y-4">
                                            <div className="flex items-center gap-2 text-[10px] font-black text-gray-500 uppercase tracking-[0.2em]">
                                                <ClipboardText size={18} className="text-primary" />
                                                DESCRIÇÃO INICIAL
                                            </div>
                                            <div className="bg-dark-bg/60 p-6 rounded-3xl border border-white/5 text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                                                {cleanGlpiText(ticketDetail.content)}
                                            </div>
                                        </div>

                                        {/* Attachments Section */}
                                        <div className="space-y-4">
                                            <div className="flex items-center gap-2 text-[10px] font-black text-gray-500 uppercase tracking-[0.2em]">
                                                <File size={18} className="text-primary" />
                                                ANEXOS DO CHAMADO ({ticketDetail.documents?.length || 0})
                                            </div>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                {ticketDetail.documents?.map((doc: any, i: number) => {
                                                    const isImage = (doc.filename || '').match(/\.(jpg|jpeg|png|gif)$/i)
                                                    return (
                                                        <a
                                                            key={i}
                                                            href={`/api/glpi/document/${doc.id || doc.documents_id}`}
                                                            target="_blank"
                                                            rel="noreferrer"
                                                            className="flex items-center gap-3 p-3 bg-white/5 rounded-2xl border border-white/5 hover:border-primary/30 transition-all group"
                                                        >
                                                            <div className="p-2 bg-dark-bg rounded-xl">
                                                                {isImage ? <ImageIcon size={20} className="text-status-new" /> : <File size={20} className="text-primary" />}
                                                            </div>
                                                            <div className="flex-1 overflow-hidden">
                                                                <div className="text-xs font-bold text-white truncate">{doc.filename || doc.name || 'Documento'}</div>
                                                                <div className="text-[10px] text-gray-500 uppercase">Clique para baixar</div>
                                                            </div>
                                                            <Download size={18} className="text-gray-600 group-hover:text-primary transition-colors" />
                                                        </a>
                                                    )
                                                })}
                                                {(!ticketDetail.documents || ticketDetail.documents.length === 0) && (
                                                    <div className="col-span-full p-6 text-center bg-white/2 rounded-2xl border border-dashed border-white/5 text-gray-600 text-xs italic">
                                                        Nenhum arquivo anexado a este chamado.
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        {/* Timeline */}
                                        <div className="space-y-6">
                                            <div className="flex items-center gap-2 text-[10px] font-black text-gray-500 uppercase tracking-[0.2em]">
                                                <ChatTeardropText size={18} className="text-primary" />
                                                HISTÓRICO & ACOMPANHAMENTOS
                                            </div>
                                            <div className="space-y-4 relative before:absolute before:left-6 before:top-2 before:bottom-2 before:w-px before:bg-white/5">
                                                {ticketDetail.followups?.map((f: any, i: number) => (
                                                    <div key={i} className="relative pl-14 group">
                                                        <div className="absolute left-[18px] top-1 w-3 h-3 rounded-full bg-primary/20 border-2 border-primary z-10 shadow-[0_0_10px_rgba(var(--primary-rgb),0.3)]"></div>
                                                        <div className="bg-dark-bg/40 p-5 rounded-2xl border border-white/5 group-hover:border-primary/20 transition-all">
                                                            <div className="flex items-center justify-between mb-2">
                                                                <span className="text-xs font-bold text-white uppercase">{f._users_id?.name || 'Técnico'}</span>
                                                                <span className="text-[10px] text-gray-600 font-medium">{new Date(f.date).toLocaleString()}</span>
                                                            </div>
                                                            <div className="text-sm text-gray-400 leading-relaxed whitespace-pre-wrap">
                                                                {cleanGlpiText(f.content)}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="lg:col-span-4 space-y-6">
                                        <div className="flex items-center gap-2 text-[10px] font-black text-gray-500 uppercase tracking-[0.2em]">
                                            <Info size={18} className="text-primary" />
                                            DETALHES DO TICKET
                                        </div>
                                        <div className="bg-dark-bg/40 p-5 rounded-3xl border border-white/5 space-y-6">
                                            <div>
                                                <span className="text-[10px] text-gray-600 font-black uppercase tracking-widest block mb-2">Categoria</span>
                                                <div className="flex items-center gap-2 p-3 bg-white/5 rounded-2xl text-xs font-bold text-white">
                                                    <Tag size={16} className="text-primary" />
                                                    {ticketDetail.category_name || 'Geral'}
                                                </div>
                                            </div>
                                            <div>
                                                <span className="text-[10px] text-gray-600 font-black uppercase tracking-widest block mb-2">Localização</span>
                                                <div className="flex items-center gap-2 p-3 bg-white/5 rounded-2xl text-xs font-bold text-white">
                                                    <MapPin size={16} className="text-primary" />
                                                    {ticketDetail.location || 'Não informado'}
                                                </div>
                                            </div>
                                            <div>
                                                <span className="text-[10px] text-gray-600 font-black uppercase tracking-widest block mb-2">Usuário</span>
                                                <div className="flex items-center gap-2 p-3 bg-white/5 rounded-2xl text-xs font-bold text-white">
                                                    <User size={16} className="text-primary" />
                                                    {ticketDetail.requester_name || 'Sistemas'}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Reply Box with Attachments */}
                                        <div className="bg-primary/5 p-6 rounded-[32px] border border-primary/10 space-y-5">
                                            <span className="text-[10px] text-primary font-black uppercase tracking-widest block">Responder ao suporte</span>
                                            <textarea
                                                value={replyContent}
                                                onChange={e => setReplyContent(e.target.value)}
                                                placeholder="Digite sua mensagem..."
                                                className="w-full h-32 bg-dark-bg p-4 rounded-2xl border border-white/5 text-sm text-white placeholder-gray-600 focus:border-primary/50 transition-all outline-none resize-none"
                                            />

                                            {/* File Selector */}
                                            <div className="space-y-3">
                                                <input
                                                    type="file"
                                                    ref={fileInputRef}
                                                    className="hidden"
                                                    onChange={handleFileChange}
                                                />
                                                {selectedFile ? (
                                                    <div className="flex items-center justify-between p-3 bg-primary/10 rounded-2xl border border-primary/20">
                                                        <div className="flex items-center gap-2 overflow-hidden">
                                                            <FileArrowUp size={18} className="text-primary" />
                                                            <span className="text-xs text-white font-bold truncate">{selectedFile.name}</span>
                                                        </div>
                                                        <button
                                                            onClick={() => setSelectedFile(null)}
                                                            className="p-1.5 hover:bg-white/10 rounded-lg text-gray-400"
                                                        >
                                                            <Trash size={16} />
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <button
                                                        onClick={() => fileInputRef.current?.click()}
                                                        className="w-full flex items-center justify-center gap-2 p-4 bg-dark-bg/50 border border-dashed border-white/10 rounded-2xl text-[10px] font-black text-gray-500 hover:text-white hover:border-primary/30 transition-all uppercase tracking-widest"
                                                    >
                                                        <FileArrowUp size={20} />
                                                        Anexar Imagem ou Log
                                                    </button>
                                                )}
                                            </div>

                                            <button
                                                onClick={() => addFollowupMutation.mutate({ id: ticketDetail.id, content: replyContent, file: selectedFile })}
                                                disabled={!replyContent || addFollowupMutation.isPending}
                                                className="w-full bg-primary hover:bg-primary-dark disabled:opacity-50 text-white p-5 rounded-2xl font-black text-xs uppercase tracking-[0.2em] shadow-xl shadow-primary/20 flex items-center justify-center gap-3 transition-all active:scale-95"
                                            >
                                                {addFollowupMutation.isPending ? 'ENVIANDO...' : <><PaperPlaneRight size={20} weight="fill" /> ENVIAR RESPOSTA</>}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* --- Create Ticket Modal --- */}
            {isCreateModalOpen && (
                <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 md:p-8">
                    <div className="absolute inset-0 bg-black/90 backdrop-blur-xl animate-in fade-in duration-300" onClick={() => !createTicketMutation.isPending && setIsCreateModalOpen(false)}></div>
                    <div className="relative bg-dark-panel w-full max-w-2xl rounded-[40px] border border-white/10 shadow-2xl overflow-hidden flex flex-col animate-in slide-in-from-bottom-8 duration-500">
                        <div className="p-8 border-b border-white/5 flex items-center justify-between">
                            <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
                                <Plus size={32} className="text-primary" />
                                NOVO CHAMADO
                            </h2>
                            <button onClick={() => setIsCreateModalOpen(false)} className="p-2 hover:bg-white/5 rounded-2xl text-gray-500 hover:text-white transition-all"><X size={24} weight="bold" /></button>
                        </div>

                        <div className="p-8 space-y-6 overflow-y-auto custom-scrollbar">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-4">O que está acontecendo?</label>
                                <input
                                    type="text"
                                    placeholder="Ex: Impressora do RH não liga"
                                    value={newTicketForm.title}
                                    onChange={e => setNewTicketForm(p => ({ ...p, title: e.target.value }))}
                                    className="w-full bg-dark-bg p-5 rounded-[24px] border border-white/5 text-white placeholder-gray-700 focus:border-primary/50 transition-all outline-none"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-4">Categoria</label>
                                    <select
                                        value={newTicketForm.category}
                                        onChange={e => setNewTicketForm(p => ({ ...p, category: e.target.value }))}
                                        className="w-full bg-dark-bg p-5 rounded-[24px] border border-white/5 text-white focus:border-primary/50 transition-all outline-none appearance-none"
                                    >
                                        <option value="">Selecione...</option>
                                        {Array.isArray(categories) && categories.map((c: any) => (
                                            <option key={c.id} value={c.id}>{c.completename || c.name}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-4">Onde você está?</label>
                                    <select
                                        value={newTicketForm.location}
                                        onChange={e => setNewTicketForm(p => ({ ...p, location: e.target.value }))}
                                        className="w-full bg-dark-bg p-5 rounded-[24px] border border-white/5 text-white focus:border-primary/50 transition-all outline-none appearance-none"
                                    >
                                        <option value="">Selecione...</option>
                                        {Array.isArray(locations) && locations.map((l: any) => (
                                            <option key={l.id} value={l.id}>{l.completename || l.name}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-4">Descrição Detalhada</label>
                                <textarea
                                    placeholder="Explique o problema detalhadamente..."
                                    value={newTicketForm.content}
                                    onChange={e => setNewTicketForm(p => ({ ...p, content: e.target.value }))}
                                    className="w-full h-40 bg-dark-bg p-6 rounded-[32px] border border-white/5 text-white placeholder-gray-700 focus:border-primary/50 transition-all outline-none resize-none"
                                />
                            </div>

                            <button
                                onClick={() => createTicketMutation.mutate(newTicketForm)}
                                disabled={!newTicketForm.title || !newTicketForm.content || createTicketMutation.isPending}
                                className="w-full bg-primary hover:bg-primary-dark disabled:opacity-50 text-white p-6 rounded-[24px] font-black text-sm uppercase tracking-[0.2em] shadow-2xl shadow-primary/30 transition-all active:scale-95"
                            >
                                {createTicketMutation.isPending ? 'Sincronizando...' : 'CRIAR CHAMADO AGORA'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default Tickets
