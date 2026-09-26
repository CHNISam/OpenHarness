# Repository Agent Harness Mechanism

**Status:** Frozen Contract v1.0

---

# 1. Purpose

将目标 Repository 编译成一个可靠的 **Agent-first execution environment**。

本 Harness 交付的不是：

```text
Prompt
流程建议
Agent 工作说明
文档约定
```

而是：

> **一组在声明的 Execution / Trust Envelope 内真实成立、可执行、可验证、可恢复、可重新验证的 Repository Guarantees。**

目标状态：

```text
Repository
+
Installed Harness Mechanisms
=
Agent-ready Repository
```

Fresh Agent 即使没有任何 conversational inheritance，也能够：

```text
ENTER
↓
locate canonical execution truth
↓
obtain legal work
↓
acquire effective mutation authority
↓
bind an authorized isolated workspace
↓
execute
↓
produce candidate-bound evidence
↓
pass enforced integration gates
↓
integrate
↓
release / hand off authority
↓
preserve valid closure
```

---

# 2. System Boundary

整个系统有四个不同 owner。

```text
SYSTEM
│
├── A. OPERATION PROTOCOL
│   └── reasoning / modeling / sourcing / delegation
│
├── B. REPOSITORY AGENT HARNESS
│   └── repository execution guarantees
│
├── C. EXECUTOR / ORCHESTRATOR
│   ├── Codex
│   ├── Symphony
│   └── equivalent runtime
│
└── D. PROJECT
    └── product / engineering Source of Truth
```

## Operation Protocol owns

```text
Why before How
Capability Sourcing
Ownership decisions
Scoped Delegated Autonomy
Build the Delta
minimum sufficient method
```

## Executor / Orchestrator owns

```text
reasoning
tool use
debugging
retry
task execution
sandbox / technical approval
native review
session execution
orchestration where applicable
```

## Project owns

```text
Product truth
Engineering contracts
Project preferences
Acceptance semantics
Project-specific authority
```

## Repository Harness owns

> **Only the repository-local execution guarantees that must remain true across Agents, Sessions, Changes and integrations.**

---

# 3. Product Form

The Harness is not a prompt.

It is a reusable mechanism source plus project-local installed mechanisms.

```text
CANONICAL HARNESS REPOSITORY
│
├── Bootstrap Compiler / Installer
├── Capability Detection
├── Reusable Guards
├── Runtime / Provider Adapters
├── Guarantee Suite
├── Doctor / Verification
├── Reconciliation
└── Upgrade Support
        │
        ▼
TARGET REPOSITORY
│
├── project-local authority mapping
├── project-local Harness configuration
├── repository instructions
├── guards / hooks / CI wiring
├── project-specific adapters
└── durable execution guarantees
```

Canonical boundary:

> **Global tool, local truth.**

Reusable mechanism may be shared.

Project truth must remain project-local.

---

# 4. What Counts as a Guarantee

A rule is not a Guarantee merely because it is documented.

A Guarantee is established only through:

```text
INVARIANT
↓
APPLICABILITY
↓
DECLARED EXECUTION / TRUST ENVELOPE
↓
AUTHORITATIVE STATE
↓
LEGAL TRANSITIONS
↓
PROTECTED MUTATION SCOPE
↓
EFFECTIVE AUTHORITY
↓
FENCING WHERE APPLICABLE
↓
ENFORCEMENT POINT
↓
ENFORCEMENT COVERAGE
↓
BYPASS CLOSED OR EXPLICITLY OUT OF SCOPE
↓
INVALID CASE REJECTED
↓
VALID CASE ACCEPTED
↓
NORMAL AUTHORITATIVE PATH WIRED
↓
RECOVERY SEMANTICS
↓
OBSERVABLE PROOF
↓
VALIDITY CONDITIONS
```

Therefore:

```text
README says X
≠ Guarantee

AGENTS.md says X
≠ Guarantee

Prompt says X
≠ Guarantee

Guard exists
≠ Guarantee

Test exists
≠ Guarantee

Normal path calls guard
≠ Guarantee
```

