# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.23.4",
#     "numpy==2.4.4",
# ]
# ///

import marimo

__generated_with = "0.23.5"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    from bits import bits_crs, bits
    import numpy as np
    from hashlib import shake_256
    from os import urandom
    from itertools import combinations
    from config import config_MPC
    import unittest
    params = config_MPC().__dict__
    globals().update(params)
    ksize = params['ksize']
    wsize = params['wsize']
    csize = params['csize']
    rsize = params['rsize']
    iosize= params['iosize']


    def split(s):
        l = len(s) // wsize ; s = s[: l*wsize]
        return [bits(x) for x in np.split(bits(s), l)]

    def pad(s, l):
        return s + b'\x00'*(l - len(s))  if l > len(s)  else s[:l]


@app.class_definition
class RNG(object):
    def __init__(self, master_key : bytes = None):
        if master_key is None: master_key = urandom(ksize)
        self.hash = shake_256(b'MASTER' + master_key)
        seed = np.frombuffer(self.hash.digest(ksize),dtype=np.uint8)
        self._master = np.random.default_rng(seed)
        self.hash.update(b'RNGS')
        seed = np.frombuffer(self.hash.digest(ksize),dtype=np.uint8)
        self._rngs = np.random.default_rng(seed).spawn(3)


    @property
    def rngs(self):
        return self._rngs

    @property
    def master(self):
        return self._master

    def update(self, sid : np.uint16 = 0):
        self.hash.update(str(sid).encode())
        seed = np.frombuffer(self.hash.digest(ksize),dtype=np.uint8)
        self._rngs = np.random.default_rng(seed).spawn(3)


@app.class_definition
class shares(bits):  # views
    def __new__(cls, *data, rngs=None):

        if len(data) == 0:
            if rngs is None:
                rngs = RNG().rngs
            s = [bits(ng.integers(256, dtype=np.uint8, size=wsize)) for ng in rngs]
            obj = bits([s[j] + s[(j+2)%3]  for j in range(3)]).view(cls)


        elif isinstance(data[0], bits) and len(data) == 1:     # inicializar shares de um input "w"
            w = data[0][:wsize] ; u = shares(rngs=rngs)
            obj = bits([bits([u[j], w + u[(j+2)%3]]) for j in range(3)]).view(cls)

        elif isinstance(data[0], bits) and len(data) > 1:   # restore a 3a. view a partir de duas views
#            j = 0; i = 1; k = 2
            x_0 = data[0][0] ; m_0 = data[0][1] ; x_1 = data[1][0] ; m_1 = data[1][1] ; x_2 = x_0 + x_1  
            w = m_1 + x_0 ; w_ = m_0 + x_2 ; m_2 = w + x_1
            assert w == w_ , f"shares inconsistentes"
            obj = bits([data[0], data[1], bits([x_2,m_2])]).view(shares)

        else:
            raise ValueError(f"do not knw how to make a shares object from {data}")
        return obj


    def __array_finalize__(self, obj):
        if obj is None: return
        self.dtype = np.uint8

    def __str__(self):
        return np.array_str(self)

    def __repr__(self):
        return np.array_repr(self) 

    def lift(self):
        return self.view(bits)

    @property
    def wire(self):
        s = self[0] + self[1] + self[2]
        assert s[0] == 0, f"not a correlated randomness on the first components"
        return s[1]

    @property
    def msg(self):
        return bits([z[0]+z[1] for z in self])

    def add(self,other):
        return (self.lift() + other.lift()).view(shares)

    def __add__(self, other):
        return self.add(other)

    def mul(self, another , rho = None):
        this = self.lift() ; other = another.lift()   
        if rho is None: rho = shares()
        r    = [rho[j] + this[j,0] * other[j,0] + this[j,1] * other[j,1] for j in range(3)] 
        return bits([bits([r[j] + r[(j+2)%3], r[j]]) for j in range(3)]).view(shares)

    def __mul__(self,other):
        return self.mul(other)


