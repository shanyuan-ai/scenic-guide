// tool-tester/src/components/FeedbackTest.tsx
import React, { useState, useEffect } from 'react';
import { MessageSquare, Plus, MapPin, Phone, RefreshCw, X, Image as ImageIcon, Upload, Shuffle, Trash2, Tag, AlertTriangle } from 'lucide-react';

interface FeedbackTestProps {
  apiUrl: string;
  onSetRawJson: (json: any) => void;
}

interface FeedbackItem {
  id: number;
  type: string;
  priority: string;
  scenic_spot?: string;
  description: string;
  keywords: string; // JSON 数组字符串
  image_paths: string; // JSON 数组字符串
  status: string;
  evaluated: boolean;
  group_id?: string | null;
  duplicate_count: number;
  group_summary?: string | null;
  merged_into_id?: number | null;
  contact_info?: string;
  created_at?: string;
  updated_at?: string;
}

interface RecycleBinItem {
  id: number;
  original_id: number;
  type: string;
  priority: string;
  scenic_spot?: string;
  description: string;
  keywords: string; // JSON 数组字符串
  merged_into_id: number;
  merge_reason?: string | null;
  contact_info?: string;
  created_at?: string;
  archived_at?: string;
}

interface IntegrateResult {
  evaluated_count: number;
  merged_count: number;
  new_groups: number;
  priority_upgrades: number;
  method: string;
  error?: string | null;
}

