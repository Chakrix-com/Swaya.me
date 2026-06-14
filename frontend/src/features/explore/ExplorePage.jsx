/**
 * ExplorePage — public template discovery, no auth required (P4-4).
 * Route: /explore (public, no ProLayout)
 */
import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card, Row, Col, Button, Input, Tag, Typography, Space, Spin,
  Empty, Tabs, Divider
} from 'antd'
import {
  SearchOutlined, ThunderboltOutlined, BarChartOutlined,
  FileTextOutlined, GlobalOutlined, LoginOutlined, ArrowRightOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { quizAPI } from '../../services/api'
import { trackEvent } from '../../services/metrics'
import PublicBrandHeader from '../../components/PublicBrandHeader'

const { Title, Text, Paragraph } = Typography

const TYPE_COLOR  = { quiz: 'blue', poll: 'green', exam: 'orange', offline_poll: 'purple' }
const TYPE_ICON   = {
  quiz: <ThunderboltOutlined />,
  poll: <BarChartOutlined />,
  exam: <FileTextOutlined />,
  offline_poll: <BarChartOutlined />,
}
const TYPE_LABEL_KEY = { quiz: 'explore.typeQuiz', poll: 'explore.typePoll', exam: 'explore.typeExam', offline_poll: 'explore.typeSurvey' }

const TABS = [
  { key: 'all',          labelKey: 'explore.tabAll' },
  { key: 'quiz',         labelKey: 'explore.tabQuizzes' },
  { key: 'poll',         labelKey: 'explore.tabPolls' },
  { key: 'exam',         labelKey: 'explore.tabTests' },
  { key: 'offline_poll', labelKey: 'explore.tabSurveys' },
]

function TemplateCard({ tmpl, onUseClick }) {
  const { t } = useTranslation()
  return (
    <Card
      hoverable
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}
      actions={[
        <Button
          key="use"
          type="primary"
          icon={<LoginOutlined />}
          block
          onClick={() => onUseClick(tmpl)}
          style={{ margin: '0 -1px' }}
        >
          {t('explore.useTemplate', 'Use this template')}
        </Button>,
      ]}
    >
      <Space size={4} wrap style={{ marginBottom: 4 }}>
        <Tag color={TYPE_COLOR[tmpl.quiz_type] || 'blue'} icon={TYPE_ICON[tmpl.quiz_type]}>
          {TYPE_LABEL_KEY[tmpl.quiz_type] ? t(TYPE_LABEL_KEY[tmpl.quiz_type]) : tmpl.quiz_type}
        </Tag>
        <Tag color="purple" icon={<GlobalOutlined />}>{t('templates.scope_global', 'Global')}</Tag>
      </Space>

      <Title level={5} style={{ margin: 0, lineHeight: 1.3 }}>{tmpl.title}</Title>

      {tmpl.description && (
        <Text type="secondary" style={{ fontSize: 12, flex: 1 }}>
          {tmpl.description.length > 110 ? tmpl.description.slice(0, 107) + '…' : tmpl.description}
        </Text>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 'auto', paddingTop: 8 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {tmpl.question_count} {t('templates.questions', 'questions')}
        </Text>
        {tmpl.template_use_count > 0 && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            🔥 {tmpl.template_use_count}×
          </Text>
        )}
      </div>
    </Card>
  )
}

export default function ExplorePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [templates, setTemplates] = useState([])
  const [loading, setLoading]   = useState(true)
  const [search, setSearch]     = useState('')
  const [activeTab, setActiveTab] = useState('all')

  useEffect(() => {
    trackEvent('explore_page_view')
    quizAPI.listPublicTemplates()
      .then(res => setTemplates(res.data || []))
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    let items = templates
    if (activeTab !== 'all') {
      items = items.filter(t => t.quiz_type === activeTab)
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      items = items.filter(t =>
        t.title.toLowerCase().includes(q) ||
        (t.description || '').toLowerCase().includes(q)
      )
    }
    return items
  }, [templates, search, activeTab])

  const handleUse = (tmpl) => {
    trackEvent('explore_use_template', { quizId: tmpl.id })
    navigate('/login', { state: { useTemplateId: tmpl.id, useTemplateTitle: tmpl.title } })
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--pub-bg, #f8fafc)' }}>
      <PublicBrandHeader />

      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
        padding: '48px 24px 40px',
        textAlign: 'center',
        color: '#fff',
      }}>
        <Title level={2} style={{ color: '#fff', margin: 0, marginBottom: 8 }}>
          {t('explore.heroTitle', 'Browse ready-to-run activities')}
        </Title>
        <Paragraph style={{ color: 'rgba(255,255,255,0.85)', margin: '0 auto', maxWidth: 560 }}>
          {t('explore.heroSubtitle', 'Pick a template, sign up for free, and run it with your audience in minutes.')}
        </Paragraph>
        <div style={{ marginTop: 24, display: 'flex', gap: 12, justifyContent: 'center' }}>
          <Button
            type="default"
            size="large"
            ghost
            icon={<LoginOutlined />}
            onClick={() => navigate('/login')}
          >
            {t('explore.signIn', 'Sign in')}
          </Button>
          <Button
            type="primary"
            size="large"
            style={{ background: '#fff', color: '#4f46e5', borderColor: '#fff', fontWeight: 600 }}
            icon={<ArrowRightOutlined />}
            onClick={() => navigate('/register')}
          >
            {t('explore.getStarted', 'Get started free')}
          </Button>
        </div>
      </div>

      {/* Templates */}
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '32px 16px 64px' }}>
        <Space direction="vertical" style={{ width: '100%' }} size={20}>
          <Input
            placeholder={t('explore.searchPlaceholder', 'Search templates…')}
            prefix={<SearchOutlined />}
            value={search}
            onChange={e => setSearch(e.target.value)}
            size="large"
            allowClear
            style={{ maxWidth: 480 }}
          />

          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={TABS.map(tab => ({ key: tab.key, label: t(tab.labelKey) }))}
          />

          {loading ? (
            <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
          ) : filtered.length === 0 ? (
            <Empty description={t('explore.noResults', 'No templates found')} style={{ padding: 60 }} />
          ) : (
            <Row gutter={[16, 16]}>
              {filtered.map(tmpl => (
                <Col key={tmpl.id} xs={24} sm={12} md={8} lg={6}>
                  <TemplateCard tmpl={tmpl} onUseClick={handleUse} />
                </Col>
              ))}
            </Row>
          )}
        </Space>

        <Divider style={{ marginTop: 48 }} />
        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">{t('explore.footerCta', 'Create your own activities for free.')}</Text>
          {' '}
          <Button type="link" onClick={() => navigate('/register')}>
            {t('explore.signUpFree', 'Sign up →')}
          </Button>
        </div>
      </div>
    </div>
  )
}
