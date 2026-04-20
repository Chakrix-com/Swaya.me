import { HoneypotAnswerOption } from './HoneypotAnswerOption';
import { HoneypotInstructionText } from './HoneypotInstructionText';
import { HoneypotInputField } from './HoneypotInputField';
import { HoneypotDecoyEndpoint } from './HoneypotDecoyEndpoint';

const TEXT_TYPES = ['paragraph', 'single_line', 'one_word', 'mcq'];

export function HoneypotBundle({ config, questionType, reportViolation }) {
  if (!config) return null;
  const showText = TEXT_TYPES.includes(questionType);
  return (
    <>
      {questionType === 'mcq' && (
        <HoneypotAnswerOption config={config} reportViolation={reportViolation} />
      )}
      {showText && <HoneypotInstructionText />}
      {showText && <HoneypotInputField config={config} reportViolation={reportViolation} />}
      <HoneypotDecoyEndpoint config={config} />
    </>
  );
}