If an in-scope authoritative bypass remains:

```text
→ OPEN GAP
```

or the Guarantee must be explicitly weakened in scope.

---

# 5. Harness Profile & Candidate Guarantee Set

A Repository must not be allowed to obtain PASS merely by omitting Guarantees from evaluation.

For the selected:

```text
Harness Profile
+
Current Execution Envelope
```

the Harness determines the complete:

```text
Candidate Guarantee Set
```

A required candidate Guarantee cannot disappear because the Repository did not declare it.

```text
Undeclared required Guarantee
≠ NOT APPLICABLE

Undeclared required Guarantee
= incomplete evaluation
```

The Candidate Guarantee Set is derived from actual execution topology, risks, authoritative surfaces and required capabilities.

It is not chosen opportunistically to make the Repository pass.

---

# 6. Guarantee Applicability

Every candidate Guarantee must first answer:

> **Does this Guarantee actually apply to the current Repository and Execution Envelope?**

Resolution:

```text
CANDIDATE GUARANTEE
↓
APPLICABILITY CONDITION
│
├── trigger demonstrably absent
│   └── NOT APPLICABLE
│
└── trigger present
    │
    ├── mechanism proven
    │   └── ESTABLISHED
    │
    └── mechanism missing / insufficient
        └── OPEN GAP
```

`NOT APPLICABLE` is itself a Proof Claim.

It cannot mean:

```text
“probably not needed”
```

It means:

```text
applicability trigger
→ demonstrably absent
inside current declared envelope
```

If applicability cannot be resolved:

```text
→ evaluation is incomplete
→ Harness closure cannot be claimed
```

---

# 7. Build Only Applicable Delta

The Harness must not install mechanisms merely because it supports them.

Incorrect:

```text
Harness supports fencing
→ install fencing everywhere

Harness supports orchestration
→ install orchestrator everywhere
```

Correct:

```text
Need
↓
Execution Envelope
↓
Candidate Guarantee
↓
Applicability
↓
Existing Guarantee?
↓
Project Delta
↓
install only missing capability
```

Canonical rule:

> **Apply only the Guarantees the execution envelope actually requires.**

---

# 8. Capability Sourcing

Before custom-building any Harness capability:

```text
Existing project mechanism
↓
Previous proven internal mechanism
↓
Executor-native capability
↓
Provider-native capability
↓
Mature external capability
↓
Custom implementation
```

Use:

> **the highest sufficiently fitting source.**

Then:

> **Build only the Delta.**

Examples:

```text
native sandbox exists
→ do not rebuild sandbox

provider PR / required checks exist
→ reuse where sufficient

mature orchestration exists
→ integrate where applicable

existing project guard already proves invariant
→ revalidate and reuse
```

Meta-capabilities receive no exemption.

Harness authoring itself must pass Capability Sourcing.

---

# 9. Execution / Trust Envelope

Every Guarantee exists only inside a declared:

```text
Execution / Trust Envelope
```

At minimum identify relevant:

```text
ACTORS
├── Coding Agents
├── Orchestrators
├── Humans
├── CI
├── Git / repository provider
├── Apps / bots
└── privileged automation
```

and:

```text
AUTHORITATIVE SURFACES
├── work state
├── filesystem / workspace
├── Git refs
├── tracker / backlog
├── PR / merge state
├── evidence state
└── Harness control surfaces
```

Do not claim universal safety beyond the envelope actually proven.

---

# 10. Enforcement Coverage

For every in-scope **authoritative transition**, at least one must be true:

```text
A. transition is forced through the enforcement point

OR

B. bypassed mutation cannot become authoritative
```

Important distinction:

```text
physical mutation
≠
authoritative mutation
```

Example:

A stale Agent may still physically modify an abandoned local worktree.

That does not violate the Guarantee if it cannot turn that mutation into authoritative project state.

Therefore:

> **Harness enforcement protects authoritative state, not every possible physical write, unless physical write prevention is itself the required invariant.**

---

# 11. Semantic Authority Map

The system does not require one universal database.

It requires:

> **Each semantic state has exactly one effective authority.**

Example:

```text
Product State
→ Product SoT

Work State
→ canonical tracker / backlog

Ownership State
→ effective ownership authority

Change State
→ Git / equivalent revision authority

Integration State
→ PR / merge provider

Evidence State
→ authoritative evidence mechanism
```

Derived:

```text
cache
projection
viewer
checkout
local copy
```

may exist.

But:

```text
Derived State
≠ Independent Authority
```

Two systems must not simultaneously claim authoritative ownership over the same semantic state.

---

# 12. Work Item, Change & Protected Mutation Scope

A Work Item is a planning / execution container.

It is not automatically the unit of exclusive ownership.

Correct relationship:

```text
WORK ITEM
│
├── CHANGE A
│   └── Protected Mutation Scope A
│
├── CHANGE B
│   └── Protected Mutation Scope B
│
└── CHANGE C
    └── Protected Mutation Scope C
```

Therefore:

```text
Work Item
→ 1..N Changes
```

Exclusive ownership applies to:

> **Protected Mutation Scope**

not automatically to the entire Work Item.

---

# 13. Protected Mutation Scope

A Protected Mutation Scope defines the authoritative state whose conflicting concurrent mutation must be prevented.

Guarantee:

> **One exclusive protected mutation scope may have at most one effective writer.**

If two scopes:

```text
overlap
```

or can perform:

```text
conflicting authoritative transitions
```

they may not have competing effective writers.

If two scopes are demonstrably:

```text
non-overlapping
+
independently enforceable
+
free from conflicting authoritative transitions
```

parallel execution is legal.

---

# 14. Scope Precision

Do not make the scope broader than necessary.

Do not make it narrower than can be proven safe.

Canonical rule:

> **Use the narrowest mutation scope whose independence can actually be established, but no narrower.**

Therefore:

```text
claimed independence
≠
proven non-interference
```

If independence cannot be established:

```text
→ use the safer shared exclusive scope
```

This prevents both:

```text
unnecessary serialization
```

and:

```text
unsafe artificial parallelism
```

---

# 15. Effective Ownership

Where exclusive ownership is applicable:

```text
Protected Mutation Scope
↓
Effective Ownership
↓
Authorized Workspace
```

Ownership must have operational meaning.

It cannot be merely:

```text
comment
label
README convention
```

An owner must be able to perform the protected transition.

A non-owner must not be able to make an unauthorized mutation authoritative.

---

# 16. Fencing — Where Applicable

Fencing is conditional.

It is required only where stale or competing owners can otherwise produce conflicting authoritative transitions.

Canonical requirement:

> **When fencing is applicable, revocation is not complete until stale authority can no longer perform an authoritative protected transition.**

Example:

```text
Owner A valid
↓
A becomes stale
↓
Owner B becomes effective
↓
A attempts authoritative transition
↓
REJECT
```

Implementation is not prescribed.

Possible mechanisms include:

```text
lease
epoch / generation
fencing token
CAS
atomic provider claim
single authoritative coordinator
integration-time ownership validation
equivalent mechanism
```

The Contract freezes the semantic guarantee, not one distributed-systems technique.

---

# 17. Workspace Binding & Isolation

Where isolated Changes are applicable:

```text
Work Item
↓
Change
↓
Protected Mutation Scope
↓
Effective Ownership
↓
Authorized Workspace
```

Concurrent Changes must not contaminate each other's execution state.

Workspace mechanisms may include:

```text
Git worktree
isolated checkout
container
remote workspace
equivalent isolation
```

The Harness specifies the isolation Guarantee, not one implementation.

---

# 18. Harness Lifecycle

Harness operation has explicit lifecycle states:

```text
GENESIS / BOOTSTRAP
↓
ACTIVATION
↓
MANAGED OPERATION
↓
UPGRADE
```

