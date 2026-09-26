# TASK-067 — adaptive multiscale and multi-validator onset experiment

Owner lead. Base a7d273ca6010c4b31d5a8c8533274c27d8c46897; branch
agent/boarding-multiscale; worktree /Users/cute/MosTransport2026Hack-worktrees/boarding-multiscale.

## Purpose / claim
On unchanged raw-selected vehicle windows, multiscale counts and adaptive temporal
and feature clustering should isolate pulses without a single15second shape.
Independent validator synchrony and cross-family agreement should exceed
rate-preserving controls and generalize from Jan-Apr to May-Oct. This claim can
fail; no agreement metric alone certifies doors or stop identity.

## Contract / scope
Source device_no and garage_number yield separate pseudonymous device/vehicle
keys; source timestamp precision is one second. Existing session_keys identity
conflict exclusions and same536ROI selection are preserved. Source immutable,
Europe/Moscow, no serving changes, labels remain experimental. Include small
5–6person bursts and variable tails in synthetic checks. No dependency changes.

## Acceptance / verification
Compare2/3/5/10s scales and longer tails, HDBSCAN variable-density time clustering,
GMM on multiscale shape features with BIC train-only selection, synchrony and
cross-family consensus. Calibrate numeric scores on train-only randomized controls;
report actual held-out null rates, temporal/route slices, tolerance sensitivity,
and20%payment thinning. Device-independent shifts retain individual device pulses;
uniform randomization within5min retains device/bin counts. Record hyperparameters
rather than claim parameter-free methods. Synthetic ground truth includes variable
boarding count, crowd-dependent long tails and1.5sdevicequeue assumption only.
Focused tests cover mass, precision/time bounds, permutation and shift controls,
chronology, consensus one-vote-per-family. Parent runs make check, integrates
verified patch preserving primary uncommitted work, retains isolated artifacts.

## Evidence
Existing dense_experiment selection, burst_detection.match_onsets and audit.py
source normalization provide contracts. Consumers searched: new offline modules
only. sklearn HDBSCAN (stable docs) supports varying densities without global eps;
GaussianMixture/BIC (official model selection example) supplies unsupervised feature
clustering. Both exist in installed sklearn1.9.1. No expensive irreversible design.

## Progress
Read task, architecture, tracker, permissions and ML rules; research complete.
Read-only subagent audits validator identity and synchrony; lead owns all files.


## Completion / recovery
All20variants completed on frozen536windows. Fit Jan-Apr216windows, held-out
May-Oct320windows. Feature mixture parameters and thresholds repeated identically;
independent one-worker evaluation equals four-worker result. Parent make check
passed1,137tests with48SQLskipped; static/build/golden/Compose passed. Independent
review correction queued all synthetic events per device, now tested. Full results,
limitations and acceptance evidence live in docs/analysis/2026-09-26-multiscale-onsets.

Prototype is retained as an offline experiment, not a promoted stop label source.
Adoption requires future-date sequence/anchor validation; TASK063 accuracy gate
remains open. Recovery is removal/reversion of these isolated modules; existing
reconstruction and immutable payments remain unchanged. Integration by verified
patch preserving existing primary edits; worktree retained for ignored artifacts.
