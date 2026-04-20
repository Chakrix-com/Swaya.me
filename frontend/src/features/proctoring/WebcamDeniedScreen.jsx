import { CameraOutlined } from '@ant-design/icons';
import { Button } from 'antd';
import { useTranslation } from 'react-i18next';

export function WebcamDeniedScreen() {
  const { t } = useTranslation();
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16, padding: 32, textAlign: 'center', background: '#fafafa' }}>
      <CameraOutlined style={{ fontSize: 64, color: '#ff4d4f' }} />
      <h2>{t('proctoring.webcam.denied')}</h2>
      <p style={{ color: '#666', maxWidth: 480 }}>{t('proctoring.webcam.deniedMessage')}</p>
      <Button type="primary" onClick={() => window.location.reload()}>
        {t('proctoring.webcam.reload')}
      </Button>
    </div>
  );
}
