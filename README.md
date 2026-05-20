# Tech Diagnosis AI — Symbolic Expert System for Hardware & Software Fault Diagnosis

A deterministic, rule-based Knowledge-Based System (KBS) that diagnoses computer hardware and software faults through multi-layer forward-chaining inference with MYCIN-style Certainty Factor propagation.

This is **not** a machine learning system. There are no trained models, no statistical pattern matching, and no gradient-based optimization. Every conclusion is derived from explicit symbolic reasoning over a structured knowledge base.

![Tech Diagnosis AI](screenshot.png)

---

## Problem Overview

Hardware and software troubleshooting is a structured reasoning task — not a prediction problem. When a device exhibits symptoms like overheating, random shutdowns, or disk performance degradation, there is a well-defined logical chain connecting observable evidence to root causes and corrective actions.

This domain is well-suited to rule-based reasoning because:

- Diagnostic logic is **expressible as explicit IF-THEN rules**, not latent statistical patterns
- Conclusions must be **auditable** — a user needs to understand *why* a recommendation was made
- The problem space is **bounded and enumerable** — faults fall into a finite set of causal categories
- **Determinism matters** — the same symptoms must always produce the same reasoning path

A machine learning model trained on fault logs would be a black box that produces probabilities with no interpretable reasoning trace. An expert system produces a fully explainable decision path from evidence to recommendation.

---

## System Features

- **Multi-layer forward-chaining inference** — symptoms resolve to issues, issues resolve to causes, causes resolve to recommendations across three discrete reasoning layers
- **MYCIN Certainty Factor propagation** — rule confidence is propagated through inference chains and combined when multiple rules contribute to the same conclusion
- **Backward-traversal explanation graph (XAI)** — a recursive dependency walker generates a human-readable reasoning trace showing exactly which rules fired and why
- **Priority-weighted rule evaluation** — rules carry explicit priority scores that govern resolution order when multiple rules compete for the same conclusion
- **Loop protection with firing signatures** — each rule firing is fingerprinted as `(rule_id, sorted_matched_facts)` to prevent redundant re-evaluation and infinite loops
- **Asynchronous inference execution** — UI runs inference on a `QThread` worker to keep the interface responsive during evaluation
- **Self-contained Windows executable** — packaged with PyInstaller; no Python runtime required for end users

---

## AI Reasoning Architecture

### Symbolic AI vs. Machine Learning

| Property | This System | Machine Learning |
|---|---|---|
| Knowledge source | Hand-crafted IF-THEN rules | Learned from training data |
| Reasoning | Deterministic symbolic inference | Statistical pattern matching |
| Explainability | Full rule trace available | Typically opaque |
| Requires training data | No | Yes |
| Output | Conclusion + CF score + reasoning graph | Probability distribution |
| Modifiable by experts | Yes — edit `rules.json` | Requires retraining |

This system is a **forward-chaining production rule system** in the tradition of MYCIN and CLIPS. The knowledge base is separable from the inference engine — rules can be added, removed, or modified without touching engine code.

### Rule Structure

Each rule is a JSON object with the following schema:

```json
{
  "id": "R1",
  "layer": "issue",
  "conditions": [
    { "fact": "overheating", "value": true },
    { "fact": "fan_noise_high", "value": true }
  ],
  "conclusion": {
    "fact": "thermal_issue",
    "value": true,
    "name": "Thermal Issue Detected"
  },
  "confidence": 0.95,
  "priority": 10
}
```

- `layer` — determines at which stage of reasoning the rule fires (`issue`, `cause`, `recommendation`)
- `conditions` — a conjunction of fact-value pairs that must all be present in working memory
- `confidence` — the rule's inherent certainty, used as the base for CF propagation
- `priority` — governs tie-breaking when multiple rules produce the same conclusion

### Inference Logic

The engine runs iterative forward chaining. At each iteration, every rule is evaluated against working memory:

1. All conditions are checked against current working memory
2. If all conditions are satisfied, the rule **fires**
3. The conclusion fact is added to working memory (or its CF is updated if it already exists)
4. Iteration continues until no new facts are derived (`changed = False`) or the safety cap of 100 iterations is reached

This is a **data-driven, exhaustive** strategy — the engine derives everything it can from the available evidence before returning results, rather than stopping at the first match.

### Certainty Factor Propagation

CF propagation follows the MYCIN model:

**Propagation** (confidence through a reasoning chain):
```
CF_conclusion = rule_CF × min(CF_premises)
```
The conclusion is bounded by the weakest premise in the chain.

