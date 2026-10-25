# Archive

`test-2r-before-hardening.json` is the first 5-block run, made before the simulator was hardened. Gemini 4 Argon took the score from 50 to 98.4 in one round by exploiting a lenient judge and telling guests to "state a compromise". It's kept as evidence of the reward hacking. See docs/FEEDBACK.md.

`demo-5block-before-hardening-2.json` is the second exploit (34.9 → 99.6, all guests 10/10). Argon pre-wrote the whole compact into a 600-word closing-plenary prompt, and the Flash delegates just endorsed it. Fix: prompts capped at 60 words, drafts are contested per red lines, mandatory pushback, and a skeptical Flash judge that asks what each guest conceded.
