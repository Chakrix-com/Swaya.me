import { useProctoringContext } from '../ProctoringProvider';
import { useFullscreenEnforcer } from './useFullscreenEnforcer';
import { useTabSwitchDetector } from './useTabSwitchDetector';
import { useCopyPasteBlocker } from './useCopyPasteBlocker';
import { useMultiTabDetector } from './useMultiTabDetector';
import { useRightClickBlocker } from './useRightClickBlocker';
import { useBotSignalDetector } from './useBotSignalDetector';
import { useDevToolsDetector } from './useDevToolsDetector';
import { useBehavioralCollector } from './useBehavioralCollector';

function hasRule(rules, ruleId) {
  return rules.some((r) => r.rule_id === ruleId);
}

function getConfig(rules, ruleId) {
  const rule = rules.find((r) => r.rule_id === ruleId);
  return rule?.config || {};
}

export function useProctoringModule() {
  const { resolvedRules, reportViolation, sessionToken } = useProctoringContext();
  const enabled = resolvedRules.length > 0;

  useFullscreenEnforcer({
    config: getConfig(resolvedRules, 'fullscreen_enforce'),
    reportViolation,
    enabled: enabled && hasRule(resolvedRules, 'fullscreen_enforce'),
  });

  useTabSwitchDetector({
    config: getConfig(resolvedRules, 'tab_switch_detect'),
    reportViolation,
    enabled: enabled && hasRule(resolvedRules, 'tab_switch_detect'),
  });

  useCopyPasteBlocker({
    reportViolation,
    enabled: enabled && hasRule(resolvedRules, 'copy_paste_block'),
  });

  useMultiTabDetector({
    reportViolation,
    enabled: enabled && hasRule(resolvedRules, 'multi_tab_detect'),
  });

  useRightClickBlocker({
    reportViolation,
    enabled: enabled && hasRule(resolvedRules, 'right_click_block'),
  });

  useBotSignalDetector({
    reportViolation,
    enabled: enabled && hasRule(resolvedRules, 'bot_signal_detect'),
  });

  useDevToolsDetector({
    config: getConfig(resolvedRules, 'devtools_detect'),
    reportViolation,
    enabled: enabled && hasRule(resolvedRules, 'devtools_detect'),
  });

  useBehavioralCollector({
    sessionToken,
    config: getConfig(resolvedRules, 'behavioral_biometrics'),
    enabled: enabled && hasRule(resolvedRules, 'behavioral_biometrics'),
  });
}
