# APE Prompt Methodology — Memory Bank

**Version**: 1.0
**Last Updated**: 2026-02-08
**Source**: ape_prompt_methodology.md

---

## Философия: Prompt Compiler, а не Prompt Library

**Ключевой принцип**: Мы НЕ пишем 1000 промптов под 1000 задач.
Мы строим КОМПИЛЯТОР, который из описания задачи генерирует оптимальный промпт.

---

## УРОВЕНЬ 1: META-PROMPT ENGINE

### Meta-Prompt (ядро системы)

```python
META_PROMPT = '''
You are APE Prompt Compiler. Given a TASK DESCRIPTION, you generate
the optimal system prompt for an LLM that will execute this task.

## YOUR METHODOLOGY (apply in order):

### Step 1: CLASSIFY the task
- What TYPE of task? (code_generation | analysis | validation | synthesis | debate)
- What DOMAIN? (financial | statistical | temporal | general)
- What OUTPUT? (structured_json | narrative | boolean | numerical)
- What RISK? (high = money decisions | medium = analysis | low = formatting)

### Step 2: SELECT techniques
Based on classification, choose from:
- Chain-of-Thought → for multi-step reasoning
- Structured Output → for parseable results (always if downstream code consumes it)
- Few-Shot → ONLY if task has non-obvious format requirements
- Role Assignment → ONLY if domain expertise matters
- Adversarial Framing → ONLY if task is validation/audit
- Constraint Injection → ALWAYS for high-risk tasks

### Step 3: COMPOSE the prompt
Structure:
1. ROLE (1 sentence — who is the LLM in this context)
2. TASK (what exactly to do — imperative, specific)
3. CONSTRAINTS (what NEVER to do — explicit prohibitions)
4. INPUT FORMAT (what data the LLM receives)
5. OUTPUT FORMAT (exact schema or structure expected)
6. EDGE CASES (what to do when input is ambiguous/broken)

### Step 4: VALIDATE
- Is the prompt TESTABLE? (can we write an assertion against output?)
- Is it MINIMAL? (remove any sentence that doesn't change output)
- Is it UNAMBIGUOUS? (would 2 different LLMs interpret it the same way?)

## OUTPUT
Return the generated system prompt + reasoning for each choice made.
'''
```

---

## УРОВЕНЬ 2: TASK TAXONOMY (APE Components)

### Категория A: Code Generation (PLAN Node)
```
Характеристики:
- Output = executable code
- Risk = HIGH (код исполняется в sandbox)
- Technique = Structured Output + Constraints + Few-Shot
- Обязательно: запрет raw numbers, only print key:value
- Обязательно: Pydantic schema для output

APE Components: PlanNode
Status: ✅ IMPLEMENTED (hardcoded v1, need v2+ DSPy optimization)
```

### Категория B: Adversarial Validation (Doubter, TIM)
```
Характеристики:
- Output = verdict (pass/fail/conditional)
- Risk = HIGH (gate decision)
- Technique = Adversarial Framing + Chain-of-Thought + Checklist
- Обязательно: DEFAULT = reject, доказывай что ok
- Обязательно: explicit checklist в промпте

APE Components: DoubterAgent, TemporalIntegrityChecker
Status:
  - DoubterAgent: ✅ IMPLEMENTED
  - TIM: ✅ IMPLEMENTED (rule-based, no LLM)
```

### Категория C: Multi-Perspective Analysis (Debate)
```
Характеристики:
- Output = structured arguments + synthesis
- Risk = MEDIUM (advisory, не gate)
- Technique = Role Assignment + Structured Output + Constraint
- Обязательно: каждый агент видит ОДНИ данные
- Обязательно: synthesizer более консервативен чем любой агент

APE Components: Debate System (planned Week 5-6)
Status: ⏸️ NOT IMPLEMENTED (Milestone 2)
```

### Категория D: Evaluation / Judging
```
Характеристики:
- Output = scores + reasoning
- Risk = LOW (метрика, не решение)
- Technique = Rubric-based + Chain-of-Thought
- Обязательно: explicit scoring rubric
- Обязательно: reasoning BEFORE score

APE Components: Evaluation Module
Status: ✅ IMPLEMENTED (ground truth comparison)
```

