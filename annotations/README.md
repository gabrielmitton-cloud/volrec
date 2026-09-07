# Annotations

LLM-written prose about specific `(date, ticker)` observations, each claim
citing the source it came from. Written to make the write-up interesting:
*"here are the largest IV moves in the sample, and here is what the filings and
the media said next to each."*

## The line that must not be crossed

**Nothing in this directory may become a numeric feature in any model.**

The moment an annotation becomes a regressor, the study has an unvalidated,
LLM-generated, look-ahead-prone variable estimated on roughly six independent
observations. It will find something. It will not be real.

A media or attention variable may enter a model only if **both** hold:

1. it is a pre-specified series built and validated by someone else - EMV, EPU,
   a COT positioning percentile, Wikipedia pageviews - not something generated
   here, and
2. it has been tested on the long sample (`samples/long/`) first.

## Licence

Never commit raw article text. Benzinga content via Alpaca is licensed, Arctic
Shift is licence "other", FNSPID is CC BY-NC-4.0. **Derived counts, scores and
short quotations with attribution only.** Annotations may quote a headline; they
may not reproduce an article.
