import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, DatePicker, Input, InputNumber, Row, Select, Space, Table, Tag, Typography } from 'antd'
import { useSelector } from 'react-redux'
import dayjs from 'dayjs'
import { platformQuizAPI } from '../../services/api'
import './Admin.css'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

function PlatformQuizzes() {
  const { user } = useSelector((state) => state.auth)
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({
    search: '',
    status: undefined,
    tenant_id: undefined,
    min_questions: undefined,
    max_questions: undefined,
    date_range: null,
  })
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 })
  const [sorting, setSorting] = useState({ sort_by: 'created_at', sort_order: 'desc' })

  const fetchQuizzes = async (
    page = pagination.current,
    pageSize = pagination.pageSize,
    nextFilters = filters,
    nextSorting = sorting,
  ) => {
    setLoading(true)
    try {
      const params = {
        limit: pageSize,
        offset: (page - 1) * pageSize,
        sort_by: nextSorting.sort_by,
        sort_order: nextSorting.sort_order,
      }
      if (nextFilters.search?.trim()) params.search = nextFilters.search.trim()
      if (nextFilters.status) params.status = nextFilters.status
      if (nextFilters.tenant_id) params.tenant_id = nextFilters.tenant_id
      if (nextFilters.min_questions !== undefined && nextFilters.min_questions !== null) params.min_questions = nextFilters.min_questions
      if (nextFilters.max_questions !== undefined && nextFilters.max_questions !== null) params.max_questions = nextFilters.max_questions
      if (nextFilters.date_range?.[0] && nextFilters.date_range?.[1]) {
        params.date_from = nextFilters.date_range[0].startOf('day').toISOString()
        params.date_to = nextFilters.date_range[1].endOf('day').toISOString()
      }

      const response = await platformQuizAPI.list(params)
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
      fetchQuizzes(1, pagination.pageSize, filters, sorting)
    }
  }, [])

  if (user?.role !== 'super_admin') {
    return (
      <div style={{ padding: 24 }}>
        <Alert message="Access denied" description="Only super admins can view platform quizzes." type="error" showIcon />
      </div>
    )
  }

  const statusColors = {
    draft: 'default',
    ready: 'success',
    archived: 'error',
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'Title',
      dataIndex: 'title',
      key: 'title',
      sorter: true,
      ellipsis: true,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      sorter: true,
      render: (value) => <Tag color={statusColors[value] || 'default'}>{value}</Tag>,
    },
    {
      title: 'Questions',
      dataIndex: 'question_count',
      key: 'question_count',
      width: 120,
      sorter: true,
    },
    {
      title: 'Tenant',
      dataIndex: 'tenant_name',
      key: 'tenant_name',
      sorter: true,
      ellipsis: true,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text>{record.tenant_name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>ID: {record.tenant_id}</Text>
        </Space>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      sorter: true,
      render: (value) => dayjs(value).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Updated',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 170,
      sorter: true,
      render: (value) => dayjs(value).format('YYYY-MM-DD HH:mm'),
    },
  ]

  const onApplyFilters = () => {
    setPagination((prev) => ({ ...prev, current: 1 }))
    fetchQuizzes(1, pagination.pageSize, filters, sorting)
  }

  const onResetFilters = () => {
    const resetFilters = {
      search: '',
      status: undefined,
      tenant_id: undefined,
      min_questions: undefined,
      max_questions: undefined,
      date_range: null,
    }
    const resetSorting = { sort_by: 'created_at', sort_order: 'desc' }
    setFilters(resetFilters)
    setSorting(resetSorting)
    setPagination((prev) => ({ ...prev, current: 1 }))
    fetchQuizzes(1, pagination.pageSize, resetFilters, resetSorting)
  }

  const handleTableChange = (pager, _, sorter) => {
    const nextPage = pager.current || 1
    const nextPageSize = pager.pageSize || 20

    let nextSorting = sorting
    if (sorter?.field) {
      nextSorting = {
        sort_by: sorter.field,
        sort_order: sorter.order === 'ascend' ? 'asc' : 'desc',
      }
      setSorting(nextSorting)
    }

    setPagination({ current: nextPage, pageSize: nextPageSize })
    fetchQuizzes(nextPage, nextPageSize, filters, nextSorting)
  }

  return (
    <div className="admin-page" style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>Platform Quizzes</Title>
        <Text type="secondary">Super admin view of all quizzes across tenants with filtering and sorting</Text>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} className="admin-action-row">
          <Col xs={24} md={8}>
            <Input
              placeholder="Search by quiz title"
              className="admin-control"
              value={filters.search}
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
              onPressEnter={onApplyFilters}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              placeholder="Status"
              allowClear
              className="admin-control"
              value={filters.status}
              onChange={(value) => setFilters((prev) => ({ ...prev, status: value }))}
              options={[
                { label: 'draft', value: 'draft' },
                { label: 'ready', value: 'ready' },
                { label: 'archived', value: 'archived' },
              ]}
            />
          </Col>
          <Col xs={24} md={4}>
            <InputNumber
              placeholder="Tenant ID"
              className="admin-control"
              style={{ width: '100%' }}
              min={1}
              value={filters.tenant_id}
              onChange={(value) => setFilters((prev) => ({ ...prev, tenant_id: value }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <InputNumber
              placeholder="Min Qs"
              className="admin-control"
              style={{ width: '100%' }}
              min={0}
              value={filters.min_questions}
              onChange={(value) => setFilters((prev) => ({ ...prev, min_questions: value }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <InputNumber
              placeholder="Max Qs"
              className="admin-control"
              style={{ width: '100%' }}
              min={0}
              value={filters.max_questions}
              onChange={(value) => setFilters((prev) => ({ ...prev, max_questions: value }))}
            />
          </Col>
          <Col xs={24} md={8}>
            <RangePicker
              className="admin-control"
              value={filters.date_range}
              onChange={(value) => setFilters((prev) => ({ ...prev, date_range: value }))}
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
          scroll={{ x: 1200 }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50', '100'],
            showTotal: (value) => `Total ${value} quizzes`,
          }}
          onChange={handleTableChange}
        />
      </Card>
    </div>
  )
}

export default PlatformQuizzes
