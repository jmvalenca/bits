# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "duckdb==1.5.3",
#     "marimo>=0.23.3",
#     "numpy==2.4.4",
#     "pytest==9.0.3",
#     "sqlglot==30.8.0",
# ]
# ///

import marimo

__generated_with = "0.23.6"
app = marimo.App(width="medium", auto_download=["html"])

with app.setup:
    import marimo as mo
    from bits import bits
    import numpy as np
    from hashlib import shake_256
    from collections.abc import Callable
    from secrets import randbits, token_bytes
    from itertools import combinations
    from dataclasses import dataclass
    from config import config_MPC
    import pytest

    params = config_MPC().__dict__
    globals().update(params)
    ksize = params['ksize']
    wsize = params['wsize']
    csize = params['csize']
    rsize = params['rsize']
    iosize= params['iosize']
    rounds= params['rounds']
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


@app.class_definition
class RNG(object):
    def __init__(self, key : int = None):
        if key is None: key = randbits(ksize)
        self._key = key
        self._master = np.random.default_rng(key)
        self.seeds   = [self._master.bytes(ksize)  for _ in range(3)]


    @property
    def master(self):
        return self._master

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value):
        self._key = value

    def F(self, party : int):
        def _S(party, gate : int = 0):
            g_id = str(gate).encode()
            return bits(shake_256(self.seeds[party] + g_id).digest(wsize))
        return lambda gate : _S(party, gate) + _S((party + 2)%3, gate)

    def FF(self, party : int):
        return lambda gate : bits([self.F(party)(gate) , self.F((party + 2)%3)(gate)])


@app.class_definition
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
#        return share(encap[1] , encap=bits([r,r])).flip()

    def __mul__(self,other):
        return self.multiply(other)


@app.class_definition(hide_code=True)
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


@app.class_definition
class shares(bits):
    def __new__(cls, x : bits , F = None, gate : int = 0):
        if F is None:
            return np.array([share(x) for _ in range(3)]).view(cls)
        encaps = bits([[F(i)(gate) , F((i+2)%3)(gate)] for i in range(3)])
        return np.array([share(x, encap=encap) for encap in encaps]).view(cls)

    def __array_Finalize__(self, obj):
        if obj is None: return

    def __init__(self, x : bits , F = None, gate : int = 0):
        self._F = F

    @property
    def lift(self):
        return self.view(bits)

    @property
    def F(self):
        return self._F

    @F.setter
    def F(self, value):
        self._F = value

    def roll(self):
        return np.roll(self,(0,2,0),axis=(0,0,0)).view(shares)

    @property
    def wire(self):
        w = self.lift
        try:
            assert sum(w[:,0]) == wzero
            return sum(w[:,1])
        except AssertionError:
            return None

    def share(self,party):
        return self[party].view(share)

    def add(self, other):
        res =  (self.lift + other.lift).view(shares)
        res.F = None
        return res

    def __add__(self, another):
        return self.add(another)


    def multiply(self, other, gate : int = 0):
        assert other.F is not None and (self.F is None or self.F == other.F)
        F = other.F
        this = self.lift ; other_ = other.lift

        rho  = [F(i)(gate) for i in range(3)]
        rs   = bits([rho[i] + this[i,0] * other_[i,0] + this[i,1] * other_[i,1] for i in range(3)])
        ms   = bits([rs[(i+2)%3] for i in range(3)])
        res  = bits([[r + m, r] for (r,m) in zip(rs,ms)]).view(shares)

        res.F = F
        return res,  ms

    def __mul__(self,other):
        return self.multiply(other)


@app.class_definition
class Test_shares():

    def test_wire_add(self):
        F = RNG().F
        x_ , y_ , z_ = wrand(), wrand(), wrand()
        x   = shares(x_,F) ; y = shares(y_,F) ; z = shares(z_,F)
        assert x.wire == x_ and (x + y).wire == x.wire + y.wire
        assert (x + y) + z == x + (y + z)



    def test_mult0(self):
        F = RNG().F
        x_  = wrand(); y_ = wrand()
        x   = shares(x_,F) ; y = shares(y_,F) 
        assert x.wire == x_ and y.wire == y_
        w,w_   = x * y
        assert w.wire == x_ * y_ 


    def test_mult1(self):
        F = RNG().F
        x_ , y_ , z_ = wrand(), wrand(), wrand()
        x   = shares(x_,F) ; y = shares(y_,F) ; z = shares(z_,F)
        w,_ = (x + y) * z ; u,_ = x * z ; v,_ = y * z ; t = u + v
        assert w.wire  == t.wire

    def test_mult2(self):
        F = RNG().F
        x_ , y_ , z_ = wrand(), wrand(), wrand()
        x   = shares(x_,F) ; y = shares(y_,F) ; z = shares(z_,F)
        w,_ = x * y ; u,_ = w * z ; v,_ = y * z ; t,t_ = x * v
        assert u.wire == t.wire

    def test_share(self):
        F = RNG().F
        x_ = wrand() ; x = shares(x_,F)
        x0 = x.share(0); x1 = x.share(1); x2 = x.share(2) ; x3 = share(x0,x1)
        assert x2 == x3
        assert x0.wire(x1) == x_


