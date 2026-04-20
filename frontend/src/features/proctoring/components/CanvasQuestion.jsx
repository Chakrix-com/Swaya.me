import { useEffect, useRef } from 'react';

export function CanvasQuestion({ questionText, options }) {
  const canvasRef = useRef();

  useEffect(() => {
    if (!canvasRef.current) return;
    const ctx = canvasRef.current.getContext('2d');
    ctx.clearRect(0, 0, 700, 300);
    ctx.font = '16px Inter, sans-serif';
    ctx.fillStyle = '#000';
    ctx.fillText(questionText, 20, 40);
    if (options) {
      options.forEach((opt, i) => {
        ctx.fillText(`${String.fromCharCode(65 + i)}. ${opt}`, 20, 80 + i * 30);
      });
    }
  }, [questionText, options]);

  return <canvas ref={canvasRef} width={700} height={300} style={{ maxWidth: '100%' }} />;
}