with exceptional:

```text
BREAK-GLASS / RECOVERY
```

---

# 19. Genesis / Bootstrap

Before initial installation:

```text
Harness does not yet exist
```

Therefore Harness cannot enforce its own creation.

Genesis may rely on:

```text
existing repository governance
+
explicit authorized installer
+
staged installation
+
Guarantee Suite
```

Before Activation:

```text
Harness Guarantees
= NOT YET ESTABLISHED
```

---

# 20. Activation

Activation is an explicit authority transition:

```text
Bootstrap Authority
↓
Managed Harness Authority
```

Activation requires all candidate Guarantees for the selected Profile / Envelope to resolve to:

```text
ESTABLISHED
```

or:

```text
currently valid NOT APPLICABLE
```

Any:

```text
OPEN GAP
unresolved applicability
stale proof
```

must remain explicit.

A stronger Harness closure cannot be claimed.

---

# 21. Managed Operation

After Activation:

> **Harness has no Harness exemption.**

Changes to Harness control surfaces must use the managed execution path where applicable:

```text
Infrastructure Change
↓
valid authority
↓
protected mutation scope
↓
isolated Change
↓
verification
↓
integration
```

---

# 22. Break-glass

Harness itself can fail.

Therefore recovery must not depend on a functioning Harness being able to authorize its own repair.

Break-glass is:

> **an explicit exceptional authority transition.**

It must be:

```text
authorized
observable
bounded where practical
auditable
```

and must:

```text
invalidate affected Guarantees
```

Affected Guarantees may not remain labelled ESTABLISHED while their enforcement substrate is bypassed.

After repair:

```text
Guarantee Suite
↓
Doctor / verification
↓
re-establish Guarantees
↓
return to Managed Operation
```

Break-glass is not an invisible backdoor.

---

# 23. Protected Harness Mutation

Relevant Harness control surfaces may include:

```text
authority mapping
ownership / claim mechanisms
fencing mechanisms
workspace guards
integration gates
evidence validity logic
bootstrap / activation logic
Doctor / verification
Harness configuration
```

In Managed Operation, these surfaces receive appropriate protection according to their applicable Guarantees.

---

# 24. Integration Candidate

Evidence must prove the thing that is actually intended to become canonical.

Therefore evidence binds to an:

> **Integration Candidate**

not merely “a commit that was tested once”.

Candidate identity should include materially relevant:

```text
change / head identity
target / base identity
resulting revision / tree
verification configuration
fixtures / contracts / baselines
environment where material
```

---

# 25. Evidence Freshness

If materially relevant Integration Candidate identity changes:

```text
head changes
base changes
rebase
merge-group recomposition
squash result changes
fixture changes
verification configuration changes
relevant contract changes
material environment changes
```

affected Evidence becomes:

```text
STALE
```

and must be re-established before it authorizes integration.

Provider-native candidate verification may satisfy this Guarantee when proven sufficient.

---

# 26. Verification Provenance

A check existing does not imply the check is authoritative.

For relevant integration Guarantees, verify:

```text
check exists
+
check blocks
+
check subject matches candidate
+
check provenance is acceptable
+
bypass policy matches Trust Envelope
+
freshness semantics are sufficient
```

Example:

```text
required check exists
```

but an untrusted actor can produce the accepted status:

```text
→ claimed Guarantee may not be established
```

---

# 27. Integration Gate

Canonical integration should preferentially reuse mature provider-native mechanisms.

Possible surfaces:

```text
PR
required checks
rulesets
protected branch
merge queue
merge-group verification
equivalent provider mechanism
```

Applicable integration checks may cover:

```text
authority validity
ownership validity
fencing validity where applicable
workspace validity
build
tests
domain verification
evidence freshness
protected-surface rules
```

Guarantee:

> **A blocking failure cannot silently become canonical integrated state.**

---

# 28. Guarantee Validity / Freshness

`ESTABLISHED` is not permanent.

Every Established Guarantee is bounded by:

```text
Claim / Scope
Applicability Condition
Trust Envelope
Authority
Enforcement Mechanism
Enforcement Substrate
Bypass Assumptions
Proof
Validity Conditions
Invalidation Triggers
```

If materially relevant substrate changes:

```text
provider ruleset
required checks
bypass actors
check provenance
CI workflow
ownership adapter
permission model
merge policy
Harness guard
authority mapping
trust envelope
```

then:

```text
old Guarantee proof
≠ automatically current Guarantee proof
```

Affected Guarantee becomes:

```text
STALE / UNPROVEN
```

until revalidated.

---

# 29. N/A Freshness

`NOT APPLICABLE` is also bounded closure.

Doctor must revalidate:

```text
ESTABLISHED
→ do validity conditions still hold?

NOT APPLICABLE
→ is the applicability trigger still absent?
```

Example:

```text
Yesterday:
single writer topology
→ fencing = N/A

Today:
second concurrent writer path introduced
↓
old N/A invalid
↓
fencing applicability must be resolved again
```

N/A is never a permanent exemption.

---

# 30. Doctor

Doctor verifies **live authoritative substrate**, not merely static files.

It answers:

```text
Which candidate Guarantees apply?

Which are ESTABLISHED?

Which are N/A?

Which are OPEN GAP?

Did any validity condition change?

Did any N/A trigger become active?

Did provider configuration drift?

Did enforcement coverage weaken?

Did bypass assumptions change?
```

Prefer observing provider state directly.

Do not mirror provider state into another database unless a real requirement demands it.

Canonical rule:

> **Observe authoritative substrate; do not mirror it unnecessarily.**

---

# 31. Closure Preservation

A sufficiently proven capability must remain discoverable while its validity conditions hold.

Fresh Agent should be able to determine:

```text
what is proven
scope of proof
validity conditions
Fixed / Proven Core
Allowed Variation
remaining Delta
```

Prefer existing project artifacts:

```text
tests
fixtures
contracts
ADR
canonical state
evidence
repository instructions
```

Do not create a mandatory Closure Registry merely because closure must be preserved.

---

# 32. Recovery & Reconciliation

Relevant failures may include:

```text
Agent dies
Session disappears
workspace survives
owner becomes stale
orchestrator restarts
tracker changes
PR changes
provider state changes
```

Recovery:

```text
OBSERVE authoritative state
↓
RECONCILE
↓
invalidate stale state / proof
↓
FENCE stale authority where applicable
↓
recover legal ownership
↓
reverify changed candidate / substrate
↓
CONTINUE
```

Recovery must not depend on conversational memory.

---

# 33. Fresh-Agent Continuity

A Fresh Agent with no inherited conversation must be able to:

```text
ENTER REPOSITORY
↓
LOCATE applicable instructions
↓
LOCATE authoritative work state
↓
IDENTIFY legal Change
↓
RESOLVE relevant authority / constraints
↓
ACQUIRE ownership where applicable
↓
ESTABLISH authorized workspace
↓
DISCOVER valid prior closure
↓
EXECUTE
↓
BUILD Integration Candidate
↓
VERIFY
↓
INTEGRATE through enforced gate
↓
RELEASE / COMPLETE
```

This is a primary end-to-end Harness proof.

The original bootstrap requirement that a new Session must independently locate state, claim safely, execute in isolation, recover and integrate remains a core acceptance surface.

---

# 34. Guarantee Map

For the complete Candidate Guarantee Set, every Guarantee must resolve to exactly one:

```text
ESTABLISHED

OPEN GAP

NOT APPLICABLE
```

Meaning:

### ESTABLISHED

```text
applicable
+
current mechanism
+
current proof
+
validity conditions hold
```

### OPEN GAP

```text
applicable
+
missing / insufficient / stale mechanism or proof
```

### NOT APPLICABLE

```text
applicability trigger
→ demonstrably absent
```

Repository closure cannot be obtained by omitting candidate Guarantees.

---

# 35. Guarantee Proof Standard

