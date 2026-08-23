# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "galois==0.4.11",
#     "marimo>=0.24.0",
#     "numpy==2.5.2",
#     "pytest==9.1.1",
# ]
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    from bits import bits, bits_crs, bits_sampler
    import numpy as np
    import galois
    from math import ceil, log2
    from hashlib import shake_256

    from config import config, config_NP
    from os import urandom
    from random import choice


    params    = config().__dict__
    params_NP = config_NP().__dict__



@app.function
def LPN_1_2_OT():
    n      = params['n']
    niters = params['n_iters']
    ncc    = params['n_ecc']
    kcc    = params['k_ecc']

    class Provider(object):
        def __init__(self):
            self.sampler = bits_sampler()
            self.crs     = bits_crs()


        def choose(self, m0 : np.uint8  , m1 : np.uint8) -> bytes:
            self.m0   = bits([m0])
            self.m1   = bits([m1])
            return self.crs.key

        def transfer(self, P, sid=0, iter=0):
            msk = self.sampler.eta()
            SID = str(sid).encode() + str(iter).encode()
            a , u    = self.crs.AU(tweak=SID)
            (p0, p1) = P 
            assert p0 + p1 == u , f"public keys p0,p1 = ({p0},{p1}) unmatch u={u}"  
            a_ = msk @ a  ; p0_ = msk @ p0 ; p1_ = msk @ p1
            return (a_, p0_ + self.m0 , p1_ + self.m1)


    class Receiver(object):
        def __init__(self):
            self.sampler = bits_sampler()
            self.s       = self.sampler.secrets(n)     # LPN OT  key

        def choose(self, key, b, sid=0, iter=0):
            self.crs = bits_crs(key)
            self.b    = b
            SID = str(sid).encode() + str(iter).encode()
            a, u = self.crs.AU(tweak=SID)
            e    = self.sampler.noise()
            t    =  a @ self.s + e
            if self.b == 0:
                return  (t , t + u)
            return (t + u , t)

        def transfer(self,C):
            (a, c0, c1) = C 
            return (a @ self.s) + (c0 if self.b == 0 else c1)

    class __main__(object):
        def __init__(self, *mess : bits):
            assert len(mess) > 1
            # galois 
            self.rs = galois.ReedSolomon(ncc,kcc)
            #
            self.provider = Provider()
            self.receiver = Receiver()
            assert len(mess[0]) == len(mess[1]), f"messages must have equal length"
            self.mess0 = bits(self.rs.encode(mess[0]))
            self.mess1 = bits(self.rs.encode(mess[1]))

        def get(self, b):
            data_ = []
            for sid in range(len(self.mess0)):    # for each position in the messages
                iters = [] ; m0 = self.mess0[sid] ; m1 = self.mess1[sid]  
                for iter in range(niters):    # for a given pair of bytes run the basic protocol niters times
                    key  = self.provider.choose(m0,m1)
                    P    = self.receiver.choose(key, b, sid, iter)
                    C    = self.provider.transfer(P , sid, iter)
                    res  = self.receiver.transfer(C)
                    iters.append(res)     # collect the byte output of each iteration
                # from the various iterations select the most frequent byte and append it to the built message
                data_.append(bits(iters).byte_round()[0])  
            # decode de received message and detect the number of errors corrected
            data, errors  = self.rs.decode(data_, errors=True)
            assert errors >= 0, f"unable to correct all errors"
            return bits(data)


    return __main__


@app.function
def Naor_Pinkas_1_of_N_OT():             # Naor & Pinkas
    ksize = params_NP['ksize']
    msize = params_NP['msize']
    N     = params_NP['N']
    l     = ceil(log2(N))

    n_key = lambda : bits(urandom(ksize))

    def ibits(I : int):
        ii = [int(i) for i in bin(I)[2:]] ; pad = [0]*(l - len(ii)) 
        return ii + pad

    def F(k : bits, I : int):
        return bits(shake_256(k.tobytes + (I).to_bytes()).digest(msize))

    class Provider(object):
        def __init__(self, Xs):
            self.ks = [(n_key(), n_key()) for j in range(l)]
            self.Ys = []
            for I in range(N):
                M = sum([F(k[i], I) for (i,k) in zip(ibits(I), self.ks)])
                self.Ys.append(Xs[I] + M) 


        def engage(self):
            cls = LPN_1_2_OT()
            return [cls(*k) for k in self.ks] 

        def transfer(self):
            return self.Ys

    class Receiver(object):
        def __init__(self, I):
            self.I = I
            self.ii = ibits(I)


        def engage(self, ots):
            self.M = sum([F(ot.get(i), self.I) for (i,ot) in zip(self.ii, ots)])   

        def reveal(self, Ys):
            return Ys[self.I] + self.M

    class __main__(object):
        def __init__(self, msgs):
            self.Provider = Provider(msgs)

        def get(self,I):
            self.Receiver = Receiver(I)
            ots = self.Provider.engage()
            self.Receiver.engage(ots)
            Ys = self.Provider.transfer()
            X  = self.Receiver.reveal(Ys)
            return X

    return __main__


if __name__ == "__main__":
    app.run()
