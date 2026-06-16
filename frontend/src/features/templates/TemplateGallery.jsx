import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Button, Input, Tabs, Tag, Typography, Space, Spin, message, Empty, Tooltip, Grid } from 'antd'

const { useBreakpoint } = Grid
import {
  SearchOutlined,
  ThunderboltOutlined,
  BarChartOutlined,
  FileTextOutlined,
  GlobalOutlined,
  TeamOutlined,
  HomeOutlined,
  FireOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { quizAPI } from '../../services/api'

const { Title, Text } = Typography

const TYPE_COLOR = {
  quiz: 'blue',
  poll: 'green',
  exam: 'orange',
  offline_poll: 'purple',
}

const TYPE_ICON = {
  quiz: <ThunderboltOutlined />,
  poll: <BarChartOutlined />,
  exam: <FileTextOutlined />,
  offline_poll: <BarChartOutlined />,
}

const TYPE_LABEL = {
  quiz: 'Live Quiz',
  poll: 'Live Poll',
  exam: 'Test',
  offline_poll: 'Poll',
}

const CATEGORY_TABS = ['all', 'classroom', 'all-hands', 'training', 'hiring', 'general', 'mine']

function TemplateCard({ template, onUse, using }) {
  const { t } = useTranslation()
  const isGlobal = template.template_scope === 'global'

  return (
    <Card
      hoverable
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}
      actions={[
        <Button
          key="use"
          type="primary"
          block
          loading={using}
          onClick={() => onUse(template.id)}
          style={{ margin: '0 -1px' }}
        >
          {using ? t('templates.using') : t('templates.useThis')}
        </Button>,
      ]}
    >
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 4 }}>
        <Tag color={TYPE_COLOR[template.quiz_type] || 'blue'} icon={TYPE_ICON[template.quiz_type]}>
          {TYPE_LABEL[template.quiz_type] || template.quiz_type}
        </Tag>
        {isGlobal && (
          <Tag color="purple" icon={<GlobalOutlined />}>{t('templates.scope_global')}</Tag>
        )}
        {!isGlobal && (
          <Tag color="cyan" icon={<TeamOutlined />}>{t('templates.scope_tenant')}</Tag>
        )}
      </div>

      <Title level={5} style={{ margin: 0, lineHeight: 1.3 }}>{template.title}</Title>

      {template.description && (
        <Text type="secondary" style={{ fontSize: 12, flex: 1 }}>
          {template.description.length > 100 ? template.description.slice(0, 97) + '…' : template.description}
        </Text>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 'auto', paddingTop: 8 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {template.question_count} {t('templates.questions')}
        </Text>
        {template.template_use_count > 0 && (
          <Tooltip title={t('templates.usedTimes')}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              <FireOutlined style={{ color: '#fa8c16', marginRight: 3 }} />
              {template.template_use_count}
            </Text>
          </Tooltip>
        )}
      </div>
    </Card>
  )
}

export default function TemplateGallery() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const screens = useBreakpoint()
  const isMobile = !screens.md

  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [activeTab, setActiveTab] = useState('all')
  const [usingId, setUsingId] = useState(null)

  useEffect(() => {
    setLoading(true)
    quizAPI.listTemplates()
      .catch(() => quizAPI.listTemplatesLegacy())
      .then(res => setTemplates(res.data || []))
      .catch(() => message.error(t('quiz.templateLoadFailed')))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    let items = templates

    if (activeTab === 'mine') {
      items = items.filter(t => t.template_scope !== 'global')
    } else if (activeTab !== 'all') {
      // Map UI tab to category field value
      const catMap = { 'all-hands': 'all-hands', classroom: 'classroom', training: 'training', hiring: 'hiring', general: 'general' }
      const cat = catMap[activeTab]
      items = items.filter(t => t.template_category === cat)
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase()
      items = items.filter(t =>
        t.title.toLowerCase().includes(q) ||
        (t.description || '').toLowerCase().includes(q)
      )
    }

    return items
  }, [templates, activeTab, search])

  const handleUse = async (templateId) => {
    setUsingId(templateId)
    try {
      let res
      try { res = await quizAPI.useTemplate(templateId) }
      catch { res = await quizAPI.useTemplateLegacy(templateId) }
      message.success(t('templates.created'))
      navigate(`/quiz/${res.data.id}/edit`)
    } catch (e) {
      message.error(e.response?.data?.detail || t('quiz.templateUseFailed'))
    } finally {
      setUsingId(null)
    }
  }

  const tabItems = CATEGORY_TABS.map(tab => ({
    key: tab,
    label: tab === 'all' ? t('templates.all')
      : tab === 'all-hands' ? t('templates.allHands')
      : tab === 'mine' ? t('templates.myTemplates')
      : t(`templates.${tab}`),
  }))

  return (
    <div style={{ padding: isMobile ? '16px 16px 32px' : '24px 24px 48px', maxWidth: 1200, margin: '0 auto', width: '100%' }}>
      <div style={{ marginBottom: 24 }}>
        <Button
          type="link"
          icon={<HomeOutlined />}
          onClick={() => navigate('/dashboard')}
          style={{ paddingLeft: 0, marginBottom: 8 }}
        >
          {t('templates.goHome')}
        </Button>
        <Title level={2} style={{ margin: 0 }}>{t('templates.title')}</Title>
        <Text type="secondary">{t('templates.subtitle')}</Text>
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <Input
          prefix={<SearchOutlined />}
          placeholder={t('templates.searchPlaceholder')}
          value={search}
          onChange={e => setSearch(e.target.value)}
          allowClear
          style={{ maxWidth: 300 }}
        />
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        style={{ marginBottom: 16 }}
      />

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
        </div>
      ) : filtered.length === 0 ? (
        <Empty description={t('templates.empty')} style={{ padding: 60 }} />
      ) : (
        <Row gutter={[16, 16]}>
          {filtered.map(tmpl => (
            <Col key={tmpl.id} xs={24} sm={12} md={8} lg={6}>
              <TemplateCard
                template={tmpl}
                onUse={handleUse}
                using={usingId === tmpl.id}
              />
            </Col>
          ))}
        </Row>
      )}
    </div>
  )
}
