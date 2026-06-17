// tool-tester/src/components/WebSearchTest.tsx
import React, { useState } from 'react';
import { Search, FileText, Globe, Link as LinkIcon } from 'lucide-react';

interface WebSearchTestProps {
  apiUrl: string;
  onSetRawJson: (json: any) => void;
}

interface SearchResult {
  title: string;
  url: string;
  content: string;
  score?: number;
}

interface ExtractResult {
  url: string;
  title: string;
  raw_content: string;
}

export const WebSearchTest: React.FC<WebSearchTestProps> = ({ apiUrl, onSetRawJson }) => {
  const [action, setAction] = useState<'search' | 'extract'>('search');
  
  // Search params
  const [query, setQuery] = useState('无锡鼋头渚樱花节时间');
  const [maxResults, setMaxResults] = useState(5);
  const [searchDepth, setSearchDepth] = useState<'basic' | 'advanced'>('basic');
  const [topic, setTopic] = useState<'general' | 'news'>('general');
  const [includeAnswer, setIncludeAnswer] = useState(true);

  // Extract params
  const [urls, setUrls] = useState('https://example.com');
  const [extractDepth, setExtractDepth] = useState<'basic' | 'advanced'>('basic');

  const [loading, setLoading] = useState(false);
  const [searchResponse, setSearchResponse] = useState<{ answer?: string; results: SearchResult[] } | null>(null);
  const [extractResults, setExtractResults] = useState<ExtractResult[]>([]);

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setSearchResponse(null);
    try {
      const res = await fetch(`${apiUrl}/api/tools/web_search/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          max_results: maxResults,
          search_depth: searchDepth,
          topic,
          include_answer: includeAnswer,
        }),
      });
      
      const data = await res.json();
      onSetRawJson({ action: 'web_search/search', request: { query, maxResults, searchDepth, topic, includeAnswer }, response: data });
      if (res.ok) {
        setSearchResponse({
          answer: data.answer,
          results: data.results || [],
        });
      } else {
        alert(data.detail || '搜索失败');
      }
    } catch (err: any) {
      console.error(err);
      onSetRawJson({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleExtractSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const urlList = urls.split('\n').map(u => u.trim()).filter(Boolean);
    if (urlList.length === 0) return;
    setLoading(true);
    setExtractResults([]);
    try {
      const res = await fetch(`${apiUrl}/api/tools/web_search/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          urls: urlList,
          extract_depth: extractDepth,
        }),
      });
      const data = await res.json();
      onSetRawJson({ action: 'web_search/extract', urls: urlList, extract_depth: extractDepth, response: data });
      if (res.ok) {
        setExtractResults(data.results || []);
      } else {
        alert(data.detail || '提取失败');
      }
    } catch (err: any) {
      console.error(err);
      onSetRawJson({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Action Selector */}
      <div className="glass-card" style={{ display: 'flex', gap: '1rem', padding: '0.75rem 1.25rem' }}>
        <button
          className={`btn ${action === 'search' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setAction('search')}
          style={{ padding: '0.5rem 1.25rem' }}
        >
          <Search size={16} />
          网页检索 (Search)
        </button>
        <button
          className={`btn ${action === 'extract' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setAction('extract')}
          style={{ padding: '0.5rem 1.25rem' }}
        >
          <FileText size={16} />
          网页提取 (Extract)
        </button>
      </div>

      {action === 'search' ? (
        /* Search Form */
        <div className="glass-card">
          <h3 style={{ marginBottom: '1.25rem' }}>Tavily 网页检索</h3>
          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="search_query">搜索关键词 (Query)</label>
              <input
                id="search_query"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="请输入搜索关键词..."
                required
              />
            </div>

            <div className="form-group row" style={{ marginBottom: 0 }}>
              <div>
                <label htmlFor="max_results">返回数量 (Max Results)</label>
                <select
                  id="max_results"
                  value={maxResults}
                  onChange={(e) => setMaxResults(Number(e.target.value))}
                >
                  {[1, 3, 5, 10, 15, 20].map(k => (
                    <option key={k} value={k}>{k} 条结果</option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="search_depth">检索深度 (Search Depth)</label>
                <select
                  id="search_depth"
                  value={searchDepth}
                  onChange={(e) => setSearchDepth(e.target.value as any)}
                >
                  <option value="basic">Basic (基础搜索)</option>
                  <option value="advanced">Advanced (深度搜索)</option>
                </select>
              </div>

              <div>
                <label htmlFor="topic">分类主题 (Topic)</label>
                <select
                  id="topic"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value as any)}
                >
                  <option value="general">General (通用)</option>
                  <option value="news">News (新闻资讯)</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.25rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={includeAnswer}
                  onChange={(e) => setIncludeAnswer(e.target.checked)}
                  style={{ width: '16px', height: '16px', accentColor: 'var(--accent)' }}
                />
                生成大模型摘要答案 (Generate AI Answer)
              </label>

              <button type="submit" className="btn btn-primary" disabled={loading} style={{ minWidth: '150px' }}>
                <Globe size={16} className={loading ? 'animate-spin' : ''} />
                {loading ? '检索中...' : '开始检索'}
              </button>
            </div>
          </form>
        </div>
      ) : (
        /* Extract Form */
        <div className="glass-card">
          <h3 style={{ marginBottom: '1.25rem' }}>网页正文提取</h3>
          <form onSubmit={handleExtractSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="urls_input">待提取的 URL 列表 (每行一个 URL)</label>
              <textarea
                id="urls_input"
                value={urls}
                onChange={(e) => setUrls(e.target.value)}
                placeholder="https://example.com&#10;https://another.com"
                rows={4}
                required
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', width: '250px' }}>
                <label htmlFor="extract_depth" style={{ whiteSpace: 'nowrap' }}>提取深度: </label>
                <select
                  id="extract_depth"
                  value={extractDepth}
                  onChange={(e) => setExtractDepth(e.target.value as any)}
                  style={{ padding: '0.5rem' }}
                >
                  <option value="basic">Basic (常规正文)</option>
                  <option value="advanced">Advanced (含媒体/详情)</option>
                </select>
              </div>

              <button type="submit" className="btn btn-primary" disabled={loading} style={{ minWidth: '150px' }}>
                <FileText size={16} className={loading ? 'animate-spin' : ''} />
                {loading ? '正在提取...' : '提取正文'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Results Display */}
      {action === 'search' && searchResponse && (
        <div className="glass-card">
          <h3 style={{ marginBottom: '1rem' }}>检索结果</h3>

          {searchResponse.answer && (
            <div 
              className="glass-card" 
              style={{ 
                backgroundColor: 'var(--accent-glow)', 
                borderColor: 'rgba(14, 165, 233, 0.3)', 
                marginBottom: '1.5rem',
                borderLeftWidth: '4px',
                borderLeftColor: 'var(--accent)'
              }}
            >
              <h4 style={{ color: 'var(--accent)', fontWeight: 600, fontSize: '0.95rem', marginBottom: '0.5rem' }}>
                AI 生成答案 (Answer)
              </h4>
              <p style={{ color: 'var(--text-primary)', fontSize: '0.925rem', lineHeight: 1.6 }}>
                {searchResponse.answer}
              </p>
            </div>
          )}

          <div className="result-list">
            {searchResponse.results.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>未搜索到内容</div>
            ) : (
              searchResponse.results.map((res, index) => (
                <div key={index} className="result-item">
                  <div className="result-title-row">
                    <a 
                      href={res.url} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '0.25rem', 
                        color: 'var(--accent)', 
                        textDecoration: 'none',
                        fontWeight: 600,
                        fontSize: '1rem'
                      }}
                    >
                      {res.title || '无标题'}
                      <LinkIcon size={14} />
                    </a>
                    {res.score !== undefined && (
                      <span className="badge" style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-secondary)' }}>
                        评分: {res.score.toFixed(3)}
                      </span>
                    )}
                  </div>
                  <p className="result-content" style={{ marginTop: '0.5rem' }}>
                    {res.content}
                  </p>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    链接: {res.url}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {action === 'extract' && extractResults.length > 0 && (
        <div className="glass-card">
          <h3 style={{ marginBottom: '1rem' }}>提取的内容 ({extractResults.length})</h3>
          <div className="result-list">
            {extractResults.map((res, idx) => (
              <div key={idx} className="result-item">
                <h4 style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '1.05rem', marginBottom: '0.25rem' }}>
                  {res.title || '提取结果'}
                </h4>
                <div style={{ fontSize: '0.8rem', color: 'var(--accent)', marginBottom: '0.75rem', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  URL: {res.url}
                </div>
                <div 
                  style={{ 
                    maxHeight: '200px', 
                    overflowY: 'auto', 
                    backgroundColor: 'rgba(0,0,0,0.2)', 
                    padding: '0.75rem', 
                    borderRadius: '6px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.825rem',
                    color: 'var(--text-secondary)'
                  }}
                >
                  {res.raw_content || '(无内容)'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
