# Demo 01 - Basic: a deliberately buggy token vault

This demo runs FORKFUZZ against `vault.json`, a tiny contract spec
modeling a deposit/withdraw vault with a buggy `transfer` function.

## The spec

State:
- `total` - total tokens held by the vault
- `alice`, `bob` - per-user balances

Functions:
- `deposit(amount)` - adds tokens to `alice` and to `total` (guarded `amount > 0`)
- `withdraw(amount)` - removes tokens from `alice` and `total`
  (guarded `amount > 0 and amount <= alice`)
- `transfer(amount)` - moves `amount` from `alice` to `bob` **but only checks
  `amount > 0`, not `amount <= alice`** -- the planted bug.

Invariants (must always hold):
1. `solvent`: `total == alice + bob` (vault accounting must balance)
2. `non_negative`: `alice >= 0 and bob >= 0` (no negative balances)

## What to expect

The buggy `transfer` lets `alice` go negative (it never checks she has
enough), which also breaks the `solvent` accounting once compared against
`total`. FORKFUZZ should find a short counterexample and shrink it.

## Run it

```
python -m forkfuzz check demos/01-basic/vault.json
```

Expected: a non-zero exit code and a `[BROKEN] non_negative` (and/or
`solvent`) finding with a minimal counterexample such as:

```
1. transfer(amount=...)
```

because a single `transfer` larger than `alice`'s balance (starting at 0)
immediately drives `alice` negative.

JSON output for CI:

```
python -m forkfuzz check demos/01-basic/vault.json --format json
```
