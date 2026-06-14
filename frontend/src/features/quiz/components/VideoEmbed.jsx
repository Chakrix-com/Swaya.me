function getVideoEmbedUrl(url) {
  if (!url) return null
  const ytMatch = url.match(
    /(?:youtube\.com\/(?:watch\?v=|shorts\/|embed\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/
  )
  if (ytMatch) return `https://www.youtube.com/embed/${ytMatch[1]}?rel=0`
  const vimeoMatch = url.match(/vimeo\.com\/(\d+)/)
  if (vimeoMatch) return `https://player.vimeo.com/video/${vimeoMatch[1]}`
  return null
}

export { getVideoEmbedUrl }

export default function VideoEmbed({ url, height = 315 }) {
  const embedUrl = getVideoEmbedUrl(url)
  if (!embedUrl) return null
  return (
    <iframe
      src={embedUrl}
      width="100%"
      height={height}
      frameBorder="0"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
      allowFullScreen
      referrerPolicy="strict-origin-when-cross-origin"
      style={{ borderRadius: 8, display: 'block', marginBottom: 12 }}
    />
  )
}
