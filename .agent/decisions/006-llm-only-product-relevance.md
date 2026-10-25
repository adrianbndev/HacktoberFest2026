# ADR-006: LLM-only product relevance for `/analyze`

* **Status:** Accepted (Level 1 / MOD-04)
* **Date:** 2026-10-25
* **Owners:** Track C (Matías) with Track B error copy
* **Supersedes:** the deep-path use of `score_relevance` and the `all_usable`
  fallback described in ADR-003/ADR-004. `/valuate` is untouched.

## Context

The deep analysis (`POST /api/market/analyze`) collects real listings from eBay,
Wallapop and Milanuncios. Before this decision it applied two deterministic
product filters before pricing:

1. `filter_usable_listings` dropped accessories/broken listings by title
   markers before they ever left the source adapter.
2. `score_relevance` kept listings that shared model/brand tokens and, when it
   rejected everything, `aggregate_results` fell back to the full sample.

Those rules are cheap but blunt: they cannot tell “AirPods Pro 2” from “AirPods
Pro”, a generation number from a capacity, or a complete unit from “con
estuche”. They also silently priced the whole sample when they found nothing,
which is the opposite of a trustworthy valuation.

The product decision for the Hacktoberfest demo is that **the LLM decides what
is the exact product**, and the price range is always built from real prices of
the accepted listings. No deterministic relevance in the deep path, no fallback
to the full sample.

## Decisions

### 1. No product prefilter in `/analyze`

Source adapters apply only technical sanitisation: visible title, finite price
`> 0` (and below `MARKET_MAX_LISTING_PRICE_EUR`) and de-duplication by
platform/title/price. Accessories, broken units, single earbuds and bundles are
sent to DeepSeek; they are not discarded by a keyword list. The Milanuncios
HTTP-vs-browser decision keeps using this sanitised count (it is a transport
heuristic, not a product filter).

### 2. DeepSeek is the relevance judge

`LlmRelevanceFilter` uses `DeepSeekChat` with `deepseek-flash`, thinking
disabled and `response_format=json_object`. Listings are classified in batches
of `MARKET_LLM_RELEVANCE_BATCH_SIZE` (default 25) with a strict Spanish prompt
that includes the target (`name`, `brand`, `model`, `category`, `description`,
condition) and each listing (`id`, `title`, `price`, `condition`).

Allowed labels: `exact`, `different_model`, `accessory`, `single_item`,
`broken`, `unrelated`, `bundle`. Only `exact` is accepted. The prompt carries
explicit AirPods-Pro-2 examples (accepted models/generations and rejected
different models, single side, broken, case/box, accessories and bundles) and
defaults to `different_model` when the model is unsure.

Responses are validated with Pydantic. Missing ids, hallucinated ids and
unknown labels are treated as **not exact**; they never fail the batch. A batch
whose JSON/transport fails fails the whole analysis — no silent subset.

### 3. Prices come from the accepted listings, never from the LLM

`aggregate_results` receives the accepted listings and runs the existing single
IQR pass, percentiles and `W_health` weight. The LLM only classifies; it never
generates `priceMin`, `priceAvg` or `priceMax`. The optional recommendation is
still clamped to the resulting range.

### 4. Failure is explicit: 503, never the full sample

| Situation | Detail |
|---|---|
| `MARKET_LLM_RELEVANCE_ENABLED=false` | `llm_relevance_disabled` |
| DeepSeek unavailable (no key, transport/JSON error) | `llm_relevance_unavailable` |
| Budget/deadline exhausted | `llm_relevance_timeout` |
| Every listing rejected (`accepted` empty) | `llm_relevance_empty` |

All four return HTTP `503` with the per-source statuses; `/analyze` never falls
back to lexical relevance or to `all_usable`. If no source produced a sanitised
listing at all, the existing `Ninguna fuente…` 503 is kept.

### 5. `/valuate` stays frozen

The fast 2.8 s path keeps `score_relevance`, `filter_usable_listings` and the
deterministic catalog fallback. This ADR changes only the deep path.

## Consequences

- A missing/invalid DeepSeek key now disables `/analyze` (503), by design. The
  demo environment must inject `DEEPSEEK_API_KEY`.
- Listing titles (and the request description) are sent to DeepSeek for
  classification. Delimiting is JSON-based; prompt-injection hardening and
  redaction remain backlog items.
- Classification adds one LLM round per batch (concurrent, 10 s budget by
  default). A 3-source run normally needs 1–5 batches; the full-analysis
  deadline is unchanged (60 s).
- `source_result` keeps the sanitised per-source count/listings; `valuation`
  (`sampleSize`, `platforms`) and `comparableListings` contain only accepted
  `exact` listings. A warning reports how many listings DeepSeek discarded.
- Cached results keep the new semantics; old cache rows expire within the 15
  minute TTL.
