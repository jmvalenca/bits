# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.23.3",
#     "numpy==2.4.6",
#     "pytest==9.0.3",
# ]
# ///

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium", auto_download=["html"])

with app.setup:
    import marimo as mo
    from bits import bits
    import asyncio as asio
    import numpy as np
    from hashlib import shake_256
    from collections.abc import Callable
    from secrets import randbits, token_bytes
    from itertools import combinations
    from dataclasses import dataclass
    from config import config_MPC
    import math
    import pytest

    params = config_MPC().__dict__
    globals().update(params)
    ksize : int = params['ksize']
    wsize : int = params['wsize']
    csize : int = params['csize']
    rsize : int = params['rsize']
    iosize: int = params['iosize']
    rounds: int = params['rounds']
    wzero = bits(np.zeros(wsize, dtype=np.uint8))
    wrand = lambda : bits(token_bytes(wsize))


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Source
    Based on the paper "High-Throughput Semi-Honest Secure Three-Party Computation with an Honest Majority", Toshinori Araki et al. CCS'16
    The implementation uses a circuit describing a symmetric cypher with a sponge construction in which every permutation is derived, via a Feistel strucure, from two pseudo-randomly generated sboxes. Thus every party  can build the same circuit from a common random key.
    """)
    return


@app.cell
def _():
    class RNG(object):
        def __init__(self, key : int = None):
            if key is None: key = randbits(ksize)
            self._key = key
            self._master = np.random.default_rng(key)
    #        self.seeds   = [self._master.bytes(ksize)  for _ in range(3)]
            self.spawns  = self._master.spawn(3)


        @property
        def master(self):
            return self._master

        @property
        def key(self):
            return self._key

        @key.setter
        def key(self, value):
            self._key = value

        def f(self, party):  
            return lambda : bits(self.spawns[party].integers(256,size=wsize,dtype=np.uint8))
    """
        def F(self, party : int):
            def _S(party, gate : int = 0):
                g_id = str(gate).encode()
                return bits(shake_256(self.seeds[party] + g_id).digest(wsize))
            return lambda gate : _S(party, gate) + _S((party + 2)%3, gate)
    """
    return (RNG,)


@app.cell(hide_code=True)
def _(RNG):
    class Test_RNG():

        def test_scr(self):
            R = RNG()
            gate = randbits(16)
            a,b,c = R.F(0)(gate), R.F(1)(gate), R.F(2)(gate)
            assert a + b + c == np.zeros(wsize)

        def test_types(self):
            R = RNG()
            assert isinstance(R.master, np.random.Generator)

        def test_F(self):
            R = RNG()
            F = R.F ; FF = R.FF
            gate = randbits(16)
            a, b, c = F(0)(gate) , F(1)(gate) , F(2)(gate) 
            aa, bb, cc = FF(0)(gate) , FF(1)(gate) , FF(2)(gate) 
            assert a.shape == (wsize,) and aa.shape == (2,wsize)

    return


@app.class_definition
class share(bits):  # views
    def __new__(cls, *data , encap : bits = None):

        if isinstance(data[0], bits) and len(data) == 1 and encap is None:
            obj = bits([wzero , data[0]]).view(cls)

        elif isinstance(data[0], bits) and len(data) == 1 and encap is not None:
            if isinstance(encap,bits) and encap.shape == (2,wsize):
                obj = encap.view(share) + share(data[0])
#            elif isinstance(encap,np.uint8):
#                e = bits([encap]); r = data[0]
#                obj = bits([r + e, r]).view(cls)    
            else:
                raise ValueError(f"do not know how to make a shares object from {data,encap}")

        elif isinstance(data[0], bits)  and len(data) == 2:   # restore a 3a. view a partir de duas views
#            j = 0; i = 1; k = 2
            v_0 = data[0][0] ; mu_0 = data[0][1] ; v_1 = data[1][0] ; mu_1 = data[1][1] 
            v_2 = v_0 + v_1  ; w = mu_1 + v_0 ; w_ = mu_0 + v_2 
            assert w == w_ , f"inconsistent shares for the same wire {w} != {w_}"
            obj = share(w , encap = bits([v_2 , v_1]))

        else:
            raise ValueError(f"do not know how to make a shares object from {data}")
        return obj


    def __array_Finalize__(self, obj):
        if obj is None: return

    def __str__(self):
        return np.array_str(self)

    def __repr__(self):
        return np.array_repr(self) 

    @property
    def lift(self):
        return self.view(bits)

    def flip(self):
        return np.flip(self, axis=0).view(share)

    def wire(self, other):
        ws = self + other + share(self,other)
        assert ws[0] == 0, f"wire ws={ws} is inconsistent"
        return ws[1].view(bits)


    def add(self,other):
        return (self.lift + other.lift).view(share)

    def __add__(self, other):
        return self.add(other)

    def multiply(self, other , encap : bits):
        assert encap.shape ==  (2,wsize)
        rho = encap[0] ; mu = encap[1]
        this = self.lift ; another = other.lift
        r    = rho + this[0] * another[0] + this[1] * another[1]
        return bits([r + mu, r]).view(share)


    def __mul__(self,other):
        return self.multiply(other)


@app.cell(hide_code=True)
def _(RNG):
    class Test_share():

        def test_1wire(self):
            R = RNG()
            x = wrand()
            msg0 = R.FF(0)(0) ; msg1 = R.FF(1)(0) ; msg2 = R.FF(2)(0)
            s0   = share(x, encap=msg0) ; s1 = share(x, encap=msg1) ; s2 = share(x, encap=msg2)
            s3   = share(s0,s1)
            assert (s2 == s3)
            assert (s0.wire(s1)== x)

        def test_ops(self):
            R = RNG(); p = R.FF(0)
            x = share(wrand(),encap=p(0))
            y = share(wrand(),encap=p(1))
            z = share(wrand(),encap=p(2))

            aX = p(3) ; aY = p(4) ; aXY = aX + aY
            u  = x.multiply(z, encap = aX) ; v = y.multiply(z , encap = aY)
            assert u.ndim == x.ndim
            assert (x + y).multiply(z , encap = aXY) ==  u + v

    return


@app.cell
def _(RNG, shares):
    class Data(object):   # implementation of View for prover and parties


        def __init__(self, secret : int , inputs : bytes,   iv : int = 1):     
            R = RNG(secret*iv)
            pad        = lambda b, n: b[:n] if len(b) > n else b + b'\x00'*(n-len(b))  
    #        if iv is None: iv = randbits(8*rsize*wsize)
            self.R     = R
            self.rate_      = bits(iv.to_bytes(rsize*wsize)).reshape(rsize,wsize)
            self.capacity_  = bits(secret.to_bytes(csize*wsize)).reshape(csize,wsize)
            blocs           = math.ceil(len(inputs) /(rsize * wsize))
            self.inputs_    = bits(pad(inputs, blocs*rsize*wsize)).reshape(blocs,rsize,wsize)

        @property 
        def start(self):
            return np.concatenate([self.rate_, self.capacity_]).view(bits)

        @property
        def inp(self):
            return self.inputs_

        @property
        def starts(self):
            rate       = [shares(r) for r in self.rate_]
            capacity   = [shares(s, self.R.F) for s in self.capacity_]
            return rate + capacity

        @property
        def inps(self):
            blocs = len(self.inputs_)
            return [[shares(self.inputs_[i,j],self.R.F,gate=i*rsize+j) for j in range(rsize)] for i in range(blocs)]

        def startp(self, party):
            rate       = [share(self.rate_[i], encap=self.R.FF(party)(i)) for i in range(rsize)]
            capacity   = [shares(self.capacity_[i], encap=self.R.FF(party)(i + rsize)) for i in range(csize)]
            return rate + capacity

        def inpp(self,party):
            blocs = len(self.inputs_)
            return [[share(self.inputs_[i,j], encap=self.R.FF(party)(i*rsize + j)) for j in range(rsize)] \
                    for i in range(blocs)]

    return (Data,)


@app.cell(hide_code=True)
def _(Data):
    class Test_data():
        def test_init(self):
            secret = randbits(csize*wsize) ; inputs = token_bytes(rounds * rsize * wsize)
            data = Data(secret, inputs)
            party = np.random.randint(3)

    return


@app.cell
def _(shares):
    class SBox(object):
        def __init__(self, shape, master):
            assert isinstance(master, np.random.Generator)
            (n, m) = shape
            assert n*(n-1) >= 2*m, f"to few inputs or to many outputs"
            all_pairs = list(combinations(range(n),2))
            self._pairs = master.permutation(all_pairs)[:m]
            self._master= master
            self._shape = shape 

        @property
        def pairs(self):
            return self._pairs

        @property
        def master(self):
            return self._master

        @property
        def shape(self):
            return self._shape

        def eval(self, inps : bits):
            ys = []
            for (i,j) in self.pairs:
                y     = inps[i] * inps[j]
                ys.append(y)
            return bits(ys)


        def evalp(self, inps, f , msg):     
            # inps é umarray de elementos do tipo share
            assert all([isinstance(i,share) for i in inps]), f"every input must be an instance of \"share\""
            gate = 0 ; ys = []
            for (i,j) in self.pairs:
                encap = bits([f(gate), msg[gate]])
                y     = inps[i].multiply(inps[j], encap)
                ys.append(y)
                gate += 1
            return ys


        def evals(self, inps):
            assert all([isinstance(i,shares) for i in inps]), f"every input must be an instance of \"shares\""
            gate = 0; ys = []; msgs = []
            for (i,j) in self.pairs:
                y, m = inps[i].multiply(inps[j], gate)
                ys.append(y); msgs.append(m)
                gate +=1
            return ys, msgs

    return (SBox,)


@app.cell(hide_code=True)
def _(RNG, SBox, shares):
    class Test_Sbox():

        def test_evals(self):
            R = RNG() 
            S = SBox((rsize,csize), R.master)
            F  = R.F 
            party = np.random.randint(3)

            xs   = [wrand() for _ in range(rsize)]
            inps = [shares(x, F) for x in xs]
            outs, msgs = S.evals(inps)

            msg = [m[party] for m in msgs] 
            out = [o.share(party) for o in outs]
            inp = [i.share(party) for i in inps]

            assert out == S.evalp(inp, F(party), msg)

    return


@app.cell
def _(SBox):
    class Permutation(object):
        def __init__(self, master):
            self.top = SBox((rsize, csize), master)
            self.bot = SBox((csize, rsize), master)


        def eval(self, inps : bits):
            rate = inps[:rsize] ; capacity = inps[rsize:] 
            for _ in range(rounds):
                capacity  = capacity + self.top.eval(rate)
                rate      = rate + self.bot.eval(capacity)
            return np.concatenate([rate, capacity]).view(bits)

        def evalp(self, inps, f , msgs):
            rate = inps[:rsize] ; capacity = inps[rsize:] 
            for msg in np.split(bits(msgs), rounds):
                msgs_top = msg[:csize] ; msgs_bot = msg[csize:]
                capacity_ = self.top.evalp(rate, f, msgs_top)
                capacity = [capacity[i] + capacity_[i] for i in range(csize)]
                rate_ = self.bot.evalp(capacity, f , msgs_bot)
                rate  = [rate[i] + rate_[i] for i in range(rsize)]
            return rate + capacity

        def evals(self, inps):
            rate = inps[:rsize] ; capacity = inps[rsize:] 
            msgs = []
            for _ in range(rounds):
                capacity_ , m = self.top.evals(rate) ; msgs += m
                capacity = [capacity[i] + capacity_[i] for i in range(csize)]
                rate_ , m = self.bot.evals(capacity); msgs += m
                rate = [rate[i] + rate_[i] for i in range(rsize)]
            return rate + capacity , msgs

    return (Permutation,)


@app.cell(hide_code=True)
def _(Permutation, RNG, shares):
    class Test_Permutation():
        def test_evals(self):
            R = RNG(); F = R.F ; master = R.master
            P = Permutation(master)
            xs   = [wrand() for _ in range(iosize)]
            inps = [shares(x, F) for x in xs]
            outs, msgs = P.evals(inps)

            party = np.random.randint(3)
            msg = [bits(m[party]) for m in msgs]
            out = [o.share(party) for o in outs]
            inp = [i.share(party) for i in inps]
            out_= P.evalp(inp, F(party), msg)

            assert out == out_

    return


@app.cell
def _(Permutation, RNG, shares):
    class Circuit(object):

        def __init__(self, key : bytes):
            R = RNG(key)
            self._Perm = Permutation(R.master) 

        @property
        def Perm(self):
            return self._Perm

        def eval(self, start, inps):
            state = self.Perm.eval(start)
            # sponge absorb
            for inp in inps:
                for k in range(rsize):
                    state[k] =  state[k] + inp[k]
                state = self.Perm.eval(state)
            # sponge finalize
            for k in range(csize):
                state[rsize + k] = start[rsize + k] + state[rsize + k]
            return state[rsize:]

        def evals(self, start, inps):
            state, msgs = self.Perm.evals(start)
            # sponge absorb
            for inp in inps:
                for k in range(rsize):
                    state[k] =  state[k].view(shares) + inp[k].view(shares)
                state, ms  = self.Perm.evals(state)
                msgs = msgs + ms
            # sponge finalize
            for k in range(csize):
                state[rsize + k] = start[rsize + k].view(shares) + state[rsize + k].view(shares)
            return state[rsize:], msgs

        def evalp(self, start, inps, f, msgs):
            msgs_ = np.split(bits(msgs), 1+len(inps))
            state = self.Perm.eval(start, f, msgs_[0])
            for (inp, msg) in zip(inps, msgs_[1:]):
                for k in range(rsize):
                    state[k] = state[k].view(share) + inp[k].view(share)
                state = self.Perm.eval(state, f , msg)
            for k in range(csize):
                state[rsize + k] = start[rsize + k].view(share) + state[rsize + k].view(share)
            return state[rsize:]

    return (Circuit,)


@app.class_definition
class Test_Circuit():
    pass


@app.cell
def _(Circuit, Data):
    def mpc_in_the_head():

        class Prover(object):
            def __init__(self, secret):
                pass
            def Committ(self,pk,sk):
                pass 
            def Prove(self,c):
                pass

        class Verifier(object):
            def __init__(self):
                pass
            def Challenge(self):
                pass

        class __main__(object):
            def __init__(self, c_key:bytes, inputs : bytes):
                self.C  = Circuit(int.from_bytes(c_key))
                self._inps =  inputs
                self._outs =  None
                self._iv   = 0
            def run(self, secret):
                self._iv += 1
                data = Data(secret, self._inps, self._iv)
                self._outs = self.C.eval(data.start, data.inp) 


        return __main__

    return (mpc_in_the_head,)


@app.cell
def _(mpc_in_the_head):
    class Test_mpc_in_the_head():
        def test_init(self):
            c_key = token_bytes(ksize)
            secret = randbits(2*ksize)
            blocs  = 4
            inputs = token_bytes(blocs*rsize*wsize)
            mpc = mpc_in_the_head()(c_key, inputs)
            mpc.run(secret)

    return


if __name__ == "__main__":
    app.run()
