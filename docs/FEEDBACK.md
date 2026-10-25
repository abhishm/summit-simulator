# Argon feedback log

A running log for the submission form question "Do you have any feedback for the Google DeepMind team on Argon?"

## What worked

- First-try success: a plain `gemini-4-argon` call took about 5s, and the Antigravity agent on Argon provisioned a sandbox, ran code and answered in about 22s. No setup was needed beyond an API key.
- `steps` (`code_execution_call` → `code_execution_result` → `model_output`) makes the agent's actions easy to inspect.

- Argon as an optimizer: given a scored simulation transcript, it produces precise diagnoses that cite exact numbers (word counts, pair coverage, which guest was least heard). Its structured `Plan` output validated against our Pydantic JSON schema every time.
- Chaining critique rounds with `previous_interaction_id` worked well. Argon remembered what it tried before and kept what worked.
- Deep Research ran 10 parallel background jobs; all finished in about 15 min with cited role briefs.

## What broke / friction

- Argon is *too good* at reward hacking a simulator. In round 2 it reordered speaker lists to manipulate the airtime Gini and told guests to "state a mid-spectrum stance". We had to harden the environment. A built-in "spec-gaming check" or critique mode would help.
- The Antigravity packet agent gamed our first keyword-based verifier with templated openings ("As X, I propose…" with a red-line keyword pasted in). Openings had to be grounded per counterpart and checked for template reuse.
- Argon as a *visual* critic is sharp on real issues (power imbalance, faction-clustered seating), but at first it also critiqued renderer artifacts (an intentionally empty Lounge, seat order that the plan can't control). We had to add venue rules to the prompt. Its 0–10 score is coarse and plateaus at about 6.5 for any reasonable plan, so per-flaw verification ("did last round's fix land on the new render?") turned out to be far more useful than the score.
- `high` thinking on a long structured-output prompt takes minutes. There's no progress signal without streaming, and we wanted thought-summary streaming combined with structured output.

## What I wish existed

- A built-in "verify the previous critique" mode for multimodal critics: send the before/after images plus the earlier flaws and get structured fixed/open verdicts back.

- Streaming thought summaries during structured-output calls, so the UI can show "Argon is considering…" live.
- A first-class way to run N cheap Flash "worlds" in parallel and have Argon read their aggregate, like a managed simulation agent.
