# Sieve demo video

This folder contains the production package for the 2:50 Build Week demo. It
uses only locally generated Sieve output, the repository source, and the local
interactive replay. No API request is made while rendering the visual cut.

## Produce the evidence

From the repository root, generate a fresh, deterministic audit. Choose a new
directory name if this one already exists; never overwrite an earlier audit.

```powershell
python -m sieve run-suite --runs-dir runs/demo-video-audit --report-path docs/demo-video/artifacts/sieve-audit.html
```

The expected completion summary is `baselines=5`, `perturbed=15`, and
`scores=15`. The checked-in workflow deliberately uses this recorded backend;
it is not a `--live` GPT-5.6 run.

## Render the visual cut

```powershell
node tools/record_demo_video.mjs
```

This builds the replay, records the ten scripted 16:9 shots, and writes the
silent visual master to `docs/demo-video/output/sieve-demo-visual.webm`. The
burned-in labels call out structured rationale, intervention, patch
divergence, and test stability. The script also keeps the short source clips,
which makes a last-minute replacement easy.

## Add the human narration

Record the exact text in [narration.md](narration.md), paced against
[captions.srt](captions.srt). Use one clear human voice and no music. Export
one approximately 168-second WAV (or adjust the final visual hold to match the spoken track),
then mux it without re-encoding the video:

```powershell
$ffmpeg = "$env:LOCALAPPDATA\ms-playwright\ffmpeg-1011\ffmpeg-win64.exe"
& $ffmpeg -y -i docs/demo-video/output/sieve-demo-visual.webm -i voiceover.wav -c:v copy -c:a libopus -shortest docs/demo-video/output/sieve-demo-final.webm
```

The final human recording and public YouTube upload are intentionally manual:
they require the presenter's voice and account. Before submitting, view the
public link in an incognito window and verify it is under three minutes.

## Accuracy checklist

- The command shown in the terminal uses the deterministic recorded backend.
- `--live` is described only as a manual, credential-protected GPT-5.6 mode.
- `SIEVE-T3 / INT-02` is the constraint-sensitive example (0.025 divergence,
  original acceptance test broke).
- `SIEVE-T1 / INT-01` is the claim-insensitive example (0.000 divergence,
  stable passing tests).
- The replay is described as local/replay-only: no code execution, changed
  evidence, upload transmission, or model/API request.