export const FeedbackTest: React.FC<FeedbackTestProps> = ({ apiUrl, onSetRawJson }) => {
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([]);
  const [recycleItems, setRecycleItems] = useState<RecycleBinItem[]>([]);
  const [loading, setLoading] = useState(false);
  
  // List toggle: 'active' (normal feedbacks) vs 'recycle' (recycle bin)
  const [listType, setListType] = useState<'active' | 'recycle'>('active');

  // Filters (for active feedbacks only)
  const [filterType, setFilterType] = useState('');
  const [filterPriority, setFilterPriority] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterSpot, setFilterSpot] = useState('');

  // Selected feedback for detail / image upload
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackItem | null>(null);
  const [selectedRecycleItem, setSelectedRecycleItem] = useState<RecycleBinItem | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);

  // New feedback form
  const [showSubmitForm, setShowSubmitForm] = useState(false);
  const [formData, setFormData] = useState({
    type: 'suggestion',
    priority: 'P3',
    scenic_spot: '大雄宝殿',
    description: '建议在大雄宝殿旁边多增加几个直饮水点，夏天天气热，直饮水排队时间较长。',
    contact_info: '手机号：13812345678',
  });
  const [keywordsInput, setKeywordsInput] = useState('直饮水少, 排队时间长');

  // Integration action states
  const [integrating, setIntegrating] = useState(false);
  const [integrateResult, setIntegrateResult] = useState<IntegrateResult | null>(null);

  const fetchActiveFeedbacks = async () => {
    setLoading(true);
    try {
      let query = `?skip=0&limit=50`;
      if (filterType) query += `&type=${filterType}`;
      if (filterPriority) query += `&priority=${filterPriority}`;
      if (filterStatus) query += `&status=${filterStatus}`;
      if (filterSpot) query += `&scenic_spot=${encodeURIComponent(filterSpot)}`;

      const res = await fetch(`${apiUrl}/api/tools/feedback${query}`);
      const data = await res.json();
      if (Array.isArray(data)) {
        setFeedbacks(data);
      } else {
        setFeedbacks([]);
      }
      onSetRawJson({ action: 'feedback/list', filters: { filterType, filterPriority, filterStatus, filterSpot }, response: data });
    } catch (err: any) {
      console.error(err);
      onSetRawJson({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const fetchRecycleBin = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/tools/feedback/recycle-bin`);
      const data = await res.json();
      if (Array.isArray(data)) {
        setRecycleItems(data);
      } else {
        setRecycleItems([]);
      }
      onSetRawJson({ action: 'feedback/recycle_bin_list', response: data });
    } catch (err: any) {
      console.error(err);
      onSetRawJson({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (listType === 'active') {
      fetchActiveFeedbacks();
    } else {
      fetchRecycleBin();
    }
  }, [apiUrl, listType, filterType, filterPriority, filterStatus, filterSpot]);

  const handleSubmitFeedback = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const keywords = keywordsInput.split(',').map(k => k.trim()).filter(Boolean);
      const payload = {
        ...formData,
        keywords: keywords.length > 0 ? keywords : undefined,
      };

      const res = await fetch(`${apiUrl}/api/tools/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      onSetRawJson({ action: 'feedback/create', request: payload, response: data });
      if (res.ok) {
        setShowSubmitForm(false);
        setKeywordsInput('');
        fetchActiveFeedbacks();
      } else {
        alert(data.detail || '提交反馈失败');
      }
    } catch (err: any) {
      console.error(err);
      onSetRawJson({ error: err.message });
    }
  };

  const handleUpdateStatus = async (itemId: number, newStatus: string) => {
    try {
      const res = await fetch(`${apiUrl}/api/tools/feedback/${itemId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      const data = await res.json();
      onSetRawJson({ action: 'feedback/update_status', item_id: itemId, status: newStatus, response: data });
      if (res.ok) {
        fetchActiveFeedbacks();
        if (selectedFeedback && selectedFeedback.id === itemId) {
          setSelectedFeedback(data);
        }
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleUpdatePriority = async (itemId: number, newPriority: string) => {
    try {
      const res = await fetch(`${apiUrl}/api/tools/feedback/${itemId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ priority: newPriority }),
      });
      const data = await res.json();
      onSetRawJson({ action: 'feedback/update_priority', item_id: itemId, priority: newPriority, response: data });
      if (res.ok) {
        fetchActiveFeedbacks();
        if (selectedFeedback && selectedFeedback.id === itemId) {
          setSelectedFeedback(data);
        }
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!selectedFeedback || !e.target.files || e.target.files.length === 0) return;
    setUploadLoading(true);
    const formDataObj = new FormData();
    for (let i = 0; i < e.target.files.length; i++) {
      formDataObj.append('files', e.target.files[i]);
    }

    try {
      const res = await fetch(`${apiUrl}/api/tools/feedback/${selectedFeedback.id}/images`, {
        method: 'POST',
        body: formDataObj,
      });
      const data = await res.json();
      onSetRawJson({ action: 'feedback/upload_images', item_id: selectedFeedback.id, response: data });
      if (res.ok) {
        const updatedRes = await fetch(`${apiUrl}/api/tools/feedback/${selectedFeedback.id}`);
        const updatedData = await updatedRes.json();
        setSelectedFeedback(updatedData);
        fetchActiveFeedbacks();
      } else {
        alert(data.detail || '图片上传失败');
      }
    } catch (err: any) {
      console.error(err);
      alert('上传图片网络出错');
    } finally {
      setUploadLoading(false);
    }
  };

  const handleDeleteFeedback = async (itemId: number) => {
    if (!window.confirm('确定要删除该条反馈吗？')) return;
    try {
      const res = await fetch(`${apiUrl}/api/tools/feedback/${itemId}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      onSetRawJson({ action: 'feedback/delete', item_id: itemId, response: data });
      if (res.ok) {
        setSelectedFeedback(null);
        fetchActiveFeedbacks();
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleIntegrate = async () => {
    setIntegrating(true);
    setIntegrateResult(null);
    try {
      const res = await fetch(`${apiUrl}/api/tools/feedback/integrate`, {
        method: 'POST',
      });
      const data = await res.json();
      onSetRawJson({ action: 'feedback/integrate', response: data });
      if (res.ok) {
        setIntegrateResult(data);
        fetchActiveFeedbacks();
        if (listType === 'recycle') {
          fetchRecycleBin();
        }
      } else {
        alert(data.detail || '整合失败');
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setIntegrating(false);
    }
  };

  const getFeedbackTypeBadge = (type: string) => {
    const types: Record<string, { label: string; color: string }> = {
      complaint: { label: '投诉', color: 'var(--error)' },
      suggestion: { label: '建议', color: 'var(--accent)' },
      praise: { label: '表扬', color: 'var(--success)' },
      help: { label: '求助', color: 'var(--warning)' },
    };
    const t = types[type] || { label: type, color: 'var(--text-muted)' };
    return (
      <span className="badge" style={{ backgroundColor: `${t.color}20`, color: t.color }}>
        {t.label}
      </span>
    );
  };

  const getPriorityBadge = (priority: string) => {
    const priorities: Record<string, { label: string; class: string }> = {
      P1: { label: 'P1 紧急', class: 'badge-critical' },
      P2: { label: 'P2 高', class: 'badge-high' },
      P3: { label: 'P3 中', class: 'badge-medium' },
      P4: { label: 'P4 低', class: 'badge-low' },
    };
    const p = priorities[priority] || { label: priority, class: 'badge-status' };
    return <span className={`badge ${p.class}`}>{p.label}</span>;
  };



  const parseJsonArray = (jsonStr?: string): string[] => {
    try {
      return JSON.parse(jsonStr || '[]');
    } catch (e) {
      return [];
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top Filter and Actions */}
      <div className="glass-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <MessageSquare size={20} className="text-accent" style={{ color: 'var(--accent)' }} />
            <h3 style={{ margin: 0 }}>智能反馈系统</h3>
          </div>

          {/* Sub-tab active vs recycle bin */}
          <div style={{ display: 'flex', border: '1px solid var(--border-color)', borderRadius: '6px', overflow: 'hidden' }}>
            <button
              onClick={() => { setListType('active'); setSelectedFeedback(null); setSelectedRecycleItem(null); }}
              className="btn"
              style={{
                padding: '0.4rem 0.8rem',
                fontSize: '0.85rem',
                backgroundColor: listType === 'active' ? 'var(--accent-glow)' : 'transparent',
                color: listType === 'active' ? 'var(--accent)' : 'var(--text-secondary)',
                borderRadius: 0,
                border: 'none',
              }}
            >
              活动列表 ({feedbacks.length})
            </button>
            <button
              onClick={() => { setListType('recycle'); setSelectedFeedback(null); setSelectedRecycleItem(null); }}
              className="btn"
              style={{
                padding: '0.4rem 0.8rem',
                fontSize: '0.85rem',
                backgroundColor: listType === 'recycle' ? 'var(--accent-glow)' : 'transparent',
                color: listType === 'recycle' ? 'var(--accent)' : 'var(--text-secondary)',
                borderRadius: 0,
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
              }}
            >
              <Trash2 size={12} />
              回收站 ({recycleItems.length})
            </button>
          </div>

          {/* Filters (Active only) */}
          {listType === 'active' && (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <select value={filterType} onChange={(e) => setFilterType(e.target.value)} style={{ padding: '0.4rem', fontSize: '0.85rem', width: '110px' }}>
                <option value="">所有类型</option>
                <option value="complaint">投诉 (complaint)</option>
                <option value="suggestion">建议 (suggestion)</option>
                <option value="praise">表扬 (praise)</option>
                <option value="help">求助 (help)</option>
              </select>

              <select value={filterPriority} onChange={(e) => setFilterPriority(e.target.value)} style={{ padding: '0.4rem', fontSize: '0.85rem', width: '110px' }}>
                <option value="">所有优先级</option>
                <option value="P1">P1 紧急</option>
                <option value="P2">P2 高</option>
                <option value="P3">P3 中</option>
                <option value="P4">P4 低</option>
              </select>

              <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} style={{ padding: '0.4rem', fontSize: '0.85rem', width: '110px' }}>
                <option value="">所有状态</option>
                <option value="submitted">已提交</option>
                <option value="confirmed">已确认</option>
                <option value="processing">处理中</option>
                <option value="resolved">已解决</option>
                <option value="closed">已关闭</option>
              </select>

              <input
                type="text"
                value={filterSpot}
                onChange={(e) => setFilterSpot(e.target.value)}
                placeholder="搜索景点"
                style={{ padding: '0.4rem', fontSize: '0.85rem', width: '100px' }}
              />
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            onClick={handleIntegrate} 
            className="btn btn-secondary" 
            disabled={integrating}
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem', borderColor: 'rgba(14, 165, 233, 0.4)', color: 'var(--accent)' }}
          >
            <Shuffle size={14} className={integrating ? 'animate-spin' : ''} />
            {integrating ? '正在智能重组...' : '智能整合报单'}
          </button>
          <button 
            onClick={listType === 'active' ? fetchActiveFeedbacks : fetchRecycleBin} 
            className="btn btn-secondary" 
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }} 
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            刷新
          </button>
          <button onClick={() => setShowSubmitForm(true)} className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
            <Plus size={14} />
            提交反馈
          </button>
        </div>
      </div>

      {/* Integration result banner */}
      {integrateResult && (
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', borderColor: 'var(--success)', backgroundColor: 'var(--success-glow)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h4 style={{ color: 'var(--success)', margin: 0, fontSize: '0.95rem', fontWeight: 600 }}>智能整合完成 (Method: {integrateResult.method})</h4>
            <button onClick={() => setIntegrateResult(null)} style={{ background: 'transparent', border: 'none', color: 'var(--success)', cursor: 'pointer' }}><X size={16} /></button>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', margin: 0 }}>
            本次评估报单数: <strong>{integrateResult.evaluated_count}</strong> | 
            合并报单数: <strong>{integrateResult.merged_count}</strong> | 
            新成分组: <strong>{integrateResult.new_groups}</strong> | 
            优先级提升: <strong>{integrateResult.priority_upgrades}</strong>
          </p>
          {integrateResult.error && (
            <div style={{ color: 'var(--warning)', fontSize: '0.8rem', marginTop: '0.25rem' }}>降级说明: {integrateResult.error}</div>
          )}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: selectedFeedback || selectedRecycleItem || showSubmitForm ? '1fr 1.2fr' : '1fr', gap: '1.5rem' }}>
        {/* Main List */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h3 style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
            {listType === 'active' ? '活跃反馈列表' : '回收站归档列表'}
          </h3>
          
          {listType === 'active' ? (
            /* Active Feedback List */
            (!Array.isArray(feedbacks) || feedbacks.length === 0) ? (
              <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>没有找到符合条件的游客反馈。</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '650px', overflowY: 'auto' }}>
                {feedbacks.map((item) => (
                  <div 
                    key={item.id} 
                    className={`result-item ${selectedFeedback?.id === item.id ? 'active' : ''}`}
                    onClick={() => { setSelectedFeedback(item); setSelectedRecycleItem(null); }}
                    style={{ 
                      cursor: 'pointer',
                      borderLeft: selectedFeedback?.id === item.id ? '4px solid var(--accent)' : '1px solid var(--border-color)',
                      backgroundColor: selectedFeedback?.id === item.id ? 'var(--accent-glow)' : ''
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>#{item.id}</span>
                      <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                        {item.duplicate_count > 1 && (
                          <span className="badge badge-critical" style={{ fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '0.2rem', padding: '0.2rem 0.4rem' }}>
                            <AlertTriangle size={10} />
                            {item.duplicate_count}次上报
                          </span>
                        )}
                        {getFeedbackTypeBadge(item.type)}
                        {getPriorityBadge(item.priority)}
                      </div>
                    </div>
                    {item.scenic_spot && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
                        <MapPin size={12} />
                        <span>{item.scenic_spot}</span>
                      </div>
                    )}
                    <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                       {item.description}
                    </p>
                    
                    {/* Render tag list */}
                    {parseJsonArray(item.keywords).length > 0 && (
                      <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                        {parseJsonArray(item.keywords).map((kw, idx) => (
                          <span key={idx} className="badge badge-status" style={{ fontSize: '0.65rem', padding: '0.1rem 0.3rem', display: 'flex', alignItems: 'center', gap: '0.15rem' }}>
                            <Tag size={8} /> {kw}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )
          ) : (
            /* Recycle Bin List */
            (!Array.isArray(recycleItems) || recycleItems.length === 0) ? (
              <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>回收站为空。</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '650px', overflowY: 'auto' }}>
                {recycleItems.map((item) => (
                  <div 
                    key={item.id} 
                    className={`result-item ${selectedRecycleItem?.id === item.id ? 'active' : ''}`}
                    onClick={() => { setSelectedRecycleItem(item); setSelectedFeedback(null); }}
                    style={{ 
                      cursor: 'pointer',
                      borderLeft: selectedRecycleItem?.id === item.id ? '4px solid var(--critical)' : '1px solid var(--border-color)',
                      backgroundColor: selectedRecycleItem?.id === item.id ? 'rgba(236, 72, 153, 0.05)' : ''
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>原 #{item.original_id} (已合并)</span>
                      <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                        {getFeedbackTypeBadge(item.type)}
                        {getPriorityBadge(item.priority)}
                      </div>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--critical)', marginBottom: '0.4rem', fontWeight: 500 }}>
                      合并至原始报单: #{item.merged_into_id}
                    </div>
                    <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', textDecoration: 'line-through' }}>
                      {item.description}
                    </p>
                    {item.merge_reason && (
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem', fontStyle: 'italic', backgroundColor: 'rgba(0,0,0,0.1)', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>
                        合并原因: {item.merge_reason}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )
          )}
        </div>

        {/* Submit Form */}
        {showSubmitForm && (
          <div className="glass-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', marginBottom: '1.25rem' }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Plus size={18} />
                提交新游客反馈
              </h3>
              <button onClick={() => setShowSubmitForm(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmitFeedback} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="form-group row" style={{ marginBottom: 0 }}>
                <div>
                  <label htmlFor="feedback_type">反馈类型</label>
                  <select id="feedback_type" value={formData.type} onChange={(e) => setFormData({ ...formData, type: e.target.value })}>
                    <option value="complaint">投诉 (complaint)</option>
                    <option value="suggestion">建议 (suggestion)</option>
                    <option value="praise">表扬 (praise)</option>
                    <option value="help">求助 (help)</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="feedback_priority">优先级</label>
                  <select id="feedback_priority" value={formData.priority} onChange={(e) => setFormData({ ...formData, priority: e.target.value })}>
                    <option value="P1">P1 紧急 (P1)</option>
                    <option value="P2">P2 高 (P2)</option>
                    <option value="P3">P3 中 (P3)</option>
                    <option value="P4">P4 低 (P4)</option>
                  </select>
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="scenic_spot">关联景点名称 (选填)</label>
                <input id="scenic_spot" type="text" value={formData.scenic_spot} onChange={(e) => setFormData({ ...formData, scenic_spot: e.target.value })} />
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="desc">反馈文字描述</label>
                <textarea id="desc" value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} required />
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="keywords">关键词标签 (以逗号分隔，选填)</label>
                <input 
                  id="keywords" 
                  type="text" 
                  value={keywordsInput} 
                  onChange={(e) => setKeywordsInput(e.target.value)} 
                  placeholder="例如: 垃圾桶少, 卫生差, 排队时间长" 
                />
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="contact">联系方式 (选填)</label>
                <input id="contact" type="text" value={formData.contact_info} onChange={(e) => setFormData({ ...formData, contact_info: e.target.value })} placeholder="如：手机号/邮箱" />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>立即提交</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowSubmitForm(false)}>取消</button>
              </div>
            </form>
          </div>
        )}

        {/* Selected Feedback Detail Panel */}
        {selectedFeedback && !showSubmitForm && (
          <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span>反馈 #{selectedFeedback.id} 详情</span>
              </h3>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button onClick={() => handleDeleteFeedback(selectedFeedback.id)} className="btn btn-danger" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                  删除
                </button>
                <button onClick={() => setSelectedFeedback(null)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                  <X size={20} />
                </button>
              </div>
            </div>

            {/* Core Info */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', backgroundColor: 'rgba(255, 255, 255, 0.01)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>反馈类型</span>
                {getFeedbackTypeBadge(selectedFeedback.type)}
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>严重优先级</span>
                <select 
                  value={selectedFeedback.priority} 
                  onChange={(e) => handleUpdatePriority(selectedFeedback.id, e.target.value)}
                  style={{ width: '130px', padding: '0.25rem', fontSize: '0.85rem' }}
                >
                  <option value="P1">P1 紧急 (P1)</option>
                  <option value="P2">P2 高 (P2)</option>
                  <option value="P3">P3 中 (P3)</option>
                  <option value="P4">P4 低 (P4)</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>处理状态</span>
                <select 
                  value={selectedFeedback.status} 
                  onChange={(e) => handleUpdateStatus(selectedFeedback.id, e.target.value)}
                  style={{ width: '130px', padding: '0.25rem', fontSize: '0.85rem' }}
                >
                  <option value="submitted">已提交 (submitted)</option>
                  <option value="confirmed">已确认 (confirmed)</option>
                  <option value="processing">处理中 (processing)</option>
                  <option value="resolved">已解决 (resolved)</option>
                  <option value="closed">已关闭 (closed)</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>AI 整合评估</span>
                <span className={`badge ${selectedFeedback.evaluated ? 'badge-low' : 'badge-medium'}`}>
                  {selectedFeedback.evaluated ? '已评估 (Evaluated)' : '待评估 (Pending)'}
                </span>
              </div>

              {selectedFeedback.scenic_spot && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>关联景点</span>
                  <span style={{ fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <MapPin size={12} /> {selectedFeedback.scenic_spot}
                  </span>
                </div>
              )}
              {selectedFeedback.contact_info && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>联系人方式</span>
                  <span style={{ fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <Phone size={12} /> {selectedFeedback.contact_info}
                  </span>
                </div>
              )}
              {selectedFeedback.created_at && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>提交时间</span>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {new Date(selectedFeedback.created_at).toLocaleString()}
                  </span>
                </div>
              )}

              {/* Keywords list */}
              <div style={{ borderTop: '1px solid var(--border-color)', marginTop: '0.5rem', paddingTop: '0.5rem' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.4rem' }}>关键词提取 (Keywords)</span>
                {parseJsonArray(selectedFeedback.keywords).length === 0 ? (
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>无提取关键词</span>
                ) : (
                  <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                    {parseJsonArray(selectedFeedback.keywords).map((kw, idx) => (
                      <span key={idx} className="badge badge-status" style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <Tag size={10} /> {kw}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Repeat heat status */}
              {selectedFeedback.duplicate_count > 1 && (
                <div style={{ borderTop: '1px solid var(--border-color)', marginTop: '0.5rem', paddingTop: '0.5rem' }}>
                  <div className="badge badge-critical" style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.3rem', width: 'fit-content' }}>
                    <AlertTriangle size={12} />
                    <strong>重复上报热度：当前已上报 {selectedFeedback.duplicate_count} 次</strong>
                  </div>
                  {selectedFeedback.group_id && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                      分组标识 (group_id): {selectedFeedback.group_id}
                    </div>
                  )}
                </div>
              )}

              {/* Description & AI summary box */}
              <div style={{ marginTop: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>描述内容</span>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>{selectedFeedback.description}</p>
              </div>

              {selectedFeedback.group_summary && (
                <div style={{ marginTop: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem', backgroundColor: 'var(--accent-glow)', padding: '0.75rem', borderRadius: '6px', borderLeft: '4px solid var(--accent)' }}>
                  <span style={{ fontSize: '0.85rem', color: 'var(--accent)', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>AI 重组摘要 (Group Summary)</span>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-primary)', margin: 0 }}>{selectedFeedback.group_summary}</p>
                </div>
              )}
            </div>

            {/* Images Gallery */}
            <div>
              <h4 style={{ fontSize: '0.95rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <ImageIcon size={16} />
                照片附件 ({parseJsonArray(selectedFeedback.image_paths).length})
              </h4>
              {parseJsonArray(selectedFeedback.image_paths).length === 0 ? (
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', border: '1px dashed var(--border-color)', padding: '1rem', borderRadius: '6px', textAlign: 'center' }}>
                  未上传图片
                </div>
              ) : (
                <div className="uploaded-images" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {parseJsonArray(selectedFeedback.image_paths).map((path, idx) => (
                    <img 
                      key={idx} 
                      src={`${apiUrl}/uploads/${path}`} 
                      alt="feedback attachment" 
                      className="uploaded-img"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=150';
                      }}
                      style={{ width: '80px', height: '80px', objectFit: 'cover', borderRadius: '6px', border: '1px solid var(--border-color)' }}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Upload form */}
            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
              <label htmlFor="file-upload" className="upload-zone" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
                <Upload size={24} style={{ color: 'var(--accent)' }} />
                <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>点击上传图片</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>支持多张图片上传</span>
                <input 
                  id="file-upload" 
                  type="file" 
                  multiple 
                  accept="image/*" 
                  onChange={handleImageUpload} 
                  style={{ display: 'none' }} 
                  disabled={uploadLoading}
                />
              </label>
              {uploadLoading && (
                <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', alignItems: 'center', fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                  <RefreshCw size={14} className="animate-spin" />
                  正在上传图片中...
                </div>
              )}
            </div>
          </div>
        )}

        {/* Selected Recycle Bin Item Detail Panel */}
        {selectedRecycleItem && !showSubmitForm && (
          <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span>归档报单 #{selectedRecycleItem.original_id}</span>
              </h3>
              <button onClick={() => setSelectedRecycleItem(null)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>

            {/* Core Info */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', backgroundColor: 'rgba(255, 255, 255, 0.01)', padding: '0.75rem', borderRadius: '6px', border: '1px dashed var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>原报单类型</span>
                {getFeedbackTypeBadge(selectedRecycleItem.type)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>原优先级</span>
                {getPriorityBadge(selectedRecycleItem.priority)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>归档状态</span>
                <span className="badge badge-critical">已合并 (Merged)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontWeight: 600 }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>合并至主报单</span>
                <span style={{ color: 'var(--accent)', cursor: 'pointer', textDecoration: 'underline' }} onClick={async () => {
                  // Find and select the parent feedback item
                  const res = await fetch(`${apiUrl}/api/tools/feedback/${selectedRecycleItem.merged_into_id}`);
                  if (res.ok) {
                    const parentData = await res.json();
                    setListType('active');
                    setSelectedFeedback(parentData);
                    setSelectedRecycleItem(null);
                  } else {
                    alert('主报单已被删除或不存在');
                  }
                }}>
                  查看主报单 #{selectedRecycleItem.merged_into_id}
                </span>
              </div>
              {selectedRecycleItem.scenic_spot && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>关联景点</span>
                  <span style={{ fontSize: '0.9rem' }}>{selectedRecycleItem.scenic_spot}</span>
                </div>
              )}
              {selectedRecycleItem.contact_info && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>联系人方式</span>
                  <span style={{ fontSize: '0.9rem' }}>{selectedRecycleItem.contact_info}</span>
                </div>
              )}
              {selectedRecycleItem.created_at && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>提交时间</span>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {new Date(selectedRecycleItem.created_at).toLocaleString()}
                  </span>
                </div>
              )}
              {selectedRecycleItem.archived_at && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>归档合并时间</span>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {new Date(selectedRecycleItem.archived_at).toLocaleString()}
                  </span>
                </div>
              )}

              {/* Keywords */}
              <div style={{ borderTop: '1px solid var(--border-color)', marginTop: '0.5rem', paddingTop: '0.5rem' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.4rem' }}>关键词</span>
                {parseJsonArray(selectedRecycleItem.keywords).length === 0 ? (
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>无关键词</span>
                ) : (
                  <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                    {parseJsonArray(selectedRecycleItem.keywords).map((kw, idx) => (
                      <span key={idx} className="badge badge-status" style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}><Tag size={10} style={{ display: 'inline', marginRight: '0.15rem' }} /> {kw}</span>
                    ))}
                  </div>
                )}
              </div>

              {/* Merge reason */}
              {selectedRecycleItem.merge_reason && (
                <div style={{ borderTop: '1px solid var(--border-color)', marginTop: '0.5rem', paddingTop: '0.5rem', backgroundColor: 'var(--error-glow)', padding: '0.75rem', borderRadius: '6px', borderLeft: '4px solid var(--error)' }}>
                  <span style={{ fontSize: '0.85rem', color: 'var(--error)', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>合并归档原因 (Merge Reason)</span>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-primary)', margin: 0 }}>{selectedRecycleItem.merge_reason}</p>
                </div>
              )}

              {/* Description */}
              <div style={{ marginTop: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>描述内容</span>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', textDecoration: 'line-through' }}>{selectedRecycleItem.description}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
