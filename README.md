# bits

Pedagogical implementations of cryptographic primitives: Oblivious Transfer (OT), Vector Oblivious Linear Evaluation (VOLE), and MPC-in-the-Head (ITH MPC).

Each file is both a runnable [marimo](https://marimo.io) interactive notebook and an importable Python module.

## Modules

| File | Purpose |
|------|---------|
| `bits.py` | Core binary field type (`bits` over GF(2)), samplers, and common reference string |
| `config.py` | Protocol parameter dataclasses |
| `ots.py` | Oblivious Transfer protocols (1-of-2, 1-of-N, all-but-one) |
| `vole.py` | Designated-verifier Vector OLE |
| `mpc.py` | MPC-in-the-Head protocol with sponge-based circuit |

**Dependency order:** `config.py` → `bits.py` → `ots.py` / `vole.py` → `mpc.py`

## Protocols

### Oblivious Transfer (`ots.py`)

- **`one_of_two_ot()`** — LPN-based 1-of-2 OT with Reed-Solomon error correction
- **`one_of_all_ot()`** — Naor-Pinkas 1-of-N OT, built from `l` parallel 1-of-2 OTs
- **`all_but_one_ot()`** — Secret-sharing based OT; receiver learns all N messages except one

All protocols follow the same factory pattern: each call returns a fresh `__main__` class with `Provider` and `Receiver` inner classes.

### Vector OLE (`vole.py`)

Designated-verifier VOLE via `VOLE_dv()`. After the protocol, for each bit `b_i` of the prover's secret `x`:

```
qs[i] = tags[i] + b_i · delta
```

### MPC-in-the-Head (`mpc.py`)

`mpcITH()` implements the ITH paradigm over a sponge-based circuit (`Circuit`) built from a `Permutation` of `SBox` layers. Each session runs Commit → Challenge → Prove → Verify. The circuit uses Araki et al. 3-party multiplication triples for the non-linear gates.

## Requirements

Python >= 3.13 (`bits.py`, `mpc.py`) / >= 3.14 (`ots.py`, `vole.py`). Dependencies are declared as PEP 735 inline script metadata in each file.

Key packages: `numpy`, `galois==0.4.10`, `marimo>=0.23.4`.

## Usage

```bash
# Run as interactive notebook
marimo edit bits.py

# Run tests
pytest test_bits.py test_ots.py test_vole.py test_mpc.py -v
```
