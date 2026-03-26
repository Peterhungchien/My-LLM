# Tokenizer — Conceptual Foundation

## Why do we need a tokenizer?

Neural networks operate in Euclidean space (R^N). Text lives in a discrete symbolic space. The tokenizer bridges this gap:

```
text → sequence of integers → (embedding layer) → vectors in R^N
```

The tokenizer's job is specifically: **text → sequence of integers**.

---

## Tokenization strategies and their tradeoffs

### Character-level
- Vocabulary is tiny (e.g. ~100 unicode bytes)
- No out-of-vocabulary (OOV) problem
- **Problem:** Sequences are D× longer (D = avg word length ≈ 5–6)
  - Attention is O(n²), so this is D²≈ 25–36× more expensive
  - More critically: a fixed context window fits D× fewer *words*, degrading the model's ability to reason over long-range context

### Word-level
- Efficient context usage — one token per word
- **Problem 1:** Vocabulary explodes (hundreds of thousands of words + morphological variants + proper nouns + technical terms)
  - Embedding matrix is `vocab_size × embedding_dim`
  - Output projection requires softmax over all vocab entries — huge per-token cost
- **Problem 2:** OOV — unseen words can't be represented at all

### Subword (the sweet spot)
Common words get their own token; rare/unknown words are broken into subword pieces. Balances vocabulary size, context efficiency, and OOV robustness.

---

## Byte Pair Encoding (BPE)

The standard algorithm for automatically learning a subword vocabulary from a corpus.

### Algorithm

1. **Initialize:** start with a vocabulary of all individual characters (or bytes). This guarantees any text can be represented.
2. **Count:** scan the corpus and count the frequency of every adjacent token pair.
3. **Merge:** take the most frequent pair and merge it into a single new token. Add it to the vocabulary.
4. **Repeat:** rescan and recount with the updated tokenization. Repeat until the vocabulary reaches a target size (a chosen hyperparameter).

### Key insight
The vocabulary is *learned* from data — frequent subwords naturally get promoted. No hand-crafted word list needed.

---

## "Merge everywhere" — what it means

After selecting the top pair (e.g. `"e"` + `"r"`), you must rewrite every occurrence of that adjacent pair in the corpus to the single token `"er"` before the next iteration. For example, `["k", "e", "r"]` becomes `["k", "er"]`.

**Why this is necessary:** if you don't update the corpus, pair counts become inconsistent. `"ker"` would count as both `("k","e")` and `("k","er")` simultaneously — double counting. Longer sequences would suffer cascading inflation, and the vocabulary would stall at very short tokens.

**The invariant:** at every iteration, the corpus tokenization must be consistent with the current vocabulary.

---

## Open question (next to explore)

Naive BPE is expensive: each iteration scans the full corpus to recount pairs and rewrites all occurrences — O(corpus size) per merge, repeated thousands of times.

**Question:** what could you precompute or cache to avoid rescanning the entire corpus from scratch each iteration?
