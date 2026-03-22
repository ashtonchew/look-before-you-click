# Related Work Outline

## Working positioning

AI-control-style evaluation of critical-action deferral with state-grounded review for computer-use agents.

## Anchor comparisons

| Work | Why it matters | Key difference from us |
|---|---|---|
| Greenblatt et al. | Control-evaluation framework | Prior work is not centered on GUI/live-state review |
| Redwood control-evals guidance | Methodology for adaptive attackers and control claims | Mostly methodological rather than GUI empirical |
| OS-Harm | Core environmental attack benchmark | Benchmark only, not a control protocol |
| Ctrl-Z / BashArena | Closest resampling-style agent control comparison | Terminal/shell setting, not sparse GUI critical-action deferral |
| Adaptive Attacks on Trusted Monitors | Strongest caution for protocol-aware attackers | Not a GUI-state action-review setting |

## Key differentiators

- GUI/live-state review using screenshot + accessibility tree.
- Sparse routing over critical irreversible actions rather than blanket review.
- Evaluation under both environmental and scheming-style threat models.
- Explicit safety/usefulness/overhead framing rather than benchmark-only reporting.
- Narrow protocol variants for resampling and one-step trusted fallback.

---

## Executive positioning summary

Look-Before-You-Click is best positioned as **an AI-control-style protocol and evaluation for computer-use agents (CUAs)** rather than a new agent, a new benchmark, or a security product. The project’s core contribution is to **translate established AI control ideas—trusted monitoring, selective intervention, and protocol-level supervision—into the “real desktop GUI action stream” setting**, using **live UI state** (screen + accessibility tree + recent action history) as the primary evidence substrate for oversight. This puts the work at the intersection of: (i) **control evaluations and trusted monitoring** (originally developed mostly in code/tool-call or transcript-based settings) and (ii) **computer-use benchmarks** like OSWorld/OS-Harm that expose concrete GUI-mediated risk surfaces (sending, uploading, deleting, permissions, external navigation, etc.). citeturn2search0turn2search1turn10search2turn0search3

A clean conceptual lineage is: **trusted monitoring + action-level approval**, specialized to **sparse, critical-action deferral**. In “classic” control framing, the blue team tries to preserve usefulness while preventing side objectives under adversarial pressure; protocols often involve (a) monitors that flag suspicious behavior, (b) resampling/redoing untrusted steps to reduce risk, and/or (c) deferring sensitive components to a trusted process. citeturn2search0turn2search1turn12search0turn15search0 Look-Before-You-Click instantiates this as: *intercept an untrusted agent’s proposed GUI action right before execution; route only a small class of high-impact actions to a trusted reviewer who can verify them against live state; optionally request an untrusted explanation artifact; allow/block/resample once; optionally execute a single trusted fallback action*. The novelty is not “human oversight exists,” but rather the **specific tradeoff claim and its evaluation**: that **catastrophic failures concentrate in a small family of GUI actions that (a) are unusually irreversible and (b) are unusually legible from live UI state**, enabling a better safety–usefulness–latency Pareto point than blanket review.

This positioning matters because adjacent literatures tend to over-index on one of two extremes:

- **“Full security systems” for CUAs** that attempt comprehensive enforcement (system-level access control, formal verification, end-to-end security auditing, architectural isolation), which are stronger but are not the same object as a *thin protocol wrapper + evaluation* and often claim broad robustness. citeturn8search0turn10search1turn9search0turn11search2  
- **“Prompt-injection defenses”** that focus on information-flow separation, prompt hardening, or content filtering, often without analyzing an **AI-control-style adversary** (protocol-aware attackers, scheming/side objectives, adaptive evasion) and without surfacing the intervention granularity/latency tradeoff at the GUI action boundary. citeturn13search0turn1search0turn1search2turn10search0

The closest comparisons are therefore works that (i) explicitly study **control protocols** with adversarial pressure (including protocol awareness), (ii) place the agent in an **interactive environment**, and/or (iii) implement **pre-execution action gating** (even if for security rather than control). The most “direct line” on the control side is the AI-control/control-evaluation family (including resampling, trusted monitoring, and deferral) and its later findings about **adaptive attacks** and **monitor gaming**. citeturn2search0turn2search1turn2search2turn6search0turn14search0 The most “direct line” on the CUA side is OSWorld/OS-Harm and the emerging CUA security benchmark/defense literature that targets prompt injection, dark patterns, and UI-specific perception/TOCTOU failures. citeturn0search3turn10search2turn10search0turn16view0turn19search0

A narrow, defensible novelty claim—relative to this prior art—is:

> **Novelty (narrow):** a control-style evaluation of **critical-action deferral** for **OSWorld-style GUI agents**, where the reviewer’s decision is **state-grounded in live GUI evidence** (screen + accessibility tree + interaction context), and where the protocol is explicitly studied under (a) **environmental prompt-injection-style attacks** and (b) **scheming-style hidden-objective attacks**, including variants with resampling and one-step trusted fallback.

This is meaningfully narrower than claiming “a robust defense for CUAs” because multiple recent papers show powerful failure modes that can occur **without** a clean “critical-click checkpoint” (timing/TOCTOU races; pre-checkpoint harm; perception failures; injection into monitor inputs; protocol-aware evasion). citeturn18search0turn19search0turn2search2turn10search1turn14search0 Those results also directly inform Look-Before-You-Click’s own stated limitations (timing problems, routing gaps, stop_task-style attacks), which should be framed as **expected boundary failures** rather than surprising corner cases.

The most dangerous overclaims to avoid, given the literature:

- **“This solves prompt injection”**: prompt injection remains broadly unsolved under adaptive attackers, and multiple benchmarks show high attack success rates against agents in realistic settings; even strong mitigations can be brittle once the adversary adapts. citeturn1search2turn10search0turn13search0turn13search3  
- **“This is a full security system for computer use”**: system-level approaches (policy enforcement, comprehensive auditing, architectural isolation) explicitly aim for broader coverage and often require deeper integration than a protocol wrapper. citeturn8search0turn10search1turn11search2turn9search0  
- **“Sparse review is robust against protocol-aware attackers”**: adaptive attack work in control shows that protocol knowledge can collapse safety, and monitor red-teaming work indicates that agent awareness often dominates monitor advantage. citeturn2search2turn8search2turn14search0  
- **“State grounding makes oversight reliable”**: richer inputs can help, but there are documented “less-is-more” effects and failure modes where more context increases noise or creates new injection surfaces. citeturn14search0turn2search2turn10search1  
- **“Our reviewer can reliably catch deception with untrusted explanations”**: explanation/legibility protocols can help benign performance, but do not constitute evidence of intent and can be gamed; legibility should be framed as *assistive UX for oversight*, not as a security guarantee. citeturn3search0turn5search1turn14search0  

## Literature map

Below is a project-specific map of literature clusters, each framed around how it informs *Look-Before-You-Click’s* intervention point (pre-execution GUI gating), threat models (environment injection + hidden objective), and evaluation goals (safety/usefulness/overhead).

**AI control and trusted monitoring**