**Combination** (when multiple rules support the same conclusion):
```
CF_combined = CF1 + CF2 − (CF1 × CF2)
```
Converges toward 1.0 as more evidence accumulates, but never exceeds it.

---

## Knowledge Base Design

The knowledge base is stored in two JSON files and is fully decoupled from the engine.

### `facts.json` — Observable Symptom Vocabulary

Defines the 16 observable symptoms a user can report. Each fact has a unique ID and a human-readable description:

```
overheating          → "Device feels unusually hot"
fan_noise_high       → "Fans are loud or constantly spinning"
slow_performance     → "System is running much slower than usual"
clicking_noise       → "Clicking or grinding noise coming from the PC"
no_display           → "Computer turns on but screen remains black"
beeping_startup      → "Computer beeps several times during startup"
... (16 total symptoms)
```

These are the **input layer** — only these facts are provided by the user. All other facts are inferred.

### `rules.json` — Three-Layer Rule Hierarchy

Rules are organized into three semantic layers that model a complete diagnostic reasoning chain:

**Layer 1 — Issue Detection** (R1–R10)
Maps raw symptom combinations to intermediate diagnostic conclusions.

```
R1:  overheating ∧ fan_noise_high          → thermal_issue         (CF: 0.95)
R2:  random_shutdown ∧ battery_drain       → power_issue           (CF: 0.90)
R4:  slow_performance ∧ high_disk_usage    → io_bottleneck         (CF: 0.90)
R8:  clicking_noise                        → mechanical_failure    (CF: 0.99)
R9:  no_display ∧ beeping_startup          → post_failure          (CF: 0.95)
```

**Layer 2 — Cause Attribution** (R11–R20)
Maps issue conclusions (possibly combined with contextual facts like `device_old`) to root causes.

```
R11: thermal_issue ∧ device_old            → dust_accumulation     (CF: 0.90)
R12: thermal_issue                         → thermal_paste_degradation (CF: 0.60)
R14: power_issue ∧ thermal_issue           → thermal_shutdown      (CF: 0.90)
R18: mechanical_failure                    → hdd_failing           (CF: 0.99)
```

**Layer 3 — Recommendation Generation** (R21–R32)
Maps root causes to actionable repair recommendations.

```
R21: dust_accumulation     → clean_fan              (CF: 0.95)
R26: failing_storage       → backup_data            (CF: 0.99)
R28: hdd_failing           → backup_and_replace_hdd (CF: 0.99)
R31: post_failure          → check_ram_seating      (CF: 0.95)
```

This three-layer architecture models the natural structure of expert diagnostic reasoning: observe → identify the problem → find the cause → prescribe the fix.

---

## Inference Engine

**Strategy: Iterative Forward Chaining with Loop Protection**

The engine (`engine/inference_engine.py`) implements a **data-driven forward-chaining** algorithm. Starting from user-reported symptoms, the engine exhaustively fires all applicable rules until the working memory reaches a fixed point.

**Execution flow:**

```
1. Load user-selected symptoms into working memory (initial facts, CF = 1.0)
2. Begin iteration loop (max 100 iterations, loop protection active)
3. For each rule in rules.json:
   a. Check all conditions against working memory
   b. If all conditions match → rule fires
   c. Compute CF_new = rule_CF × min(premise_CFs)
   d. If conclusion is new → add to working memory
   e. If conclusion exists → CF_combined = CF1 + CF2 − (CF1 × CF2)
   f. Record firing edge in trace_graph: (rule_id, from_facts, to_fact, cf_contribution)
4. If no new facts were derived → terminate
5. Return (working_memory, trace_graph)
```

**Loop Protection:**
Each rule firing is recorded as a signature `(rule_id, frozenset(matched_fact_ids))`. A rule is not allowed to fire on the same evidence set twice, preventing infinite cycles if rules were to form circular dependencies.

**Explanation System: Backward Traversal**

After inference, `engine/explanation.py` runs a recursive backward traversal over the `trace_graph` edges. Starting from a target conclusion, it walks back through all contributing rule firings to the original user-supplied facts, building a readable reasoning tree at each level.

---

## Example Diagnosis Flow

**User reports:**
- Overheating
- Loud fan noise
- Random shutdowns
- Battery draining fast
- Device is more than 4 years old

**Working memory after user input:**
```
overheating       = True  (CF: 1.0)
fan_noise_high    = True  (CF: 1.0)
random_shutdown   = True  (CF: 1.0)
battery_drain     = True  (CF: 1.0)
device_old        = True  (CF: 1.0)
```

**Iteration 1 — Issue layer fires:**

