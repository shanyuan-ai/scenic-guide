// tool-tester/src/components/RagTest.tsx
import React, { useState, useEffect } from 'react';
import { Search, RefreshCw, Info, Database } from 'lucide-react';

interface RagTestProps {
  apiUrl: string;
  onSetRawJson: (json: any) => void;
}

interface SearchResult {
  id?: number;
  title: string;
  content: string;
  category: string;
  score: number;
  source_type: string;
  retrieval_score?: number;
  rerank_score?: number;
}

interface IndexStatus {
  total_items: number;
  indexed_items: number;
  index_ready: boolean;
  model_error?: string | null;
}

export const RagTest: React.FC<RagTestProps> = ({ apiUrl, onSetRawJson }) => {
  const [query, setQuery] = useState('门票多少钱');
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [status, setStatus] = useState<IndexStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [reindexing, setReindexing] = useState(false);

  const fetchStatus = async () => {
    setStatusLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/tools/rag/index_status`);
      const data = await res.json();
      setStatus(data);
      onSetRawJson({ action: 'index_status', response: data });
    } catch (err: any) {
      console.error(err);
      setStatus(null);
    } finally {
      setStatusLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [apiUrl]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/tools/rag/search?query=${encodeURIComponent(query)}&top_k=${topK}`);
      const data = await res.json();
      setResults(data.results || []);
      onSetRawJson({ action: 'search', query, top_k: topK, response: data });
    } catch (err: any) {
      console.error(err);
      onSetRawJson({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleReindex = async () => {
    setReindexing(true);
    try {
      const res = await fetch(`${apiUrl}/api/tools/rag/reindex`, { method: 'POST' });
      const data = await res.json();
      onSetRawJson({ action: 'reindex', response: data });
      await fetchStatus();
    } catch (err: any) {
      console.error(err);
      onSetRawJson({ error: err.message });
    } finally {
      setReindexing(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Index Status & Actions Panel */}
      <div className="glass-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Database size={20} className="text-accent" style={{ color: 'var(--accent)' }} />
            <h3 style={{ margin: 0 }}>知识库索引状态</h3>
          </div>
          {status && (
            <div style={{ display: 'flex', gap: '1rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              <span>总文档: <strong style={{ color: 'var(--text-primary)' }}>{status.total_items}</strong></span>
              <span>已索引: <strong style={{ color: 'var(--text-primary)' }}>{status.indexed_items}</strong></span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                就绪: 
                <strong style={{ color: status.index_ready ? 'var(--success)' : 'var(--warning)' }}>
                  {status.index_ready ? '已就绪' : '待更新'}
                </strong>
              </span>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button 
            onClick={fetchStatus} 
            className="btn btn-secondary" 
            disabled={statusLoading}
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            <RefreshCw size={14} className={statusLoading ? 'animate-spin' : ''} />
            刷新状态
          </button>
          <button 
            onClick={handleReindex} 
            className="btn btn-primary" 
            disabled={reindexing}
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            <RefreshCw size={14} className={reindexing ? 'animate-spin' : ''} />
            {reindexing ? '正在重构...' : '重构索引'}
          </button>
        </div>
      </div>

      {status?.model_error && (
        <div className="glass-card" style={{ borderColor: 'var(--error)', backgroundColor: 'var(--error-glow)', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <Info size={18} style={{ color: 'var(--error)' }} />
          <span style={{ color: 'var(--error)', fontSize: '0.9rem' }}>模型加载错误: {status.model_error}</span>
        </div>
      )}

      {/* Query Form */}
      <div className="glass-card">
        <h3 style={{ marginBottom: '1.25rem' }}>检索测试</h3>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
          <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
            <label htmlFor="query">检索问题 (Query)</label>
            <input
              id="query"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="请输入您的问题，例如：灵山大佛手势含义..."
              required
            />
          </div>
          
          <div className="form-group" style={{ width: '120px', marginBottom: 0 }}>
            <label htmlFor="top_k">返回条数 (Top K)</label>
            <select
              id="top_k"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
            >
              {[1, 3, 5, 10, 20, 30].map(k => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </div>

          <button type="submit" className="btn btn-primary" disabled={loading} style={{ height: '42px', padding: '0 1.5rem' }}>
            <Search size={16} className={loading ? 'animate-spin' : ''} />
            {loading ? '正在检索...' : '开始检索'}
          </button>
        </form>
      </div>

      {/* Results Section */}
      <div className="glass-card">
        <h3 style={{ marginBottom: '1rem' }}>检索结果 ({results.length})</h3>
        {results.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>
            没有匹配的文档。请输入内容并进行检索。
          </div>
        ) : (
          <div className="result-list">
            {results.map((item, idx) => (
              <div key={item.id || idx} className="result-item">
                <div className="result-title-row">
                  <div>
                    <h4 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                      {item.title}
                    </h4>
                    <div className="result-meta">
                      <span className="badge" style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                        ID: {item.id}
                      </span>
                      <span className="badge" style={{ backgroundColor: 'var(--accent-glow)', color: 'var(--accent)', fontSize: '0.7rem' }}>
                        {item.category}
                      </span>
                      <span className="badge" style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-secondary)', fontSize: '0.7rem' }}>
                        来源: {item.source_type}
                      </span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span className="badge" style={{ backgroundColor: 'var(--success-glow)', color: 'var(--success)', fontSize: '0.8rem', padding: '0.3rem 0.6rem' }}>
                      得分: {item.score.toFixed(3)}
                    </span>
                    {item.rerank_score !== undefined && item.rerank_score !== null && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                        重排: {item.rerank_score.toFixed(3)} | 召回: {item.retrieval_score?.toFixed(3)}
                      </div>
                    )}
                  </div>
                </div>
                <p className="result-content" style={{ marginTop: '0.75rem' }}>
                  {item.content}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
