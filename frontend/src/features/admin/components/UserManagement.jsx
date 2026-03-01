import { useState, useEffect, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useTranslation } from 'react-i18next';
import {
  Table,
  Button,
  Input,
  Select,
  Tag,
  Space,
  Modal,
  message,
  Card,
  Row,
  Col,
  Tooltip,
  Dropdown,
  Statistic
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  MoreOutlined,
  UserOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  TeamOutlined,
  CrownOutlined,
  SafetyOutlined,
  EyeOutlined,
  DownloadOutlined
} from '@ant-design/icons';
import * as XLSX from 'xlsx';
import {
  fetchUsers,
  deleteUser,
  clearError
} from '../../../store/slices/userManagementSlice';
import UserForm from './UserForm';
import '../Admin.css';

const { Search } = Input;
const { Option } = Select;

const UserManagement = () => {
  const { t } = useTranslation();
  const dispatch = useDispatch();
  const { users, total, page, perPage, pages, loading, error } = useSelector(
    (state) => state.userManagement
  );
  const { user: currentUser } = useSelector((state) => state.auth);

  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState(null);
  const [statusFilter, setStatusFilter] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [isFormVisible, setIsFormVisible] = useState(false);
  const [editingUser, setEditingUser] = useState(null);

  const isSuperAdmin = currentUser?.role === 'super_admin';

  useEffect(() => {
    loadUsers();
  }, [currentPage, searchText, roleFilter, statusFilter]);

  useEffect(() => {
    if (error) {
      message.error(error);
      dispatch(clearError());
    }
  }, [error]);

  const loadUsers = () => {
    const params = {
      page: currentPage,
      per_page: perPage,
    };

    if (searchText) params.search = searchText;
    if (roleFilter) params.role = roleFilter;
    if (statusFilter !== null) params.is_active = statusFilter;

    dispatch(fetchUsers(params));
  };

  const handleSearch = (value) => {
    setSearchText(value);
    setCurrentPage(1);
  };

  const handleRoleFilterChange = (value) => {
    setRoleFilter(value);
    setCurrentPage(1);
  };

  const handleStatusFilterChange = (value) => {
    setStatusFilter(value);
    setCurrentPage(1);
  };

  const handleCreateUser = () => {
    setEditingUser(null);
    setIsFormVisible(true);
  };

  const handleEditUser = (user) => {
    setEditingUser(user);
    setIsFormVisible(true);
  };

  const handleDeleteUser = (userId, userName) => {
    Modal.confirm({
      title: t('admin.users.deleteUser'),
      content: t('admin.users.deleteConfirm', { userName }),
      okText: t('admin.users.delete'),
      okType: 'danger',
      onOk: async () => {
        try {
          await dispatch(deleteUser(userId)).unwrap();
          message.success(t('admin.users.userDeletedSuccess'));
          loadUsers();
        } catch (err) {
          message.error(err.message || t('admin.users.userDeletedError'));
        }
      },
    });
  };

  const handleFormSuccess = () => {
    setIsFormVisible(false);
    setEditingUser(null);
    loadUsers();
  };

  const handleFormCancel = () => {
    setIsFormVisible(false);
    setEditingUser(null);
  };

  const handleExportToExcel = () => {
    try {
      // Prepare data for export
      const exportData = users.map(user => ({
        'Email': user.email,
        'Full Name': user.full_name || '',
        'Role': {
          super_admin: t('admin.users.superAdmin'),
          admin: t('admin.users.admin'),
          user: t('admin.users.user'),
          viewer: t('admin.users.viewer'),
        }[user.role] || user.role,
        'Status': user.is_active ? t('admin.users.active') : t('admin.users.inactive'),
        'Login Count': user.login_count || 0,
        'Last Login': user.last_login_at 
          ? new Date(user.last_login_at).toLocaleString() 
          : 'Never',
        'Created At': new Date(user.created_at).toLocaleString(),
        'Tenant': user.tenant_name || '',
      }));

      // Create workbook and worksheet
      const worksheet = XLSX.utils.json_to_sheet(exportData);
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, 'Users');

      // Auto-size columns
      const maxWidth = 50;
      const colWidths = Object.keys(exportData[0] || {}).map(key => ({
        wch: Math.min(
          maxWidth,
          Math.max(
            key.length,
            ...exportData.map(row => String(row[key] || '').length)
          )
        )
      }));
      worksheet['!cols'] = colWidths;

      // Generate filename with timestamp
      const timestamp = new Date().toISOString().split('T')[0];
      const filename = `users_export_${timestamp}.xlsx`;

      // Download file
      XLSX.writeFile(workbook, filename);
      
      message.success(t('admin.users.exportedUsers', { count: users.length, filename }));
    } catch (error) {
      console.error('Export error:', error);
      message.error(t('admin.users.exportError'));
    }
  };

  const getRoleBadge = (role) => {
    const roleColors = {
      super_admin: 'purple',
      admin: 'blue',
      user: 'green',
      viewer: 'default',
    };

    const roleLabels = {
      super_admin: t('admin.users.superAdmin'),
      admin: t('admin.users.admin'),
      user: t('admin.users.user'),
      viewer: t('admin.users.viewer'),
    };

    return <Tag color={roleColors[role]}>{roleLabels[role]}</Tag>;
  };

  const getStatusBadge = (isActive) => {
    return isActive ? (
      <Tag icon={<CheckCircleOutlined />} color="success">
        {t('admin.users.active')}
      </Tag>
    ) : (
      <Tag icon={<CloseCircleOutlined />} color="error">
        {t('admin.users.inactive')}
      </Tag>
    );
  };

  // Calculate statistics from users list
  const statistics = useMemo(() => {
    const stats = {
      total: users.length,
      byRole: {
        super_admin: 0,
        admin: 0,
        user: 0,
        viewer: 0
      },
      byStatus: {
        active: 0,
        inactive: 0
      }
    };

    users.forEach(user => {
      // Count by role
      if (user.role in stats.byRole) {
        stats.byRole[user.role]++;
      }
      // Count by status
      if (user.is_active) {
        stats.byStatus.active++;
      } else {
        stats.byStatus.inactive++;
      }
    });

    return stats;
  }, [users]);

  const getActionMenu = (record) => ({
    items: [
      {
        key: 'edit',
        label: t('admin.users.editUser'),
        icon: <EditOutlined />,
        onClick: () => handleEditUser(record),
      },
      {
        key: 'delete',
        label: t('admin.users.deleteUser'),
        icon: <DeleteOutlined />,
        danger: true,
        onClick: () => handleDeleteUser(record.id, record.email),
        disabled: record.id === currentUser?.id, // Can't delete yourself
      },
    ],
  });

  const columns = [
    {
      title: t('admin.users.email'),
      dataIndex: 'email',
      key: 'email',
      sorter: (a, b) => a.email.localeCompare(b.email),
      render: (email, record) => (
        <Space>
          <UserOutlined />
          <div>
            <div>{email}</div>
            {record.full_name && (
              <div style={{ fontSize: 12, color: '#888' }}>{record.full_name}</div>
            )}
          </div>
        </Space>
      ),
    },
    {
      title: t('admin.users.role'),
      dataIndex: 'role',
      key: 'role',
      sorter: (a, b) => a.role.localeCompare(b.role),
      render: getRoleBadge,
      filters: [
        { text: t('admin.users.superAdmin'), value: 'super_admin' },
        { text: t('admin.users.admin'), value: 'admin' },
        { text: t('admin.users.user'), value: 'user' },
        { text: t('admin.users.viewer'), value: 'viewer' },
      ],
      onFilter: (value, record) => record.role === value,
    },
    {
      title: t('admin.users.status'),
      dataIndex: 'is_active',
      key: 'is_active',
      sorter: (a, b) => (a.is_active === b.is_active ? 0 : a.is_active ? -1 : 1),
      render: getStatusBadge,
      filters: [
        { text: t('admin.users.active'), value: true },
        { text: t('admin.users.inactive'), value: false },
      ],
      onFilter: (value, record) => record.is_active === value,
    },
    {
      title: t('admin.users.lastLogin'),
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      sorter: (a, b) => {
        if (!a.last_login_at && !b.last_login_at) return 0;
        if (!a.last_login_at) return 1;
        if (!b.last_login_at) return -1;
        return new Date(a.last_login_at) - new Date(b.last_login_at);
      },
      render: (date) =>
        date ? new Date(date).toLocaleDateString() + ' ' + new Date(date).toLocaleTimeString() : 'Never',
    },
    {
      title: t('admin.users.loginCount'),
      dataIndex: 'login_count',
      key: 'login_count',
      align: 'center',
      sorter: (a, b) => a.login_count - b.login_count,
      defaultSortOrder: 'descend',
    },
    {
      title: t('admin.users.created'),
      dataIndex: 'created_at',
      key: 'created_at',
      sorter: (a, b) => new Date(a.created_at) - new Date(b.created_at),
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: t('admin.users.actions'),
      key: 'actions',
      align: 'center',
      render: (_, record) => (
        <Dropdown menu={getActionMenu(record)} trigger={['click']}>
          <Button type="text" icon={<MoreOutlined />} />
        </Dropdown>
      ),
    },
  ];

  return (
    <div className="admin-page" style={{ padding: 24 }}>
      {/* Statistics Cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('admin.users.totalUsers')}
              value={total}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('admin.users.activeUsers')}
              value={statistics.byStatus.active}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('admin.users.inactiveUsers')}
              value={statistics.byStatus.inactive}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('admin.users.currentPage')}
              value={users.length}
              suffix={`of ${total}`}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Role Distribution */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('admin.users.superAdmins')}
              value={statistics.byRole.super_admin}
              prefix={<CrownOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('admin.users.admins')}
              value={statistics.byRole.admin}
              prefix={<SafetyOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('admin.users.users')}
              value={statistics.byRole.user}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('admin.users.viewers')}
              value={statistics.byRole.viewer}
              prefix={<EyeOutlined />}
              valueStyle={{ color: '#8c8c8c' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Table Card */}
      <Card>
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }} className="admin-action-row">
          <Col xs={24} md="auto" flex="auto">
            <Space size="middle" wrap>
              <Search
                placeholder={t('admin.users.searchByEmailOrName')}
                allowClear
                enterButton={<SearchOutlined />}
                onSearch={handleSearch}
                className="admin-control"
                style={{ width: 300 }}
              />
              <Select
                placeholder={t('admin.users.filterByRole')}
                allowClear
                className="admin-control"
                style={{ width: 150 }}
                onChange={handleRoleFilterChange}
              >
                <Option value="super_admin">{t('admin.users.superAdmin')}</Option>
                <Option value="admin">{t('admin.users.admin')}</Option>
                <Option value="user">{t('admin.users.user')}</Option>
                <Option value="viewer">{t('admin.users.viewer')}</Option>
              </Select>
              <Select
                placeholder={t('admin.users.filterByStatus')}
                allowClear
                className="admin-control"
                style={{ width: 150 }}
                onChange={handleStatusFilterChange}
              >
                <Option value={true}>{t('admin.users.active')}</Option>
                <Option value={false}>{t('admin.users.inactive')}</Option>
              </Select>
            </Space>
          </Col>
          <Col xs={24} md="auto">
            <Space wrap>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExportToExcel}
                className="admin-control"
              >
                {t('admin.users.exportToExcel')}
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreateUser}
                className="admin-control"
              >
                {t('admin.users.createUser')}
              </Button>
            </Space>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={users}
          rowKey="id"
          loading={loading}
          pagination={{
            current: currentPage,
            pageSize: perPage,
            total: total,
            onChange: setCurrentPage,
            showSizeChanger: false,
            showTotal: (total) => t('admin.users.totalCount', { total }),
          }}
          scroll={{ x: true }}
        />
      </Card>

      <UserForm
        visible={isFormVisible}
        user={editingUser}
        onSuccess={handleFormSuccess}
        onCancel={handleFormCancel}
      />
    </div>
  );
};

export default UserManagement;