```
R1 fires:  overheating ∧ fan_noise_high → thermal_issue
           CF = 0.95 × min(1.0, 1.0) = 0.95

R2 fires:  random_shutdown ∧ battery_drain → power_issue
           CF = 0.90 × min(1.0, 1.0) = 0.90
```

**Iteration 2 — Cause layer fires:**

```
R11 fires: thermal_issue ∧ device_old → dust_accumulation
           CF = 0.90 × min(0.95, 1.0) = 0.855

R12 fires: thermal_issue → thermal_paste_degradation
           CF = 0.60 × min(0.95) = 0.57

R13 fires: power_issue ∧ device_old → battery_degradation
           CF = 0.95 × min(0.90, 1.0) = 0.855

R14 fires: power_issue ∧ thermal_issue → thermal_shutdown
           CF = 0.90 × min(0.90, 0.95) = 0.81
```

**Iteration 3 — Recommendation layer fires:**

```
R21 fires: dust_accumulation → clean_fan          (CF: 0.95 × 0.855 ≈ 0.812)
R22 fires: thermal_paste_degradation → repaste    (CF: 0.90 × 0.57 ≈ 0.513)
R23 fires: battery_degradation → replace_battery  (CF: 0.99 × 0.855 ≈ 0.847)
R24 fires: thermal_shutdown → improve_ventilation (CF: 0.95 × 0.81 ≈ 0.770)
```

**Iteration 4 — No new facts derived. Engine terminates.**

**Final diagnosis output (ordered by priority and CF):**

| Recommendation | CF Score |
|---|---|
| Improve device ventilation immediately | 0.770 |
| Clean cooling fans and vents | 0.812 |
| Replace Battery | 0.847 |
| Repaste CPU/GPU | 0.513 |

**Explanation trace for `thermal_shutdown`:**
```
* Inferred: Critical Thermal Shutdown (Final CF: 0.81)
  Because Rule R14 fired:
    * Inferred: Power Delivery Issue (Final CF: 0.90)
      Because Rule R2 fired:
        - random_shutdown (Initial User Input)
        - battery_drain (Initial User Input)
    * Inferred: Thermal Issue Detected (Final CF: 0.95)
      Because Rule R1 fired:
        - overheating (Initial User Input)
        - fan_noise_high (Initial User Input)
```

---

## Technologies Used

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Inference engine | Custom forward-chaining implementation |
| Confidence model | MYCIN Certainty Factor arithmetic |
| Knowledge base | JSON (rules + facts, engine-agnostic) |
| GUI framework | PySide6 (Qt6 bindings) |
| Async execution | `QThread` worker pattern |
| Explainability | Recursive backward graph traversal |
| Packaging | PyInstaller (single-file `.exe`) |
| Installer | Inno Setup (`.iss` script) |
| Testing | Python `unittest` (`test_engine.py`) |

---

## Project Structure

```
KBS Project/
├── engine/
│   ├── inference_engine.py    # Forward-chaining core with CF propagation and loop protection
│   ├── confidence.py          # MYCIN Certainty Factor: combine() and propagate()
│   └── explanation.py         # Recursive backward-traversal explanation graph builder
├── knowledge_base/
│   ├── facts.json             # Observable symptom vocabulary (16 symptoms)
│   └── rules.json             # Three-layer diagnostic rule set (32 rules: R1–R32)
├── ui/
│   ├── app.py                 # PySide6 async UI, QThread worker, dark theme
│   └── interface.py           # UI component layout and bindings
├── main.py                    # Application entry point
├── test_engine.py             # Unit tests for inference correctness
├── requirements.txt           # Python dependencies (PySide6)
├── Tech Diagnosis AI.spec     # PyInstaller build specification
├── Tech Diagnosis AI.exe      # Pre-built Windows executable
├── Tech_Diagnosis_AI_Setup.exe # Inno Setup installer
└── setup.iss                  # Inno Setup compiler script
```

---

## Screenshots

**Diagnosis Interface — Symptom selection and result display**

![Diagnosis Interface](screenshot.png)

> Additional screenshots: reasoning trace output, rule evaluation panel, and CF score display.

---

## Engineering Challenges

**1. Preventing conflicting conclusions from multi-path inference**

When multiple rules can fire to produce the same conclusion via different evidence paths, the system must combine their certainty contributions rather than override one with the other. This required implementing the MYCIN probabilistic sum (`CF1 + CF2 − CF1×CF2`) to accumulate evidence correctly, and tracking whether a fact was newly derived or already in memory before deciding whether to combine or insert.

**2. Designing rules that avoid false positives**

