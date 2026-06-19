# Claude Certified Architect – Foundations: Extracted Questions (Set 3)

> Source: photos in `Photos-3-001/`. Exam has 60 questions total; this set captures the questions visible in the photos (Q3–Q21, Q27, Q48, Q51–Q60, plus one question whose number was cut off).
> "Marked answer" = the option that was selected/highlighted in the screenshot. Treat as the test-taker's choice, not a verified correct answer.

---

## Question 3 — Developer Productivity with Claude

An engineer submits two requests:

- **Request A:** "Rename the `getUserData` function to `fetchUserProfile` everywhere it's used."
- **Request B:** "Improve error handling throughout the data processing module — add try/catch blocks, meaningful error messages, and ensure failures don't silently corrupt data."

For which request does specifying an explicit multi-phase workflow (such as analyze → propose → implement with review) most improve outcome quality?

- A. Neither request benefits significantly
- B. Both requests benefit equally
- C. Request A, the function rename task
- D. Request B, the error-handling improvement task *(option cut off in photo)*

---

## Question 4 — Developer Productivity with Claude

After integrating a local MCP server providing code analysis tools (`analyze_dependencies`, `find_dead_code`, `calculate_complexity`), you verify the server is healthy and tools appear in the `tools/list` response. However, you observe that the agent consistently uses Grep to search for import statements instead of calling `analyze_dependencies` — even when users explicitly ask about "code dependencies."

Examining tool definitions reveals:

- **MCP:** `analyze_dependencies` — "Analyzes dependency graph"
- **Built-in:** Grep — "Search file contents for a pattern using regular expressions. Returns matching lines with line numbers and surrounding context."

What's the most effective approach to improve the agent's selection of MCP tools?

- A. Add routing instructions to the system prompt specifying that dependency-related questions should use MCP tools rather than Grep.
- B. Expand MCP tool descriptions to detail capabilities and outputs—e.g., "Builds dependency graph showing direct imports, transitive dependencies, and cycles." **(Marked answer)**
- C. Split `analyze_dependencies` into granular tools (`list_imports`, `resolve_transitive_deps`, `detect_circular_deps`) so each has a focused purpose less likely to overlap with Grep.
- D. Remove Grep from available tools when the MCP server is connected to eliminate functional overlap.

---

## Question 5 — Developer Productivity with Claude

Your agent has spent 25 minutes exploring a game engine's rendering subsystem—reading shader code, buffer management, and frame synchronization logic. An engineer now asks it to understand how the physics engine integrates with rendering for collision debug overlays. You notice recent responses reference "typical rendering patterns" rather than the specific `VulkanPipeline` and `FrameGraph` classes it discovered earlier.

What's the most effective approach?

- A. Summarize key rendering findings, then spawn a sub-agent for physics exploration with that summary in its initial context.
- B. Spawn a sub-agent to explore physics independently, then manually synthesize its findings with the rendering knowledge accumulated in the main conversation. **(Marked answer)**
- C. Continue in the current context with more targeted prompts referencing the specific classes by name.
- D. Use `/clear` to reset context completely, then start fresh with physics exploration using file paths from the project's CLAUDE.md.

---

## Question 6 — Developer Productivity with Claude

A developer asks the agent to investigate why a specific API endpoint intermittently returns 500 errors. The codebase has 200+ files and the developer doesn't know which components are involved. The agent must trace the error through routing, middleware, business logic, and database layers. What task decomposition approach would be most effective?

- A. Define a fixed sequence of investigation steps upfront—grep for error patterns, then read error handlers, then check database queries, then examine middleware—executing each step regardless of intermediate findings.
- B. Have the agent first create a comprehensive plan mapping all code paths through the endpoint before beginning any file exploration or code reading.
- C. Have the agent dynamically generate investigation subtasks based on what it discovers at each step, adapting its exploration plan as new information about the error path emerges. **(Marked answer)**
- D. Run parallel worker agents that simultaneously investigate all four layers, then synthesize their findings to identify where the error originates.

