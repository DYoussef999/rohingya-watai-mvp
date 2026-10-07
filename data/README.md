# data/

Everything in here except this file is gitignored. **Never commit recordings of people.**

Suggested layout:

```
data/
  raw/<speaker_id>/<clip_id>.wav     original recordings, read-only
  clips.csv                          one row per clip (see below)
  splits/train.txt, dev.txt, test.txt
```

`clips.csv` columns: `clip_id, speaker_id, path, duration_s, english, rohingyalish, hanifi, dialect_region, consent_id`.

Rules:
- Every clip has a `consent_id` pointing to documented informed consent (purpose, storage, right to withdraw).
- Speaker IDs are pseudonymous. No names, phone numbers or locations finer than region.
- A speaker's clips all go in the same split, so the test set measures new voices.
- The test split is fixed and never used for training.
