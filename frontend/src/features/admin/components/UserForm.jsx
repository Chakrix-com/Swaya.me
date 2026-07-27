import { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useTranslation } from 'react-i18next';
import { Form, Input, Switch, message, theme } from 'antd';
import { createUser, updateUser } from '../../../store/slices/userManagementSlice';
import SafeModal from '../../../components/SafeModal';

const UserForm = ({ visible, user, onSuccess, onCancel }) => {
  const { t } = useTranslation();
  const dispatch = useDispatch();
  const { loading } = useSelector((state) => state.userManagement);
  const { user: currentUser } = useSelector((state) => state.auth);
  const [form] = Form.useForm();
  const { token } = theme.useToken();

  const arrowSvg = `data:image/svg+xml,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="${token.colorPrimary}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>`
  )}`;

  const nativeSelectStyle = {
    boxSizing: 'border-box',
    width: '100%',
    height: 32,
    lineHeight: '30px',
    borderRadius: token.borderRadius,
    border: `1px solid ${token.colorBorder}`,
    background: `${token.colorBgContainer} url("${arrowSvg}") no-repeat right 8px center / 10px`,
    color: token.colorText,
    padding: '0 28px 0 11px',
    fontFamily: 'inherit',
    fontSize: 14,
    cursor: 'pointer',
    appearance: 'none',
    WebkitAppearance: 'none',
    MozAppearance: 'none',
  };

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
        tier: user.tier ? user.tier.toLowerCase() : undefined,
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
        const originalTier = user.tier ? user.tier.toLowerCase() : undefined;
        const updates = {
          full_name: values.full_name,
          role: values.role,
          is_active: values.is_active,
          ...(isSuperAdmin && values.tier && values.tier !== originalTier ? { tier: values.tier } : {}),
        };

        await dispatch(updateUser({ userId: user.id, updates })).unwrap();
        message.success(t('admin.userForm.userUpdatedSuccess'));
      } else {
        // Create new user
        await dispatch(createUser(values)).unwrap();
        message.success(t('admin.userForm.userCreatedSuccess'));
      }

      form.resetFields();
      onSuccess();
    } catch (err) {
      if (err.errors) {
        // Validation error from form
        return;
      }
      message.error(err.message || t('admin.userForm.userActionFailed', { action: isEditing ? t('common.update') : t('common.create') }));
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
        { value: 'super_admin', label: t('admin.userForm.roleSuperAdmin') },
        { value: 'admin', label: t('admin.userForm.roleAdmin') },
        { value: 'user', label: t('admin.userForm.roleUser') },
        { value: 'viewer', label: t('admin.userForm.roleViewer') },
      ];
    }

    // Regular admin can only assign user and viewer roles
    return [
      { value: 'user', label: t('admin.userForm.roleUser') },
      { value: 'viewer', label: t('admin.userForm.roleViewer') },
    ];
  };

  return (
    <SafeModal
      title={isEditing ? t('admin.userForm.editUserTitle') : t('admin.userForm.createUserTitle')}
      open={visible}
      onOk={handleSubmit}
      onCancel={handleCancel}
      confirmLoading={loading}
      okText={isEditing ? t('common.update') : t('common.create')}
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
          label={t('admin.userForm.email')}
          name="email"
          rules={[
            { required: true, message: t('admin.userForm.emailRequired') },
            { type: 'email', message: t('admin.userForm.emailInvalid') },
          ]}
        >
          <Input
            placeholder={t('admin.userForm.emailPlaceholder')}
            disabled={isEditing} // Can't change email when editing
          />
        </Form.Item>

        {!isEditing && (
          <Form.Item
            label={t('admin.userForm.password')}
            name="password"
            rules={[
              { required: true, message: t('admin.userForm.passwordRequired') },
              { min: 8, message: t('admin.userForm.passwordMinLength') },
            ]}
          >
            <Input.Password placeholder={t('admin.userForm.passwordPlaceholder')} />
          </Form.Item>
        )}

        <Form.Item
          label={t('admin.userForm.fullName')}
          name="full_name"
          rules={[{ required: false }]}
        >
          <Input placeholder={t('admin.userForm.fullNamePlaceholder')} />
        </Form.Item>

        <Form.Item
          label={t('admin.userForm.role')}
          name="role"
          rules={[{ required: true, message: t('admin.userForm.roleRequired') }]}
        >
          <select style={nativeSelectStyle}>
            {getAvailableRoles().map((role) => (
              <option key={role.value} value={role.value}>
                {role.label}
              </option>
            ))}
          </select>
        </Form.Item>

        {isSuperAdmin && isEditing && (
          <Form.Item label={t('admin.users.tier')} name="tier">
            <select style={nativeSelectStyle}>
              <option value="free">{t('admin.orgs.tierFree')}</option>
              <option value="basic">{t('admin.orgs.tierBasic')}</option>
              <option value="pro">{t('admin.orgs.tierPro')}</option>
              <option value="enterprise">{t('admin.orgs.tierEnterprise')}</option>
            </select>
          </Form.Item>
        )}

        <Form.Item
          label={t('admin.userForm.active')}
          name="is_active"
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>
      </Form>
    </SafeModal>
  );
};

export default UserForm;
