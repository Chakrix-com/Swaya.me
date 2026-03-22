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

export default function PrivacyPolicy() {
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
          <Title level={1}>{t('pages.privacy.title')}</Title>
          <Text type="secondary">{t('pages.legal.lastUpdated')}</Text>
          <Divider />

          <Paragraph>{t('pages.privacy.intro')}</Paragraph>

          <Title level={3}>{t('pages.privacy.s1')}</Title>
          <Paragraph>
            <strong>{t('pages.privacy.s1Body1Label')}</strong> {t('pages.privacy.s1Body1')}
          </Paragraph>
          <Paragraph>
            <strong>{t('pages.privacy.s1Body2Label')}</strong> {t('pages.privacy.s1Body2')}
          </Paragraph>
          <Paragraph>
            <strong>{t('pages.privacy.s1Body3Label')}</strong> {t('pages.privacy.s1Body3')}
          </Paragraph>

          <Title level={3}>{t('pages.privacy.s2')}</Title>
          <Paragraph>{t('pages.privacy.s2Intro')}</Paragraph>
          <ul>
            <li>{t('pages.privacy.s2li1')}</li>
            <li>{t('pages.privacy.s2li2')}</li>
            <li>{t('pages.privacy.s2li3')}</li>
            <li>{t('pages.privacy.s2li4')}</li>
            <li>{t('pages.privacy.s2li5')}</li>
          </ul>
          <Paragraph>{t('pages.privacy.s2Note')}</Paragraph>

          <Title level={3}>{t('pages.privacy.s3')}</Title>
          <Paragraph>{t('pages.privacy.s3Body')}</Paragraph>

          <Title level={3}>{t('pages.privacy.s4')}</Title>
          <Paragraph>
            {t('pages.privacy.s4Body1')}{' '}
            <a href="mailto:info@chakrix.net">info@chakrix.net</a>. {t('pages.privacy.s4Body2')}
          </Paragraph>

          <Title level={3}>{t('pages.privacy.s5')}</Title>
          <Paragraph>{t('pages.privacy.s5Body')}</Paragraph>

          <Title level={3}>{t('pages.privacy.s6')}</Title>
          <Paragraph>{t('pages.privacy.s6Body')}</Paragraph>

          <Title level={3}>{t('pages.privacy.s7')}</Title>
          <Paragraph>{t('pages.privacy.s7Body')}</Paragraph>

          <Title level={3}>{t('pages.privacy.s8')}</Title>
          <Paragraph>
            {t('pages.privacy.s8Body')}{' '}
            <a href="mailto:info@chakrix.net">info@chakrix.net</a>.
          </Paragraph>

          <Title level={3}>{t('pages.privacy.s9')}</Title>
          <Paragraph>{t('pages.privacy.s9Body')}</Paragraph>

          <Title level={3}>{t('pages.privacy.s10')}</Title>
          <Paragraph>
            {t('pages.privacy.s10Body')}{' '}
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
            <a onClick={() => navigate('/help')}>{t('pages.help.footerHelp')}</a>
            <a href="mailto:info@chakrix.net">{t('pages.legal.contactLink')}</a>
          </Space>
        </Space>
      </Footer>
    </Layout>
  )
}
