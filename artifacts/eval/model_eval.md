# Model evaluation: weekly marketing brief

Same payloads, same prompt, same validator for every model. Numbers are computed in SQL/Python;
models only write the analysis.

| model | weeks | validated_% | first_try_pass_% | invented_numbers_first_try_avg | fallbacks | format_failures | tracking_flags_respected_% | actions_on_placeholders | calendar_used_% | avg_latency_s | avg_prompt_tokens | avg_completion_tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen/qwen3.8-27b:free | 12 | 100.0 | 8.3 | 0.0 | 0 | 13 | 100.0 | 0 | 100.0 | 379.9 | 12605.8 | 15266.3 |

**How to read this**
- *validated_%*: briefs that passed the number validator (within 3 attempts). Anything else fell back
  to the deterministic brief, so no invented number can reach a reader.
- *first_try_pass_%* and *invented_numbers_first_try_avg*: how often the model tried to invent numbers
  before being corrected. This is the honest measure of hallucination.
- *tracking_flags_respected_%*: when the data carried a "check tracking" flag, did the brief treat it as
  a data question rather than a demand story?
- *actions_on_placeholders*: actions recommended on obfuscated values like `<Other>` (should be 0).
- *calendar_used_%*: in holiday weeks, did the brief use the retail calendar to explain seasonality?
