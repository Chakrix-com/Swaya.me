import { useEffect, useMemo, useState, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSelector, useDispatch } from 'react-redux'
import {
  Button, Tag, Space, Popconfirm, Tooltip, message, Select, Spin,
  Row, Col, Card, Modal, Input, Progress, Table, Typography, Badge, Dropdown,
} from 'antd'
import {
  PlusOutlined,
  PlayCircleOutlined,
  ArrowUpOutlined,
  ThunderboltOutlined,
  CloseOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  FileTextOutlined,
  HistoryOutlined,
  StarOutlined,
  BarChartOutlined,
  MoreOutlined,
  LinkOutlined,
  WifiOutlined,
  EyeOutlined,
  StopOutlined,
  AppstoreOutlined,
  SearchOutlined,
  InboxOutlined,
} from '@ant-design/icons'
import { setQuizzes, setFolders } from '../../store/quizSlice'
import { quizAPI, sessionAPI, authAPI } from '../../services/api'
import CreateChooser from './CreateChooser'
import './Dashboard.css'

const { Title, Text } = Typography

// ── Colour tokens — CSS variable references so all themes work ───────────────
const C = {
  primary:   'var(--sw-primary)',
  primary50: 'var(--sw-primary-soft)',
  primary100:'var(--sw-primary-soft)',
  primary600:'var(--sw-primary-strong)',
  success:   'var(--sw-success)',
  warning:   'var(--sw-warning)',
  error:     'var(--sw-error)',
  blue:      'var(--sw-info)',
  orange:    'var(--sw-tile-poll-fg)',
  pink:      'var(--sw-tile-opoll-fg)',
  green:     'var(--sw-tile-exam-fg)',
  text1:     'var(--sw-text1)',
  text2:     'var(--sw-text2)',
  text3:     'var(--sw-text3)',
  bg:        'var(--sw-bg)',
  bgCard:    'var(--sw-card)',
  border:    'var(--sw-border)',
}

// ── Activity type config ──────────────────────────────────────────────────────
const ACTIVITY_TYPES = [
  {
    key: 'quiz',
    titleKey: 'quiz.createQuiz',
    defaultTitle: 'Live Quiz',
    descKey: 'tooltip.emptyStateQuizDesc',
    defaultDesc: 'Run a quiz in real time.',
    bg: 'var(--sw-tile-quiz-bg)',
    iconBg: 'var(--sw-tile-icon-bg)',
    iconColor: 'var(--sw-tile-quiz-fg)',
    Icon: ThunderboltOutlined,
  },
  {
    key: 'exam',
    titleKey: 'exam.createExam',
    defaultTitle: 'Test / Exam',
    descKey: 'tooltip.emptyStateExamDesc',
    defaultDesc: 'Timed assessments with auto-grading.',
    bg: 'var(--sw-tile-exam-bg)',
    iconBg: 'var(--sw-tile-icon-bg)',
    iconColor: 'var(--sw-tile-exam-fg)',
    Icon: FileTextOutlined,
  },
  {
    key: 'poll',
    titleKey: 'quiz.createPoll',
    defaultTitle: 'Live Poll',
    descKey: 'tooltip.emptyStatePollDesc',
    defaultDesc: 'Collect instant audience feedback.',
    bg: 'var(--sw-tile-poll-bg)',
    iconBg: 'var(--sw-tile-icon-bg)',
    iconColor: 'var(--sw-tile-poll-fg)',
    Icon: BarChartOutlined,
  },
  {
    key: 'offline_poll',
    titleKey: 'offlinePoll.createOfflinePoll',
    defaultTitle: 'Survey',
    descKey: 'tooltip.emptyStateOfflinePollDesc',
    defaultDesc: 'Collect responses asynchronously.',
    bg: 'var(--sw-tile-opoll-bg)',
    iconBg: 'var(--sw-tile-icon-bg)',
    iconColor: 'var(--sw-tile-opoll-fg)',
    Icon: AppstoreOutlined,
  },
]

// ── Status tag config ─────────────────────────────────────────────────────────
const STATUS_TAG = {
  ready:    { bg: 'var(--sw-chip-ready-bg)', color: 'var(--sw-chip-ready-fg)', labelKey: 'activities.statusReady' },
  draft:    { bg: 'var(--sw-chip-draft-bg)', color: 'var(--sw-chip-draft-fg)', labelKey: 'activities.statusDraft' },
  archived: { bg: 'var(--sw-chip-done-bg)',  color: 'var(--sw-chip-done-fg)',  labelKey: 'activities.statusCompleted' },
}

// ── Type tag colours ──────────────────────────────────────────────────────────
const TYPE_TAG = {
  quiz:         { bg: 'var(--sw-tile-quiz-bg)',  color: 'var(--sw-tile-quiz-fg)',  labelKey: 'activities.typeQuiz' },
  exam:         { bg: 'var(--sw-tile-exam-bg)',  color: 'var(--sw-tile-exam-fg)',  labelKey: 'activities.typeExam' },
  poll:         { bg: 'var(--sw-tile-poll-bg)',  color: 'var(--sw-tile-poll-fg)',  labelKey: 'activities.typePoll' },
  offline_poll: { bg: 'var(--sw-tile-opoll-bg)', color: 'var(--sw-tile-opoll-fg)', labelKey: 'activities.typeSurvey' },
}

const TEMPLATE_CACHE_KEY = 'templateQuizIds'

function Dashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const dispatch = useDispatch()
  const { quizzes, folders, foldersVersion } = useSelector((s) => s.quiz)
  const { user } = useSelector((s) => s.auth)

  const [tierPlans, setTierPlans] = useState(null)
  const [bannerDismissed, setBannerDismissed] = useState(() => {
    const ts = localStorage.getItem('upgrade-banner-dismissed')
    return ts ? Date.now() - Number(ts) < 3 * 24 * 60 * 60 * 1000 : false
  })

  const [chooserOpen, setChooserOpen] = useState(false)
  const [homeStats, setHomeStats] = useState(null)
  const [templateModalOpen, setTemplateModalOpen] = useState(false)
  const [templates, setTemplates] = useState([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [usingTemplateId, setUsingTemplateId] = useState(null)

  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState(null)
  const [showArchived, setShowArchived] = useState(false)

  const selectedFolderId = useMemo(() => {
    const raw = searchParams.get('folder')
    return raw ? Number(raw) : undefined
  }, [searchParams])

  // Reload quizzes when folder structure changes (e.g. folder deleted moves quizzes to root)
  const folderVersionRef = useRef(foldersVersion)
  useEffect(() => {
    if (foldersVersion !== folderVersionRef.current) {
      folderVersionRef.current = foldersVersion
      loadQuizzes(showArchived)
    }
  }, [foldersVersion])

  useEffect(() => {
    loadQuizzes()
    authAPI.getTierPlans().then(r => setTierPlans(r.data)).catch(() => {})
    sessionAPI.homeStats().then(r => setHomeStats(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    document.body.classList.add('dashboard-scroll-active')
    return () => document.body.classList.remove('dashboard-scroll-active')
  }, [])

  const loadQuizzes = async (includeArchived) => {
    try {
      const res = await quizAPI.list(undefined, undefined, includeArchived)
      dispatch(setQuizzes(res.data))
    } catch (e) {
      console.error('Failed to load quizzes:', e)
    }
  }

  const handleDeleteQuiz = async (quizId) => {
    try {
      await quizAPI.delete(quizId)
      loadQuizzes(showArchived)
    } catch (e) {
      message.error(e?.response?.data?.detail || t('quiz.deleteFailed', { defaultValue: 'Failed to delete quiz' }))
      console.error('Failed to delete quiz:', e)
    }
  }

  const handleArchiveQuiz = async (quizId) => {
    try {
      await quizAPI.archive(quizId)
      message.success(t('quiz.archiveSuccess', { defaultValue: 'Activity archived' }))
      loadQuizzes(showArchived)
    } catch (e) {
      message.error(e?.response?.data?.detail || t('quiz.archiveFailed', { defaultValue: 'Failed to archive activity' }))
    }
  }

  const handleUnarchiveQuiz = async (quizId) => {
    try {
      await quizAPI.unarchive(quizId)
      message.success(t('quiz.unarchiveSuccess', { defaultValue: 'Activity restored' }))
      loadQuizzes(showArchived)
    } catch (e) {
      message.error(e?.response?.data?.detail || t('quiz.unarchiveFailed', { defaultValue: 'Failed to restore activity' }))
    }
  }

  const handleDuplicateQuiz = async (quizId) => {
    try {
      const res = await quizAPI.duplicate(quizId)
      message.success(t('quiz.duplicateSuccess', { defaultValue: 'Quiz duplicated successfully' }))
      loadQuizzes()
      navigate(`/quiz/${res.data.id}/edit`)
    } catch (e) {
      const detail = e?.response?.data?.detail
      message.error((typeof detail === 'string' ? detail : null) || t('quiz.duplicateFailed', { defaultValue: 'Failed to duplicate quiz' }))
    }
  }

  const handleStopActiveSession = async (sessionId) => {
    try {
      await sessionAPI.end(sessionId)
      message.success(t('quiz.activeSessionStopped', { defaultValue: 'Active session stopped' }))
      loadQuizzes()
    } catch (e) {
      message.error(e?.response?.data?.detail || t('quiz.failedToStopActiveSession', { defaultValue: 'Failed to stop active session' }))
    }
  }

  const handleToggleTemplate = async (quiz) => {
    const next = !quiz.is_template
    try {
      const res = await quizAPI.setTemplate(quiz.id, { is_template: next })
      const updated = { ...quiz, ...res.data, is_template: typeof res.data?.is_template === 'boolean' ? res.data.is_template : next }
      dispatch(setQuizzes((quizzes || []).map(q => q.id === updated.id ? { ...q, ...updated } : q)))
      const cached = new Set(JSON.parse(localStorage.getItem(TEMPLATE_CACHE_KEY) || '[]').filter(Number.isInteger))
      updated.is_template ? cached.add(updated.id) : cached.delete(updated.id)
      localStorage.setItem(TEMPLATE_CACHE_KEY, JSON.stringify([...cached]))
      message.success(next ? t('quiz.templateSetSuccess', { defaultValue: 'Template set successfully' }) : t('quiz.templateUnsetSuccess', { defaultValue: 'Template removed' }))
      loadQuizzes()
    } catch (e) {
      message.error(e.response?.data?.detail || t('quiz.templateSetFailed', { defaultValue: 'Failed to update template status' }))
    }
  }

  const openTemplateModal = async () => {
    setTemplateModalOpen(true)
    setTemplatesLoading(true)
    const cachedIds = JSON.parse(localStorage.getItem(TEMPLATE_CACHE_KEY) || '[]').filter(Number.isInteger)
    setTemplates((quizzes || []).filter(q => q.is_template || cachedIds.includes(q.id)).map(q => ({
      id: q.id, title: q.title, quiz_type: q.quiz_type || 'quiz',
      template_scope: q.template_scope || 'tenant', question_count: q.question_count || 0,
    })))
    try {
      let items = []
      try { items = (await quizAPI.listTemplates()).data || [] }
      catch { items = (await quizAPI.listTemplatesLegacy()).data || [] }
      if (items.length > 0) setTemplates(items)
    } catch (e) {
      message.error(e.response?.data?.detail || t('quiz.templateLoadFailed', { defaultValue: 'Failed to load templates' }))
    } finally {
      setTemplatesLoading(false)
    }
  }

  const handleUseTemplate = async (templateId) => {
    setUsingTemplateId(templateId)
    try {
      let res
      try { res = await quizAPI.useTemplate(templateId) }
      catch { res = await quizAPI.useTemplateLegacy(templateId) }
      message.success(t('quiz.templateUseSuccess', { defaultValue: 'Template quiz created' }))
      setTemplateModalOpen(false)
      loadQuizzes()
      navigate(`/quiz/${res.data.id}/edit`)
    } catch (e) {
      message.error(e.response?.data?.detail || t('quiz.templateUseFailed', { defaultValue: 'Failed to use template' }))
    } finally {
      setUsingTemplateId(null)
    }
  }

  // ── Derived data ──────────────────────────────────────────────────────────
  const filteredQuizzes = useMemo(() => {
    const term = searchText.trim().toLowerCase()
    return (quizzes || []).filter(q => {
      const matchSearch = !term || q.title.toLowerCase().includes(term)
      const matchFolder = selectedFolderId ? Number(q.folder_id) === Number(selectedFolderId) : q.folder_id == null
      const matchStatus = !statusFilter || q.status === statusFilter
      const matchArchived = showArchived ? !!q.archived_at : !q.archived_at
      return matchSearch && matchFolder && matchStatus && matchArchived
    })
  }, [quizzes, searchText, selectedFolderId, statusFilter, showArchived])

  const statistics = useMemo(() => {
    const all = quizzes || []
    const active = all.filter(q => !q.archived_at)
    return {
      total: active.length,
      byStatus: {
        ready: active.filter(q => q.status === 'ready').length,
        draft: active.filter(q => q.status === 'draft').length,
        archived: all.filter(q => !!q.archived_at).length,
      },
    }
  }, [quizzes])

  const activeSessions = useMemo(() => (quizzes || []).filter(q => q.has_active_session), [quizzes])

  // P2-4: Up next = non-archived ready quizzes (live-runnable types), up to 4
  const upNextQuizzes = useMemo(() => (quizzes || [])
    .filter(q => !q.archived_at && q.status === 'ready' && q.quiz_type !== 'exam' && q.quiz_type !== 'offline_poll')
    .slice(0, 4), [quizzes])

  // P2-4: Continue editing = 3 most recently updated drafts
  const recentDrafts = useMemo(() => (quizzes || [])
    .filter(q => !q.archived_at && q.status === 'draft')
    .sort((a, b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0))
    .slice(0, 3), [quizzes])

  const visibleTemplateData = useMemo(() => {
    if (templates?.length) return templates
    const cachedIds = JSON.parse(localStorage.getItem(TEMPLATE_CACHE_KEY) || '[]').filter(Number.isInteger)
    return (quizzes || []).filter(q => q.is_template || cachedIds.includes(q.id))
      .map(q => ({ id: q.id, title: q.title, quiz_type: q.quiz_type || 'quiz', template_scope: q.template_scope || 'tenant', question_count: q.question_count || 0 }))
  }, [templates, quizzes])

  const TIER_ORDER = ['free', 'basic', 'pro', 'enterprise']
  const TIER_COLOR = { free: '#8c8c8c', basic: '#1677ff', pro: '#722ed1', enterprise: '#d48806' }
  const currentTier = user?.tier || 'free'
  const currentTierIdx = TIER_ORDER.indexOf(currentTier)
  const nextTier = currentTierIdx >= 0 && currentTierIdx < TIER_ORDER.length - 1 ? TIER_ORDER[currentTierIdx + 1] : null
  const nextPlan = tierPlans?.find(p => p.tier === nextTier)
  const currentPlan = tierPlans?.find(p => p.tier === currentTier)
  const showBanner = !bannerDismissed && nextTier && currentPlan
  const maxQ = currentPlan?.max_questions ?? 0
  const usedQ = statistics.total
  const qPct = maxQ > 0 ? Math.min(100, Math.round((usedQ / maxQ) * 100)) : 0
  const nearLimit = qPct >= 70 || currentTier === 'free'

  const handleDismiss = () => {
    localStorage.setItem('upgrade-banner-dismissed', String(Date.now()))
    setBannerDismissed(true)
  }

  // ── Up Next helpers ───────────────────────────────────────────────────────
  const handleStartSession = (quiz) => navigate(`/quiz/${quiz.id}/control`)
  const handleCopyLink = (quiz) => {
    const url = quiz.poll_url || quiz.exam_url || `${window.location.origin}/join`
    navigator.clipboard.writeText(url)
    message.success(t('quiz.linkCopied', 'Link copied!'))
  }

  // ── Table action helpers ──────────────────────────────────────────────────
  const getPrimaryAction = (quiz) => {
    if (quiz.quiz_type === 'exam') return 'exam_results'
    if (quiz.quiz_type === 'offline_poll') return 'poll_results'
    if (quiz.has_active_session && quiz.active_session_id) return 'open'
    if (quiz.status === 'ready') return 'launch'
    return 'edit'
  }

  const getTypeTag = (type) => {
    const cfg = TYPE_TAG[type] || TYPE_TAG.quiz
    return (
      <Tag style={{ background: cfg.bg, color: cfg.color, border: 'none', borderRadius: 6, fontWeight: 500, fontSize: 12 }}>
        {t(cfg.labelKey)}
      </Tag>
    )
  }

  const getStatusTag = (status) => {
    const cfg = STATUS_TAG[status] || STATUS_TAG.draft
    return (
      <Tag style={{ background: cfg.bg, color: cfg.color, border: 'none', borderRadius: 6, fontWeight: 500, fontSize: 12 }}>
        {t(cfg.labelKey)}
      </Tag>
    )
  }

  const getMoreMenuItems = (quiz) => [
    {
      key: 'edit',
      label: t('common.edit', 'Edit'),
      icon: <EditOutlined />,
      onClick: () => navigate(`/quiz/${quiz.id}/edit`),
    },
    {
      key: 'duplicate',
      label: t('quiz.duplicate', 'Duplicate'),
      icon: <CopyOutlined />,
      onClick: () => handleDuplicateQuiz(quiz.id),
    },
    {
      key: 'history',
      label: t('quiz.history', 'History'),
      icon: <HistoryOutlined />,
      onClick: () => navigate(`/quiz/${quiz.id}/history`),
    },
    {
      key: 'template',
      label: quiz.is_template ? t('quiz.removeTemplate', 'Remove Template') : t('quiz.makeTemplate', 'Make Template'),
      icon: <StarOutlined />,
      onClick: () => handleToggleTemplate(quiz),
    },
    ...(quiz.quiz_type === 'exam' && quiz.exam_url ? [{
      key: 'copy_exam',
      label: t('exam.copyLink', 'Copy Exam Link'),
      icon: <LinkOutlined />,
      onClick: () => { navigator.clipboard.writeText(quiz.exam_url); message.success(t('exam.linkCopied', 'Link copied!')) },
    }] : []),
    ...(quiz.quiz_type === 'offline_poll' && quiz.poll_url ? [{
      key: 'copy_poll',
      label: t('offlinePoll.copyLink', 'Copy Poll Link'),
      icon: <LinkOutlined />,
      onClick: () => { navigator.clipboard.writeText(quiz.poll_url); message.success(t('offlinePoll.linkCopied', 'Link copied!')) },
    }] : []),
    ...(quiz.has_active_session && quiz.active_session_id ? [{
      key: 'stop',
      label: t('quiz.stopActiveSession', 'Stop Session'),
      icon: <StopOutlined />,
      danger: true,
      onClick: () => {},
    }] : []),
    { type: 'divider' },
    quiz.archived_at ? {
      key: 'unarchive',
      label: t('quiz.unarchive', { defaultValue: 'Restore' }),
      icon: <HistoryOutlined />,
      onClick: () => handleUnarchiveQuiz(quiz.id),
    } : {
      key: 'archive',
      label: t('quiz.archive', { defaultValue: 'Archive' }),
      icon: <InboxOutlined />,
      onClick: () => handleArchiveQuiz(quiz.id),
    },
    {
      key: 'delete',
      label: t('common.delete', 'Delete'),
      icon: <DeleteOutlined />,
      danger: true,
      onClick: () => {},
    },
  ]

  // ── Table columns ─────────────────────────────────────────────────────────
  const tableColumns = [
    {
      title: t('quiz.title', 'Name'),
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 600, color: C.text1, lineHeight: 1.4, cursor: 'pointer' }}
            onClick={() => navigate(`/quiz/${record.id}/edit`)}
          >
            {text}
          </div>
          {record.has_active_session && (
            <Badge status="processing" text={<span style={{ fontSize: 11, color: C.success }}>Live</span>} />
          )}
          {record.is_template && (
            <Tag style={{ fontSize: 10, padding: '0 5px', marginLeft: 4, background: C.primary50, color: C.primary, border: 'none' }}>
              Template
            </Tag>
          )}
        </div>
      ),
    },
    {
      title: t('dashboard.type', 'Type'),
      dataIndex: 'quiz_type',
      key: 'quiz_type',
      width: 130,
      render: (type) => getTypeTag(type),
    },
    {
      title: t('quiz.status', 'Status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status, record) => {
        if (record.has_active_session) {
          return <Tag style={{ background: 'var(--sw-chip-live-bg)', color: 'var(--sw-chip-live-fg)', border: 'none', borderRadius: 6 }}>Live</Tag>
        }
        return getStatusTag(status)
      },
    },
    {
      title: t('quiz.questions', 'Questions'),
      dataIndex: 'question_count',
      key: 'question_count',
      width: 100,
      responsive: ['md'],
      render: (count) => <span style={{ color: C.text3, fontSize: 13 }}>{count || 0}</span>,
    },
    {
      title: t('dashboard.created', 'Created'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 130,
      responsive: ['lg'],
      render: (date) => date
        ? <span style={{ color: C.text3, fontSize: 12 }}>{new Date(date).toLocaleDateString()}</span>
        : '—',
    },
    {
      title: t('common.actions', 'Actions'),
      key: 'actions',
      width: 200,
      render: (_, quiz) => {
        const primaryAction = getPrimaryAction(quiz)
        return (
          <Space size={6}>
            {primaryAction === 'launch' && (
              <Button
                type="primary"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => navigate(`/quiz/${quiz.id}/control`)}
                style={{ background: C.success, borderColor: C.success }}
              >
                {t('quiz.startQuiz', 'Launch')}
              </Button>
            )}
            {primaryAction === 'open' && (
              <Button
                type="primary"
                size="small"
                icon={<WifiOutlined />}
                onClick={() => navigate(`/quiz/${quiz.id}/control`)}
              >
                {t('quiz.openRoom', 'Open Room')}
              </Button>
            )}
            {primaryAction === 'edit' && (
              <Button
                size="small"
                icon={<EditOutlined />}
                onClick={() => navigate(`/quiz/${quiz.id}/edit`)}
              >
                {t('quiz.continue', 'Continue')}
              </Button>
            )}
            {primaryAction === 'exam_results' && (
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={() => navigate(`/quiz/${quiz.id}/exam-results`)}
              >
                {t('exam.resultsTitle', 'Results')}
              </Button>
            )}
            {primaryAction === 'poll_results' && (
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={() => navigate(`/quiz/${quiz.id}/offline-results`)}
              >
                {t('offlinePoll.viewResults', 'Results')}
              </Button>
            )}
            {/* Wrap destructive actions in their own handlers via Dropdown onClick */}
            <Dropdown
              trigger={['click']}
              menu={{
                items: getMoreMenuItems(quiz).map(item => ({
                  ...item,
                  onClick: item.key === 'delete' ? undefined : item.onClick,
                })),
                onClick: async ({ key }) => {
                  if (key === 'delete') {
                    // handled separately via Popconfirm — skip
                  }
                },
              }}
              dropdownRender={(menu) => (
                <div>
                  {/* Render the dropdown, but intercept delete */}
                  <div className="dashboard-more-menu">
                    {getMoreMenuItems(quiz).map(item => {
                      if (item.type === 'divider') return <div key="div" style={{ borderTop: `1px solid ${C.border}`, margin: '4px 0' }} />
                      if (item.key === 'delete') {
                        return (
                          <Popconfirm
                            key="delete"
                            title={t('quiz.deleteConfirm', 'Delete this quiz?')}
                            description={t('quiz.deleteWarning', 'This action cannot be undone.')}
                            onConfirm={() => handleDeleteQuiz(quiz.id)}
                            okText={t('common.delete', 'Delete')}
                            okButtonProps={{ danger: true }}
                            cancelText={t('common.cancel', 'Cancel')}
                          >
                            <div className="dashboard-more-menu-item dashboard-more-menu-item--danger">
                              <DeleteOutlined />
                              <span>{t('common.delete', 'Delete')}</span>
                            </div>
                          </Popconfirm>
                        )
                      }
                      if (item.key === 'stop') {
                        return (
                          <Popconfirm
                            key="stop"
                            title={t('quiz.stopActiveSessionConfirm', 'Stop active session?')}
                            description={t('quiz.stopQuizConfirm', 'This will end the session for all participants.')}
                            onConfirm={() => handleStopActiveSession(quiz.active_session_id)}
                            okText={t('quiz.stopQuizOk', 'Yes, stop it')}
                            okButtonProps={{ danger: true }}
                            cancelText={t('common.cancel', 'Cancel')}
                          >
                            <div className="dashboard-more-menu-item dashboard-more-menu-item--danger">
                              <StopOutlined />
                              <span>{t('quiz.stopActiveSession', 'Stop Session')}</span>
                            </div>
                          </Popconfirm>
                        )
                      }
                      return (
                        <div
                          key={item.key}
                          className={`dashboard-more-menu-item${item.danger ? ' dashboard-more-menu-item--danger' : ''}`}
                          onClick={item.onClick}
                        >
                          {item.icon}
                          <span>{item.label}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            >
              <Button size="small" icon={<MoreOutlined />} />
            </Dropdown>
          </Space>
        )
      },
    },
  ]

  // ── Hero illustration (abstract SVG) ──────────────────────────────────────
  const HeroIllustration = (
    <svg width="220" height="170" viewBox="0 0 220 170" fill="none" xmlns="http://www.w3.org/2000/svg" className="hero-illustration">
      {/* Laptop base */}
      <rect x="18" y="18" width="164" height="108" rx="10" fill="#C7D2FE" opacity="0.5" />
      <rect x="26" y="26" width="148" height="92" rx="6" fill="#EEF2FF" />
      {/* Screen content */}
      <rect x="38" y="38" width="72" height="9" rx="4" fill="#6366F1" opacity="0.75" />
      <rect x="38" y="54" width="48" height="7" rx="3" fill="#A5B4FC" opacity="0.9" />
      <rect x="38" y="67" width="60" height="7" rx="3" fill="#A5B4FC" opacity="0.7" />
      <rect x="38" y="80" width="42" height="7" rx="3" fill="#C7D2FE" opacity="0.8" />
      <rect x="38" y="93" width="55" height="7" rx="3" fill="#C7D2FE" opacity="0.6" />
      {/* Bar chart */}
      <rect x="122" y="84" width="11" height="28" rx="3" fill="#6366F1" opacity="0.85" />
      <rect x="138" y="68" width="11" height="44" rx="3" fill="#4F46E5" />
      <rect x="154" y="76" width="11" height="36" rx="3" fill="#818CF8" opacity="0.8" />
      {/* Status dot */}
      <circle cx="128" cy="44" r="5" fill="#10B981" />
      <rect x="136" y="40" width="28" height="8" rx="4" fill="#D1FAE5" />
      {/* Laptop stand */}
      <rect x="8" y="126" width="184" height="12" rx="5" fill="#C7D2FE" opacity="0.4" />
      {/* Floating badges */}
      <rect x="160" y="6" width="52" height="22" rx="8" fill="#FDF4FF" />
      <circle cx="171" cy="17" r="5" fill="#DB2777" opacity="0.7" />
      <rect x="179" y="13" width="25" height="8" rx="4" fill="#FBCFE8" />
      <rect x="0" y="94" width="28" height="28" rx="8" fill="#ECFDF5" />
      <rect x="6" y="100" width="16" height="7" rx="3" fill="#6EE7B7" />
      <rect x="6" y="110" width="10" height="6" rx="3" fill="#A7F3D0" />
    </svg>
  )

  return (
    <div className="dashboard-scroll">
      <div className="dashboard-page">

        {/* ── Hero Section ────────────────────────────────────────────────── */}
        <div className="hero-section">
          <div className="hero-content">
            <div className="hero-left">
              <Title level={2} style={{ color: C.text1, margin: 0, lineHeight: 1.2 }}>
                {t('dashboard.welcomeBack', { name: user?.full_name?.split(' ')[0] || '', defaultValue: `Welcome back, ${user?.full_name?.split(' ')[0] || 'there'} 👋` })}
              </Title>
              <Text style={{ color: C.text3, fontSize: 16, display: 'block', marginTop: 8 }}>
                {t('dashboard.heroSubtitle', 'Create quizzes, polls and assessments in minutes.')}
              </Text>
              <Space size={12} style={{ marginTop: 24 }} wrap>
                <Button type="primary" size="large" icon={<PlusOutlined />}
                  onClick={() => setChooserOpen(true)}
                  style={{ background: C.primary, borderColor: C.primary, fontWeight: 600, paddingInline: 24 }}>
                  {t('dashboard.createNew', 'Create New')}
                </Button>
                <Button size="large" onClick={() => navigate('/templates')}
                  style={{ color: C.text2, fontWeight: 500 }}>
                  <StarOutlined /> {t('quiz.useTemplate', 'Use Template')}
                </Button>
              </Space>
            </div>
            <div className="hero-right">
              {HeroIllustration}
            </div>
          </div>
        </div>

        {/* ── Create Activity Section ──────────────────────────────────── */}
        <section className="section-block">
          <Title level={5} style={{ color: C.text2, marginBottom: 16 }}>
            {t('dashboard.createActivityTitle', 'What would you like to create today?')}
          </Title>
          <Row gutter={[16, 16]}>
            {ACTIVITY_TYPES.map(type => (
              <Col xs={12} sm={12} md={6} key={type.key}>
                <Card
                  hoverable
                  onClick={() => navigate(`/quiz/new?type=${type.key}`)}
                  style={{
                    background: type.bg,
                    border: 'none',
                    borderRadius: 16,
                    cursor: 'pointer',
                    height: '100%',
                    transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                  }}
                  styles={{ body: { padding: 20 } }}
                  className="activity-type-card"
                >
                  <div style={{
                    width: 52, height: 52, borderRadius: 14,
                    background: type.iconBg,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    marginBottom: 14,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                  }}>
                    <type.Icon style={{ fontSize: 24, color: type.iconColor }} />
                  </div>
                  <div style={{ fontWeight: 700, color: C.text1, fontSize: 15, marginBottom: 6 }}>
                    {t(type.titleKey, type.defaultTitle)}
                  </div>
                  <div style={{ color: C.text3, fontSize: 13, lineHeight: 1.5 }}>
                    {t(type.descKey, type.defaultDesc)}
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </section>

        {/* ── Workflow Summary ─────────────────────────────────────────── */}
        {/* ── This week stats ─────────────────────────────────────────── */}
        <section className="section-block">
          <Row gutter={[16, 16]}>
            {[
              {
                key: 'sessions',
                title: t('dashboard.sessionsThisWeek', 'Sessions this week'),
                count: homeStats?.sessions_this_week ?? '—',
                Icon: PlayCircleOutlined,
                bg: 'var(--sw-stat-ready-bg)', accent: C.success,
              },
              {
                key: 'participants',
                title: t('dashboard.participantsThisWeek', 'Participants this week'),
                count: homeStats?.participants_this_week ?? '—',
                Icon: WifiOutlined,
                bg: 'var(--sw-stat-works-bg)', accent: C.warning,
              },
              {
                key: 'score',
                title: t('dashboard.avgScoreThisWeek', 'Avg score this week'),
                count: homeStats?.avg_score_this_week != null ? `${homeStats.avg_score_this_week}%` : '—',
                Icon: BarChartOutlined,
                bg: 'var(--sw-stat-past-bg)', accent: C.blue,
              },
            ].map(card => (
              <Col xs={24} sm={8} key={card.key}>
                <Card
                  style={{ background: card.bg, border: 'none', borderRadius: 16 }}
                  styles={{ body: { padding: '20px 24px' } }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ fontSize: 36, fontWeight: 800, color: card.accent, lineHeight: 1 }}>
                        {card.count}
                      </div>
                      <div style={{ fontWeight: 600, color: C.text2, marginTop: 4, fontSize: 13 }}>
                        {card.title}
                      </div>
                    </div>
                    <div style={{
                      width: 44, height: 44, borderRadius: 12,
                      background: 'var(--sw-stat-icon-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                    }}>
                      <card.Icon style={{ fontSize: 20, color: card.accent }} />
                    </div>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </section>

        {/* ── Up Next ─────────────────────────────────────────────────── */}
        {upNextQuizzes.length > 0 && (
          <section className="section-block">
            <Title level={5} style={{ color: C.text2, marginBottom: 14 }}>
              {t('dashboard.upNext', 'Up Next')}
            </Title>
            <Row gutter={[12, 12]}>
              {upNextQuizzes.map(q => {
                const typeConf = TYPE_TAG[q.quiz_type] || TYPE_TAG.quiz
                return (
                  <Col xs={24} sm={12} md={6} key={q.id}>
                    <Card
                      style={{ background: typeConf.bg, border: 'none', borderRadius: 14 }}
                      styles={{ body: { padding: '16px' } }}
                    >
                      <Tag color={typeConf.bg} style={{ color: typeConf.color, border: 'none', fontWeight: 700, fontSize: 10, marginBottom: 8, padding: '2px 8px' }}>
                        {typeConf.label}
                      </Tag>
                      <div style={{ fontWeight: 700, color: C.text1, fontSize: 14, marginBottom: 12, lineHeight: 1.3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {q.title}
                      </div>
                      <Space size={6} wrap>
                        <Button size="small" type="primary" icon={<PlayCircleOutlined />}
                          style={{ fontSize: 12 }}
                          onClick={() => handleStartSession(q)}>
                          {t('quiz.run', 'Run')}
                        </Button>
                        <Button size="small" icon={<LinkOutlined />}
                          style={{ fontSize: 12 }}
                          onClick={() => handleCopyLink(q)}>
                          {t('quiz.copyLink', 'Link')}
                        </Button>
                      </Space>
                    </Card>
                  </Col>
                )
              })}
            </Row>
          </section>
        )}

        {/* ── Continue Editing + Last Session ─────────────────────────── */}
        {(recentDrafts.length > 0 || homeStats?.last_session) && (
          <section className="section-block">
            <Row gutter={[16, 16]}>
              {recentDrafts.length > 0 && (
                <Col xs={24} md={homeStats?.last_session ? 14 : 24}>
                  <Title level={5} style={{ color: C.text2, marginBottom: 12 }}>
                    {t('dashboard.continueEditing', 'Continue Editing')}
                  </Title>
                  <Card style={{ border: 'none', borderRadius: 14, background: C.bgCard }} styles={{ body: { padding: '4px 0' } }}>
                    {recentDrafts.map((q, i) => {
                      const typeConf = TYPE_TAG[q.quiz_type] || TYPE_TAG.quiz
                      return (
                        <div key={q.id} style={{
                          display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
                          borderBottom: i < recentDrafts.length - 1 ? `1px solid ${C.border}` : 'none',
                        }}>
                          <div style={{
                            width: 36, height: 36, borderRadius: 10,
                            background: typeConf.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                          }}>
                            <EditOutlined style={{ color: typeConf.color, fontSize: 14 }} />
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontWeight: 600, color: C.text1, fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {q.title}
                            </div>
                            <div style={{ fontSize: 11, color: C.text3 }}>
                              {q.question_count === 1 ? t('dashboard.oneQuestion', '1 question') : `${q.question_count || 0} ${t('dashboard.questions', 'questions')}`} · {typeConf.label}
                            </div>
                          </div>
                          <Button size="small" icon={<EditOutlined />}
                            onClick={() => navigate(`/quiz/${q.id}/edit`)}>
                            {t('common.edit', 'Edit')}
                          </Button>
                        </div>
                      )
                    })}
                  </Card>
                </Col>
              )}
              {homeStats?.last_session && (
                <Col xs={24} md={recentDrafts.length > 0 ? 10 : 24}>
                  <Title level={5} style={{ color: C.text2, marginBottom: 12 }}>
                    {t('dashboard.lastSession', 'Last Session')}
                  </Title>
                  <Card style={{ border: 'none', borderRadius: 14, background: C.bgCard }} styles={{ body: { padding: '16px' } }}>
                    {(() => {
                      const ls = homeStats.last_session
                      const typeConf = TYPE_TAG[ls.quiz_type] || TYPE_TAG.quiz
                      return (
                        <>
                          <Tag color={typeConf.bg} style={{ color: typeConf.color, border: 'none', fontWeight: 700, fontSize: 10, marginBottom: 8 }}>
                            {typeConf.label}
                          </Tag>
                          <div style={{ fontWeight: 700, color: C.text1, fontSize: 15, marginBottom: 8 }}>{ls.quiz_title}</div>
                          <Row gutter={16} style={{ marginBottom: 12 }}>
                            <Col span={12}>
                              <div style={{ fontSize: 22, fontWeight: 800, color: C.primary }}>{ls.participant_count}</div>
                              <div style={{ fontSize: 11, color: C.text3 }}>{t('dashboard.joined', 'joined')}</div>
                            </Col>
                            {ls.avg_score != null && (
                              <Col span={12}>
                                <div style={{ fontSize: 22, fontWeight: 800, color: C.success }}>{ls.avg_score}%</div>
                                <div style={{ fontSize: 11, color: C.text3 }}>{t('dashboard.avgCorrect', 'avg correct')}</div>
                              </Col>
                            )}
                          </Row>
                          <Button size="small" icon={<BarChartOutlined />}
                            onClick={() => navigate(`/quiz/${ls.quiz_id}/sessions`)}>
                            {t('dashboard.viewRecap', 'View recap →')}
                          </Button>
                        </>
                      )
                    })()}
                  </Card>
                </Col>
              )}
            </Row>
          </section>
        )}

        {/* ── Upgrade Banner ───────────────────────────────────────────── */}
        {showBanner && (
          <div className="upgrade-banner" style={{ '--tier-color': TIER_COLOR[nextTier] }}>
            <ThunderboltOutlined style={{ fontSize: 22, color: TIER_COLOR[nextTier], flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2, color: C.text1 }}>
                {nearLimit
                  ? t('dashboard.upgradeBannerNearLimit', { pct: qPct })
                  : <>
                      {t('dashboard.upgradeBannerOnPlan')}
                      <Tag color={TIER_COLOR[nextTier]} style={{ textTransform: 'uppercase', fontWeight: 700, fontSize: 11, margin: '0 4px' }}>{currentTier}</Tag>
                      {t('dashboard.upgradeBannerPlan')}
                    </>}
              </div>
              {nextPlan && (
                <div style={{ fontSize: 13, color: 'var(--sw-text2)' }}>
                  {t('dashboard.upgradeBannerNextTier', {
                    tier: nextTier.charAt(0).toUpperCase() + nextTier.slice(1),
                    participants: nextPlan.max_participants.toLocaleString(),
                    questions: nextPlan.max_questions,
                    sessions: nextPlan.max_concurrent_events,
                  })}
                </div>
              )}
              {nearLimit && (
                <Progress percent={qPct} size="small"
                  strokeColor={qPct >= 90 ? '#ff4d4f' : '#faad14'}
                  style={{ marginTop: 6, maxWidth: 260 }}
                  format={() => t('dashboard.upgradeBannerQuizUsage', { used: usedQ, max: maxQ })} />
              )}
            </div>
            <Space>
              <Button type="primary" icon={<ArrowUpOutlined />} size="small"
                href="mailto:info@chakrix.net?subject=Upgrade%20Enquiry"
                style={{ background: TIER_COLOR[nextTier], borderColor: TIER_COLOR[nextTier] }}>
                {t('dashboard.upgradeBannerCta', { tier: nextTier.charAt(0).toUpperCase() + nextTier.slice(1) })}
              </Button>
              <Button type="text" icon={<CloseOutlined />} size="small" onClick={handleDismiss} style={{ color: 'var(--sw-text3)' }} />
            </Space>
          </div>
        )}

        {/* ── Activity Table + Live Sessions ──────────────────────────── */}
        <section className="section-block explorer-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <Title level={5} style={{ color: C.text2, margin: 0 }}>
              {t('dashboard.allActivities', 'All Activities')}
            </Title>
            <Button size="small" type="link" onClick={() => navigate('/activities')}>
              {t('dashboard.viewAll', 'View all →')}
            </Button>
          </div>
          {/* Toolbar */}
          <div className="explorer-toolbar">
            <Input
              prefix={<SearchOutlined style={{ color: C.text3 }} />}
              allowClear
              placeholder={t('dashboard.searchQuizzes', 'Search activities…')}
              style={{ maxWidth: 300, borderRadius: 10 }}
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
            />

            {statusFilter && (
              <Tag
                closable
                onClose={() => setStatusFilter(null)}
                style={{ background: C.primary50, color: C.primary, border: `1px solid ${C.primary100}`, borderRadius: 8, fontSize: 12 }}
              >
                Status: {statusFilter}
              </Tag>
            )}
            <Button
              size="small"
              icon={<InboxOutlined />}
              type={showArchived ? 'primary' : 'default'}
              onClick={() => {
                const next = !showArchived
                setShowArchived(next)
                loadQuizzes(next)
              }}
              style={{ borderRadius: 8 }}
            >
              {showArchived ? t('quiz.hideArchived', { defaultValue: 'Hide archived' }) : t('quiz.showArchived', { defaultValue: 'Show archived' })}
            </Button>
          </div>

          {/* Content */}
          <div className="explorer-layout">
            <div className="activity-pane">
              {filteredQuizzes.length === 0 && !searchText.trim() && !selectedFolderId && !statusFilter ? (
                /* Empty state */
                <div className="empty-state">
                  <div style={{ fontSize: 20, fontWeight: 700, color: C.text1, marginBottom: 8 }}>
                    {t('tooltip.emptyStateTitle', 'Create your first activity')}
                  </div>
                  <div style={{ color: C.text3, marginBottom: 32, fontSize: 14 }}>
                    {t('tooltip.emptyStateSubtitle', 'Pick an activity type to get started.')}
                  </div>
                  <Row gutter={[16, 16]} justify="center">
                    {ACTIVITY_TYPES.map(type => (
                      <Col xs={12} sm={12} md={6} key={type.key}>
                        <Card hoverable onClick={() => navigate(`/quiz/new?type=${type.key}`)}
                          style={{ borderTop: `3px solid ${type.iconColor}`, cursor: 'pointer', borderRadius: 12 }}
                          styles={{ body: { padding: '20px 16px', textAlign: 'center' } }}
                        >
                          <type.Icon style={{ fontSize: 28, color: type.iconColor, marginBottom: 8 }} />
                          <div style={{ fontWeight: 600, color: C.text1, marginBottom: 4 }}>{t(type.titleKey, type.defaultTitle)}</div>
                          <div style={{ fontSize: 12, color: C.text3 }}>{t(type.descKey, type.defaultDesc)}</div>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </div>
              ) : (
                <Table
                  rowKey="id"
                  dataSource={filteredQuizzes}
                  columns={tableColumns}
                  pagination={{
                    pageSize: 12,
                    showSizeChanger: false,
                    showTotal: (total) => `${total} ${t('quiz.activities', 'activities')}`,
                    style: { marginTop: 8 },
                  }}
                  size="middle"
                  scroll={{ x: 600 }}
                  style={{ background: C.bgCard, borderRadius: 12 }}
                  rowClassName="activity-table-row"
                  locale={{
                    emptyText: (
                      <div style={{ padding: '32px 16px', color: C.text3 }}>
                        {t('quiz.noQuizzes', 'No activities found.')}
                      </div>
                    ),
                  }}
                />
              )}
            </div>

          </div>
        </section>

        {/* ── Modals ──────────────────────────────────────────────────── */}
        <CreateChooser open={chooserOpen} onClose={() => setChooserOpen(false)} />

        <Modal
          title={t('quiz.templateLibrary', 'Template Library')}
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
              { title: t('quiz.title', 'Title'), dataIndex: 'title' },
              {
                title: t('dashboard.type', 'Type'),
                dataIndex: 'quiz_type',
                width: 110,
                render: v => getTypeTag(v),
              },
              {
                title: t('quiz.scope', 'Scope'),
                dataIndex: 'template_scope',
                width: 160,
                render: v => (
                  <Tag color={v === 'global' ? 'purple' : 'blue'}>
                    {v === 'global' ? t('quiz.globalTemplate', 'Global Template') : t('quiz.tenantTemplate', 'Tenant Template')}
                  </Tag>
                ),
              },
              { title: t('quiz.questions', 'Questions'), dataIndex: 'question_count', width: 120 },
              {
                title: t('common.actions', 'Actions'),
                width: 180,
                render: (_, rec) => (
                  <Button type="primary" loading={usingTemplateId === rec.id}
                    onClick={() => handleUseTemplate(rec.id)}>
                    {t('quiz.useTemplate', 'Use Template')}
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
