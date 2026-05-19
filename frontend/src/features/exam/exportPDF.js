import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import dayjs from 'dayjs'
import logoUrl from '../../assets/logo.png'

const C = {
  blue:    [24, 144, 255],
  dark:    [22, 30, 46],
  gray:    [108, 117, 125],
  lightBg: [246, 249, 255],
  green:   [82, 196, 26],
  red:     [255, 77, 79],
  orange:  [250, 173, 20],
  white:   [255, 255, 255],
  text:    [32, 40, 56],
  border:  [210, 225, 250],
}

async function getLogoBase64() {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.width
      canvas.height = img.height
      canvas.getContext('2d').drawImage(img, 0, 0)
      resolve(canvas.toDataURL('image/png'))
    }
    img.onerror = () => resolve(null)
    img.src = logoUrl
  })
}

function strip(html) {
  return (html || '').replace(/<[^>]*>/g, '').trim()
}

function difficultyLabel(pct) {
  if (pct < 40) return 'Hard'
  if (pct < 70) return 'Medium'
  return 'Easy'
}

function slimHeader(doc, W, M, title) {
  doc.setFillColor(...C.dark)
  doc.rect(0, 0, W, 12, 'F')
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(7.5)
  doc.setTextColor(...C.white)
  const label = `Swaya.me  |  ${title.length > 55 ? title.slice(0, 55) + '…' : title}`
  doc.text(label, M, 8.2)
}

function pageFooter(doc, W, H, M, pageNum, total) {
  doc.setDrawColor(...C.border)
  doc.line(M, H - 10, W - M, H - 10)
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(7)
  doc.setTextColor(160, 160, 160)
  doc.text('Swaya.me  •  Exam Results Report', M, H - 5)
  doc.text(`${pageNum} / ${total}`, W - M, H - 5, { align: 'right' })
}

