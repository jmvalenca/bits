# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "galois==0.4.11",
#     "marimo>=0.24.0",
#     "numpy==2.5.2",
#     "pytest==9.1.1",
# ]
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App()

with app.setup:
    import marimo as mo
    from bits import bits, bits_crs, bits_sampler
    from ots  import one_of_two_ot as OT
    from hashlib import shake_256
    import numpy  as np
    import galois as ga

    from config import config, config_VOLE
    from os import urandom
    from random import choice

    params = config().__dict__
    params_VOLE = config_VOLE().__dict__
    globals().update(params)

    zero = bits([0])
    one  = bits([255])

    n_tags = params_VOLE['n_tags']
    tsize  = params_VOLE['t_size']
    # tests
    import pytest


@app.class_definition
class POL(object):
    def __init__(self, n_tags = n_tags , key = None, tweak = b'\x00\x00'):
        if key is None:
            key = urandom(tsize)
        self._key = key
        n = n_tags // 8
        hash = shake_256(b'POL' + self._key + tweak)
        buff = hash.digest(3*n)
        self._coef  =  {'c' : bits([0]),
                        'b' : bits(buff[:n]).unpack(), 
                        'u' : bits(buff[n:2*n]).unpack(), 
                        'v' : bits(buff[2*n:]).unpack()}

    @property
    def c(self):
        return self._coef['c']

    @c.setter
    def c(self, value : np.ndarray):
        self._coef['c'] = value

    def e_value(self, x : np.ndarray , y : np.ndarray = one):
        if x.ndim == 1:
            x = x.unpack()
        bx, ux, vx = self._coef['b'] @ x, self._coef['u'] @ x, self._coef['v'] @ x
        return y*y*self.c + (y * bx) + (ux * vx)

    def a_values(self, x : np.ndarray , m : np.ndarray):
        x = x.unpack()
        bx, ux, vx = self._coef['b'] @ x, self._coef['u'] @ x, self._coef['v'] @ x
        bm, um, vm = self._coef['b'] @ m, self._coef['u'] @ m, self._coef['v'] @ m
        return bm + (ux * vm) + (vx * um) , um * vm


@app.function
def VOLE_dv():
    class Prover(object):
        def __init__(self, x : np.ndarray):
            self._x = x

        @property
        def x(self):
            return self._x


        def accept(self, ots):
            x_bits = list(self._x.unpack())[:n_tags]
            self._tags = [o.get(b) for (b,o) in zip(x_bits,ots)]


        @property
        def tags(self):
            return bits(self._tags).reshape((n_tags,-1))


    class Verifier(object):
        def __init__(self):
            spl = bits_sampler()
            ot_class = OT()
            self._delta = spl.secrets(tsize)
            self._qs    = [spl.secrets(tsize) for _ in range(n_tags)]
            self._ots   = [ot_class(q, q + self.delta) for q in self._qs]

        @property
        def ots(self):
            return self._ots

        @property
        def delta(self):
            return self._delta

        @property
        def qs(self):
            return bits(self._qs).reshape((n_tags,-1))



    class __main__(object):
        def __init__(self, x : np.ndarray):
            self._prover = Prover(x)
            self._verifier = Verifier()
            self._prover.accept(self._verifier._ots)

        @property
        def prover(self):
            return self._prover

        @property
        def verifier(self):
            return self._verifier

    return __main__


if __name__ == "__main__":
    app.run()
