import { useEffect, useState } from 'react'
import { useSelector } from 'react-redux'
import { useTranslation } from 'react-i18next'
import { Row, Col, Card, Tag, Space, Button, Typography } from 'antd'
import { CheckCircleOutlined, ArrowUpOutlined, CrownOutlined } from '@ant-design/icons'
import { authAPI } from '../../services/api'

const { Title, Text } = Typography

const TIER_ORDER = ['free', 'basic', 'pro', 'enterprise']
const TIER_COLOR = { free: '#8c8c8c', basic: '#6366F1', pro: '#7C3AED', enterprise: '#D97706' }

export default function UserPlans() {
  const { t } = useTranslation()
  const { user } = useSelector((state) => state.auth)
  const [tierPlans, setTierPlans] = useState(null)

  useEffect(() => {
    authAPI.getTierPlans().then(r => setTierPlans(r.data)).catch(() => {})
  }, [])

  const currentTier = user?.tier || 'free'
  const currentTierIdx = TIER_ORDER.indexOf(currentTier)

  return (
    <div style={{ padding: '32px 24px', maxWidth: 1000, margin: '0 auto', width: '100%' }}>
      {/* Page header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <CrownOutlined style={{ fontSize: 20, color: '#6366F1' }} />
          <Title level={3} style={{ margin: 0 }}>{t('dashboard.plansTab', 'Your Plan')}</Title>
        </div>
        <Text type="secondary">{t('dashboard.plansSubtitle', 'Active subscription and feature limits')}</Text>
      </div>

      {tierPlans ? (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
            {TIER_ORDER.map(tier => {
              const plan = tierPlans.find(p => p.tier === tier)
              const isCurrentPlan = tier === currentTier
              const canUpgrade = TIER_ORDER.indexOf(tier) > currentTierIdx
              const color = TIER_COLOR[tier] || '#8c8c8c'
              return (
                <Col xs={24} sm={12} lg={6} key={tier}>
                  <Card
                    style={{
                      borderColor: isCurrentPlan ? color : '#E5E7EB',
                      borderWidth: isCurrentPlan ? 2 : 1,
                      borderRadius: 16,
                      height: '100%',
                      position: 'relative',
                      overflow: 'hidden',
                      boxShadow: isCurrentPlan
                        ? `0 4px 20px ${color}22`
                        : '0 1px 4px rgba(0,0,0,0.06)',
                    }}
                  >
                    {isCurrentPlan && (
                      <Tag
                        color={color}
                        style={{ position: 'absolute', top: 0, right: 0, borderRadius: '0 0 0 6px', margin: 0, fontWeight: 600, fontSize: 11 }}
                      >
                        {t('dashboard.currentPlan', 'Current Plan')}
                      </Tag>
                    )}
                    <div style={{ textAlign: 'center', marginBottom: 16, marginTop: isCurrentPlan ? 4 : 0 }}>
                      <Tag color={color} style={{ fontSize: 14, padding: '3px 14px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1 }}>
                        {tier}
                      </Tag>
                    </div>
                    {plan && (
                      <Space direction="vertical" size={8} style={{ width: '100%' }}>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                          <CheckCircleOutlined style={{ color, flexShrink: 0 }} />
                          <span style={{ fontSize: 13 }}>
                            <strong>{plan.max_participants.toLocaleString()}</strong>{' '}{t('dashboard.tierTooltipParticipants').toLowerCase()}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                          <CheckCircleOutlined style={{ color, flexShrink: 0 }} />
                          <span style={{ fontSize: 13 }}>
                            <strong>{plan.max_questions}</strong>{' '}{t('dashboard.tierTooltipQuestions').toLowerCase()}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                          <CheckCircleOutlined style={{ color, flexShrink: 0 }} />
                          <span style={{ fontSize: 13 }}>
                            <strong>{plan.max_concurrent_events}</strong>{' '}{t('dashboard.tierTooltipSessions').toLowerCase()}
                          </span>
                        </div>
                        {canUpgrade && (
                          <Button
                            type="primary"
                            block
                            size="small"
                            href={`mailto:info@chakrix.net?subject=Upgrade%20to%20${tier.charAt(0).toUpperCase() + tier.slice(1)}%20Plan`}
                            style={{ background: color, borderColor: color, marginTop: 8 }}
                            icon={<ArrowUpOutlined />}
                          >
                            {t('dashboard.upgradeTo', { tier: tier.charAt(0).toUpperCase() + tier.slice(1) })}
                          </Button>
                        )}
                      </Space>
                    )}
                  </Card>
                </Col>
              )
            })}
          </Row>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {t('dashboard.plansNote', 'Contact info@chakrix.net to upgrade your plan.')}
          </Text>
        </>
      ) : (
        <div style={{ textAlign: 'center', padding: 40, color: '#8c8c8c' }}>
          {t('common.loading', 'Loading…')}
        </div>
      )}
    </div>
  )
}
