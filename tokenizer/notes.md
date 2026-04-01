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

---

## Tokenizer training vs. model training

**Q: Can you train BPE incrementally, streaming through the corpus one document at a time?**

A: No. BPE needs global pair frequency counts before making any merge decision. You must have access to the full corpus upfront to know which pair is most frequent. There is no principled way to make merge decisions incrementally.

**Q: So tokenizer training and model training are completely separate phases?**

A: Yes. BPE tokenizer training is a one-time, offline preprocessing step. The resulting merge rules are then frozen and used to tokenize all future data.

| | Tokenizer training | Model training |
|---|---|---|
| Data access | Full corpus, random access | Streaming OK |
| Run frequency | Once, frozen forever | Iterated over many epochs |
| Corpus size | Can be a curated sample | As large as possible |

**Q: What happens if `max_vocab_size` is set too large for the corpus?**

A: BPE terminates early — once no pair appears more than once, there is nothing left to merge. You end up with long substring tokens covering the corpus, which is useless. Vocab size must be chosen relative to corpus size; typical values (32k–100k) require a large, diverse corpus.

---

## Special tokens

**Q: Do we need to insert `<|endoftext|>` when training the tokenizer?**

A: No. BPE only needs raw text to count pair frequencies — document boundaries are irrelevant. Special tokens are only needed during LLM pre-training, where documents are packed end-to-end and boundaries must be marked.

**Q: So how does the tokenizer know to treat `<|endoftext|>` as a single token and never split it?**

A: Special tokens are manually appended to the vocabulary *after* BPE training. A regex pre-tokenization step then matches and splits them out before BPE runs, so they are always treated as indivisible units. BPE merge rules never touch them.

The vocabulary therefore has two distinct parts:
- **Learned vocab:** initial characters/bytes + all merged subword tokens from BPE
- **Special tokens:** `<|endoftext|>`, `<|pad|>`, `<|user|>`, etc. — appended afterward, atomic by definition

---

## Why documents are concatenated during pre-training

**Q: Why not feed each document separately to the model during pre-training?**

A: GPU utilization. Neural network training requires fixed-length batches. A 200-token document in a 2048-token context window wastes 1848 positions on padding — compute spent on nothing. By packing documents end-to-end and chopping into fixed-length chunks, every token position carries real gradient signal.

**Q: But doesn't that corrupt the model — training it to predict across document boundaries?**

A: Yes, which is why `<|endoftext|>` is inserted at each boundary. The model learns to treat it as a hard reset. A cleaner but more expensive alternative is to mask attention across document boundaries:

| Approach | GPU utilization | Cross-doc contamination |
|---|---|---|
| Feed separately with padding | Poor | None |
| Concatenate + `<|endoftext|>` | Full | Model learns to ignore boundary |
| Concatenate + masked attention | Full | None |

Most large-scale pre-training (GPT, LLaMA) uses the middle approach.

---

## Pre-tokenization

**Q: How do we split text into units before BPE runs? Naive space-splitting seems fragile.**

A: A hand-crafted **regex pre-tokenization step** splits text into chunks before BPE sees it. BPE merges only happen *within* each chunk, never across them — this prevents tokens from spanning what should be word boundaries.

**Q: What does GPT-2's regex actually capture?**

A: It splits on:
- Contractions: `'s`, `'t`, `'re`, ...
- Words with an optional **leading space attached** (` hello` is one chunk, not `" "` + `"hello"`)
- Numbers
- Punctuation / symbol runs
- Whitespace runs

Attaching the leading space to the following word means the vocabulary distinguishes `"hello"` (start of text) from `" hello"` (mid-sentence). This is why GPT-2's vocabulary has the `Ġ` prefix on many tokens.

**Q: What about languages without spaces, or code, or ASCII art?**

A: This is the core limitation. Pre-tokenization rules embed assumptions about what a "word" is and behave poorly on languages like Chinese, Japanese, or Thai, and on edge cases like ASCII art or dense code. Newer tokenizers (tiktoken's cl100k) use more sophisticated regex patterns; some research explores *learning* pre-tokenization rules rather than hand-crafting them.

**Q: How does GPT-2 handle rare Unicode characters or unseen scripts without an OOV problem?**

A: By operating on **bytes**, not characters. The base vocabulary is the 256 possible byte values, guaranteeing any Unicode text is representable. BPE then merges bytes into longer subword sequences. This is called byte-level BPE.