---

## Question 7 — Developer Productivity with Claude

After adding an MCP server with specialized code refactoring tools (`extract_function`, `rename_variable`, `inline_function`), you notice the agent still uses basic text manipulation via Write and Bash `sed` commands for refactoring tasks. The MCP server is connected and healthy. Examining the configuration, you find each MCP tool has a minimal description like "extract_function: Extracts a function from code."

What's the most effective way to improve adoption of the MCP refactoring tools?

- A. Accept this as expected behavior since simpler tools like sed are more predictable than specialized refactoring tools.
- B. Remove the Write tool from the agent's configuration for refactoring sessions so it must use the MCP tools for code modifications.
- C. Implement a request classifier that detects refactoring intent and automatically routes those requests to the MCP server before the agent processes them.
- D. Enhance the MCP tool descriptions to explain when each tool is preferable to text manipulation and clarify expected inputs and outputs. **(Marked answer)**

---

## Question 8 — Developer Productivity with Claude

You're building a security scanning workflow. When engineers need to locate all occurrences of a dangerous function like `eval()` across a large codebase, which tool should your agent use for content search?

- A. Use Grep to search for the pattern `eval(` across all files in the codebase. **(Marked answer)**
- B. Use Glob with a pattern like `**/*eval*` to find files, then Read each matching file.
- C. Use Bash to run `ls -R | grep eval` to recursively list files containing eval.
- D. Read the project's main entry file and follow import statements to trace where eval might be used.

---

## Question 9 — Developer Productivity with Claude

Engineers frequently ask the agent to cross-reference code changes with Jira tickets during reviews—checking ticket descriptions, acceptance criteria, and recent comments. This currently requires manually copy-pasting content into conversations. The team wants the agent to access this standard Jira ticket data directly. What's the most effective approach?

- A. Export Jira tickets to markdown files in the repository that the agent accesses using the Read tool.
- B. Build a custom MCP server wrapping Jira's API with tools designed specifically for this team's code review workflow.
- C. Use the Bash tool with `curl` to call Jira's REST API, including authentication headers and parsing JSON responses inline.
- D. Integrate an existing Jira MCP server that exposes tickets, comments, and metadata through discoverable tool interfaces. **(Marked answer)**

---

## Question 10 — Developer Productivity with Claude

An engineer asks your agent to identify untested code paths in a legacy payment processing module spanning 45 files. After reading the first 8 source files, the agent's responses are becoming noticeably less accurate—it's forgetting previously discussed code patterns and hasn't yet located all test files or traced critical payment flows. What's the most effective approach to complete this investigation?

- A. Clear context with `/clear`, then selectively re-read only the most critical files discovered so far, writing key findings to a scratchpad file that persists between context resets.
- B. Spawn subagents to investigate specific questions (e.g., "find all test files for payment processing," "trace refund flow dependencies") while the main agent coordinates findings and preserves high-level understanding. **(Marked answer)**
- C. Document all current findings in a summary report, clear context completely, then use that report as the sole reference for continuing the investigation.
- D. Switch to using Grep to search for specific function names instead of reading full files, reducing the content loaded into context for remaining exploration.

---

## Question 11 — Developer Productivity with Claude

An engineer sees an unfamiliar error message "SYNC_CONFLICT: entity version mismatch detected" in production logs but doesn't know which of the 12 services in the codebase generates it. They ask the agent to help locate the source code. What exploration approach will most efficiently find the responsible code?

- A. Use Grep to find all files that import the project's error handling module, then Read those files to locate custom error definitions.
- B. Use Grep to search for distinctive text from the error message (like "SYNC_CONFLICT" or "entity version mismatch"), then Read the matching files to understand context. **(Marked answer)**
- C. Read the project's README and service configuration files to understand the architecture, then systematically Read source files in each service directory.
- D. Use Glob to find files in directories commonly associated with error handling (such as `errors/`, `exceptions/`, or `handlers/`) across all services, then Read each matching file.

