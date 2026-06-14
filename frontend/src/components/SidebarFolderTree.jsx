import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import {
  Collapse, Tree, Spin, Button, Tooltip, Dropdown, Modal, Form, Input,
  TreeSelect, message, Switch, Select, List, Avatar, Space, Tag,
} from 'antd'
import {
  FolderFilled, FolderOpenOutlined, FolderAddOutlined, MoreOutlined,
  EditOutlined, ShareAltOutlined, DeleteOutlined, UserOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { setFolders } from '../store/quizSlice'
import { quizAPI, authAPI } from '../services/api'
import './SidebarFolderTree.css'

const ROOT_KEY = 'swayame-root'

function SidebarFolderTree() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const dispatch = useDispatch()
  const { folders } = useSelector(s => s.quiz)
  const { user } = useSelector(s => s.auth)
  const { t } = useTranslation()

  const selectedFolderId = useMemo(() => {
    const raw = searchParams.get('folder')
    return raw ? Number(raw) : undefined
  }, [searchParams])

  const fetchedRef = useRef(false)
  useEffect(() => {
    if (fetchedRef.current || folders.length > 0) return
    fetchedRef.current = true
    quizAPI.listFolders()
      .then(r => dispatch(setFolders(r.data || [])))
      .catch(() => {})
  }, [])

  const reloadFolders = async () => {
    try {
      const r = await quizAPI.listFolders()
      dispatch(setFolders(r.data || []))
    } catch (e) {}
  }

  // ── Create folder ──────────────────────────────────────────────────────────
  const [createForm] = Form.useForm()
  const [createOpen, setCreateOpen] = useState(false)
  const [createLoading, setCreateLoading] = useState(false)

  const openCreate = (parentId = null) => {
    createForm.setFieldsValue({ name: '', parent_id: parentId ?? undefined })
    setCreateOpen(true)
  }

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields()
      setCreateLoading(true)
      await quizAPI.createFolder({ name: values.name, parent_id: values.parent_id ?? null })
      message.success(t('dashboard.folderCreated'))
      setCreateOpen(false)
      createForm.resetFields()
      await reloadFolders()
    } catch (e) {
      if (e?.errorFields) return
      message.error(e?.response?.data?.detail || t('dashboard.folderCreateFailed'))
    } finally {
      setCreateLoading(false)
    }
  }

  // ── Rename / Move folder ───────────────────────────────────────────────────
  const [renameForm] = Form.useForm()
  const [renameTarget, setRenameTarget] = useState(null)
  const [renameOpen, setRenameOpen] = useState(false)
  const [renameLoading, setRenameLoading] = useState(false)

  const openRename = (rn) => {
    setRenameTarget(rn)
    renameForm.setFieldsValue({ name: rn.name, parent_id: rn.parent_id ?? undefined })
    setRenameOpen(true)
  }

  const handleRename = async () => {
    try {
      const values = await renameForm.validateFields()
      setRenameLoading(true)
      await quizAPI.updateFolder(renameTarget.id, {
        name: values.name,
        parent_id: values.parent_id ?? null,
      })
      message.success(t('dashboard.folderUpdated'))
      setRenameOpen(false)
      await reloadFolders()
    } catch (e) {
      if (e?.errorFields) return
      message.error(e?.response?.data?.detail || t('dashboard.folderRenameFailed'))
    } finally {
      setRenameLoading(false)
    }
  }

  // ── Delete folder ──────────────────────────────────────────────────────────
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)

  const openDelete = (rn) => {
    setDeleteTarget(rn)
    setDeleteOpen(true)
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleteLoading(true)
    try {
      await quizAPI.deleteFolder(deleteTarget.id)
      message.success(t('dashboard.folderDeleted'))
      setDeleteOpen(false)
      if (selectedFolderId === deleteTarget.id) setSearchParams({}, { replace: true })
      setDeleteTarget(null)
      await reloadFolders()
    } catch (e) {
      message.error(e?.response?.data?.detail || t('dashboard.folderDeleteFailed'))
    } finally {
      setDeleteLoading(false)
    }
  }

  // ── Share folder ───────────────────────────────────────────────────────────
  const [shareTarget, setShareTarget] = useState(null)
  const [shareOpen, setShareOpen] = useState(false)
  const [shareLoading, setShareLoading] = useState(false)
  const [shareUserIds, setShareUserIds] = useState([])
  const [shareCanEdit, setShareCanEdit] = useState(false)
  const [shareCurrentShares, setShareCurrentShares] = useState([])
  const [tenantUsers, setTenantUsers] = useState([])

  const openShare = async (rn) => {
    setShareTarget(rn)
    setShareOpen(true)
    setShareLoading(true)
    try {
      const [sharesRes, usersRes] = await Promise.all([
        quizAPI.getFolderShares(rn.id),
        authAPI.getTenantUsers(),
      ])
      const current = sharesRes.data || []
      setShareCurrentShares(current)
      setShareUserIds(current.map(s => s.user_id))
      setShareCanEdit(current[0]?.can_edit ?? false)
      setTenantUsers(usersRes.data?.users || [])
    } catch (e) {
      message.error(e?.response?.data?.detail || t('dashboard.failedToLoadShares'))
    } finally {
      setShareLoading(false)
    }
  }

  const handleSaveShare = async () => {
    if (!shareTarget) return
    setShareLoading(true)
    try {
      await quizAPI.updateFolderShares(shareTarget.id, {
        user_ids: shareUserIds,
        can_edit: shareCanEdit,
      })
      message.success(t('dashboard.folderSharingUpdated'))
      setShareOpen(false)
    } catch (e) {
      message.error(e?.response?.data?.detail || t('dashboard.failedToUpdateSharing'))
    } finally {
      setShareLoading(false)
    }
  }

  // ── Derived data ───────────────────────────────────────────────────────────
  const folderTreeData = useMemo(() => {
    const map = (nodes) => nodes.map(n => ({
      value: n.id, title: n.name, children: map(n.children || []),
    }))
    return map(folders)
  }, [folders])

  const treeData = useMemo(() => {
    const map = (nodes) => (nodes || []).map(n => ({
      key: String(n.id),
      title: n.name,
      icon: selectedFolderId === n.id
        ? <FolderOpenOutlined style={{ color: '#F59E0B' }} />
        : <FolderFilled style={{ color: '#F59E0B' }} />,
      children: map(n.children || []),
      rawNode: n,
    }))
    return [{
      key: ROOT_KEY,
      title: 'All Activities',
      icon: <FolderOpenOutlined style={{ color: '#F59E0B' }} />,
      children: map(folders),
    }]
  }, [folders, selectedFolderId])

  const getFolderMenu = (rn) => {
    if (rn.is_shared_to_me) return []
    return [
      { key: 'rename', label: t('dashboard.renameMove'), icon: <EditOutlined />, onClick: () => openRename(rn) },
      { key: 'subfolder', label: t('dashboard.newSubfolder'), icon: <FolderAddOutlined />, onClick: () => openCreate(rn.id) },
      { key: 'share', label: t('dashboard.share'), icon: <ShareAltOutlined />, onClick: () => openShare(rn) },
      { type: 'divider' },
      {
        key: 'delete',
        label: <span style={{ color: '#ff4d4f' }}><DeleteOutlined style={{ marginRight: 6 }} />{t('common.delete')}</span>,
        onClick: () => openDelete(rn),
      },
    ]
  }

  const handleSelect = (keys) => {
    const key = keys[0]
    if (!key || key === ROOT_KEY) {
      setSearchParams({}, { replace: true })
    } else {
      setSearchParams({ folder: key }, { replace: true })
    }
    if (!window.location.pathname.startsWith('/dashboard')) {
      navigate('/dashboard')
    }
  }

  const collapseItems = [{
    key: 'folders',
    label: (
      <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
        <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--sw-text2)' }}>{t('dashboard.foldersTitle')}</span>
        <Tooltip title={t('dashboard.tooltipNewFolder')}>
          <Button
            type="text" size="small" icon={<FolderAddOutlined />}
            onClick={(e) => { e.stopPropagation(); openCreate(null) }}
            style={{ padding: '0 4px', height: 20, color: 'var(--sw-text3)', fontSize: 13 }}
          />
        </Tooltip>
      </span>
    ),
    children: (
      <Tree
        key={folders.length}
        showIcon
        showLine={{ showLeafIcon: false }}
        treeData={treeData}
        selectedKeys={[selectedFolderId ? String(selectedFolderId) : ROOT_KEY]}
        onSelect={handleSelect}
        defaultExpandAll
        className="sidebar-folder-tree"
        style={{ background: 'transparent', fontSize: 13 }}
        titleRender={(node) => {
          if (node.key === ROOT_KEY) {
            return <span className="sf-node-title"><span className="sf-node-label">{t('dashboard.allActivities')}</span></span>
          }
          const rn = node.rawNode
          if (!rn) return <span>{node.title}</span>
          const isShared = !!rn.is_shared_to_me
          return (
            <span className="sf-node-title">
              <span className="sf-node-label">{node.title}</span>
              {isShared && (
                <Tag color="blue" style={{ fontSize: 10, padding: '0 3px', lineHeight: '16px', flexShrink: 0 }}>shared</Tag>
              )}
              {!isShared && (
                <span className="sf-node-actions" onClick={e => e.stopPropagation()}>
                  <Tooltip title={t('dashboard.tooltipNewSubfolder')}>
                    <Button
                      type="text" size="small" icon={<FolderAddOutlined />}
                      onClick={(e) => { e.stopPropagation(); openCreate(rn.id) }}
                      style={{ padding: '0 3px', height: 20, color: 'var(--sw-text3)' }}
                    />
                  </Tooltip>
                  <Dropdown menu={{ items: getFolderMenu(rn) }} trigger={['click']} onClick={e => e.stopPropagation()}>
                    <Button
                      type="text" size="small" icon={<MoreOutlined />}
                      style={{ padding: '0 3px', height: 20, color: 'var(--sw-text3)' }}
                    />
                  </Dropdown>
                </span>
              )}
            </span>
          )
        }}
      />
    ),
  }]

  return (
    <div className="sidebar-folder-accordion">
      <Collapse
        defaultActiveKey={['folders']}
        ghost
        items={collapseItems}
        className="sidebar-folder-collapse"
      />

      <Modal title={t('dashboard.newFolder')} open={createOpen}
        onCancel={() => { setCreateOpen(false); createForm.resetFields() }}
        onOk={handleCreate} confirmLoading={createLoading}>
        <Form form={createForm} layout="vertical">
          <Form.Item name="name" label={t('dashboard.folderName')}
            rules={[{ required: true, message: t('dashboard.folderNameRequired') }]}>
            <Input autoFocus />
          </Form.Item>
          <Form.Item name="parent_id" label={t('dashboard.parentFolder')}>
            <TreeSelect allowClear treeData={folderTreeData}
              placeholder={t('dashboard.noParentRoot')} treeDefaultExpandAll />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title={t('dashboard.renameMoveFolder')} open={renameOpen}
        onCancel={() => { setRenameOpen(false); renameForm.resetFields() }}
        onOk={handleRename} confirmLoading={renameLoading}>
        <Form form={renameForm} layout="vertical">
          <Form.Item name="name" label={t('dashboard.folderName')}
            rules={[{ required: true, message: t('dashboard.folderNameRequired') }]}>
            <Input autoFocus />
          </Form.Item>
          <Form.Item name="parent_id" label={t('dashboard.moveTo')}>
            <TreeSelect allowClear
              treeData={folderTreeData.filter(n => n.value !== renameTarget?.id)}
              placeholder={t('dashboard.rootNoParent')} treeDefaultExpandAll />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title={t('dashboard.deleteFolderTitle')} open={deleteOpen}
        onCancel={() => { setDeleteOpen(false); setDeleteTarget(null) }}
        onOk={handleDelete} confirmLoading={deleteLoading}
        okButtonProps={{ danger: true }} okText={t('common.delete')}>
        <p>{t('dashboard.deleteFolderConfirm', { name: deleteTarget?.name })}</p>
      </Modal>

      <Modal
        title={<Space><ShareAltOutlined /> {t('dashboard.shareFolderTitle', { name: shareTarget?.name })}</Space>}
        open={shareOpen} onCancel={() => setShareOpen(false)}
        onOk={handleSaveShare} confirmLoading={shareLoading} okText={t('dashboard.saveFolderSharing')}>
        {shareLoading ? (
          <div style={{ textAlign: 'center', padding: 32 }}><Spin /></div>
        ) : (
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            <div>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>{t('dashboard.shareWith')}</div>
              <Select
                mode="multiple" style={{ width: '100%' }} placeholder={t('dashboard.selectTeammates')}
                value={shareUserIds} onChange={setShareUserIds} optionFilterProp="label"
                options={tenantUsers.filter(u => u.id !== user?.id).map(u => ({ value: u.id, label: u.email }))}
                notFoundContent={tenantUsers.length === 0 ? t('dashboard.noOtherUsers') : t('dashboard.noMatch')}
              />
            </div>
            <Space>
              <span style={{ fontSize: 13 }}>{t('dashboard.allowEditing')}</span>
              <Switch size="small" checked={shareCanEdit} onChange={setShareCanEdit} />
            </Space>
            {shareCurrentShares.length > 0 && (
              <div>
                <div style={{ fontWeight: 600, marginBottom: 6, fontSize: 13 }}>{t('dashboard.currentlySharedWith')}</div>
                <List size="small" dataSource={shareCurrentShares}
                  renderItem={s => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={<Avatar icon={<UserOutlined />} size={28} />}
                        title={s.email}
                        description={s.can_edit ? t('dashboard.canEdit') : t('dashboard.viewOnly')}
                      />
                    </List.Item>
                  )}
                />
              </div>
            )}
          </Space>
        )}
      </Modal>
    </div>
  )
}

export default SidebarFolderTree