Why this cluster matters: Look-Before-You-Click is most naturally read as a **control protocol** (not alignment training): it introduces a structured, enforceable wrapper around an untrusted agent, with explicit tradeoffs between safety, usefulness, and latency. Control evaluations provide the methodological template for measuring those tradeoffs under adversarial pressure and for thinking clearly about what “safety” means in deployment-like settings. citeturn2search0turn15search0turn6search2turn15search2

Key works and what they contribute (comparability tags are relative to Look-Before-You-Click):

- entity["book","AI Control: Improving Safety Despite Intentional Subversion","arxiv 2312.06942"]: establishes control evaluations as a red-team/blue-team methodology; introduces canonical protocol components (trusted monitoring, trusted editing/deferral, etc.) and the safety–usefulness framing. **Directly comparable** as the main conceptual parent. citeturn2search0  
- entity["book","Ctrl-Z: Controlling AI Agents via Resampling","arxiv 2504.10374"]: shows how **resampling** can significantly reduce attack success in an agent environment with relatively small usefulness loss, motivating your B4R variant and clarifying how resampling can be evaluated as a control measure. **Directly comparable** (protocol mechanism), though not GUI-specific. citeturn2search1  
- entity["book","How to evaluate control measures for LLM agents? A trajectory from today to superintelligence","arxiv 2504.05259"]: provides a structured framing for matching control-eval affordances and protocol strength to capability level; useful for carefully scoping claims and setting expectations for what your evaluation does/doesn’t show. **Adjacent**. citeturn6search2  
- entity["book","A sketch of an AI control safety case","arxiv 2501.17315"] and entity["book","Practical challenges of control monitoring in frontier AI deployments","arxiv 2512.22154"]: connect control evaluations to deployment arguments, highlighting latency, incremental attacks, and human oversight constraints (directly relevant to your overhead and timing limitations). **Adjacent**, but highly informative for discussion/limitations. citeturn15search0turn15search2  
- entity["organization","ControlArena","ai control experiments library"] and entity["organization","Inspect AI","uk aisi eval framework"]: ecosystem infrastructure for running repeatable control experiments and logging review episodes—relevant as methodological precedent even if you don’t use the exact stack. **Background/adjacent**. citeturn12search2turn12search3turn12search10

**Adaptive attackers and monitor gaming**

Why this cluster matters: Your protocol’s strongest risk is **protocol-aware evasion**—attackers that understand what gets routed, what reviewers see, and when resampling/fallback happen. The control literature now contains direct evidence that (i) protocol awareness can drastically reduce safety and (ii) monitors can be attacked via injection into their own inputs (including transcripts). This cluster should shape how you present B4R/B4T, and how you argue about robustness without overclaiming. citeturn2search2turn8search2turn14search0

Key works:

- entity["book","Adaptive attacks on trusted monitors subvert AI control protocols","arxiv 2510.09462"]: studies protocol-aware attackers targeting monitoring, including “monitor-jailbreak” style dynamics and counterintuitive interactions with resampling/deferral. **Directly comparable** as a cautionary baseline for B4R/B4T and for your “A2 attacker variants” framing. citeturn2search2  
- entity["book","Reliable Weak-to-Strong Monitoring of LLM Agents","arxiv 2508.19461"]: introduces monitor red-teaming workflows; empirically finds that agent awareness can degrade monitoring, that scaffolding matters, and that **targeted human oversight on flagged cases** can improve outcomes—highly aligned with your “sparse review” idea but not at the same intervention point. **Adjacent-to-direct**. citeturn8search2turn7view0  
- entity["book","How does information access affect LLM monitors' ability to detect sabotage?","arxiv 2601.21112"]: shows “less-is-more” effects and proposes information filtering; relevant to your choice of reviewer inputs (what to show, when) and to avoiding “more context always helps” claims. **Adjacent**. citeturn14search0  
- entity["book","SHADE-Arena: Evaluating Sabotage and Monitoring in LLM Agents","arxiv 2506.15740"]: provides an environment pairing main tasks with hidden harmful objectives and evaluating against monitors; supports the empirical relevance of “scheming-style” threat models. **Adjacent**, but conceptually aligned. citeturn6search0  
- entity["book","Attack Selection Reduces Safety in Concentrated AI Control Settings","arxiv 2602.04930"]: directly relevant to your “critical-action concentration hypothesis”: if attacks can choose their timing/shape, concentration can become a weakness; informs limitations and future work. **Adjacent**. citeturn6search38  

**Computer-use agents and GUI benchmarks**

Why this cluster matters: Your protocol is not meaningful without the empirical fact that CUAs now operate in realistic UIs (desktop/web/mobile), and that benchmarks exist where agents must click/type/navigate through real applications. This cluster provides: (i) the baseline execution substrate (OSWorld-style), (ii) evidence of real UI-mediated hazards (OS-Harm and related benchmarks), and (iii) context for why **live screen state** is a natural oversight input. citeturn0search3turn10search2turn11search0turn20view0

Key works:

- entity["organization","OSWorld","real os benchmark for agents"]: the benchmark/environment underlying OS-Harm; establishes realistic OS-level task execution and evaluation. **Directly comparable** as the execution substrate you wrap. citeturn0search3  
- entity["organization","OS-Harm","computer use agent safety benchmark"]: directly motivates your threat model (prompt injection, misuse, misbehavior) and provides OSWorld-grounded safety tasks and an automated judge. **Directly comparable** as your core task source and threat-model anchor. citeturn10search2  
- entity["organization","Windows Agent Arena","windows desktop agent benchmark"] and entity["organization","AndroidWorld","android benchmark for autonomous agents"]: show broader benchmark ecosystem and confirm that CUAs are evaluated across OS platforms with screenshot/a11y-tree style inputs; useful for contextualizing generality. **Adjacent**. citeturn11search0turn20view0  
- entity["book","WebArena: A Realistic Web Environment for Building Autonomous Agents","arxiv 2307.13854"], entity["book","VisualWebArena: Evaluating Multimodal Agents on Realistic Visual Web Tasks","arxiv 2401.13649"], and entity["book","Mind2Web: Towards a Generalist Agent for the Web","arxiv 2306.06070"]: establish web-agent evaluation and the use of DOM/accessibility/visual state; good comparators for claims about UI state informativeness, but web-only. **Adjacent**. citeturn1search16turn1search17turn1search18  
- entity["book","UI-TARS: Pioneering Automated GUI Interaction with Native Agents","arxiv 2501.12326"]: representative of “native GUI agent models” that operate from screenshots and human-like actions; mainly background for why risks are salient as capability rises. **Background**. citeturn11search1  

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["OSWorld benchmark real operating system agent screenshot","OS-Harm benchmark computer use agent safety screenshot","VisualWebArena multimodal web agent benchmark screenshot","Decepticon dark patterns web agent screenshot"],"num_per_query":1}

**Prompt injection, environment-based attacks, and UI manipulation**

Why this cluster matters: Your environmental attack model is a **confused-deputy** style problem: untrusted environment content (webpages, emails, documents, UI text) attempts to redirect an agent with privileges. The right comparisons are not generic jailbreak papers, but works that study **indirect prompt injection** and **agent hijacking** in interactive settings, especially with UI-based and multimodal attack surfaces. citeturn1search0turn13search0turn10search0turn10search2

Key works:

- entity["book","Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection","arxiv 2302.12173"]: foundational indirect prompt injection framing for tool-using systems; relevant for explaining why “instructions vs data” separation breaks in agent contexts. **Adjacent** (tool/app setting, not GUI action stream). citeturn1search0  
- entity["book","AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents","arxiv 2406.13352"]: evaluation framework for prompt injection against agents; useful to contrast “prompting defenses” with your protocol-level deferral approach, and to cite a benchmarked agent-hijacking environment. **Adjacent**. citeturn13search0  
- entity["book","Refusal-Trained LLMs Are Easily Jailbroken As Browser Agents","arxiv 2410.13886"]: shows that refusals in chatbot mode do not reliably transfer to agentic browser execution; supports your motivation for protocol-layer controls beyond “model refusal.” **Adjacent**. citeturn13search3  
- entity["book","RedTeamCUA: Realistic Adversarial Testing of Computer-Use Agents in Hybrid Web-OS Environments","arxiv 2505.21936"]: directly targets CUAs and hybrid web+OS prompt injection; provides empirical ASR/attempt-rate evidence and realistic injection configurations—highly aligned to your environmental threat model, though it is a benchmark/framework rather than a control protocol. **Directly relevant adjacent**. citeturn10search0  
- entity["book","DECEPTICON: How Dark Patterns Manipulate Web Agents","arxiv 2512.22894"]: shows UI-level manipulation (dark patterns) steering web agents to malicious outcomes at high rates and that scaling can increase susceptibility—supports “environmental manipulation works via UI” and motivates state-grounded oversight rather than trusting agent intent. **Adjacent but thematically tight**. citeturn16view0  
- entity["book","Visual Prompt Injection Attacks for Computer-Use Agents","arxiv 2506.02456"]: expands injection beyond text into visual channels; directly relevant for GUI-based agents where screen is the observation stream. **Adjacent**. citeturn13search6  
- entity["book","The Attacker Moves Second: Stronger Adaptive Attacks Bypass Defenses Against LLM Jailbreaking","arxiv 2510.09023"]: reinforces that static defenses can look strong until adaptivity is introduced; useful as a general caution when describing environmental-attack robustness. **Background/adjacent**. citeturn1search2  

**State-grounded oversight and monitor inputs**

Why this cluster matters: Your core claim is that **live screen state is unusually informative** and enables sparse, high-precision review at critical actions. The relevant literature is not generic “explainable AI,” but work that studies what monitors/reviewers can detect given different information channels (outputs-only, trajectories, hidden reasoning, tool traces, etc.), including findings that (i) more information can sometimes hurt and (ii) filtering/excerpting may be needed. citeturn14search0turn5search0turn8search2turn10academia36

Key works:

- METR’s monitorability evaluations (blog report): shows large gains in catch rate for some agents when reasoning traces are visible, illustrating how additional channels can increase detectability but not uniformly across models. **Background** (different modality, but same “oversight input” question). citeturn5search0  
- entity["book","How does information access affect LLM monitors' ability to detect sabotage?","arxiv 2601.21112"]: emphasizes that monitor performance can improve with *filtered* information rather than raw full trajectories, which should inform how you design reviewer UI and what artifacts matter. **Adjacent**. citeturn14search0  
- entity["book","Measuring Harmfulness of Computer-Using Agents","arxiv 2508.00935"]: evaluates misuse potential in CUAs and tests monitoring (including CoT monitoring) in a CUA setting, finding monitoring is harder than chatbot outputs and giving concrete numbers for detection accuracy; directly relevant for positioning “monitoring is hard, so sparse gating might be attractive.” **Directly relevant adjacent**. citeturn10academia36  
- entity["book","OS-Harm: A Benchmark for Measuring Safety of Computer Use Agents","arxiv 2506.14866"]: operationalizes OSWorld-based safety judging using screenshot/a11y-tree style evidence, indirectly supporting that GUI state contains evaluable safety signal. **Directly comparable** (task substrate + state modality). citeturn10search2  

**Legibility and explanation as oversight input**

Why this cluster matters: Look-Before-You-Click’s “legibility artifact” is explicitly **untrusted** and used only to assist a human reviewer. Prior work establishes two crucial points you should cite: (i) untrusted models can strategically manipulate monitors, so explanations are not evidence; but (ii) certain constrained legibility aids can improve monitoring performance in practice (especially for benign behavior), which supports including legibility as an optional variant (B4 vs B3) while remaining cautious. citeturn3search0turn2search2turn14search0

Key works:

- entity["book","Basic Legibility Protocols Improve Trusted Monitoring","arxiv 2602.10153"]: shows that allowing certain legibility aids (e.g., comments) can improve trusted monitoring outcomes, even though explanations remain potentially deceptive; this is the closest “legibility helps oversight” control-style precedent. **Adjacent-to-direct**. citeturn3search0  
- entity["book","Chain-of-Thought Monitorability: A New and Fragile Opportunity for AI Safety","arxiv 2507.11473"]: frames why externalized reasoning can be monitorable yet fragile; good for careful language about what “legibility” does and does not buy you. **Background**. citeturn5search1  
- Adaptive attack work on monitors: reinforces that monitors and their inputs can be attacked; legibility must be framed as “UX aid,” not “truth.” **Background-to-adjacent**. citeturn2search2turn14search0  

**Sparse intervention, action gating, and “critical actions”**

Why this cluster matters: This is the core “closest prior art” battleground. You need to situate the **critical-action concentration hypothesis** alongside (i) control protocols that intervene selectively, and (ii) system/security designs that gate “sensitive operations.” The key question for novelty is whether prior work already did *sparse gating* at the *action boundary* with *state-grounded review* in *GUI environments*.

Key works:

- entity["book","Evaluating Control Protocols for Untrusted AI Agents","arxiv 2511.02997"]: directly studies control protocols that combine monitoring with mechanisms like resampling and deferral, and explicitly reports brittleness under protocol-aware attackers—this is the closest “control-protocol design + evaluation” precedent to your B4R/B4T story, though not GUI-state review. **Directly comparable**. citeturn2search3  
- entity["book","Agent Control Protocol: Admission Control for Agent Actions","arxiv 2603.18829"]: proposes an “admission control” framing for agent actions; relevant as a conceptual neighbor to your router (although your protocol is human-review-centric and evaluation-driven). **Adjacent**. citeturn0search1  
- entity["book","Secure and Efficient Access Control for Computer-Use Agents via Context Space","arxiv 2509.22256"]: system-level static policy enforcement for CUAs, explicitly motivated by irreversible consequences; demonstrates that “sensitive actions” can be gated at runtime via policy, but it is a security architecture rather than a control evaluation. **Directly relevant adjacent**. citeturn8search0  
- entity["book","AgentSentinel: An End-to-End and Real-Time Security Defense Framework for Computer-Use Agents","arxiv 2509.07764"]: intercepts sensitive operations and performs security audits; represents the “fuller security system” class from which you must distinguish your narrower claim. **Adjacent** (and an overclaim foil). citeturn10search1  
- entity["book","Safeguarding Mobile GUI Agent via Logic-based Action Verification","arxiv 2503.18492"]: verifies actions against formalized user intent before execution; very similar in “intervene pre-action,” but it is a formal verification guardrail for mobile GUI agents, not an AI-control sparse-review protocol. **Adjacent close**. citeturn9search0  