---

## Question 12 — Developer Productivity with Claude

You've configured your Claude agent with three MCP servers: one for git operations, one for Jira ticket management, and one for documentation search. When a user asks the agent to "create a branch for JIRA-123 and add documentation links to the ticket," how does the agent access tools across these servers?

- A. Tools from all configured MCP servers are discovered at connection time and available simultaneously to the agent. **(Marked answer)**
- B. The agent queries each server sequentially to determine which handles each tool, routing calls based on tool name prefixes.
- C. The agent automatically selects the most relevant server based on the request and loads only that server's tools.
- D. You must specify which MCP server to use for each turn, and the agent can only access one server's tools at a time.

---

## Question 13 — Developer Productivity with Claude

Your codebase exploration tool stores session IDs to allow engineers to continue investigations across work sessions. An engineer spent an hour yesterday analyzing a legacy authentication module, building context about its architecture and dependencies. They want to continue today. The session ID is valid, but version control shows 3 of the 12 files the agent previously read were modified overnight by a teammate's merge. What approach best balances efficiency and accuracy?

- A. Resume the session without informing the agent about the changed files.
- B. Resume the session and inform the agent which specific files changed for targeted re-analysis. **(Marked answer)**
- C. Resume the session and immediately have the agent re-read all 12 previously analyzed files.
- D. Start a fresh session to ensure the agent works with current codebase state without stale assumptions.

---

## Question 14 — Developer Productivity with Claude

An engineer asks the agent to find all files in the monorepo that import the `@company/auth` package to understand how authentication is used across services. Which built-in tool is most appropriate for this task?

- A. Read, starting with package.json files to trace dependency declarations.
- B. Grep, to search for the import statement pattern across file contents. **(Marked answer)**
- C. Bash, to execute `find . -type d -name "auth"` and explore matching directories.
- D. Glob, to find files with "auth" in their filename or path.

---

## Question 15 — Developer Productivity with Claude

An engineer asks your agent to add comprehensive tests to a legacy codebase with 200 files and minimal existing test coverage. The engineer hasn't specified which modules to prioritize. How should the agent decompose this open-ended task?

- A. Start writing tests for the first module alphabetically, using test failures and imports to discover related files organically.
- B. Create a fixed testing schedule upfront based on directory structure, allocating equal effort to each top-level directory regardless of code complexity or business importance.
- C. Use Glob and Grep to map codebase structure, identify heavily-coupled modules, create a prioritized plan for high-impact areas, and revise as dependencies are discovered. **(Marked answer)**
- D. Systematically read all 200 files to create a complete function inventory before writing any tests, ensuring the testing plan accounts for every function before beginning.

---

## Question 16 — Structured Data Extraction

Monitoring shows 12% of extractions fail Pydantic validation with specific errors like "expected float for quantity, got '2 to 3'". Retrying these requests without modification produces identical failures. What's the most effective approach to recover from these validation failures?

- A. Send a follow-up request including the validation error, asking the model to correct its output. **(Marked answer)**
- B. Implement a secondary pipeline using a larger model tier to reprocess documents that fail validation.
- C. Set temperature to 0 to eliminate output variability and ensure consistent formatting.
- D. Pre-process source documents to standardize problematic formats before sending them for extraction.

---

## Question 17 — Structured Data Extraction

The system routes documents with extraction confidence below 85% to human review. A quarterly audit reveals that 12% of high-confidence extractions (>85%) also contain errors—cases where the model finds plausible-but-incorrect values. Error sources vary: comparison tables showing competitor specs, appendices referencing different product variants, and ambiguous phrasing the model misinterprets. You need a sustainable strategy to catch these high-confidence errors and measure whether improvements reduce the error rate over time. What approach is most effective?