app._unparsable_cell(
    r"""
    class View(shares
    """,
    name="_"
)


@app.class_definition
class SBox(object):
    def __init__(self, shape, R):
        (n, m) = shape
        assert n*(n-1) >= 2*m, f"to few inputs or to many outputs"
        all_pairs = list(combinations(range(n),2))
        self._pairs = R.master.permutation(all_pairs)[:m]
        self._rngs  = R.rngs

    @property
    def pairs(self):
        return self._pairs

    @property
    def rngs(self):
        return self._rngs

    def eval(self, xs : list, rngs):
        ys = [] ; rhos = [] ; msgs = []
        for (i,j) in self.pairs:
            rho = shares(rngs=rngs)
            prod = (xs[i].view(shares)).mul(xs[j].view(shares), rho=rho)
            ys.append(prod) ; rhos.append(rho) ; msgs.append(prod.msg)
        return bits(ys), rhos, msgs


@app.class_definition
class Permutation(object):
    def __init__(self, key : bytes, n=rsize , m=csize):
        self.R = RNG(key)
        self.top = SBox((n, m), self.R)
        self.bot = SBox((m, n), self.R)

    @property
    def rngs(self):
        return self.R.rngs

    def eval(self, rate, capacity):
        (capacity_,r0,m0) = self.top.eval(rate, rngs=self.rngs)
        capacity = capacity + capacity_
        (rate_,r1,m1) = self.bot.eval(capacity, rngs=self.rngs)
        rate     = rate + rate_ 
        return (rate, capacity, r1 + r0, m1 + m0)


@app.class_definition
class Circuit(object):

    def __init__(self, key : bytes , secret : bytes, sid : int = 0):
        self.p = Permutation(key) ; rngs = self.p.rngs
        rate_  = np.zeros(wsize*rsize); secret_ = pad(secret,wsize*csize)
        rate     = [shares(z, rngs=rngs) for z in split(rate_)]
        capacity = [shares(z, rngs=rngs) for z in split(secret_)]
        self.start = self.p.eval(rate, capacity)

    def sponge(self, inputs : bytes):
        rngs = self.p.rngs ; blks = iosize // (rsize * wsize)
        inps = np.split([shares(z) for z in split(pad(inputs,iosize))], blks)

        rate, capacity, rs , ms = self.start
            # absorb
        for inp in inps:
            rate, capacity, r_ , m_ = self.p([r+i for (r,i) in zip(rate,inp)], capacity)
            rs = rs + r_ ; ms = ms + m_
            #squeeze
        out = []
        for _ in range(blks):
            rate, capacity, r_, m_  = self.p(rate, capacity)
            rs = rs + r_ ; ms = ms + m_
            out.append(rate)
        return bits(out), rs, ms


@app.class_definition
class Test_MPC(unittest.TestCase):

    #@unittest.skip("wire")
    def test_wire(self):
        w = bits(urandom(wsize)) ; rngs = RNG().rngs
        sh= shares(w, rngs=rngs)
        self.assertEqual(w, sh.wire)
        sh_ = shares(sh[0],sh[1])
        self.assertEqual(w, sh_.wire)

    #@unittest.skip("ops")
    def test_ops(self):
        w = bits(urandom(wsize)) ; w_ = bits(urandom(wsize)) 
        rngs = RNG().rngs
        sh = shares(w, rngs=rngs) ; sh_ = shares(w_, rngs=rngs)
        self.assertEqual(w + w_ , (sh + sh_).wire)
        self.assertEqual(w * w_ , (sh * sh_).wire)
        rho = shares(rngs=rngs) ; sh = sh.mul(sh_,rho=rho)
        self.assertEqual(w * w_ , sh.wire)

    #@unittest.skip("circuit")
    def test_circuit(self):
        key    = urandom(ksize)
        secret = urandom(csize)
        circuit = Circuit(key, secret)
        self.assertTrue(True)


if __name__ == "__main__":
    app.run()
