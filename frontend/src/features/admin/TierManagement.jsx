import { useEffect, useState } from 'react'
import { Alert, Button, Card, Form, Input, InputNumber, Space, Table, Tag, Typography, message } from 'antd'
import SafeModal from '../../components/SafeModal'
import { EditOutlined } from '@ant-design/icons'
import { useSelector } from 'react-redux'
import { useTranslation } from 'react-i18next'
import { tierConfigAPI } from '../../services/api'
import './Admin.css'

const { Title, Text } = Typography

function TierManagement() {
  const { t } = useTranslation()
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
      message.error(error.response?.data?.detail || t('admin.tierManagementPage.loadFailed'))
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
        <Alert message={t('admin.tierManagementPage.accessDenied')} description={t('admin.tierManagementPage.accessDeniedDescription')} type="error" showIcon />
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
      message.success(t('admin.tierManagementPage.updatedTier', { tier: selected.tier }))
      setIsModalOpen(false)
      setSelected(null)
      form.resetFields()
      loadConfigs()
    } catch (error) {
      if (!error?.errorFields) {
          message.error(error.response?.data?.detail || t('admin.tierManagementPage.updateFailed'))
      }
    } finally {
      setSaving(false)
    }
  }

  const columns = [
    {
      title: t('admin.tierManagementPage.columns.tier'),
      dataIndex: 'tier',
      key: 'tier',
      width: 140,
      render: (value) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: t('admin.tierManagementPage.columns.maxParticipants'),
      dataIndex: 'max_participants',
      key: 'max_participants',
      width: 160,
    },
    {
      title: t('admin.tierManagementPage.columns.maxQuestions'),
      dataIndex: 'max_questions',
      key: 'max_questions',
      width: 140,
    },
    {
      title: t('admin.tierManagementPage.columns.maxConcurrentEvents'),
      dataIndex: 'max_concurrent_events',
      key: 'max_concurrent_events',
      width: 200,
    },
    {
      title: t('admin.tierManagementPage.columns.features'),
      dataIndex: 'features',
      key: 'features',
      render: (value) => (
        <Space wrap>
          {(value || []).length === 0 ? <Text type="secondary">{t('admin.tierManagementPage.none')}</Text> : value.map((feature) => <Tag key={feature}>{feature}</Tag>)}
        </Space>
      ),
    },
    {
      title: t('admin.tierManagementPage.columns.actions'),
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Button icon={<EditOutlined />} onClick={() => openEditModal(record)}>
          {t('common.edit')}
        </Button>
      ),
    },
  ]

  return (
    <div className="admin-page" style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>{t('admin.tierManagement')}</Title>
        <Text type="secondary">{t('admin.tierManagementPage.description')}</Text>
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

      <SafeModal
        title={selected ? t('admin.tierManagementPage.editTierWithName', { tier: selected.tier }) : t('admin.tierManagementPage.editTier')}
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false)
          setSelected(null)
          form.resetFields()
        }}
        onOk={handleSave}
        okText={t('common.save')}
        confirmLoading={saving}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="max_participants" label={t('admin.tierManagementPage.columns.maxParticipants')} rules={[{ required: true }]}>
            <InputNumber min={1} max={1000000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="max_questions" label={t('admin.tierManagementPage.columns.maxQuestions')} rules={[{ required: true }]}>
            <InputNumber min={1} max={100000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="max_concurrent_events" label={t('admin.tierManagementPage.columns.maxConcurrentEvents')} rules={[{ required: true }]}>
            <InputNumber min={1} max={10000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="features"
            label={t('admin.tierManagementPage.featuresCommaSeparated')}
            extra={t('admin.tierManagementPage.featuresExample')}
          >
            <Input placeholder={t('admin.tierManagementPage.featuresPlaceholder')} />
          </Form.Item>
        </Form>
      </SafeModal>
    </div>
  )
}

export default TierManagement