- A. Add a verification pass that re-extracts from each high-confidence document, flagging cases where the two extraction attempts produce different results.
- B. Lower the confidence threshold from 85% to 70%, routing a larger volume of extractions to human review.
- C. Implement heuristic rules that flag documents containing comparison tables or appendices for review regardless of confidence score.
- D. Implement stratified random sampling reviewing a fixed percentage of high-confidence extractions weekly, enabling error rate measurement and novel pattern detection. **(Marked answer)**

---

## Question 18 — Structured Data Extraction

Your extraction pipeline processes contracts that frequently include amendments. When a contract contains both original terms and later amendments (e.g., original clause specifies "30-day payment terms" while Amendment 1 changes this to "45 days"), the model inconsistently extracts one value or the other with no indication of which applies. What's the most effective approach to improve extraction accuracy for documents with amendments?

- A. Add prompt instructions to always extract the most recent amendment value and ignore superseded original terms.
- B. Implement post-extraction validation using pattern matching to detect amendments and flag those extractions for manual review.
- C. Preprocess documents with a classifier that identifies and removes superseded sections before the main extraction step.
- D. Redesign the schema so amended fields capture multiple values, each with source location and effective date. **(Marked answer)**

---

## Question 19 — Structured Data Extraction

Your extraction system parses e-commerce product descriptions to extract specifications like dimensions, weight, and materials into JSON. Despite having a well-defined schema, the model inconsistently extracts the "materials" field—sometimes returning "cotton blend", other times "Cotton/Polyester mix", and occasionally omitting the field when material information is clearly present in the source. What's the most effective way to improve extraction consistency?

- A. Set temperature to 0 to eliminate randomness and ensure deterministic outputs.
- B. Add few-shot examples showing 2-3 complete input-output pairs with standardized material description formats. **(Marked answer)**
- C. Make the "materials" field required instead of optional in the schema to force the model to always extract a value.
- D. Switch to a more capable model tier since inconsistent extraction indicates insufficient model capability.

---

## Question 20 — Structured Data Extraction

After implementing tool use with strict schema definitions, JSON syntax errors are eliminated, but 5% of extractions still have valid JSON with empty arrays or null values for required fields like citations and methodology. Spot-checking reveals that source documents contain this information, but in varied formats—inline citations vs. bibliographies, methodology sections vs. details embedded in introductions. What's the most effective way to address these failures?

- A. Add few-shot examples demonstrating extractions from documents with varied structures—showing how to identify citations in different formats and locate methodology details across section types. **(Marked answer)**
- B. Build a regex-based post-processing layer that scans source documents for citation patterns and methodology keywords, populating empty fields when the model fails to extract.
- C. Modify your schema to make citations and methodology optional, and flag incomplete records for manual review rather than failing validation.
- D. Implement retry logic that re-sends requests when validation detects empty required fields.

---

## Question 21 — Structured Data Extraction

Your system has been operating with 100% human review for 3 months. Analysis shows that extractions with model confidence >90% have 97% accuracy overall. To reduce reviewer workload, you plan to automate high-confidence extractions. Before deploying, what validation step is most critical?

- A. Analyze accuracy by document type and field to verify high-confidence extractions perform consistently across all segments, not just in aggregate. **(Marked answer)**
- B. Run a two-week pilot routing 25% of high-confidence extractions directly to downstream systems and monitor error reports.
- C. Compare accuracy at different confidence thresholds (85%, 90%, 95%) to find the optimal cutoff that maximizes automation while minimizing errors.
- D. Verify that 97% accuracy meets requirements for all downstream systems that consume the extracted data.

---

## Question 27 — Structured Data Extraction

The system processes product reviews using tool use with a defined schema: rating (integer 1-5), pros (string array), cons (string array), and overall_sentiment (enum: positive, negative, mixed). Testing reveals two issues with brief or ambiguous reviews (~20% of the dataset): (1) for reviews like "Great product!", Claude fabricates specific pros and cons rather than indicating this information isn't explicitly stated, and (2) for sarcastic reviews like "Well that was... interesting", Claude picks sentiment arbitrarily since there's no option for ambiguous cases. What schema modification best addresses both issues?

