# Multi-Source Fact Reconciliation Agent

A multi-step agent that answers country population questions by retrieving evidence from multiple sources, evaluating their reliability, and reconciling conflicting or partial results into a single answer with an explicit confidence level.

The system queries three distinct retrieval paths - a local population dataset, the World Bank API, and web search - then evaluates the returned evidence for freshness, provenance, source quality, and numerical disagreement. When evidence is insufficient or a source fails, the agent can adapt its retrieval strategy rather than failing, retrying indefinitely, or silently guessing.

This project was built for the **LEC AI Engineering Intern build assessment**.

## What the agent does

Given a country name, the program:

1. Resolves the country to its ISO alpha-3 code using the local population dataset.
2. Attempts three initial retrievals:
   - local CSV data;
   - World Bank population API;
   - web search via Claude.
3. Standardises successful and failed retrievals into a common evidence format.
4. Evaluates the collected evidence for:
   - source availability;
   - data age and freshness;
   - underlying provenance;
   - duplicate provenance;
   - pairwise numerical disagreement;
   - source quality.
5. Decides whether the current evidence is sufficient.
6. If necessary, adapts by:
   - retrying a failed source within a bounded retry limit;
   - seeking additional web evidence;
   - stopping when evidence is sufficient, the retrieval budget is reached, or no useful retrieval actions remain.
7. Reconciles the final evidence into:
   - one selected population value;
   - its year and publisher;
   - source quality;
   - a categorical confidence level (`high`, `medium`, or `low`);
   - a concise explanation of the result and any unresolved uncertainty.

The implementation is intentionally scoped to **country population facts** rather than attempting to be a general-purpose fact checker. I preferred a smaller system whose complete behaviour I could implement, test and explain over a broader system with shallow reconciliation logic.

---

## Architecture

```text
User input
    |
    v
Country name -> ISO alpha-3 code
    |
    v
+--------------------------------+
|           Agent loop           |
|                                |
|  Local CSV retrieval           |
|  World Bank API                |
|  Claude web search             |
|          |                     |
|          v                     |
|   Evidence evaluation          |
|          |                     |
|          v                     |
|   Choose next action           |
|          |                     |
|      repeat / stop             |
+--------------------------------+
    |
    v
Reconciliation
    |
    +--> deterministic confidence
    +--> deterministic best-evidence selection
    +--> grounded Claude explanation
    |
    v
Final answer
```

The main architectural separation is:

- **Retrieval** - obtain evidence.
- **Evaluation** - measure the quality and consistency of that evidence.
- **Agent policy** - decide what to do next.
- **Reconciliation** - decide what answer the accumulated evidence supports.
- **Language model** - handle narrowly scoped semantic tasks and produce a readable explanation.

---

# Data Sources

## 1. Local population dataset

The local source is a CSV based on the Kaggle **World Population Dataset**. The dataset metadata identifies World Population Review as its underlying source.

https://www.kaggle.com/datasets/iamsouravbanerjee/world-population-dataset?resource=download

The local retrieval function identifies the latest non-null population column available for the requested country.

This source is useful because it is:

- local and fast;
- available even if external services are unavailable;
- structurally predictable.

Its main limitation is freshness: the bundled dataset may be older than current API or web evidence.

---

## 2. World Bank API

The public World Bank API is queried for the population indicator:

```text
SP.POP.TOTL
```

The retrieval function walks through the returned records and selects the latest non-null population value.

The API path includes defensive error handling for request failures, timeouts, unusable responses and missing population data.

Importantly, an unavailable API does not terminate the program. A failure is converted into structured evidence with:

```python
"status": "failed"
```

This allows the agent to observe the failure and reason about what to do next.

---

## 3. Web search

Web retrieval uses Claude Haiku with Anthropic's web-search tool.

The model is deliberately constrained to retrieve **one webpage as one piece of evidence** rather than being asked to reconcile the entire problem itself.

For each web retrieval it identifies:

- population;
- reference year;
- publisher;
- underlying provenance, if stated;
- URL.

Structured JSON output is used so the result can be converted directly into the same evidence format as the local and API retrieval paths.

Previously used URLs are passed back as exclusions when another web retrieval is requested. This encourages the agent to seek additional evidence rather than repeatedly returning the same webpage.

---

# Standard Evidence Format

Each retrieval method returns the same core structure:

```python
{
    "retrieval_type": ...,
    "population": ...,
    "year": ...,
    "publisher": ...,
    "provenance": ...,
    "url": ...,
    "last_updated": ...,
    "status": "success" | "failed",
    "error": ...
}
```

