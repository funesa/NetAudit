import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import ErrorBoundary from './components/ErrorBoundary'

// Global error handler for debugging "black screen"
window.onerror = (msg, url, lineNo, columnNo, error) => {
  console.error('Frontend Crash:', { msg, url, lineNo, columnNo, error });
  // alert('Erro Crítico no Frontend: ' + msg); // Alert pode ser intrusivo, o ErrorBoundary é melhor
  return false;
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
