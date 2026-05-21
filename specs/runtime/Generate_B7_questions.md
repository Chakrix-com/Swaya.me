
***

## **Prompt to Generate Tough B7 Data Engineer Assessment**

Create a **45-minute, high-difficulty technical assessment** for a **Band 7 Data Engineer (3–5 years experience)** designed to **differentiate strong vs exceptional candidates**.

***

## **Format Requirements**

* **18–22 Multiple Choice Questions (MCQs)**
* Each question must include:
  * 4 options (A–D)
  * Correct answer clearly marked
  * **Concise explanation (focused on reasoning, not definition)**

***

## **Core Design Principles**

* Questions must be **non-trivial, edge-case driven, and require careful reasoning**
* Avoid recall-based or definition-only questions
* Prioritise:
  * **Ambiguity handling**
  * **Execution tracing**
  * **Hidden traps (state, mutation, scope, evaluation order)**
* Difficulty level: **Top 20–30% of candidates should struggle**

***

## **Coverage Areas**

### #1 **Programming Logic (Language-Agnostic)**

* Use **advanced pseudocode only (not simple loops)**
* Include:
  * Execution tracing with **state mutation**
  * **Short-circuit evaluation**
  * **Pass-by-reference vs value**
  * **Recursion with subtle behaviour**
  * **Loop traps (off-by-one, mutation inside loops)**
  * **Concurrency/race-condition reasoning (conceptual)**

✅ Must include **at least 6–8 questions** where:

> Candidate must **predict exact output of complex pseudocode**

***

### #2 **SQL & Data Engineering**

* Scenario-based, not syntax recall
* Include:
  * Window functions with edge cases
  * Join behaviour on skewed/missing data
  * Query performance trade-offs
  * Deduplication with multiple constraints
  * Incremental data processing logic

***

### #3 **Linux / OS Concepts**

* Focus on:
  * Process behaviour, memory, file systems
  * Permissions with non-obvious implications
  * Execution/environment behaviour (not command memorisation)

***

### #4 **Modern Engineering Practices**

* CI/CD failure scenarios
* Data pipeline reliability issues
* Version control conflicts and branching strategy
* Testing strategy trade-offs
* Observability/debugging in production

***

## **Question Style (Critical)**

* Use **real-world problem framing**
* Avoid clues in wording
* Include **distractor options that reflect common misconceptions**
* At least **30–40% questions should include traps or misleading intuition**

***

## **Example Difficulty Guidance**

Good questions should:

* Require **multi-step reasoning**
* Force candidates to **track changing state**
* Punish superficial reading
* Reward **deep conceptual clarity**

***

## **Output Structure**

1. Question
2. 4 options (A–D)
3. ✅ Correct answer
4. Explanation (why correct + why trap options are wrong if relevant)

***

## **Final Instruction**

Ensure the test **feels like a high-quality tech company screening**, not an academic exam. The goal is to **identify engineers with strong debugging instincts, system thinking, and precision under pressure**.

