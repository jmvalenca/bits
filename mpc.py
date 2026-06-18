# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.23.3",
#     "numpy==2.4.6",
#     "pytest==9.0.3",
# ]
# ///

import marimo

__generated_with = "0.23.9"
app = marimo.App(width="medium", auto_download=["html"])

with app.setup:
    import marimo as mo
    from bits import bits
    import numpy as np
    from hashlib import shake_256
    from collections.abc import Collection
    from secrets import randbits, token_bytes
    from itertools import combinations
    from dataclasses import dataclass
    from config import config_MPC
    import math
    import pytest
    import typing
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
    pad   = lambda b, n: b[:n] if len(b) > n else b + b'\x00'*(n-len(b))
    def chunks(l : Collection , n : int):
        assert n > 0
        bloc = len(l) // n ; rem = len(l) - n*bloc
        blocs = [l[k*bloc:(k+1)*bloc] for k in range(n)]
        return blocs + [l[-rem:]] if rem > 0 else blocs


@app.cell
def _():
    l = range(15)
    isinstance(l, Collection)
    l[0]
    return


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

    @property
    def rho(self):
        return bits([self.f(i)() for i in range(3)])

    @property
    def encaps(self):
        rs = self.rho
        return bits([[rs[i], rs[(i+2)%3]] for i in range(3)])


@app.class_definition
class Test_RNG():

    def test_types(self):
        R = RNG()
        assert isinstance(R.master, np.random.Generator)

#    @pytest.mark.skip(reason="needs debugging")
    def test_f(self):
        R = RNG() 
        rho = R.rho

    def  test_encaps(self):
        es = RNG().encaps
        assert sum(es[:,0]) == sum(es[:,1])


@app.class_definition
@dataclass
class message:
    rho  : bits
    mu   : bits


@app.class_definition
class share(bits):  # views
    def __new__(cls, *data , encap : bits = None, tau : bits = None):

        if isinstance(data[0], bits) and len(data) == 1 and encap is None:
            obj = bits([wzero , data[0]]).view(cls)

        elif isinstance(data[0], bits) and len(data) == 1 and encap is not None:
            if isinstance(encap,bits) and encap.shape == (2,wsize):
                obj = encap.view(share) + share(data[0])   
            else:
                raise ValueError(f"do not know how to make a shares object from {data,encap}")

        elif isinstance(data[0], bits)  and len(data) == 2:   # restore a 3a. view a partir de duas views
#           
            v_0 = data[0][0].lift ; mu_0 = data[0][1].lift 
            v_1 = data[1][0].lift ; mu_1 = data[1][1].lift 
            v_2 = v_0 + v_1
            if tau is not None:
                v_2 = v_2 + tau
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

    def wire(self, other, tau = None):
        ws = self + other + share(self,other, tau=tau)
        return (ws[0] + ws[1]).view(bits)


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
class Test_share():

    def test_1wire(self):
        es = RNG().encaps ; t = sum(es[:,0])
        assert t == sum(es[:,1])
        x = wrand()
        a,b,c   = (share(x, encap=e) for e in es)
        s       = share(a, b, tau=t)
        assert c == s
        assert a.wire(b,tau=t) == x


@app.class_definition
class shares(bits):
    def __new__(cls, x : bits , rng : RNG = None):
        if rng is None:
            return np.array([share(x) for _ in range(3)]).view(cls)
        assert isinstance(rng, RNG)
        return np.array([share(x, encap=e) for e in rng.encaps]).view(cls)


    def __array_finalize__(self, obj):
        if obj is None: return


    @property
    def lift(self):
        return self.view(bits)

    @property
    def tau(self):
        w = self.lift
        return sum(w[:,0])

    def roll(self):
        return np.roll(self,(0,2,0),axis=(0,0,0)).view(shares)

    @property
    def wire(self):
        w = self.lift
        return sum(w[:,0]) + sum(w[:,1]) 


    def share(self,party):
        return self[party].view(share)

    def add(self, other):
        res =  (self.lift + other.lift).view(shares)
        return res

    def __add__(self, other):
        return self.add(other)


    def multiply(self, other, rng : RNG):
        rho = rng.rho ; Tau = sum(rho) + (self.wire)*(other.tau) + (other.wire)*(self.tau)
        this = self.lift ; other_ = other.lift        
        rs   = [rho[i] + this[i,0] * other_[i,0] + this[i,1] * other_[i,1] for i in range(3)]
        ms   = [rs[(i+2)%3] + Tau  for i in range(3)]
        res  = bits([[r + m, r] for (r,m) in zip(rs,ms)]).view(type=shares)
        return res,  [message(rho=r,mu=m) for (r,m) in zip(rho,ms)]


@app.class_definition
class Test_shares():
#    @pytest.mark.skip(reason="needs debugging")
    def test_wire_add(self):
        R = RNG()
        x_ , y_ , z_ = wrand(), wrand(), wrand()
        x   = shares(x_, rng=R) ; y = shares(y_, rng=R) ; z = shares(z_,rng=R)
        assert (x + y).wire == x.wire + y.wire
        assert (x + y) + z == x + (y + z)
        assert (x + y).tau == x.tau + y.tau

#    @pytest.mark.skip(reason="needs debugging")
    def test_mult0(self):
        R = RNG() 
        x_  = wrand(); y_ = wrand() ; w_ = x_ * y_
        x   = shares(x_, rng=R) ; y = shares(y_, rng=R) ; w = shares(w_, rng=R)
        p, _   = x.multiply(y, rng=R)
        assert p.wire == w.wire


