# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "galois==0.4.10",
#     "marimo>=0.23.3",
#     "numpy==2.3.5",
#     "pytest==9.0.2",
#     "pyzmq>=27.1.0",
# ]
# [tool.marimo.runtime]
# auto_instantiate = false
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium", auto_download=["html"])

with app.setup:
    import marimo as mo
    import numpy as np
    from math import log2, floor, ceil
    from collections.abc import Iterable
    from random import choice
    from hashlib import shake_256, sha3_224
    from secrets import token_bytes, randbits
    from os import urandom
    from config import config
    import pytest


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
    def __new__(cls, arg):
        if isinstance(arg, bytes) or isinstance(arg, bytearray):
            obj = np.frombuffer(arg, dtype=np.uint8).view(cls)
        elif isinstance(arg, np.ndarray):
            obj = arg.astype(np.uint8).view(cls)
        elif isinstance(arg, Iterable):
            data = np.stack(arg).astype(np.uint8)
            if isinstance(arg,str) and arg.isdecimal():
                data = np.packbits(data)
            obj = data.view(cls)
        elif isinstance(arg,int):
            size = ceil(arg.bit_length()/8)
            obj  = bits(arg.to_bytes(size))
        else:
            raise ValueError(f"do not knw how to make a bits object from {arg}")
        return obj

#    def __array_finalize__(self, obj):
#        if obj is None: return
#        self.dtype = np.uint8


    def __str__(self):
        return np.array_str(self)

    def __repr__(self):
        return np.array_repr(self) 

    def roll(self, shift = None , axis = None):
        n = self.ndim
        assert n > 0
        if shift is None: 
            shift =  (0,1) + (0,)*(n-2) if n > 1 else 1
        if axis is None:
            axis = (0,)*n
        return np.roll(self,shift,axis).view(bits)


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



    def byte_round(self,d=1):
        data = self.unpack().reshape((-1,8*d)).T
        g    = params['gamma']
        size   = len(data[0]) ; err = floor(g * size)
        byt = []
        for i in range(8*d):
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

    @property
    def tobytes(self):
        return self.lift().tobytes().strip(b'\x00')

    @property
    def toInt(self):
        return int.from_bytes(self.tobytes)

    @property
    def hash(self):
        return hash(self.tobytes)

    def __hash__(self):
        return self.hash


    def add(self, other):
        if np.ndim(self) > 0:
            return np.bitwise_xor.__call__(self,other).view(bits)
        return np.bitwise_xor(self,other).view(bits)

    def __add__(self,other):
        return self.add(other)

    def mul(self, other):
        if np.ndim(self) > 0:
            return np.bitwise_and.__call__(self,other).view(bits)
        return np.bitwise_and(self, other).view(bits)

    def __mul__(self,other):
        return self.mul(other)

    def invert(self):
        if np.ndim(self) > 0:
            return np.bitwise_invert.__call__(self).view(bits) 
        return np.bitwise_invert(self).view(bits)

    def __invert__(self):
        return self.invert()

    def implies(self,other):
        return (self + self.mul(other)).invert()

    def __pow__(self,other):
        return self.implies(other)

    def matmul(self,other):
        if np.ndim(self) == 1 and np.ndim(other) == 1:
            return (self * other).sum().view(bits)
        if np.ndim(self) == 1:
            (_,k) = other.shape
            return np.array([self.matmul(other[:,j]) for j in range(k)]).view(bits)
        if np.ndim(other) == 1:
            (l,_) = self.shape
            return np.array([self[t].matmul(other) for t in range(l)]).view(bits)
        else:
            (l,n) = self.shape ; (m,k) = other.shape
            assert n == m, f"shapes {(l,n)} and {(m,k)} are incompatible in matmul"
            return np.array([[self[i,:].matmul(other[:,j]) for j in range(k)] for i in range(l)]).view(bits)

    def __matmul__(self,other):
        return self.matmul(other)

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
        return bits(np.packbits([1 if self.rng.random() < eps else 0 for _ in range(l*8)]))

    def secrets(self, n=n):
        data = self.rng.integers(256, size=n, dtype=np.uint8)
        return bits(data)

    def eta(self, l:int = l, cut:float = cut):
        l8 = l*8 ; d = floor(l8*cut) ; r = l8-d
        slice = self.rng.permutation(l8)
        data = np.array([1]*d + [0]*r)[slice]
        return bits(np.packbits(data))


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
