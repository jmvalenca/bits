# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.19.10",
#     "numpy>=2.4.2",
#     "pyzmq>=27.1.0",
# ]
# ///

import marimo

__generated_with = "0.20.2"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import numpy as np
    from math import log2, floor
    from dataclasses import dataclass


@app.class_definition
#parameters
@dataclass
class config:
#round bytes
    gamma : float = 0.25
    tsize : int   = 128

# bits
    N : int       = 16

# OT security
    n : int  = 16
    l : int = max(tsize, floor(n * log2(N)))
# iterações
    n_iters : int = n

# sampler
    eps : float = 0.02
    cut : float = eps

# MDS codes 
    n_ecc : int = 255
    k_ecc : int = 223
    t_ecc : int = (n_ecc - k_ecc)/2   # ecc = 16
    d_ecc : int = n_ecc - k_ecc + 1


if __name__ == "__main__":
    app.run()