Single-condition rules (e.g., R8: `clicking_noise → mechanical_failure`, CF: 0.99) are intentionally high-confidence because the symptom is highly specific. Multi-condition rules (e.g., R1: `overheating ∧ fan_noise_high`) are used when individual symptoms are ambiguous on their own. Getting this balance right — specificity vs. coverage — required deliberate rule authoring rather than mechanical enumeration.

**3. Preventing infinite loops in iterative inference**

Without protection, a rule that fires on an inferred fact (which was itself a conclusion) could theoretically create cycles if rules were bidirectional or contradictory. The solution was to fingerprint each firing event as `(rule_id, sorted_matched_facts)` and reject re-firing on identical evidence, while still allowing a rule to re-fire on genuinely new evidence combinations.

**4. Ordering recommendations when multiple are valid**

The engine can derive multiple valid recommendations simultaneously. Presenting them meaningfully required assigning priority scores to rules so that high-urgency recommendations (e.g., `backup_data`, priority 25) surface above lower-urgency ones (e.g., `update_usb_drivers`, priority 5), independent of the order in which rules happened to fire.

**5. Maintaining knowledge base scalability**

The three-layer rule hierarchy (issue → cause → recommendation) keeps rules single-responsibility. Adding a new hardware category requires adding rules to each relevant layer independently, without modifying other rules. This reduces the risk of unintended interactions when the knowledge base grows.

---

## Limitations

- **Static knowledge base** — rules are hand-authored and do not update from diagnostic outcomes. There is no feedback loop or self-correction mechanism.
- **No probabilistic reasoning over continuous data** — the system works with boolean facts. It cannot reason over sensor readings, temperature values, or CPU load percentages directly.
- **Binary symptom model** — each symptom is either present or absent. Partial or graduated symptoms (e.g., "slightly warm" vs. "critically hot") are not representable in the current fact schema.
- **Closed-world assumption** — facts not reported by the user are treated as false. The system cannot express uncertainty about whether a symptom exists versus whether it was simply not observed.
- **Limited rule coverage** — 32 rules cover common fault categories. Unusual or compound failures (e.g., simultaneous RAM and GPU failure) may fall outside current rule coverage.
- **No machine learning component** — the system cannot discover new diagnostic patterns from historical cases.

---

## Future Improvements

- **Probabilistic fact representation** — extend the fact schema to support fuzzy or graded truth values, enabling rules to reason over graduated evidence rather than boolean flags
- **Bayesian network integration** — replace or augment CF arithmetic with a Bayesian network to support more rigorous probabilistic reasoning with conditional independence
- **Hybrid symbolic + statistical pipeline** — use an ML model to classify ambiguous symptom descriptions from free-text input, then pass structured facts into the symbolic inference engine
- **Expandable rule authoring interface** — build a domain expert UI for adding and editing rules without touching JSON directly
- **Case-based reasoning layer** — store resolved cases and use similarity matching to retrieve analogous past diagnoses as supporting evidence
- **REST API deployment** — expose the inference engine as a stateless HTTP endpoint, enabling integration with remote diagnostic tools or technician dashboards

---

## Installation & Usage

### Option A — Run the Pre-built Executable (Windows)

No Python required. Download and run directly:

```
Tech Diagnosis AI.exe
```

Or use the installer for a proper Windows installation:

```
Tech_Diagnosis_AI_Setup.exe
```

### Option B — Run from Source

**Requirements:** Python 3.10+

```bash
git clone https://github.com/Mark1amgad/Tech-Diagnosis-AI.git
cd Tech-Diagnosis-AI
pip install -r requirements.txt
python main.py
```

### Option C — Rebuild the Executable

If you modify the source and want to repackage:

```bash
pip install pyinstaller
pyinstaller "Tech Diagnosis AI.spec"
```

Output will be placed in the `dist/` directory.

---

## Symbolic AI Context

This system implements the classical **production rule model** of expert systems. The architecture cleanly separates three components that are distinct in any well-engineered KBS:

- **Knowledge Base** — domain-specific facts and rules, authored by subject matter experts, stored in `knowledge_base/`
- **Inference Engine** — domain-agnostic reasoning mechanism that applies rules to facts, implemented in `engine/`
- **Working Memory** — the dynamic fact store that accumulates derived conclusions during a reasoning session

This separation means the inference engine is reusable across different diagnostic domains — swapping `rules.json` for a different rule set would redirect the same engine toward a different problem space without any code changes.

---

### Author
* **Mark Amgad Nassief Botros Mekhaiel**
  * *Artificial Intelligence Engineering Student*
  * *Faculty of Computer Science and Engineering*
  * *New Mansoura University*