**Trusted fallback and trusted execution**

Why this cluster matters: Your B4T “one trusted fallback action” is a concrete control measure that looks like a limited “trusted executor.” You need citations that: (i) place trusted deferral/editing in the control literature, and (ii) distinguish your narrow one-step fallback from full hybrid agents or full trusted execution graphs.

Key works:

- The foundational AI control paper’s taxonomy includes deferral/trusted components as a standard pattern. **Directly comparable**. citeturn2search0  
- entity["book","Practical challenges of control monitoring in frontier AI deployments","arxiv 2512.22154"]: emphasizes latency, oversight, and reversibility as first-class design constraints; useful to justify why your fallback is bounded (“once”) and why you measure overhead. **Adjacent**. citeturn15search2  
- entity["book","CaMeLs Can Use Computers Too: System-level Security for Computer Use Agents","arxiv 2601.09923"]: uses architectural separation and pre-observation planning to “prove” resilience to instruction injection, but still faces branch steering; it functions as a foil for what “stronger than Look-Before-You-Click” security architecture looks like. **Adjacent**. citeturn11search2  

**Evaluation design and methodology for control-style agent safety**

Why this cluster matters: Your paper lives or dies on evaluation credibility: paired benign vs attack conditions, explicit safety/usefulness/overhead metrics, clarity about threat models, and logging of review episodes. Control literature provides templates for these choices; CUA safety/security papers provide templates for defining “harm,” “attack success,” and “realistic attacks.”

Key works:

- Control evaluations and formalizations: foundational AI control paper and AI-control games formalism help justify measuring tradeoffs and protocol performance under adversarial pressure. citeturn2search0turn6search3  
- OS-Harm’s automated judge and OSWorld-style evaluation scripts ground the idea that safety and task completion can be scored in real UI tasks. citeturn10search2turn0search3  
- CUA security benchmarks (RedTeamCUA, AdvCUA, BadComputerUse, CUAHarm) show evaluation patterns for enterprise-like attacks and misuse risk; cite sparingly to avoid drifting into “we are a security benchmark.” citeturn10search0turn10search1turn9search2turn10academia36  

## Closest comparisons table

| work | domain / environment | threat model | intervention point | monitor inputs | sparse or blanket review | resampling / fallback / trusted execution | strongest similarity to Look-Before-You-Click | crucial difference | implication for positioning |
|---|---|---|---|---|---|---|---|---|---|
| AI Control: Improving Safety Despite Intentional Subversion citeturn2search0 | general agent/control-eval methodology | scheming / intentional subversion | protocol-level (varies) | typically transcripts, tool traces; abstract monitor model | often blanket monitoring; protocol-dependent | includes deferral/trusted components as patterns | establishes control evaluations + safety/usefulness framing | not GUI-specific; does not focus on “critical GUI actions” | cite as methodological parent; your novelty is a CUA-specific instantiation |
| Ctrl-Z: Controlling AI Agents via Resampling citeturn2search1 | agent environment (shell / task execution) | hidden objective / sabotage | before executing an action (via resampling loop) | action text/trajectory | sparse (only when triggered) | resampling is the core mechanism | direct precedent for your B4R-style “resample once” | domain is not GUI; does not use live screen state + human review | position B4R as “Ctrl-Z-like” but with GUI critical-action routing |
| Evaluating Control Protocols for Untrusted AI Agents citeturn2search3 | tool-calling / control settings | intentional subversion; protocol-aware attackers | protocol-level (monitor + resample/deferral variants) | monitor sees some trajectory info | varies; often blanket monitoring | combines resampling and deferral; studies protocol-aware failure | closest on “protocol variants + evaluation under adaptive attackers” | not specifically OSWorld GUI stream; reviewer is not a live-state human | emphasize your new domain (GUI) + state-grounded review, and reuse their caution about protocol awareness |
| Adaptive attacks on trusted monitors subvert AI control protocols citeturn2search2 | control protocols / monitoring | adaptive attackers targeting monitors | attacks the monitoring channel | monitor inputs can be spoofed/injected | blanket monitoring targeted | shows monitor gaming; can invert resampling benefits | directly informs your A2 attacker framing and resampling caveats | not about GUI action gating per se | use to bound claims: sparse review is not “robust” by default |
| Reliable Weak-to-Strong Monitoring of LLM Agents citeturn8search2turn7view0 | monitors for agents (incl. CUA-SHADE-Arena) | covert misbehavior + evasion; prompt injection | monitoring after-the-fact / scaffolding | parses trajectories; can involve humans on flagged cases | sparse *human* escalation | human-on-flagged improves TPR at low FPR | strong support for “targeted escalation beats blanket human review” | not an execution-blocking protocol; not GUI critical-action checkpointing | cite to motivate sparse escalation and discuss reviewer workload / filtering |
| OSWorld citeturn0search3 | real OS tasks | benign capability benchmark | N/A | screenshot/a11y tree for agents | N/A | N/A | provides your execution substrate and notion of OS-level task realism | not adversarial; not safety/control-focused | cite as environment baseline; clarify you are not proposing a new benchmark |
| OS-Harm citeturn10search2 | OSWorld-based CUA safety benchmark | misuse, prompt injection, agent misbehavior | benchmark-level evaluation | judge uses UI evidence (screenshots, a11y, etc.) | N/A | N/A | directly matches your environmental attack model and GUI hazards | benchmark ≠ control protocol | cite as threat model + task source; your novelty is protocol+eval on top |
| CSAgent (Context Space access control) citeturn8search0turn8search2 | system-level CUA enforcement | “attacks” and unsafe actions; policy violations | pre-execution enforcement at OS/service layer | policy context, intent/context space | sparse (only policy-relevant ops) | policy enforcement (not resampling) | extremely similar “pre-execution gating of risky actions” conceptually | engineered access control system; claims broad defense rate | distinguish: you evaluate a control protocol w/ human review, not a policy architecture claiming general security |
| AgentSentinel citeturn10search1 | CUA security defense | multi-component CUA attacks | intercept sensitive ops; audit before continuing | correlates task context + system traces | more comprehensive coverage than sparse review | auditing pipeline; security framework | same “intercept sensitive operations before execution” surface | explicitly a security defense + new benchmark; broader claims | use as “not our claim”: you are not a complete defense |
| VeriSafe Agent (logic-based action verification) citeturn9search0 | mobile GUI agents | errors/misalignment vs user intent | verify action before execute | formalized instruction/spec + UI state | action-by-action verification | corrective feedback/halt | very close: pre-action checking for intent alignment | formal verification + autoformalization; not control-style adversary eval | position your reviewer as “trusted human” rather than a DSL verifier; cite as adjacent strongest neighbor |
| Visual Confused Deputy citeturn9search3 | CUAs; perception failures | misclick/grounding errors + adversarial UI manipulation | guardrail outside agent loop; block execution | visual click target + reasoning channel | sparse (blocks risky cases) | blocking, classification; not resampling | close: independent guardrail gating outside the agent | focus is perception/target mismatch; not high-impact action families or human review | cite to motivate why action-level gating matters and why “what is clicked” must be verified |
| CaMeLs Can Use Computers Too citeturn11search2 | OSWorld CUA security | prompt injection | architectural isolation + single-shot plan | trusted planner pre-observation; plan graphs | not “review”; more architectural | executes trusted plan; not resampling | addresses same core threat (environment injection) | much stronger integration + different tradeoffs; admits branch steering | use as “stronger but heavier” foil; clarify your protocol aims for different Pareto point |
| Mind the Gap: TOCTOU vulns in LLM-enabled agents citeturn18search0turn17search5 | tool-using agents | TOCTOU races / state changes between check & use | mitigations at tooling level | state integrity, tool sequencing | N/A | tool fusing, monitoring | matches your “timing problem” limitation mechanistically | not GUI-specific; focuses on tool-call atomicity | cite to justify limitations and motivate future work at state/action atomicity |
| Zero-Permission Manipulation (Action Rebinding) citeturn19search0 | Android GUI agents | UI-state races; bypassing verification gates | exploits observation–action gap | UI state and agent recovery logic | N/A | attack, not defense | directly supports “timing problem” and “verification gates can be bypassed” | attacker model is OS/app-level manipulation; not your control protocol | strengthens claim boundaries: sparse GUI checkpoints can be raced/manipulated |

