import { useState, useRef, useEffect } from 'react'
import {
    Desktop, HardDrives, WifiHigh,
    Globe, SquaresFour, Plus,
    Trash, Download, ShareNetwork, MagnifyingGlass,
    ArrowsOut, Selection, HandPointing, Link, Lightning,
    Shield, Cloud, Database, PencilSimple
} from '@phosphor-icons/react'
import api from '../services/api'
import type { Device } from '../types'

interface Node {
    id: string
    type: 'pc' | 'server' | 'router' | 'switch' | 'wifi' | 'globe' | 'firewall' | 'database' | 'cloud'
    x: number
    y: number
    label: string
}

interface Connection {
    id: string
    from: string
    to: string
}

const Topology = () => {
    const [nodes, setNodes] = useState<Node[]>(() => {
        const saved = localStorage.getItem('netaudit_topology_nodes')
        return saved ? JSON.parse(saved) : []
    })
    const [connections, setConnections] = useState<Connection[]>(() => {
        const saved = localStorage.getItem('netaudit_topology_conns')
        return saved ? JSON.parse(saved) : []
    })
    const [draggingNode, setDraggingNode] = useState<string | null>(null)
    const [connectingNode, setConnectingNode] = useState<string | null>(null)
    const [searchTerm, setSearchTerm] = useState('')
    const [zoom, setZoom] = useState(1)
    const [viewport, setViewport] = useState({ x: 0, y: 0 })
    const [mode, setMode] = useState<'select' | 'pan'>('select')
    const [isPanning, setIsPanning] = useState(false)
    const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
    const [editingNode, setEditingNode] = useState<string | null>(null)
    const [editValue, setEditValue] = useState('')
    const canvasRef = useRef<HTMLDivElement>(null)
    const dragStartPos = useRef({ x: 0, y: 0 })
    const panStartPos = useRef({ x: 0, y: 0 })

    // Auto-save logic
    useEffect(() => {
        if (nodes.length > 0) {
            localStorage.setItem('netaudit_topology_nodes', JSON.stringify(nodes))
        }
        if (connections.length > 0) {
            localStorage.setItem('netaudit_topology_conns', JSON.stringify(connections))
        }
    }, [nodes, connections])

    const tools = [
        { type: 'router', name: 'Roteador', icon: <Globe size={24} />, color: 'text-blue-400', glow: 'shadow-blue-500/20' },
        { type: 'switch', name: 'Switch', icon: <SquaresFour size={24} />, color: 'text-indigo-400', glow: 'shadow-indigo-500/20' },
        { type: 'firewall', name: 'Firewall', icon: <Shield size={24} />, color: 'text-red-400', glow: 'shadow-red-500/20' },
        { type: 'server', name: 'Servidor', icon: <HardDrives size={24} />, color: 'text-amber-400', glow: 'shadow-amber-500/20' },
        { type: 'database', name: 'Banco Dados', icon: <Database size={24} />, color: 'text-emerald-400', glow: 'shadow-emerald-500/20' },
        { type: 'pc', name: 'Estação PC', icon: <Desktop size={24} />, color: 'text-zinc-400', glow: 'shadow-zinc-500/20' },
        { type: 'wifi', name: 'Access Point', icon: <WifiHigh size={24} />, color: 'text-purple-400', glow: 'shadow-purple-500/20' },
        { type: 'cloud', name: 'Nuvem/Internet', icon: <Cloud size={24} />, color: 'text-cyan-400', glow: 'shadow-cyan-500/20' },
    ]

    const importFromScanner = async () => {
        try {
            const res = await api.get('/api/scanner/results')
            const devices: Device[] = res.data

            const newNodes: Node[] = devices.map((device, index) => {
                let type: any = 'pc'
                const dtype = device.device_type?.toLowerCase() || ''
                if (dtype.includes('router') || dtype.includes('network')) type = 'router'
                if (dtype.includes('server')) type = 'server'
                if (dtype.includes('switch')) type = 'switch'
                if (dtype.includes('printer')) type = 'wifi' // Mocking printer as wifi icon for now

                return {
                    id: `scan-${device.ip}`,
                    type,
                    x: 100 + (index % 5) * 150,
                    y: 100 + Math.floor(index / 5) * 150,
                    label: device.hostname || device.ip
                }
            })

            // Filter out existing ones
            const existingIds = new Set(nodes.map(n => n.id))
            const uniqueNewNodes = newNodes.filter(n => !existingIds.has(n.id))

            setNodes([...nodes, ...uniqueNewNodes])
        } catch (error) {
            console.error("Failed to import scanner results", error)
        }
    }

    const addNode = (type: any, x = 100, y = 100) => {
        const newNode: Node = {
            id: Math.random().toString(36).substr(2, 9),
            type,
            x,
            y,
            label: `${type.charAt(0).toUpperCase() + type.slice(1)} ${nodes.length + 1}`
        }
        setNodes([...nodes, newNode])
    }

    const removeNode = (id: string, e: React.MouseEvent) => {
        e.stopPropagation()
        setNodes(nodes.filter(n => n.id !== id))
        setConnections(connections.filter(c => c.from !== id && c.to !== id))
    }

    const handleCanvasMouseDown = (e: React.MouseEvent) => {
        if (mode === 'pan') {
            setIsPanning(true)
            panStartPos.current = {
                x: e.clientX - viewport.x,
                y: e.clientY - viewport.y
            }
            document.body.style.cursor = 'grabbing'
        }
    }

    const startDragging = (id: string, e: React.MouseEvent) => {
        if (connectingNode || mode === 'pan') return
        // Prevent drag when clicking controls
        if ((e.target as HTMLElement).closest('button')) return

        e.stopPropagation()
        setDraggingNode(id)
        const node = nodes.find(n => n.id === id)
        if (node) {
            dragStartPos.current = {
                x: (e.clientX / zoom) - node.x,
                y: (e.clientY / zoom) - node.y
            }
        }
    }

    const handleMouseMove = (e: MouseEvent) => {
        if (isPanning) {
            setViewport({
                x: e.clientX - panStartPos.current.x,
                y: e.clientY - panStartPos.current.y
            })
            return
        }

        if (draggingNode) {
            setNodes(nodes.map(n =>
                n.id === draggingNode
                    ? { ...n, x: (e.clientX / zoom) - dragStartPos.current.x, y: (e.clientY / zoom) - dragStartPos.current.y }
                    : n
            ))
        }

        if (connectingNode && canvasRef.current) {
            const rect = canvasRef.current.getBoundingClientRect()
            setMousePos({
                x: (e.clientX - rect.left - viewport.x) / zoom,
                y: (e.clientY - rect.top - viewport.y) / zoom
            })
        }
    }

    const handleMouseUp = () => {
        setDraggingNode(null)
        setIsPanning(false)
        document.body.style.cursor = 'default'
    }

    const handleWheel = (e: React.WheelEvent) => {
        if (e.ctrlKey) {
            e.preventDefault()
            const delta = e.deltaY > 0 ? 0.9 : 1.1
            setZoom(prev => Math.min(Math.max(prev * delta, 0.2), 3))
        }
    }

    const fitToScreen = () => {
        setViewport({ x: 0, y: 0 })
        setZoom(1)
    }

    useEffect(() => {
        window.addEventListener('mousemove', handleMouseMove)
        window.addEventListener('mouseup', handleMouseUp)
        return () => {
            window.removeEventListener('mousemove', handleMouseMove)
            window.removeEventListener('mouseup', handleMouseUp)
        }
    }, [draggingNode, nodes, connectingNode, isPanning, viewport, zoom, mode])

    const startEditing = (id: string, currentLabel: string, e: React.MouseEvent) => {
        e.stopPropagation()
        setEditingNode(id)
        setEditValue(currentLabel)
    }

    const saveName = (id: string) => {
        setNodes(nodes.map(n => n.id === id ? { ...n, label: editValue } : n))
        setEditingNode(null)
    }

    const handleConnect = (id: string, e: React.MouseEvent) => {
        e.stopPropagation()
        if (!connectingNode) {
            setConnectingNode(id)
        } else {
            if (connectingNode !== id) {
                const connId = `${connectingNode}-${id}`
                if (!connections.find(c => c.id === connId)) {
                    setConnections([...connections, { id: connId, from: connectingNode, to: id }])
                }
            }
            setConnectingNode(null)
        }
    }

    const filteredTools = tools.filter(t => t.name.toLowerCase().includes(searchTerm.toLowerCase()))

    return (
        <div className="page-transition space-y-6 h-[calc(100vh-140px)] flex flex-col">
            {/* Header Area */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="space-y-1">
                    <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
                        <ShareNetwork size={32} className="text-primary" weight="fill" />
                        Topologia de Rede
                    </h1>
                    <p className="text-dark-muted text-sm font-medium">Desenhe e gerencie a infraestrutura visual da sua rede.</p>
                </div>

                <div className="flex items-center gap-3">
                    <button className="p-3 bg-dark-surface hover:bg-white/10 rounded-xl border border-dark-border text-dark-muted transition-all">
                        <Download size={20} />
                    </button>
                    <button
                        onClick={importFromScanner}
                        className="bg-primary/20 hover:bg-primary/30 text-primary p-3 rounded-xl border border-primary/30 transition-all flex items-center gap-2 font-bold text-xs"
                        title="Importar do Scanner"
                    >
                        <Lightning size={18} weight="fill" />
                        AUTO-IMPORT
                    </button>
                    <button
                        onClick={() => { setNodes([]); setConnections([]); }}
                        className="btn-primary flex items-center gap-2"
                    >
                        <Plus size={18} weight="bold" />
                        Novo Desenho
                    </button>
                </div>
            </div>

            <div className="flex-1 flex gap-6 overflow-hidden">
                {/* Left Sidebar - Toolbox */}
                <div className="w-[280px] flex flex-col gap-4">
                    {/* Search Component */}
                    <div className="bg-dark-surface/50 p-2 rounded-2xl border border-dark-border flex items-center gap-2 group focus-within:border-primary/50 transition-all">
                        <MagnifyingGlass size={16} className="text-dark-muted ml-2" />
                        <input
                            type="text"
                            placeholder="Buscar ativo..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="bg-transparent border-none text-xs text-white placeholder:text-dark-muted focus:ring-0 w-full font-medium"
                        />
                    </div>

                    {/* Draggable Assets */}
                    <div className="bg-dark-panel/30 border border-dark-border rounded-3xl p-4 flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-3">
                        <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em] mb-2 px-1">Ativos de Rede</h3>
                        {filteredTools.map(tool => (
                            <div
                                key={tool.type}
                                onClick={() => addNode(tool.type)}
                                className="group flex items-center gap-4 p-4 bg-white/[0.03] hover:bg-white/[0.06] border border-white/5 hover:border-white/10 rounded-2xl cursor-pointer transition-all active:scale-95 shadow-sm"
                            >
                                <div className={`p-3 bg-dark-bg rounded-xl group-hover:bg-primary/10 transition-colors ${tool.color}`}>
                                    {tool.icon}
                                </div>
                                <div>
                                    <div className="text-xs font-bold text-white group-hover:text-primary transition-colors">{tool.name}</div>
                                    <div className="text-[9px] text-dark-muted font-bold uppercase tracking-wider opacity-60">Padrão SNMP</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Main Drawing Canvas Area */}
                <div
                    ref={canvasRef}
                    onMouseDown={handleCanvasMouseDown}
                    onWheel={handleWheel}
                    className={`flex-1 bg-dark-panel/20 border border-dark-border rounded-[40px] relative overflow-hidden group/canvas ${mode === 'pan' ? 'cursor-grab active:cursor-grabbing' : ''}`}
                    style={{
                        backgroundImage: `radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px)`,
                        backgroundSize: `${30 * zoom}px ${30 * zoom}px`,
                        backgroundPosition: `${viewport.x}px ${viewport.y}px`
                    }}
                >
                    {/* Transform Container for Panning and Zooming */}
                    <div
                        className="absolute inset-0 pointer-events-none"
                        style={{
                            transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${zoom})`,
                            transformOrigin: '0 0',
                            transition: isPanning ? 'none' : 'transform 0.1s ease-out'
                        }}
                    >
                        <div className="pointer-events-auto w-full h-full relative">
                            {/* Canvas Controls Overlay */}
                            <div className="absolute top-6 left-6 flex items-center gap-2 z-50">
                                <div className="bg-black/40 backdrop-blur-xl border border-white/10 p-1.5 rounded-xl flex items-center gap-1 shadow-2xl">
                                    <button
                                        onClick={() => setMode('select')}
                                        className={`p-2 rounded-lg transition-all ${mode === 'select' ? 'bg-primary text-white shadow-lg' : 'text-dark-muted hover:text-white'}`}
                                        title="Selecionar"
                                    >
                                        <Selection size={18} />
                                    </button>
                                    <button
                                        onClick={() => setMode('pan')}
                                        className={`p-2 rounded-lg transition-all ${mode === 'pan' ? 'bg-primary text-white shadow-lg' : 'text-dark-muted hover:text-white'}`}
                                        title="Mover Câmera"
                                    >
                                        <HandPointing size={18} />
                                    </button>
                                    <div className="w-px h-4 bg-white/10 mx-1"></div>
                                    <button
                                        onClick={fitToScreen}
                                        className="p-2 text-dark-muted hover:text-white transition-colors"
                                        title="Ajustar Tela"
                                    >
                                        <ArrowsOut size={18} />
                                    </button>
                                </div>
                                {connectingNode && (
                                    <div className="bg-amber-500/20 text-amber-500 border border-amber-500/30 px-4 py-2 rounded-xl text-xs font-bold animate-pulse backdrop-blur-md">
                                        Selecione outro dispositivo para conectar...
                                    </div>
                                )}
                                <div className="bg-black/40 backdrop-blur-xl border border-white/10 px-3 py-2 rounded-xl text-[10px] font-bold text-dark-muted shadow-2xl">
                                    ZOOM: {Math.round(zoom * 100)}%
                                </div>
                            </div>

                            {/* SVG Connections Layer */}
                            <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
                                <defs>
                                    <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                                        <stop offset="0%" stopColor="rgba(129, 140, 248, 0.2)" />
                                        <stop offset="50%" stopColor="rgba(129, 140, 248, 0.8)" />
                                        <stop offset="100%" stopColor="rgba(129, 140, 248, 0.2)" />
                                    </linearGradient>
                                    <filter id="glow">
                                        <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                                        <feMerge>
                                            <feMergeNode in="coloredBlur" />
                                            <feMergeNode in="SourceGraphic" />
                                        </feMerge>
                                    </filter>
                                </defs>
                                {connections.map(conn => {
                                    const from = nodes.find(n => n.id === conn.from)
                                    const to = nodes.find(n => n.id === conn.to)
                                    if (!from || !to) return null
                                    return (
                                        <g key={conn.id}>
                                            <line
                                                x1={from.x + 32}
                                                y1={from.y + 32}
                                                x2={to.x + 32}
                                                y2={to.y + 32}
                                                stroke="rgba(129, 140, 248, 0.2)"
                                                strokeWidth="4"
                                                strokeLinecap="round"
                                            />
                                            <line
                                                x1={from.x + 32}
                                                y1={from.y + 32}
                                                x2={to.x + 32}
                                                y2={to.y + 32}
                                                stroke="url(#lineGrad)"
                                                strokeWidth="2"
                                                strokeDasharray="10 15"
                                                filter="url(#glow)"
                                                className="animate-flow"
                                            />
                                        </g>
                                    )
                                })}
                                {/* Preview Line while connecting */}
                                {connectingNode && nodes.find(n => n.id === connectingNode) && (
                                    <line
                                        x1={nodes.find(n => n.id === connectingNode)!.x + 32}
                                        y1={nodes.find(n => n.id === connectingNode)!.y + 32}
                                        x2={mousePos.x}
                                        y2={mousePos.y}
                                        stroke="rgba(129, 140, 248, 0.6)"
                                        strokeWidth="2"
                                        strokeDasharray="8 8"
                                        className="animate-dash"
                                    />
                                )}
                            </svg>

                            {/* Nodes (Devices) */}
                            {nodes.map(node => (
                                <div
                                    key={node.id}
                                    style={{ left: node.x, top: node.y }}
                                    onMouseDown={(e) => startDragging(node.id, e)}
                                    className={`absolute w-16 h-16 flex flex-col items-center justify-center cursor-grab active:cursor-grabbing group/node z-20 ${draggingNode === node.id ? 'z-50' : ''}`}
                                >
                                    <div className={`
                                w-full h-full rounded-2xl border backdrop-blur-md flex items-center justify-center shadow-xl transition-all duration-300
                                ${connectingNode === node.id ? 'bg-primary/20 border-primary shadow-[0_0_20px_rgba(129,140,248,0.4)]' : 'bg-white/[0.04] border-white/10 hover:border-primary/40 hover:bg-white/[0.08]'}
                                ${draggingNode === node.id ? 'scale-110 shadow-2xl opacity-80' : ''}
                            `}>
                                        <div className={`transition-colors flex flex-col items-center ${node.type === 'router' ? 'text-blue-400' :
                                            node.type === 'switch' ? 'text-indigo-400' :
                                                node.type === 'firewall' ? 'text-red-400' :
                                                    node.type === 'server' ? 'text-amber-400' :
                                                        node.type === 'database' ? 'text-emerald-400' :
                                                            node.type === 'pc' ? 'text-zinc-400' :
                                                                node.type === 'cloud' ? 'text-cyan-400' : 'text-purple-400'
                                            }`}>
                                            {node.type === 'pc' && <Desktop size={26} weight="fill" />}
                                            {node.type === 'router' && <Globe size={26} weight="fill" />}
                                            {node.type === 'switch' && <SquaresFour size={26} weight="fill" />}
                                            {node.type === 'firewall' && <Shield size={26} weight="fill" />}
                                            {node.type === 'server' && <HardDrives size={26} weight="fill" />}
                                            {node.type === 'database' && <Database size={26} weight="fill" />}
                                            {node.type === 'wifi' && <WifiHigh size={26} weight="fill" />}
                                            {node.type === 'cloud' && <Cloud size={26} weight="fill" />}
                                        </div>

                                        {/* Floating Tooltip Controls - Added padding bridge to avoid hover loss */}
                                        <div className="absolute -top-12 left-1/2 -translate-x-1/2 opacity-0 group-hover/node:opacity-100 transition-all flex items-center gap-1.5 pointer-events-none group-hover/node:pointer-events-auto pb-4 px-4 bg-transparent">
                                            <button
                                                onMouseDown={(e) => e.stopPropagation()}
                                                onClick={(e) => startEditing(node.id, node.label, e)}
                                                className="p-2 bg-white text-black rounded-xl hover:bg-emerald-500 hover:text-white transition-all shadow-xl active:scale-90"
                                                title="Renomear"
                                            >
                                                <PencilSimple size={16} weight="bold" />
                                            </button>
                                            <button
                                                onMouseDown={(e) => e.stopPropagation()} // Stop drag from parent
                                                onClick={(e) => handleConnect(node.id, e)}
                                                className="p-2 bg-white text-black rounded-xl hover:bg-primary hover:text-white transition-all shadow-xl active:scale-90"
                                                title="Conectar"
                                            >
                                                <Link size={16} weight="bold" />
                                            </button>
                                            <button
                                                onMouseDown={(e) => e.stopPropagation()}
                                                onClick={(e) => removeNode(node.id, e)}
                                                className="p-2 bg-white text-black rounded-xl hover:bg-red-500 hover:text-white transition-all shadow-xl active:scale-90"
                                                title="Excluir"
                                            >
                                                <Trash size={16} weight="bold" />
                                            </button>
                                        </div>
                                    </div>

                                    {editingNode === node.id ? (
                                        <div className="absolute -bottom-8 w-max z-50">
                                            <input
                                                autoFocus
                                                value={editValue}
                                                onChange={(e) => setEditValue(e.target.value)}
                                                onKeyDown={(e) => e.key === 'Enter' && saveName(node.id)}
                                                onBlur={() => saveName(node.id)}
                                                className="bg-primary/90 backdrop-blur-md border border-white/20 rounded-lg px-2 py-0.5 text-[10px] font-bold text-white uppercase text-center focus:ring-2 ring-white/50 w-32 outline-none shadow-2xl"
                                            />
                                        </div>
                                    ) : (
                                        <div
                                            onDoubleClick={(e) => startEditing(node.id, node.label, e as any)}
                                            className="absolute -bottom-6 w-max bg-black/60 backdrop-blur-md border border-white/5 rounded-full px-2 py-0.5 text-[8px] font-bold text-white uppercase tracking-wider shadow-sm opacity-80 cursor-text hover:bg-black/80 transition-colors"
                                        >
                                            {node.label}
                                        </div>
                                    )}
                                </div>
                            ))}

                        </div>
                    </div>

                    {!nodes.length && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-8 pointer-events-none">
                            <div className="w-20 h-20 bg-primary/5 rounded-[32px] flex items-center justify-center mb-6 opacity-30">
                                <Selection size={40} className="text-primary" />
                            </div>
                            <h4 className="text-lg font-bold text-white mb-1 opacity-50 uppercase tracking-tighter">Área de Projeto Vazia</h4>
                            <p className="text-xs text-dark-muted max-w-[240px] uppercase font-bold tracking-widest opacity-40 leading-relaxed">Arraste ativos da barra lateral ou clique neles para começar seu desenho.</p>
                        </div>
                    )}
                </div>
            </div>

            <style>{`
                @keyframes dash {
                    to { stroke-dashoffset: -20; }
                }
                @keyframes flow {
                    to { stroke-dashoffset: -50; }
                }
                .animate-dash {
                    animation: dash 5s linear infinite;
                }
                .animate-flow {
                    animation: flow 3s linear infinite;
                }
                .custom-scrollbar::-webkit-scrollbar {
                    width: 4px;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: rgba(255,255,255,0.1);
                    border-radius: 10px;
                }
            `}</style>
        </div>
    )
}

export default Topology