@app.class_definition
class SBox(object):
    def __init__(self, shape, master, sbox : int = 0):
        assert isinstance(master, np.random.Generator)
        (n, m) = shape
        assert n*(n-1) >= 2*m, f"to few inputs or to many outputs"
        all_pairs = list(combinations(range(n),2))
        self._pairs = master.permutation(all_pairs)[:m]
        self._master= master
        self._shape = shape 
        self._sbox  = sbox

    @property
    def pairs(self):
        return self._pairs

    @property
    def master(self):
        return self._master

    @property
    def shape(self):
        return self._shape

    @property
    def sbox(self):
        return self._sbox

    def eval(self, inps, f , msg):     
        # inps é umarray de elementos do tipo share
        assert all([isinstance(i,share) for i in inps]), f"every input must be an instance of \"share\""
        gate = self.sbox ; ys = []
        for (i,j) in self.pairs:
            encap = bits([f(gate), msg[gate]])
            y     = inps[i].multiply(inps[j], encap)
            ys.append(y)
            gate += 1
        return ys


    def evals(self, inps):
        assert all([isinstance(i,shares) for i in inps]), f"every input must be an instance of \"shares\""
        gate = self.sbox; ys = []; msgs = []
        for (i,j) in self.pairs:
            y, m = inps[i].multiply(inps[j], gate)
            ys.append(y); msgs.append(m)
            gate +=1
        return ys, msgs


@app.class_definition
class Test_Sbox():

    def test_evals(self):
        R = RNG() ; n = 6 ; m = 8
        S = SBox((n,m), R.master)
        F  = R.F 
        party = np.random.randint(3)

        xs   = [wrand() for _ in range(n)]
        inps = [shares(x, F) for x in xs]
        outs, msgs = S.evals(inps)

        msg = [m[party] for m in msgs] 
        out = [o.share(party) for o in outs]
        inp = [i.share(party) for i in inps]

        assert out == S.eval(inp, F(party), msg)


@app.class_definition
class Permutation(object):
    def __init__(self, master, id: int = 0):
        self.id  = id
        self.top = SBox((rsize, csize), master, sbox = 2*id )
        self.bot = SBox((csize, rsize), master, sbox = 2*id +1)

    def eval(self, inps, f , msgs):
        rate = inps[:rsize] ; capacity = inps[rsize:] 
        for msg in np.split(msgs, rounds):
            msgs_top = msg[:csize] ; msgs_bot = msg[csize:]
            capacity_ = self.top.eval(rate, f, msgs_top)
            capacity = [capacity[i] + capacity_[i] for i in range(csize)]
            rate_ = self.bot.eval(capacity, f , msgs_bot)
            rate  = [rate[i] + rate_[i] for i in range(rsize)]
        return rate + capacity

    def evals(self, inps):
        rate = inps[:rsize] ; capacity = inps[rsize:] 
        msgs = []
        for _ in range(rounds):
            capacity_ , m = self.top.evals(rate) ; msgs += m
            capacity = [capacity[i] + capacity_[i] for i in range(csize)]
            rate_, m = self.bot.evals(capacity); msgs += m
            rate = [rate[i] + rate_[i] for i in range(rsize)]
        return rate + capacity , msgs


@app.class_definition
class Test_Permutation():
    def test_evals(self):
        R = RNG(); F = R.F ; master = R.master
        P = Permutation(master)
        xs   = [wrand() for _ in range(iosize)]
        inps = [shares(x, F) for x in xs]
        outs, msgs = P.evals(inps)


@app.cell
def _(pad, split):
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

    return


@app.class_definition
class Test_Circuit():
    pass


@app.cell
def _(msgs, obj):
    def mpc():

        class _Party(obj):
            def __init__(self, input_share , f : Callable[[bytes], bytes], cnt : int=0):
                self.gate_idx = cnt ; self.f = f

            def eval(self, box, xs, msg):
                if isinstance(box,SBox):
                    pairs = box.pairs; m = len(pairs); n = len(xs)
                    xss = [x.view(share) for x in xs]; ys = [] ; rs = []
                    for k in range(m):
                        (i,j) = pairs[k] 
                        rho = self.f(str(self.gate_idx + k).encode())
                        self.gate_idx += 1
                        y,r = xss[i].multiply(xss[j], rho, msgs[k])
                    ys.append(y); rs.append(r)
                    return bits(ys), bits(rs)



        class __main__(object):
            def __init__(self, input_wires, key):
                R = RNG(key)
                # buid shares of the inputs
                Party = [_Party(id, R.F(id)) for id in range(3)]
                # builf circuit
    return


@app.class_definition
class Test_MPC():
    pass


if __name__ == "__main__":
    app.run()