export async function exportExamResultsPDF(results, analysis) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
  const W = doc.internal.pageSize.getWidth()
  const H = doc.internal.pageSize.getHeight()
  const M = 15

  const logoBase64 = await getLogoBase64()

  // ── Page 1: Branded cover header ──────────────────────────────
  doc.setFillColor(...C.dark)
  doc.rect(0, 0, W, 32, 'F')

  if (logoBase64) {
    doc.addImage(logoBase64, 'PNG', M, 8, 16, 16)
  }

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(15)
  doc.setTextColor(...C.white)
  doc.text('Swaya.me', M + (logoBase64 ? 21 : 0), 17.5)

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(8.5)
  doc.setTextColor(180, 200, 230)
  doc.text('Exam Results Report', W - M, 17.5, { align: 'right' })

  doc.setFontSize(7)
  doc.setTextColor(130, 160, 200)
  doc.text(`Generated ${dayjs().format('DD MMM YYYY, HH:mm')}`, W - M, 24, { align: 'right' })

  let y = 40

  // Exam title
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(18)
  doc.setTextColor(...C.text)
  const titleLines = doc.splitTextToSize(results.quiz_title, W - M * 2)
  doc.text(titleLines, M, y)
  y += titleLines.length * 8 + 3

  // Status pill + date range
  const statusColor = results.is_open ? C.green : C.red
  doc.setFillColor(...statusColor)
  doc.roundedRect(M, y - 1, 23, 7, 1.5, 1.5, 'F')
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(7)
  doc.setTextColor(...C.white)
  doc.text(results.is_open ? 'OPEN' : 'CLOSED', M + 11.5, y + 4, { align: 'center' })

  if (results.exam_start_at && results.exam_end_at) {
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    doc.setTextColor(...C.gray)
    const dateStr = `${dayjs(results.exam_start_at).format('DD MMM YYYY, HH:mm')}  →  ${dayjs(results.exam_end_at).format('DD MMM YYYY, HH:mm')}`
    doc.text(dateStr, M + 27, y + 4)
  }
  y += 13

  // ── Stats box ─────────────────────────────────────────────────
  const boxH = 28
  doc.setFillColor(...C.lightBg)
  doc.roundedRect(M, y, W - M * 2, boxH, 3, 3, 'F')
  doc.setDrawColor(...C.border)
  doc.roundedRect(M, y, W - M * 2, boxH, 3, 3, 'S')

  const colW = (W - M * 2) / 4
  const statsData = [
    { label: 'Total Started',   value: String(results.total_started),                    color: C.blue  },
    { label: 'Completed',       value: String(results.total_completed),                  color: C.green },
    { label: 'Abandoned',       value: String(results.total_abandoned),                  color: C.red   },
    { label: 'Avg Score',       value: `${results.average_score} / ${results.max_score}`, color: C.blue  },
  ]

  statsData.forEach((s, i) => {
    const cx = M + colW * i + colW / 2
    if (i > 0) {
      doc.setDrawColor(...C.border)
      doc.line(M + colW * i, y + 5, M + colW * i, y + boxH - 5)
    }
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(15)
    doc.setTextColor(...s.color)
    doc.text(s.value, cx, y + 14, { align: 'center' })
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(7)
    doc.setTextColor(...C.gray)
    doc.text(s.label, cx, y + 22, { align: 'center' })
  })

  y += boxH + 6

  // Completion rate bar
  if (results.total_started > 0) {
    const rate = Math.round((results.total_completed / results.total_started) * 100)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(7.5)
    doc.setTextColor(...C.gray)
    doc.text(`Completion rate: ${rate}%`, M, y)
    y += 3.5
    const barW = W - M * 2
    doc.setFillColor(220, 225, 235)
    doc.roundedRect(M, y, barW, 3.5, 1, 1, 'F')
    doc.setFillColor(...C.green)
    doc.roundedRect(M, y, Math.max(barW * rate / 100, 2), 3.5, 1, 1, 'F')
    y += 10
  }

  // ── Section header: Leaderboard ───────────────────────────────
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(12)
  doc.setTextColor(...C.text)
  doc.text('Leaderboard', M, y)
  y += 4

  const completed = results.leaderboard.filter(p => p.is_completed)

  autoTable(doc, {
    startY: y,
    margin: { left: M, right: M, top: 16 },
    head: [['Rank', 'Name', 'Email', 'Score', '%', 'Correct', 'Time']],
    body: completed.length > 0 ? completed.map(p => [
      p.rank,
      p.display_name,
      p.email || '—',
      `${p.score} / ${p.max_score}`,
      `${p.percentage}%`,
      p.correct_count,
      p.time_taken_seconds != null
        ? `${Math.floor(p.time_taken_seconds / 60)}m ${Math.round(p.time_taken_seconds % 60)}s`
        : '—',
    ]) : [['—', 'No completed participants', '', '', '', '', '']],
    headStyles: {
      fillColor: C.dark,
      textColor: C.white,
      fontSize: 8,
      fontStyle: 'bold',
      halign: 'center',
    },
    bodyStyles: { fontSize: 7.5 },
    alternateRowStyles: { fillColor: C.lightBg },
    columnStyles: {
      0: { halign: 'center', cellWidth: 13 },
      2: { cellWidth: 45, fontSize: 7 },
      3: { halign: 'center', cellWidth: 24 },
      4: { halign: 'center', cellWidth: 16 },
      5: { halign: 'center', cellWidth: 18 },
      6: { halign: 'center', cellWidth: 20 },
    },
    didParseCell: (data) => {
      if (data.section !== 'body' || data.column.index !== 4) return
      const pct = parseInt(data.cell.raw)
      if (pct >= 70) data.cell.styles.textColor = C.green
      else if (pct >= 40) data.cell.styles.textColor = C.orange
      else data.cell.styles.textColor = C.red
      data.cell.styles.fontStyle = 'bold'
    },
  })

  y = doc.lastAutoTable.finalY + 10

  // ── Section: Question Analytics ───────────────────────────────
  if (y > H - 50) { doc.addPage(); y = 18 }

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(12)
  doc.setTextColor(...C.text)
  doc.text('Question Analytics', M, y)
  y += 4

  autoTable(doc, {
    startY: y,
    margin: { left: M, right: M, top: 16 },
    head: [['#', 'Question', '% Correct', 'Responses', 'Difficulty']],
    body: results.question_analytics.map((qa, i) => {
      const qText = strip(qa.question_text)
      return [
        `Q${i + 1}`,
        qText.length > 80 ? qText.slice(0, 80) + '…' : qText,
        `${qa.percent_correct}%`,
        qa.total_answers,
        difficultyLabel(qa.percent_correct),
      ]
    }),
    headStyles: {
      fillColor: C.dark,
      textColor: C.white,
      fontSize: 8,
      fontStyle: 'bold',
    },
    bodyStyles: { fontSize: 7.5 },
    alternateRowStyles: { fillColor: C.lightBg },
    columnStyles: {
      0: { halign: 'center', cellWidth: 12 },
      2: { halign: 'center', cellWidth: 22 },
      3: { halign: 'center', cellWidth: 22 },
      4: { halign: 'center', cellWidth: 22 },
    },
    didParseCell: (data) => {
      if (data.section !== 'body' || data.column.index !== 4) return
      const label = data.cell.raw
      if (label === 'Hard')   data.cell.styles.textColor = C.red
      else if (label === 'Medium') data.cell.styles.textColor = C.orange
      else data.cell.styles.textColor = C.green
      data.cell.styles.fontStyle = 'bold'
    },
  })

  // ── Section: AI Analysis ──────────────────────────────────────
  if (analysis) {
    doc.addPage()
    y = 18  // leave room for slim header drawn in post-loop

    // Blue section banner
    doc.setFillColor(...C.blue)
    doc.rect(M, y, W - M * 2, 12, 'F')
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(11)
    doc.setTextColor(...C.white)
    doc.text('AI Analysis Report', M + 4, y + 8)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(7.5)
    doc.setTextColor(200, 230, 255)
    doc.text('Generated by Swaya.me AI', W - M - 2, y + 8, { align: 'right' })
    y += 17

    // Render markdown-like content
    const lines = analysis.split('\n')
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(9)
    doc.setTextColor(...C.text)

    for (const rawLine of lines) {
      const line = rawLine.trimEnd()

      if (y > H - 16) {
        doc.addPage()
        y = 18
        doc.setFont('helvetica', 'normal')
        doc.setFontSize(9)
        doc.setTextColor(...C.text)
      }

      if (!line) { y += 2.5; continue }

      if (/^##\s/.test(line)) {
        y += 2
        const headText = line.replace(/^##\s+/, '')
        doc.setFillColor(238, 245, 255)
        doc.rect(M, y - 3, W - M * 2, 9, 'F')
        doc.setFont('helvetica', 'bold')
        doc.setFontSize(10)
        doc.setTextColor(...C.blue)
        doc.text(headText, M + 3, y + 3)
        y += 10
        doc.setFont('helvetica', 'normal')
        doc.setFontSize(9)
        doc.setTextColor(...C.text)
        continue
      }

      if (/^###\s/.test(line)) {
        const headText = line.replace(/^###\s+/, '')
        doc.setFont('helvetica', 'bold')
        doc.setFontSize(9)
        doc.setTextColor(...C.text)
        doc.text(headText, M, y)
        y += 6
        doc.setFont('helvetica', 'normal')
        doc.setFontSize(9)
        doc.setTextColor(...C.text)
        continue
      }

      if (/^[-*•]\s/.test(line)) {
        const bulletText = line.replace(/^[-*•]\s+/, '').replace(/\*\*(.*?)\*\*/g, '$1').replace(/\*(.*?)\*/g, '$1')
        const wrapped = doc.splitTextToSize(bulletText, W - M * 2 - 7)

        if (y + wrapped.length * 4.5 > H - 16) {
          doc.addPage()
          y = 18
          doc.setFont('helvetica', 'normal')
          doc.setFontSize(9)
          doc.setTextColor(...C.text)
        }

        doc.setTextColor(...C.blue)
        doc.text('•', M + 2, y)
        doc.setTextColor(...C.text)
        doc.text(wrapped, M + 7, y)
        y += wrapped.length * 4.5 + 1.5
        continue
      }

      const plainText = line.replace(/\*\*(.*?)\*\*/g, '$1').replace(/\*(.*?)\*/g, '$1').replace(/`(.*?)`/g, '$1')
      const wrapped = doc.splitTextToSize(plainText, W - M * 2)

      if (y + wrapped.length * 4.5 > H - 16) {
        doc.addPage()
        y = 18
        doc.setFont('helvetica', 'normal')
        doc.setFontSize(9)
        doc.setTextColor(...C.text)
      }

      doc.text(wrapped, M, y)
      y += wrapped.length * 4.5 + 2
    }
  }

  // ── Headers + footers on all pages ───────────────────────────
  const totalPages = doc.internal.getNumberOfPages()
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i)
    pageFooter(doc, W, H, M, i, totalPages)
    if (i > 1) slimHeader(doc, W, M, results.quiz_title)
  }

  const safeName = results.quiz_title.replace(/[^\w\s-]/g, '').replace(/\s+/g, '_').slice(0, 40)
  doc.save(`${safeName}_results_${dayjs().format('YYYYMMDD')}.pdf`)
}
