import { useFullscreenEnforcer } from '../hooks/useFullscreenEnforcer';
import { useTabSwitchDetector } from '../hooks/useTabSwitchDetector';
import { useCopyPasteBlocker } from '../hooks/useCopyPasteBlocker';
import { useMultiTabDetector } from '../hooks/useMultiTabDetector';
import { useRightClickBlocker } from '../hooks/useRightClickBlocker';
import { useBotSignalDetector } from '../hooks/useBotSignalDetector';
import { useDevToolsDetector } from '../hooks/useDevToolsDetector';
import { useBehavioralCollector } from '../hooks/useBehavioralCollector';

export const RULE_REGISTRY = {
  fullscreen_enforce: { hook: useFullscreenEnforcer, type: 'hook' },
  tab_switch_detect: { hook: useTabSwitchDetector, type: 'hook' },
  copy_paste_block: { hook: useCopyPasteBlocker, type: 'hook' },
  multi_tab_detect: { hook: useMultiTabDetector, type: 'hook' },
  right_click_block: { hook: useRightClickBlocker, type: 'hook' },
  bot_signal_detect: { hook: useBotSignalDetector, type: 'hook' },
  devtools_detect: { hook: useDevToolsDetector, type: 'hook' },
  behavioral_biometrics: { hook: useBehavioralCollector, type: 'hook' },
  honeypot_traps: { type: 'component' },
  webcam_monitoring: { type: 'webcam' },
  question_randomization: { type: 'server' },
  option_randomization: { type: 'server' },
  answer_timing_enforce: { type: 'timing' },
  browser_fingerprint_bind: { type: 'server' },
  ip_bind: { type: 'server' },
  steg_watermark: { type: 'server' },
  canvas_rendering: { type: 'component' },
};
