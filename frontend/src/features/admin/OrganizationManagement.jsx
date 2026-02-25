import { useState, useEffect } from 'react'
import {
  Table, Button, Modal, Form, Input, Select, message, Space, Tag, Progress, Card, Statistic, Row, Col
} from 'antd'
import {
  PlusOutlined, EditOutlined, TeamOutlined, UserOutlined, SettingOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { organizationAPI } from '../../services/api'

const { Option } = Select

function OrganizationManagement() {
  const { t } = useTranslation()
  const [organizations, setOrganizations] = useState([])
  const [loading, setLoading] = useState(false)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [adminModalVisible, setAdminModalVisible] = useState(false)
  const [selectedOrg, setSelectedOrg] = useState(null)
  const [admins, setAdmins] = useState([])
  const [form] = Form.useForm()
  const [adminForm] = Form.useForm()

  useEffect(() => {
    fetchOrganizations()
  }, [])

  const fetchOrganizations = async () => {
    setLoading(true)
    try {
      const response = await organizationAPI.listOrganizations()
      setOrganizations(response.data)
    } catch (error) {
      message.error(t('admin.orgs.loadOrgsError'))
    } finally {
      setLoading(false)
    }
  }

  const handleCreateOrganization = async (values) => {
    try {
      await organizationAPI.createOrganization(values)
      message.success(t('admin.orgs.orgCreatedSuccess'))
      setCreateModalVisible(false)
      form.resetFields()
      fetchOrganizations()
    } catch (error) {
      message.error(error.response?.data?.detail || t('admin.orgs.orgCreatedError'))
    }
  }

  const handleViewAdmins = async (org) => {
    setSelectedOrg(org)
    setLoading(true)
    try {
      const response = await organizationAPI.listAdmins(org.id)
      setAdmins(response.data)
      setAdminModalVisible(true)
    } catch (error) {
      message.error(t('admin.orgs.loadAdminsError'))
    } finally {
      setLoading(false)
    }
  }

  const handleCreateAdmin = async (values) => {
    try {
      await organizationAPI.createAdmin({
        ...values,
        tenant_id: selectedOrg.id
      })
      message.success(t('admin.orgs.adminCreatedSuccess'))
      adminForm.resetFields()
      // Refresh admin list
      const response = await organizationAPI.listAdmins(selectedOrg.id)
      setAdmins(response.data)
      fetchOrganizations() // Refresh org list to update counts
    } catch (error) {
      message.error(error.response?.data?.detail || t('admin.orgs.adminCreatedError'))
    }
  }

  const handleUpdateQuota = async (adminId, newQuota) => {
    try {
      await organizationAPI.updateAdminQuota(adminId, newQuota)
      message.success(t('admin.orgs.quotaUpdatedSuccess'))
      // Refresh admin list
      const response = await organizationAPI.listAdmins(selectedOrg.id)
      setAdmins(response.data)
    } catch (error) {
      message.error(t('admin.orgs.quotaUpdatedError'))
    }
  }

  const orgColumns = [
    {
      title: t('admin.orgs.id'),
      dataIndex: 'id',
      key: 'id',
      width: 60
    },
    {
      title: t('admin.orgs.organization'),
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <>
          <div style={{ fontWeight: 500 }}>{text}</div>
          <div style={{ fontSize: 12, color: '#888' }}>{record.slug}</div>
        </>
      )
    },
    {
      title: t('admin.orgs.tier'),
      dataIndex: 'tier',
      key: 'tier',
      render: (tier) => {
        const colors = {
          free: 'default',
          basic: 'blue',
          pro: 'purple',
          enterprise: 'gold'
        }
        return <Tag color={colors[tier] || 'default'}>{tier.toUpperCase()}</Tag>
      }
    },
    {
      title: t('admin.orgs.users'),
      dataIndex: 'user_count',
      key: 'user_count',
      render: (count) => (
        <Tag icon={<UserOutlined />} color="blue">{count}</Tag>
      )
    },
    {
      title: t('admin.orgs.admins'),
      dataIndex: 'admin_count',
      key: 'admin_count',
      render: (count) => (
        <Tag icon={<TeamOutlined />} color="green">{count}</Tag>
      )
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? 'Active' : 'Inactive'}
        </Tag>
      )
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button 
            type="link" 
            icon={<TeamOutlined />}
            onClick={() => handleViewAdmins(record)}
          >
            {t('admin.orgs.manageAdmins')}
          </Button>
        </Space>
      )
    }
  ]

  const adminColumns = [
    {
      title: t('admin.orgs.email'),
      dataIndex: 'email',
      key: 'email'
    },
    {
      title: t('admin.orgs.name'),
      dataIndex: 'full_name',
      key: 'full_name'
    },
    {
      title: t('admin.orgs.quota'),
      key: 'quota',
      render: (_, record) => {
        const percentage = record.user_quota 
          ? Math.round((record.quota_usage / record.user_quota) * 100) 
          : 0
        return (
          <div style={{ minWidth: 150 }}>
            <div style={{ marginBottom: 4 }}>
              {record.quota_usage} / {record.user_quota} users
            </div>
            <Progress 
              percent={percentage} 
              status={percentage >= 100 ? 'exception' : 'normal'}
              size="small"
            />
          </div>
        )
      }
    },
    {
      title: t('admin.orgs.status'),
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? t('admin.orgs.active') : t('admin.orgs.inactive')}
        </Tag>
      )
    },
    {
      title: t('admin.orgs.actions'),
      key: 'actions',
      render: (_, record) => (
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => {
            Modal.confirm({
              title: t('admin.orgs.updateQuotaTitle'),
              content: (
                <Form
                  id="quota-form"
                  onFinish={(values) => {
                    handleUpdateQuota(record.id, values.quota)
                    Modal.destroyAll()
                  }}
                  initialValues={{ quota: record.user_quota }}
                >
                  <Form.Item
                    name="quota"
                    label={t('admin.orgs.newQuota')}
                    rules={[{ required: true, message: t('admin.orgs.quotaRequired') }]}
                  >
                    <Input type="number" min={1} />
                  </Form.Item>
                </Form>
              ),
              onOk: () => {
                document.getElementById('quota-form').dispatchEvent(
                  new Event('submit', { cancelable: true, bubbles: true })
                )
              }
            })
          }}
        >
          {t('admin.orgs.updateQuota')}
        </Button>
      )
    }
  ]

  // Calculate summary stats
  const totalOrgs = organizations.length
  const totalUsers = organizations.reduce((sum, org) => sum + org.user_count, 0)
  const totalAdmins = organizations.reduce((sum, org) => sum + org.admin_count, 0)
  const activeOrgs = organizations.filter(org => org.is_active).length

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <h1>{t('admin.orgs.orgManagement')}</h1>
        <p style={{ color: '#666' }}>{t('admin.orgs.orgManagementDesc')}</p>
      </div>

      {/* Summary Cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('admin.orgs.totalOrganizations')}
              value={totalOrgs}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('admin.orgs.activeOrganizations')}
              value={activeOrgs}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('admin.orgs.totalAdmins')}
              value={totalAdmins}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('admin.orgs.totalUsers')}
              value={totalUsers}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Organizations Table */}
      <Card
        title="Organizations"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            {t('admin.orgs.createOrg')}
          </Button>
        }
      >
        <Table
          columns={orgColumns}
          dataSource={organizations}
          loading={loading}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Create Organization Modal */}
      <Modal
        title={t('admin.orgs.createOrg')}
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false)
          form.resetFields()
        }}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateOrganization}
        >
          <Form.Item
            name="name"
            label={t('admin.orgs.orgName')}
            rules={[{ required: true, message: t('admin.orgs.orgNameRequired') }]}
          >
            <Input placeholder="e.g., Acme Corporation" />
          </Form.Item>

          <Form.Item
            name="slug"
            label={t('admin.orgs.slug')}
            help={t('admin.orgs.slugPlaceholder')}
          >
            <Input placeholder="e.g., acme-corp" />
          </Form.Item>

          <Form.Item
            name="tier"
            label={t('admin.orgs.subscriptionTier')}
            initialValue="free"
            rules={[{ required: true }]}
          >
            <Select>
              <Option value="free">{t('admin.orgs.tierFree')}</Option>
              <Option value="basic">{t('admin.orgs.tierBasic')}</Option>
              <Option value="pro">{t('admin.orgs.tierPro')}</Option>
              <Option value="enterprise">{t('admin.orgs.tierEnterprise')}</Option>
            </Select>
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {t('admin.orgs.create')}
              </Button>
              <Button onClick={() => {
                setCreateModalVisible(false)
                form.resetFields()
              }}>
                {t('admin.orgs.cancel')}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Manage Admins Modal */}
      <Modal
        title={`Admins - ${selectedOrg?.name || ''}`}
        open={adminModalVisible}
        onCancel={() => {
          setAdminModalVisible(false)
          setSelectedOrg(null)
          setAdmins([])
          adminForm.resetFields()
        }}
        width={900}
        footer={null}
      >
        <Card
          size="small"
          title="Create Admin User"
          style={{ marginBottom: 16 }}
        >
          <Form
            form={adminForm}
            layout="vertical"
            onFinish={handleCreateAdmin}
          >
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="email"
                  label={t('admin.orgs.email')}
                  rules={[
                    { required: true, message: 'Please enter email' },
                    { type: 'email', message: 'Invalid email' }
                  ]}
                >
                  <Input />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="full_name"
                  label={t('admin.orgs.fullName')}
                >
                  <Input />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="password"
                  label={t('admin.orgs.password')}
                  rules={[
                    { required: true, message: 'Please enter password' },
                    { min: 8, message: t('admin.orgs.passwordMinLength') }
                  ]}
                >
                  <Input.Password />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="user_quota"
                  label={t('admin.orgs.userQuota')}
                  initialValue={10}
                  rules={[{ required: true }]}
                >
                  <Input type="number" min={1} addonAfter="users" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item>
              <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>
                {t('admin.orgs.createAdmin')}
              </Button>
            </Form.Item>
          </Form>
        </Card>

        <Table
          columns={adminColumns}
          dataSource={admins}
          rowKey="id"
          pagination={false}
        />
      </Modal>
    </div>
  )
}

export default OrganizationManagement
