# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "galois==0.4.10",
#     "marimo>=0.19.10",
#     "numpy==2.3.5",
#     "pyzmq>=27.1.0",
# ]
# [tool.marimo.runtime]
# auto_instantiate = false
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App(width="medium", auto_download=["ipynb"])

with app.setup:
    import marimo as mo
    import numpy as np
    from math import log2, floor
    from collections.abc import Iterable
    from random import choice
    from hashlib import shake_256
    from os import urandom
    from config_nb import config




    params = config().__dict__
    globals().update(params)

    gamma  = params['gamma']
    n      = params['n']
    N      = params['N']
    eps    = params['eps']
    cut    = params['cut']
    l      = params['l']


@app.class_definition
class bits(np.ndarray):
    def __new__(cls, input_array):
        if isinstance(input_array, bytes) or isinstance(input_array, bytearray):
            obj = np.frombuffer(input_array, dtype=np.uint8).view(cls)
        elif isinstance(input_array, np.ndarray):
            obj = input_array.astype(np.uint8).view(cls)
        elif isinstance(input_array, Iterable):
            obj = np.stack(input_array).astype(np.uint8).view(cls)
        else:
            obj = np.packbits(input_array).view(cls)
        return obj

    def __array_finalize__(self, obj):
        if obj is None: return
        self.dtype = np.uint8


    def __str__(self):
        return np.array_str(self)

    def __repr__(self):
        return np.array_repr(self) 


    def unpack(self):
        return np.unpackbits(self)

    def lift(self):
        return self.view(np.ndarray)

    def bit_counts(self):
        data = np.vectorize(lambda x: int(x).bit_count() , otypes=[np.uint8])(self.lift())
        if np.ndim(self) > 0:
            if np.ndim(data) < 2:
                return data
            else:
                data = data.reshape((data.shape[0], -1))
                return data
        if np.issubdtype(self.dtype, np.integer):
            return np.add.reduce(data)
        return np.unpackbits(self).sum()

    def bit_count(self):
        res = self.bit_counts()
        if np.ndim(res) == 0:
            return res
        else:
            return sum(res) 



    def byte_round(self):
        data = self.unpack().reshape((-1,8)).T
        g    = params['gamma']
        size   = len(data[0]) ; err = floor(g * size)
        byt = []
        for i in range(8):
            x = sum(data[i])
            if size - x < err:
                byt.append(np.uint(1))
            elif x < err:
                byt.append(np.uint(0))
            else:
                byt.append(choice([np.uint(0), np.uint(1)]))
        return np.packbits(byt)



    def __eq__(self, other):
#        return np.array_equal(self, other)
        return np.all(np.array_equiv(self, other))

    def tobytes(self):
        return self.lift().tobytes().strip(b'\x00')

    def hash(self):
        hash = shake_256(self.tobytes())
        return hash.digest(N)


    def add(self, other):
        if np.ndim(self) > 0:
            return np.bitwise_xor.__call__(self,other).view(bits)
        return np.bitwise_xor(self,other)

    def __add__(self,other):
        return self.add(other)

    def mul(self, other):
        if np.ndim(self) > 0:
            return np.bitwise_and.__call__(self,other).view(bits)
        return np.bitwise_and(self, other)

    def __mul__(self,other):
        return self.mul(other)

    def sum(self):
        return np.bitwise_xor.reduce(self)

    def bissect(self):
        size_ = self.size // 2
        return (self[:size_], self[size_:])


@app.class_definition
class bits_sampler(object):

    def __init__(self, seed=None):
        if seed is None:
            seed = bits(urandom(n))
        if not isinstance(seed, bits):
            seed = bits(seed)
        self.rng = np.random.default_rng(seed)



    def noise(self, l : int =l, eps : float = eps):
        return bits(np.packbits([1 if self.rng.random() < eps else 0 for _ in range(l * 8)]))

    def secrets(self, n=n):
        data = self.rng.integers(256, size=n, dtype=np.uint8)
        return bits(data)

    def eta(self, l:int = l, cut:float = cut):
        d = floor(l * cut) ; slice = self.rng.permutation(l)
        data  = bits([255]*d + [0]*(l-d))
        return bits(data[slice]).T


@app.class_definition
class bits_crs(object):
    def __init__(self, key=None):
        if key is None:
            key = urandom(n)
        self._key = key 


    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value):
        self._key = value


    def AU(self, tweak : bytes = b'\x00\x00', l : int = l, n : int = n):
        hash = shake_256(b'AU' + self._key + tweak)
        A = bits(hash.digest(l*n)).reshape((l,n))
        hash.update(b'U')
        U = bits(hash.digest(l))
        return A,U


if __name__ == "__main__":
    app.run()
