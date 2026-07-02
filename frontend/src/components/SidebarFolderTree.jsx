import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import {
  Tree, Spin, Button, Tooltip, Dropdown, Modal, Form, Input,
  TreeSelect, message, Switch, Select, List, Avatar, Space, Tag,
} from 'antd'
import {
  FolderFilled, FolderOpenFilled, FolderAddOutlined, MoreOutlined,
  EditOutlined, ShareAltOutlined, DeleteOutlined, UserOutlined,
  CaretRightFilled, CaretDownFilled,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { setFolders } from '../store/quizSlice'
import { quizAPI, authAPI } from '../services/api'
import './SidebarFolderTree.css'

const ROOT_KEY = 'swayame-root'

// ── Recursive folder node ────────────────────────────────────────────────────
function FolderNode({ node, depth, selectedFolderId, onSelect, onCreateSub, getFolderMenu, onShare, t }) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = (node.children || []).length > 0
  const isSelected = selectedFolderId === node.id
  const isShared = !!node.is_shared_to_me

  return (
    <>
      <div
        className={`sf2-row${isSelected ? ' sf2-row--active' : ''}`}
        style={{ paddingLeft: 6 + depth * 14 }}
        onClick={() => onSelect(node.id)}
      >
        <button
          type="button"
          className="sf2-chevron"
          onClick={e => { e.stopPropagation(); setExpanded(v => !v) }}
          tabIndex={-1}
          style={{ visibility: hasChildren ? 'visible' : 'hidden' }}
        >
          {expanded ? <CaretDownFilled /> : <CaretRightFilled />}
        </button>
        <span className="sf2-icon">
          {(expanded && hasChildren) || isSelected ? <FolderOpenFilled /> : <FolderFilled />}
        </span>
        <span className="sf2-label">{node.name}</span>
        {isShared && <span className="sf2-shared-badge">shared</span>}
        {!isShared && node.share_count > 0 && (
          <Tooltip title={t('dashboard.sharedWithCount', { count: node.share_count })}>
            <span className="sf2-share-indicator" onClick={e => { e.stopPropagation(); onShare(node) }}>
              <ShareAltOutlined style={{ fontSize: 10 }} /> {node.share_count}
            </span>
          </Tooltip>
        )}
        {!isShared && (
          <span className="sf2-actions" onClick={e => e.stopPropagation()}>
            <Tooltip title={t('dashboard.tooltipNewSubfolder')}>
              <Button type="text" size="small" icon={<FolderAddOutlined />}
                className="sf2-action-btn" onClick={() => onCreateSub(node.id)} />
            </Tooltip>
            <Dropdown menu={{ items: getFolderMenu(node) }} trigger={['click']}
              getPopupContainer={trigger => trigger.parentElement}>
              <Button type="text" size="small" icon={<MoreOutlined />} className="sf2-action-btn" />
            </Dropdown>
          </span>
        )}
      </div>
      {expanded && hasChildren && (node.children || []).map(child => (
        <FolderNode
          key={child.id}
          node={child}
          depth={depth + 1}
          selectedFolderId={selectedFolderId}
          onSelect={onSelect}
          onCreateSub={onCreateSub}
          getFolderMenu={getFolderMenu}
          onShare={onShare}
          t={t}
        />
      ))}
    </>
  )
}

// ── Main component ───────────────────────────────────────────────────────────
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

  // ── Derived ────────────────────────────────────────────────────────────────
  const folderTreeData = useMemo(() => {
    const map = (nodes) => nodes.map(n => ({
      value: n.id, title: n.name, children: map(n.children || []),
    }))
    return map(folders)
  }, [folders])

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

  const handleSelectFolder = (id) => {
    if (id === undefined) {
      setSearchParams({}, { replace: true })
    } else {
      setSearchParams({ folder: String(id) }, { replace: true })
    }
    if (!window.location.pathname.startsWith('/dashboard')) {
      navigate('/dashboard')
    }
  }

  return (
    <div className="sf2-container">
      {/* Section header */}
      <div className="sf2-header">
        <span className="sf2-section-label">{t('dashboard.foldersTitle')}</span>
        <Tooltip title={t('dashboard.tooltipNewFolder')}>
          <Button
            type="text" size="small" icon={<FolderAddOutlined />}
            className="sf2-header-add"
            onClick={() => openCreate(null)}
          />
        </Tooltip>
      </div>

      {/* Tree */}
      <div className="sf2-tree">
        {/* All Activities — virtual root */}
        <div
          className={`sf2-row${!selectedFolderId ? ' sf2-row--active' : ''}`}
          style={{ paddingLeft: 6 }}
          onClick={() => handleSelectFolder(undefined)}
        >
          <span className="sf2-chevron" style={{ visibility: 'hidden' }} />
          <span className="sf2-icon sf2-icon--root">
            {!selectedFolderId ? <FolderOpenFilled /> : <FolderFilled />}
          </span>
          <span className="sf2-label">{t('dashboard.allActivities')}</span>
        </div>

        {/* User folders */}
        {folders.map(folder => (
          <FolderNode
            key={folder.id}
            node={folder}
            depth={1}
            selectedFolderId={selectedFolderId}
            onSelect={handleSelectFolder}
            onCreateSub={openCreate}
            getFolderMenu={getFolderMenu}
            onShare={openShare}
            t={t}
          />
        ))}

        {folders.length === 0 && (
          <div className="sf2-empty">{t('dashboard.noFolders', 'No folders yet')}</div>
        )}
      </div>

      {/* ── Modals ── */}
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
