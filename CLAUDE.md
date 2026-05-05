# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Research implementation of cryptographic primitives: Oblivious Transfer (OT) protocols, Vector Oblivious Linear Evaluation (VOLE), and Multi-Party Computation (MPC). Files are both runnable marimo interactive notebooks and importable Python modules.

## Commands

```bash
# Run tests for a specific module
pytest bits.py -v
pytest ots.py -v
pytest vole.py -v
pytest mpc.py -v

# Run a single test
pytest mpc.py::Test_MPC::test_circuit -v

# Launch as interactive marimo notebook
marimo run bits.py
marimo edit ots.py
```

Dependencies are declared as PEP 735 inline script metadata at the top of each file (`# /// script` blocks). Python >= 3.13 required. Key packages: `numpy`, `galois==0.4.10`, `marimo>=0.23.2`.

## Architecture

Each `.py` file is a self-contained marimo notebook module with its own `unittest.TestCase` subclass at the bottom.

**Dependency order:** `bits.py` → `config.py` → `ots.py` / `vole.py` → `mpc.py`

### `bits.py` — Core abstraction

`bits` subclasses `numpy.ndarray` to implement binary field arithmetic:
- Addition = XOR, multiplication = AND, `@` = binary matrix multiply
- `bits_sampler`: generates random secrets, noise (with ε probability), and structured η values
- `bits_crs`: Common Reference String — produces random matrix `A` and vector `U` from a seed/tweak via SHAKE-256

### `config.py` — Protocol parameters

Dataclasses (`config`, `config_VOLE`, `config_NP`, `config_MPC`) that bundle all protocol parameters (γ, n, N, ε, cut, l, ECC codes, rounds) in one place. All protocols take a config instance.

### `ots.py` — Oblivious Transfer protocols

Factory functions that return nested `Provider`/`Receiver` class pairs:
- `one_of_two_bytes_OT()` — basic 1-of-2 OT
- `one_of_N_OT()` — 1-of-N via binary tree reduction over 1-of-2 OTs
- `one_of_N_noreduct_OT()` — direct 1-of-N (Naor-Pinkas style, uses Reed-Solomon via `galois`)
- `N_1_of_N_OT()` — N parallel 1-of-N OTs
- `N_1_of_N_noreduct_OT()` — N parallel 1-of-N without reduction

Protocol pattern: `Provider` and `Receiver` inner classes exchange messages round by round; each has a `__main__` inner class that orchestrates the full execution.

### `vole.py` — Vector OLE

- `POL`: polynomial over `bits`, supports evaluation
- `VOLE_dv()`: factory returning `Prover`/`Verifier` — implements VOLE with designated verifier. Prover holds `(x, y)`, Verifier holds `Δ`, result satisfies `y = x·Δ + e`

### `mpc.py` — 3-party MPC

- `RNG`: deterministic bit generation from a key (used for shared randomness)
- `shares`: 3-party additive secret sharing over `bits`; `wire` property = XOR of all shares
- `SBox`: evaluates a non-linear gate using shared multiplication
- `Permutation`: mixing layer combining linear and non-linear steps
- `Circuit`: sponge-based absorb/squeeze construction for multi-party evaluation

## Key Conventions

- Protocols are written as nested classes inside factory functions so each call produces fresh, independent instances.
- Tests are frequently decorated with `@unittest.skip` during development; re-enable by removing the decorator when verifying correctness.
- The `olds/` directory keeps prior implementations for reference — do not modify them.
