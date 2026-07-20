import { useEffect, useMemo, useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSelector, useDispatch } from 'react-redux'
import {
  Button, Tag, Space, Tooltip, message,
  Input, Table, Typography, Badge, Select, Alert, Grid,
} from 'antd'
import SafeConfirm from '../../components/SafeConfirm'

const { useBreakpoint } = Grid
import {
  PlayCircleOutlined, EditOutlined, DeleteOutlined, CopyOutlined,
  FileTextOutlined, CheckCircleOutlined, HistoryOutlined, StarOutlined,
  BarChartOutlined, LinkOutlined, WifiOutlined, EyeOutlined,
  StopOutlined, SearchOutlined, InboxOutlined, FilterOutlined,
  WarningOutlined, ThunderboltOutlined,
} from '@ant-design/icons'
import { setQuizzes } from '../../store/quizSlice'
import { quizAPI, sessionAPI } from '../../services/api'
import MoreActionsMenu from '../../components/MoreActionsMenu'
import '../dashboard/Dashboard.css'

const { Title, Text } = Typography

const C = {
  primary:   'var(--sw-primary)',
  primary50: 'var(--sw-primary-soft)',
  success:   'var(--sw-success)',
  warning:   'var(--sw-warning)',
  error:     'var(--sw-error)',
  blue:      'var(--sw-info)',
  orange:    'var(--sw-tile-poll-fg)',
  text1:     'var(--sw-text1)',
  text2:     'var(--sw-text2)',
  text3:     'var(--sw-text3)',
  bg:        'var(--sw-bg)',
  bgCard:    'var(--sw-card)',
  border:    'var(--sw-border)',
}

const TYPE_TAG = {
  quiz:         { bg: 'var(--sw-tile-quiz-bg)',  color: 'var(--sw-tile-quiz-fg)',  labelKey: 'activities.typeQuiz' },
  exam:         { bg: 'var(--sw-tile-exam-bg)',  color: 'var(--sw-tile-exam-fg)',  labelKey: 'activities.typeExam' },
  poll:         { bg: 'var(--sw-tile-poll-bg)',  color: 'var(--sw-tile-poll-fg)',  labelKey: 'activities.typePoll' },
  offline_poll: { bg: 'var(--sw-tile-opoll-bg)', color: 'var(--sw-tile-opoll-fg)', labelKey: 'activities.typeSurvey' },
}

const STATUS_TAG = {
  ready:    { bg: 'var(--sw-chip-ready-bg)', color: 'var(--sw-chip-ready-fg)', labelKey: 'activities.statusReady' },
  draft:    { bg: 'var(--sw-chip-draft-bg)', color: 'var(--sw-chip-draft-fg)', labelKey: 'activities.statusDraft' },
  archived: { bg: 'var(--sw-chip-done-bg)',  color: 'var(--sw-chip-done-fg)',  labelKey: 'activities.statusArchived' },
}

