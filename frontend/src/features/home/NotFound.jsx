import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, Result } from 'antd'

export default function NotFound() {
  const navigate = useNavigate()
  const { t } = useTranslation()

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', padding: 24 }}>
      <Result
        status="404"
        title="404"
        subTitle={t('errors.notFoundSubtitle', 'This activity doesn\'t exist or has been removed.')}
        extra={
          <Button type="primary" onClick={() => navigate('/dashboard')}>
            {t('errors.backToDashboard', 'Back to Dashboard')}
          </Button>
        }
      />
    </div>
  )
}