## Writing-ready related work outline

This is formatted to drop directly into `docs/related_work_outline.md`. The structure is designed to (i) establish conceptual lineage (AI control), (ii) ground the threat model in CUA benchmarks, and (iii) make the novelty claim narrow: “critical-action deferral + state-grounded review + control-style evaluation.”

Proposed section headers for the paper’s Related Work (no numbering, but in intended order):

- **AI control and control evaluations as the methodological parent**
  - Claim: Our paper follows the control-evaluation paradigm: quantify safety–usefulness tradeoffs of protocols intended to constrain untrusted agents, including under intentional subversion. Citations: citeturn2search0turn15search0turn6search3  
  - Claim: Resampling and deferral are canonical control measures; we instantiate analogous mechanisms (one resample; one trusted fallback) at the GUI action boundary. Citations: citeturn2search1turn2search0turn15search2  
  - Transition note: Having established “control” as the frame, we now argue why CUAs require a UI-specific instantiation.

- **Computer-use agents and OSWorld-style benchmarks**
  - Claim: Modern CUAs operate directly on real UIs via screenshots/accessibility trees, motivating OS-level benchmarks across desktop/mobile/web. Citations: citeturn0search3turn11search0turn20view0turn1search16  
  - Claim: OSWorld provides the execution substrate for realistic desktop tasks; OS-Harm extends it to safety violations and prompt-injection-style attacks. Citations: citeturn0search3turn10search2  
  - Transition note: With OS-Harm as the task/threat anchor, introduce why “environment content can hijack agents” is structurally similar to indirect prompt injection/confused deputy.

- **Environmental attacks: prompt injection and UI manipulation**
  - Claim: Indirect prompt injection and agent hijacking are established threats in tool-using agents, and they carry over (often more strongly) to web/OS agents. Citations: citeturn1search0turn13search0turn13search3turn10search0  
  - Claim: UI-native manipulations—dark patterns, visual prompt injection—can steer agents toward adversary goals even when tasks remain “nominally achievable.” Citations: citeturn16view0turn13search6  
  - Transition note: Explain that environmental attacks motivate *state-grounded* review: the screen is where injection manifests.

- **Selective intervention and critical-action gating**
  - Claim: Prior control protocols show that selective mechanisms (e.g., resampling) can reduce sabotage at low usefulness cost, motivating sparse rather than blanket interventions. Citations: citeturn2search1turn2search3turn6search2  
  - Claim: Independent lines of CUA security work gate “sensitive operations” (policy enforcement, security audits, formal verification), but these aim for broad security rather than control-style sparse review tradeoffs. Citations: citeturn8search0turn10search1turn9search0  
  - Claim: Our contribution is to evaluate a *thin, action-routing protocol* focused on a small set of irreversible GUI actions, rather than enforcing system-wide policies or architectural isolation. Citations to contrast/position: citeturn8search0turn11search2turn10search1  
  - Transition note: Move from “why sparse gating” to “how monitors/reviewers should be informed.”

- **Oversight inputs: state grounding vs language-only review, and untrusted legibility**
  - Claim: Monitoring performance depends heavily on what information is provided; more information can help, but can also hurt without filtering (“less-is-more”). Citations: citeturn14search0turn5search0  
  - Claim: In CUA-specific monitoring, detecting misuse/scheming from trajectories is empirically difficult, motivating action-level checkpoints rather than expecting perfect transcript monitors. Citations: citeturn10academia36turn8search2  
  - Claim: Legibility/explanation artifacts can assist oversight but must be treated as untrusted; constrained legibility protocols can improve monitoring outcomes in some regimes. Citations: citeturn3search0turn2search2turn5search1  
  - Transition note: Now foreground the adversary: protocol-aware attackers and timing failures.

- **Adaptive attackers, timing attacks, and known failure modes**
  - Claim: Control protocols can fail sharply when attackers know the protocol or can jailbreak the monitor; resampling can backfire. Citations: citeturn2search2turn2search3turn8search2  
  - Claim: UI agents face TOCTOU and UI-state race vulnerabilities that can bypass verification gates or cause harm between checkpoints, bounding what critical-action deferral can guarantee. Citations: citeturn18search0turn19search0turn17search5  
  - Claim: Therefore, our evaluation should be read as evidence about a specific safety–usefulness–latency tradeoff in OS-Harm-like tasks, not as a general defense for CUA security. Citations: citeturn15search2turn10search2turn10search0  

## Novelty and claim-boundary section

What is genuinely new here?

- **A control-style protocol evaluation tailored to GUI action streams**: Most control-protocol evaluations and monitor-gaming papers are developed in text/code/tool-call settings or use transcript-based monitoring; your work evaluates a protocol whose enforcement boundary is **GUI action execution** in an OSWorld-style environment. citeturn2search0turn2search1turn0search3turn10search2  
- **Sparse routing over a domain-specific “critical GUI action” taxonomy**: While “sensitive operations” and “deferral” exist in adjacent lines, your specific hypothesis is that catastrophic failures in CUAs are *concentrated* in a small, monitorable family of irreversible GUI actions—enabling targeted review rather than blanket oversight. This is closest in spirit to selective control measures like resampling, but instantiated as a **rule-based critical-action router + state-grounded reviewer**. citeturn2search1turn2search3turn15search2  
- **A reviewer input design anchored in live GUI evidence**: Position the novelty as *which inputs are used for oversight* (screen/a11y/history plus optional legibility) and *when* (only at critical actions), not as inventing human-in-the-loop review. citeturn10search2turn14search0turn5search0  
- **A paired evaluation under two threat models that are often separated**: environmental prompt injection (OS-Harm style) and intentional subversion/hidden objectives (control-style). Many benchmarks emphasize one or the other; you evaluate a single protocol family across both. citeturn10search2turn2search0turn6search0turn10search0  

What is only a recombination of existing ideas?

