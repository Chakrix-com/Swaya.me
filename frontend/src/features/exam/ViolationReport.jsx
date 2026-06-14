/**
 * ViolationReport — integrity report panel for hosts in ExamResults
 */
import { useState, useEffect } from 'react';
import {
  Card, Table, Tag, Badge, Modal, Button, Space, Typography, Spin, Alert, Timeline, Image
} from 'antd';
import { LockOutlined, UnlockOutlined, WarningOutlined, CheckCircleOutlined, CameraOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { proctoringAPI } from '../../services/api';
import dayjs from 'dayjs';

const { Text } = Typography;

function integrityColor(score) {
  if (score >= 70) return '#52c41a';
  if (score >= 40) return '#faad14';
  return '#ff4d4f';
}

function StatusTag({ entry }) {
  const { t } = useTranslation();
  if (entry.is_locked) return <Tag color="red" icon={<LockOutlined />}>{t('proctoring.report.locked')}</Tag>;
  if (entry.violation_count > 0) return <Tag color="orange" icon={<WarningOutlined />}>{t('proctoring.report.flagged')}</Tag>;
  return <Tag color="green" icon={<CheckCircleOutlined />}>{t('proctoring.report.clean')}</Tag>;
}

export function ViolationReport({ quizId }) {
  const { t } = useTranslation();
  const [report, setReport] = useState(null);
  const [proctoringEnabled, setProctoringEnabled] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [snapshotsLoading, setSnapshotsLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [reportRes, configRes] = await Promise.all([
        proctoringAPI.getReport(quizId),
        fetch(`/api/v1/proctoring/config/${quizId}`).then(r => r.json()).catch(() => null),
      ]);
      setReport(reportRes.data);
      setProctoringEnabled(configRes?.enabled ?? false);
    } catch (_) {
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [quizId]);

  const handleLock = async (entry) => {
    setActionLoading(true);
    try {
      // We need a session_token — find it from events
      const token = entry.events?.[0]?.session_token;
      if (token) await proctoringAPI.lockSession(token);
      await load();
    } catch (_) {} finally { setActionLoading(false); }
  };

  const handleUnlock = async (entry) => {
    setActionLoading(true);
    try {
      const token = entry.events?.[0]?.session_token;
      if (token) await proctoringAPI.unlockSession(token);
      await load();
    } catch (_) {} finally { setActionLoading(false); }
  };

  if (loading) return <Spin style={{ display: 'block', margin: '24px auto' }} />;
  if (!report || report.length === 0) {
    if (!proctoringEnabled) {
      return (
        <Alert
          message={t('proctoring.report.notEnabled')}
          description={t('proctoring.report.notEnabledDesc')}
          type="info"
          showIcon
          style={{ marginTop: 24 }}
        />
      );
    }
    return (
      <Alert
        message={t('proctoring.report.enabledNoData')}
        description={t('proctoring.report.enabledNoDataDesc')}
        type="success"
        showIcon
        style={{ marginTop: 24 }}
      />
    );
  }

  const columns = [
    {
      title: t('proctoring.report.participant'),
      render: (_, entry) => (
        <div>
          <Text strong>{entry.display_name || `#${entry.participant_id}`}</Text>
          {entry.email && (
            <div style={{ fontSize: 12, color: '#888' }}>{entry.email}</div>
          )}
        </div>
      ),
    },
    {
      title: t('proctoring.report.integrityScore'),
      dataIndex: 'integrity_score',
      render: (score) => (
        <Badge
          count={score}
          style={{ backgroundColor: integrityColor(score) }}
          overflowCount={100}
        />
      ),
      sorter: (a, b) => a.integrity_score - b.integrity_score,
    },
    {
      title: t('proctoring.report.violations'),
      dataIndex: 'violation_count',
    },
    {
      title: t('proctoring.report.status'),
      render: (_, entry) => <StatusTag entry={entry} />,
    },
    {
      title: t('proctoring.report.webcam'),
      render: (_, entry) =>
        entry.webcam_required
          ? entry.webcam_granted
            ? <Tag color="green">{t('proctoring.report.granted')}</Tag>
            : <Tag color="red">{t('proctoring.report.denied')}</Tag>
          : <Tag color="default">{t('proctoring.report.na')}</Tag>,
    },
    {
      title: t('proctoring.report.actions'),
      render: (_, entry) => (
        <Space>
          <Button size="small" onClick={() => {
            setSelectedEntry(entry);
            setSnapshots([]);
            setSnapshotsLoading(true);
            proctoringAPI.getSnapshots(quizId, entry.participant_id)
              .then(res => setSnapshots(res.data.snapshots || []))
              .catch(() => setSnapshots([]))
              .finally(() => setSnapshotsLoading(false));
          }}>
            {t('proctoring.report.viewDetail')}
          </Button>
          {entry.is_locked ? (
            <Button size="small" type="link" onClick={() => handleUnlock(entry)} loading={actionLoading}>
              <UnlockOutlined /> {t('proctoring.report.unlock')}
            </Button>
          ) : (
            <Button size="small" type="link" danger onClick={() => handleLock(entry)} loading={actionLoading}>
              <LockOutlined /> {t('proctoring.report.lock')}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card title={<Space><LockOutlined /> {t('proctoring.report.title')}</Space>} style={{ marginTop: 24 }}>
        <Table
          dataSource={report}
          columns={columns}
          rowKey="participant_id"
          size="small"
          pagination={{ pageSize: 20 }}
        />
      </Card>

      <Modal
        title={<Space><CameraOutlined /> {selectedEntry?.display_name || `#${selectedEntry?.participant_id}`}{selectedEntry?.email ? ` — ${selectedEntry.email}` : ''}</Space>}
        open={!!selectedEntry}
        onCancel={() => { setSelectedEntry(null); setSnapshots([]); }}
        footer={null}
        width={700}
      >
        {selectedEntry && (
          <>
            {/* Webcam snapshot filmstrip */}
            <div style={{ marginBottom: 20 }}>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>
                <CameraOutlined /> Webcam Snapshots ({snapshotsLoading ? '…' : snapshots.length})
              </Text>
              {snapshotsLoading ? (
                <Spin size="small" />
              ) : snapshots.length === 0 ? (
                <Alert message={t('exam.noSnapshotsParticipant')} type="warning" showIcon style={{ marginBottom: 8 }} />
              ) : (
                <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 8 }}>
                  <Image.PreviewGroup>
                    {snapshots.map((snap) => {
                      // Highlight if a violation event occurred within 60s of this snapshot
                      const snapTime = snap.timestamp_ms;
                      const nearViolation = selectedEntry.events.some((e) => {
                        if (!e.occurred_at) return false;
                        const evtMs = dayjs(e.occurred_at).valueOf();
                        return Math.abs(evtMs - snapTime) < 60000;
                      });
                      return (
                        <div key={snap.filename} style={{ flexShrink: 0, textAlign: 'center' }}>
                          <Image
                            src={snap.url}
                            width={100}
                            height={75}
                            style={{
                              objectFit: 'cover',
                              border: nearViolation ? '2px solid #ff4d4f' : '2px solid #d9d9d9',
                              borderRadius: 4,
                            }}
                            preview={{ src: snap.url }}
                          />
                          <div style={{ fontSize: 10, color: nearViolation ? '#ff4d4f' : '#999', marginTop: 2 }}>
                            {snap.timestamp_ms ? dayjs(snap.timestamp_ms).format('HH:mm:ss') : ''}
                            {nearViolation && ' ⚠'}
                          </div>
                        </div>
                      );
                    })}
                  </Image.PreviewGroup>
                </div>
              )}
            </div>

            {/* Violation event timeline */}
            {selectedEntry.events.length === 0 ? (
              <Alert message={t('exam.noViolationEvents')} type="success" showIcon />
            ) : (
              <Timeline
                items={selectedEntry.events.map((e) => ({
                  color: e.event_type.includes('LOCK') ? 'red' : e.event_type.includes('HONEYPOT') ? 'red' : 'orange',
                  children: (
                    <div>
                      <Text strong>{e.event_type}</Text>
                      {e.rule_id && <Text type="secondary"> ({e.rule_id})</Text>}
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {e.occurred_at ? dayjs(e.occurred_at).format('HH:mm:ss') : ''}
                      </Text>
                      {e.metadata && Object.keys(e.metadata).length > 0 && (
                        <pre style={{ fontSize: 11, marginTop: 4, color: '#666' }}>
                          {JSON.stringify(e.metadata, null, 2)}
                        </pre>
                      )}
                    </div>
                  ),
                }))}
              />
            )}
          </>
        )}
      </Modal>
    </>
  );
}