- A. Allow null values for pros/cons, and add "unclear" to the sentiment enum.
- B. Add an extraction_confidence field (0.0-1.0) for each value, and filter outputs where any confidence falls below a threshold.
- C. Allow empty arrays for pros/cons as valid output, and add "unclear" to the sentiment enum.
- D. Make pros and cons optional fields, and add "neutral" and "unclear" to the sentiment enum. **(Marked answer)**

---

## Question 48 — Claude Code for Continuous Integration

Your pipeline reviews every PR using a single API call with a static prompt containing the diff and full text of each changed file — unchanged files are not included. Reviews are posted asynchronously and don't block PR creation. Developers report that reviews consistently miss bugs involving cross-file interactions — for example, a PR renames a function's parameters but the review doesn't flag callers in unchanged files that still use the old argument order. Evaluation shows cross-file bugs account for 35% of production incidents from reviewed PRs. What is the most effective change to your review design?

- A. Add chain-of-thought instructions asking the model to list all external references in the diff, then reason step-by-step about how each change might affect callers in other files.
- B. Run parallel review passes per changed file with direct dependents included in each pass, then aggregate and deduplicate findings using a final summarization call.
- C. Redesign the review as a turn-limited agentic task where the model can read files and search the codebase via tools, following references to verify cross-file findings. **(Marked answer)**
- D. Use static analysis to build a dependency graph of changed code, then expand the prompt to include all files within two dependency hops of any changed file.

---

## Question 51 — Claude Code for Continuous Integration

Your automated review calls the Claude API for each PR, using tool_use with a `report_findings` tool that returns a JSON array of finding objects (each with `file_path`, `line_number`, `severity`, `category`, and `description`). During testing on a large PR touching 30+ files, the response hits the `max_tokens` limit and the output is truncated mid-JSON, causing your pipeline's parser to fail. What is the most effective way to handle this?

- A. Switch from tool_use to prompting Claude to return findings as a markdown list.
- B. Split the review into multiple API calls that each analyze a subset of the changed files, then merge the resulting findings arrays.
- C. Add retry logic that detects truncated JSON and re-sends the request with instructions to report only critical and high severity findings.
- D. Increase `max_tokens` to the model's maximum and instruct Claude to keep finding descriptions under 50 words each. **(Marked answer)**

---

## Question 52 — Claude Code for Continuous Integration

After deploying automated code review, developers report that approximately 35% of flagged findings are false positives falling into consistent patterns: style suggestions contradicting team conventions, security warnings for patterns safe in your deployment context, and performance suggestions that would degrade your specific use case. You want to reduce false positives while maintaining the ability to catch genuine issues. Which approach best enables the model to generalize its judgment to novel code patterns it hasn't seen before?

- A. Implement post-processing that uses keyword matching to filter out findings containing terms like "convention," "context-dependent," or "trade-off."
- B. Add instructions to your system prompt to "be conservative," "only flag definite issues," and "consider that some patterns may be intentional."
- C. Include few-shot examples in your prompt showing annotated code snippets that distinguish acceptable patterns from genuine issues in each category. **(Marked answer)**
- D. Create a comprehensive written specification of all patterns that should not be flagged, then include this full documentation in the system prompt.

---

## Question 53 — Claude Code for Continuous Integration

Your automated review CI jobs take 18 seconds to initialize before Claude begins analyzing code. Profiling reveals the delay comes from auto-discovery of hooks, MCP servers, plugins, skills, and multiple nested CLAUDE.md files throughout your monorepo. You need to cut startup time while ensuring reviews still enforce your team's coding standards, which are documented in your root-level CLAUDE.md file. What is the most effective approach?

