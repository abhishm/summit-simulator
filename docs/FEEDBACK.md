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
- `high` thinking on a long structured-output prompt takes minutes. There's no progress signal without streaming, and we wanted thought-summary streaming combined with structured output.

## What I wish existed

- Streaming thought summaries during structured-output calls, so the UI can show "Argon is considering…" live.
- A first-class way to run N cheap Flash "worlds" in parallel and have Argon read their aggregate, like a managed simulation agent.
