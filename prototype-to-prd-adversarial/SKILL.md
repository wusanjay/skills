---
name: prototype-to-prd-adversarial
description: Generate, review, and harden a product PRD from a prototype or demo, especially HTML prototypes, clickable mocks, screenshots, design files, meeting notes, spreadsheets, and product方案. Use whenever the user asks to turn a prototype into a PRD, align a PRD to a prototype, review a prototype-derived PRD, or run adversarial review and repair. It separates demo behavior from formal requirements, traces claims to evidence, resolves conflicts through meeting decisions, records unresolved decisions instead of inventing them, and runs multiple orthogonal review passes until the document passes mechanical and product-quality gates.
---

# Prototype → PRD Adversarial Workflow

Use this skill when a prototype is being treated as the starting point for a product requirements document. The prototype is evidence, not the requirements source. Your job is to reconstruct the intended product contract, expose what the prototype only simulates, and leave a PRD that another team can implement without reopening the prototype for basic facts.

## Operating principles

1. **Separate evidence from interpretation.** Every important claim must be traceable to a source or explicitly labeled as a recommendation.
2. **Treat the prototype as demo truth, not requirement truth.** A visible button, fixed number, toast, hard-coded sample, or animation does not prove a production capability.
3. **Prefer the latest explicit user decision.** For unresolved product decisions, inspect meeting content first as requested by the user, then cross-check the prototype and authoritative project documents. If the dispute remains, do not choose silently: create a decision item.
4. **Do not let an agent’s repair suggestion become a fact automatically.** Issue localization and repair proposals have different confidence levels. Re-verify every number, threshold, date, role, state, and rule in the original evidence before writing it.
5. **Keep business scope separate from demo coverage.** The industries, customer segments, or workflows prioritized by the business may differ from the samples embedded in the prototype.
6. **Make the PRD implementable without the prototype.** Add permission, empty, error, retry, missing-data, audit, and terminal-state behavior that a production product needs, while labeling it as a formalized addition when the prototype does not show it.
7. **Use recommendations without disguising them as decisions.** A useful recommendation is allowed; it must say that it is a recommendation and name the decision owner or confirmation path.

## Evidence model

Before drafting, build an evidence matrix. At minimum, capture:

| Evidence type | Extract | Label in PRD |
|---|---|---|
| Confirmed decision | User instruction, approved meeting conclusion, signed or authoritative project rule | `已确认` / source citation |
| Prototype design | Page, label, route, action, field, state, enum, data shape | `原型设定` |
| Demo simplification | Static sample, fixed score, fake progress, toast-only action, mock authorization, placeholder content | `演示差异` |
| Formalized product addition | Production behavior absent from the prototype but required for implementation | `PRD 新增要求（原型未实现）` |
| Recommendation baseline | Reasonable proposed default not yet approved | `PRD 建议基线（未经确认）` |

These are the skill's **four evidence/status labels**; use them consistently rather than inventing synonyms. Do not call a claim `已确认` merely because it exists in the prototype. Do not cite a meeting for a rule that only appears in the prototype. Do not cite memory, a previous summary, or an agent report without checking the original file.

### Source extraction checklist

For the prototype, record:

- all top-level surfaces, routes, navigation entries, entry points, and return paths;
- buttons and their actual handlers, including `data-*` delegation, inline handlers, template-string actions, and toast-only actions;
- fields, enums, validation, loading, empty, error, retry, success, cancellation, and terminal states;
- roles, permissions, ownership, visibility boundaries, and tenant/context switching;
- data constants, derived values, scoring, thresholds, date ranges, sample names, and displayed figures;
- which actions mutate state and which only show a message;
- prototype limitations, disclaimers, fixed samples, simulated integrations, and absent controls.

For meetings, requirements files, spreadsheets, and product plans, record:

- exact decision text and the date/context in which it was made;
- unresolved alternatives and the people responsible for deciding them;
- required data fields, periods, providers, formats, priority, authorization, and masking rules;
- business scope versus sample coverage;
- expert or human-review boundaries;
- commitments that are explicitly not in scope.

For long single-file prototypes, use line-numbered reads and search both static markup and JavaScript/data definitions. A single grep hit is not enough to prove a capability is absent: check definitions, templates, event delegation, `data-*` attributes, inline strings, and, when relevant, browser behavior.

## Drafting contract

Start the PRD with a short document contract:

- what the document describes (formal product behavior, not merely the demo);
- which chapter explains prototype differences;
- where unresolved decisions live;
- which values are samples, estimates, or placeholders;
- the product stage and version.

Use one primary term for each concept and include a compact terminology table when the prototype uses aliases. Enumerations must be complete and counted. Avoid leaving `TBD`, `待拍板`, or unexplained placeholders in a purported final PRD.

A practical PRD structure is:

1. product position, scope, goals, and success measures;
2. users, roles, permissions, and tenant/data boundaries;
3. information architecture and navigation;
4. end-to-end workflows;
5. functional requirements with IDs, priority, behavior, validation, states, and acceptance;
6. data, rules, scoring, thresholds, integrations, and human-review boundaries;
7. non-functional requirements and security;
8. MVP phases and explicit exclusions;
9. acceptance criteria;
10. disputed decisions and ordinary confirmations;
11. prototype-versus-PRD differences;
12. source index.

Adapt the structure to the product; do not invent modules merely to fill headings.

### Requirements writing rules

For each important requirement, specify as applicable:

