function hashString(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0;
  }
  return Math.abs(hash).toString(16);
}

export function computeFingerprint() {
  try {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    ctx.fillText('Swaya.me fp', 10, 10);
    const canvasData = ctx.getImageData(0, 0, 200, 50).data;
    const canvasHash = hashString(Array.from(canvasData).join(','));

    const components = [
      canvasHash,
      screen.width,
      screen.height,
      screen.colorDepth,
      navigator.userAgent,
      Intl.DateTimeFormat().resolvedOptions().timeZone,
    ].join('|');

    return hashString(components);
  } catch (_) {
    return 'unknown';
  }
}
