import { useMemo } from 'react';

function generateGarbageSpans() {
  const chars = '⁠​‌‍‎‏\u2060\u2061\u2062\u2063\u2064';
  return Array.from({ length: 8 }, () =>
    Array.from({ length: 12 }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
  );
}

export function DomNoise() {
  const garbage = useMemo(() => generateGarbageSpans(), []);
  return (
    <>
      {garbage.map((text, i) => (
        <span key={i} style={{ display: 'none' }} aria-hidden="true">
          {text}
        </span>
      ))}
    </>
  );
}