Failures use the same shape, with unavailable values represented by `None`.

Standardising evidence early means the later evaluation and agent logic can operate on evidence without needing separate logic for every retrieval method.

---

# Evidence Evaluation

The evaluator deliberately separates measurable checks from semantic judgement.

## Availability

Only evidence where:

```python
status == "success"
```

is used for numerical reconciliation.

Failed retrieval attempts are still preserved in the complete evidence list so the system can reason about missing coverage and explain failures in the final response.

---

## Freshness

For each successful source, the evaluator calculates its age from its reference year.

Population data from different years is not automatically contradictory. Older evidence can still provide useful context, but it should not automatically be treated as equivalent to current evidence.

Freshness therefore contributes both to stopping decisions and final confidence.

---

## Provenance independence

A key distinction in the project is between:

- **retrieval source** - where the agent found the value;
- **underlying provenance** - where the population data ultimately originates.

This matters because two different websites can repeat the same underlying dataset.

For example, two websites both citing the same United Nations population dataset should not automatically count as two fully independent confirmations simply because they have different URLs.

Known provenance strings are normalised into canonical forms where possible.

The evaluator records:

- number of unique known provenances;
- duplicate provenance groups;
- number of unknown provenances.

This prevents confidence from being increased simply by retrieving the same underlying evidence through multiple publishing routes.

---

## Numerical disagreement

For every unique pair of successful population values, the evaluator calculates symmetric percentage difference:

```text
|A - B|
-------  x 100
(A + B) / 2
```

I used symmetric percentage difference because neither source is automatically assumed to be the correct baseline.

The pairwise comparison also preserves:

- publishers;
- retrieval methods;
- reference years;
- percentage difference.

This gives later stages more context than simply storing one disagreement number.

---

## Source quality

Source quality is represented categorically as:

```text
high
medium
unknown
```

The classification approach is intentionally hybrid.

### Deterministic classification

Sources that can be identified reliably using explicit rules are handled in code.

Examples include:

- World Bank → `high`;
- recognised official statistical provenance → `high`;
- secondary publishing/distribution platforms such as Kaggle or Wikipedia → `medium`, unless stronger underlying provenance is identified first.

### Semantic fallback

Publisher and provenance names encountered through web search are not always predictable.

If a source cannot be classified using the deterministic rules, Claude is used for a tightly constrained semantic classification task.

It can return only:

```text
high
medium
unknown
```

plus a short explanation.

This lets deterministic code handle obvious cases while using the language model where rigid string rules would become brittle.

---

# Agent Decision Policy

The agent is not a single LLM call or a fixed sequence of retrievals.

It maintains state containing:

- all evidence collected so far;
- URLs already used for web evidence;
- total retrieval count;
- attempt count for each retrieval mechanism;
- the latest evidence evaluation.

The agent initially attempts all three retrieval paths so it has a baseline of diverse evidence to evaluate.

After this initial retrieval phase, it enters an adaptive loop.

---

## Handling source failures

Each retrieval mechanism has a bounded number of attempts:

```text
MAX_SOURCE_ATTEMPTS = 2
```

If an initial source fails, the agent can retry it once.

If it continues to fail, the agent does not retry indefinitely.

If the available evidence is still insufficient and web-search attempts remain, the agent can use the remaining retrieval budget to seek additional web evidence instead.

This means a source outage changes subsequent behaviour.

---

## Evidence sufficiency

The current policy considers the evidence sufficient when it has:

- at least 3 successful sources;
- at least 3 unique known provenances;
- maximum pairwise disagreement below the configured acceptable threshold;
- at least one sufficiently recent source.

If those conditions are met, the agent stops early.

It does not perform extra retrievals simply because more retrieval budget exists.

---

## Bounded execution

The system also has a global retrieval budget:

```text
MAX_RETRIEVAL_COUNT = 5
```

This prevents uncontrolled searching and API usage.

The retrieval count is a maximum rather than a target.

The agent can therefore terminate because:

1. evidence is already sufficient;
2. no useful retrieval actions remain within the source attempt limits;
3. the global retrieval budget has been reached.

---

# Heuristic Thresholds

The current configuration contains intentionally simple policy thresholds:

```python
MAX_RETRIEVAL_COUNT = 5
MAX_SOURCE_ATTEMPTS = 2

MAX_ACCEPTABLE_DISAGREEMENT = 7.5
HIGH_DISAGREEMENT = 15.0
MAX_RECENT_AGE = 1
```

