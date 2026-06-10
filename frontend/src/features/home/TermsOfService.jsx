import { useNavigate } from 'react-router-dom'
import { Layout, Typography, Button, Space, Divider } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import logo from '../../assets/logo.png'
import LanguageSwitcher from '../../components/LanguageSwitcher'
import ThemeToggleButton from '../../components/ThemeToggleButton'
import './LegalPage.css'

const { Header, Content, Footer } = Layout
const { Title, Paragraph, Text } = Typography

export default function TermsOfService() {
  const navigate = useNavigate()
  const { t } = useTranslation()

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
          <Title level={1}>{t('pages.terms.title')}</Title>
          <Text type="secondary">{t('pages.legal.lastUpdated')}</Text>
          <Divider />

          <Paragraph>{t('pages.terms.intro')}</Paragraph>

          <Title level={3}>{t('pages.terms.s1')}</Title>
          <Paragraph>{t('pages.terms.s1Body1')}</Paragraph>
          <Paragraph>{t('pages.terms.s1Body2')}</Paragraph>
          <Paragraph>{t('pages.terms.s1Body3')}</Paragraph>

          <Title level={3}>{t('pages.terms.s2')}</Title>
          <Paragraph>{t('pages.terms.s2Body')}</Paragraph>

          <Title level={3}>{t('pages.terms.s3')}</Title>
          <Paragraph>{t('pages.terms.s3Intro')}</Paragraph>
          <ul>
            <li>{t('pages.terms.s3li1')}</li>
            <li>{t('pages.terms.s3li2')}</li>
            <li>{t('pages.terms.s3li3')}</li>
            <li>{t('pages.terms.s3li4')}</li>
            <li>{t('pages.terms.s3li5')}</li>
            <li>{t('pages.terms.s3li6')}</li>
          </ul>
          <Paragraph>{t('pages.terms.s3Note')}</Paragraph>

          <Title level={3}>{t('pages.terms.s4')}</Title>
          <Paragraph>{t('pages.terms.s4Body1')}</Paragraph>
          <Paragraph>{t('pages.terms.s4Body2')}</Paragraph>

          <Title level={3}>{t('pages.terms.s5')}</Title>
          <Paragraph>{t('pages.terms.s5Body')}</Paragraph>

          <Title level={3}>{t('pages.terms.s6')}</Title>
          <Paragraph>{t('pages.terms.s6Body')}</Paragraph>

          <Title level={3}>{t('pages.terms.s7')}</Title>
          <Paragraph>{t('pages.terms.s7Body1')}</Paragraph>
          <Paragraph>{t('pages.terms.s7Body2')}</Paragraph>

          <Title level={3}>{t('pages.terms.s8')}</Title>
          <Paragraph>{t('pages.terms.s8Body')}</Paragraph>

          <Title level={3}>{t('pages.terms.s9')}</Title>
          <Paragraph>{t('pages.terms.s9Body')}</Paragraph>

          <Title level={3}>{t('pages.terms.s10')}</Title>
          <Paragraph>{t('pages.terms.s10Body')}</Paragraph>

          <Title level={3}>{t('pages.terms.s11')}</Title>
          <Paragraph>
            {t('pages.terms.s11Body')}{' '}
            <a href="mailto:info@chakrix.net">info@chakrix.net</a>
          </Paragraph>
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
