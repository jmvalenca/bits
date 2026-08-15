# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.23.3",
#     "numpy==2.5.2",
#     "pytest==9.1.1",
# ]
# ///

import marimo

__generated_with = "0.23.16"
app = marimo.App()

with app.setup:
    import marimo as mo
    from config import config_MPC
    import numpy as np
    import mpc 
    from secrets import randbits, token_bytes, choice
    globals().update(config_MPC().__dict__)
    globals().update(mpc.__dict__)


@app.cell
def _(RNG, wzero):
    class Test_R():

        def test_types(self):
            R = RNG()
            assert isinstance(R.master, np.random.Generator)

    #    @pytest.mark.skip(reason="needs debugging")
        def test_rho(self):
            R = mpc.RNG() 
            x = R.rho ; y = R.rho
            assert np.any(x != y)

        def test_scr(self):
            R  = mpc.RNG()
            ss = R.scr
            assert sum(ss) == wzero

        def  test_encaps(self):
            es = mpc.RNG().encaps
            assert sum(es[:,0]) == sum(es[:,1])

    return


@app.cell
def _(share, wrand):
    class Test_share():

        def test_1wire(self):
            R = mpc.RNG()
            es = R.encaps 
            x = wrand()
            a,b,c   = (share(x, encap=e) for e in es)
            try:
                s  = share(b, a)
            except AssertionError:
                s  = share(a, b)
            assert c == s
            assert c.wire(a) == x

    return


@app.cell
def _(RNG, shares, wrand):
    class Test_shares():
    #    @pytest.mark.skip(reason="needs debugging")
        def test_wire_add(self):
            R = RNG()
            x_ , y_ , z_ = wrand(), wrand(), wrand()
            x   = shares(x_, rng=R, tau=wrand()) ; y = shares(y_, rng=R, tau=wrand())
            z   = shares(z_,rng=R, tau=wrand())
            assert (x + y).wire == x.wire + y.wire
            assert (x + y) + z == x + (y + z)
            assert (x + y).tau == x.tau + y.tau

    #    @pytest.mark.skip(reason="needs debugging")
        def test_mult0(self):
            R = RNG() 
            x , tx , y , ty = [wrand(), wrand(), wrand(), wrand()]
            w = x * y
            xs   = shares(x, rng=R, tau=tx) ; ys = shares(y, rng=R, tau=ty) 
            p, _   = xs.multiply(ys, rng=R)
            assert p.wire == w

    return


@app.cell
def _(RNG, SBox, csize, parties, rsize, shares, wrand):
    class Test_Sbox():

        def test_evals(self):
            R = RNG() 
            S = SBox((rsize,csize), R.master)

            xs   = [wrand() for _ in range(rsize)]
            ys   = S.eval(xs)
            inps = [shares(x, R) for x in xs]
            outs, msgs = S.evals(inps, R)

            for j in range(csize):
                assert outs[j].wire == ys[j]

            for party in range(parties):
                msg = [m[party] for m in msgs] 
                out = [o.share(party) for o in outs]
                inp = [i.share(party) for i in inps]

                assert out == S.evalp(inp, msg)

    return


@app.cell
def _(Permutation, RNG, bits, iosize, parties, shares, wrand):
    class Test_Permutation():
        def test_evals(self):
            R = RNG()
            P = Permutation(R.master)
            xs   = [wrand() for _ in range(iosize)]
            ys   = P.eval(bits(xs))
            inps = [shares(x, R, tau=wrand()) for x in xs]
            outs, msgs = P.evals(inps, R)

            for j in range(iosize):
                assert outs[j].wire == ys[j]

            for party in range(parties):
                msg = [m[party] for m in msgs]
                out = [o.share(party) for o in outs]
                inp = [i.share(party) for i in inps]
                out_= P.evalp(inp, msg)
                assert out == out_

    return


@app.cell
def _(Data, csize, rsize):
    class Test_data():
        def test_start(self):
            data   = Data(b'1111')
            s = data.start; ss = data.starts
            iosize = rsize + csize
            for i in range(iosize):
                assert ss[i].wire == s[i]

    return


@app.cell
def _(Circuit, Data, Inputs, csize, ksize, parties):
    class Test_Circuit():
        def test_evals_evalp(self):
            # public information
            circuit = randbits(8*ksize)
            key     = token_bytes(ksize)
            source  = token_bytes(ksize)
    
            # pub+private 
            secret  = randbits(8*ksize)
            data = Data(key, secret=secret)
            inp  = Inputs(source)

            #calculo do commit
            C = Circuit(circuit)
            commit  = C.eval(data.start, inp.input)
            # Par de chaves
            public_key = {'data': key, 'circuit': circuit, 'commit' : commit}
            private_key = secret

            #confirmação
            outs, msgs = C.evals(data.starts, inp.inputs, data.rng)
            assert np.all([commit[i] == outs[i].wire for i in range(csize)])
            taus = [c.tau for c in outs]

            #verificação
            for party in range(parties):
                msg   = [m[party] for m in msgs]
                out   = [o.share(party) for o in outs]
                out_  = C.evalp(data.startp(party), inp.inputp, msg)
                assert out == out_

            #two-party 
            # challendge
            (c0,c1) = choice([(0,1), (1,2),(2,0)])
            #reply     msg0,startp(c0),msg(1),starp(c1), taus
            msg0      = [m[c0] for m in msgs]
            msg1      = [m[c1] for m in msgs]
            # verificação
            out0      = C.evalp(data.startp(c0), inp.inputp, msg0)
            out1      = C.evalp(data.startp(c1), inp.inputp, msg1)
            assert np.all([commit[i] == out0[i].wire(out1[i], tau=taus[i]) for i in range(csize)])
    #
    return


@app.cell
def Test_mpcITH(mpcITH):
    class Test_mpcITH():
        def test_mpc_run(self):
            key = token_bytes(16); source = token_bytes(16)
            simulation = mpcITH()(key,source)
            simulation.run()

    return


if __name__ == "__main__":
    app.run()
