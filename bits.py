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
    from os import urandom

    return Iterable, choice, floor, galois, log2, np, shake_256, urandom


@app.cell
def _(floor, galois, log2, np):
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
    # sampler
    eps = 0.1
    # OT security
    n = 16
    l = floor(n * log2(n))
    return N, eps, every, gamma, l, n, rs, tsize


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
def _(N, bits, eps, np, urandom):
    class bits_sampler(object):

        def __init__(self, seed=None):
            if seed is None:
                seed = bits(urandom(N//2))
            if not isinstance(seed, bits):
                seed = bits(seed)
            self.rng = np.random.default_rng(seed)



        def noise(self, l=N, eps=eps):
            return bits(np.packbits([1 if self.rng.random() < eps else 0 for _ in range(l * 8)]))

        def secrets(self, l=N):
            data = self.rng.integers(256, size=l, dtype=np.uint8)
            return bits(data)

        def eta(self, eps, l):
            data = self.rng.binomial(256, eps , size=(l))
            return bits(data)


    return (bits_sampler,)


@app.cell
def _(bits, l, n, shake_256, urandom):
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

    return (bits_crs,)


@app.cell
def _(bits, bits_crs, bits_sampler, eps, l, n, np, rs):
    def one_of_two_bytes_OT():
        class Provider(object):
            def __init__(self, ):
                self.sampler = bits_sampler()
                self.crs     = bits_crs()


            def choose(self, m0 : np.uint8  , m1 : np.uint8) -> bytes:
                self.m0   = bits([m0])
                self.m1   = bits([m1])
                return self.crs.key

            def transfer(self, P, sid=0):
                eta = self.sampler.eta(eps, l)
                SID = str(sid).encode()
                a , u    = self.crs.AU(tweak=SID)
                (p0, p1) = P 
                assert p0 + p1 == u , f"public keys p0,p1 = ({p0},{p1}) unmatch u={u}"     
                a_ = eta @ a ; p0_ = eta @ p0 ; p1_ = eta @ p1
                return (a_, p0_ + self.m0 , p1_ + self.m1)

        class Receiver(object):
            def __init__(self):
                self.sampler = bits_sampler()
                self.s       = self.sampler.secrets(n)     # LPN OT  key

            def choose(self, key, b, sid=0):
                self.crs = bits_crs(key)
                self.b    = b
                SID = str(sid).encode()
                a, u = self.crs.AU(tweak=SID)
                e    = self.sampler.noise(l, eps)
                t    =  a @ self.s + e
                if self.b == 0:
                    return  (t , t + u)
                return (t + u , t)

            def transfer(self,C):
                (a, c0, c1) = C 
                key = a @ self.s
                if self.b == 0:
                    return (c0 + key).byte_round()
                else:
                    return (c1 + key).byte_round()

        class __main__(object):
            def __init__(self, mess0 : bits , mess1 : bits):
                self.provider = Provider()
                self.receiver = Receiver()
                assert len(mess0) == len(mess1), f"messages must have equal length"
                self.mess0 = bits(rs.encode(mess0))
                self.mess1 = bits(rs.encode(mess1))

            def get(self, b):
                data = []
                for sid in range(len(self.mess0)):
                    key  = self.provider.choose(self.mess0[sid], self.mess1[sid])
                    P    = self.receiver.choose(key, b, sid)
                    crpt = self.provider.transfer(P , sid)
                    res  = self.receiver.transfer(crpt)
                    if not (res is None):
                        data.append(res[0])
                #print(data)
                data_  = bits(rs.decode(data))
                return bits(data_)


        return __main__


    return


if __name__ == "__main__":
    app.run()
