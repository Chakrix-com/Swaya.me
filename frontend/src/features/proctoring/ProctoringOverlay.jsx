import { useEffect, useState } from 'react';
import { Modal, Button } from 'antd';
import { WarningOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

export function ProctoringOverlay({ violationsLeft, onDismiss }) {
  const { t } = useTranslation();
  const isFinalWarning = violationsLeft !== null && violationsLeft <= 1;
  const countdownSec = isFinalWarning ? 30 : 10;
  const [seconds, setSeconds] = useState(countdownSec);

  useEffect(() => {
    setSeconds(countdownSec);
    const timer = setInterval(() => {
      setSeconds((s) => {
        if (s <= 1) {
          clearInterval(timer);
          onDismiss(); // always dismiss — final warning now also auto-dismisses
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [violationsLeft]);

  return (
    <Modal
      open
      closable={false}
      footer={
        !isFinalWarning ? (
          <Button type="primary" onClick={onDismiss}>
            {t('proctoring.overlay.understand', { seconds })}
          </Button>
        ) : null
      }
      centered
      width={420}
    >
      <div style={{ textAlign: 'center', padding: '8px 0' }}>
        <WarningOutlined style={{ fontSize: 48, color: isFinalWarning ? '#ff4d4f' : '#faad14' }} />
        <h3 style={{ marginTop: 12 }}>
          {isFinalWarning ? t('proctoring.overlay.finalWarning') : t('proctoring.overlay.violation')}
        </h3>
        <p style={{ color: '#666' }}>
          {isFinalWarning
            ? t('proctoring.overlay.finalWarningMessage')
            : t('proctoring.overlay.violationMessage')}
        </p>
        {violationsLeft !== null && (
          <p style={{ color: '#ff4d4f', fontWeight: 600 }}>
            {t('proctoring.overlay.remaining', { count: violationsLeft })}
          </p>
        )}
        {isFinalWarning && (
          <p style={{ color: '#aaa', fontSize: 13 }}>
            {t('proctoring.overlay.autoDismiss', { seconds })}
          </p>
        )}
      </div>
    </Modal>
  );
}
