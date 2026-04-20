/**
 * Filter resolved rules to those applicable to a given question type.
 */
export function filterRulesForQuestion(resolvedRules, questionType) {
  if (!resolvedRules) return [];
  return resolvedRules.filter((rule) => {
    // Most rules are globally active; copy_paste_block and others are filtered server-side
    // This is a client-side additional filter for per-question applicability
    return true;
  });
}
