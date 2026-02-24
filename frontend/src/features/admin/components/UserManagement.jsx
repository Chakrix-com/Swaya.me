import { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
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
  Dropdown
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  MoreOutlined,
  UserOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import {
  fetchUsers,
  deleteUser,
  clearError
} from '../../../store/slices/userManagementSlice';
import UserForm from './UserForm';

const { Search } = Input;
const { Option } = Select;

const UserManagement = () => {
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
      title: 'Delete User',
      content: `Are you sure you want to delete ${userName}? This will deactivate their account.`,
      okText: 'Delete',
      okType: 'danger',
      onOk: async () => {
        try {
          await dispatch(deleteUser(userId)).unwrap();
          message.success('User deleted successfully');
          loadUsers();
        } catch (err) {
          message.error(err.message || 'Failed to delete user');
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

  const getRoleBadge = (role) => {
    const roleColors = {
      super_admin: 'purple',
      admin: 'blue',
      user: 'green',
      viewer: 'default',
    };

    const roleLabels = {
      super_admin: 'Super Admin',
      admin: 'Admin',
      user: 'User',
      viewer: 'Viewer',
    };

    return <Tag color={roleColors[role]}>{roleLabels[role]}</Tag>;
  };

  const getStatusBadge = (isActive) => {
    return isActive ? (
      <Tag icon={<CheckCircleOutlined />} color="success">
        Active
      </Tag>
    ) : (
      <Tag icon={<CloseCircleOutlined />} color="error">
        Inactive
      </Tag>
    );
  };

  const getActionMenu = (record) => ({
    items: [
      {
        key: 'edit',
        label: 'Edit User',
        icon: <EditOutlined />,
        onClick: () => handleEditUser(record),
      },
      {
        key: 'delete',
        label: 'Delete User',
        icon: <DeleteOutlined />,
        danger: true,
        onClick: () => handleDeleteUser(record.id, record.email),
        disabled: record.id === currentUser?.id, // Can't delete yourself
      },
    ],
  });

  const columns = [
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
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
      title: 'Role',
      dataIndex: 'role',
      key: 'role',
      render: getRoleBadge,
      filters: [
        { text: 'Super Admin', value: 'super_admin' },
        { text: 'Admin', value: 'admin' },
        { text: 'User', value: 'user' },
        { text: 'Viewer', value: 'viewer' },
      ],
      onFilter: (value, record) => record.role === value,
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: getStatusBadge,
      filters: [
        { text: 'Active', value: true },
        { text: 'Inactive', value: false },
      ],
      onFilter: (value, record) => record.is_active === value,
    },
    {
      title: 'Last Login',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (date) =>
        date ? new Date(date).toLocaleDateString() + ' ' + new Date(date).toLocaleTimeString() : 'Never',
    },
    {
      title: 'Login Count',
      dataIndex: 'login_count',
      key: 'login_count',
      align: 'center',
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Actions',
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
    <div style={{ padding: 24 }}>
      <Card>
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col flex="auto">
            <Space size="middle">
              <Search
                placeholder="Search by email or name"
                allowClear
                enterButton={<SearchOutlined />}
                onSearch={handleSearch}
                style={{ width: 300 }}
              />
              <Select
                placeholder="Filter by Role"
                allowClear
                style={{ width: 150 }}
                onChange={handleRoleFilterChange}
              >
                <Option value="super_admin">Super Admin</Option>
                <Option value="admin">Admin</Option>
                <Option value="user">User</Option>
                <Option value="viewer">Viewer</Option>
              </Select>
              <Select
                placeholder="Filter by Status"
                allowClear
                style={{ width: 150 }}
                onChange={handleStatusFilterChange}
              >
                <Option value={true}>Active</Option>
                <Option value={false}>Inactive</Option>
              </Select>
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateUser}
            >
              Create User
            </Button>
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
            showTotal: (total) => `Total ${total} users`,
          }}
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
