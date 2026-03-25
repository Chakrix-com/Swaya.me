import { useNavigate } from 'react-router-dom'
import { Layout, Typography, Button, Space, Divider, Row, Col, Card } from 'antd'
import LanguageSwitcher from '../../components/LanguageSwitcher'
import ThemeToggleButton from '../../components/ThemeToggleButton'
import {
  ArrowLeftOutlined,
  QuestionCircleOutlined,
  TeamOutlined,
  DashboardOutlined,
  TrophyOutlined,
  MailOutlined,
  GlobalOutlined,
  GiftOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import logo from '../../assets/logo.png'
import './LegalPage.css'

const { Header, Content, Footer } = Layout
const { Title, Paragraph, Text } = Typography

export default function About() {
  const navigate = useNavigate()
  const { t } = useTranslation()

  const useCases = [
    {
      icon: <QuestionCircleOutlined style={{ fontSize: 36, color: '#1890ff' }} />,
      title: t('pages.about.useCase1Title'),
      description: t('pages.about.useCase1Desc'),
    },
    {
      icon: <TeamOutlined style={{ fontSize: 36, color: '#52c41a' }} />,
      title: t('pages.about.useCase2Title'),
      description: t('pages.about.useCase2Desc'),
    },
    {
      icon: <DashboardOutlined style={{ fontSize: 36, color: '#722ed1' }} />,
      title: t('pages.about.useCase3Title'),
      description: t('pages.about.useCase3Desc'),
    },
    {
      icon: <TrophyOutlined style={{ fontSize: 36, color: '#faad14' }} />,
      title: t('pages.about.useCase4Title'),
      description: t('pages.about.useCase4Desc'),
    },
  ]

  const features = [
    t('pages.about.feature1'),
    t('pages.about.feature2'),
    t('pages.about.feature3'),
    t('pages.about.feature4'),
    t('pages.about.feature5'),
    t('pages.about.feature6'),
    t('pages.about.feature7'),
    t('pages.about.feature8'),
  ]

  return (
    <Layout className="legal-layout">
      <Header className="legal-header">
        <div className="legal-header-content">
          <div className="legal-logo" onClick={() => navigate('/')} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12 }}>
            <img src={logo} alt="Swaya.me" style={{ height: 32, objectFit: 'contain', borderRadius: 4 }} />
            <Text strong style={{ fontSize: 18 }}>Swaya.me</Text>
          </div>
          <Space>
            <ThemeToggleButton />
            <LanguageSwitcher />
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>{t('pages.legal.backToHome')}</Button>
          </Space>
        </div>
      </Header>

      <Content className="legal-content">
        <div className="legal-body">

          {/* Hero */}
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <img src={logo} alt="Swaya.me" style={{ height: 80, objectFit: 'contain', borderRadius: 12, marginBottom: 16 }} />
            <Title level={1} style={{ marginBottom: 8 }}>{t('pages.about.title')}</Title>
            <Paragraph style={{ fontSize: 18, maxWidth: 640, margin: '0 auto' }}>
              {t('pages.about.subtitle')}
            </Paragraph>
          </div>

          <Divider />

          {/* What it is */}
          <Title level={2}>{t('pages.about.whatTitle')}</Title>
          <Paragraph>{t('pages.about.whatBody1')}</Paragraph>
          <Paragraph>{t('pages.about.whatBody2')}</Paragraph>

          {/* Who is it for */}
          <Title level={2}>{t('pages.about.whoTitle')}</Title>
          <Row gutter={[24, 24]} style={{ marginBottom: 40 }}>
            {useCases.map((uc, i) => (
              <Col xs={24} sm={12} key={i}>
                <Card bordered={false} style={{ background: '#fafafa', height: '100%' }}>
                  <Space align="start">
                    {uc.icon}
                    <div>
                      <Text strong style={{ fontSize: 15 }}>{uc.title}</Text>
                      <Paragraph type="secondary" style={{ marginBottom: 0, marginTop: 4 }}>
                        {uc.description}
                      </Paragraph>
                    </div>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>

          {/* Pricing / Beta */}
          <Title level={2}>{t('pages.about.pricingTitle')}</Title>
          <Card
            bordered={false}
            style={{ background: '#f6ffed', borderLeft: '4px solid #52c41a', marginBottom: 32 }}
          >
            <Space>
              <GiftOutlined style={{ fontSize: 22, color: '#52c41a' }} />
              <Paragraph style={{ marginBottom: 0 }}>{t('pages.about.pricingBody')}</Paragraph>
            </Space>
          </Card>

          {/* Beta Status */}
          <Title level={2}>{t('pages.about.betaTitle')}</Title>
          <Paragraph>{t('pages.about.betaBody')}</Paragraph>

          {/* Key features */}
          <Title level={2}>{t('pages.about.featuresTitle')}</Title>
          <ul>
            {features.map((f, i) => <li key={i}>{f}</li>)}
          </ul>

          <Divider />

          {/* Contact */}
          <Title level={2}>{t('pages.about.contactTitle')}</Title>
          <Paragraph>{t('pages.about.contactBody')}</Paragraph>
          <Space direction="vertical" size={8}>
            <Space>
              <MailOutlined style={{ color: '#1890ff' }} />
              <Text>{t('pages.about.contactGeneral')} <a href="mailto:info@chakrix.net">info@chakrix.net</a></Text>
            </Space>
            <Space>
              <GlobalOutlined style={{ color: '#1890ff' }} />
              <Text>{t('pages.about.contactPlatform')} <a href="https://www.swaya.me" target="_blank" rel="noreferrer">www.swaya.me</a></Text>
            </Space>
          </Space>

        </div>
      </Content>

      <Footer className="legal-footer">
        <Space direction="vertical" size={8} style={{ width: '100%', alignItems: 'center' }}>
          <Text type="secondary">© 2026 Swaya.me. {t('home.footer.rights')}</Text>
          <Space split={<Divider type="vertical" />} wrap>
            <a onClick={() => navigate('/about')}>{t('pages.legal.aboutLink')}</a>
            <a onClick={() => navigate('/privacy-policy')}>{t('pages.legal.privacyLink')}</a>
            <a onClick={() => navigate('/terms-of-service')}>{t('pages.legal.termsLink')}</a>
            {/* <a onClick={() => navigate('/help')}>{t('pages.help.footerHelp')}</a> */}
            <a href="mailto:info@chakrix.net">{t('pages.legal.contactLink')}</a>
          </Space>
        </Space>
      </Footer>
    </Layout>
  )
}