export default function Activities() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const dispatch = useDispatch()
  const { quizzes } = useSelector((s) => s.quiz)
  const screens = useBreakpoint()
  const isMobile = !screens.md

  const [searchText, setSearchText] = useState('')
  const [typeFilter, setTypeFilter] = useState(null)
  const [statusFilter, setStatusFilter] = useState(null)
  const [showArchived, setShowArchived] = useState(false)
  const [attentionFilter, setAttentionFilter] = useState(false)
  const [sortBy, setSortBy] = useState('created_at')
  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const [bulkLoading, setBulkLoading] = useState(false)
  const [confirmBulkArchive, setConfirmBulkArchive] = useState(false)
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false)

  const loadQuizzes = useCallback(async (includeArchived) => {
    try {
      const res = await quizAPI.list(undefined, undefined, includeArchived)
      dispatch(setQuizzes(res.data))
    } catch (e) {
      console.error('Failed to load quizzes:', e)
    }
  }, [dispatch])

  useEffect(() => {
    loadQuizzes(showArchived)
  }, [showArchived, loadQuizzes])

  const filteredQuizzes = useMemo(() => {
    const term = searchText.trim().toLowerCase()
    let list = (quizzes || []).filter(q => {
      const matchSearch = !term || q.title.toLowerCase().includes(term)
      const matchType = !typeFilter || q.quiz_type === typeFilter
      const matchStatus = !statusFilter || q.status === statusFilter
      const matchArchived = showArchived ? !!q.archived_at : !q.archived_at
      const matchAttention = !attentionFilter || (q.status === 'draft' && (q.question_count || 0) === 0)
      return matchSearch && matchType && matchStatus && matchArchived && matchAttention
    })
    list = [...list].sort((a, b) => {
      const aVal = new Date(sortBy === 'created_at' ? (a.created_at || 0) : (a.updated_at || a.created_at || 0))
      const bVal = new Date(sortBy === 'created_at' ? (b.created_at || 0) : (b.updated_at || b.created_at || 0))
      return bVal - aVal
    })
    return list
  }, [quizzes, searchText, typeFilter, statusFilter, showArchived, attentionFilter, sortBy])

  const needsAttentionCount = useMemo(() =>
    (quizzes || []).filter(q => !q.archived_at && q.status === 'draft' && (q.question_count || 0) === 0).length,
    [quizzes])

  const handleDeleteQuiz = async (quizId) => {
    try {
      await quizAPI.delete(quizId)
      loadQuizzes(showArchived)
    } catch (e) {
      message.error(e?.response?.data?.detail || t('quiz.deleteFailed', 'Failed to delete'))
    }
  }

  const handleArchiveQuiz = async (quizId) => {
    try {
      await quizAPI.archive(quizId)
      message.success(t('quiz.archiveSuccess', 'Activity archived'))
      loadQuizzes(showArchived)
    } catch (e) {
      message.error(e?.response?.data?.detail || t('quiz.archiveFailed', 'Failed to archive'))
    }
  }

  const handleUnarchiveQuiz = async (quizId) => {
    try {
      await quizAPI.unarchive(quizId)
      message.success(t('quiz.unarchiveSuccess', 'Activity restored'))
      loadQuizzes(showArchived)
    } catch (e) {
      message.error(e?.response?.data?.detail || t('quiz.unarchiveFailed', 'Failed to restore'))
    }
  }

  const handleDuplicateQuiz = async (quizId) => {
    try {
      const res = await quizAPI.duplicate(quizId)
      message.success(t('quiz.duplicateSuccess', 'Duplicated'))
      loadQuizzes()
      navigate(`/quiz/${res.data.id}/edit`)
    } catch (e) {
      message.error(e?.response?.data?.detail || t('quiz.duplicateFailed', 'Failed to duplicate'))
    }
  }

  const handleStopActiveSession = async (sessionId) => {
    try {
      await sessionAPI.end(sessionId)
      message.success(t('quiz.activeSessionStopped', 'Session stopped'))
      loadQuizzes()
    } catch (e) {
      message.error(e?.response?.data?.detail || t('quiz.failedToStopActiveSession', 'Failed to stop session'))
    }
  }

  const handleToggleTemplate = async (quiz) => {
    try {
      if (quiz.is_template) await quizAPI.removeTemplate(quiz.id)
      else await quizAPI.makeTemplate(quiz.id)
      message.success(quiz.is_template ? t('quiz.removedTemplate', 'Removed template') : t('quiz.madeTemplate', 'Made template'))
      loadQuizzes()
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed')
    }
  }

  // Bulk actions
  const handleBulkArchive = async () => {
    setBulkLoading(true)
    try {
      await Promise.all(selectedRowKeys.map(id => quizAPI.archive(id)))
      message.success(t('activities.bulkArchived', `Archived ${selectedRowKeys.length} activities`))
      setSelectedRowKeys([])
      loadQuizzes(showArchived)
    } catch (e) {
      message.error(t('activities.bulkArchiveFailed', 'Some archives failed'))
    } finally {
      setBulkLoading(false)
    }
  }

  const handleBulkDelete = async () => {
    setBulkLoading(true)
    try {
      await Promise.all(selectedRowKeys.map(id => quizAPI.delete(id)))
      message.success(t('activities.bulkDeleted', `Deleted ${selectedRowKeys.length} activities`))
      setSelectedRowKeys([])
      loadQuizzes(showArchived)
    } catch (e) {
      message.error(t('activities.bulkDeleteFailed', 'Some deletes failed'))
    } finally {
      setBulkLoading(false)
    }
  }

  const getPrimaryAction = (quiz) => {
    if (quiz.has_active_session && quiz.active_session_id) return 'open'
    if (quiz.status === 'ready' && quiz.quiz_type !== 'offline_poll' && quiz.quiz_type !== 'exam') return 'launch'
    if (quiz.status === 'draft') return 'edit'
    if (quiz.quiz_type === 'exam') return 'exam_results'
    if (quiz.quiz_type === 'offline_poll') return 'poll_results'
    return 'edit'
  }

  const getTypeTag = (type) => {
    const cfg = TYPE_TAG[type] || TYPE_TAG.quiz
    return <Tag style={{ background: cfg.bg, color: cfg.color, border: 'none', borderRadius: 6, fontWeight: 500, fontSize: 12 }}>{t(cfg.labelKey)}</Tag>
  }

  const getStatusTag = (status) => {
    const cfg = STATUS_TAG[status] || STATUS_TAG.draft
    return <Tag style={{ background: cfg.bg, color: cfg.color, border: 'none', borderRadius: 6, fontWeight: 500, fontSize: 12 }}>{t(cfg.labelKey)}</Tag>
  }

  const getMoreMenuItems = (quiz) => [
    { key: 'edit', label: t('common.edit', 'Edit'), icon: <EditOutlined />, onClick: () => navigate(`/quiz/${quiz.id}/edit`) },
    { key: 'duplicate', label: t('quiz.duplicate', 'Duplicate'), icon: <CopyOutlined />, onClick: () => handleDuplicateQuiz(quiz.id) },
    { key: 'history', label: t('quiz.history', 'History'), icon: <HistoryOutlined />, onClick: () => navigate(`/quiz/${quiz.id}/sessions`) },
    { key: 'template', label: quiz.is_template ? t('quiz.removeTemplate', 'Remove Template') : t('quiz.makeTemplate', 'Make Template'), icon: <StarOutlined />, onClick: () => handleToggleTemplate(quiz) },
    ...(quiz.quiz_type === 'exam' && quiz.exam_url ? [{ key: 'copy_exam', label: t('exam.copyLink', 'Copy Exam Link'), icon: <LinkOutlined />, onClick: () => { navigator.clipboard.writeText(quiz.exam_url); message.success(t('exam.linkCopied', 'Link copied!')) } }] : []),
    ...(quiz.quiz_type === 'offline_poll' && quiz.poll_url ? [{ key: 'copy_poll', label: t('offlinePoll.copyLink', 'Copy Survey Link'), icon: <LinkOutlined />, onClick: () => { navigator.clipboard.writeText(quiz.poll_url); message.success(t('offlinePoll.linkCopied', 'Link copied!')) } }] : []),
    ...(quiz.has_active_session && quiz.active_session_id ? [{ key: 'stop', label: t('quiz.stopActiveSession', 'Stop Session'), icon: <StopOutlined />, danger: true }] : []),
    { type: 'divider' },
    quiz.archived_at
      ? { key: 'unarchive', label: t('quiz.unarchive', 'Restore'), icon: <HistoryOutlined />, onClick: () => handleUnarchiveQuiz(quiz.id) }
      : { key: 'archive', label: t('quiz.archive', 'Archive'), icon: <InboxOutlined />, onClick: () => handleArchiveQuiz(quiz.id) },
    { key: 'delete', label: t('common.delete', 'Delete'), icon: <DeleteOutlined />, danger: true },
  ]

  const columns = [
    {
      title: t('quiz.title', 'Name'),
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 600, color: C.text1, cursor: 'pointer' }} onClick={() => navigate(`/quiz/${record.id}/edit`)}>
            {text}
          </div>
          {record.has_active_session && <Badge status="processing" text={<span style={{ fontSize: 11, color: C.success }}>Live</span>} />}
          {record.is_template && <Tag style={{ fontSize: 10, padding: '0 5px', marginLeft: 4, background: C.primary50, color: C.primary, border: 'none' }}>Template</Tag>}
          {!record.archived_at && record.status === 'draft' && (record.question_count || 0) === 0 && (
            <Tooltip title={t('activities.needsQuestions', 'Add questions to make this ready')}>
              <WarningOutlined style={{ color: 'var(--sw-warning)', marginLeft: 6, fontSize: 13 }} />
            </Tooltip>
          )}
        </div>
      ),
    },
    { title: t('dashboard.type', 'Type'), dataIndex: 'quiz_type', key: 'quiz_type', width: 130, render: getTypeTag },
    {
      title: t('quiz.status', 'Status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status, record) => {
        if (record.has_active_session) return <Tag style={{ background: 'var(--sw-chip-live-bg)', color: 'var(--sw-chip-live-fg)', border: 'none', borderRadius: 6 }}>Live</Tag>
        return getStatusTag(status)
      },
    },
    { title: t('quiz.questions', 'Questions'), dataIndex: 'question_count', key: 'question_count', width: 100, responsive: ['md'], render: (c) => <span style={{ color: C.text3, fontSize: 13 }}>{c || 0}</span> },
    {
      title: (
        <Space size={4}>
          {t('dashboard.created', 'Date')}
          <Select size="small" value={sortBy} onChange={setSortBy} style={{ width: 110, fontSize: 11 }}
            options={[{ value: 'created_at', label: t('activities.sortCreated', 'Created') }, { value: 'updated_at', label: t('activities.sortUpdated', 'Updated') }]}
          />
        </Space>
      ),
      dataIndex: sortBy,
      key: 'date',
      width: 150,
      responsive: ['lg'],
      render: (date) => date ? <span style={{ color: C.text3, fontSize: 12 }}>{new Date(date).toLocaleDateString()}</span> : '—',
    },
    {
      title: t('common.actions', 'Actions'),
      key: 'actions',
      width: 200,
      render: (_, quiz) => {
        const primaryAction = getPrimaryAction(quiz)
        return (
          <Space size={6}>
            {primaryAction === 'launch' && <Button type="primary" size="small" icon={<PlayCircleOutlined />} onClick={() => navigate(`/quiz/${quiz.id}/control`)} style={{ background: C.success, borderColor: C.success }}>{t('quiz.startQuiz', 'Launch')}</Button>}
            {primaryAction === 'open' && <Button type="primary" size="small" icon={<WifiOutlined />} onClick={() => navigate(`/quiz/${quiz.id}/control`)}>{t('quiz.openRoom', 'Open Room')}</Button>}
            {primaryAction === 'edit' && <Button size="small" icon={<EditOutlined />} onClick={() => navigate(`/quiz/${quiz.id}/edit`)}>{t('quiz.continue', 'Continue')}</Button>}
            {primaryAction === 'exam_results' && <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/quiz/${quiz.id}/exam-results`)}>{t('exam.resultsTitle', 'Results')}</Button>}
            {primaryAction === 'poll_results' && <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/quiz/${quiz.id}/offline-results`)}>{t('offlinePoll.viewResults', 'Results')}</Button>}
            <MoreActionsMenu items={getMoreMenuItems(quiz).map(item => {
              if (item.key === 'delete') {
                return { ...item, confirm: { title: t('quiz.deleteConfirm', 'Delete this activity?'), description: t('quiz.deleteWarning', 'Cannot be undone.'), onConfirm: () => handleDeleteQuiz(quiz.id), okText: t('common.delete', 'Delete'), cancelText: t('common.cancel', 'Cancel') } }
              }
              if (item.key === 'stop') {
                return { ...item, confirm: { title: t('quiz.stopActiveSessionConfirm', 'Stop session?'), onConfirm: () => handleStopActiveSession(quiz.active_session_id), okText: t('quiz.stopQuizOk', 'Yes'), cancelText: t('common.cancel', 'Cancel') } }
              }
              return item
            })} />
          </Space>
        )
      },
    },
  ]

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys) => setSelectedRowKeys(keys),
    getCheckboxProps: (record) => ({
      disabled: !!record.has_active_session,
    }),
  }

  return (
    <div style={{ padding: isMobile ? '16px' : '24px', maxWidth: 1200, margin: '0 auto', width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0, color: C.text1 }}>
          {t('activities.title', 'Activities')}
        </Title>
        <Button type="primary" onClick={() => navigate('/dashboard')}>
          {t('activities.goHome', '← Home')}
        </Button>
      </div>

      {/* Toolbar */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16, alignItems: 'center' }}>
        <Input
          prefix={<SearchOutlined style={{ color: C.text3 }} />}
          allowClear
          placeholder={t('dashboard.searchQuizzes', 'Search activities…')}
          style={{ flex: '1 1 180px', minWidth: 0, borderRadius: 10 }}
          value={searchText}
          onChange={e => setSearchText(e.target.value)}
        />
        <Select
          allowClear
          placeholder={t('dashboard.type', 'Type')}
          style={{ flex: '0 0 auto', width: isMobile ? 110 : 140 }}
          value={typeFilter}
          onChange={setTypeFilter}
          options={[
            { value: 'quiz', label: t('activities.typeQuiz') },
            { value: 'poll', label: t('activities.typePoll') },
            { value: 'exam', label: t('activities.typeExam') },
            { value: 'offline_poll', label: t('activities.typeSurvey') },
          ]}
        />
        <Select
          allowClear
          placeholder={t('quiz.status', 'Status')}
          style={{ flex: '0 0 auto', width: isMobile ? 100 : 120 }}
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { value: 'ready', label: t('activities.statusReady') },
            { value: 'draft', label: t('activities.statusDraft') },
          ]}
        />
        <Button
          icon={<InboxOutlined />}
          type={showArchived ? 'primary' : 'default'}
          onClick={() => setShowArchived(v => !v)}
        >
          {showArchived ? t('activities.hideArchived', 'Hide Archived') : t('activities.showArchived', 'Show Archived')}
        </Button>
        {needsAttentionCount > 0 && (
          <Button
            icon={<WarningOutlined />}
            type={attentionFilter ? 'primary' : 'default'}
            danger={!attentionFilter}
            onClick={() => setAttentionFilter(v => !v)}
          >
            {t('activities.needsAttention', 'Needs Attention')} ({needsAttentionCount})
          </Button>
        )}
      </div>

      {/* Bulk action bar */}
      {selectedRowKeys.length > 0 && (
        <Alert
          style={{ marginBottom: 12, borderRadius: 10 }}
          message={
            <Space>
              <Text strong>{selectedRowKeys.length} {t('activities.selected', 'selected')}</Text>
              <Button size="small" icon={<InboxOutlined />} loading={bulkLoading} onClick={() => setConfirmBulkArchive(true)}>{t('quiz.archive', 'Archive')}</Button>
              <Button size="small" icon={<DeleteOutlined />} danger loading={bulkLoading} onClick={() => setConfirmBulkDelete(true)}>{t('common.delete', 'Delete')}</Button>
              <Button size="small" onClick={() => setSelectedRowKeys([])}>{t('common.clear', 'Clear')}</Button>
            </Space>
          }
          type="info"
          showIcon={false}
        />
      )}

      <SafeConfirm
        open={confirmBulkArchive}
        title={t('activities.bulkArchiveConfirm', `Archive ${selectedRowKeys.length} activities?`)}
        okText={t('quiz.archive', 'Archive')}
        cancelText={t('common.cancel', 'Cancel')}
        danger={false}
        onConfirm={() => { setConfirmBulkArchive(false); handleBulkArchive() }}
        onCancel={() => setConfirmBulkArchive(false)}
      />
      <SafeConfirm
        open={confirmBulkDelete}
        title={t('activities.bulkDeleteConfirm', `Delete ${selectedRowKeys.length} activities?`)}
        description={t('quiz.deleteWarning', 'Cannot be undone.')}
        okText={t('common.delete', 'Delete')}
        cancelText={t('common.cancel', 'Cancel')}
        onConfirm={() => { setConfirmBulkDelete(false); handleBulkDelete() }}
        onCancel={() => setConfirmBulkDelete(false)}
      />

      <Table
        rowKey="id"
        dataSource={filteredQuizzes}
        columns={columns}
        rowSelection={rowSelection}
        pagination={{ pageSize: 20, showSizeChanger: false, showTotal: (total) => `${total} ${t('quiz.activities', 'activities')}` }}
        size="middle"
        scroll={{ x: 600 }}
        style={{ background: C.bgCard, borderRadius: 12 }}
        rowClassName="activity-table-row"
        locale={{ emptyText: <div style={{ padding: '32px', color: C.text3 }}>{t('quiz.noQuizzes', 'No activities found.')}</div> }}
      />
    </div>
  )
}
