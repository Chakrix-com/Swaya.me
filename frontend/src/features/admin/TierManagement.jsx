import { useEffect, useState } from 'react'
import { Alert, Button, Card, Form, Input, InputNumber, Modal, Space, Table, Tag, Typography, message } from 'antd'
import { EditOutlined } from '@ant-design/icons'
import { useSelector } from 'react-redux'
import { tierConfigAPI } from '../../services/api'
import './Admin.css'

const { Title, Text } = Typography

function TierManagement() {
  const { user } = useSelector((state) => state.auth)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [items, setItems] = useState([])
  const [selected, setSelected] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadConfigs = async () => {
    setLoading(true)
    try {
      const response = await tierConfigAPI.list()
      setItems(response.data || [])
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to load tier configurations')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (user?.role === 'super_admin') {
      loadConfigs()
    }
  }, [])

  if (user?.role !== 'super_admin') {
    return (
      <div style={{ padding: 24 }}>
        <Alert message="Access denied" description="Only super admins can manage tiers." type="error" showIcon />
      </div>
    )
  }

  const openEditModal = (record) => {
    setSelected(record)
    form.setFieldsValue({
      max_participants: record.max_participants,
      max_questions: record.max_questions,
      max_concurrent_events: record.max_concurrent_events,
      features: (record.features || []).join(', '),
    })
    setIsModalOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      const payload = {
        max_participants: values.max_participants,
        max_questions: values.max_questions,
        max_concurrent_events: values.max_concurrent_events,
        features: String(values.features || '')
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
      }

      setSaving(true)
      await tierConfigAPI.update(selected.tier, payload)
      message.success(`Updated ${selected.tier} tier`)
      setIsModalOpen(false)
      setSelected(null)
      form.resetFields()
      loadConfigs()
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error.response?.data?.detail || 'Failed to update tier configuration')
      }
    } finally {
      setSaving(false)
    }
  }

  const columns = [
    {
      title: 'Tier',
      dataIndex: 'tier',
      key: 'tier',
      width: 140,
      render: (value) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: 'Max Participants',
      dataIndex: 'max_participants',
      key: 'max_participants',
      width: 160,
    },
    {
      title: 'Max Questions',
      dataIndex: 'max_questions',
      key: 'max_questions',
      width: 140,
    },
    {
      title: 'Max Concurrent Events',
      dataIndex: 'max_concurrent_events',
      key: 'max_concurrent_events',
      width: 200,
    },
    {
      title: 'Features',
      dataIndex: 'features',
      key: 'features',
      render: (value) => (
        <Space wrap>
          {(value || []).length === 0 ? <Text type="secondary">None</Text> : value.map((feature) => <Tag key={feature}>{feature}</Tag>)}
        </Space>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Button icon={<EditOutlined />} onClick={() => openEditModal(record)}>
          Edit
        </Button>
      ),
    },
  ]

  return (
    <div className="admin-page" style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>Tier Management</Title>
        <Text type="secondary">Manage platform-wide limits and feature sets for each tier.</Text>
      </div>

      <Card>
        <Table
          rowKey="tier"
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={false}
          scroll={{ x: 1000 }}
        />
      </Card>

      <Modal
        title={selected ? `Edit ${selected.tier} tier` : 'Edit Tier'}
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false)
          setSelected(null)
          form.resetFields()
        }}
        onOk={handleSave}
        okText="Save"
        confirmLoading={saving}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="max_participants" label="Max Participants" rules={[{ required: true }]}>
            <InputNumber min={1} max={1000000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="max_questions" label="Max Questions" rules={[{ required: true }]}>
            <InputNumber min={1} max={100000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="max_concurrent_events" label="Max Concurrent Events" rules={[{ required: true }]}>
            <InputNumber min={1} max={10000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="features"
            label="Features (comma-separated)"
            extra="Example: advanced_reports,priority_support,custom_branding"
          >
            <Input placeholder="feature_one,feature_two" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default TierManagement
