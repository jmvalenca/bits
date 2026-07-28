# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.23.3",
#     "numpy==2.4.6",
#     "pytest==9.0.3",
# ]
# ///

import marimo

__generated_with = "0.23.15"
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
class Test_RNG():

    def test_types(self):
        R = RNG()
        assert isinstance(R.master, np.random.Generator)

#    @pytest.mark.skip(reason="needs debugging")
    def test_rho(self):
        R = RNG() 
        x = R.rho ; y = R.rho
        assert np.any(x != y)

    def test_scr(self):
        R = RNG()
        ss = R.scr
        assert sum(ss) == wzero

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

    def wire(self, other):
        ws = self + other + share(self,other)
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
        es = RNG().encaps 
        x = wrand()
        a,b,c   = (share(x, encap=e) for e in es)
        try:
            s  = share(b, a)
        except AssertionError:
            s  = share(a, b)
        assert c == s
        assert a.wire(b) == x


@app.class_definition
class shares(bits):
    def __new__(cls, x : bits , rng : RNG = None):
        if rng is None:
            return np.array([share(x) for _ in range(parties)]).view(cls)
        assert isinstance(rng, RNG)
        return np.array([share(x, encap=e) for e in rng.encaps]).view(cls)


    def __array_finalize__(self, obj):
        if obj is None: return


    @property
    def lift(self):
        return self.view(bits)

    """
    @property
    def tau(self):
        w = self.lift
        return sum(w[:,0])

    def roll(self):
        return np.roll(self,(0,2,0),axis=(0,0,0)).view(shares)
    """
    @property
    def wire(self):
        w = self.lift
#        return sum(w[:,0]) + sum(w[:,1]) 
        return sum(w[:,1]) 

    def share(self,party):
        return self[party].view(share)

    def add(self, other):
        res =  (self.lift + other.lift).view(shares)
        return res

    def __add__(self, other):
        return self.add(other)


    def multiply(self, other, rng : RNG):
        rho = rng.scr 
        # rho = rng.rho ; Tau = sum(rho) + (self.wire)*(other.tau) + (other.wire)*(self.tau)
        this = self.lift ; other_ = other.lift        
        rs   = [rho[i] + this[i,0] * other_[i,0] + this[i,1] * other_[i,1] for i in range(parties)]
        #ms   = [rs[(i+parties-1)%parties] + Tau  for i in range(parties)]
        ms   = [rs[(i+parties-1)%parties] for i in range(parties)]
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
#        assert (x + y).tau == x.tau + y.tau

#    @pytest.mark.skip(reason="needs debugging")
    def test_mult0(self):
        R = RNG() 
        x_  = wrand(); y_ = wrand() ; w_ = x_ * y_
        x   = shares(x_, rng=R) ; y = shares(y_, rng=R) ; w = shares(w_, rng=R)
        p, _   = x.multiply(y, rng=R)
        assert p.wire == w.wire


@app.class_definition
class Data(object):   # implementation of View for prover and parties


    def __init__(self, inputs : bytes, iv : int = 1):     

        self.rate_   = bits((2**(rsize*wsize) - iv).to_bytes(rsize*wsize)).reshape(rsize,wsize)
        blocs        = math.ceil(len(inputs) /(rsize * wsize))
        self.inputs_ = bits(pad(inputs, blocs*rsize*wsize)).reshape(blocs,rsize,wsize)
        self.R       = RNG()
        self.capacity_ = None
        self.start_shares = None

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
    def has_secret(self):
        return self.capacity_ is None
    @has_secret.setter
    def has_secret(self, secret : int):
        if secret <= 0:
            secret = randbits(8*csize*wsize)
        self.capacity_  = bits(secret.to_bytes(csize*wsize)).reshape(csize,wsize)


    @property
    def start(self):
        assert self.capacity_ is not None and self.rate_ is not None
        return np.concatenate([self.rate_, self.capacity_]).view(bits)

    @property
    def inp(self):
        return self.inputs_

    @property
    def starts(self):
        if self.start_shares is None:
            rng = self.rng
            rate       = [shares(r) for r in self.rate_]
            capacity   = [shares(s, rng=rng) for s in self.capacity_]
            self.start_shares =  rate + capacity
        return self.start_shares

    @property
    def inps(self):
        blocs = len(self.inputs_)
        return [[shares(self.inputs_[i,j]) for j in range(rsize)] for i in range(blocs)]

    def startp(self, party):
        assert self.start_shares is not None
        return [s.share(party) for s in self.start_shares]

    @property
    def inpp(self):
        blocs = len(self.inputs_)
        return [[share(self.inputs_[i,j]) for j in range(rsize)] for i in range(blocs)]


@app.class_definition
class Test_data():
    def test_init(self):
        inputs = token_bytes(rounds * rsize * wsize)
        data = Data(inputs)
        data.rng = randbits(csize*wsize)


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
class Test_Sbox():

    def test_evals(self):
        R = RNG() 
        S = SBox((rsize,csize), R.master)
        party = np.random.randint(parties)
        for party in range(parties):
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

        for party in range(parties):
            msg = [m[party] for m in msgs]
            out = [o.share(party) for o in outs]
            inp = [i.share(party) for i in inps]
            out_= P.evalp(inp, msg)

            assert out == out_


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


@app.cell
def _():
    class Test_Circuit():
        def test_evals_evalp(self):
            # public information
            key = randbits(8*ksize)
            inputs = token_bytes(rounds * rsize * wsize)
            data = Data(inputs, iv=0)
            pub_key = (key, data.inpp)
            # private key
            secret = randbits(csize*wsize)
            data.has_secret = secret
            R = data.rng

            #calculo do commit
            C = Circuit(key)
            commit  = C.eval(data.start, data.inp)

            #confirmação
            outs, msgs = C.evals(data.starts,data.inps, R)
            assert np.all([commit[i] == outs[i].wire for i in range(csize)])


            #verificação
            for party in range(parties):
                msg   = [m[party] for m in msgs]
                out   = [o.share(party) for o in outs]
                out_  = C.evalp(data.startp(party),data.inpp, msg)
                assert out == out_

            #two-party 
            # challendge
            (c0,c1) = choice([(0,1), (1,2),(2,0)])
            #reply     msg0,startp(c0),msg(1),starp(c1), taus
            msg0      = [m[c0] for m in msgs]
            msg1      = [m[c1] for m in msgs]
            # verificação
            out0      = C.evalp(data.startp(c0),data.inpp, msg0)
            out1      = C.evalp(data.startp(c1),data.inpp, msg1)
            assert np.all([commit[i] == out0[i].wire(out1[i]) for i in range(csize)])
    #
    return


@app.function
def mpc():
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


@app.class_definition
class Test_mpc_in_the_head():
    pass


if __name__ == "__main__":
    app.run()