### Категория E: Data Extraction / Parsing
```
Характеристики:
- Output = structured data from unstructured input
- Risk = MEDIUM
- Technique = Structured Output + Examples
- Обязательно: schema validation

APE Components: Truth Boundary Gate (TruthBoundaryGate)
Status: ✅ IMPLEMENTED (deterministic, no LLM)
```

### Категория F: Temporal / Regulatory Validation
```
Характеристики:
- Output = temporal_valid: bool + violations[]
- Risk = HIGH (look-ahead bias = всё обнуляет)
- Technique = Rule Injection + Checklist + Structured Output
- Обязательно: hard rules (10-K = T+90, etc.) прямо в промпте

APE Components: TemporalIntegrityChecker (TIM)
Status: ✅ IMPLEMENTED (rule-based regex, no LLM)
```

---

## УРОВЕНЬ 3: PROMPT COMPOSITION (6 блоков)

### Блок 1: ROLE (кто)
```
Шаблон: "You are APE {RoleName} — {one-sentence expertise description}."
Правило: ОДНО предложение. Не больше.
Когда нужен: Categories A, B, C (domain expertise matters)
Когда НЕ нужен: Categories D, E (generic task)
```

### Блок 2: TASK (что)
```
Шаблон: Императив. "Generate..." / "Validate..." / "Compare..."
Правило: Первое предложение = action verb + object + purpose
Когда нужен: ВСЕГДА
```

### Блок 3: CONSTRAINTS (чего никогда)
```
Шаблон: "## ABSOLUTE RULES\n1. NEVER...\n2. ALWAYS..."
Правило: Только запреты которые РЕАЛЬНО нарушаются без них
Когда нужен: Categories A, B, F (high-risk)
Anti-pattern: Не добавляй constraint "для безопасности" —
  каждый constraint = потеря creativity
```

### Блок 4: INPUT FORMAT (что получает)
```
Шаблон: "## INPUT\nYou receive: {description of data structure}"
Правило: Конкретные имена переменных, типы, примеры значений
Когда нужен: ВСЕГДА когда input не просто текст
```

### Блок 5: OUTPUT FORMAT (что возвращает)
```
Шаблон: "## OUTPUT\nReturn JSON matching {SchemaName} schema:\n{schema}"
Правило: Если downstream код парсит → Pydantic schema обязательна
Когда нужен: Categories A, B, C, D, E, F (почти всегда в APE)
```

### Блок 6: EDGE CASES (что делать когда непонятно)
```
Шаблон: "## EDGE CASES\n- If {condition}: {action}\n- If {condition}: {action}"
Правило: Только РЕАЛЬНЫЕ edge cases из тестов/production
Anti-pattern: Не выдумывай edge cases заранее — добавляй по мере обнаружения
```

---

## УРОВЕНЬ 4: PROMPT LIFECYCLE

### Current APE Implementation Status

| Component | Lifecycle Stage | Notes |
|-----------|-----------------|-------|
| PLAN Node | v1 (hardcoded) | Need v2+ DSPy optimization |
| DoubterAgent | v1 (hardcoded) | Working, can optimize |
| TIM | N/A | Rule-based (no LLM) |
| Truth Gate | N/A | Deterministic (no LLM) |
| Evaluation | v1 | Ground truth comparison |

### Recommended Evolution

**Week 4 Day 4+**: Prompt Compiler Implementation
- Create `APEPromptCompiler` class
- Implement dynamic prompt generation for Doubter
- Add TDD tests for prompts
- DSPy optimization for PLAN Node (Week 5)

---

## УРОВЕНЬ 5: ANTI-PATTERNS (текущий проект)

### ✅ What We're Doing Right

1. **Structured Output Everywhere**: All LLM nodes use Pydantic schemas
2. **TDD for Prompts**: Tests validate LLM outputs before implementation
3. **Minimal Prompts**: Current prompts are concise (1-2 paragraphs)
4. **Deterministic Where Possible**: Gate and TIM use code, not LLM

### ❌ Current Weaknesses (to fix)

1. **Hardcoded Prompts**: PLAN Node prompt is hardcoded string
   - **Fix**: Implement `APEPromptCompiler` (Week 4 Day 4)

