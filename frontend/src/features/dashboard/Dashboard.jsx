import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSelector, useDispatch } from 'react-redux'
import { ProCard } from '@ant-design/pro-components'
import { Button, Tag, Space, Popconfirm, Tooltip, message, Row, Col, Card, Statistic, Modal, Table, Input, TreeSelect, Form, Tree, Progress, Alert } from 'antd'
import {
  PlusOutlined,
  PlayCircleOutlined,
  CloseCircleOutlined,
  ArrowUpOutlined,
  ThunderboltOutlined,
  CloseOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  EditFilled,
  RocketOutlined,
  HistoryOutlined,
  StarOutlined,
  BarChartOutlined,
  FolderFilled,
  FolderOpenOutlined,
  FolderAddOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import { setQuizzes } from '../../store/quizSlice'
import { logout } from '../../store/authSlice'
import { quizAPI, sessionAPI, authAPI } from '../../services/api'
import './Dashboard.css'

function Dashboard() {
  const TEMPLATE_CACHE_KEY = 'templateQuizIds'
  const ROOT_FOLDER_KEY = 'swayame-root'
  const { t } = useTranslation()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { quizzes } = useSelector((state) => state.quiz)
  const { user } = useSelector((state) => state.auth)
  const [tierPlans, setTierPlans] = useState(null)
  const [bannerDismissed, setBannerDismissed] = useState(() => {
    const ts = localStorage.getItem('upgrade-banner-dismissed')
    if (!ts) return false
    return Date.now() - Number(ts) < 3 * 24 * 60 * 60 * 1000 // 3 days
  })
  const [folderForm] = Form.useForm()
  const [renameFolderForm] = Form.useForm()
  const [templateModalOpen, setTemplateModalOpen] = useState(false)
  const [templates, setTemplates] = useState([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [usingTemplateId, setUsingTemplateId] = useState(null)
  const [folders, setFolders] = useState([])
  const [foldersLoading, setFoldersLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [selectedFolderId, setSelectedFolderId] = useState(undefined)
  const [folderModalOpen, setFolderModalOpen] = useState(false)
  const [folderSubmitting, setFolderSubmitting] = useState(false)
  const [renameFolderModalOpen, setRenameFolderModalOpen] = useState(false)
  const [renameFolderSubmitting, setRenameFolderSubmitting] = useState(false)
  const [isExplorerCollapsed, setIsExplorerCollapsed] = useState(false)

  useEffect(() => {
    loadQuizzes()
    loadFolders()
    authAPI.getTierPlans().then(r => setTierPlans(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    document.body.classList.add('dashboard-scroll-active')
    return () => {
      document.body.classList.remove('dashboard-scroll-active')
    }
  }, [])

  const loadQuizzes = async () => {
    try {
      const response = await quizAPI.list()
      dispatch(setQuizzes(response.data))
    } catch (error) {
      console.error('Failed to load quizzes:', error)
    }
  }

  const loadFolders = async () => {
    setFoldersLoading(true)
    try {
      const response = await quizAPI.listFolders()
      setFolders(response.data || [])
    } catch (error) {
      console.error('Failed to load folders:', error)
      setFolders([])
    } finally {
      setFoldersLoading(false)
    }
  }

  const handleDeleteQuiz = async (quizId) => {
    try {
      await quizAPI.delete(quizId)
      loadQuizzes()
    } catch (error) {
      console.error('Failed to delete quiz:', error)
    }
  }

  const handleDuplicateQuiz = async (quizId) => {
    const extractErrorDetail = (err) => {
      const detail = err?.response?.data?.detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail) && detail.length > 0) {
        return detail[0]?.msg || null
      }
      return null
    }

    try {
      const response = await quizAPI.duplicate(quizId)
      message.success(t('quiz.duplicateSuccess', { defaultValue: 'Quiz duplicated successfully' }))
      loadQuizzes()
      navigate(`/quiz/${response.data.id}/edit`)
    } catch (error) {
      console.error('Failed to duplicate quiz:', error)
      const detail = extractErrorDetail(error)
      message.error(
        detail ||
        t('quiz.duplicateFailed', { defaultValue: 'Failed to duplicate quiz' })
      )
    }
  }

  const handleStopActiveSession = async (sessionId) => {
    try {
      await sessionAPI.end(sessionId)
      message.success(t('quiz.activeSessionStopped', { defaultValue: 'Active session stopped' }))
      loadQuizzes()
    } catch (error) {
      console.error('Failed to stop active session:', error)
      message.error(
        error?.response?.data?.detail ||
        t('quiz.failedToStopActiveSession', { defaultValue: 'Failed to stop active session' })
      )
    }
  }

  const handleAssignFolder = async (quizId, folderId) => {
    try {
      await quizAPI.assignFolder(quizId, folderId ?? null)
      message.success(t('dashboard.folderAssigned', { defaultValue: 'Folder updated' }))
      await loadQuizzes()
    } catch (error) {
      message.error(error?.response?.data?.detail || t('dashboard.folderAssignFailed', { defaultValue: 'Failed to update folder' }))
    }
  }

  const openCreateFolderModal = (parentId = null) => {
    folderForm.setFieldsValue({ name: '', parent_id: parentId })
    setFolderModalOpen(true)
  }

  const handleCreateFolder = async () => {
    try {
      const values = await folderForm.validateFields()
      setFolderSubmitting(true)
      await quizAPI.createFolder({
        name: values.name,
        parent_id: values.parent_id || null,
      })
      message.success(t('dashboard.folderCreated', { defaultValue: 'Folder created' }))
      setFolderModalOpen(false)
      await loadFolders()
    } catch (error) {
      if (error?.errorFields) return
      message.error(error?.response?.data?.detail || t('dashboard.folderCreateFailed', { defaultValue: 'Failed to create folder' }))
    } finally {
      setFolderSubmitting(false)
    }
  }

  const handleDeleteFolder = async () => {
    if (!selectedFolderId) return
    try {
      await quizAPI.deleteFolder(selectedFolderId)
      message.success(t('dashboard.folderDeleted', { defaultValue: 'Folder deleted' }))
      setSelectedFolderId(undefined)
      await loadFolders()
      await loadQuizzes()
    } catch (error) {
      message.error(error?.response?.data?.detail || t('dashboard.folderDeleteFailed', { defaultValue: 'Failed to delete folder' }))
    }
  }

  const openRenameFolderModal = () => {
    if (!selectedFolderId || !selectedFolderName) return
    renameFolderForm.setFieldsValue({ name: selectedFolderName })
    setRenameFolderModalOpen(true)
  }

  const handleRenameFolder = async () => {
    if (!selectedFolderId) return
    try {
      const values = await renameFolderForm.validateFields()
      setRenameFolderSubmitting(true)
      await quizAPI.updateFolder(selectedFolderId, { name: values.name })
      message.success(t('dashboard.folderRenamed', { defaultValue: 'Folder renamed' }))
      setRenameFolderModalOpen(false)
      await loadFolders()
      await loadQuizzes()
    } catch (error) {
      if (error?.errorFields) return
      message.error(error?.response?.data?.detail || t('dashboard.folderRenameFailed', { defaultValue: 'Failed to rename folder' }))
    } finally {
      setRenameFolderSubmitting(false)
    }
  }

  const handleToggleTemplate = async (quiz) => {
    const nextTemplateState = !quiz.is_template
    try {
      const response = await quizAPI.setTemplate(quiz.id, { is_template: nextTemplateState })
      const updatedQuiz = response.data
      const normalizedQuiz = {
        ...quiz,
        ...updatedQuiz,
        is_template: typeof updatedQuiz?.is_template === 'boolean' ? updatedQuiz.is_template : nextTemplateState,
      }
      const nextQuizzes = (quizzes || []).map((q) => (q.id === normalizedQuiz.id ? { ...q, ...normalizedQuiz } : q))
      dispatch(setQuizzes(nextQuizzes))
      const cachedIds = new Set(
        JSON.parse(localStorage.getItem(TEMPLATE_CACHE_KEY) || '[]').filter((id) => Number.isInteger(id))
      )
      if (normalizedQuiz.is_template) cachedIds.add(normalizedQuiz.id)
      else cachedIds.delete(normalizedQuiz.id)
      localStorage.setItem(TEMPLATE_CACHE_KEY, JSON.stringify(Array.from(cachedIds)))
      setTemplates((prev) => {
        const withoutCurrent = (prev || []).filter((tq) => tq.id !== normalizedQuiz.id)
        if (!normalizedQuiz.is_template) return withoutCurrent
        return [
          {
            id: normalizedQuiz.id,
            title: normalizedQuiz.title,
            quiz_type: normalizedQuiz.quiz_type || 'quiz',
            template_scope: normalizedQuiz.template_scope || 'tenant',
            question_count: normalizedQuiz.question_count || 0,
            tenant_id: normalizedQuiz.tenant_id,
          },
          ...withoutCurrent,
        ]
      })
      message.success(
        quiz.is_template
          ? t('quiz.templateUnsetSuccess', { defaultValue: 'Template removed' })
          : t('quiz.templateSetSuccess', { defaultValue: 'Template set successfully' })
      )
      loadQuizzes()
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.templateSetFailed', { defaultValue: 'Failed to update template status' }))
    }
  }

  const openTemplateModal = async () => {
    setTemplateModalOpen(true)
    setTemplatesLoading(true)
    const cachedTemplateIds = JSON.parse(localStorage.getItem(TEMPLATE_CACHE_KEY) || '[]').filter((id) => Number.isInteger(id))
    let myTemplates = (quizzes || []).filter((q) => q.is_template || cachedTemplateIds.includes(q.id))
    setTemplates(
      myTemplates.map((q) => ({
        id: q.id,
        title: q.title,
        quiz_type: q.quiz_type || 'quiz',
        template_scope: q.template_scope || 'tenant',
        question_count: q.question_count || 0,
        tenant_id: q.tenant_id,
      }))
    )
    try {
      try {
        const quizListResponse = await quizAPI.list()
        const latestQuizzes = quizListResponse.data || []
        dispatch(setQuizzes(latestQuizzes))
        myTemplates = latestQuizzes.filter((q) => q.is_template || cachedTemplateIds.includes(q.id))
      } catch (refreshError) {
        // Keep existing local state as fallback.
      }

      let templateItems = []
      try {
        const response = await quizAPI.listTemplates()
        templateItems = response.data || []
      } catch (primaryError) {
        const legacyResponse = await quizAPI.listTemplatesLegacy()
        templateItems = legacyResponse.data || []
      }

      if (templateItems.length > 0) {
        setTemplates(templateItems)
      } else {
        setTemplates(myTemplates)
      }
    } catch (error) {
      if (myTemplates.length > 0) {
        setTemplates(myTemplates)
      } else {
        message.error(error.response?.data?.detail || t('quiz.templateLoadFailed', { defaultValue: 'Failed to load templates' }))
        setTemplates([])
      }
    } finally {
      setTemplatesLoading(false)
    }
  }

  const handleUseTemplate = async (templateId) => {
    setUsingTemplateId(templateId)
    try {
      let response
      try {
        response = await quizAPI.useTemplate(templateId)
      } catch (primaryError) {
        response = await quizAPI.useTemplateLegacy(templateId)
      }
      message.success(t('quiz.templateUseSuccess', { defaultValue: 'Template quiz created' }))
      setTemplateModalOpen(false)
      loadQuizzes()
      navigate(`/quiz/${response.data.id}/edit`)
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.templateUseFailed', { defaultValue: 'Failed to use template' }))
    } finally {
      setUsingTemplateId(null)
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      draft: 'default',
      ready: 'success',
      archived: 'error',
    }
    return colors[status] || 'default'
  }

  const getStatusTranslation = (status) => {
    const statusMap = {
      draft: 'statusDraft',
      ready: 'statusReady',
      archived: 'statusArchived'
    }
    return t(`quiz.${statusMap[status] || 'statusDraft'}`)
  }

  const getQuizTypeColor = (quizType) => {
    if (quizType === 'exam') return 'volcano'
    if (quizType === 'offline_poll') return 'magenta'
    if (quizType === 'poll') return 'purple'
    return 'blue'
  }
  const getQuizTypeLabel = (quizType) => {
    if (quizType === 'exam') return t('exam.typeLabel', 'Test')
    if (quizType === 'offline_poll') return t('offlinePoll.typeLabel', 'Offline Poll')
    if (quizType === 'poll') return t('quiz.poll', { defaultValue: 'Poll' })
    return t('quiz.quizTypeLabel', { defaultValue: 'Quiz' })
  }

  const folderTreeData = useMemo(() => {
    const mapNodes = (nodes) => (nodes || []).map((node) => ({
      value: node.id,
      title: node.name,
      children: mapNodes(node.children || []),
    }))
    return mapNodes(folders)
  }, [folders])

  const folderNavTreeData = useMemo(() => {
    const mapNodes = (nodes) => (nodes || []).map((node) => ({
      key: String(node.id),
      title: node.name,
      icon: selectedFolderId === node.id ? <FolderOpenOutlined /> : <FolderFilled />,
      children: mapNodes(node.children || []),
    }))
    return [{
      key: ROOT_FOLDER_KEY,
      title: t('common.appTitle'),
      icon: <FolderOpenOutlined />,
      children: mapNodes(folders),
    }]
  }, [folders, selectedFolderId])

  const selectedFolderName = useMemo(() => {
    const stack = [...folders]
    while (stack.length > 0) {
      const node = stack.pop()
      if (!node) continue
      if (node.id === selectedFolderId) return node.name
      if (node.children?.length) stack.push(...node.children)
    }
    return null
  }, [folders, selectedFolderId])

  const filteredQuizzes = useMemo(() => {
    const term = searchText.trim().toLowerCase()
    return (quizzes || []).filter((quiz) => {
      const matchesSearch = !term || quiz.title.toLowerCase().includes(term)
      const folderId = quiz.folder_id
      const matchesFolder = selectedFolderId
        ? Number(folderId) === Number(selectedFolderId)
        : folderId == null
      return matchesSearch && matchesFolder
    })
  }, [quizzes, searchText, selectedFolderId])

  // Calculate quiz statistics
  const statistics = useMemo(() => {
    const stats = {
      total: quizzes.length,
      byStatus: {
        draft: 0,
        ready: 0,
        archived: 0
      },
      totalQuestions: 0
    }

    filteredQuizzes.forEach(quiz => {
      // Count by status
      if (quiz.status in stats.byStatus) {
        stats.byStatus[quiz.status]++
      }
      // Count total questions
      if (quiz.question_count) {
        stats.totalQuestions += quiz.question_count
      }
    })

    return stats
  }, [filteredQuizzes])

  const visibleTemplateData = (templates && templates.length > 0
    ? templates
    : (quizzes || [])
        .filter((q) => {
          const cachedTemplateIds = JSON.parse(localStorage.getItem(TEMPLATE_CACHE_KEY) || '[]').filter((id) => Number.isInteger(id))
          return q.is_template || cachedTemplateIds.includes(q.id)
        })
        .map((q) => ({
          id: q.id,
          title: q.title,
          quiz_type: q.quiz_type || 'quiz',
          template_scope: q.template_scope || 'tenant',
          question_count: q.question_count || 0,
          tenant_id: q.tenant_id,
        })))

  const TIER_ORDER = ['free', 'basic', 'pro', 'enterprise']
  const TIER_COLOR = { free: '#8c8c8c', basic: '#1677ff', pro: '#722ed1', enterprise: '#d48806' }
  const TIER_GRADIENT = {
    free:   'linear-gradient(135deg, #f5f5f5 0%, #e6f4ff 100%)',
    basic:  'linear-gradient(135deg, #e6f4ff 0%, #f0f0ff 100%)',
    pro:    'linear-gradient(135deg, #f9f0ff 0%, #fff0f6 100%)',
  }

  const currentTier = user?.tier || 'free'
  const currentTierIdx = TIER_ORDER.indexOf(currentTier)
  const nextTier = currentTierIdx >= 0 && currentTierIdx < TIER_ORDER.length - 1
    ? TIER_ORDER[currentTierIdx + 1]
    : null
  const nextPlan = tierPlans?.find(p => p.tier === nextTier)
  const currentPlan = tierPlans?.find(p => p.tier === currentTier)

  const showBanner = !bannerDismissed && nextTier && currentPlan

  const maxQ = currentPlan?.max_questions ?? 0
  const usedQ = statistics.total
  const qPct = maxQ > 0 ? Math.min(100, Math.round((usedQ / maxQ) * 100)) : 0
  const nearLimit = qPct >= 70

  const handleDismiss = () => {
    localStorage.setItem('upgrade-banner-dismissed', String(Date.now()))
    setBannerDismissed(true)
  }

  return (
    <div className="dashboard-scroll">
      <div className="dashboard-page" style={{ padding: 24, overflowX: 'hidden' }}>

      {/* Upgrade Banner */}
      {showBanner && (
        <div style={{
          background: TIER_GRADIENT[currentTier] || '#f5f5f5',
          border: `1px solid ${TIER_COLOR[nextTier] || '#d9d9d9'}`,
          borderRadius: 10,
          padding: '14px 20px',
          marginBottom: 20,
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          flexWrap: 'wrap',
        }}>
          <ThunderboltOutlined style={{ fontSize: 22, color: TIER_COLOR[nextTier], flexShrink: 0 }} />
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2, color: '#141414' }}>
              {nearLimit
                ? t('dashboard.upgradeBannerNearLimit', { pct: qPct })
                : t('dashboard.upgradeBannerOnPlan')}
              {!nearLimit && (
                <Tag color={TIER_COLOR[currentTier]} style={{ textTransform: 'uppercase', fontWeight: 700, fontSize: 11, margin: '0 4px' }}>
                  {currentTier}
                </Tag>
              )}
              {!nearLimit && t('dashboard.upgradeBannerPlan')}
            </div>
            {nextPlan && (
              <div style={{ fontSize: 13, color: '#434343' }}>
                {t('dashboard.upgradeBannerNextTier', {
                  tier: nextTier.charAt(0).toUpperCase() + nextTier.slice(1),
                  participants: nextPlan.max_participants.toLocaleString(),
                  questions: nextPlan.max_questions,
                  sessions: nextPlan.max_concurrent_events,
                })}
              </div>
            )}
            {nearLimit && (
              <Progress
                percent={qPct}
                size="small"
                strokeColor={qPct >= 90 ? '#ff4d4f' : '#faad14'}
                style={{ marginTop: 6, maxWidth: 260 }}
                format={() => t('dashboard.upgradeBannerQuizUsage', { used: usedQ, max: maxQ })}
              />
            )}
          </div>
          <Space>
            <Button
              type="primary"
              icon={<ArrowUpOutlined />}
              size="small"
              href="mailto:info@chakrix.net?subject=Upgrade%20Enquiry"
              style={{ background: TIER_COLOR[nextTier], borderColor: TIER_COLOR[nextTier] }}
            >
              {t('dashboard.upgradeBannerCta', { tier: nextTier.charAt(0).toUpperCase() + nextTier.slice(1) })}
            </Button>
            <Button
              type="text"
              icon={<CloseOutlined />}
              size="small"
              onClick={handleDismiss}
              style={{ color: '#8c8c8c' }}
            />
          </Space>
        </div>
      )}

      {/* Statistics Cards */}
      <Row gutter={[8, 8]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('admin.stats.totalQuizzes')}
              value={statistics.total}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('dashboard.readyToLaunch', { defaultValue: 'Ready to Launch' })}
              value={statistics.byStatus.ready}
              prefix={<RocketOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('dashboard.drafts', { defaultValue: 'Drafts' })}
              value={statistics.byStatus.draft}
              prefix={<EditFilled />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('dashboard.totalQuestions', { defaultValue: 'Total Questions' })}
              value={statistics.totalQuestions}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Quiz List */}
      <ProCard
        title={t('quiz.myQuizzes')}
        style={{ overflowX: 'hidden' }}
        extra={
          <div className="dashboard-action-buttons">
            <Tooltip title={t('tooltip.useTemplate')}>
              <Button icon={<StarOutlined />} onClick={openTemplateModal}>
                {t('quiz.useTemplate', { defaultValue: 'Use Template' })}
              </Button>
            </Tooltip>
            <Space size={4}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => navigate('/quiz/new?type=quiz')}
              >
                {t('quiz.createQuiz')}
              </Button>
              <Tooltip title={t('quiz.quizTypeInfo')}>
                <InfoCircleOutlined style={{ color: '#1677ff', cursor: 'pointer', fontSize: 14 }} />
              </Tooltip>
            </Space>
            <Space size={4}>
              <Button
                type="primary"
                icon={<BarChartOutlined />}
                onClick={() => navigate('/quiz/new?type=poll')}
                style={{ backgroundColor: '#722ed1', borderColor: '#722ed1' }}
              >
                {t('quiz.createPoll', { defaultValue: 'Create Poll' })}
              </Button>
              <Tooltip title={t('quiz.pollTypeInfo')}>
                <InfoCircleOutlined style={{ color: '#722ed1', cursor: 'pointer', fontSize: 14 }} />
              </Tooltip>
            </Space>
            <Space size={4}>
              <Button
                type="primary"
                icon={<BarChartOutlined />}
                onClick={() => navigate('/quiz/new?type=offline_poll')}
                style={{ backgroundColor: '#eb2f96', borderColor: '#eb2f96' }}
              >
                {t('offlinePoll.createOfflinePoll', 'Create Poll')}
              </Button>
              <Tooltip title={t('offlinePoll.typeInfo')}>
                <InfoCircleOutlined style={{ color: '#eb2f96', cursor: 'pointer', fontSize: 14 }} />
              </Tooltip>
            </Space>
            <Space size={4}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => navigate('/quiz/new?type=exam')}
                style={{ backgroundColor: '#fa541c', borderColor: '#fa541c' }}
              >
                {t('exam.createExam', 'Create Test')}
              </Button>
              <Tooltip title={t('exam.typeInfo')}>
                <InfoCircleOutlined style={{ color: '#fa541c', cursor: 'pointer', fontSize: 14 }} />
              </Tooltip>
            </Space>
          </div>
        }
      >
      <div className={`dashboard-explorer-layout${isExplorerCollapsed ? ' collapsed' : ''}`}>
        {!isExplorerCollapsed ? (
        <aside className="dashboard-folder-pane">
          <div className="dashboard-folder-pane-header">
            <span>{t('dashboard.foldersTitle', { defaultValue: 'Folders' })}</span>
            <Space size={6}>
              <Tooltip title={t('dashboard.newFolder', { defaultValue: 'New Folder' })}>
                <Button
                  size="small"
                  shape="circle"
                  icon={<FolderAddOutlined />}
                  onClick={() => openCreateFolderModal(selectedFolderId || null)}
                />
              </Tooltip>
              <Tooltip title={t('dashboard.renameFolder', { defaultValue: 'Rename Folder' })}>
                <Button
                  size="small"
                  shape="circle"
                  icon={<EditOutlined />}
                  onClick={openRenameFolderModal}
                  disabled={!selectedFolderId}
                />
              </Tooltip>
              <Popconfirm
                title={t('dashboard.deleteFolderConfirmTitle', { defaultValue: 'Delete selected folder?' })}
                description={t('dashboard.deleteFolderConfirmDesc', { defaultValue: 'Subfolders and quizzes will be moved to parent/root.' })}
                onConfirm={handleDeleteFolder}
                okText={t('common.delete', { defaultValue: 'Delete' })}
                cancelText={t('common.cancel', { defaultValue: 'Cancel' })}
                disabled={!selectedFolderId}
              >
                <Tooltip title={t('dashboard.deleteFolder', { defaultValue: 'Delete Folder' })}>
                  <Button
                    size="small"
                    shape="circle"
                    danger
                    icon={<DeleteOutlined />}
                    disabled={!selectedFolderId}
                  />
                </Tooltip>
              </Popconfirm>
            </Space>
          </div>
          <div className="dashboard-folder-tree-wrapper">
            {foldersLoading ? (
              <div style={{ color: '#888', padding: '8px 4px' }}>
                {t('common.loading', { defaultValue: 'Loading...' })}
              </div>
            ) : (
              <Tree
                showIcon
                showLine={{ showLeafIcon: false }}
                treeData={folderNavTreeData}
                selectedKeys={[selectedFolderId ? String(selectedFolderId) : ROOT_FOLDER_KEY]}
                onSelect={(keys) => {
                  const selectedKey = keys[0]
                  if (!selectedKey || selectedKey === ROOT_FOLDER_KEY) {
                    setSelectedFolderId(undefined)
                    return
                  }
                  setSelectedFolderId(Number(selectedKey))
                }}
                defaultExpandAll
                className="dashboard-folder-tree"
              />
            )}
          </div>
        </aside>
        ) : null}
        <section className="dashboard-content-pane">
          <Space wrap style={{ marginBottom: 16, width: '100%' }}>
            <Tooltip title={isExplorerCollapsed
              ? t('dashboard.expandFolders', { defaultValue: 'Show folders' })
              : t('dashboard.collapseFolders', { defaultValue: 'Hide folders' })}
            >
              <Button
                icon={isExplorerCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setIsExplorerCollapsed((prev) => !prev)}
              />
            </Tooltip>
            <Input.Search
              className="dashboard-search-input"
              allowClear
              placeholder={t('dashboard.searchQuizzes', { defaultValue: 'Search quizzes/polls' })}
              style={{ width: 'min(320px, 100%)' }}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
            />
            {selectedFolderId ? (
              <Tag color="blue">
                {t('dashboard.inFolder', { defaultValue: 'In folder' })}: {selectedFolderName}
              </Tag>
            ) : null}
          </Space>
          <div style={{ width: '100%', overflow: 'hidden' }}>
        {filteredQuizzes.length === 0 ? (
          !searchText.trim() && !selectedFolderId ? (
            <div style={{ padding: '40px 24px', textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>{t('tooltip.emptyStateTitle')}</div>
              <div style={{ color: '#888', marginBottom: 32, fontSize: 14 }}>{t('tooltip.emptyStateSubtitle')}</div>
              <Row gutter={[16, 16]} justify="center">
                {[
                  { type: 'quiz', icon: '🎯', desc: t('tooltip.emptyStateQuizDesc'), color: '#1677ff' },
                  { type: 'poll', icon: '📊', desc: t('tooltip.emptyStatePollDesc'), color: '#722ed1' },
                  { type: 'offline_poll', icon: '📋', desc: t('tooltip.emptyStateOfflinePollDesc'), color: '#eb2f96' },
                  { type: 'exam', icon: '📝', desc: t('tooltip.emptyStateExamDesc'), color: '#fa541c' },
                ].map(({ type, icon, desc, color }) => (
                  <Col xs={24} sm={12} md={6} key={type}>
                    <Card
                      hoverable
                      onClick={() => navigate(`/quiz/new?type=${type}`)}
                      style={{ borderTop: `3px solid ${color}`, cursor: 'pointer' }}
                      bodyStyle={{ padding: '20px 16px', textAlign: 'center' }}
                    >
                      <div style={{ fontSize: 32, marginBottom: 8 }}>{icon}</div>
                      <div style={{ fontSize: 13, color: '#444', lineHeight: 1.5 }}>{desc}</div>
                    </Card>
                  </Col>
                ))}
              </Row>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '24px', color: '#999' }}>
              {t('quiz.noQuizzes') || 'No quizzes yet. Create your first quiz!'}
            </div>
          )
        ) : filteredQuizzes.map((quiz, index) => (
          <div
            key={quiz.id}
            className="quiz-item"
          >
            <div className="quiz-item-title">
              <strong>{quiz.title}</strong>
            </div>
            <div className="quiz-item-body">
              <div className="quiz-item-meta">
                <Space>
                  <Tag color={getQuizTypeColor(quiz.quiz_type)}>
                    {getQuizTypeLabel(quiz.quiz_type)}
                  </Tag>
                  <Tag color={getStatusColor(quiz.status)}>{getStatusTranslation(quiz.status)}</Tag>
                  {quiz.is_template && (
                    <Tag color={quiz.template_scope === 'global' ? 'purple' : 'blue'}>
                      {quiz.template_scope === 'global'
                        ? t('quiz.globalTemplate', { defaultValue: 'Global Template' })
                        : t('quiz.tenantTemplate', { defaultValue: 'Tenant Template' })}
                    </Tag>
                  )}
                  <span>
                    {t('quiz.questionCount', {
                      count: quiz.question_count || 0,
                      defaultValue: `${quiz.question_count || 0} ${t('quiz.questions')}`,
                    })}
                  </span>
                  {quiz.folder_path && (
                    <Tag color="cyan">
                      {t('dashboard.folder', { defaultValue: 'Folder' })}: {quiz.folder_path}
                    </Tag>
                  )}
                  {quiz.quiz_type === 'offline_poll' && quiz.offline_start_at && (
                    <Tag color={(() => {
                      const now = new Date()
                      const start = new Date(quiz.offline_start_at)
                      const end = quiz.offline_end_at ? new Date(quiz.offline_end_at) : null
                      if (now < start) return 'blue'
                      if (end && now > end) return 'default'
                      return 'green'
                    })()}>
                      {(() => {
                        const now = new Date()
                        const start = new Date(quiz.offline_start_at)
                        const end = quiz.offline_end_at ? new Date(quiz.offline_end_at) : null
                        if (now < start) return t('offlinePoll.statusNotStarted', 'Not Started')
                        if (end && now > end) return t('offlinePoll.statusClosed', 'Closed')
                        return t('offlinePoll.statusActive', 'Active')
                      })()}
                    </Tag>
                  )}
                </Space>
              </div>
              <div className="quiz-item-actions">
                <TreeSelect
                  allowClear
                  treeData={folderTreeData}
                  value={quiz.folder_id ?? undefined}
                  onChange={(value) => handleAssignFolder(quiz.id, value)}
                  placeholder={t('dashboard.assignFolder', { defaultValue: 'Assign folder' })}
                  style={{ minWidth: 180 }}
                  treeDefaultExpandAll
                />
                <Tooltip title={quiz.is_template ? t('tooltip.removeTemplate') : t('tooltip.makeTemplate')}>
                  <Button
                    icon={<StarOutlined />}
                    onClick={() => handleToggleTemplate(quiz)}
                  >
                    {quiz.is_template
                      ? t('quiz.removeTemplate', { defaultValue: 'Remove Template' })
                      : t('quiz.makeTemplate', { defaultValue: 'Make Template' })}
                  </Button>
                </Tooltip>
                <Button
                  icon={<CopyOutlined />}
                  onClick={() => handleDuplicateQuiz(quiz.id)}
                >
                  {t('quiz.duplicate', { defaultValue: 'Duplicate' })}
                </Button>
                <Button
                  icon={<EditOutlined />}
                  onClick={() => navigate(`/quiz/${quiz.id}/edit`)}
                >
                  {t('common.edit')}
                </Button>
                <Tooltip title={t('tooltip.quizHistory')}>
                  <Button
                    icon={<HistoryOutlined />}
                    onClick={() => navigate(`/quiz/${quiz.id}/history`)}
                  >
                    {t('quiz.history')}
                  </Button>
                </Tooltip>
                {quiz.has_active_session && quiz.active_session_id ? (
                  <Popconfirm
                    title={t('quiz.stopActiveSessionConfirm', { defaultValue: 'Stop active session?' })}
                    description={t('quiz.stopQuizConfirm', { defaultValue: 'This will end the session for all participants. You cannot restart it.' })}
                    onConfirm={() => handleStopActiveSession(quiz.active_session_id)}
                    okText={t('quiz.stopQuizOk', { defaultValue: 'Yes, stop it' })}
                    cancelText={t('common.cancel')}
                  >
                    <Button danger icon={<CloseCircleOutlined />}>
                      {t('quiz.stopActiveSession', { defaultValue: 'Stop Active Session' })}
                    </Button>
                  </Popconfirm>
                ) : null}
                {quiz.status === 'ready' && !quiz.has_active_session && quiz.quiz_type !== 'offline_poll' && quiz.quiz_type !== 'exam' && (
                  <Tooltip title={t('tooltip.startSession')}>
                    <Button
                      type="primary"
                      icon={<PlayCircleOutlined />}
                      onClick={() => navigate(`/quiz/${quiz.id}/control`)}
                    >
                      {t('quiz.startQuiz')}
                    </Button>
                  </Tooltip>
                )}
                {quiz.quiz_type === 'exam' && quiz.exam_url && (
                  <Button
                    icon={<CopyOutlined />}
                    onClick={() => {
                      navigator.clipboard.writeText(quiz.exam_url)
                      message.success(t('exam.linkCopied', 'Link copied!'))
                    }}
                  >
                    {t('exam.copyLink', 'Copy Link')}
                  </Button>
                )}
                {quiz.quiz_type === 'exam' && quiz.status === 'ready' && (
                  <Button
                    onClick={() => navigate(`/quiz/${quiz.id}/exam-results`)}
                  >
                    {t('exam.resultsTitle', 'Exam Results')}
                  </Button>
                )}
                {quiz.quiz_type === 'offline_poll' && quiz.poll_url && (
                  <Button
                    icon={<CopyOutlined />}
                    onClick={() => {
                      navigator.clipboard.writeText(quiz.poll_url)
                      message.success(t('offlinePoll.linkCopied', 'Link copied!'))
                    }}
                  >
                    {t('offlinePoll.copyLink', 'Copy Link')}
                  </Button>
                )}
                {quiz.quiz_type === 'offline_poll' && quiz.status === 'ready' && (
                  <Button
                    onClick={() => navigate(`/quiz/${quiz.id}/offline-results`)}
                  >
                    {t('offlinePoll.viewResults', 'View Results')}
                  </Button>
                )}
                <Popconfirm
                  title={t('quiz.deleteConfirm')}
                  description={t('quiz.deleteWarning')}
                  onConfirm={() => handleDeleteQuiz(quiz.id)}
                  okText={t('common.submit')}
                  cancelText={t('common.cancel')}
                >
                  <Button danger icon={<DeleteOutlined />}>
                    {t('common.delete')}
                  </Button>
                </Popconfirm>
              </div>
            </div>
          </div>
        ))}
      </div>
        </section>
      </div>
    </ProCard>
      <Modal
        title={t('dashboard.newFolder', { defaultValue: 'New Folder' })}
        open={folderModalOpen}
        onCancel={() => setFolderModalOpen(false)}
        onOk={handleCreateFolder}
        confirmLoading={folderSubmitting}
      >
        <Form form={folderForm} layout="vertical">
          <Form.Item
            name="name"
            label={t('dashboard.folderName', { defaultValue: 'Folder name' })}
            rules={[{ required: true, message: t('dashboard.folderNameRequired', { defaultValue: 'Folder name is required' }) }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="parent_id"
            label={t('dashboard.parentFolder', { defaultValue: 'Parent folder' })}
          >
            <TreeSelect
              allowClear
              treeData={folderTreeData}
              placeholder={t('dashboard.noParentRoot', { defaultValue: 'No parent (root)' })}
              treeDefaultExpandAll
            />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        title={t('dashboard.renameFolder', { defaultValue: 'Rename Folder' })}
        open={renameFolderModalOpen}
        onCancel={() => setRenameFolderModalOpen(false)}
        onOk={handleRenameFolder}
        confirmLoading={renameFolderSubmitting}
      >
        <Form form={renameFolderForm} layout="vertical">
          <Form.Item
            name="name"
            label={t('dashboard.folderName', { defaultValue: 'Folder name' })}
            rules={[{ required: true, message: t('dashboard.folderNameRequired', { defaultValue: 'Folder name is required' }) }]}
          >
            <Input />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        title={t('quiz.templateLibrary', { defaultValue: 'Template Library' })}
        open={templateModalOpen}
        onCancel={() => setTemplateModalOpen(false)}
        footer={null}
        width={900}
      >
        <Table
          rowKey="id"
          loading={templatesLoading}
          dataSource={visibleTemplateData}
          pagination={{ pageSize: 8 }}
          columns={[
            {
              title: t('quiz.title', { defaultValue: 'Title' }),
              dataIndex: 'title',
            },
            {
              title: t('dashboard.type', { defaultValue: 'Type' }),
              dataIndex: 'quiz_type',
              width: 110,
              render: (value) => (
                <Tag color={getQuizTypeColor(value)}>
                  {getQuizTypeLabel(value)}
                </Tag>
              ),
            },
            {
              title: t('quiz.scope', { defaultValue: 'Scope' }),
              dataIndex: 'template_scope',
              width: 160,
              render: (value) => (
                <Tag color={value === 'global' ? 'purple' : 'blue'}>
                  {value === 'global'
                    ? t('quiz.globalTemplate', { defaultValue: 'Global Template' })
                    : t('quiz.tenantTemplate', { defaultValue: 'Tenant Template' })}
                </Tag>
              ),
            },
            {
              title: t('quiz.questions', { defaultValue: 'Questions' }),
              dataIndex: 'question_count',
              width: 120,
            },
            {
              title: t('common.actions', { defaultValue: 'Actions' }),
              width: 180,
              render: (_, record) => (
                <Button
                  type="primary"
                  loading={usingTemplateId === record.id}
                  onClick={() => handleUseTemplate(record.id)}
                >
                  {t('quiz.useTemplate', { defaultValue: 'Use Template' })}
                </Button>
              ),
            },
          ]}
        />
      </Modal>
      </div>
    </div>
  )
}

export default Dashboard