@app.class_definition
class Data(object):   # implementation of View for prover and parties


    def __init__(self, inputs : bytes, iv : int = 2**(rsize*wsize)-1):     

        self.rate_   = bits(iv.to_bytes(rsize*wsize)).reshape(rsize,wsize)
        blocs        = math.ceil(len(inputs) /(rsize * wsize))
        self.inputs_ = bits(pad(inputs, blocs*rsize*wsize)).reshape(blocs,rsize,wsize)
        self.R       = None
        self.capacity_ = None
        self.start_shares = None

    @property
    def has_rng(self):
        return self.R is not None
    @property
    def rng(self):
        return self.R
    @rng.setter
    def rng(self, secret : int):
        if secret <= 0:
            secret = randbits(8*csize*wsize)
        self.R = RNG(secret)
        self.capacity_  = bits(secret.to_bytes(csize*wsize)).reshape(csize,wsize)


    def start(self):
        assert self.capacity_
        return np.concatenate([self.rate_, self.capacity_]).view(bits)

    @property
    def inp(self):
        return self.inputs_

    @property
    def starts(self):
        assert self.has_rng
        return self.start_shares

    @starts.setter
    def starts(self, rng):
        if rng is None:
            rng = self.rng
        rate       = [shares(r) for r in self.rate_]
        capacity   = [shares(s, rng=rng) for s in self.capacity_]
        self.start_shares =  rate + capacity

    @property
    def inps(self):
        blocs = len(self.inputs_)
        return [[shares(self.inputs_[i,j]) for j in range(rsize)] for i in range(blocs)]

    def startp(self, party):
        assert self.start_shares is not None
        return [s.share(party) for s in self.start_shares]


    def inpp(self,party):
        blocs = len(self.inputs_)
        return [[share(self.inputs_[i,j]) for j in range(rsize)] for i in range(blocs)]


@app.class_definition
class Test_data():
    def test_init(self):
        secret = randbits(csize*wsize) ; inputs = token_bytes(rounds * rsize * wsize)
        data = Data(inputs)
        data.rng = secret
        party = np.random.randint(3)


@app.class_definition
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
class Test_Sbox():

    def test_evals(self):
        R = RNG() 
        S = SBox((rsize,csize), R.master)
        party = np.random.randint(3)
        for party in range(3):
            xs   = [wrand() for _ in range(rsize)]
            inps = [shares(x, R) for x in xs]
            outs, msgs = S.evals(inps, R)

            msg = [m[party] for m in msgs] 
            out = [o.share(party) for o in outs]
            inp = [i.share(party) for i in inps]

            assert out == S.evalp(inp, msg)


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
class Test_Permutation():
    def test_evals(self):
        R = RNG()
        P = Permutation(R.master)
        xs   = [wrand() for _ in range(iosize)]
        inps = [shares(x, R) for x in xs]
        outs, msgs = P.evals(inps, R)

        for party in range(3):
            msg = [m[party] for m in msgs]
            out = [o.share(party) for o in outs]
            inp = [i.share(party) for i in inps]
            out_= P.evalp(inp, msg)

            assert out == out_


@app.class_definition
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


    def evalp(self, start, inps, msgs):
        msgs_ = chunks(msgs, 1+len(inps))
        state = self.Perm.eval(start, msgs_[0])
        for (inp, msg) in zip(inps, msgs_[1:]):
            for k in range(rsize):
                state[k] = state[k].view(share) + inp[k].view(share)
            state = self.Perm.eval(state, msg)
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
class Test_Circuit():
    def test_evals_evalp(self):
        R = RNG()
        P = Circuit(randbits(8*ksize))
        xs   = [wrand() for _ in range(iosize)]
        inps = [shares(x, R) for x in xs]
        outs, msgs = P.evals(inps,inps, R)

        for party in range(3):
            msg = [m[party] for m in msgs]
            out = [o.share(party) for o in outs]
            inp = [i.share(party) for i in inps]
            out_= P.evalp(inp,inp, msg)

            assert out == out_


@app.cell
def _():
    return


@app.cell
def _(ctr):
    def mpc_in_the_head():

        class Prover(object):
            def __init__(self, circuit):
                self.circuit = circuit
            def Committ(self):
                pass 
            def Prove(self,c):
                pass
        class Verifier(object):
            def __init__(self, inputs):
                pass
            def Challenge(self):
                pass
            def Verify(self):
                pass


        class __main__(object):
            def __init__(self, key : bytes):
                self.circuit  = Circuit(int.from_bytes(key))
                self.ctr   = 0

            def run(self, secret, inputs):
                self.ctr += 1
                self.circuit.data = Data(secret, inputs, ctr)
                outputs = self.circuit.eval()
                prover = Prover(self.circuit)



        return __main__

    return (mpc_in_the_head,)


@app.cell
def _():
    return


@app.cell
def _(mpc_in_the_head):
    class Test_mpc_in_the_head():
        def test_init(self):
            key = token_bytes(ksize)
            secret = randbits(2*ksize)
            blocs  = 4
            inputs = token_bytes(blocs*rsize*wsize)
            mpc = mpc_in_the_head()(key)
            mpc.run(secret, inputs)

    return


if __name__ == "__main__":
    app.run()
