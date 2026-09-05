# ourdash SDK v0.1 — Product Requirements (SPEC)

Date: 04-09-26. Status: draft for human review. Audience: app developers, analysts, and the solo maintainer.

This document describes WHAT the `ourdash` v0.1 SDK must do for its users. It does not describe HOW it will be built. A separate planning step will turn these requirements into an implementation plan; nothing here is a build order.

> Name note: `ourdash` is a Python SDK for Dash crypto (dash.org). It is NOT related to Plotly Dash (the dashboard framework that owns the `dash` name on PyPI). This name choice is deliberate and permanent.

## Summary

`ourdash` v0.1 gives Python developers one typed, well-documented SDK for reading from and writing to the Dash network: Dash Core (a user's own node: account balances, blocks, transactions, wallets, network and masternode data) and Dash Platform (decentralized application data: documents, identities, usernames, and tokens). Today there is no mature typed Python SDK for Dash — only thin command wrappers and read-only helpers — so Python app developers and analysts must piece together shell commands, raw web requests, and JavaScript examples. v0.1 closes that gap for the most common jobs: connect to a node, look things up, build and sign payments safely, and read Platform application data with proof checking. Anything beyond that — hosted APIs, graphical wallets, running network infrastructure — is explicitly out of scope.

## User Stories / Jobs To Be Done

1. **Core RPC user.** As an app developer running my own Dash node, I want to connect to it with a username and password and run standard queries (blockchain info, blocks, transactions, balances) so that my app reads live chain data without shelling out to command-line tools.
2. **Wallet / transaction builder.** As an app developer holding user funds flows, I want to create a wallet from a recovery phrase, derive receiving addresses, build a payment offline, review it, sign it, and submit it as separate steps so that I never sign blindly and never expose secrets.
3. **Addresses / keys user.** As a developer accepting Dash payments, I want to validate any Dash address, tell which network and address kind it belongs to, and derive fresh addresses from my wallet so that I reject mistyped or wrong-network addresses before money moves.
4. **Network-data consumer.** As a developer monitoring network health, I want masternode-list changes, chain tips, and ChainLock confirmation status through one client so that I can show finality and network state without learning three separate interfaces.
5. **Platform app developer (reads).** As a Platform app developer, I want to query application data (documents and data contracts) from Dash Platform with cryptographic proofs checked automatically so that I can trust the answers without running my own Platform node.
6. **Identity / username user.** As a Platform app developer, I want to look up an identity (its keys, credit balance, and sequence number) and resolve a human-readable username to its identity so that logins and name displays just work.
7. **Token user.** As a Platform app developer, I want to read a token's rules and recent transfer activity so that my app can display balances and histories governed by on-chain rules.
8. **Analyst / data user.** As an analyst, I want to pull blocks, transactions, and address activity into plain Python objects I can feed to my own tools so that I can analyze Dash usage without operating infrastructure beyond an API endpoint.
9. **SDK maintainer (quality / docs).** As the solo maintainer, I want every release to pass automated tests, style checks, and type checks, with install and first-use guides verified from a clean checkout, so that quality stays strict without a team to catch mistakes.

## What The User Wants

Observable outcomes only. If you can see or check it from outside the SDK, it belongs here.

- A developer installs one package (plus one documented optional add-on for Platform features) and connects to a local node using credentials supplied through the environment — never typed into code or config files checked into version control.
- Reads work against the developer's own node by default (local-only), against standard public test networks for experiments, and against a discoverable set of Platform endpoints per network — with no dead or placeholder web address ever shipped as a default.
- Address handling tells the user, in plain terms: valid or invalid, which network (main network, test network, regtest, devnet), and which address kind — before any funds move.
- Wallet flows keep secrets safe: recovery phrases and private keys are never written to logs, error messages, or saved files by the SDK; the default posture is watch-only, with signing as an explicit, warned step.
- Payments are a visible pipeline — build, review, sign, submit — where each step can be inspected and where submitting an unsigned or malformed payment is refused with a clear error.
- Platform reads return application data together with a trust verdict: proof-checked against the chain, or explicitly marked as unchecked because the user chose a trusted-node shortcut (which requires an explicit opt-in flag, never silent).
- Failures are clear and safe: wrong credentials, unreachable nodes, timed-out requests, and rejected transactions each produce a distinct, actionable error that contains no secrets.
- The SDK behaves identically on every supported Python version, installs cleanly from scratch, and ships guides (install, connect, first payment on a test network, first Platform read, troubleshooting) that a new developer can follow end to end.

## Flow / State Diagram

The core payment journey plus the two read-only journeys (Core reads, Platform reads). Branches show failure handling and the trusted-node shortcut.

```
                    +------------------+
                    |  Configure:      |
                    |  network + creds |
                    |  (env only)      |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
     +--------+------+ +-----+-----+ +-----+------+
     | Core read:    | | Build     | | Platform   |
     | query own     | | payment   | | read: query|
     | node          | | offline   | | app data   |
     +-------+-------+ +-----+-----+ +-----+------+
             |               |               |
             v               v               v
     +-------+-------+ +-----+-----+ +-----+------+
     | OK?           | | Review    | | Proof      |
     | no -> typed   | | details   | | available? |
     | error (retry? | +-----+-----+ +-----+------+
     +-------+-------+       |          |        |
             |               v          v        v
             v         +-----+-----+  YES:     NO:
     +-------+-------+ | Sign      | verify    explicit
     | Return data   | | (explicit,+--+--+  trusted-node
     | (plain        | | warned)   |  |  |  flag?
     | objects)      | +-----+-----+  v  v   +--+--+
     +---------------+       |      PASS  FAIL  |  |
                             v        |    |    v  v
                     +-------+---+    |    |   ON: mark
                     | Submit to |    v    v   UNCHECKED
                     | network   |  return return + warn
                     +---+---+---+  data  typed
                         |   |           error
                        OK  REJECTED:
                        |   typed error,
                        v   no retry w/o fix
                 +------+------+
                 | Confirm:    |
                 | ChainLock / |
                 | InstantSend |
                 | status shown|
                 +-------------+
```

State summary: `unconfigured → configured → (reading | building → reviewing → signing → submitting → confirming)`. Any network or proof failure returns to a safe resting state with a typed error; secrets never appear in any error or log output.

## Acceptance Criteria

Max 20. Each is observable, names its proof scenario, and declares one test strategy grounded in the repo's test tiers (Fully-Automated = pytest with vectors/fakes, no node; Hybrid = needs the regtest node fixture or recorded proof fixtures, both yet to be built; Agent-Probe = live testnet or cross-checks a human/agent runs).

1. **Local node read works.** A developer connects to their own node and reads chain info, a block, and a wallet balance. *Proven by:* local-node read scenario. *Strategy:* Hybrid (regtest node fixture, to build).
2. **Connection setup is safe by default.** Pointing at a remote node address is refused unless the developer passes an explicit remote opt-in; credentials come only from the environment. *Proven by:* remote-refused-by-default scenario. *Strategy:* Fully-Automated.
3. **Multiple wallets selectable.** A developer with several wallets on one node picks which wallet each call acts on. *Proven by:* multi-wallet selection scenario. *Strategy:* Hybrid (regtest node fixture, to build).
4. **Recovery phrase creates wallet and addresses.** A developer restores from a standard recovery phrase and derives a valid receiving address for the chosen network. *Proven by:* recovery-phrase vector scenario (standard published test phrases). *Strategy:* Fully-Automated.
5. **Payment pipeline is inspectable and refuses bad submits.** Build → review → sign → submit are separate observable steps; submitting an unsigned or malformed payment is refused with a clear error. *Proven by:* offline build-and-sign scenario plus bad-submit refusal scenario. *Strategy:* Fully-Automated (vectors) for build/sign/refusal; live submit covered in criterion 6.
6. **Signed payment submits and confirms.** A signed test-network payment submits and its confirmation/finality status (including InstantSend/ChainLock state) is readable. *Proven by:* test payment scenario. *Strategy:* Hybrid (regtest node fixture preferred; Agent-Probe on testnet).
7. **Addresses validate with network and kind.** Any address input returns valid/invalid plus network (main/test/regtest/devnet) and kind, checked against known version-byte vectors. *Proven by:* address-vector scenario. *Strategy:* Fully-Automated.
8. **Wrong-network addresses are caught.** A test-network address presented on main network (and vice versa) is rejected before use. *Proven by:* wrong-network scenario. *Strategy:* Fully-Automated.
9. **Network health reads work.** Masternode-list changes, chain tips, and ChainLock status are readable through one client. *Proven by:* network-health scenario. *Strategy:* Hybrid (regtest node fixture, to build).
10. **Platform app data reads with proof verdict.** A developer queries Platform documents/contract data and gets the data plus a trust verdict (proof-checked vs. unchecked). *Proven by:* Platform read scenario. *Strategy:* Hybrid (recorded proof fixtures, to build).
11. **Trusted-node shortcut is explicit.** Proof checking can only be skipped with an explicit opt-in flag, and unchecked answers are always labeled as such. *Proven by:* explicit-fallback scenario. *Strategy:* Fully-Automated.
12. **Identity and username lookups work.** An identity's keys, credit balance, and sequence number are readable, and a username resolves to its identity. *Proven by:* identity-and-name scenario. *Strategy:* Hybrid (recorded fixtures, to build) with Agent-Probe spot-check on testnet.
13. **Token rules and transfers are readable.** A token's on-chain rules and recent transfer activity are returned as plain objects. *Proven by:* token-read scenario. *Strategy:* Hybrid (recorded fixtures, to build).
14. **Analyst reads need no node operation.** Blocks, transactions, and address activity load as plain Python objects usable in the analyst's own tools. *Proven by:* analysis-pull scenario. *Strategy:* Agent-Probe (testnet) after Hybrid fixtures exist.
15. **Errors are typed, actionable, and secret-free.** Wrong credentials, unreachable node, timeout, and rejected transaction each produce a distinct error containing no secrets. *Proven by:* failure-matrix scenario (fake server + bad-creds cases). *Strategy:* Fully-Automated.
16. **Secrets never leak.** Recovery phrases, private keys, and passwords never appear in logs, error output, or files written by the SDK during any scenario above. *Proven by:* secret-scan scenario over captured outputs. *Strategy:* Fully-Automated.
17. **Quality gates green on every change.** The test suite, style check, format check, and strict type check all pass, and the automated check workflow exists in the repo. *Proven by:* clean-gate scenario (fresh checkout → install → all four checks pass). *Strategy:* Fully-Automated.
18. **Docs work from zero.** A new developer follows the shipped guides (install, connect, first test-network payment, first Platform read, troubleshooting) end to end without outside help. *Proven by:* docs walkthrough scenario. *Strategy:* Agent-Probe (human/agent follows guides on testnet).

## Out Of Scope

v0.1 explicitly does NOT include:

- **Exchange or brokerage integrations** (trading, order books, fiat on/off-ramps, price feeds). Users bring their own market data.
- **A graphical wallet or mobile app.** The SDK is a library for developers; no user-facing wallet software ships.
- **Running network infrastructure for the user** (setting up, hosting, or operating nodes, masternodes, or validators). The SDK connects to infrastructure the user already runs or is granted access to.
- **A BlockCypher-style hosted API service.** No `ourdash`-operated servers, API keys, or usage billing — reads go to the user's own node or the public network endpoints.
- **Portfolio, tax, or compliance reporting.** Analysts get raw objects (criterion 14); reporting products are someone else's job.
- **Full Platform write coverage** (publishing data contracts, complex state transitions beyond basic payment-adjacent flows). v0.1 locks Platform reads plus identity/username/token lookups; broader writes wait for a later version.

## Constraints

User requirements, system rules, and research boundaries that the SDK and its plan must respect:

- **Naming.** The package is `ourdash`. The PyPI name `dash` belongs to Plotly Dash (currently v4.4.1, a dashboard framework) — never install or reference it expecting crypto. Every public doc disambiguates "Dash (dash.org)" vs "Plotly Dash". The maintainer reserves `ourdash` on PyPI and TestPyPI.
- **Core compatibility pin.** Dash Core v23.1.8 (latest as of Aug 2026; v23.0.0 was the breaking major). Command/behavior parity is checked against `dash-cli help` from that version.
- **Node connection realities.** Node RPC is HTTP POST JSON-RPC; default ports are mainnet 9998, testnet 19998, regtest 19898, devnet 19788; nodes bind to the local machine by default with username/password or cookie-file login; the desktop wallet needs server mode enabled; multi-wallet support (Core 18+) selects wallets per call; batched requests are supported by the node but not by the `dash-cli` helper. Read-only web access and real-time push feeds are separate, opt-in, same-port/unsecured-by-default mechanisms for trusted networks only, with user-visible warnings.
- **Protocol facts.** ChainLocks (active since block 1088640, Jun 2019) mean no reorganization below a locked block; InstantSend exists in an original and a current deterministic form (the rotation upgrade only changed quorum selection, it did not invent either feature); special transaction types 0–9 follow the canonical registry (classical, masternode registrations/updates/revocation, coinbase payload, quorum commitment, hard-fork signal, asset locks/unlocks). Block hashing uses the eleven-hash X11 chain; transactions, Merkle trees, and addresses stay on standard SHA-256/RIPEMD-160 hashing.
- **Address facts.** Address version bytes are fixed per network and kind (main/test × standard/multisig script) with double-SHA-256 checksums, verified against Core's chain parameters.
- **Platform access.** Platform queries use per-network seed-based discovery (e.g. the documented testnet seed pattern); no single main-network web address is documented, and the `api.dash.org` placeholder does not resolve — it must never ship as a default. Layer-1 info queries are a small fixed set (best block hash, block hash, status, raw-transaction submit); richer and streaming queries (headers with ChainLocks, transactions with proofs, masternode lists) use the streaming interface, while application-data queries with optional proofs use the versioned application interface.
- **Trust model.** Platform answers carry cryptographic proofs checked against the per-block commitment and quorum signatures; proof verification in Python is greenfield (only Rust/WebAssembly/Node verifiers exist today), so v0.1 scopes it to a port/bridge path and always offers the explicit trusted-node fallback flag — never silent trust.
- **Wallet scope.** v0.1 includes recovery-phrase wallet restore, standard account-structure derivation, and signing — always with custody warnings, watch-only default, and a never-log-secrets rule.
- **Security rules.** Credentials live in the environment only and never appear in logs or errors; local-only is the default with explicit remote opt-in; every network call has timeouts and retries with typed errors; push-feed/web-access features carry trusted-network-only warnings; Platform connections verify transport security; proofs are on unless the explicit fallback flag is set.
- **Platform facts.** Data contracts are JSON-Schema-based (current version supports tokens, groups, keywords); documents query like a document database; state changes come in numbered types (batched operations incl. token mint/burn/transfer/freeze, identity create/top-up/update, credit transfer/withdrawal, masternode votes incl. premium-name votes); identities use hierarchical keys with credits and sequence numbers; usernames resolve to identities incl. contested-name voting; tokens carry declarative rules with group authority. The recommended JavaScript reference for new work is the proof-capable toolkit; the older all-in-one bundle is trusted-nodes-only without proofs.
- **Ecosystem gap (holds).** Existing Python options are a thin command-line wrapper (2017, ~2 stars), a minimal command-line wallet (~1 star), and a basic read-only helper with no validation or submit — no mature typed SDK. `ourdash` fills this; the record on the minimal-wallet option is corrected per validation.
- **Python and quality.** Python 3.10+; strict typing, style, and format checks plus the pytest suite must pass; source-layout packaging; documented default plus optional Platform add-on.
- **Test reality.** pytest only; two smoke tests exist today with seven modules at zero coverage and no fixtures or automation workflow. Realistic now: vector/framing/config-parsing tests; to build: local-node fixture and recorded proof fixtures; human/agent-run: test-network and cross-implementation spot checks; known gaps: signing vectors, live suites, and the automation workflow file (which v0.1 must add).

## Open Questions

None. All questions arising during discovery were resolved by the decisions below:

- Core pin: v23.1.8. Read-only web vs push-feed wording: split as two separate mechanisms. Protocol numbers: per the canonical registries stated in Constraints. Platform endpoints: per-network seed discovery, no hard-coded address. InstantSend: original + current forms both cited. Special-transaction registry: complete types 0–9. Ecosystem record: minimal-wallet entry corrected. JavaScript reference versions: pinned per validation. Devnet port included. Package name reservation: maintainer action. Proof verification: scoped as port/bridge path. Wallet signing: in v0.1 with custody warnings. Test strategy: local-node fixture preferred, test-network spot checks. Automation workflow: in v0.1.

## Background / Research Findings

Key facts that shaped these requirements (condensed; full sources live in the research notes, not here):

- **Node access shape.** The node speaks HTTP POST JSON-RPC with basic login, local-machine binding, per-version command lists, multi-wallet selection, and batch support the CLI helper lacks. Read-only web access and push feeds are separate opt-in trusted-network mechanisms. This is why the SDK defaults to local-only, requires explicit remote opt-in, and warns on the trusted-network features.
- **Finality model.** ChainLocks (quorum-signed, active since Jun 2019) plus InstantSend in its original and current deterministic forms define Dash confirmation semantics — including the guarantee of no reorganization below a locked block. The SDK must surface this status (criteria 6, 9) and never credit the rotation-only upgrade with inventing either feature.
- **Address and hashing facts.** Fixed version bytes per network/kind with double-SHA-256 checksums (verified against Core's chain parameters); the eleven-hash chain is block-hashing only while transactions and addresses use standard hashes. This grounds the offline vector tests (criteria 7, 8).
- **Platform shape.** Small fixed Layer-1 info set; streaming for headers/transactions/masternode lists; versioned application interface with optional proofs for app data; per-network seed discovery with no documented single main-network address (the placeholder address does not resolve and must not ship). Application layer: schema-based contracts, document-style queries, numbered state-change types, hierarchical-key identities with credits/sequence numbers, username-to-identity resolution with contested-name voting, rule-carrying tokens. This is why Platform reads carry a proof verdict with an explicit fallback flag (criteria 10, 11).
- **Proof gap.** No Python proof verifier exists (only Rust/WebAssembly/Node implementations; generic signature libraries are insufficient). v0.1 therefore scopes verification to a port/bridge path with a loud trusted fallback — a deliberate boundary, not an oversight.
- **Ecosystem gap.** No mature typed Python SDK exists — only a dated thin wrapper, a minimal CLI wallet, and a basic read-only helper. Cross-checking the JavaScript side: the older all-in-one bundle (pinned per validation) is trusted-nodes-only without proofs; the newer proof-capable toolkit is the recommended reference. This confirms both the need and the trust-model requirements.
- **Test reality.** Two smoke tests, zero-coverage modules, no fixtures or automation. Vector/config tests are realistic today; the local-node fixture and recorded proof fixtures must be built; test-network and cross-implementation checks stay human/agent-run; signing vectors, live suites, and the automation workflow are the known gaps v0.1 must close.
- **Validation corrections baked in.** Core pin v23.1.8; web-vs-push split wording; canonical DIP/transaction-type numbers; seed-based Platform discovery; InstantSend original+current citation; complete special-transaction registry; corrected minimal-wallet record; pinned JS reference versions; devnet port in the table; package-name reservation; greenfield proof scoping; wallet signing in v0.1 with warnings; fixture-first testing with test-network spot checks; automation workflow in v0.1.