- A. Run with `--bare` mode and pass `--append-system-prompt-file ./CLAUDE.md` to explicitly load your project standards while skipping all auto-discovery.
- B. Keep the default initialization and add `--exclude-dynamic-system-prompt-sections` to reduce per-machine prompt variability and improve prompt cache hit rates across runners.
- C. Run with `--bare` mode and specify all review criteria directly in the `-p` prompt argument for each CI invocation, without referencing any external files.
- D. Replace the default prompt entirely using `--system-prompt-file ./CLAUDE.md`, which bypasses default prompt assembly and loads only your project rules. **(Marked answer)**

---

## Question 54 — Claude Code for Continuous Integration

Your pipeline includes a release notes generation step that classifies and summarizes approximately 200 commits at the end of each weekly release cycle. Each commit is currently sent as a separate Messages API call using a Sonnet-tier Claude model. The release notes aren't needed until the following morning (results have ~12 hours of acceptable latency). Your team needs to reduce per-token API cost for this step while keeping the same model and prompts (no change to model tier or output quality). Which approach satisfies all of these constraints?

- A. Switch the summarization calls from the Sonnet-tier model to a Haiku-tier model to take advantage of Haiku's lower per-token rates.
- B. Issue the 200 Messages API requests in parallel using concurrent connections, since concurrency lowers the per-token price charged by the API.
- C. Submit the 200 requests to the Message Batches API with unique custom_ids and retrieve results once the batch ends, which applies a 50% discount to all input and output tokens. **(Marked answer)**
- D. Concatenate all 200 commit messages into a single Messages API request and have the model return all summaries in one response, since fewer requests always reduces total token cost.

---

## Question 55 — Claude Code for Continuous Integration

The automated review consistently flags patterns your team uses intentionally — force-unwrapping optionals in test files, using large coordinator classes that follow your established architecture, and importing internally-maintained modules marked as deprecated in the public SDK. Developers are dismissing roughly 30% of all findings as project-specific false positives. Which approach prevents the model from generating these findings in the first place by supplying the project's conventions as persistent context on every review?

- A. Document the team's accepted patterns and intentional conventions in the project's CLAUDE.md file so the model receives this context during every review. **(Marked answer)**
- B. Build post-processing keyword filters that suppress findings containing terms like "force unwrap," "large class," or "deprecated import" before results reach developers.
- C. Have developers add inline suppress-comments at flagged lines and preprocess diffs to exclude suppressed lines before sending code to the model.
- D. Configure the review to analyze only the changed lines in the diff without surrounding file context, reducing the amount of code the model evaluates per review.

---

## Question 56 — Claude Code for Continuous Integration

During initial testing of the automated review pipeline, you notice that reviews on large PRs (50+ changed files) sometimes take over 20 minutes and cost $8-12 per run due to extensive agentic loops — Claude reads files, runs analysis tools, and iterates many times. Your team needs each invocation to abort once it reaches a fixed iteration count and a fixed dollar amount, enforced by Claude Code itself rather than the surrounding job runner. Which configuration change directly enforces both of those per-invocation caps?

- A. Set `timeout-minutes: 5` on the GitHub Actions job step and monitor per-run costs via the Anthropic Console usage dashboard.
- B. Add `--max-turns 10 --max-budget-usd 2.00` to the `claude -p` invocation to cap iterations and spend. **(Marked answer)**
- C. Set `--permission-mode dontAsk` to auto-deny any tool permission requests not in the explicitly allowed set.
- D. Switch the `--model` flag to a smaller, cheaper model so each iteration uses fewer tokens and lower per-call cost.

---

## Question 57 — Claude Code for Continuous Integration

You built an LLM-powered code review tool that analyzes pull requests and outputs structured findings. Each finding is a JSON object with `file_path`, `line_number`, `issue_category` (e.g., "Security", "Style"), and `description`. Developers can click "dismiss" on any finding they consider unhelpful—currently 35% of findings get dismissed. You want to analyze these dismissals to understand what your system is getting wrong and improve your prompts accordingly. What change to your output structure would best support this analysis?

