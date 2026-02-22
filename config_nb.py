import marimo

__generated_with = "0.19.11"
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
    n : int  = 24
    l : int = max(tsize, floor(n * log2(N)))
# iterações
    niters : int = n

# sampler
    eps : float = 0.02
    cut : float = 0.02


if __name__ == "__main__":
    app.run()
