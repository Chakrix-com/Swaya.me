import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, DatePicker, Input, Rate, Row, Select, Space, Table, Tabs, Tag, Tooltip, Typography } from 'antd'
import dayjs from 'dayjs'
import { useSelector } from 'react-redux'
import { useTranslation } from 'react-i18next'
import { statsAPI, appFeedbackAPI } from '../../services/api'
import './Admin.css'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

// ─── Quiz Feedback Tab ────────────────────────────────────────────────────────

function QuizFeedbackTab() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({ source_type: undefined, rating: undefined, search: '', date_range: null })
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 })

  const fetchFeedback = async (page = pagination.current, pageSize = pagination.pageSize, nextFilters = filters) => {
    setLoading(true)
    try {
      const params = { limit: pageSize, offset: (page - 1) * pageSize }
      if (nextFilters.source_type) params.source_type = nextFilters.source_type
      if (nextFilters.rating) params.rating = nextFilters.rating
      if (nextFilters.search?.trim()) params.search = nextFilters.search.trim()
      if (nextFilters.date_range?.[0] && nextFilters.date_range?.[1]) {
        params.date_from = nextFilters.date_range[0].startOf('day').toISOString()
        params.date_to = nextFilters.date_range[1].endOf('day').toISOString()
      }
      const response = await statsAPI.getFeedback(params)
      setItems(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch {
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchFeedback(1, pagination.pageSize, filters) }, [])

  const columns = [
    { title: t('admin.feedbackPage.columns.when'), dataIndex: 'created_at', key: 'created_at', width: 170, render: (v) => dayjs(v).format('YYYY-MM-DD HH:mm') },
    { title: t('admin.feedbackPage.columns.quiz'), dataIndex: 'quiz_title', key: 'quiz_title', width: 220, ellipsis: true },
    { title: t('admin.feedbackPage.columns.tenant'), dataIndex: 'tenant_id', key: 'tenant_id', width: 90 },
    { title: t('admin.feedbackPage.columns.source'), dataIndex: 'source_type', key: 'source_type', width: 120, render: (v) => <Tag color={v === 'participant' ? 'blue' : 'green'}>{v}</Tag> },
    { title: t('admin.feedbackPage.columns.rating'), dataIndex: 'rating', key: 'rating', width: 130, render: (v) => (v ? <Rate disabled value={v} /> : <Text type="secondary">{t('admin.feedbackPage.notAvailable')}</Text>) },
    { title: t('admin.feedbackPage.columns.submittedBy'), key: 'submitted_by', width: 220, render: (_, r) => r.display_name || r.user_email || t('admin.feedbackPage.anonymous'), ellipsis: true },
    {
      title: t('admin.feedbackPage.columns.feedback'),
      dataIndex: 'feedback_text',
      key: 'feedback_text',
      ellipsis: true,
      render: (v) => <Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{v}</Text>,
    },
  ]

  const onApply = () => { setPagination((p) => ({ ...p, current: 1 })); fetchFeedback(1, pagination.pageSize, filters) }
  const onReset = () => {
    const f = { source_type: undefined, rating: undefined, search: '', date_range: null }
    setFilters(f); setPagination((p) => ({ ...p, current: 1 })); fetchFeedback(1, pagination.pageSize, f)
  }
  const onTableChange = (pager) => {
    const page = pager.current || 1; const size = pager.pageSize || 20
    setPagination({ current: page, pageSize: size }); fetchFeedback(page, size, filters)
  }

  return (
    <>
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} className="admin-action-row">
          <Col xs={24} md={6}>
            <Select placeholder={t('admin.feedbackPage.filterSource')} allowClear className="admin-control" value={filters.source_type} onChange={(v) => setFilters((p) => ({ ...p, source_type: v }))} options={[{ label: t('admin.feedbackPage.participant'), value: 'participant' }, { label: t('admin.feedbackPage.user'), value: 'user' }]} />
          </Col>
          <Col xs={24} md={4}>
            <Select placeholder={t('admin.feedbackPage.filterRating')} allowClear className="admin-control" value={filters.rating} onChange={(v) => setFilters((p) => ({ ...p, rating: v }))} options={[1,2,3,4,5].map((v) => ({ label: `${v}`, value: v }))} />
          </Col>
          <Col xs={24} md={8}>
            <RangePicker className="admin-control" value={filters.date_range} onChange={(v) => setFilters((p) => ({ ...p, date_range: v }))} />
          </Col>
          <Col xs={24} md={6}>
            <Input placeholder={t('admin.feedbackPage.filterSearch')} className="admin-control" value={filters.search} onChange={(e) => setFilters((p) => ({ ...p, search: e.target.value }))} onPressEnter={onApply} />
          </Col>
          <Col xs={24}><Space wrap><Button type="primary" onClick={onApply}>{t('admin.feedbackPage.applyFilters')}</Button><Button onClick={onReset}>{t('admin.feedbackPage.reset')}</Button></Space></Col>
        </Row>
      </Card>
      <Card>
        <Table rowKey="id" columns={columns} dataSource={items} loading={loading} scroll={{ x: 1300 }} pagination={{ current: pagination.current, pageSize: pagination.pageSize, total, showSizeChanger: true, pageSizeOptions: ['10','20','50','100'], showTotal: (v) => t('admin.feedbackPage.totalEntries', { value: v }) }} onChange={onTableChange} />
      </Card>
    </>
  )
}

