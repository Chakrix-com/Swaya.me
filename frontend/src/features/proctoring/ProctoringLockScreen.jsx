import { LockOutlined } from '@ant-design/icons';
import { Button } from 'antd';
import { useTranslation } from 'react-i18next';

export function ProctoringLockScreen({ lockReason, autoSubmitted }) {
  const { t } = useTranslation();
  return (
    <div style={{ position: 'fixed', inset: 0, background: '#141414', color: '#fff', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', zIndex: 9999, gap: 16, padding: 32, textAlign: 'center' }}>
      <LockOutlined style={{ fontSize: 64, color: '#ff4d4f' }} />
      <h2 style={{ color: '#fff', margin: 0 }}>{t('proctoring.lock.title')}</h2>
      {!lockReason || lockReason === 'ADMIN_LOCK' ? (
        <p style={{ color: '#aaa', maxWidth: 480 }}>{t('proctoring.lock.adminMessage')}</p>
      ) : (
        <p style={{ color: '#aaa', maxWidth: 480 }}>{t('proctoring.lock.violationMessage')}</p>
      )}
      {autoSubmitted && (
        <p style={{ color: '#52c41a' }}>{t('proctoring.lock.submitted')}</p>
      )}
      <Button type="default" ghost onClick={() => window.location.reload()} style={{ marginTop: 8 }}>
        {t('proctoring.lock.reload')}
      </Button>
    </div>
  );
}
