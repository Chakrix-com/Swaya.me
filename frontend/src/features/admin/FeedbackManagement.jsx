import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, DatePicker, Input, Rate, Row, Select, Space, Table, Tag, Typography } from 'antd'
import dayjs from 'dayjs'
import { useSelector } from 'react-redux'
import { useTranslation } from 'react-i18next'
import { statsAPI } from '../../services/api'
import './Admin.css'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

function FeedbackManagement() {
  const { t } = useTranslation()
  const { user } = useSelector((state) => state.auth)
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({
    source_type: undefined,
    rating: undefined,
    search: '',
    date_range: null,
  })
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
  })

  const fetchFeedback = async (page = pagination.current, pageSize = pagination.pageSize, nextFilters = filters) => {
    setLoading(true)
    try {
      const params = {
        limit: pageSize,
        offset: (page - 1) * pageSize,
      }
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
    } catch (error) {
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (user?.role === 'super_admin') {
      fetchFeedback(1, pagination.pageSize, filters)
    }
  }, [])

  if (user?.role !== 'super_admin') {
    return (
      <div style={{ padding: 24 }}>
        <Alert message={t('admin.feedbackPage.accessDenied')} description={t('admin.feedbackPage.accessDeniedDescription')} type="error" showIcon />
      </div>
    )
  }

  const columns = [
    {
      title: t('admin.feedbackPage.columns.when'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (value) => dayjs(value).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: t('admin.feedbackPage.columns.quiz'),
      dataIndex: 'quiz_title',
      key: 'quiz_title',
      width: 220,
      ellipsis: true,
    },
    {
      title: t('admin.feedbackPage.columns.tenant'),
      dataIndex: 'tenant_id',
      key: 'tenant_id',
      width: 90,
    },
    {
      title: t('admin.feedbackPage.columns.source'),
      dataIndex: 'source_type',
      key: 'source_type',
      width: 120,
      render: (value) => <Tag color={value === 'participant' ? 'blue' : 'green'}>{value}</Tag>,
    },
    {
      title: t('admin.feedbackPage.columns.rating'),
      dataIndex: 'rating',
      key: 'rating',
      width: 130,
      render: (value) => (value ? <Rate disabled value={value} /> : <Text type="secondary">{t('admin.feedbackPage.notAvailable')}</Text>),
    },
    {
      title: t('admin.feedbackPage.columns.submittedBy'),
      key: 'submitted_by',
      width: 220,
      render: (_, record) => record.display_name || record.user_email || t('admin.feedbackPage.anonymous'),
      ellipsis: true,
    },
    {
      title: t('admin.feedbackPage.columns.feedback'),
      dataIndex: 'feedback_text',
      key: 'feedback_text',
      ellipsis: true,
      render: (value) => (
        <Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {value}
        </Text>
      ),
    },
  ]

  const onApplyFilters = () => {
    const nextPage = 1
    setPagination((prev) => ({ ...prev, current: nextPage }))
    fetchFeedback(nextPage, pagination.pageSize, filters)
  }

  const onResetFilters = () => {
    const resetFilters = { source_type: undefined, rating: undefined, search: '', date_range: null }
    setFilters(resetFilters)
    const nextPage = 1
    setPagination((prev) => ({ ...prev, current: nextPage }))
    fetchFeedback(nextPage, pagination.pageSize, resetFilters)
  }

  const handleTableChange = (pager) => {
    const nextPage = pager.current || 1
    const nextSize = pager.pageSize || 20
    setPagination({ current: nextPage, pageSize: nextSize })
    fetchFeedback(nextPage, nextSize, filters)
  }

  return (
    <div className="admin-page" style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>{t('admin.feedback')}</Title>
        <Text type="secondary">{t('admin.feedbackPage.description')}</Text>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} className="admin-action-row">
          <Col xs={24} md={6}>
            <Select
              placeholder={t('admin.feedbackPage.filterSource')}
              allowClear
              className="admin-control"
              value={filters.source_type}
              onChange={(value) => setFilters((prev) => ({ ...prev, source_type: value }))}
              options={[
                { label: t('admin.feedbackPage.participant'), value: 'participant' },
                { label: t('admin.feedbackPage.user'), value: 'user' },
              ]}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              placeholder={t('admin.feedbackPage.filterRating')}
              allowClear
              className="admin-control"
              value={filters.rating}
              onChange={(value) => setFilters((prev) => ({ ...prev, rating: value }))}
              options={[1, 2, 3, 4, 5].map((value) => ({ label: `${value}`, value }))}
            />
          </Col>
          <Col xs={24} md={8}>
            <RangePicker
              className="admin-control"
              value={filters.date_range}
              onChange={(value) => setFilters((prev) => ({ ...prev, date_range: value }))}
            />
          </Col>
          <Col xs={24} md={6}>
            <Input
              placeholder={t('admin.feedbackPage.filterSearch')}
              className="admin-control"
              value={filters.search}
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
              onPressEnter={onApplyFilters}
            />
          </Col>
          <Col xs={24}>
            <Space wrap>
              <Button type="primary" onClick={onApplyFilters}>{t('admin.feedbackPage.applyFilters')}</Button>
              <Button onClick={onResetFilters}>{t('admin.feedbackPage.reset')}</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Card>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          scroll={{ x: 1300 }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50', '100'],
            showTotal: (value) => t('admin.feedbackPage.totalEntries', { value }),
          }}
          onChange={handleTableChange}
        />
      </Card>
    </div>
  )
}

export default FeedbackManagement
