# Local Corpus Fingerprint Validation

Date: 2026-03-22
Task: `P13-I003`

## Scope

Validate the new local corpus fingerprint sampler against the real `bio-agent-lab` mirrors without
collapsing present, partial, and missing sources together.

## Real Mirror Results

- Total cataloged local sources: `39`
- Present sources: `29`
- Partial sources: `2`
- Missing sources: `8`
- Sampled files across present/partial sources: `101`

## Real Checks Exercised

- `uniprot` stayed `partial` and sampled `uniprot_sprot.dat.gz`
- `reactome` stayed `present` and sampled `UniProt2Reactome_All_Levels.txt`
- `biolip` stayed `present` and sampled `BioLiP.txt`
- `pdbbind_pp` stayed `present`
- `pdbbind_pl` stayed `partial`
- `biogrid` stayed `missing` with zero sampled files

## Outcome

The sampler is behaving conservatively on the actual local mirror tree:

- present roots yield real sampled files and stable fingerprints
- partial roots remain partial instead of being promoted to complete
- missing roots remain explicit and do not generate fake samples

## Commands Run

- `python -m pytest tests\integration\test_local_corpus_sampler.py -q`
- `python -m ruff check tests\integration\test_local_corpus_sampler.py`
