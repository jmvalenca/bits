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
    import numpy as np
    from math import log2, floor
    from collections.abc import Iterable
    from random import choice
    from hashlib import shake_256
    import galois
    from os import urandom
    import config_nb as config

    #globals().update(config.config().__dict__)

    params = config.config().__dict__
    tsize  = params['tsize']
    gamma  = params['gamma']
    niters = params['niters']
    n      = params['n']
    N      = params['N']
    eps    = params['eps']
    cut    = params['cut']
    l      = params['l']


@app.cell
def _():
    import marimo as mo

    return


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
        return np.all(np.array_equiv(self, other))

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


@app.class_definition
class bits_sampler(object):

    def __init__(self, seed=None):
        if seed is None:
            seed = bits(urandom(n))
        if not isinstance(seed, bits):
            seed = bits(seed)
        self.rng = np.random.default_rng(seed)



    def noise(self, l=l, eps=eps):
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


    def AU(self, tweak : bytes = b'\x00\x00', l : int = l):
        hash = shake_256(b'AU' + self._key + tweak)
        A = bits(hash.digest(l*n)).reshape((l,n))
        hash.update(b'U')
        U = bits(hash.digest(l))
        return A,U


@app.function
def one_of_two_bytes_OT():
    class Provider(object):
        def __init__(self):
            self.sampler = bits_sampler()
            self.crs     = bits_crs()


        def choose(self, m0 : np.uint8  , m1 : np.uint8) -> bytes:
            self.m0   = bits([m0])
            self.m1   = bits([m1])
            return self.crs.key

        def transfer(self, P, sid=0, iter=0):
            msk = self.sampler.eta()
            SID = str(sid).encode() + str(iter).encode()
            a , u    = self.crs.AU(tweak=SID)
            (p0, p1) = P 
            assert p0 + p1 == u , f"public keys p0,p1 = ({p0},{p1}) unmatch u={u}"     
            a_ = msk @ a ; p0_ = msk @ p0 ; p1_ = msk @ p1
            return (a_, p0_ + self.m0 , p1_ + self.m1)

    class Receiver(object):
        def __init__(self):
            self.sampler = bits_sampler()
            self.s       = self.sampler.secrets(n)     # LPN OT  key

        def choose(self, key, b, sid=0, iter=0):
            self.crs = bits_crs(key)
            self.b    = b
            SID = str(sid).encode() + str(iter).encode()
            a, u = self.crs.AU(tweak=SID)
            e    = self.sampler.noise()
            t    =  (a @ self.s) + e
            if self.b == 0:
                return  (t , t + u)
            return (t + u , t)

        def transfer(self,C):
            (a, c0, c1) = C 
            return (a @ self.s) + (c0 if self.b == 0 else c1)


    class __main__(object):
        def __init__(self, mess0 : bits , mess1 : bits):
            # galois 
            ng  = 255 ; ecc = 127
            self.rs = galois.ReedSolomon(ng,ng-ecc+1)
            #
            self.provider = Provider()
            self.receiver = Receiver()
            assert len(mess0) == len(mess1), f"messages must have equal length"
            self.mess0 = bits(self.rs.encode(mess0))
            self.mess1 = bits(self.rs.encode(mess1))

        def get(self, b):
            data = []
            for sid in range(len(self.mess0)):
                iters = [] ; m0 = self.mess0[sid] ; m1 = self.mess1[sid]
                for iter in range(niters):    
                    key  = self.provider.choose(m0,m1)
                    P    = self.receiver.choose(key, b, sid, iter)
                    C    = self.provider.transfer(P , sid, iter)
                    res  = self.receiver.transfer(C)
                    iters.append(res)  
                data.append(bits(iters).byte_round()[0])
            data_, errors  = self.rs.decode(data, errors=True)
            assert errors >= 0, f"existem erros que não foram corrigidos"
            return bits(data_)


    return __main__


if __name__ == "__main__":
    app.run()
