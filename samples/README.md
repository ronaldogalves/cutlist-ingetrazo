# Sample models

Real furniture models used to design and check part detection (M0) and
the cut list (M1), and later to benchmark the packer (M2).

- `samples/` — models that may be public. Each `<name>.skp` may come with
  `<name>.opencutlist.csv` (OpenCutList's cut list export for the same
  model) and, for M2, OpenCutList's cutting-diagram PDF.
- `samples/private/` — clients' or personal models that must not be
  published. **Git-ignored**: they stay on the developer's machines
  (OneDrive) and never reach GitHub.

Once a sample becomes an automated test, a small copy goes to
`tests/fixtures/`.
