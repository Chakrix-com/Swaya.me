import { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Modal, Form, Input, Select, Switch, message } from 'antd';
import { createUser, updateUser } from '../../../store/slices/userManagementSlice';

const { Option } = Select;

const UserForm = ({ visible, user, onSuccess, onCancel }) => {
  const dispatch = useDispatch();
  const { loading } = useSelector((state) => state.userManagement);
  const { user: currentUser } = useSelector((state) => state.auth);
  const [form] = Form.useForm();

  const isSuperAdmin = currentUser?.role === 'super_admin';
  const isEditing = !!user;

  useEffect(() => {
    if (visible && user) {
      // Populate form when editing
      form.setFieldsValue({
        email: user.email,
        full_name: user.full_name,
        role: user.role,
        is_active: user.is_active,
      });
    } else if (visible) {
      // Reset form when creating
      form.resetFields();
      form.setFieldsValue({
        role: 'user',
        is_active: true,
      });
    }
  }, [visible, user, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (isEditing) {
        // Update existing user
        const updates = {
          full_name: values.full_name,
          role: values.role,
          is_active: values.is_active,
        };

        await dispatch(updateUser({ userId: user.id, updates })).unwrap();
        message.success('User updated successfully');
      } else {
        // Create new user
        await dispatch(createUser(values)).unwrap();
        message.success('User created successfully');
      }

      form.resetFields();
      onSuccess();
    } catch (err) {
      if (err.errors) {
        // Validation error from form
        return;
      }
      message.error(err.message || `Failed to ${isEditing ? 'update' : 'create'} user`);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  const getAvailableRoles = () => {
    // Super admin can assign any role
    if (isSuperAdmin) {
      return [
        { value: 'super_admin', label: 'Super Admin' },
        { value: 'admin', label: 'Admin' },
        { value: 'user', label: 'User' },
        { value: 'viewer', label: 'Viewer' },
      ];
    }

    // Regular admin can only assign user and viewer roles
    return [
      { value: 'user', label: 'User' },
      { value: 'viewer', label: 'Viewer' },
    ];
  };

  return (
    <Modal
      title={isEditing ? 'Edit User' : 'Create User'}
      open={visible}
      onOk={handleSubmit}
      onCancel={handleCancel}
      confirmLoading={loading}
      okText={isEditing ? 'Update' : 'Create'}
      width={500}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          role: 'user',
          is_active: true,
        }}
      >
        <Form.Item
          label="Email"
          name="email"
          rules={[
            { required: true, message: 'Please enter email' },
            { type: 'email', message: 'Please enter a valid email' },
          ]}
        >
          <Input
            placeholder="user@example.com"
            disabled={isEditing} // Can't change email when editing
          />
        </Form.Item>

        {!isEditing && (
          <Form.Item
            label="Password"
            name="password"
            rules={[
              { required: true, message: 'Please enter password' },
              { min: 8, message: 'Password must be at least 8 characters' },
            ]}
          >
            <Input.Password placeholder="Enter password" />
          </Form.Item>
        )}

        <Form.Item
          label="Full Name"
          name="full_name"
          rules={[{ required: false }]}
        >
          <Input placeholder="Enter full name (optional)" />
        </Form.Item>

        <Form.Item
          label="Role"
          name="role"
          rules={[{ required: true, message: 'Please select a role' }]}
        >
          <Select placeholder="Select role">
            {getAvailableRoles().map((role) => (
              <Option key={role.value} value={role.value}>
                {role.label}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          label="Active"
          name="is_active"
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default UserForm;
