import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { WarningOctagon, ArrowsClockwise } from '@phosphor-icons/react';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
        errorInfo: null
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error, errorInfo: null };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("Uncaught error:", error, errorInfo);
        this.setState({ errorInfo });
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-dark-bg p-8 text-white font-sans">
                    <div className="max-w-2xl w-full bg-dark-panel border border-red-500/20 rounded-3xl p-8 shadow-2xl">
                        <div className="flex items-center gap-4 mb-6 text-red-500">
                            <div className="p-4 bg-red-500/10 rounded-2xl">
                                <WarningOctagon size={48} weight="fill" />
                            </div>
                            <h1 className="text-3xl font-black tracking-tight">System Crash</h1>
                        </div>

                        <p className="text-gray-400 mb-6 font-medium">
                            Ocorreu um erro crítico na renderização da interface.
                        </p>

                        <div className="bg-black/50 p-4 rounded-xl border border-white/5 font-mono text-xs text-red-300 overflow-auto max-h-64 mb-6">
                            <p className="font-bold mb-2">{this.state.error?.toString()}</p>
                            <pre className="text-gray-500">{this.state.errorInfo?.componentStack}</pre>
                        </div>

                        <div className="flex gap-4">
                            <button
                                onClick={() => window.location.reload()}
                                className="bg-primary hover:bg-primary-dark text-white px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all"
                            >
                                <ArrowsClockwise size={20} weight="bold" />
                                REINICIAR SISTEMA
                            </button>
                            <button
                                onClick={() => { localStorage.clear(); window.location.href = '/login'; }}
                                className="bg-dark-bg hover:bg-white/5 border border-white/10 text-gray-300 px-6 py-3 rounded-xl font-bold transition-all"
                            >
                                LIMPAR SESSÃO
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
