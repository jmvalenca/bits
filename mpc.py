# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.23.3",
#     "numpy==2.4.6",
#     "pytest==9.0.3",
# ]
# ///

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", auto_download=["html"])

with app.setup:
    import marimo as mo
    from bits import bits
    import numpy as np
    from hashlib import shake_256
    from collections.abc import Collection
    from secrets import randbits, token_bytes, choice
    from itertools import combinations
    from dataclasses import dataclass
    from config import config_MPC
    import math
    import pytest
    import typing
    params = config_MPC().__dict__

    globals().update(params)
    parties : int = params['parties']
    ksize   : int = params['ksize']
    wsize   : int = params['wsize']
    csize   : int = params['csize']
    rsize   : int = params['rsize']
    iosize  : int = params['iosize']
    rounds  : int = params['rounds']

    wzero = bits(np.zeros(wsize, dtype=np.uint8))
    wrand = lambda : bits(token_bytes(wsize))
    pad   = lambda b, n: b[:n] if len(b) > n else b + b'\x00'*(n-len(b))
    def chunks(l : Collection , n : int):
        assert n > 0
        bloc = len(l) // n ; rem = len(l) - n*bloc
        blocs = [l[k*bloc:(k+1)*bloc] for k in range(n)]
        return blocs + [l[-rem:]] if rem > 0 else blocs


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Source
    Based on the paper "High-Throughput Semi-Honest Secure Three-Party Computation with an Honest Majority", Toshinori Araki et al. CCS'16
    The implementation uses a circuit describing a symmetric cypher with a sponge construction in which every permutation is derived, via a Feistel strucure, from two pseudo-randomly generated sboxes. Thus every party  can build the same circuit from a common random key.
    """)
    return


@app.class_definition
class RNG(object):
    def __init__(self, key : int = None):
        if key is None: key = randbits(ksize)
        self._key = key
        self._master = np.random.default_rng(key)
        self.spawns  = self._master.spawn(parties)


    @property
    def master(self):
        return self._master

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value):
        self._key = value


    @property
    def rho(self):
        f = lambda party: bits(self.spawns[party].integers(256,size=wsize,dtype=np.uint8))
        return bits([f(i) for i in range(parties)])

    @property
    def scr(self):
        rs = self.rho
        return bits([rs[i]+rs[(i+parties-1)%parties] for i in range(parties)])

    @property
    def encaps(self):
        rs = self.scr
        return bits([[rs[i], rs[(i+parties-1)%parties]] for i in range(parties)])


@app.class_definition
@dataclass
class message:
    rho  : bits
    mu   : bits


@app.class_definition
class share(bits):  # views
    def __new__(cls, *data , encap : bits = None):

        if isinstance(data[0], bits) and len(data) == 1 and encap is None:
            obj = bits([wzero , data[0]]).view(cls)
  
        elif isinstance(data[0], bits) and len(data) == 1 and encap is not None:
            if isinstance(encap,bits) and encap.shape == (2,wsize):
                obj = encap.view(share) + share(data[0])   
            else:
                raise ValueError(f"do not know how to make a shares object from {data,encap}")

        elif isinstance(data[0], bits)  and len(data) == 2:   # restore a partiesa. view a partir de duas views
#           
            v_0 = data[0][0].lift ; mu_0 = data[0][1].lift 
            v_1 = data[1][0].lift ; mu_1 = data[1][1].lift 
            v_2 = v_0 + v_1
            w1 = mu_1 + v_0 ; w0 = mu_0 + v_2 
            assert w1 == w0 , f"inconsistent shares for the same wire"
            obj = share(w1 , encap = bits([v_2 , v_1]))

        else:
            raise ValueError(f"do not know how to make a shares object from {data}")
        return obj


    def __array_finalize__(self, obj):
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

    def wire(self, other, tau = wzero):
        ws = self + other + share(self,other)
        return ws[1].view(bits) + tau


    def add(self,other):
        return (self.lift + other.lift).view(share)

    def __add__(self, other):
        return self.add(other)

    def multiply(self, other , msg : message = None):
        if msg is None:
            msg = message(wzero,wzero)
        this = self.lift ; another = other.lift
        r    = msg.rho + this[0] * another[0] + this[1] * another[1]
        return bits([r + msg.mu, r]).view(share)

    def __mul__(self,other):
        return self.multiply(other)


@app.class_definition
class shares(bits):
    def __new__(cls, x : bits , rng : RNG = None, tau : bits = wzero):
        if rng is None:
            return np.array([share(x) for _ in range(parties)]).view(cls)
        assert isinstance(rng, RNG)
        obj =  np.array([share(x + tau, encap=e) for e in rng.encaps]).view(cls)
        obj._tau = tau
        return obj

    def __array_finalize__(self, obj):
        if obj is None: return
        self._tau = getattr(obj, 'tau', wzero)

    @property
    def lift(self):
        return self.view(bits)

    @property
    def tau(self):
        return self._tau

    @tau.setter
    def tau(self, value):
        self._tau = value

    def roll(self):
        return np.roll(self,(0,2,0),axis=(0,0,0)).view(shares)

    @property
    def wire(self):
        w = self.lift
#        return sum(w[:,0]) + sum(w[:,1]) 
        return sum(w[:,1]) + self.tau

    def share(self,party):
        return self[party].view(share)

    def add(self, other):
        res =  (self.lift + other.lift).view(shares)
        res.tau = self.tau + other.tau
        return res

    def __add__(self, other):
        return self.add(other)


    def multiply(self, other, rng : RNG):
        rho = rng.scr 
        # rho = rng.rho
        Tau = (self.wire)*(other.tau) + (other.wire)*(self.tau) + (self.tau)*(other.tau) 
        this = self.lift ; other_ = other.lift        
        rs   = [rho[i] + this[i,0] * other_[i,0] + this[i,1] * other_[i,1] for i in range(parties)]
        #ms   = [rs[(i+parties-1)%parties] + Tau  for i in range(parties)]
        ms   = [rs[(i+parties-1)%parties] for i in range(parties)]
        res  = bits([[r + m, r] for (r,m) in zip(rs,ms)]).view(shares)
        res.tau = Tau  
        return res,  [message(rho=r,mu=m) for (r,m) in zip(rho,ms)]


@app.class_definition
class SBox(object):
    def __init__(self, shape, master):
        assert isinstance(master, np.random.Generator)
        (n, m) = shape
        assert n*(n-1) >= 2*m, f"to few inputs or to many outputs"
        all_pairs = list(combinations(range(n),2))
        self._pairs = master.permutation(all_pairs)[:m]

    @property
    def pairs(self):
        return self._pairs


    def eval(self, inps : bits):
        ys = []
        for (i,j) in self.pairs:
            y     = inps[i] * inps[j]
            ys.append(y)
        return bits(ys)


    def evalp(self, inps, msgs):     
        # inps é umarray de elementos do tipo share
#        assert all([isinstance(i,share) for i in inps]), f"every input must be an instance of \"share\"\"
        gate = 0 ; ys = []
        for (i,j) in self.pairs:
            y     = inps[i].multiply(inps[j], msgs[gate])
            ys.append(y)
            gate += 1
        return ys


    def evals(self, inps, rng):
#        assert all([isinstance(i,shares) for i in inps]), f"every input must be an instance of \"shares\"\"
        gate = 0; ys = []; msgs = []
        for (i,j) in self.pairs:
            y, m = inps[i].multiply(inps[j], rng)
            ys.append(y); msgs.append(m)
            gate +=1
        return ys, msgs


@app.class_definition
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

    def evalp(self, inps, msgs):
        rate = inps[:rsize] ; capacity = inps[rsize:] 
        for msg in chunks(msgs,rounds):
            msgs_top = msg[:csize] ; msgs_bot = msg[csize:]
            capacity_ = self.top.evalp(rate, msgs_top)
            capacity = [capacity[i] + capacity_[i] for i in range(csize)]
            rate_ = self.bot.evalp(capacity, msgs_bot)
            rate  = [rate[i] + rate_[i] for i in range(rsize)]
        return rate + capacity

    def evals(self, inps, rng):
        rate = inps[:rsize] ; capacity = inps[rsize:] 
        msgs = []
        for _ in range(rounds):
            capacity_ , m = self.top.evals(rate, rng) ; msgs += m
            capacity = [capacity[i] + capacity_[i] for i in range(csize)]
            rate_ , m = self.bot.evals(capacity, rng); msgs += m
            rate = [rate[i] + rate_[i] for i in range(rsize)]
        return rate + capacity , msgs


@app.class_definition
class Circuit(object):

    def __init__(self, key : bytes):
        self._key = key
        R = RNG(key)
        self._Perm = Permutation(R.master) 

    @property
    def key(self):
        return self._key

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


    def evalp(self, start, inps, msgs):
        msgs_ = chunks(msgs, 1+len(inps))
        state = self.Perm.evalp(start, msgs_[0])
        for (inp, msg) in zip(inps, msgs_[1:]):
            for k in range(rsize):
                state[k] = state[k].view(share) + inp[k].view(share)
            state = self.Perm.evalp(state, msg)
        for k in range(csize):
            state[rsize + k] = start[rsize + k].view(share) + state[rsize + k].view(share)
        return state[rsize:]


    def evals(self, start, inps, rng):
        state, msgs = self.Perm.evals(start, rng)
        # sponge absorb
        for inp in inps:
            for k in range(rsize):
                state[k] =  state[k].view(shares) + inp[k].view(shares)
            state, ms  = self.Perm.evals(state, rng)
            msgs = msgs + ms
        # sponge finalize
        for k in range(csize):
            state[rsize + k] = start[rsize + k].view(shares) + state[rsize + k].view(shares)
        return state[rsize:], msgs


@app.class_definition
class Data(object):   # implementation of View for prover and parties


    def __init__(self, inputs : bytes, iv : int = 0, secret : int = -1):     

        
        blocs        = math.ceil(len(inputs) /(rsize * wsize))
        self.inputs_ = bits(pad(inputs, blocs*rsize*wsize)).reshape(blocs,rsize,wsize)

        self.rate_    = bits(iv.to_bytes(rsize*wsize)).reshape(rsize,wsize)
        if secret <= 0:
            secret = randbits(8*csize*wsize)
        self.capacity_ = bits(secret.to_bytes(csize*wsize)).reshape(csize,wsize)

        rate       = [shares(r) for r in self.rate_]
        self.R     = RNG()
        capacity   = [shares(s, rng=self.R, tau=wrand()) for s in self.capacity_]
        self.start_shares =  rate + capacity

    @property
    def rng(self):
        return self.R
    @rng.setter
    def rng(self, seed : int):
        if seed < 0:
            self.R = RNG()
        else:
            self.R = RNG(seed)


    @property
    def start(self):
        return np.concatenate([self.rate_, self.capacity_]).view(bits)

    @property
    def inp(self):
        return self.inputs_

    @property
    def starts(self):
        return self.start_shares

    @property
    def inps(self):
        blocs = len(self.inputs_)
        return [[shares(self.inputs_[i,j]) for j in range(rsize)] for i in range(blocs)]

    def startp(self, party):
        return [s.share(party) for s in self.start_shares]

    @property
    def inpp(self):
        blocs = len(self.inputs_)
        return [[share(self.inputs_[i,j]) for j in range(rsize)] for i in range(blocs)]


@app.function
def mpcITH():
    class KeyGen(object):
        def __init__(self):
            pass
    
    class Prover(object):
        def __init__(self, public_key, private_key):
            pass
        def Committ(self):
            pass 
        def Prove(self,c):
            pass

    class Verifier(object):
        def __init__(self, public_key):
            pass
        def Challenge(self):
            pass
        def Verify(self):
                        pass


    class __main__(object):
        def __init__(self, key : bytes, inputs):
            pass


        def run(self, secret, inputs):
            pass


if __name__ == "__main__":
    app.run()