These are **engineering heuristics**, not statistically calibrated probabilities or universal truths.

I kept them explicit in `config.py` so that the behaviour is visible, explainable and easy to change rather than being hidden inside prompts or model behaviour.

---

# Reconciliation

Once the agent stops retrieving, the accumulated evidence is reconciled into a single result.

The reconciliation stage performs two important decisions deterministically:

1. confidence calculation;
2. best-evidence selection.

Claude does not decide either of these.

---

## Confidence

Confidence is categorical:

```text
high
medium
low
```

I intentionally avoided returning values such as `87% confidence`, because that would imply statistical calibration that the system does not currently have.

### Low confidence

Confidence becomes `low` when there is a major weakness in the evidence, such as:

- fewer than 2 successful sources;
- fewer than 2 unique known provenances;
- no recent source;
- very high numerical disagreement.

### Medium confidence

Confidence becomes `medium` when the evidence is usable but does not satisfy the stronger requirements for high confidence, including:

- fewer than 3 successful sources;
- fewer than 3 unique known provenances;
- disagreement above the acceptable threshold;
- fewer than 2 recent sources.

### High confidence

`high` is returned only when the evidence clears both the low- and medium-confidence checks.

Confidence therefore describes the quality of the **usable evidence that remains**, rather than simply whether every network request happened to succeed.

---

## Selecting the best evidence

The final population value is selected deterministically.

The policy is:

1. ignore failed evidence;
2. prefer evidence with higher source quality;
3. when quality ties, prefer the fresher reference year.

The system therefore returns a population value that actually came from one of the retrieved sources.

It does **not** average all returned values together.

Averaging could create a new figure that corresponds to no real source and would implicitly treat all evidence as equally trustworthy.

---

# Role of Claude

Claude is used in three deliberately limited parts of the system.

## 1. Web retrieval

Claude's web-search capability provides one of the three retrieval mechanisms.

It is instructed to retrieve one webpage as evidence rather than solve the complete reconciliation problem itself.

---

## 2. Ambiguous source-quality classification

Known sources are handled using deterministic rules.

Claude is only used when publisher/provenance information is unfamiliar enough that semantic classification is useful.

---

## 3. Final explanation

By the time Claude generates the final explanation, the program has already determined:

- selected population;
- reference year;
- publisher;
- source quality;
- confidence.

Claude receives the complete evidence and evaluation state and is explicitly instructed not to change the selected population or confidence.

Its role is to turn the structured reasoning state into a concise explanation covering:

- why the selected evidence was preferred;
- meaningful disagreement;
- stale evidence;
- failed retrievals;
- provenance limitations;
- why the confidence level is appropriate.

The prompt also prevents the model from:

- introducing unsupported facts;
- inventing methodological explanations;
- describing evidence as independent when duplicate provenance has been detected;
- claiming that year differences caused numerical differences;
- changing deterministic decisions already made by the program.

This separation was intentional.

I wanted deterministic code to control decisions that can be made explicitly and reproducibly, while using the language model for semantic tasks where it provides clear value.

---

# Graceful Degradation

Every retrieval path converts expected failures into structured evidence rather than allowing the entire application to terminate.

The agent can therefore observe a failure and adapt.

A possible failure path is:

```text
Local source       -> success
World Bank API     -> fail
Web search         -> success
World Bank retry   -> fail
Additional web     -> attempted
Retrieval budget   -> reached
                         |
                         v
              Reconcile available evidence
                         |
                         v
          Return answer + confidence + explanation
```

The important behaviour is that the agent does **not**:

- retry a failed service indefinitely;
- return silence;
- silently ignore the missing source;
- fabricate a missing value;
- automatically treat every retrieved source as independent.

Instead, it returns the strongest answer supported by the evidence it could obtain and exposes remaining uncertainty through confidence and explanation.

---

# Example Agent Behaviour

For a straightforward case where the initial evidence is sufficient:

```text
Enter a country: United Kingdom

[AGENT]
Action: Getting initial local data

[AGENT]
Action: Getting initial API data

[AGENT]
Action: Getting initial web data

[AGENT]
Action: finish
Reason: current evidence is sufficient
```

The agent stops after the initial three retrievals rather than searching unnecessarily.

A more difficult case can trigger:

```text
[AGENT]
Action: api
Reason: retrying, initial api retrieval failed

[AGENT]
Action: web_search
Reason: current evidence is insufficient; seeking additional web evidence
```

The system can then return a lower-confidence result if the remaining evidence has weak provenance coverage or substantial disagreement.

