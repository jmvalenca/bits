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
    from bits import bits, bits_sampler, boolpol
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


@app.class_definition
class Test_boolpol():

    def test_init(self):
        p = boolpol(2)
        assert p.n == 2
        assert p.spectrum == set()
        assert p.support == set()

        e0 = bits(np.array([1,0], dtype=np.uint8))
        e1 = bits(np.array([1,1], dtype=np.uint8))
        p = boolpol(2, {e0, e1})
        assert p.spectrum == {e0, e1}

    def test_eval(self):
        e0 = bits(np.array([1,0], dtype=np.uint8))
        e1 = bits(np.array([1,1], dtype=np.uint8))
        p = boolpol(2, {e0, e1})
        for x0 in (0,1):
            for x1 in (0,1):
                x = bits(np.array([x0,x1], dtype=np.uint8))
                expected = x0 ^ (x0 & x1)
                assert int(p.eval(x)) == expected

    def test_sat(self):
        e0 = bits(np.array([1,0], dtype=np.uint8))
        e1 = bits(np.array([1,1], dtype=np.uint8))
        p = boolpol(2, {e0, e1})
        support = p.sat()
        assert support == p.support
        expected = {bits(np.array([x0,x1], dtype=np.uint8))
                    for x0 in (0,1) for x1 in (0,1)
                    if (x0 ^ (x0 & x1)) == 1}
        assert support == expected

    def test_eq(self):
        e0 = bits(np.array([1,0], dtype=np.uint8))
        e1 = bits(np.array([1,1], dtype=np.uint8))
        p = boolpol(2, {e0, e1})
        q = boolpol(2, {e0, e1})
        r = boolpol(2, {e0})
        assert p == q
        assert p != r
        assert p != object()

    def test_repr(self):
        p = boolpol(2, {bits(np.array([1,0], dtype=np.uint8))})
        assert "boolpol" in repr(p)


if __name__ == "__main__":
    app.run()