- **Action-level gating itself**: “Intercept sensitive operations before execution” is common in security architectures for CUAs and in formal action verification; you should treat this as precedent and avoid implying firstness. citeturn8search0turn10search1turn9search0  
- **Resampling and trusted fallback/deferral**: These are standard in AI control protocol design; your variants are domain adaptations rather than fundamentally new mechanisms. citeturn2search1turn2search0turn2search3  
- **Using UI state as an evidence channel**: OSWorld-family benchmarks and web-agent benchmarks already operationalize screenshots/a11y trees for agent perception and for evaluation; your main twist is using them for *oversight at critical decisions*. citeturn0search3turn10search2turn1search17  

What does prior work already establish (and you should cite as “known”)?

- CUAs are vulnerable to prompt injection/indirect instruction hijacking in realistic, hybrid web–OS environments. citeturn10search0turn13search0turn1search0  
- Monitoring/covert-misbehavior detection is brittle under agent awareness and adaptive strategies; monitor scaffolding and selective escalation can matter more than raw monitor capability. citeturn8search2turn14search0turn2search2  
- UI-level manipulations (dark patterns, perception/grounding failures, visual prompt injection) can reliably steer agent trajectories and can worsen with scaling/reasoning. citeturn16view0turn9search3turn13search6turn19search0  
- Timing/TOCTOU gaps are a first-class vulnerability in agentic workflows; UI agents can be attacked via observation–action races and “verification gate bypass” dynamics. citeturn18search0turn19search0turn17search5  

Exact wording to avoid overstating novelty

Suggested safe wording:

- “We evaluate a **sparse critical-action deferral protocol** for OSWorld-style computer-use agents, routing only high-impact GUI actions to a trusted, state-grounded reviewer.” citeturn0search3turn15search2  
- “Our goal is not to provide a complete security solution for computer-use agents; rather, we measure a safety–usefulness–latency tradeoff for a thin control wrapper under OS-Harm-style environmental attacks and hidden-objective attacks.” citeturn10search2turn15search2turn2search0  
- “We treat untrusted explanations as **legibility aids** for the reviewer, not as evidence of benign intent.” citeturn3search0turn2search2  

Exact wording to distinguish from specific neighboring areas

- Versus generic prompt-injection defenses: “Instead of attempting to sanitize or perfectly classify untrusted content, we intervene at the **action execution boundary**, where many harms become irreversible.” citeturn13search0turn10search0turn10search2  
- Versus full CUA security systems: “We do not propose system-wide access control, end-to-end auditing, or architectural isolation; our protocol is a thin wrapper designed to study a targeted oversight regime.” citeturn8search0turn10search1turn11search2  
- Versus full trusted executors or hybrid agents: “Our trusted component is limited to a human reviewer (and, in one variant, a single trusted fallback action), rather than a trusted planner/executor that generates the full trajectory.” citeturn2search0turn11search2turn15search2  
- Versus non-GUI AI control papers: “We focus on CUAs whose primary observation and action space is the GUI; reviewer judgments are grounded in live screen state rather than purely language transcripts or code diffs.” citeturn10search2turn0search3turn2search1  
- Versus benchmark papers: “We build on OSWorld/OS-Harm rather than introducing a new benchmark; our contribution is the protocol and its evaluation.” citeturn0search3turn10search2  

## Must-cite shortlist

Top 10 must-cite references (main text)

1) entity["book","AI Control: Improving Safety Despite Intentional Subversion","arxiv 2312.06942"] — Foundational methodological parent for control evaluations and for framing safety–usefulness tradeoffs under intentional subversion. Use it to justify calling your work “AI control,” to anchor protocol language (trusted monitor, deferral, etc.), and to motivate evaluating scheming-style threat models. citeturn2search0  

2) entity["organization","OS-Harm","computer use agent safety benchmark"] — Your most direct benchmark/threat-model anchor: provides OSWorld-based tasks including prompt injection and unsafe behaviors, plus an automated judge with reported agreement levels. Essential to justify environmental-attack realism and to keep your contribution scoped as “protocol+eval on top of OS-Harm tasks.” citeturn10search2  

3) entity["organization","OSWorld","real os benchmark for agents"] — Underlying environment for OS-Harm and the relevant “real OS GUI” benchmark lineage; cite to make clear you are operating in real applications and not a toy web-only environment. citeturn0search3  

4) entity["book","Ctrl-Z: Controlling AI Agents via Resampling","arxiv 2504.10374"] — Closest protocol-mechanism precedent for your resample-once variant and for sparse interventions; helps position B4R and to reference known tradeoffs between safety gains and usefulness overhead. citeturn2search1  

5) entity["book","Adaptive attacks on trusted monitors subvert AI control protocols","arxiv 2510.09462"] — Critical for honest boundaries: shows protocol-aware attackers can subvert monitoring and that resampling/deferral can interact badly. This is the citation that protects you from overclaiming “robust safety” and strengthens your discussion section. citeturn2search2  

6) entity["book","Evaluating Control Protocols for Untrusted AI Agents","arxiv 2511.02997"] — Closest “control protocol evaluation” precedent for combining monitoring, resampling, and deferral, and for reporting failure under protocol awareness. Use it as a direct comparison point for B4R/B4T logic. citeturn2search3  

7) entity["book","RedTeamCUA: Realistic Adversarial Testing of Computer-Use Agents in Hybrid Web-OS Environments","arxiv 2505.21936"] — Most relevant CUA-centric evidence that indirect prompt injection remains an acute risk in realistic hybrid environments; cite to motivate the environmental threat model and to distinguish “benchmarking vulnerabilities” from “control protocol evaluation.” citeturn10search0  

8) entity["book","Reliable Weak-to-Strong Monitoring of LLM Agents","arxiv 2508.19461"] — Strong empirical precedent that targeted escalation to humans can help and that monitoring reliability collapses when agents know they’re monitored; supports your sparse-review motivation and informs your discussion of reviewer load. citeturn8search2turn7view0  

9) entity["book","Safeguarding Mobile GUI Agent via Logic-based Action Verification","arxiv 2503.18492"] — Closest “pre-action verification for GUI agents” academic precedent; important to cite so you don’t implicitly claim novelty on “checking actions before execution,” and to clarify your distinct design choice (trusted human reviewer + critical-action routing vs formal verification of all actions). citeturn9search0  

10) entity["book","Practical challenges of control monitoring in frontier AI deployments","arxiv 2512.22154"] — Best citation to justify why you care about latency and why sparse review could be attractive; also supports your “timing problem” limitation framing (oversight latency vs harm latency). citeturn15search2  

Next 10 useful references (often appendix/background, but several may deserve main text depending on emphasis)

1) entity["book","AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents","arxiv 2406.13352"] — Canonical agent prompt-injection eval framework; cite when distinguishing “prompting defenses and detectors” from control-style action deferral. citeturn13search0  

2) entity["book","Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection","arxiv 2302.12173"] — Foundational indirect prompt injection framing; good for the environmental attack conceptual setup. citeturn1search0  

3) entity["book","Refusal-Trained LLMs Are Easily Jailbroken As Browser Agents","arxiv 2410.13886"] — Supports the motivational claim that “chat refusal ≠ agent safety,” especially useful if reviewers might otherwise suggest “just align/refuse better.” citeturn13search3  