Because web retrieval is dynamic, exact web sources and values can vary between runs.

---

# Running Locally

## 1. Clone the repository

```bash
git clone <repository-url>
cd fact_reconciliation_agent
```

## 2. Create a virtual environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Add an Anthropic API key

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

The `.env` file should not be committed to the repository.

## 5. Ensure the local dataset is available

The project expects the population CSV at:

```text
data/world_population.csv
```

## 6. Run the agent

```bash
python src/main.py
```

Then enter a country:

```text
Enter a country: Bangladesh
```

The CLI prints the agent's retrieval decisions followed by the final reconciled result.

It also handles an unrecognised country name without attempting retrieval:

```text
Enter a country: United Kingdo
Country United Kingdo is not found
```

---

# Project Structure

```text
fact_reconciliation_agent/
|
|-- data/
|   `-- world_population.csv
|
|-- src/
|   |-- main.py
|   |-- agent.py
|   |-- evaluation.py
|   |-- reconciliation.py
|   |-- config.py
|   |
|   `-- tools/
|       |-- local_population.py
|       |-- world_bank.py
|       `-- web_population.py
|
|-- tests/
|   `-- test_claude.py
|
|-- requirements.txt
|-- .gitignore
`-- README.md
```

### `main.py`

The command-line entry point.

It resolves the user's country name to a country code, runs the agent and displays the reconciled result.

### `agent.py`

Owns orchestration:

- initial retrieval;
- agent state;
- retry limits;
- global retrieval budget;
- evidence sufficiency;
- adaptive next-action selection.

### `evaluation.py`

Evaluates:

- successful and failed retrievals;
- freshness;
- provenance independence;
- pairwise disagreement;
- source quality.

### `reconciliation.py`

Handles:

- deterministic confidence;
- deterministic best-evidence selection;
- constrained natural-language explanation.

### `config.py`

Contains explicit retrieval and evidence-policy thresholds.

### `tools/`

Contains the three distinct retrieval implementations.

---

# Design Decisions and Trade-offs

## Why population data?

The assessment allows many factual domains.

I deliberately narrowed the implementation to country populations so I could build the complete reconciliation loop rather than attempting a general fact agent whose reliability would be difficult to evaluate.

Population data also provides useful reconciliation challenges:

- values change over time;
- different sources can report different reference years;
- multiple publishers can share an underlying dataset;
- APIs can be unavailable or lack coverage;
- web evidence can disagree substantially.

---

## Why not let Claude make every decision?

It would be possible to give an LLM several sources and simply ask it which answer to trust.

I deliberately avoided that architecture because important decisions would become hidden inside a prompt.

Instead, objective operations are implemented in code:

- retrieval budgets;
- retry limits;
- freshness calculation;
- pairwise disagreement;
- known provenance matching;
- stopping conditions;
- confidence policy;
- final evidence selection.

Claude is used where semantic reasoning or natural-language synthesis provides clear value.

This also makes the system easier to inspect and defend: the final population and confidence can be traced back to explicit evidence and rules.

---

## Why categorical confidence?

Returning something such as:

```text
Confidence: 83.7%
```

would suggest a calibrated probability model that this project does not contain.

The `high` / `medium` / `low` levels instead communicate the strength of evidence according to transparent rules.

---

## Why not average all population values?

The retrieved values can represent different years and come from sources of different quality.

Averaging them would:

- treat sources as equally trustworthy;
- ignore differences in reference year;
- create a population figure that may not appear in any source.

The system instead chooses one best-supported evidence record and treats the remaining records as corroborating or conflicting evidence.

---

## Why distinguish publisher from provenance?

A web publisher is not necessarily the creator of the underlying data.

Two different websites can both publish values derived from the same dataset.

Without provenance tracking, the system could incorrectly interpret:

```text
website A -> UN dataset
website B -> UN dataset
```

as two independent confirmations.

Tracking underlying provenance allows duplicate evidence to reduce confidence appropriately.

---

## Why bounded retries?

A source being temporarily unavailable should not destroy the whole answer, but repeatedly retrying the same failed service is also not useful.

Each source therefore has a limited number of attempts and the complete agent has a global retrieval budget.

This gives the agent a clear failure policy and keeps execution bounded.

---

# Going Beyond the Minimum Requirements

The minimum requirement was to retrieve from at least three sources and reconcile their answers.

I added several mechanisms specifically to make the reconciliation more meaningful:

### Provenance-aware independence

Different webpages are not automatically counted as independent evidence. The system attempts to identify shared underlying provenance.

### Explicit numerical disagreement

Every successful source pair is compared using symmetric percentage difference rather than relying only on an LLM to describe whether numbers "look close."

### Hybrid source-quality evaluation

Known sources are evaluated deterministically, with a constrained semantic fallback for unfamiliar publishers/provenance.

### Adaptive retrieval

The agent does not simply call each source once and stop. Its next action depends on whether previous retrievals succeeded and whether the current evidence satisfies the configured requirements.

### Bounded failure recovery

Both per-source attempts and total retrievals are bounded, preventing blind retry loops.

### Deterministic reconciliation

The LLM does not choose the winning population or confidence level.

### Grounded explanation

The final language model receives the already-computed evidence state and is explicitly prevented from changing deterministic decisions or adding unsupported claims.

---

# Limitations

This is deliberately a small assessment implementation rather than a production-ready fact-verification platform.

Current limitations include:

- the system only supports country population questions;
- provenance normalisation is rule-based and cannot resolve every possible synonym or provenance chain;
- disagreement thresholds are heuristic rather than empirically calibrated;
- source-quality categories are intentionally coarse;
- web-search evidence is dynamic and may vary between executions;
- evidence identity currently relies on publisher/provenance fields rather than persistent source identifiers;
- best-evidence selection uses a simple quality-first, freshness-second policy;
- retrieval is sequential rather than concurrent;
- automated test coverage is limited;
- the bundled local dataset can become stale and requires manual updating.

These limitations are intentionally acknowledged rather than hidden behind the final generated explanation.

---

# What I Would Do Next

Given more time, I would prioritise the following improvements.

## 1. Stronger provenance resolution

I would build a more robust provenance layer that canonicalises common organisations and datasets and represents relationships between publishers and underlying datasets explicitly.

This would make duplicate-evidence detection more reliable than string normalisation alone.

---

## 2. Empirically calibrate confidence

The current disagreement and freshness thresholds are transparent heuristics.

With a larger labelled evaluation set, I would test the agent across many countries and failure conditions and calibrate the confidence policy against known outcomes.

---

## 3. Stronger evidence identity

Evaluated evidence is currently associated using publisher/provenance information.

I would introduce stable evidence/source identifiers so each retrieval can be tracked throughout the pipeline without relying on string matching.

---

## 4. Generalise to additional factual domains

The orchestration pattern could be extended so a domain supplies its own:

- retrieval tools;
- evidence schema;
- freshness policy;
- disagreement metric;
- source-quality rules.

This would allow the same agent architecture to support other factual domains without pretending that population-specific heuristics apply universally.

---

## 5. Parallelise initial retrieval

The three initial retrieval paths do not depend on each other, so they could be executed concurrently to reduce latency.

The adaptive stage would remain conditional because its actions depend on the evidence already observed.

---

## 6. Expand automated testing

I would add unit and integration tests covering cases such as:

- World Bank timeout;
- malformed local CSV;
- web-search failure;
- duplicate provenance;
- unknown provenance;
- substantial source disagreement;
- all sources unavailable;
- confidence-boundary conditions;
- retry limits;
- retrieval-budget exhaustion.

---

## 7. Structured observability

The current `[AGENT]` terminal output intentionally makes the decision process visible during the assessment demo.

For a more mature system, I would replace this with structured logging covering:

- retrieval action;
- reason for action;
- latency;
- success/failure;
- source selected;
- confidence;
- API/token cost.

---

## 8. Cost-aware retrieval

The current agent bounds resource usage through fixed attempt and retrieval limits.

A more advanced policy could explicitly track latency and monetary/token cost and use those alongside expected information value when selecting the next retrieval action.

---

# Final Notes

The goal of this project was not to build the largest possible agent.

It was to build a small system whose behaviour I could observe and account for end to end:

```text
retrieve
    ->
evaluate
    ->
decide whether more evidence is needed
    ->
adapt retrieval
    ->
reconcile
    ->
explain confidence and unresolved conflicts
```

The resulting system includes:

- three distinct retrieval mechanisms;
- standardised evidence;
- explicit freshness evaluation;
- provenance-aware corroboration;
- source-quality assessment;
- numerical conflict detection;
- bounded adaptive retries;
- graceful degradation;
- deterministic confidence;
- deterministic evidence selection;
- constrained LLM use for semantic tasks and explanation.

Most importantly, when the available evidence is weak, duplicated, unavailable or contradictory, the agent is designed to expose that uncertainty rather than silently hiding it.