- A. Add a `detected_pattern` field recording the code construct (e.g., "single-letter loop variable") that triggered each finding. **(Marked answer)**
- B. Add a `model_confidence` field (0.0-1.0) and filter out findings below a threshold calibrated against historical dismiss rates.
- C. Remove the `issue_category` field and track dismiss rates at the individual finding level only.
- D. Expand the `description` field to include more detailed explanations of why each issue matters and how to fix it.

---

## Question 58 — Claude Code for Continuous Integration

Your test generation produces unit tests for new code, but reviews show 55% are low-value: trivial assertions that only verify functions don't throw exceptions, tests duplicating existing coverage, or tests ignoring your team's fixture conventions. How do you reduce the rate of low-value tests being generated in the first place?

- A. Restrict test generation to directories where historical quality metrics show higher acceptance rates, disabling it for areas where generated tests consistently require heavy editing.
- B. Document testing standards in CLAUDE.md and include valuable test criteria, available fixtures with intended use cases, and examples distinguishing meaningful behavioral tests from trivial assertions. **(Marked answer)**
- C. Add post-generation coverage analysis that automatically filters out any generated test that doesn't increase line coverage beyond what existing tests provide.
- D. Implement a two-phase generation where a second Claude call scores each test against quality criteria, filtering out low-scoring tests before presenting results to developers.

---

## Question 59 — Claude Code for Continuous Integration

Your automated code review is missing genuine bugs in pull requests. Investigation reveals that your review prompt includes the instruction: "Only flag critical issues that would definitely cause production failures. Ignore minor concerns and anything you're uncertain about." Developers confirm that some missed bugs are real logic errors the model investigated but chose not to report. The team requires that review output remain structured (each finding tagged with metadata) and actionable, tagged output for downstream filtering. Which prompt change both removes the cause of the suppressed findings and preserves structured, tagged output for downstream filtering?

- A. Add a second review pass that re-reads the diff using the same prompt, looking for anything the first pass may have missed.
- B. Enable extended thinking and instruct the model to reason step-by-step about each code change before producing its review.
- C. Remove all severity-related instructions from the prompt and let the model use its default judgment about what to report.
- D. Instruct the model to report all findings with a confidence level and severity tag, deferring filtering to a downstream step. **(Marked answer)**

---

## Question 60 — Claude Code for Continuous Integration

Your pipeline reviews approximately 200 database migration scripts daily using the Message Batches API. Each batch request includes a shared 8,000-token system prompt containing migration guidelines and schema documentation, followed by the individual migration script. You've added `cache_control` breakpoints on the shared system prompt in every request, but monitoring shows cache hit rates of only 32%, with cache misses concentrated on requests processed later in the batch window. Which change will address the root cause of these cache misses without adding sequential processing latency?

- A. Add pre-warming requests with `max_tokens: 0` at the beginning of each batch to seed the cache before the review requests execute.
- B. Split the 200 requests into 10 sequential batches of 20, submitting each only after the previous completes, to keep requests temporally close enough for cache reuse. **(Marked answer)**
- C. Move the `cache_control` breakpoints from the system prompt to the individual migration script content to cache similar code patterns across reviews.
- D. Use the extended 1-hour cache TTL instead of the default 5-minute TTL on your cache breakpoints.

---

## Unnumbered Question (number cut off in photo) — Tool Use / Editing

*(Question stem partially visible)* …parameter cannot find unique text to match — the file has repetitive docstrings, variable names, and structural patterns. What's the most reliable way to complete this insertion?

- A. Use Read to load the file, add the function at the appropriate location, then Write the updated file. **(Marked answer)**
- B. Use Bash to append the function definition to the end of the file using heredoc syntax.
- C. Use Edit with an extremely long old_string capturing 30+ lines of context to guarantee uniqueness.
- D. *(option cut off in photo)*

<!-- generated by claude code on 2026-06-19 for CCA-F; review and edit -->