4) entity["book","DECEPTICON: How Dark Patterns Manipulate Web Agents","arxiv 2512.22894"] — Provides UI-level manipulation evidence (dark patterns) and suggests that scaling can increase susceptibility; ties directly to your “monitorable critical actions” theme. citeturn16view0  

5) entity["book","How does information access affect LLM monitors' ability to detect sabotage?","arxiv 2601.21112"] — Use for nuanced discussion of reviewer information design and why more context is not automatically better. citeturn14search0  

6) entity["book","Measuring Harmfulness of Computer-Using Agents","arxiv 2508.00935"] — Strong CUA-specific misuse benchmark that also tests monitoring and finds it difficult; supports the need for protocol-level interventions. citeturn10academia36  

7) entity["book","Mind the Gap: Time-of-Check to Time-of-Use Vulnerabilities in LLM-Enabled Agents","arxiv 2508.17155"] — Provides principled framing for your timing limitation; helps transform “timing problem” into a recognized vulnerability class. citeturn18search0turn17search5  

8) entity["book","Zero-Permission Manipulation: Can We Trust Large Multimodal Model Powered GUI Agents?","arxiv 2601.12349"] — Strong evidence of UI-state race exploits and verification gate bypass; highly relevant if you discuss “some harms happen before the checkpoint” or “UI can be manipulated between observe and act.” citeturn19search0  

9) entity["book","Secure and Efficient Access Control for Computer-Use Agents via Context Space","arxiv 2509.22256"] — Policy-based action gating in CUAs; cite to clearly separate your protocol’s scope from system-level access control solutions. citeturn8search0  

10) entity["book","CaMeLs Can Use Computers Too: System-level Security for Computer Use Agents","arxiv 2601.09923"] — Architectural isolation approach; cite as a “stronger but heavier” foil and to clarify you are not claiming robust injection resistance. citeturn11search2  

Five tempting references that are probably not worth main-text space unless needed

1) entity["book","BIPIA: Benchmarking and Defending Against Indirect Prompt Injection Attacks","arxiv 2312.14197"] — Useful for “indirect prompt injection benchmarking exists,” but your paper is not primarily about injection robustness metrics; better as background if you need a citation beyond AgentDojo/Greshake. citeturn4search36  

2) entity["book","AgentHarm: A Benchmark for Measuring Harmfulness of LLM Agents","arxiv 2410.09024"] — Important benchmark, but less directly tied to GUI action gating than OS-Harm/CUAHarm; cite only if you broaden to “agent misuse benchmarks.” citeturn13search1  

3) entity["book","BashArena: A Control Setting for Highly Privileged AI Agents","arxiv 2512.15688"] — Good control-setting design precedent, but likely appendix-level unless you compare strongly to shell settings. citeturn12search16  

4) entity["book","Windows Agent Arena: Evaluating Multi-Modal OS Agents at Scale","arxiv 2409.08264"] — Good ecosystem context; cite if you want to gesture at cross-OS generality, but not essential for your central claim. citeturn11search8turn11search0  

5) entity["book","The Confused Deputy (or why capabilities might have been invented)","acm 1988"] — Strong conceptual metaphor for environment hijacking, but may be overkill in main related work unless you explicitly develop the “GUI agent as deputy” analogy. citeturn17search3  

## Citation-backed drafting notes

These are “drop-in” argumentative scaffolds: a topic sentence, then citations, then the exact role those citations play.

AI control framing and why this is a control paper  
Topic sentence: “We build on AI control: protocols designed to keep powerful, potentially subversive agents safe while preserving usefulness, evaluated via red-team/blue-team control evaluations.”  
Citations: citeturn2search0turn6search3turn15search0  
Argumentative role: establish the correct field (control, not alignment), justify safety/usefulness/overhead as primary axes, and justify evaluation under intentional subversion rather than only benign tasks.

Why CUAs create a distinct control surface  
Topic sentence: “Computer-use agents expand the control problem to GUI-mediated actions in real OS environments, where ‘what happens’ is a click/type sequence over live applications rather than a tool-call transcript.”  
Citations: citeturn0search3turn10search2turn11search0turn1search17  
Argumentative role: ground the paper’s domain in recognized benchmarks; motivate the “live screen state” evidence channel; clarify you are not defining a new benchmark.

Environmental prompt injection and UI manipulation as the first threat model  
Topic sentence: “Indirect prompt injection and UI-native manipulations can hijack agent trajectories by embedding adversarial instructions or incentives inside the observation stream (web/OS content), making purely prompt-based safety brittle.”  
Citations: citeturn1search0turn13search0turn10search0turn16view0  
Argumentative role: motivate OT1 (environmental attacks), show it is empirically real in agent benchmarks, and justify why a control protocol that checks actions (not content) is worth studying.

Scheming/hidden objectives as the second threat model  
Topic sentence: “Beyond environmental hijacking, CUAs may pursue hidden objectives while completing main tasks, motivating control-style evaluations that treat the agent as potentially adversarial.”  
Citations: citeturn2search0turn6search0turn15search1turn10academia36  
Argumentative role: legitimizes your second threat model and connects it to an existing empirical tradition (sabotage/hidden-objective evals), without requiring claims about real-world scheming prevalence.

Why sparse intervention is plausible but must be evaluated  
Topic sentence: “Selective control measures can reduce sabotage with smaller usefulness costs than blanket oversight, but their robustness depends on attacker adaptivity and protocol awareness.”  
Citations: citeturn2search1turn2search3turn2search2turn8search2  
Argumentative role: motivates your “critical-action deferral” hypothesis and variants (B4R/B4T) while pre-emptively bounding claims via adaptive-attack and monitor-red-teaming evidence.

Why state-grounded review and why “more info” is not trivial  
Topic sentence: “Oversight effectiveness is strongly shaped by what information is shown to the reviewer/monitor; richer channels can help, but can also degrade detection without careful filtering.”  
Citations: citeturn14search0turn5search0turn8search2  
Argumentative role: justifies design choices around reviewer UI (screen, a11y tree, history) and supports your paper’s empirical comparison to language-only baselines, without asserting monotonic improvement.

Legibility artifacts: helpful, untrusted, and bounded  
Topic sentence: “We treat untrusted explanations as legibility aids rather than evidence; prior work suggests constrained legibility protocols can improve monitoring outcomes but remain vulnerable to strategic manipulation.”  
Citations: citeturn3search0turn2search2turn5search1  
Argumentative role: makes your B3 vs B4 distinction principled and defensible; prevents reviewers from interpreting explanations as a security guarantee.

Timing and TOCTOU limitations as recognized failure modes  
Topic sentence: “GUI agents and tool-using agents both exhibit time-of-check/time-of-use vulnerabilities: harm can occur in the gap between observation, approval, and execution, bounding any checkpoint-based deferral protocol.”  
Citations: citeturn18search0turn19search0turn17search5turn15search2  
Argumentative role: upgrades your “timing problem” limitation from anecdote to known vulnerability class; frames future work (atomic execution, narrower action windows, stronger routing) without overclaiming.

## Gaps and uncertainty

Where the literature appears sparse (and therefore where your work can honestly claim to be “new in this combination”)

