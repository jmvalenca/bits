---
title: Claude
marimo-version: 0.23.14
---

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Research implementation of cryptographic primitives: Oblivious Transfer (OT) protocols, Vector Oblivious Linear Evaluation (VOLE), and Multi-Party Computation (MPC). Files are both runnable marimo interactive notebooks and importable Python modules.

## Commands

```bash
# Run tests for a specific module
pytest test_bits.py -v
pytest test_ots.py -v
pytest test_vole.py -v
pytest test_mpc.py -v

# Run a single test
pytest test_mpc.py::Test_Circuit::test_evals_evalp -v

# Launch as interactive marimo notebook
marimo run bits.py
marimo edit ots.py
```

Dependencies are declared as PEP 735 inline script metadata at the top of each file (`# /// script` blocks). `bits.py` and `mpc.py` require Python >= 3.13; `ots.py` and `vole.py` require >= 3.14. Key packages: `numpy`, `galois==0.4.10`, `marimo>=0.23.4`.

## Architecture

Each `.py` file is a self-contained marimo notebook and importable module. Tests live in separate files (`test_bits.py`, `test_ots.py`, `test_vole.py`, `test_mpc.py`).

**Dependency order:** `config.py` → `bits.py` → `ots.py` / `vole.py` → `mpc.py`

### `bits.py` — Core abstraction

`bits` subclasses `numpy.ndarray` to implement binary field arithmetic:
- Addition = XOR, multiplication = AND, `@` = binary matrix multiply
- `bits_sampler(seed)`: generates random `secrets(n)`, `noise(l, eps)` (Bernoulli), and structured `eta(l, cut)` values
- `bits_crs(key)`: Common Reference String — `AU(tweak, l, n)` derives matrix `A` (shape `l×n`) and vector `U` (length `l`) from a SHAKE-256 key

### `config.py` — Protocol parameters

Dataclasses that bundle all protocol parameters in one place:
- `config`: main params — `gamma`, `tsize`, `N`, `n`, `l`, `n_iters`, `eps`, `cut`, Reed-Solomon `n_ecc`/`k_ecc`
- `config_VOLE`: `x_size`, `t_size`, `n_tags`
- `config_NP`: `N`, `msize`, `ksize`, `ntags`
- `config_MPC`: `parties`, `rsize`, `csize`, `rounds`, `ksize`, `wsize`, `iosize`, `sessions`

### `ots.py` — Oblivious Transfer protocols

Factory functions that return a `__main__` class encapsulating `Provider`/`Receiver` inner classes:
- `one_of_two_ot()` — LPN-based 1-of-2 OT; uses Reed-Solomon repetition codes and `byte_round()` for decoding
- `one_of_all_ot()` — Naor-Pinkas 1-of-N OT; internally composes `l` instances of `one_of_two_ot()`
- `all_but_one_ot()` — All-but-one OT by secret sharing; receiver learns all messages except one index

Protocol pattern: `Provider` and `Receiver` exchange messages; `__main__` orchestrates the full execution via `get(b)`.

### `vole.py` — Vector OLE

- `POL(n_tags, key, tweak)`: polynomial over `bits`; `e_value(x, y)` evaluates at `(x, y)`; `a_values(x, m)` returns first- and second-order terms for consistency checking
- `VOLE_dv()`: factory returning `Prover`/`Verifier` — designated-verifier VOLE. After the protocol: `qs[i] = tags[i] + b_i * delta` for each bit `b_i` of `x`

### `mpc.py` — ITH MPC (MPC-in-the-Head)

- `RNG(key)`: correlated randomness; `.rho` gives per-party independent wires; `.scr` gives ring-correlated values summing to zero; `.encaps` gives per-party `[scr[i], scr[i-1]]` pairs
- `message`: `@dataclass` with fields `rho: bits`, `mu: bits`
- `view`: `@dataclass` with fields `start: list`, `messages: list`
- `share(bits)`: one party's wire view; construction modes: `share(w)` (trivial), `share(w, encap=...)` (masked), `share(view_i, view_j)` (reconstruct + verify); `multiply(other, msg)` uses a preprocessed `message`
- `shares(bits)`: all parties' shares of one wire plus public mask `tau`; `multiply(other, rng)` runs Araki et al. multiplication triple
- `SBox(shape, master)`: non-linear layer; selects random input-pair combinations; `eval`/`evalp`/`evals` for plaintext/per-party/shared evaluation
- `Permutation(master)`: mixing layer; composes two `SBox` instances for `rounds` iterations
- `Circuit(key)`: sponge-based construction; `eval`/`evalp`/`evals` for full circuit evaluation
- `Inputs(source)`: formats byte input into `(blocs, rsize, wsize)` array for circuit ingestion
- `Data(key, secret)`: prover's key material; builds `rate` and `capacity` as `shares` start states
- `mpcITH()`: ITH protocol factory with `KeyGen`, `Prover`, `Verifier` inner classes; `__main__.run()` loops `sessions` Commit→Challenge→Prove→Verify rounds

## Key Conventions

- Protocols are written as nested classes inside factory functions so each call produces fresh, independent instances.
- Tests live in separate `test_*.py` files as `unittest.TestCase` subclasses; `test_mpc.py` uses cell-scoped classes via `@app.cell`.
- The `olds/` directory keeps prior implementations for reference — do not modify them.
