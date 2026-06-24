# Useful Links — CCA-F (Claude Certified Architect – Foundations)

---

## Official Anthropic resources

- **Enrollment / start (CCAF)** — https://clau.de/CCAF
- **Skilljar practice exam** — https://anthropic.skilljar.com/anthropic-certification-practice-exam
  - Access after completing the 4 base courses, using a `@horustech.dev` email.
- **Skilljar access request (CCA-F)** — https://anthropic.skilljar.com/claude-certified-architect-foundations-access-request
  - Note: the real exam is **proctored** and **paid**.
- **Certification FAQ** — https://claudecertifications.com/claude-certified-architect/faq
- **Claude Code docs (agents)** — https://code.claude.com/docs/ru/agents
- **Partner support contact** — partner-support@anthropic.com

## Study guides

- **Study Guide (PDF, paullarionov)** — https://github.com/paullarionov/claude-certified-architect/blob/main/pdf/guide_en.pdf
  - Covers all 5 exam domains.
- **Preliminary guide by Ivan Stadnik (Google Doc)** — https://docs.google.com/document/d/1uDc7L7XSavAJCXXw8PDDg5qKea8S1bnZrgV389mQlUA/edit?usp=sharing
  - Based on real exam experience; includes hard practice questions at the bottom.
- **claudecertificationguide.com (theory by topic)** — https://claudecertificationguide.com/learn/1-agentic-architecture/1-1-agentic-loops
  - Recommended by Michael as very helpful.

## Practice / mock exams

- **CyberSkill mock exam** — https://ccaf.cyberskill.world/
  - Questions very similar to the real exam. (Mirror: https://claude-certified-architect-mock-exam-cyberskill.vercel.app/#exam)
- **Udemy — 3 Full Practice Exams (TekSystems)** — https://external-teksystems.udemy.com/course/anthropic-claude-certified-architect-3-full-practice-exams
- **Udemy — 5 Practice Tests (coupon MT260529G2)** — https://www.udemy.com/course/claude-certified-architect-certification-5-practice-tests/?couponCode=MT260529G2
-  **certificationpractice.com** — https://certificationpractice.com/practice-exams/anthropic-claude-certified-architect-foundations
- **TutorialsDojo — free sampler** — https://portal.tutorialsdojo.com/product/free-claude-certified-architect-foundations-cca-f-practice-exams-sampler/
- **claudecertificationguide.com (tests)** — http://claudecertificationguide.com

## Our own materials

- **Shared study-material repository** — https://github.com/MichaelWalker-git/anthropic_study_material
  - Mock-exam branch (more questions, runs locally): https://github.com/MichaelWalker-git/anthropic_study_material/tree/feature/cca-f-mock-exam
  - Agents branch (Diagnostician + Generator): https://github.com/MichaelWalker-git/anthropic_study_material/tree/feature/exam-trainer
  - Example PR adding/refining questions: https://github.com/MichaelWalker-git/anthropic_study_material/pull/3
  - ⚠️ Remember to download and push new resources to the shared repo.
- **Question bank (NotebookLM, built from all Anthropic docs)** — https://notebooklm.google.com/notebook/424ad1d9-30ab-4ed4-9a5f-5fed08eea5cd

## Udemy platform (access)

- **External TekSystems Udemy** — https://external-teksystems.udemy.com
  - Has unlimited courses.
- **Udemy 2FA codes (Google Group)** — https://groups.google.com/a/horustech.dev/g/udemy
  - Login credentials are posted in `#anthropic-certification-internal` — not duplicated here for security.

## Tools

- **NotebookLM Audio Overviews (turn materials into a podcast)** — https://blog.google/innovation-and-ai/products/notebooklm-audio-overviews/
- **Otter.ai (recording / transcript)** — https://otter.ai/u/O2gp4qfv1N9kdR2VSvw35RQHAQI

---

## Exam structure (5 domains)

1. Agent Architecture (Agentic Architecture & Orchestration)
2. Tools and MCP
3. Claude Code Configuration & Workflows
4. Prompt Engineering
5. Context and Reliability

## Exam tips (from people who took it)

- 4 scenarios: Document processing, CI/CD with Claude, Claude in action, Chat.
- Questions are similar to the practice exams but worded differently, with close answer choices — you must actually understand best practices, not memorize.
- Many questions about **MCP**: how Claude Code discovers and loads tools from multiple MCP servers; how it retrieves prompts from MCP servers.
- When to use **Plan Mode vs. Direct Mode**.
- A significant portion covers **context management**: preserving context, subagent handoffs, using a scratchpad to maintain state, and the Grep/Edit/Write tools.
- Lots of variations on **Code Review giving false positives** and how to fix them.
- Recommendation: take the exam first thing in the morning — it is draining and requires a lot of focus.
- Readiness target: pass practice tests in timed/exam mode at 85%+.
- Exam cost: ~$50 (for corporate-domain emails); a failed attempt can be retaken (a second attempt is available, reportedly at half price within ~1 day).
- The exam is proctored with face scanning; no passport required, just a recording. (Note: Anthropic may invalidate results / ban the domain for cheating.)