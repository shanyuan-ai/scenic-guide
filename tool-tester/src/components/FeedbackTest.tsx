// tool-tester/src/components/FeedbackTest.tsx
import React, { useState, useEffect } from 'react';
import { MessageSquare, Plus, MapPin, Phone, RefreshCw, X, Image as ImageIcon, Upload } from 'lucide-react';

interface FeedbackTestProps {
  apiUrl: string;
  onSetRawJson: (json: any) => void;
}

interface FeedbackItem {
  id: number;
  type: string;
  severity: string;
  scenic_spot?: string;
  description: string;
  image_paths: string; // JSON array string
  status: string;
  contact_info?: string;
  created_at?: string;
  updated_at?: string;
}

export const FeedbackTest: React.FC<FeedbackTestProps> = ({ apiUrl, onSetRawJson }) => {
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Filters
  const [filterType, setFilterType] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterSpot, setFilterSpot] = useState('');

  // Selected feedback for detail / image upload
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackItem | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);

  // New feedback form
  const [showSubmitForm, setShowSubmitForm] = useState(false);
  const [formData, setFormData] = useState({
    type: 'suggestion',
    severity: 'medium',
    scenic_spot: '大雄宝殿',
    description: '建议在大雄宝殿旁边多增加几个直饮水点，夏天天气热，直饮水排队时间较长。',
    contact_info: '手机号：13812345678',
  });

  const fetchFeedbacks = async () => {
    setLoading(true);
    try {
      let query = `?skip=0&limit=50`;
      if (filterType) query += `&type=${filterType}`;
      if (filterSeverity) query += `&severity=${filterSeverity}`;
      if (filterStatus) query += `&status=${filterStatus}`;
      if (filterSpot) query += `&scenic_spot=${encodeURIComponent(filterSpot)}`;

      const res = await fetch(`${apiUrl}/api/tools/feedback${query}`);
      const data = await res.json();
      setFeedbacks(data);
      onSetRawJson({ action: 'feedback/list', filters: { filterType, filterSeverity, filterStatus, filterSpot }, response: data });
    } catch (err: any) {
      console.error(err);
      onSetRawJson({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeedbacks();
  }, [apiUrl, filterType, filterSeverity, filterStatus, filterSpot]);

  const handleSubmitFeedback = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${apiUrl}/api/tools/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      onSetRawJson({ action: 'feedback/create', request: formData, response: data });
      if (res.ok) {
        setShowSubmitForm(false);
        fetchFeedbacks();
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
        fetchFeedbacks();
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
        body: formDataObj, // Fetch handles multipart boundaries automatically
      });
      const data = await res.json();
      onSetRawJson({ action: 'feedback/upload_images', item_id: selectedFeedback.id, response: data });
      if (res.ok) {
        // Refresh selected feedback item
        const updatedRes = await fetch(`${apiUrl}/api/tools/feedback/${selectedFeedback.id}`);
        const updatedData = await updatedRes.json();
        setSelectedFeedback(updatedData);
        fetchFeedbacks();
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
        fetchFeedbacks();
      }
    } catch (err: any) {
      console.error(err);
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

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      submitted: '已提交',
      confirmed: '已确认',
      processing: '处理中',
      resolved: '已解决',
      closed: '已关闭',
    };
    return labels[status] || status;
  };

  const parseImages = (jsonStr: string): string[] => {
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
            <h3 style={{ margin: 0 }}>游客反馈管理</h3>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <select value={filterType} onChange={(e) => setFilterType(e.target.value)} style={{ padding: '0.4rem', fontSize: '0.85rem', width: '110px' }}>
              <option value="">所有类型</option>
              <option value="complaint">投诉 (complaint)</option>
              <option value="suggestion">建议 (suggestion)</option>
              <option value="praise">表扬 (praise)</option>
              <option value="help">求助 (help)</option>
            </select>

            <select value={filterSeverity} onChange={(e) => setFilterSeverity(e.target.value)} style={{ padding: '0.4rem', fontSize: '0.85rem', width: '110px' }}>
              <option value="">所有严重度</option>
              <option value="low">低 (low)</option>
              <option value="medium">中 (medium)</option>
              <option value="high">高 (high)</option>
              <option value="critical">紧急 (critical)</option>
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
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button onClick={fetchFeedbacks} className="btn btn-secondary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            刷新
          </button>
          <button onClick={() => setShowSubmitForm(true)} className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
            <Plus size={14} />
            提交反馈
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selectedFeedback || showSubmitForm ? '1fr 1.2fr' : '1fr', gap: '1.5rem' }}>
        {/* Feedbacks list */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h3 style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>反馈列表</h3>
          {feedbacks.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>
              没有找到符合条件的游客反馈。
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '650px', overflowY: 'auto' }}>
              {feedbacks.map((item) => (
                <div 
                  key={item.id} 
                  className={`result-item ${selectedFeedback?.id === item.id ? 'active' : ''}`}
                  onClick={() => setSelectedFeedback(item)}
                  style={{ 
                    cursor: 'pointer',
                    borderLeft: selectedFeedback?.id === item.id ? '4px solid var(--accent)' : '1px solid var(--border-color)',
                    backgroundColor: selectedFeedback?.id === item.id ? 'var(--accent-glow)' : ''
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      #{item.id}
                    </span>
                    <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                      {getFeedbackTypeBadge(item.type)}
                      <span className="badge badge-status">{getStatusLabel(item.status)}</span>
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
                  {parseImages(item.image_paths).length > 0 && (
                    <div style={{ display: 'flex', gap: '0.25rem', marginTop: '0.4rem', alignItems: 'center', fontSize: '0.8rem', color: 'var(--accent)' }}>
                      <ImageIcon size={12} />
                      <span>附带 {parseImages(item.image_paths).length} 张图片</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
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
                  <label htmlFor="feedback_severity">严重度</label>
                  <select id="feedback_severity" value={formData.severity} onChange={(e) => setFormData({ ...formData, severity: e.target.value })}>
                    <option value="low">低 (low)</option>
                    <option value="medium">中 (medium)</option>
                    <option value="high">高 (high)</option>
                    <option value="critical">紧急 (critical)</option>
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
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>反馈类型</span>
                {getFeedbackTypeBadge(selectedFeedback.type)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>严重度</span>
                <span className={`badge badge-${selectedFeedback.severity}`}>{selectedFeedback.severity}</span>
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
              <div style={{ marginTop: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>描述内容</span>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>{selectedFeedback.description}</p>
              </div>
            </div>

            {/* Images Gallery */}
            <div>
              <h4 style={{ fontSize: '0.95rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <ImageIcon size={16} />
                照片附件 ({parseImages(selectedFeedback.image_paths).length})
              </h4>
              {parseImages(selectedFeedback.image_paths).length === 0 ? (
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', border: '1px dashed var(--border-color)', padding: '1rem', borderRadius: '6px', textAlign: 'center' }}>
                  未上传图片
                </div>
              ) : (
                <div className="uploaded-images" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {parseImages(selectedFeedback.image_paths).map((path, idx) => (
                    <img 
                      key={idx} 
                      src={`${apiUrl}/uploads/${path}`} 
                      alt="feedback attachment" 
                      className="uploaded-img"
                      onError={(e) => {
                        // Fallback in case upload path isn't served or mapped
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
      </div>
    </div>
  );
};
