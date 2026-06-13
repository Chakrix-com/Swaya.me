/**
 * Participant-facing skins — applied to AudienceSession and QuizPresent (projector).
 * Unlike admin themes (themes.js), skins only change what the audience sees.
 * Each skin overrides CSS variables on the .sw-skinned container element.
 *
 * To add a skin: add an entry here. QuizBuilder picks it up automatically.
 */

export const skins = {
  default: {
    id: 'default',
    name: 'Default',
    emoji: '🎨',
    description: 'Clean indigo — the classic Swaya look',
    preview: ['#6366F1', '#F8FAFC', '#FFFFFF'],
    cssVars: {},
  },

  classroom: {
    id: 'classroom',
    name: 'Classroom',
    emoji: '📚',
    description: 'Warm parchment — great for learning environments',
    preview: ['#92400E', '#FEF3C7', '#FFFBEB'],
    cssVars: {
      '--visitor-aud-bg': 'linear-gradient(160deg, #FFFBEB 0%, #FEF3C7 50%, #FDE68A 100%)',
      '--visitor-aud-surface': 'rgba(255, 255, 255, 0.92)',
      '--visitor-aud-border': 'rgba(146, 64, 14, 0.20)',
      '--visitor-aud-text-primary': '#1C1917',
      '--visitor-aud-text-secondary': '#78716C',
      '--visitor-aud-input-bg': '#FFFFFF',
      '--visitor-aud-input-text': '#1C1917',
      '--visitor-aud-input-placeholder': '#A78BFA',
      '--ctrl-btn-primary-bg': '#92400E',
      '--ctrl-btn-primary-border': '#92400E',
      '--ctrl-btn-primary-text': '#FFFFFF',
      '--ctrl-radio-selected-bg': '#FEF3C7',
      '--ctrl-radio-selected-border': '#D97706',
      '--ctrl-spinner': '#D97706',
      // Skin-specific extras
      '--skin-accent': '#D97706',
      '--skin-accent-soft': 'rgba(217, 119, 6, 0.12)',
      '--skin-podium-1': '#D97706',
      '--skin-podium-2': '#92400E',
      '--skin-podium-3': '#B45309',
      '--skin-correct': '#15803D',
      '--skin-correct-bg': '#DCFCE7',
      '--skin-wrong': '#DC2626',
      '--skin-wrong-bg': '#FEE2E2',
    },
  },

  boardroom: {
    id: 'boardroom',
    name: 'Boardroom',
    emoji: '🏢',
    description: 'Dark navy — professional and polished',
    preview: ['#F59E0B', '#0F172A', '#1E293B'],
    cssVars: {
      '--visitor-aud-bg': 'linear-gradient(160deg, #0F172A 0%, #1E293B 50%, #0F172A 100%)',
      '--visitor-aud-surface': 'rgba(30, 41, 59, 0.95)',
      '--visitor-aud-border': 'rgba(248, 250, 252, 0.12)',
      '--visitor-aud-text-primary': '#F1F5F9',
      '--visitor-aud-text-secondary': '#94A3B8',
      '--visitor-aud-input-bg': '#1E293B',
      '--visitor-aud-input-text': '#F1F5F9',
      '--visitor-aud-input-placeholder': '#64748B',
      '--ctrl-btn-bg': '#1E293B',
      '--ctrl-btn-text': '#F1F5F9',
      '--ctrl-btn-border': 'rgba(248, 250, 252, 0.18)',
      '--ctrl-btn-hover-bg': '#334155',
      '--ctrl-btn-primary-bg': '#F59E0B',
      '--ctrl-btn-primary-border': '#F59E0B',
      '--ctrl-btn-primary-text': '#0F172A',
      '--ctrl-radio-option-bg': '#1E293B',
      '--ctrl-radio-option-border': 'rgba(248, 250, 252, 0.18)',
      '--ctrl-radio-selected-bg': 'rgba(245, 158, 11, 0.14)',
      '--ctrl-radio-selected-border': '#F59E0B',
      '--ctrl-input-bg': '#1E293B',
      '--ctrl-input-text': '#F1F5F9',
      '--ctrl-input-border': 'rgba(248, 250, 252, 0.18)',
      '--ctrl-input-placeholder': '#64748B',
      '--ctrl-success-bg': 'rgba(74, 222, 158, 0.12)',
      '--ctrl-success-border': '#4ADE9E',
      '--ctrl-error-bg': 'rgba(255, 107, 107, 0.12)',
      '--ctrl-error-border': '#FF6B6B',
      '--ctrl-option-bg-alt': '#263246',
      '--ctrl-divider': 'rgba(255, 255, 255, 0.10)',
      '--ctrl-progress-track': 'rgba(255, 255, 255, 0.08)',
      '--ctrl-tag-text': '#F1F5F9',
      '--ctrl-alert-text': '#F1F5F9',
      '--ctrl-spinner': '#F59E0B',
      // Skin-specific extras
      '--skin-accent': '#F59E0B',
      '--skin-accent-soft': 'rgba(245, 158, 11, 0.16)',
      '--skin-podium-1': '#F59E0B',
      '--skin-podium-2': '#64748B',
      '--skin-podium-3': '#B45309',
      '--skin-correct': '#4ADE9E',
      '--skin-correct-bg': 'rgba(74, 222, 158, 0.14)',
      '--skin-wrong': '#FF6B6B',
      '--skin-wrong-bg': 'rgba(255, 107, 107, 0.14)',
    },
  },

  party: {
    id: 'party',
    name: 'Party',
    emoji: '🎉',
    description: 'Bold gradient — high-energy fun',
    preview: ['#EC4899', '#8B5CF6', '#06B6D4'],
    cssVars: {
      '--visitor-aud-bg': 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 35%, #EC4899 70%, #F59E0B 100%)',
      '--visitor-aud-surface': 'rgba(255, 255, 255, 0.14)',
      '--visitor-aud-border': 'rgba(255, 255, 255, 0.22)',
      '--visitor-aud-text-primary': '#FFFFFF',
      '--visitor-aud-text-secondary': 'rgba(255, 255, 255, 0.72)',
      '--visitor-aud-input-bg': 'rgba(255, 255, 255, 0.18)',
      '--visitor-aud-input-text': '#FFFFFF',
      '--visitor-aud-input-placeholder': 'rgba(255,255,255,0.55)',
      '--ctrl-btn-bg': 'rgba(255, 255, 255, 0.18)',
      '--ctrl-btn-text': '#FFFFFF',
      '--ctrl-btn-border': 'rgba(255, 255, 255, 0.30)',
      '--ctrl-btn-hover-bg': 'rgba(255, 255, 255, 0.28)',
      '--ctrl-btn-primary-bg': '#FFFFFF',
      '--ctrl-btn-primary-border': '#FFFFFF',
      '--ctrl-btn-primary-text': '#4F46E5',
      '--ctrl-radio-option-bg': 'rgba(255, 255, 255, 0.14)',
      '--ctrl-radio-option-border': 'rgba(255, 255, 255, 0.28)',
      '--ctrl-radio-selected-bg': 'rgba(255, 255, 255, 0.28)',
      '--ctrl-radio-selected-border': '#FFFFFF',
      '--ctrl-input-bg': 'rgba(255, 255, 255, 0.18)',
      '--ctrl-input-text': '#FFFFFF',
      '--ctrl-input-border': 'rgba(255, 255, 255, 0.30)',
      '--ctrl-input-placeholder': 'rgba(255,255,255,0.55)',
      '--ctrl-success-bg': 'rgba(255, 255, 255, 0.20)',
      '--ctrl-success-border': '#FFFFFF',
      '--ctrl-error-bg': 'rgba(255, 100, 100, 0.30)',
      '--ctrl-error-border': 'rgba(255, 255, 255, 0.60)',
      '--ctrl-option-bg-alt': 'rgba(255, 255, 255, 0.10)',
      '--ctrl-divider': 'rgba(255, 255, 255, 0.20)',
      '--ctrl-progress-track': 'rgba(255, 255, 255, 0.15)',
      '--ctrl-tag-text': '#FFFFFF',
      '--ctrl-alert-text': '#FFFFFF',
      '--ctrl-spinner': '#FFFFFF',
      // Skin-specific extras
      '--skin-accent': '#F59E0B',
      '--skin-accent-soft': 'rgba(245, 158, 11, 0.20)',
      '--skin-podium-1': '#F59E0B',
      '--skin-podium-2': '#C084FC',
      '--skin-podium-3': '#22D3EE',
      '--skin-correct': '#A7F3D0',
      '--skin-correct-bg': 'rgba(255, 255, 255, 0.20)',
      '--skin-wrong': '#FCA5A5',
      '--skin-wrong-bg': 'rgba(255, 100, 100, 0.25)',
    },
  },
}

export const DEFAULT_SKIN_ID = 'default'

export function getSkin(id) {
  return skins[id] || skins[DEFAULT_SKIN_ID]
}

export function applySkin(skinId, containerEl) {
  const skin = getSkin(skinId)
  const target = containerEl || document.documentElement

  // Clear all skin vars first (fall back to index.css defaults)
  const allVarNames = [...new Set(
    Object.values(skins).flatMap(s => Object.keys(s.cssVars))
  )]
  for (const name of allVarNames) {
    target.style.removeProperty(name)
  }

  for (const [name, val] of Object.entries(skin.cssVars)) {
    target.style.setProperty(name, val)
  }
}