- actor and permission;
- trigger and preconditions;
- input fields, requiredness, format, period, and source;
- normal behavior and output;
- empty, invalid, missing-data, timeout, denial, retry, cancellation, and duplicate-submission behavior;
- state transitions and terminal behavior;
- audit/event history and ownership;
- acceptance criteria;
- evidence label and source location.

When the prototype performs only a toast or simulated flow, write both facts separately:

- prototype behavior: what the demo currently does;
- formal product requirement: what the production implementation should do;
- gap label: `原型演示差异` or `PRD 新增要求（原型未实现）`.

Do not silently upgrade an animation, fixed sample, static count, simulated authorization, or toast into a production SLA or implemented capability.

### Numbers and examples

Treat every number as a claim requiring evidence: periods, counts, ratios, thresholds, prices, amounts, response times, file limits, retention windows, sample scores, and industry counts. Before writing a number, search all source files and record the exact source. If sources disagree:

1. list the original values;
2. state which source is the current working baseline, if a noncontroversial operational baseline is needed;
3. put unresolvable differences in the decision or confirmation chapter;
4. never make a precise number from a vague statement.

Copy examples from the evidence source rather than reconstructing them from memory. Keep business scope and prototype sample coverage in separate sentences or explicitly label the distinction.

## Decision handling

Use two separate sections:

### Disputed decisions

Create a `待决策` section for multi-party disagreement, unresolved meeting language, or choices that materially change scope, behavior, pricing, data use, or architecture. Each item should contain:

- ID;
- evidence from each relevant source;
- alternatives and the exact disagreement;
- current working baseline, if one is needed to keep implementation moving;
- recommendation, clearly marked as `PRD 建议基线（未经双方确认）`;
- decision owner;
- affected PRD sections.

In正文, use the pattern: **“现行基线……最终以 D-x 决策为准。”** Do not write an unresolved option as `已定`.

### Ordinary confirmations

Use a separate `待确认` section for routine follow-up such as customer lists, file templates, integration contacts, operational schedules, or measured performance baselines. It may include a recommendation, but begin the section with:

> 以下建议基于已核对的原型、会议和项目资料，供确认时参考，不视为已定口径。

Any suggestion that touches a disputed item must explicitly defer to `D-x`.

## Adversarial review loop

Do not stop after one “looks good” review. Use orthogonal passes; each pass asks a different question.

### Pass 1: source-to-PRD trace

Review by chapter. Classify every finding as:

- **错误**: contradicts the evidence;
- **遗漏**: prototype/decision requires it but PRD lacks it;
- **无依据**: PRD asserts it without a source;
- **内部矛盾**: different PRD sections disagree;
- **演示混淆**: demo behavior is written as production behavior.

Every finding needs a file/line or exact source excerpt and a concrete repair proposal.

### Pass 2: scenario and implementation walk

Run these scenarios against the PRD, not just the happy path:

1. a new subject enters with no data;
2. registration, authorization, or submission is denied and retried;
3. parsing, review, or approval fails and returns for correction;
4. a workflow reaches its terminal state and then receives a new event;
5. the user switches subject, role, tenant, or context;
6. a marketing or narrative promise claims a complete loop—verify every step has a requirement.

Also perform a terminology/enum pass and an “implementer does not open the prototype” pass: select several P0 modules and list any missing fields, states, validation, empty/error behavior, or permissions.

### Pass 3: patch coherence

After repairs, grep every changed concept and compare all occurrences. Specifically check:

- repeated dates, counts, thresholds, prices, periods, and role names;
- list numbering, requirement IDs, section references, and decision IDs;
- `已确认`, `原型设定`, `演示差异`, `PRD 新增要求`, and `PRD 建议基线` labels;
-正文 claims versus the decision chapter;
- source index versus actual citations.

### Pass 4: fresh-eyes review

Run one review with no repair history, no “already fixed” list, and no prior reviewer conclusions. Give it only the PRD and evidence sources. This prevents the reviewer from validating the patch list while overlooking untouched chapters. If an agent is unavailable, perform the same pass in the main session using direct file extraction.

### Repair proposal verification

Before applying any reviewer suggestion:

1. separate the finding from the proposed wording;
2. verify every number, threshold, date, role, and state in the original evidence;
3. if verified, apply it with the correct evidence label;
4. if not verified but useful, downgrade it to a recommendation baseline or a decision item;
5. if unsupported and unnecessary, reject it.

The reviewer’s suggestion is not evidence. Neither are memory, summaries, or previous-session conclusions.

## Mechanical quality gate

Run a small script or equivalent checks after every repair round and before delivery:

- chapter headings are sequential;
- ordered lists have no duplicate or skipped numbers;
- Markdown tables have consistent column counts;
- every `D-x`, `FR-x`, `DEC-x`, or local cross-reference has a target;
- parentheses and quotation marks are balanced enough for the document’s conventions;
- links resolve or are explicitly local references;
- forbidden residue scan is clean (`TBD`, stale labels, old numbers, obsolete feature names);
- the version increments with a short change note;
- disputed claims use “current baseline / final per D-x” wording;
- every final claim has an evidence source or an explicit recommendation label.

For prototype changes, add syntax checks, static assertions, browser flow tests, and diff-level regression review. Keep read-only review agents read-only; never let an analysis task perform Git operations.

## Completion standard

Finish only when:

- the PRD can be implemented without reopening the prototype for basic behavior;
- demo-only behavior is visibly separated from formal requirements;
- every disputed item is in the decision section or explicitly resolved by a source;
- every recommendation is recognizable as a recommendation;
- all four adversarial passes or documented fallbacks are complete;
- mechanical checks pass;
- the final response names remaining decisions and states any residual risks instead of claiming certainty.
