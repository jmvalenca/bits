# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.23.2",
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



app._unparsable_cell(
    r"""
    class SCR(object):
        def __init__(self, master_key : bytes = None:
            if master_key is None : key
            self.hash = shake_256(b'master'+ master_key)
            self._keys = bits(np.split(bits(self.hash.digest(3*wsize)),3))
            self._prgs = [np.random.default_rng(k) for k in self._keys]
 

        @property
        def keys(self):
            return self._keys
        @keys.setter
        def keys(self,sid : np.uint16):
            self.hash.update(str(sid).encode())
            self._keys = bits(np.split(bits(self.hash.digest(3*wsize)),3))
            self._prgs = [np.random.default_rng(k) for k in self._keys]
        @property
        def prgs(self):
            return self._prgs
        @property    
        def scr(self):
            p  = self.prgs
            s = [bits(p[j].integers(256, dtype=np.uint8, size=wsize)) for j in range(3)]
            return bits([s[j] + s[(j+2)%3]  for j in range(3)])
    """,
    name="_"
)


app._unparsable_cell(
    r"""
    class shares(bits):  # views
        def __new__(cls, *data):

            if len(data) == 0 or isinstance(data, bytes):
        

            elif isinstance(data , bytes):
                obj = shares(key=data)

            elif isinstance(data[0], bits) and len(data) == 1:     # inicializar shares de um input "w"
                w = data[0][:wsize]
                u = shares(key=w.hash())
                obj = bits([bits([u[0], w + u[2]]) , bits([u[1], w + u[0]]) , bits([u[2], w + u[1]])]).view(cls)

            elif isinstance(data[0], bits) and len(data) > 1:   # restore a 3a. view a partir de duas views
    #            j = 0; i = 1; k = 2
                x_0 = data[0][0] ; m_0 = data[0][1] ; x_1 = data[1][0] ; m_1 = data[1][1] ; x_2 = x_0 + x_1  
                w = m_1 + x_0 ; w_ = m_0 + x_2 ; m_2 = w + x_1
                assert w == w_ , f"shares inconsistentes"
                obj = bits([data[0], data[1], bits([x_2,m_2])]).view(shares)

            else:
                raise ValueError(f"do not knw how to make a bits object from {data}")
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

        def add(self,other):
            return (self.lift() + other.lift()).view(shares)

        def __add__(self, other):
            return self.add(other)

        def mul(self, another , rho = None , views = None):
            this = self.lift() ; other = another.lift()
            if rho is None:
                rho  = shares(key=urandom(ksize)).lift()     
            r    = [rho[j] + this[j,0] * other[j,0] + this[j,1] * other[j,1] for j in range(3)]
            m    = [r[(j+2) % 3 ] for j in range(3)]   #   "push" n num qualquer estado   
            if views is not None:
                for j in range(3):
                    views[j].msgs.append(m[j])
            res =  bits([bits([r[j] + m[j], r[j]]) for j in range(3)])
            return res.view(shares)

        def __mul__(self,other):
            return self.mul(other)
    """,
    name="*shares"
)


@app.cell
def _(self):
    class view(bits):    # Views
        def __new__(cls, *data):
            self.sshare = None

    return


@app.cell
def _(shares):
    def Circuit(key : bytes = None):
        if key is None:
            key = urandom(ksize)
        rsize = params['rsize']
        csize = params['csize']
        rounds= params['rounds']

        split_bytes = lambda s: np.split(np.frombuffer(s, dtype=np.uint8), wsize)
        def pad(s : bytes, l : int):
            l_ = l - len(s)
            return s + b'\x00'*l_  if l_ > 0  else s[:l] 

        class SBox(object):
            def __init__(self, shape , key : bytes = None):
                if key is None:
                    key = urandom(ksize)
                self._key = key
                self.rng  = np.random.default_rng(np.frombuffer(key, dtype=np.uint8))
                (n, m) = shape
                assert n*(n-1) >= 2*m, f"to few inputs or to many outputs"
                all_pairs = list(combinations(range(n),2))
                self._pairs = self.rng.permutation(all_pairs)[:m]

            @property
            def key(self):
                return self._key

            @key.setter
            def key(self, value):
                self._key = value
                self.rng = np.random.default_rng(np.frombuffer(self._key, dtype=np.uint8))

            @property
            def pairs(self):
                return self._pairs

            @pairs.setter
            def pairs(self,shape):
                (n,m) = self._shape
                all_pairs = list(combinations(range(n),2))
                self._pairs = self.rng.permutation(all_pairs)[:m]

            def eval(self, input_shares : bits):
                output_shares = []
                for (i,j) in self.pairs:
                    output_shares.append(input_shares[i] * input_shares[j])
                return bits(output_shares)

        class Permutation(object):
            def __init__(self):
                self.top = SBox((rsize, csize), key = key + b'top').eval
                self.bot = SBox((csize, rsize), key = key + b'bot').eval

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
                capacity   = bits([shares(bits(c)) for c in split_bytes(pad(secret,wsize*csize))])[:csize]
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
def _(Circuit, shares):
    class Test_MPC(unittest.TestCase):

        #@unittest.skip("wire")
        def test_wire(self):
            w = bits(urandom(wsize)) ; key=urandom(ksize)
            sh= shares(w , key=key)
            self.assertEqual(w, sh.wire)
            sh_ = shares(sh[0],sh[1])
            self.assertEqual(w, sh_.wire)

        #@unittest.skip("ops")
        def test_ops(self):
            w = bits(urandom(wsize)) ; w_ = bits(urandom(wsize))
            sh = shares(w) ; sh_ = shares(w_)
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
