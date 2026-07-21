# V6 Stop Building, Begin Runs

V6 completes the directional correction. The next action is the ADE20K dry-run.
Do not build V7.

Generic infrastructure work is disallowed after V6. Allowed future coding only
if real execution exposes one of these blockers:
- run crashes
- gate missing
- artifact contract mismatch
- edit generation fails
- detectability pipeline missing field
- VLM output parser fails

Otherwise, run:
1. ADE20K dry-run
2. bounded 20-edit diffusion pilot
3. edit detectability
4. tiny-pilot go/no-go
5. human review and item certificates
6. first open-VLM eval only after gates pass

No evidence claims are made at this stage.
