import { theme as antdTheme } from 'antd'

// UI theme registry — each entry fully describes one look & feel.
// To add a new theme, add an object here; the ThemePicker, ConfigProvider
// and ProLayout pick it up automatically.
//
// Shape of a theme:
//   id        — stable key (matches the registry key)
//   name      — display name shown in the picker
//   swatch    — 2-4 colors for the picker preview dots
//   fonts     — Google Fonts stylesheet URLs injected when the theme is applied
//   antd      — passed straight to <ConfigProvider theme={...}> (token, algorithm, components)
//   proLayout — passed to <ProLayout token={...}> (sider/header colors)
//   cssVars   — CSS custom properties set on <html>. The --sw-* app variables
//               have their Classic Indigo defaults in index.css :root; a theme
//               only lists what it overrides. Selector-scoped rules (public
//               visitor pages, heading fonts) live in funky-studio.css keyed
//               off html[data-theme="<id>"].

export const themes = {
  'classic-indigo': {
    id: 'classic-indigo',
    name: 'Classic Indigo',
    swatch: ['#6366F1', '#F8FAFC'],
    onPrimary: '#FFFFFF',
    antd: {
      token: {
        colorPrimary: '#6366F1',
        colorSuccess: '#10B981',
        colorWarning: '#F59E0B',
        colorError: '#EF4444',
        borderRadius: 12,
        colorBgLayout: '#F8FAFC',
        colorBgContainer: '#FFFFFF',
        colorBorder: '#E5E7EB',
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Roboto', sans-serif",
      },
    },
    proLayout: {
      bgLayout: '#F8FAFC',
      sider: {
        colorMenuBackground: '#FFFFFF',
        colorTextMenuSelected: '#6366F1',
        colorBgMenuItemSelected: '#EEF2FF',
        colorTextMenu: '#374151',
        colorTextMenuTitle: '#111827',
        colorTextMenuItemHover: '#6366F1',
        colorBgMenuItemHover: '#F8FAFC',
      },
      header: {
        colorBgHeader: '#FFFFFF',
        colorHeaderTitle: '#111827',
        colorTextMenu: '#374151',
        colorTextMenuSelected: '#6366F1',
        colorBgMenuItemSelected: '#EEF2FF',
      },
    },
    cssVars: {
      '--pub-bg':          '#F8FAFC',
      '--pub-card':        '#FFFFFF',
      '--pub-ink':         '#111827',
      '--pub-muted':       '#6B7280',
      '--pub-line':        '#E5E7EB',
      '--pub-soft':        '#EEF2FF',
      '--pub-primary':     '#6366F1',
      '--pub-on-primary':  '#FFFFFF',
      '--pub-quiz':        '#EC4899',
      '--pub-poll':        '#0EA5E9',
      '--pub-test':        '#10B981',
      '--pub-opoll':       '#8B5CF6',
      '--pub-quiz-soft':   'rgba(236, 72, 153, 0.10)',
      '--pub-poll-soft':   'rgba(14, 165, 233, 0.10)',
      '--pub-test-soft':   'rgba(16, 185, 129, 0.10)',
      '--pub-opoll-soft':  'rgba(139, 92, 246, 0.10)',
      '--pub-beam':        'linear-gradient(90deg, #6366F1, #8B5CF6 34%, #0EA5E9 67%, #10B981)',
      '--pub-shadow':      '0 1px 3px rgba(0,0,0,.06), 0 8px 24px -8px rgba(99,102,241,.18)',
      '--pub-cta-bg':      '#6366F1',
      '--pub-cta-text':    '#FFFFFF',
      '--pub-cta-muted':   'rgba(255,255,255,0.72)',
      '--pub-font-display': "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      '--pub-font-body':   "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      '--pub-font-mono':   "source-code-pro, Menlo, Monaco, Consolas, monospace",
    },
  },

  // "Funky-Studio" — dark live-stage look derived from the new-home artifact
  // (Major UI Enhancement/new-home-artifact.html). Ink backdrop, four mode
  // accents: amber=quiz, mint=test, sky=poll, coral=offline poll / live.
  'funky-studio': {
    id: 'funky-studio',
    name: 'Funky-Studio',
    swatch: ['#0E0B33', '#FFB224', '#5AB8FF', '#4ADE9E'],
    onPrimary: '#0E0B33',
    fonts: [
      'https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=Hanken+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap',
    ],
    antd: {
      algorithm: antdTheme.darkAlgorithm,
      token: {
        colorPrimary: '#FFB224',
        colorInfo: '#5AB8FF',
        colorSuccess: '#4ADE9E',
        colorWarning: '#FFB224',
        colorError: '#FF6B6B',
        borderRadius: 14,
        colorBgLayout: '#0E0B33',
        colorBgContainer: '#1A1554',
        colorBgElevated: '#241D6B',
        colorBorder: 'rgba(255, 255, 255, 0.14)',
        colorBorderSecondary: 'rgba(255, 255, 255, 0.10)',
        colorText: '#F4F3FF',
        colorTextSecondary: '#A9A4D9',
        fontFamily: "'Hanken Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Roboto', sans-serif",
      },
      components: {
        // amber primary buttons need dark text, not antd's default white
        Button: { primaryColor: '#0E0B33', fontWeight: 600 },
      },
    },
    proLayout: {
      bgLayout: '#0E0B33',
      sider: {
        colorMenuBackground: '#120E42',
        colorTextMenuSelected: '#FFB224',
        colorBgMenuItemSelected: 'rgba(255, 178, 36, 0.12)',
        colorTextMenu: '#A9A4D9',
        colorTextMenuTitle: '#F4F3FF',
        colorTextMenuItemHover: '#F4F3FF',
        colorBgMenuItemHover: 'rgba(255, 255, 255, 0.06)',
      },
      header: {
        colorBgHeader: '#120E42',
        colorHeaderTitle: '#F4F3FF',
        colorTextMenu: '#A9A4D9',
        colorTextMenuSelected: '#FFB224',
        colorBgMenuItemSelected: 'rgba(255, 178, 36, 0.12)',
      },
    },
    cssVars: {
      '--sw-primary': '#FFB224',
      '--sw-primary-strong': '#FFC95E',
      '--sw-primary-soft': 'rgba(255, 178, 36, 0.14)',
      '--sw-primary-border': 'rgba(255, 178, 36, 0.35)',
      '--sw-success': '#4ADE9E',
      '--sw-warning': '#FFB224',
      '--sw-error': '#FF6B6B',
      '--sw-info': '#5AB8FF',
      '--sw-text1': '#F4F3FF',
      '--sw-text2': '#D7D4F0',
      '--sw-text3': '#A9A4D9',
      '--sw-bg': '#0E0B33',
      '--sw-card': '#1A1554',
      '--sw-border': 'rgba(255, 255, 255, 0.10)',
      '--sw-hover': 'rgba(255, 255, 255, 0.05)',
      '--sw-tile-quiz-bg': 'rgba(255, 178, 36, 0.12)',
      '--sw-tile-quiz-fg': '#FFB224',
      '--sw-tile-exam-bg': 'rgba(74, 222, 158, 0.12)',
      '--sw-tile-exam-fg': '#4ADE9E',
      '--sw-tile-poll-bg': 'rgba(90, 184, 255, 0.12)',
      '--sw-tile-poll-fg': '#5AB8FF',
      '--sw-tile-opoll-bg': 'rgba(255, 107, 107, 0.12)',
      '--sw-tile-opoll-fg': '#FF6B6B',
      '--sw-tile-icon-bg': 'rgba(255, 255, 255, 0.08)',
      '--sw-chip-ready-bg': 'rgba(74, 222, 158, 0.16)',
      '--sw-chip-ready-fg': '#4ADE9E',
      '--sw-chip-draft-bg': 'rgba(255, 178, 36, 0.16)',
      '--sw-chip-draft-fg': '#FFB224',
      '--sw-chip-done-bg': 'rgba(255, 255, 255, 0.08)',
      '--sw-chip-done-fg': '#A9A4D9',
      '--sw-chip-live-bg': 'rgba(90, 184, 255, 0.16)',
      '--sw-chip-live-fg': '#5AB8FF',
      '--sw-stat-ready-bg': 'rgba(74, 222, 158, 0.10)',
      '--sw-stat-works-bg': 'rgba(255, 178, 36, 0.10)',
      '--sw-stat-past-bg': 'rgba(90, 184, 255, 0.10)',
      '--sw-stat-icon-bg': 'rgba(255, 255, 255, 0.08)',
      '--sw-hero-bg':
        'radial-gradient(600px 300px at 85% -20%, rgba(255, 178, 36, 0.18), transparent 60%), ' +
        'radial-gradient(500px 280px at 0% 110%, rgba(90, 184, 255, 0.14), transparent 55%), ' +
        'linear-gradient(135deg, #1A1554 0%, #241D6B 100%)',
      '--sw-banner-bg': 'linear-gradient(135deg, rgba(255, 178, 36, 0.10) 0%, rgba(90, 184, 255, 0.10) 100%)',
      '--sw-banner-border': 'rgba(255, 255, 255, 0.12)',
      // public home page palette (design is shared; see Home.jsx / index.css --pub-*)
      '--pub-bg': '#0E0B33',
      '--pub-card': '#1A1554',
      '--pub-ink': '#F4F3FF',
      '--pub-muted': '#A9A4D9',
      '--pub-line': 'rgba(255, 255, 255, 0.12)',
      '--pub-soft': 'rgba(255, 255, 255, 0.07)',
      '--pub-primary': '#FFB224',
      '--pub-on-primary': '#0E0B33',
      '--pub-quiz': '#FFB224',
      '--pub-poll': '#5AB8FF',
      '--pub-test': '#4ADE9E',
      '--pub-opoll': '#FF6B6B',
      '--pub-quiz-soft': 'rgba(255, 178, 36, 0.14)',
      '--pub-poll-soft': 'rgba(90, 184, 255, 0.14)',
      '--pub-test-soft': 'rgba(74, 222, 158, 0.14)',
      '--pub-opoll-soft': 'rgba(255, 107, 107, 0.14)',
      '--pub-beam': 'linear-gradient(90deg, #FFB224, #FF6B6B 34%, #5AB8FF 67%, #4ADE9E)',
      '--pub-shadow': '0 30px 80px rgba(0, 0, 0, 0.45)',
      '--pub-cta-bg': '#1A1554',
      '--pub-cta-text': '#F4F3FF',
      '--pub-cta-muted': '#A9A4D9',
      '--pub-font-display': "'Bricolage Grotesque', 'Hanken Grotesk', sans-serif",
      '--pub-font-body': "'Hanken Grotesk', -apple-system, BlinkMacSystemFont, sans-serif",
      '--pub-font-mono': "'JetBrains Mono', Menlo, monospace",
    },
  },

  // "Perky-Game" — the Prism concept (Major UI Enhancement/theme3-prism-home.html):
  // porcelain paper, ink primary, Fraunces display, four mode accents:
  // rose=quiz, sky=poll, emerald=test, violet=offline poll.
  'perky-game': {
    id: 'perky-game',
    name: 'Perky-Game',
    swatch: ['#FBFAF7', '#171614', '#FF4D6D', '#0E9BE9'],
    onPrimary: '#FBFAF7',
    fonts: [
      'https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,650;1,9..144,500;1,9..144,650&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap',
    ],
    antd: {
      token: {
        colorPrimary: '#171614',
        colorInfo: '#0E9BE9',
        colorSuccess: '#0FA873',
        colorWarning: '#D97706',
        colorError: '#FF4D6D',
        borderRadius: 12,
        colorBgLayout: '#FBFAF7',
        colorBgContainer: '#FFFFFF',
        colorBorder: '#E9E5DC',
        colorBorderSecondary: '#F0EDE5',
        colorText: '#171614',
        colorTextSecondary: '#6E6A61',
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      },
      components: {
        Button: { fontWeight: 600 },
      },
    },
    proLayout: {
      bgLayout: '#FBFAF7',
      sider: {
        colorMenuBackground: '#FFFFFF',
        colorTextMenuSelected: '#171614',
        colorBgMenuItemSelected: '#F4F1EA',
        colorTextMenu: '#6E6A61',
        colorTextMenuTitle: '#171614',
        colorTextMenuItemHover: '#171614',
        colorBgMenuItemHover: '#F8F6F0',
      },
      header: {
        colorBgHeader: '#FFFFFF',
        colorHeaderTitle: '#171614',
        colorTextMenu: '#6E6A61',
        colorTextMenuSelected: '#171614',
        colorBgMenuItemSelected: '#F4F1EA',
      },
    },
    cssVars: {
      '--sw-primary': '#171614',
      '--sw-primary-strong': '#171614',
      '--sw-primary-soft': '#F4F1EA',
      '--sw-primary-border': '#E0DBD0',
      '--sw-success': '#0FA873',
      '--sw-warning': '#D97706',
      '--sw-error': '#FF4D6D',
      '--sw-info': '#0E9BE9',
      '--sw-text1': '#171614',
      '--sw-text2': '#44403A',
      '--sw-text3': '#6E6A61',
      '--sw-bg': '#FBFAF7',
      '--sw-card': '#FFFFFF',
      '--sw-border': '#E9E5DC',
      '--sw-hover': '#FAF8F3',
      '--sw-tile-quiz-bg': 'rgba(255, 77, 109, 0.09)',
      '--sw-tile-quiz-fg': '#D62B4E',
      '--sw-tile-exam-bg': 'rgba(15, 168, 115, 0.09)',
      '--sw-tile-exam-fg': '#0B7A55',
      '--sw-tile-poll-bg': 'rgba(14, 155, 233, 0.09)',
      '--sw-tile-poll-fg': '#0A77B4',
      '--sw-tile-opoll-bg': 'rgba(139, 92, 246, 0.09)',
      '--sw-tile-opoll-fg': '#6B3FD1',
      '--sw-tile-icon-bg': '#FFFFFF',
      '--sw-chip-ready-bg': 'rgba(15, 168, 115, 0.12)',
      '--sw-chip-ready-fg': '#0B7A55',
      '--sw-chip-draft-bg': '#FFF3D6',
      '--sw-chip-draft-fg': '#8A6D00',
      '--sw-chip-done-bg': '#F0EDE5',
      '--sw-chip-done-fg': '#57534A',
      '--sw-chip-live-bg': '#171614',
      '--sw-chip-live-fg': '#FBFAF7',
      '--sw-stat-ready-bg': '#FFFFFF',
      '--sw-stat-works-bg': '#FFFFFF',
      '--sw-stat-past-bg': '#FFFFFF',
      '--sw-stat-icon-bg': '#FAF8F3',
      '--sw-hero-bg':
        'radial-gradient(500px 240px at 90% -30%, rgba(139, 92, 246, 0.08), transparent 60%), ' +
        'radial-gradient(440px 240px at 4% 130%, rgba(255, 77, 109, 0.07), transparent 60%), ' +
        '#FFFFFF',
      '--sw-banner-bg': 'linear-gradient(135deg, #FFF8E0 0%, #FDFBF4 100%)',
      '--sw-banner-border': '#E9E5DC',
      // public home page palette — the Prism original
      '--pub-bg': '#FBFAF7',
      '--pub-card': '#FFFFFF',
      '--pub-ink': '#171614',
      '--pub-muted': '#6E6A61',
      '--pub-line': '#E9E5DC',
      '--pub-soft': '#F2EFE8',
      '--pub-primary': '#171614',
      '--pub-on-primary': '#FBFAF7',
      '--pub-quiz': '#FF4D6D',
      '--pub-poll': '#0E9BE9',
      '--pub-test': '#0FA873',
      '--pub-opoll': '#8B5CF6',
      '--pub-quiz-soft': 'rgba(255, 77, 109, 0.10)',
      '--pub-poll-soft': 'rgba(14, 155, 233, 0.10)',
      '--pub-test-soft': 'rgba(15, 168, 115, 0.10)',
      '--pub-opoll-soft': 'rgba(139, 92, 246, 0.10)',
      '--pub-beam': 'linear-gradient(90deg, #FF4D6D, #8B5CF6 34%, #0E9BE9 67%, #0FA873)',
      '--pub-shadow': '0 1px 2px rgba(23, 22, 20, 0.05), 0 12px 32px -12px rgba(23, 22, 20, 0.12)',
      '--pub-cta-bg': '#171614',
      '--pub-cta-text': '#FBFAF7',
      '--pub-cta-muted': '#B9B5AB',
      '--pub-font-display': "'Fraunces', Georgia, serif",
      '--pub-font-body': "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      '--pub-font-mono': "'IBM Plex Mono', Menlo, monospace",
    },
  },
}

export const DEFAULT_THEME_ID = 'classic-indigo'

export function getTheme(id) {
  return themes[id] || themes[DEFAULT_THEME_ID]
}

// Union of every CSS var any theme defines, so switching themes also
// clears vars the new theme doesn't set (falling back to index.css defaults).
const allVarNames = [...new Set(Object.values(themes).flatMap((t) => Object.keys(t.cssVars || {})))]

export function applyTheme(theme) {
  const root = document.documentElement

  // selector hook for theme-scoped CSS (funky-studio.css etc.)
  root.dataset.theme = theme.id

  // inject the theme's webfonts once; keep them loaded across switches
  for (const href of theme.fonts || []) {
    if (!document.querySelector(`link[data-theme-font="${href}"]`)) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = href
      link.dataset.themeFont = href
      document.head.appendChild(link)
    }
  }

  const vars = theme.cssVars || {}
  for (const name of allVarNames) {
    if (name in vars) {
      root.style.setProperty(name, vars[name])
    } else {
      root.style.removeProperty(name)
    }
  }
}
