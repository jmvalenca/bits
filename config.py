# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.19.10",
#     "numpy>=2.4.2",
#     "pyzmq>=27.1.0",
# ]
# ///

import marimo

__generated_with = "0.23.5"
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
    tsize : int   = 16

# bits
    N : int       = 16

# OT security
    n : int  = 16
    l : int = max(tsize, floor(n * log2(N)))
# iterações
    n_iters : int = 31

# sampler
    eps : float = 0.02
    cut : float = 0.1

# MDS codes 
    n_ecc : int = 255
    k_ecc : int = 191
    t_ecc : int = (n_ecc - k_ecc)/2   
    d_ecc : int = n_ecc - k_ecc + 1


@app.class_definition
@dataclass
class config_VOLE:
    x_size : int = 32        # lenght of "x" in bits
    t_size : int = 16
    n_tags : int = x_size


@app.class_definition
@dataclass
class config_NP:
    N     : int = 32
    msize : int = 16
    ksize : int = 16


@app.class_definition
@dataclass
class config_MPC:
    rsize : int = 8   # "rate" em bytes
    csize : int = 24  # "capacity" em bytes
    rounds: int = 8   # numero de "rounds" por permutação
    ksize : int = 16  
    wsize : int = 2
    iosize: int = 32


if __name__ == "__main__":
    app.run()
