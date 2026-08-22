# /// script
# dependencies = [
#     "marimo",
#     "numpy==2.5.2",
#     "pytest==9.1.1",
# ]
# requires-python = ">=3.14"
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import numpy as np
    from bits import bits, bits_sampler
    from secrets import token_bytes, randbits
    from os import urandom
    import pytest


@app.class_definition
class Test_bits():

    def test_init(self):
        u = token_bytes(8)
        assert u == bits(u).tobytes
        r = randbits(128)
        assert r == bits(r).toInt


    def test_add(self):
        spl=bits_sampler()
        n = 4
        a = spl.secrets(n) 
        b = spl.secrets(n*n).reshape((n,n))
        c = a + b
        assert isinstance(c, bits)
        assert np.all([c[i] ==  a + b[i] for i in range(n)])


    def test_mul(self):
        spl=bits_sampler()
        n = 4
        a = spl.secrets(n) 
        b = spl.secrets(n*n).reshape((n,n))
        c = a * b
        assert np.all([c[i] ==  a * b[i] for i in range(n)])

    def test_matmul_0(self):
        a = bits(urandom(8)).reshape((2,4))
        b = bits(urandom(8)).reshape((4,2))
        assert (a @ b).T == (b.T @ a.T)

    def test_matmul_1(self):
        for l in range(2,16):
            m = bits(urandom(2*l*l)).reshape((l,2*l))
            q = (m.T) @ m
            x = bits(urandom(2*l))
            assert (x @ q) == (q @ x)


if __name__ == "__main__":
    app.run()
