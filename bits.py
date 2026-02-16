# /// script
# [tool.marimo.runtime]
# auto_instantiate = false
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App(width="medium")


@app.cell
def _():
    import numpy as np
    from math import log2, floor
    from collections.abc import Iterable
    from random import choice
    from hashlib import shake_256
    import galois


    return Iterable, choice, floor, galois, np, shake_256


@app.cell
def _(galois, np):
    #parameters
    #round bytes
    gamma = 0.25
    tsize = 128
    # galois 
    ng  = 255
    ecc = 9
    rs = galois.ReedSolomon(ng,ng-ecc+1)
    GF = rs.field
    # np
    every = np.all
    #bits
    N = 16
    return every, gamma, rs, tsize


@app.cell
def _(Iterable, choice, every, floor, gamma, np, shake_256, tsize):
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
    #        n = getattr(obj, 'n', None)
            self.dtype = np.uint8
        
 
        def __str__(self):
            return np.array_str(self)
    
        def __repr__(self):
            return np.array_repr(self)     #[:-1] + ', p=' + str(self.p) + ')'
    
    
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
            l   = len(data[0]) ; err = floor(gamma * l)
            _0 = np.uint(0) ; _1 = np.uint(1)
            byt = []
            for i in range(8):
                x = sum(data[i])
                if l - x < err:
                    byt.append(_1)
                elif x < err:
                    byt.append(_0)
                else:
                    byt.append(choice([_0 , _1]))
            return np.packbits(byt)
        
    
    
        def __eq__(self, other):
    #        return np.array_equal(self, other)
            return every(np.array_equiv(self, other))
    
        def tobytes(self):
            return self.lift().tobytes().strip(b'\x00')

        def hash(self):
            hash = shake_256(self.tobytes())
            return hash.digest(tsize)

    
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

    


    return (bits,)


@app.cell
def _():
    from os import urandom

    return (urandom,)


@app.cell
def _(bits, urandom):
    a = bits([bits(urandom(8)) for _ in range(4)])
    a, a.bit_count()
    return (a,)


@app.cell
def _(bits, urandom):
    eta = bits(urandom(4))
    s   = bits(urandom(8))
    return eta, s


@app.cell
def _(a, eta, s):
    x = eta @ a @ s
    x, x.bit_count()
    return


@app.cell
def _(a, bits, rs):
    aa = bits(rs.encode(a))

    return (aa,)


@app.cell
def _(aa, bits, rs):
    bb = bits(rs.decode(aa))
    bb
    return


if __name__ == "__main__":
    app.run()
