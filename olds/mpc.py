# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.23.3",
#     "numpy>=2.4.4",
#     "pytest>=9.0.3",
# ]
# ///

import marimo

__generated_with = "0.23.4"
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


@app.class_definition
class SCR(object):
    def __init__(self, master_key : bytes = None):
        if master_key is None : master_key = urandom(ksize)
        self.hash = shake_256(b'master'+ master_key)
        seed = np.frombuffer(self.hash.digest(ksize),dtype=np.uint8)
        master = np.random.default_rng(seed)
        self._prgs = [master] + master.spawn(2)


    @property
    def prgs(self):
        return self._prgs

    @prgs.setter
    def prgs(self,sid : np.uint16):
        self.hash.update(str(sid).encode())
        seed = np.frombuffer(self.hash.digest(ksize),dtype=np.uint8)
        master = np.random.default_rng(seed)
        self._prgs = [master] + master.spawn(2)

    @property    
    def scr(self):
        s = [bits(prg.integers(256, dtype=np.uint8, size=wsize)) for prg in self.prgs]
        return bits([s[j] + s[(j+2)%3]  for j in range(3)])


@app.class_definition
class shares(bits):  # views
    def __new__(cls, *data, scr=None):

        if len(data) == 0:
            if scr is None: scr = SCR()
            obj = scr.scr.view(cls)

        elif isinstance(data[0],bytes) and scr is None:
            scr = SCR(data[0])
            obj = scr.scr.view(cls)

        elif isinstance(data[0], bits) and len(data) == 1 and scr is not None:     # inicializar shares de um input "w"
            w = data[0][:wsize] ; u = scr.scr
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
        if rho is None: rho = shares(urandom(ksize))
        r    = [rho[j] + this[j,0] * other[j,0] + this[j,1] * other[j,1] for j in range(3)] 
        return bits([bits([r[j] + r[(j+2)%3], r[j]]) for j in range(3)]).view(shares)

    def __mul__(self,other):
        return self.mul(other)


app._unparsable_cell(
    r"""
    class SBox(object):
        def __init__(self, shape, key : bytes = None ,  sid : np.uint):
            self.hash = shake_256(b'sbox'+key+str(sid).encode())
            seed = np.frombuffer(hash.digest(ksize),dtype=np.uint8)
            self.rng  = np.random.default_rng(seed)
            (n, m) = shape
            assert n*(n-1) >= 2*m, f"to few inputs or to many outputs"
            all_pairs = list(combinations(range(n),2))
            self._pairs = self.rng.permutation(all_pairs)[:m]

        @property
        def pairs(self):
            return self._pairs

        @pairs.setter
        def pairs(self,shape):
            (n,m) = self._shape
            all_pairs = list(combinations(range(n),2))
            self._pairs = self.rng.permutation(all_pairs)[:m]

        def eval(self, input_shares):
            output_shares = []
            for (i,j) in self.pairs:
                rho = self.scr.scr
                prod = input_shares[i].mul(input_shares[j], rho)
                output_shares.append(prod)
                logs['msg'] = logs['msg'].append(prod.msg)
                logs['rho'] = logs['rho'].append(rho)
            return bits(output_shares)
    """,
    name="_"
)


@app.cell
def _(SBox):
    def Circuit(key : bytes = None):
        if key is None:
            key = urandom(ksize)

        hash = shake_256(b'circuit' + key)
        scr  = SCR()
        logs = {'rho' : [] , 'msg' : []}

        rsize = params['rsize']
        csize = params['csize']
        rounds= params['rounds']

        def split_bytes(s):
            return  bits([bits(a) for a in np.split(np.frombuffer(s, dtype=np.uint8), wsize)])

        def pad(s : bytes, l : int):
            l_ = l - len(s)
            return s + b'\x00'*l_  if l_ > 0  else s[:l] 



        class Permutation(object):
            def __init__(self, sid : bytes = b'\x00\x00'):
                self.top = SBox((rsize, csize)).eval
                self.bot = SBox((csize, rsize)).eval

            def eval(self, rate, capacity):
                for _ in range(rounds):
                    capacity = capacity + self.top(rate)
                    rate     = rate     + self.bot(capacity)
                return (rate, capacity)



        class __main__(object):
            def __init__(self, secret : bytes):
                self.f = Permutation(key).eval 
    #            rate       = bits([shares(bits(r)) for r in split_bytes(pad(iv,wsize*rsize))])[:rsize]
                rate       = bits(pad(b'\x00', wsize*rsize))
                capacity   = bits([shares(bits(c), scr=scr) for c in split_bytes(pad(secret,wsize*csize))])[:csize]
                self.start = self.f(rate, capacity)

            def sponge(self, inputs : bytes , l : int = None):
                inps = bits([shares(bits(r)) for r in split_bytes(inputs)])[:rsize]
                rate, capacity = self.start
                # absorb
                for inp in inps:
                    rate, capacity = self.f(rate + inp, capacity) 
                #squeeze
                out = []
                for _ in range(rsize):
                    rate, capacity = self.f(rate, capacity)
                    out.append(rate)
                return bits(out)

        return __main__

    return (Circuit,)


@app.cell
def _(Circuit):
    class Test_MPC(unittest.TestCase):

        #@unittest.skip("wire")
        def test_wire(self):
            w = bits(urandom(wsize)) ; scr = SCR()
            sh= shares(w, scr=scr)
            self.assertEqual(w, sh.wire)
            sh_ = shares(sh[0],sh[1])
            self.assertEqual(w, sh_.wire)

        #@unittest.skip("ops")
        def test_ops(self):
            w = bits(urandom(wsize)) ; w_ = bits(urandom(wsize)) ; scr=SCR()
            sh = shares(w, scr=scr) ; sh_ = shares(w_, scr=scr)
            self.assertEqual(w + w_ , (sh + sh_).wire)
            self.assertEqual(w * w_ , (sh * sh_).wire)

        @unittest.skip("circuit")
        def test_circuit(self):
            secret = urandom(csize)
            circuit = Circuit()(secret)
            self.assertTrue(True)

    return


if __name__ == "__main__":
    app.run()