For a mechanically decidable Guarantee:

```text
known invalid case rejected
+
representative valid case accepted
+
normal authoritative path enforced
+
material bypass case rejected or explicitly outside envelope
```

Additional proof where applicable:

```text
ownership
→ stale-owner case rejected

evidence
→ stale-candidate case rejected

applicability
→ trigger-absent case proven

freshness
→ substrate-drift case invalidates old closure
```

The original principle remains:

```text
mechanically decidable invariant
→ cheapest reliable guard
→ invalid rejected
+ valid accepted
+ normal path enforced
```



---

# 36. Required Harness Capabilities

The reusable Harness should expose capabilities equivalent to:

```text
BOOTSTRAP
→ inspect / compile / install

VERIFY / DOCTOR
→ evaluate live Guarantees

PREFLIGHT
→ reject invalid protected transitions

RECONCILE
→ recover authoritative state

UPGRADE
→ modify Harness under managed governance

BREAK-GLASS
→ explicit exceptional recovery
```

Specific:

```text
CLI names
programming language
storage technology
provider
orchestration engine
```

are not frozen by this Contract.

Only capability semantics are frozen.

---

# 37. Prompt Boundary

Prompt may:

```text
invoke Bootstrap
describe project intent
provide missing project semantics
request verification
request upgrade
```

Prompt is not the Harness.

Canonical test:

```text
conversation disappears
↓
Harness Guarantees remain
```

If the Guarantee exists only while a prompt remains in model context:

> **The Mechanism was never established.**

---

# 38. Non-Goals

This Harness must not become, by default:

```text
a new Coding Agent
a replacement for Codex
a second Symphony
a universal Project Manager
a Product ontology
a Preference database
a global Project Authority registry
a new Review Engine
a Prompt Management Platform
a general Workflow DSL
a distributed scheduler
a universal lock service
a second provider-state database
```

New infrastructure requires actual evidence of a missing applicable capability.

---

# 39. Canonical Bootstrap Flow

```text
TARGET REPOSITORY
↓
LOCATE existing state
↓
VALIDATE intended Harness Profile / Execution Envelope
↓
DERIVE complete Candidate Guarantee Set
↓
RESOLVE Applicability
↓
SOURCE existing capabilities
↓
REVALIDATE existing Guarantees
↓
IDENTIFY Project Delta
↓
INSTALL / ADAPT only missing mechanisms
↓
WIRE authoritative paths
↓
CLOSE / DECLARE bypass surfaces
↓
RUN Guarantee Suite
↓
DOCTOR live substrate
↓
ACTIVATE
```

---

# 40. Canonical Runtime Flow

```text
AGENT ENTERS
↓
LOAD scoped project context
↓
LOCATE canonical work authority
↓
SELECT legal Change
↓
IDENTIFY protected mutation scope
↓
ACQUIRE effective authority where applicable
↓
ESTABLISH authorized workspace
↓
PREFLIGHT
↓
EXECUTE
↓
FORM Integration Candidate
↓
PRODUCE candidate-bound Evidence
↓
VERIFY
↓
PASS enforced integration
↓
INTEGRATE
↓
RELEASE authority
↓
PRESERVE closure
```

Exceptional path:

```text
FAILURE / DRIFT / INTERRUPTION
↓
RECONCILE
↓
INVALIDATE stale authority / evidence / guarantee
↓
FENCE where applicable
↓
RECOVER
↓
REVERIFY
↓
CONTINUE
```

---

# 41. Exit Proof

A Repository Harness may claim closure for the selected Profile / Envelope only after representative proof covers all applicable Guarantees.

At minimum, where applicable:

```text
APPLICABILITY PROOF
→ required Guarantees cannot disappear by omission

AUTHORITY PROOF
→ competing semantic authorities cannot both be effective

ENFORCEMENT COVERAGE PROOF
→ in-scope authoritative bypass cannot silently avoid enforcement

CONCURRENCY PROOF
→ conflicting protected scopes cannot have competing effective writers

FENCING PROOF
→ stale authority cannot perform protected authoritative transition

ISOLATION PROOF
→ concurrent legal Changes do not contaminate each other

MUTATION PROOF
→ invalid mutation cannot become authoritative

CANDIDATE FRESHNESS PROOF
→ changed Integration Candidate invalidates affected Evidence

CHECK PROVENANCE PROOF
→ accepted integration proof comes from valid authority

INTEGRATION PROOF
→ blocking failure cannot become canonical state

GUARANTEE FRESHNESS PROOF
→ enforcement-substrate drift invalidates affected Guarantee closure

N/A FRESHNESS PROOF
→ applicability change invalidates obsolete N/A

RECOVERY PROOF
→ interruption converges to legal recoverable state

BREAK-GLASS PROOF
→ exceptional repair invalidates and restores Guarantees explicitly

CLOSURE PROOF
→ still-valid prior closure remains discoverable

FRESH-AGENT PROOF
→ normal operation requires no conversational inheritance
```

---

# 42. Closure Rule

For the selected Harness Profile and current Execution Envelope:

```text
EVERY Candidate Guarantee
```

must resolve to:

```text
ESTABLISHED
```

or:

```text
currently valid NOT APPLICABLE
```

before full Harness closure may be claimed.

Any:

```text
OPEN GAP
STALE / UNPROVEN
unresolved Applicability
missing candidate evaluation
```

must remain explicit.

---

# 43. Final Canonical Chain

The complete Contract reduces to:

```text
INTENDED EXECUTION ENVELOPE
↓
COMPLETE CANDIDATE GUARANTEE SET
↓
APPLICABILITY
↓
AUTHORITATIVE STATE
↓
PROTECTED MUTATION SCOPE
↓
EFFECTIVE AUTHORITY
+
FENCING WHERE APPLICABLE
↓
AUTHORIZED EXECUTION SURFACE
↓
ENFORCEMENT COVERAGE
↓
INTEGRATION CANDIDATE
↓
FRESH AUTHORITATIVE EVIDENCE
↓
CURRENT ENFORCEMENT SUBSTRATE
↓
INVALID REJECTED
+
VALID ACCEPTED
+
BYPASS CLOSED / DECLARED
↓
RECOVERY
↓
OBSERVABLE PROOF
↓
ESTABLISHED GUARANTEE
```

And:

```text
material change to
applicability
authority
candidate
enforcement substrate
trust envelope
validity conditions
↓
invalidate affected closure
↓
re-evaluate
```

---

# 44. Final Invariants

```text
Prompt ≠ Mechanism.

Instruction ≠ Enforcement.

Guard exists ≠ Guarantee.

Normal path guarded ≠ bypass impossible.

Physical mutation ≠ authoritative mutation.

Work Item ≠ lock.

Claim ≠ fencing.

Fencing ≠ universally required.

Multiple Changes ≠ conflicting Changes.

Parallelism ≠ arbitrary scope splitting.

PASS once ≠ PASS forever.

N/A ≠ permanent exemption.

Provider state ≠ copy into another database.

Harness capability exists ≠ every Repository needs it.

Repository omission ≠ Guarantee N/A.

Fresh Agent ≠ previous conversation required.

Build only the applicable Project Delta.
```

---

# 45. Stop Rule

The Contract is sufficient when it guarantees:

```text
only applicable mechanisms are installed

authoritative state cannot silently fork

conflicting mutation cannot silently become authoritative

stale authority cannot remain effective where fencing is required

enforcement cannot be bypassed inside the declared envelope

Evidence proves the actual Integration Candidate

Guarantee closure expires when its validity conditions stop holding

N/A expires when its applicability assumptions stop holding

Fresh Agents can operate without conversational inheritance

existing platform / runtime capabilities are reused instead of duplicated
```

At that point:

> **STOP DESIGNING THE CONTRACT.**

Further evolution must be driven by implementation evidence or a demonstrated failure mode.

Build the Delta.