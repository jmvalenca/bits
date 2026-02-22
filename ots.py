import marimo

__generated_with = "0.20.1"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    from bits import bits, bits_crs, bits_sampler
    import numpy as np
    import galois
    from config_nb import config
    from os import urandom
    from random import choice


    params = config().__dict__
    globals().update(params)


@app.function
def one_of_two_bytes_OT():
    n = params['n']
    niters = params['niters']
    
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
            a_ = msk @ a ; p0_ = msk @ p0 ; p1_ = msk @ p1
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
            t    =  (a @ self.s) + e
            if self.b == 0:
                return  (t , t + u)
            return (t + u , t)

        def transfer(self,C):
            (a, c0, c1) = C 
            return (a @ self.s) + (c0 if self.b == 0 else c1)

    class __main__(object):
        def __init__(self, mess0 : bits , mess1 : bits):
            # galois 
            ng  = 255 ; ecc = 127
            self.rs = galois.ReedSolomon(ng,ng-ecc+1)
            #
            self.provider = Provider()
            self.receiver = Receiver()
            assert len(mess0) == len(mess1), f"messages must have equal length"
            self.mess0 = bits(self.rs.encode(mess0))
            self.mess1 = bits(self.rs.encode(mess1))

        def get(self, b):
            data = []
            for sid in range(len(self.mess0)):
                iters = [] ; m0 = self.mess0[sid] ; m1 = self.mess1[sid]
                for iter in range(niters):    
                    key  = self.provider.choose(m0,m1)
                    P    = self.receiver.choose(key, b, sid, iter)
                    C    = self.provider.transfer(P , sid, iter)
                    res  = self.receiver.transfer(C)
                    iters.append(res)  
                data.append(bits(iters).byte_round()[0])
            data_, errors  = self.rs.decode(data, errors=True)
            assert errors >= 0, f"existem erros que não foram corrigidos"
            return bits(data_)


    return __main__


@app.function
def one_of_N_OT():

    class Provider(object):
        def __init__(self, data):
            left, right = data.bissect()
            self.ot = one_of_two_bytes_OT()(left, right)
        def reveal(self):
            return self.ot

    class Receiver(object):
        def __init__(self, b : np.uint8):
            self.b = b

        def accept(self,ot):
            self.data = ot.get(self.b)
        def reveal(self):
            return self.data

    class __main__(object):
        def __init__(self, *tags):
            self.data    =  bits(np.concatenate(tags))
            self.width   =  len(tags)
        def get(self, b : np.uint8):
            assert b < self.width , f"message index {b} out of range 0..{self.width-1}"
            data = self.data
            width = self.width
            while True: 
                if width <= 1:
                    break

                provider = Provider(data)
                ot       = provider.reveal()
                width    = width // 2
                (side, b) = (0,b) if b < width else (1,b-width)
                receiver = Receiver(side)
                receiver.accept(ot)
                data = receiver.reveal()
            return data

    return __main__


@app.function
def N_1_of_N_OT():

    class Provider(object):
        def __init__(self, left, right):
            self.ot = one_of_two_bytes_OT()(left, right)
        def reveal(self):
            return self.ot

    class Receiver(object):
        def __init__(self, b : np.uint8):
            self.b = b

        def accept(self,ot):
            self.data = ot.get(self.b)
        def reveal(self):
            return self.data

    class __main__(object):
        def __init__(self, *tags):
            self.tsize   = len(tags[0])
            self.data    =  bits(np.concatenate(tags))
            self.width   =  len(tags)

        def all_but(self, b : np.uint8):
            assert b < self.width , f"message index {b} out of range 0..{self.width-1}"
            data  = self.data
            restof = []
            width = self.width
            while True: 
                if width <= 1:
                    break
                left, right = data.bissect()
                provider = Provider(left, right)
                ot       = provider.reveal()
                width    = width // 2
                (side, b)  = (0,b)  if b < width else (1, b - width)
                receiver = Receiver(side)
                receiver.accept(ot)
                data = receiver.reveal()
                restof.append(left if side == 1 else right)
            res = bits(np.concatenate(restof))
            return bits(np.split(res, res.size // self.tsize))

    return __main__


if __name__ == "__main__":
    app.run()
