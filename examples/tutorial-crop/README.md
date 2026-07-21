# TeXFrog Tutorial: Segment Cropping

> [!NOTE]
> **Package:** This tutorial uses [`algpseudocodex`](https://ctan.org/pkg/algpseudocodex).
> Cropping needs a *line-based* pseudocode body (`algpseudocodex` or `nicodemus`);
> it is effectively unsupported for `cryptocode`, whose lines live inside the
> brace argument of `\procedure{…}{…}`. See the note in
> [writing-proofs.md](../../docs/writing-proofs.md#cropping-long-listings).

For a proof with many hops, a diffed render of a later game is mostly lines
carried over unchanged from earlier games. **Segment cropping** marks boundaries
in the source so a diffed `\tfrendergame` shows only the segments that actually
changed, collapsing every unchanged segment into a single stub line such as
_[Setup unchanged]_.

This example is the smallest proof that shows the feature paying off: a five-step
IND-CPA game for a KEM/DEM hybrid where **each hop changes exactly one line, in
one segment**, of an otherwise identical listing.

## The Proof Scenario

**Scheme.** Hybrid public-key encryption of a message `m`:

```
Encaps(pk) -> (c1, K)            # KEM: ciphertext + shared key
pad <- PRF(K, r)                 # derive a one-time pad for fresh nonce r
send (c1, r, pad XOR m)          # DEM: one-time-pad the message
```

**Theorem.** The hybrid scheme is IND-CPA secure if the KEM is IND-CPA secure
and `PRF` is a secure pseudorandom function.

**Proof.** Via a four-hop game sequence. Each row below changes one line:

| Game | Segment touched | What changes |
|------|-----------------|--------------|
| G0 | — | Real IND-CPA game: `(c1,K) <- Encaps`, `pad <- PRF(K,r)`, `c2 <- pad XOR m_b` |
| G1 | Encapsulation | `K <-$ K` sampled uniformly (KEM IND-CPA) |
| G2 | Key derivation | `pad <- RF(r)` (PRF replaced by a random function) |
| G3 | Key derivation | `pad <-$ {0,1}^ℓ` (fresh nonce ⇒ perfect rewrite) |
| G4 | DEM | `c2 <-$ {0,1}^ℓ` (ciphertext independent of `m_b`) |

## How Cropping Is Set Up

Three ingredients, all in `main.tex`:

1. **`\tfcropdefault{on}`** in the preamble turns cropping on document-wide, so
   every diffed `\tfrendergame` crops unless a per-call `crop=` overrides it.
2. **`\tfsegment{Caption}`** markers split the `tfsource` body. Because the game
   is written as a flat sequence of `\State` lines (no `\Procedure` wrapper),
   every marker sits at **block depth 0** — the placement cropping requires. The
   four markers are `Setup`, `Encapsulation`, `Key derivation`, and `DEM`.
3. Clean, no-`diff` renders are **never** cropped: `\tfrendergame{kemdem}{G0}`
   shows the full listing regardless of the default.

**What is pinned vs. what crops.** Only two pieces are always kept, since they
anchor a balanced, compilable environment: **segment 0** (the `algorithmic`
opener plus the game header) and the **final segment** (the bare
`\end{algorithmic}` closer). Every content segment in between — `Setup`,
`Encapsulation`, `Key derivation`, and `DEM` — collapses to a stub in any diffed
render where it did not change. In `G4` (which changes only `DEM`), the other
three collapse at once.

## PDF-only `crop=off`

The last figure re-renders the `G3 -> G4` hop with `\tfrendergame[diff=G3,
crop=off]{kemdem}{G4}` to force a full listing for that one call.

> [!IMPORTANT]
> The `crop=` key is **PDF-only**. The HTML viewer compiles one SVG per game and
> is governed **solely** by `\tfcropdefault`; it ignores per-call `crop=`. If you
> set `crop=off` (or `crop=on`) on a single call, the PDF and the HTML viewer
> will show that game differently.

## Files in This Directory

| File | Purpose |
|------|---------|
| `main.tex` | Single source: games, `\tfsegment` markers, `\tfcropdefault{on}`, render calls |
| `macros.tex` | Short macro definitions (no external dependencies) |
| `commentary/*.tex` | Per-game prose pulled in by `\tfcommentary` |

## Build It

```bash
# PDF (cropped renders + the crop=off comparison figure)
latexmk -pdf main.tex        # needs texfrog.sty on TEXINPUTS

# HTML site (cropping governed by \tfcropdefault only)
texfrog html build main.tex -o /tmp/tfcrop
texfrog html serve main.tex -o /tmp/tfcrop
```

## Next Steps

- [Writing a proof § Cropping Long Listings](../../docs/writing-proofs.md#cropping-long-listings) — full reference for `\tfsegment`, `\tfcropdefault`, `\tfsegmentstub`, and the `crop=` key
- [tutorial-algpseudocodex/](../tutorial-algpseudocodex/) — the same `algpseudocodex` syntax without cropping