2. **No Prompt Versioning**: Can't A/B test prompts
   - **Fix**: Store prompts in config/prompts/ directory

3. **No DSPy Optimization**: PLAN Node not optimized
   - **Fix**: Week 5 - DSPy optimization session

4. **No Edge Case Handling**: Prompts don't handle ambiguous queries
   - **Fix**: Add Блок 6 (EDGE CASES) to all prompts

---

## УРОВЕНЬ 6: APE LANGGRAPH INTEGRATION

### Recommended Architecture

```python
# src/prompt_compiler/compiler.py
class APEPromptCompiler:
    def __init__(self):
        self.meta_prompt = META_PROMPT
        self.taxonomy = TaskTaxonomy()  # 6 категорий
        self.blocks = PromptBlocks()    # 6 блоков
        self.cache = {}                 # compiled prompts cache

    def compile(self, task_description: str, context: dict) -> str:
        # 1. Classify задачу
        task_type = self.taxonomy.classify(task_description)

        # 2. Выбрать нужные блоки
        required_blocks = self.taxonomy.get_blocks(task_type)

        # 3. Заполнить блоки контекстом
        filled_blocks = []
        for block in required_blocks:
            filled = block.fill(context)
            filled_blocks.append(filled)

        # 4. Собрать prompt
        prompt = "\n\n".join(filled_blocks)

        # 5. Validate
        self.validate(prompt, task_type)

        # 6. Cache
        cache_key = hash(task_description + str(context))
        self.cache[cache_key] = prompt

        return prompt
```

### LangGraph Node Integration (Example)

```python
def plan_node(state: APEState, config: RunnableConfig) -> APEState:
    compiler = APEPromptCompiler()

    # Compile prompt динамически под конкретный запрос
    system_prompt = compiler.compile(
        task_description="Generate executable Python code for financial analysis",
        context={
            "query": state.query_text,
            "tickers": state.available_tickers,
            "date_range": (state.start_date, state.end_date),
            "task_type": "code_generation",
        }
    )

    # Invoke Claude with compiled prompt
    response = claude.messages.create(
        system=system_prompt,
        messages=[{"role": "user", "content": state.query_text}]
    )

    state.plan = response.content
    return state
```

---

## HARDCODED vs COMPILED — Текущая Стратегия

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| PLAN Node | Hardcoded v1 | DSPy v2+ | 🔴 HIGH (Week 5) |
| Truth Boundary | N/A (code) | N/A (keep) | ✅ Done |
| VEE Sandbox | N/A (code) | N/A (keep) | ✅ Done |
| Doubter Agent | Hardcoded v1 | Compiled | 🟡 MEDIUM (Week 4 Day 4) |
| Debate agents | Not impl | Semi-hard | ⏸️ Week 5-6 |
| TIM | N/A (regex) | Hardcoded rules | ✅ Done |

---

## ЕДИНСТВЕННЫЕ HARDCODED ПРОМПТЫ (Целевое состояние)

1. **META_PROMPT** — сам компилятор (меняется редко)
2. **PLAN_SYSTEM_PROMPT** — ядро pipeline (после v2+ DSPy optimization)
3. **TEMPORAL_RULES** — физические правила (10-K=T+90, не меняются)

Всё остальное — COMPILED динамически.

---

## Immediate Action Items (Week 4 Day 4)

### High Priority
1. ✅ Integrate this methodology into memory bank
2. 🔴 Create `APEPromptCompiler` skeleton (Week 4 Day 4-5)
3. 🔴 Refactor DoubterAgent to use compiled prompts
4. 🟡 Add prompt versioning system (config/prompts/)

### Medium Priority (Week 5)
5. DSPy optimization for PLAN Node
6. Add EDGE CASES block to all prompts
7. Implement Debate system (Category C)

### Low Priority (Week 6+)
8. A/B testing infrastructure for prompts
9. Prompt analytics dashboard
10. Production feedback loop automation

---

## References

- Original: `C:\Users\serge\Downloads\ape_prompt_methodology.md`
- Integration Date: 2026-02-08
- Integrated By: Claude Sonnet 4.5 (Autonomous Session)
- Next Review: Week 5 Day 1 (before DSPy optimization)

---

*This is a living document. Update as methodology evolves.*
