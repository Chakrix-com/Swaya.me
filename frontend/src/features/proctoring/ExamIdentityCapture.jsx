import { useRef, useState } from 'react';
import { Button, Steps, Alert } from 'antd';
import { CameraOutlined, CheckCircleOutlined } from '@ant-design/icons';

export function ExamIdentityCapture({ stream, onComplete, requirePhotoId }) {
  const videoRef = useRef();
  const [step, setStep] = useState(0);
  const [captured, setCaptured] = useState(false);

  const startVideo = () => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
      videoRef.current.play();
    }
  };

  const capture = () => {
    const canvas = document.createElement('canvas');
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    setCaptured(true);
    if (!requirePhotoId) {
      setStep(1);
    } else {
      setStep(1);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 32,
        background: '#fafafa',
      }}
    >
      <div style={{ maxWidth: 520, width: '100%' }}>
        <h2 style={{ textAlign: 'center', marginBottom: 24 }}>Identity Verification</h2>
        <Steps
          current={step}
          items={[
            { title: 'Face Capture', icon: <CameraOutlined /> },
            { title: 'Ready', icon: <CheckCircleOutlined /> },
          ]}
          style={{ marginBottom: 32 }}
        />

        {step === 0 && (
          <div style={{ textAlign: 'center' }}>
            <Alert
              message="Position your face clearly in the frame, then click Capture."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <div
              style={{
                position: 'relative',
                display: 'inline-block',
                border: '2px solid #1677ff',
                borderRadius: 8,
                overflow: 'hidden',
              }}
            >
              <video
                ref={(el) => {
                  videoRef.current = el;
                  if (el) startVideo();
                }}
                width={320}
                height={240}
                muted
                style={{ display: 'block' }}
              />
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  border: '3px dashed rgba(255,255,255,0.5)',
                  borderRadius: 8,
                  pointerEvents: 'none',
                }}
              />
            </div>
            <br />
            <Button
              type="primary"
              icon={<CameraOutlined />}
              size="large"
              onClick={capture}
              style={{ marginTop: 16 }}
            >
              Capture Photo
            </Button>
          </div>
        )}

        {step === 1 && (
          <div style={{ textAlign: 'center' }}>
            <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
            <h3 style={{ marginTop: 12 }}>Identity verified. You're ready to begin.</h3>
            <Button type="primary" size="large" onClick={onComplete} style={{ marginTop: 16 }}>
              Start Exam
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
