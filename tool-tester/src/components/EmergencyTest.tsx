// tool-tester/src/components/EmergencyTest.tsx
import React, { useState, useEffect } from 'react';
import { ShieldAlert, Plus, MapPin, User, Send, RefreshCw, X, MessageSquare } from 'lucide-react';

interface EmergencyTestProps {
  apiUrl: string;
  onSetRawJson: (json: any) => void;
}

interface EmergencyEvent {
  id: number;
  type: string;
  severity: string;
  location: string;
  description: string;
  status: string;
  affected_areas: string; // JSON array string
  reporter_info?: string;
  created_at?: string;
  updated_at?: string;
}

interface ResponseLog {
  id: number;
  event_id: number;
  action: string;
  actor?: string;
  note?: string;
  created_at?: string;
}

export const EmergencyTest: React.FC<EmergencyTestProps> = ({ apiUrl, onSetRawJson }) => {
  const [events, setEvents] = useState<EmergencyEvent[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Filters
  const [filterType, setFilterType] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  // Selected Event Detail
  const [selectedEvent, setSelectedEvent] = useState<EmergencyEvent | null>(null);
  const [eventLogs, setEventLogs] = useState<ResponseLog[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);

  // New Event Form
  const [showReportForm, setShowReportForm] = useState(false);
  const [formData, setFormData] = useState({
    type: 'other',
    severity: 'medium',
    location: '九龙灌浴广场',
    description: '有游客发生轻微擦伤，需要创可贴和简易包扎。',
    affected_areas: '九龙灌浴',
    reporter_info: '导游张三',
  });

  // Log Form
  const [logForm, setLogForm] = useState({
    action: 'confirm',
    actor: '控制中心值班员',
    note: '已确认，正在调度医务人员。',
  });

  const fetchEvents = async () => {
    setLoading(true);
    try {
      let query = `?skip=0&limit=50`;
      if (filterType) query += `&type=${filterType}`;
      if (filterSeverity) query += `&severity=${filterSeverity}`;
      if (filterStatus) query += `&status=${filterStatus}`;

      const res = await fetch(`${apiUrl}/api/tools/emergency/events${query}`);
      const data = await res.json();
      setEvents(data);
      onSetRawJson({ action: 'emergency/list_events', filters: { filterType, filterSeverity, filterStatus }, response: data });
    } catch (err: any) {
      console.error(err);
      onSetRawJson({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, [apiUrl, filterType, filterSeverity, filterStatus]);

  const handleSelectEvent = async (event: EmergencyEvent) => {
    setSelectedEvent(event);
    setDetailLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/tools/emergency/events/${event.id}`);
      const data = await res.json();
      onSetRawJson({ action: 'emergency/get_event_detail', event_id: event.id, response: data });
      if (res.ok) {
        setEventLogs(data.response_logs || []);
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleReportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        affected_areas: formData.affected_areas.split(',').map(a => a.trim()).filter(Boolean),
      };
      const res = await fetch(`${apiUrl}/api/tools/emergency/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      onSetRawJson({ action: 'emergency/report_event', request: payload, response: data });
      if (res.ok) {
        setShowReportForm(false);
        fetchEvents();
      } else {
        alert(data.detail || '上报失败');
      }
    } catch (err: any) {
      console.error(err);
      onSetRawJson({ error: err.message });
    }
  };

  const handleAddLogSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEvent) return;
    try {
      const res = await fetch(`${apiUrl}/api/tools/emergency/events/${selectedEvent.id}/logs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logForm),
      });
      const data = await res.json();
      onSetRawJson({ action: 'emergency/add_response_log', event_id: selectedEvent.id, request: logForm, response: data });
      if (res.ok) {
        // Refresh event details and status
        const updatedRes = await fetch(`${apiUrl}/api/tools/emergency/events/${selectedEvent.id}`);
        const updatedData = await updatedRes.json();
        setEventLogs(updatedData.response_logs || []);
        if (updatedData.event) {
          setSelectedEvent(updatedData.event);
        }
        // Refresh events list in bg
        fetchEvents();
        setLogForm({ ...logForm, note: '' });
      } else {
        alert(data.detail || '日志添加失败');
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  const getSeverityBadge = (sev: string) => {
    return <span className={`badge badge-${sev}`}>{sev}</span>;
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      reported: '已上报',
      confirmed: '已确认',
      responding: '处置中',
      resolved: '已解决',
      closed: '已关闭',
    };
    return labels[status] || status;
  };

  const parseAreas = (areasJson: string): string[] => {
    try {
      return JSON.parse(areasJson);
    } catch (e) {
      return [];
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top filter & Actions */}
      <div className="glass-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldAlert size={20} className="text-accent" style={{ color: 'var(--accent)' }} />
            <h3 style={{ margin: 0 }}>应急事件管理</h3>
          </div>

          {/* Filters */}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <select value={filterType} onChange={(e) => setFilterType(e.target.value)} style={{ padding: '0.4rem', fontSize: '0.85rem', width: '110px' }}>
              <option value="">所有类型</option>
              <option value="fire">火灾 (fire)</option>
              <option value="crowd">拥挤 (crowd)</option>
              <option value="equipment">故障 (equipment)</option>
              <option value="weather">天气 (weather)</option>
              <option value="medical">医疗 (medical)</option>
              <option value="other">其他 (other)</option>
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
              <option value="reported">已上报</option>
              <option value="confirmed">已确认</option>
              <option value="responding">处置中</option>
              <option value="resolved">已解决</option>
              <option value="closed">已关闭</option>
            </select>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button onClick={fetchEvents} className="btn btn-secondary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            刷新
          </button>
          <button onClick={() => setShowReportForm(true)} className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
            <Plus size={14} />
            事件上报
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selectedEvent || showReportForm ? '1fr 1.2fr' : '1fr', gap: '1.5rem' }}>
        {/* Left Side: Events List */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h3 style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>事件列表</h3>
          {events.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>
              没有找到符合条件的应急事件。
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '650px', overflowY: 'auto' }}>
              {events.map((e) => (
                <div 
                  key={e.id} 
                  className={`result-item ${selectedEvent?.id === e.id ? 'active' : ''}`}
                  onClick={() => handleSelectEvent(e)}
                  style={{ 
                    cursor: 'pointer',
                    borderLeft: selectedEvent?.id === e.id ? '4px solid var(--accent)' : '1px solid var(--border-color)',
                    backgroundColor: selectedEvent?.id === e.id ? 'var(--accent-glow)' : ''
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      #{e.id} - {e.type.toUpperCase()}
                    </span>
                    <div style={{ display: 'flex', gap: '0.4rem' }}>
                      {getSeverityBadge(e.severity)}
                      <span className="badge badge-status">{getStatusLabel(e.status)}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
                    <MapPin size={12} />
                    <span>{e.location}</span>
                  </div>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                    {e.description}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Side: Details Drawer OR Report Form */}
        {showReportForm && (
          <div className="glass-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', marginBottom: '1.25rem' }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldAlert size={18} className="text-critical" style={{ color: 'var(--critical)' }} />
                应急事件上报
              </h3>
              <button onClick={() => setShowReportForm(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleReportSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="form-group row" style={{ marginBottom: 0 }}>
                <div>
                  <label htmlFor="type">事件类型</label>
                  <select id="type" value={formData.type} onChange={(e) => setFormData({ ...formData, type: e.target.value })}>
                    <option value="fire">火灾 (fire)</option>
                    <option value="crowd">拥挤 (crowd)</option>
                    <option value="equipment">设备故障 (equipment)</option>
                    <option value="weather">恶劣天气 (weather)</option>
                    <option value="medical">医疗救助 (medical)</option>
                    <option value="other">其他紧急 (other)</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="severity">严重度</label>
                  <select id="severity" value={formData.severity} onChange={(e) => setFormData({ ...formData, severity: e.target.value })}>
                    <option value="low">低 (low)</option>
                    <option value="medium">中 (medium)</option>
                    <option value="high">高 (high)</option>
                    <option value="critical">特别紧急 (critical)</option>
                  </select>
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="location">事发地点</label>
                <input id="location" type="text" value={formData.location} onChange={(e) => setFormData({ ...formData, location: e.target.value })} required />
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="description">事件详述</label>
                <textarea id="description" value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} required />
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="affected_areas">受影响区域 (逗号分隔)</label>
                <input id="affected_areas" type="text" value={formData.affected_areas} onChange={(e) => setFormData({ ...formData, affected_areas: e.target.value })} placeholder="例如: 九龙灌浴, 灵山梵宫" />
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="reporter_info">上报人/联系方式</label>
                <input id="reporter_info" type="text" value={formData.reporter_info} onChange={(e) => setFormData({ ...formData, reporter_info: e.target.value })} />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>立即上报</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowReportForm(false)}>取消</button>
              </div>
            </form>
          </div>
        )}

        {selectedEvent && !showReportForm && (
          <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span>事件 #{selectedEvent.id} 详情</span>
              </h3>
              <button onClick={() => setSelectedEvent(null)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>

            {/* Event core info */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', backgroundColor: 'rgba(255, 255, 255, 0.01)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>类型 / 级别</span>
                <div>
                  <span className="badge" style={{ marginRight: '0.4rem', backgroundColor: 'rgba(255, 255, 255, 0.05)' }}>{selectedEvent.type}</span>
                  {getSeverityBadge(selectedEvent.severity)}
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>当前状态</span>
                <span className="badge badge-status active-status">{getStatusLabel(selectedEvent.status)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>发生地点</span>
                <span style={{ fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  <MapPin size={12} /> {selectedEvent.location}
                </span>
              </div>
              {selectedEvent.reporter_info && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>上报人</span>
                  <span style={{ fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <User size={12} /> {selectedEvent.reporter_info}
                  </span>
                </div>
              )}
              {parseAreas(selectedEvent.affected_areas).length > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>受影响景点</span>
                  <div style={{ display: 'flex', gap: '0.25rem' }}>
                    {parseAreas(selectedEvent.affected_areas).map((area, idx) => (
                      <span key={idx} className="badge badge-status" style={{ fontSize: '0.7rem' }}>{area}</span>
                    ))}
                  </div>
                </div>
              )}
              <div style={{ marginTop: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>描述内容</span>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>{selectedEvent.description}</p>
              </div>
            </div>

            {/* Timeline logs */}
            <div>
              <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.95rem', marginBottom: '0.75rem' }}>
                <MessageSquare size={16} />
                处置追踪进展 ({eventLogs.length})
              </h4>
              {detailLoading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '1rem' }}><RefreshCw className="animate-spin" /></div>
              ) : eventLogs.length === 0 ? (
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textAlign: 'center', padding: '1rem', border: '1px dashed var(--border-color)', borderRadius: '6px' }}>
                  暂无处理日志，请开始跟踪处置。
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '180px', overflowY: 'auto', paddingRight: '0.25rem' }}>
                  {eventLogs.map((log) => (
                    <div key={log.id} style={{ display: 'flex', gap: '0.5rem', fontSize: '0.85rem', padding: '0.5rem', backgroundColor: 'rgba(0,0,0,0.15)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                          <strong style={{ color: 'var(--accent)' }}>{getStatusLabel(log.action === 'add_log' ? '更新' : log.action)}</strong>
                          <span>{log.actor || '未知'}</span>
                        </div>
                        {log.note && <p style={{ color: 'var(--text-primary)', fontSize: '0.825rem' }}>{log.note}</p>}
                        {log.created_at && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'right' }}>
                            {new Date(log.created_at).toLocaleString()}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Add log Form */}
            <form onSubmit={handleAddLogSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
              <h4 style={{ fontSize: '0.95rem' }}>添加响应日志</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label htmlFor="log_action">操作指令</label>
                  <select 
                    id="log_action" 
                    value={logForm.action} 
                    onChange={(e) => setLogForm({ ...logForm, action: e.target.value })}
                    style={{ padding: '0.4rem' }}
                  >
                    <option value="confirm">确认事件 (confirm)</option>
                    <option value="dispatch">派发处置 (dispatch)</option>
                    <option value="resolve">宣布解决 (resolve)</option>
                    <option value="close">关闭事件 (close)</option>
                  </select>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label htmlFor="log_actor">操作人</label>
                  <input 
                    id="log_actor" 
                    type="text" 
                    value={logForm.actor} 
                    onChange={(e) => setLogForm({ ...logForm, actor: e.target.value })} 
                    style={{ padding: '0.4rem' }}
                  />
                </div>
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="log_note">备注说明</label>
                <input 
                  id="log_note" 
                  type="text" 
                  value={logForm.note} 
                  onChange={(e) => setLogForm({ ...logForm, note: e.target.value })} 
                  placeholder="请输入处置说明..."
                  required
                  style={{ padding: '0.4rem' }}
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ padding: '0.4rem', fontSize: '0.875rem' }}>
                <Send size={14} />
                发送进展指令
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