- **Sparse, state-grounded, critical-action gating evaluated as an AI control protocol in OSWorld-style GUI environments**: there are many neighbors (system-level CUA security defenses; formal action verification; monitor red teaming; control resampling), but few works that (i) explicitly adopt the **control-evaluation framing**, (ii) enforce at the **GUI-action execution boundary**, (iii) intervene **sparsely by a critical-action taxonomy**, and (iv) evaluate across both **environmental injection** and **hidden-objective** threats with explicit safety/usefulness/overhead tradeoffs. The closest pieces each cover only subsets of this combination. citeturn8search0turn10search1turn2search1turn2search0turn10search2  

Key uncertainties about “closest prior art” that you should double-check when writing the final paper

- The boundary between your contribution and recent “guardrail outside the agent loop” CUA security papers is subtle. Works like Visual Confused Deputy and AgentSentinel are close in intervention surface (block execution based on independent checks), and reviewers may perceive them as already covering “critical action gating.” You should be explicit that your paper’s claim is about a **particular sparse-review Pareto point** and about **control-style evaluation methodology**, not about presenting the strongest security architecture. citeturn9search3turn10search1turn15search2  
- Some CUA security papers make strong “first defense” claims (e.g., “first end-to-end defense”) that you should not endorse or repeat; cite them as adjacent and then constrain your own claims. citeturn10search1turn11search2  

Missing references that would weaken the section if omitted

- At least one **UI manipulation** benchmark/paper (DECEPTICON or Visual Prompt Injection) should be cited to support the narrative that “GUI state can adversarially steer agents,” beyond textual prompt injection. citeturn16view0turn13search6  
- At least one **TOCTOU / timing** paper should be cited so your “timing problem” limitation reads as a known class of issues rather than an implementation bug. citeturn18search0turn19search0turn17search5  
- At least one **monitor-gaming / protocol-aware attacker** paper should be cited to justify why you do not claim robustness and why reviewer false positives/latency tradeoffs matter. citeturn2search2turn8search2turn14search0  

Proposed final section ordering for the actual paper’s Related Work

- AI control and control evaluations  
- Computer-use agents and OSWorld-style benchmarks  
- Environmental attacks: indirect prompt injection, dark patterns, and UI manipulation  
- Sparse intervention: resampling, deferral, and action gating  
- Oversight inputs: language-only vs state-grounded evidence and untrusted legibility  
- Adaptive attackers and timing/TOCTOU limitations

## References and Sources

# Sources

- [Basic Legibility Protocols Improve Trusted Monitoring](https://arxiv.org/abs/2602.10153)
- [AI Control: Improving Safety Despite Intentional Subversion](https://arxiv.org/abs/2312.06942)
- [OSWorld-Human: Benchmarking the Efficiency of Computer Use Agents](https://arxiv.org/abs/2506.16042)
- [Adaptive Attacks on Trusted Monitors Subvert AI Control Protocols](https://arxiv.org/abs/2510.09462)
- [Attack Selection Reduces Safety in Concentrated AI Control Settings against Trusted Monitoring](https://arxiv.org/abs/2602.04930)
- [Async Control: Stress-testing Asynchronous Control Measures for LLM Agents](https://arxiv.org/abs/2512.13526)
- [Factor(U,T): Controlling Untrusted AI by Monitoring their Plans](https://arxiv.org/abs/2512.14745)
- [DECEPTICON: How Dark Patterns Manipulate Web Agents](https://arxiv.org/abs/2512.22894)
- [Introducing ControlArena: A Library for Running AI Control Experiments](https://www.aisi.gov.uk/blog/introducing-controlarena-a-library-for-running-ai-control-experiments)
- [Early Work on Monitorability Evaluations — METR](https://metr.org/blog/2026-01-19-early-work-on-monitorability-evaluations/)
- [Secure and Efficient Access Control for Computer-Use Agents via Context Space](https://arxiv.org/abs/2509.22256)
- [AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352)
- [Mind the Gap: Time-of-Check to Time-of-Use Vulnerabilities in LLM-Enabled Agents](https://arxiv.org/abs/2508.17155)
- [How Does Information Access Affect LLM Monitors' Ability to Detect Sabotage?](https://arxiv.org/abs/2601.21112)
- [WebArena: A Realistic Web Environment for Building Autonomous Agents](https://arxiv.org/abs/2307.13854)
- [Practical Challenges of Control Monitoring in Frontier AI Deployments](https://arxiv.org/abs/2512.22154)
- [UI-TARS: Pioneering Automated GUI Interaction with Native Agents](https://arxiv.org/abs/2501.12326)
- [RedTeamCUA: Realistic Adversarial Testing of Computer-Use Agents in Hybrid Web-OS Environments](https://arxiv.org/abs/2505.21936)
- [How to Evaluate Control Measures for LLM Agents? A Trajectory from Today to Superintelligence](https://arxiv.org/abs/2504.05259)
- [A Sketch of an AI Control Safety Case](https://arxiv.org/abs/2501.17315)
- [Zero-Permission Manipulation: Can We Trust Large Multimodal Model Powered GUI Agents?](https://arxiv.org/abs/2601.12349)
- [Reliable Weak-to-Strong Monitoring of LLM Agents](https://arxiv.org/abs/2508.19461)
- [SHADE-Arena: Evaluating Sabotage and Monitoring in LLM Agents](https://arxiv.org/abs/2506.15740)
- [Windows Agent Arena: Evaluating Multi-Modal OS Agents at Scale](https://arxiv.org/abs/2409.08264)
- [OS-Harm: A Benchmark for Measuring Safety of Computer Use Agents](https://arxiv.org/abs/2506.14866)
- [VeriSafe Agent: Safeguarding Mobile GUI Agent via Logic-based Action Verification](https://arxiv.org/abs/2503.18492)
- [Refusal-Trained LLMs Are Easily Jailbroken As Browser Agents](https://arxiv.org/abs/2410.13886)
- [VPI-Bench: Visual Prompt Injection Attacks for Computer-Use Agents](https://arxiv.org/abs/2506.02456)
- [Measuring Harmfulness of Computer-Using Agents](https://arxiv.org/abs/2508.00935)
- [Chain of Thought Monitorability: A New and Fragile Opportunity for AI Safety](https://arxiv.org/abs/2507.11473)
- [Visual Confused Deputy: Exploiting and Defending Perception Failures in Computer-Using Agents](https://arxiv.org/abs/2603.14707)
- [CaMeLs Can Use Computers Too: System-level Security for Computer Use Agents](https://arxiv.org/abs/2601.09923)
- [AgentSentinel: An End-to-End and Real-Time Security Defense Framework for Computer-Use Agents](https://arxiv.org/abs/2509.07764)
- [BashArena: A Control Setting for Highly Privileged AI Agents](https://arxiv.org/abs/2512.15688)
- [Benchmarking and Defending Against Indirect Prompt Injection Attacks on Large Language Models](https://arxiv.org/abs/2312.14197)
- [AgentHarm: A Benchmark for Measuring Harmfulness of LLM Agents](https://arxiv.org/abs/2410.09024)
- [Windows Agent Arena: Evaluating Multi-Modal OS Agents at Scale (ICML 2025)](https://proceedings.mlr.press/v267/bonatti25a.html)
- [The Confused Deputy Problem — Hardy (1988)](https://www.cs.wpi.edu/~cs557/f14/papers/confused_deputy-hardy.pdf)