// ─── App Feedback Tab ─────────────────────────────────────────────────────────

function AppFeedbackTab() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({ source_type: undefined, rating: undefined, search: '', date_range: null, page_url_contains: '' })
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 })

  const fetchFeedback = async (page = pagination.current, pageSize = pagination.pageSize, nextFilters = filters) => {
    setLoading(true)
    try {
      const params = { limit: pageSize, offset: (page - 1) * pageSize }
      if (nextFilters.source_type) params.source_type = nextFilters.source_type
      if (nextFilters.rating) params.rating = nextFilters.rating
      if (nextFilters.search?.trim()) params.search = nextFilters.search.trim()
      if (nextFilters.page_url_contains?.trim()) params.page_url_contains = nextFilters.page_url_contains.trim()
      if (nextFilters.date_range?.[0] && nextFilters.date_range?.[1]) {
        params.date_from = nextFilters.date_range[0].startOf('day').toISOString()
        params.date_to = nextFilters.date_range[1].endOf('day').toISOString()
      }
      const response = await appFeedbackAPI.listAppFeedback(params)
      setItems(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch {
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchFeedback(1, pagination.pageSize, filters) }, [])

  const columns = [
    { title: t('admin.feedbackPage.columns.when'), dataIndex: 'created_at', key: 'created_at', width: 170, render: (v) => dayjs(v).format('YYYY-MM-DD HH:mm') },
    {
      title: t('admin.feedbackPage.columns.pageUrl'),
      dataIndex: 'page_url',
      key: 'page_url',
      width: 240,
      ellipsis: true,
      render: (v) => <Tooltip title={v}><Text style={{ fontFamily: 'monospace', fontSize: 12 }}>{v}</Text></Tooltip>,
    },
    { title: t('admin.feedbackPage.columns.source'), dataIndex: 'source_type', key: 'source_type', width: 120, render: (v) => <Tag color={v === 'anonymous' ? 'default' : 'green'}>{v}</Tag> },
    { title: t('admin.feedbackPage.columns.rating'), dataIndex: 'rating', key: 'rating', width: 130, render: (v) => (v ? <Rate disabled value={v} /> : <Text type="secondary">{t('admin.feedbackPage.notAvailable')}</Text>) },
    { title: t('admin.feedbackPage.columns.submittedBy'), key: 'submitted_by', width: 200, render: (_, r) => r.display_name || r.user_email || t('admin.feedbackPage.anonymous'), ellipsis: true },
    {
      title: t('admin.feedbackPage.columns.feedback'),
      dataIndex: 'feedback_text',
      key: 'feedback_text',
      render: (v) => <div dangerouslySetInnerHTML={{ __html: v }} style={{ maxHeight: 120, overflow: 'hidden', wordBreak: 'break-word' }} />,
    },
  ]

  const onApply = () => { setPagination((p) => ({ ...p, current: 1 })); fetchFeedback(1, pagination.pageSize, filters) }
  const onReset = () => {
    const f = { source_type: undefined, rating: undefined, search: '', date_range: null, page_url_contains: '' }
    setFilters(f); setPagination((p) => ({ ...p, current: 1 })); fetchFeedback(1, pagination.pageSize, f)
  }
  const onTableChange = (pager) => {
    const page = pager.current || 1; const size = pager.pageSize || 20
    setPagination({ current: page, pageSize: size }); fetchFeedback(page, size, filters)
  }

  return (
    <>
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} className="admin-action-row">
          <Col xs={24} md={5}>
            <Select placeholder={t('admin.feedbackPage.filterSource')} allowClear className="admin-control" value={filters.source_type} onChange={(v) => setFilters((p) => ({ ...p, source_type: v }))} options={[{ label: t('admin.feedbackPage.anonymous'), value: 'anonymous' }, { label: t('admin.feedbackPage.user'), value: 'user' }]} />
          </Col>
          <Col xs={24} md={3}>
            <Select placeholder={t('admin.feedbackPage.filterRating')} allowClear className="admin-control" value={filters.rating} onChange={(v) => setFilters((p) => ({ ...p, rating: v }))} options={[1,2,3,4,5].map((v) => ({ label: `${v}`, value: v }))} />
          </Col>
          <Col xs={24} md={7}>
            <RangePicker className="admin-control" value={filters.date_range} onChange={(v) => setFilters((p) => ({ ...p, date_range: v }))} />
          </Col>
          <Col xs={24} md={4}>
            <Input placeholder={t('admin.feedbackPage.filterPageUrl')} className="admin-control" value={filters.page_url_contains} onChange={(e) => setFilters((p) => ({ ...p, page_url_contains: e.target.value }))} onPressEnter={onApply} />
          </Col>
          <Col xs={24} md={5}>
            <Input placeholder={t('admin.feedbackPage.filterSearch')} className="admin-control" value={filters.search} onChange={(e) => setFilters((p) => ({ ...p, search: e.target.value }))} onPressEnter={onApply} />
          </Col>
          <Col xs={24}><Space wrap><Button type="primary" onClick={onApply}>{t('admin.feedbackPage.applyFilters')}</Button><Button onClick={onReset}>{t('admin.feedbackPage.reset')}</Button></Space></Col>
        </Row>
      </Card>
      <Card>
        <Table rowKey="id" columns={columns} dataSource={items} loading={loading} scroll={{ x: 1300 }} pagination={{ current: pagination.current, pageSize: pagination.pageSize, total, showSizeChanger: true, pageSizeOptions: ['10','20','50','100'], showTotal: (v) => t('admin.feedbackPage.totalEntries', { value: v }) }} onChange={onTableChange} />
      </Card>
    </>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

function FeedbackManagement() {
  const { t } = useTranslation()
  const { user } = useSelector((state) => state.auth)

  if (user?.role !== 'super_admin') {
    return (
      <div style={{ padding: 24 }}>
        <Alert message={t('admin.feedbackPage.accessDenied')} description={t('admin.feedbackPage.accessDeniedDescription')} type="error" showIcon />
      </div>
    )
  }

  const tabItems = [
    { key: 'quiz', label: t('admin.feedbackPage.quizFeedbackTab'), children: <QuizFeedbackTab /> },
    { key: 'app', label: t('admin.feedbackPage.appFeedbackTab'), children: <AppFeedbackTab /> },
  ]

  return (
    <div className="admin-page" style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>{t('admin.feedback')}</Title>
        <Text type="secondary">{t('admin.feedbackPage.description')}</Text>
      </div>
      <Tabs defaultActiveKey="quiz" items={tabItems} />
    </div>
  )
}

export default FeedbackManagement
