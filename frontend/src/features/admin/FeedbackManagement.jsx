import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, DatePicker, Input, Rate, Row, Select, Space, Table, Tag, Typography } from 'antd'
import dayjs from 'dayjs'
import { useSelector } from 'react-redux'
import { statsAPI } from '../../services/api'
import './Admin.css'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

function FeedbackManagement() {
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
        <Alert message="Access denied" description="Only super admins can view feedback." type="error" showIcon />
      </div>
    )
  }

  const columns = [
    {
      title: 'When',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (value) => dayjs(value).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Quiz',
      dataIndex: 'quiz_title',
      key: 'quiz_title',
      width: 220,
      ellipsis: true,
    },
    {
      title: 'Tenant',
      dataIndex: 'tenant_id',
      key: 'tenant_id',
      width: 90,
    },
    {
      title: 'Source',
      dataIndex: 'source_type',
      key: 'source_type',
      width: 120,
      render: (value) => <Tag color={value === 'participant' ? 'blue' : 'green'}>{value}</Tag>,
    },
    {
      title: 'Rating',
      dataIndex: 'rating',
      key: 'rating',
      width: 130,
      render: (value) => (value ? <Rate disabled value={value} /> : <Text type="secondary">N/A</Text>),
    },
    {
      title: 'Submitted By',
      key: 'submitted_by',
      width: 220,
      render: (_, record) => record.display_name || record.user_email || 'Anonymous',
      ellipsis: true,
    },
    {
      title: 'Feedback',
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
        <Title level={2} style={{ margin: 0 }}>Feedback</Title>
        <Text type="secondary">Super admin feedback console with server-side filtering and pagination</Text>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} className="admin-action-row">
          <Col xs={24} md={6}>
            <Select
              placeholder="Source"
              allowClear
              className="admin-control"
              value={filters.source_type}
              onChange={(value) => setFilters((prev) => ({ ...prev, source_type: value }))}
              options={[
                { label: 'Participant', value: 'participant' },
                { label: 'User', value: 'user' },
              ]}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              placeholder="Rating"
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
              placeholder="Search feedback text"
              className="admin-control"
              value={filters.search}
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
              onPressEnter={onApplyFilters}
            />
          </Col>
          <Col xs={24}>
            <Space wrap>
              <Button type="primary" onClick={onApplyFilters}>Apply Filters</Button>
              <Button onClick={onResetFilters}>Reset</Button>
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
            showTotal: (value) => `Total ${value} feedback entries`,
          }}
          onChange={handleTableChange}
        />
      </Card>
    </div>
  )
}

export default FeedbackManagement
