// tool-tester/src/App.tsx
import { useState, useEffect } from 'react';
import { Database, Globe, ShieldAlert, MessageSquare, Terminal, RefreshCw, Copy, Check, RotateCcw, Play } from 'lucide-react';
import { RagTest } from './components/RagTest';
import { WebSearchTest } from './components/WebSearchTest';
import { EmergencyTest } from './components/EmergencyTest';
import { FeedbackTest } from './components/FeedbackTest';

type TabType = 'rag' | 'web_search' | 'emergency' | 'feedback';

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('rag');
  const [apiUrl, setApiUrl] = useState('http://localhost:8000');
  const [backendStatus, setBackendStatus] = useState<'online' | 'offline' | 'checking'>('checking');
  const [rawJson, setRawJson] = useState<any>(null);
  const [copied, setCopied] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [startingBackend, setStartingBackend] = useState(false);

  const checkConnection = async () => {
    setBackendStatus('checking');
    try {
      const res = await fetch(apiUrl + '/');
      if (res.ok) {
        setBackendStatus('online');
      } else {
        setBackendStatus('offline');
      }
    } catch (e) {
      setBackendStatus('offline');
    }
  };

  const handleStartBackend = async () => {
    setStartingBackend(true);
    setBackendStatus('checking');
    try {
      // 向 Vite 开发服务器发送启动后端的 POST 请求
      const res = await fetch('/api/system/start-backend', { method: 'POST' });
      const data = await res.json();
      setRawJson({ action: 'vite/start-backend', response: data });
    } catch (err: any) {
      setRawJson({ error: '无法向 Vite 发送启动命令', detail: err.message });
    }

    // 轮询检测后端接口，最多尝试 16 次（共 8 秒）
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      try {
        const res = await fetch(apiUrl + '/');
        if (res.ok) {
          setBackendStatus('online');
          setStartingBackend(false);
          clearInterval(interval);
        }
      } catch (e) {
        if (attempts >= 16) {
          setBackendStatus('offline');
          setStartingBackend(false);
          clearInterval(interval);
        }
      }
    }, 500);
  };

  const handleRestartBackend = async () => {
    if (!window.confirm('确定要重启后端服务吗？')) return;
    setRestarting(true);
    setBackendStatus('checking');
    try {
      const res = await fetch(`${apiUrl}/api/system/restart`, { method: 'POST' });
      const data = await res.json();
      setRawJson({ action: 'system/restart', response: data });
    } catch (err: any) {
      setRawJson({ error: '请求重启已发送，服务可能已在重启或断开', detail: err.message });
    }
    // 等待 2.5 秒后重新检测并恢复按钮状态
    setTimeout(async () => {
      await checkConnection();
      setRestarting(false);
    }, 2500);
  };

  useEffect(() => {
    checkConnection();
  }, [apiUrl]);

  const handleCopyJson = () => {
    if (!rawJson) return;
    navigator.clipboard.writeText(JSON.stringify(rawJson, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'rag':
        return <RagTest apiUrl={apiUrl} onSetRawJson={setRawJson} />;
      case 'web_search':
        return <WebSearchTest apiUrl={apiUrl} onSetRawJson={setRawJson} />;
      case 'emergency':
        return <EmergencyTest apiUrl={apiUrl} onSetRawJson={setRawJson} />;
      case 'feedback':
        return <FeedbackTest apiUrl={apiUrl} onSetRawJson={setRawJson} />;
      default:
        return null;
    }
  };

  return (
    <div className="dashboard">
      {/* Navigation Sidebar */}
      <aside className="sidebar">
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', fontSize: '1.4rem' }}>
            景区智能导览
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>工具能力集成测试面板</p>
        </div>

        <nav>
          <ul className="nav-list">
            <li className="nav-item">
              <button
                className={`nav-btn ${activeTab === 'rag' ? 'active' : ''}`}
                onClick={() => setActiveTab('rag')}
              >
                <Database size={18} />
                RAG 知识检索
              </button>
            </li>
            <li className="nav-item">
              <button
                className={`nav-btn ${activeTab === 'web_search' ? 'active' : ''}`}
                onClick={() => setActiveTab('web_search')}
              >
                <Globe size={18} />
                联网搜索 (Tavily)
              </button>
            </li>
            <li className="nav-item">
              <button
                className={`nav-btn ${activeTab === 'emergency' ? 'active' : ''}`}
                onClick={() => setActiveTab('emergency')}
              >
                <ShieldAlert size={18} />
                应急管理系统
              </button>
            </li>
            <li className="nav-item">
              <button
                className={`nav-btn ${activeTab === 'feedback' ? 'active' : ''}`}
                onClick={() => setActiveTab('feedback')}
              >
                <MessageSquare size={18} />
                游客反馈系统
              </button>
            </li>
          </ul>
        </nav>

        <div style={{ marginTop: 'auto', borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div className="server-status">
              <span className={`status-dot ${backendStatus}`}></span>
              <span style={{ textTransform: 'capitalize' }}>
                服务状态: {backendStatus === 'online' ? '运行中' : backendStatus === 'offline' ? '已断开' : '检查中...'}
              </span>
            </div>
            <button 
              className="btn btn-secondary" 
              onClick={checkConnection}
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem', width: '100%' }}
            >
              <RefreshCw size={12} className={backendStatus === 'checking' ? 'animate-spin' : ''} />
              重新检测
            </button>
            <button 
              className="btn btn-danger" 
              onClick={handleRestartBackend}
              disabled={restarting}
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem', width: '100%', gap: '0.4rem' }}
            >
              <RotateCcw size={12} className={restarting ? 'animate-spin' : ''} />
              {restarting ? '重启中...' : '重启后端'}
            </button>
            {backendStatus === 'offline' && (
              <button 
                className="btn btn-primary" 
                onClick={handleStartBackend}
                disabled={startingBackend}
                style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem', width: '100%', gap: '0.4rem', backgroundColor: 'var(--success)' }}
              >
                <Play size={12} className={startingBackend ? 'animate-spin' : ''} />
                {startingBackend ? '正在启动...' : '一键启动后端'}
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* Main Panel */}
      <main className="main-content">
        <header className="global-header">
          <h2>
            {activeTab === 'rag' && 'RAG 检索工具测试'}
            {activeTab === 'web_search' && '联网搜索与网页正文提取'}
            {activeTab === 'emergency' && '应急预案与事件上报测试'}
            {activeTab === 'feedback' && '游客意见、投诉与求助反馈'}
          </h2>
          
          <div className="api-url-input">
            <label htmlFor="api-url" style={{ whiteSpace: 'nowrap' }}>后端服务地址:</label>
            <input
              id="api-url"
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="http://localhost:8000"
            />
          </div>
        </header>

        {/* Dynamic Tab Body */}
        <section style={{ flexGrow: 1 }}>
          {renderTabContent()}
        </section>

        {/* Bottom JSON Output Console */}
        <footer className="json-container">
          <div className="json-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Terminal size={14} style={{ color: 'var(--text-muted)' }} />
              <span>调试输出控制台 (Last Action JSON Output)</span>
            </div>
            {rawJson && (
              <button 
                onClick={handleCopyJson}
                style={{ 
                  background: 'transparent', 
                  border: 'none', 
                  color: 'var(--text-muted)', 
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  fontSize: '0.75rem'
                }}
              >
                {copied ? <Check size={14} className="text-success" style={{ color: 'var(--success)' }} /> : <Copy size={14} />}
                {copied ? '已复制' : '复制 JSON'}
              </button>
            )}
          </div>
          <div className="json-body">
            {rawJson ? JSON.stringify(rawJson, null, 2) : '// 在上方执行任何操作，相应的请求与响应 JSON 会在此实时更新展示。'}
          </div>
        </footer>
      </main>
    </div>
  );
}

export default App;
