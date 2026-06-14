import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Table, Tag, Button, Select, Space, Typography, Input, Badge, Tooltip, Empty, Spin,
} from 'antd'
import {
  TrophyOutlined, TeamOutlined, CalendarOutlined, SearchOutlined, ReloadOutlined,
  BarChartOutlined, FileTextOutlined, BulbOutlined, ExperimentOutlined, PlayCircleOutlined,
} from '@ant-design/icons'
import { sessionAPI } from '../../services/api'

const { Title, Text } = Typography
const { Option } = Select

const MODE_META = {
  quiz:         { labelKey: 'results.modeQuiz',        color: '#4F46E5', icon: <BulbOutlined /> },
  poll:         { labelKey: 'results.modePoll',        color: '#EA580C', icon: <BarChartOutlined /> },
  offline_poll: { labelKey: 'results.modeOfflinePoll', color: '#DB2777', icon: <FileTextOutlined /> },
  exam:         { labelKey: 'results.modeExam',        color: '#059669', icon: <ExperimentOutlined /> },
}

function ModeTag({ type }) {
  const { t } = useTranslation()
  const m = MODE_META[type] || { labelKey: null, color: '#6b7280', icon: <BulbOutlined /> }
  return (
    <Tag style={{ background: `${m.color}15`, borderColor: `${m.color}50`, color: m.color }}>
      {m.icon} {m.labelKey ? t(m.labelKey) : type}
    </Tag>
  )
}

function StatusBadge({ status }) {
  const { t } = useTranslation()
  const map = {
    ended:   { color: 'default',    textKey: 'results.statusEnded' },
    active:  { color: 'processing', textKey: 'results.statusActive' },
    created: { color: 'warning',    textKey: 'results.statusCreated' },
  }
  const s = map[status] || { color: 'default', textKey: null }
  return <Badge status={s.color} text={s.textKey ? t(s.textKey) : status} />
}

function recapUrl(item) {
  if (item.quiz_type === 'exam') return `/quiz/${item.quiz_id}/exam-results`
  if (item.quiz_type === 'offline_poll') return `/quiz/${item.quiz_id}/offline-results`
  return `/quiz/${item.quiz_id}/recap/${item.id}`
}

export default function ResultsHub() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [sessions, setSessions]   = useState([])
  const [total, setTotal]         = useState(0)
  const [loading, setLoading]     = useState(false)
  const [page, setPage]           = useState(1)
  const [pageSize]                = useState(20)
  const [quizTypeFilter, setQuizTypeFilter] = useState(null)
  const [statusFilter, setStatusFilter]     = useState(null)
  const [search, setSearch]       = useState('')

  const load = useCallback(async (p = page) => {
    setLoading(true)
    try {
      const params = { page: p, page_size: pageSize }
      if (quizTypeFilter) params.quiz_type = quizTypeFilter
      if (statusFilter)   params.status    = statusFilter
      const res = await sessionAPI.listAllSessions(params)
      setSessions(res.data.items || [])
      setTotal(res.data.total || 0)
    } catch (_) {
      setSessions([])
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, quizTypeFilter, statusFilter])

  useEffect(() => { load(1); setPage(1) }, [quizTypeFilter, statusFilter])
  useEffect(() => { load(page) }, [page])

  const filtered = search
    ? sessions.filter(s => s.quiz_title.toLowerCase().includes(search.toLowerCase()))
    : sessions

  const columns = [
    {
      title: t('results.activity', 'Activity'),
      dataIndex: 'quiz_title',
      ellipsis: true,
      render: (title, row) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ fontSize: 14 }}>{title}</Text>
          <ModeTag type={row.quiz_type} />
        </Space>
      ),
    },
    {
      title: t('results.status', 'Status'),
      dataIndex: 'status',
      width: 90,
      render: (s) => <StatusBadge status={s} />,
    },
    {
      title: <><TeamOutlined /> {t('results.participants', 'Participants')}</>,
      dataIndex: 'participant_count',
      width: 110,
      align: 'center',
      render: (n) => <Text strong>{n}</Text>,
    },
    {
      title: <><CalendarOutlined /> {t('results.date', 'Date')}</>,
      dataIndex: 'created_at',
      width: 140,
      render: (d) => {
        const dt = new Date(d)
        return (
          <Space direction="vertical" size={0}>
            <Text style={{ fontSize: 13 }}>{dt.toLocaleDateString()}</Text>
            <Text type="secondary" style={{ fontSize: 11 }}>{dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</Text>
          </Space>
        )
      },
    },
    {
      title: '',
      key: 'actions',
      width: 130,
      render: (_, row) => (
        row.status === 'ended' ? (
          <Button
            size="small"
            icon={<TrophyOutlined />}
            onClick={() => navigate(recapUrl(row))}
          >
            {t('results.viewResults', 'Results')}
          </Button>
        ) : row.status === 'active' ? (
          <Button
            size="small"
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => navigate(`/quiz/${row.quiz_id}/control`)}
          >
            {t('results.goLive', 'Go live')}
          </Button>
        ) : null
      ),
    },
  ]

  return (
    <div style={{ padding: '24px 24px 48px' }}>
      <Space style={{ marginBottom: 20, justifyContent: 'space-between', width: '100%', flexWrap: 'wrap' }}>
        <Space direction="vertical" size={0}>
          <Title level={3} style={{ margin: 0 }}>{t('results.title', 'Results')}</Title>
          <Text type="secondary">{t('results.subtitle', 'All sessions across your activities')}</Text>
        </Space>
        <Space wrap>
          <Input
            prefix={<SearchOutlined />}
            placeholder={t('results.searchPlaceholder', 'Search by title…')}
            value={search}
            onChange={e => setSearch(e.target.value)}
            allowClear
            style={{ width: 220 }}
          />
          <Select
            allowClear
            placeholder={t('results.filterMode', 'All modes')}
            style={{ width: 140 }}
            value={quizTypeFilter}
            onChange={setQuizTypeFilter}
          >
            <Option value="quiz">{t('quiz.quizTypeLabel', 'Quiz')}</Option>
            <Option value="poll">{t('quiz.poll', 'Poll')}</Option>
            <Option value="exam">{t('exam.typeLabel', 'Exam')}</Option>
            <Option value="offline_poll">{t('offlinePoll.typeLabel', 'Offline Poll')}</Option>
          </Select>
          <Select
            allowClear
            placeholder={t('results.filterStatus', 'All statuses')}
            style={{ width: 140 }}
            value={statusFilter}
            onChange={setStatusFilter}
          >
            <Option value="ended">{t('results.statusEnded', 'Ended')}</Option>
            <Option value="active">{t('results.statusActive', 'Live')}</Option>
            <Option value="created">{t('results.statusCreated', 'Open')}</Option>
          </Select>
          <Tooltip title={t('common.refresh', 'Refresh')}>
            <Button icon={<ReloadOutlined />} onClick={() => load(page)} loading={loading} />
          </Tooltip>
        </Space>
      </Space>

      <Spin spinning={loading}>
        {filtered.length === 0 && !loading ? (
          <Empty description={t('results.empty', 'No sessions found. Run a quiz or poll to see results here.')} />
        ) : (
          <Table
            dataSource={filtered}
            columns={columns}
            rowKey="id"
            pagination={{
              current: page,
              pageSize,
              total,
              showTotal: (t2) => `${t2} sessions`,
              onChange: (p) => setPage(p),
              showSizeChanger: false,
            }}
            size="middle"
          />
        )}
      </Spin>
    </div>
  )
}
