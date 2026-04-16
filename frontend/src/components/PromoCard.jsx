import { useContext } from 'react'
import { Button, Card, Space, Typography, message } from 'antd'
import { GlobalOutlined, StarOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { VisitorThemeContext } from '../App'

const { Text } = Typography

const HOME_URL = 'https://www.swaya.me'

export default function PromoCard() {
  const { t } = useTranslation()
  const { theme } = useContext(VisitorThemeContext)
  const isDark = theme === 'dark'

  const handleBookmark = () => {
    // Mobile: use Web Share API to share the home page
    if (navigator.share) {
      navigator.share({ title: 'Swaya.me', url: HOME_URL }).catch(() => {})
      return
    }
    // Desktop: keyboard shortcut hint
    message.info(t('promo.bookmarkTip'), 4)
  }

  return (
    <Card
      size="small"
      style={{
        width: '100%',
        marginTop: 24,
        background: isDark
          ? 'linear-gradient(135deg, #111827 0%, #1a2035 100%)'
          : 'linear-gradient(135deg, #e6f4ff 0%, #f0f5ff 100%)',
        border: isDark ? '1px solid #2d3a52' : '1px solid #91caff',
        borderRadius: 12,
        textAlign: 'center',
      }}
      styles={{ body: { padding: '18px 16px' } }}
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Text strong style={{ fontSize: 14, color: isDark ? 'rgba(255,255,255,0.88)' : '#152238' }}>
          {t('promo.tagline')}
        </Text>
        <Space style={{ justifyContent: 'center', flexWrap: 'wrap' }}>
          <Button
            type="primary"
            icon={<GlobalOutlined />}
            href={HOME_URL}
            target="_blank"
            rel="noopener noreferrer"
            size="small"
          >
            {t('promo.visitBtn')}
          </Button>
          <Button
            icon={<StarOutlined />}
            size="small"
            onClick={handleBookmark}
            style={isDark ? undefined : { color: '#152238', borderColor: '#91caff' }}
          >
            {t('promo.bookmarkBtn')}
          </Button>
        </Space>
      </Space>
    </Card>
  )
}
