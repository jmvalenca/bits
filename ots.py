import marimo

__generated_with = "0.21.1"
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

    # tests
    import unittest
    # test data
    ntags = 16
    tags = bits([bits(urandom(params['N'])) for _ in range(ntags)])


@app.function
def one_of_two_bytes_OT():
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


@app.function
def N_1_of_N_noreduct_OT():
    n      = params['n']
    niters = params['n_iters']
    n_ecc  = params['n_ecc']
    k_ecc  = params['k_ecc']
    l      = params['l']



    class Provider(object):
        def __init__(self):
            self.sampler = bits_sampler()
            self.crs     = bits_crs()

        def choose(self, *mm) -> bytes:
            self.mm_   = [bits([m]) for m in mm]
            return self.crs.key

        def transfer(self, sid=0, iter=0, *pks):
            msk = self.sampler.eta()
            SID = str(sid).encode() + str(iter).encode()
            a , u    = self.crs.AU(tweak=SID)
            assert bits(sum(pks)) == u , f"public keys  unmatch u={u}"     
            a_ = msk @ a  ; pp_ = [msk @ p for p in pks]
            return (a_, [p_ + m_ for (p_,m_) in zip(pp_, self.mm_)])


    class Receiver(object):
        def __init__(self):
            self.sampler = bits_sampler()
            self.ss    = [self.sampler.secrets(n)  for _ in range(ntags-1)]  # LPN OT  key

        def choose(self, key, b, sid=0, iter=0):
            self.b = b
            self.crs = bits_crs(key)
            SID = str(sid).encode() + str(iter).encode()
            a, u = self.crs.AU(tweak=SID)
            ee    = [self.sampler.noise() for _ in range(ntags-1)]
            goodks  = [(a @ s) + e  for (s,e) in zip(self.ss, ee)]
            badks   = [bits(sum(goodks)) + u]
            pks     = goodks[:b-1] + badks  + goodks[b-1:]
            ## debug
            assert  u == sum(pks), f"bad u+parity ={u + sum(pks)}"
            return pks

        def transfer(self,crypt):
            (A, C) = crypt ; b = self.b
            aa = [A @ s  for s in self.ss] 
            cc = C[:b] + C[b+1:]
            return [a + c for (a,c) in zip(aa,cc)]

    class __main__(object):
        def __init__(self, *tags):
            self.n_tags    = len(tags)
            assert self.n_tags >= 2, "n_tags {self.n_tags} must be at least 2"
            self.tag_size  = len(tags[0])
            # galois 
            self.rs = galois.ReedSolomon(n_ecc,k_ecc)
            self.provider = Provider()
            self.receiver = Receiver()
            messages = []
            for tag in tags:
                assert len(tag) == self.tag_size, f"tags must be all of the same size"
                messages.append(bits(self.rs.encode(tag)))
            self.messages = bits(messages)


        def all_but(self, b : np.uint8):
            data_ = []
            for sid in range(len(self.messages[0])):    # for each position in the messages
                iters = [] ; mm = [self.messages[i][sid]  for i in range(ntags)] 
                for iter in range(niters):    # for a given pair of bytes run the basic protocol niters times
                    key   = self.provider.choose(*mm)
                    pks   = self.receiver.choose(key, b, sid, iter)
                    crypt = self.provider.transfer(sid, iter, *pks )
                    res   = self.receiver.transfer(crypt)
                    iters.append(res)  
                iters_ = bits(iters).byte_round(d=ntags-1)
                # from the various iterations select the most frequent bytes and append it to the built message
                data_.append(iters_)  
            data = list(bits(data_).T)
            # decode de received message and detect the number of errors corrected
            tags_and_errors  = [self.rs.decode(tag_, errors=True) for tag_ in data]
            assert all([errors >= 0 for (_,errors) in tags_and_errors]), f"unable to correct all errors"
            return [bits(tag) for (tag, _) in tags_and_errors]


    return __main__


@app.class_definition
class Test_OTS(unittest.TestCase):
#    @unittest.skip("em experiencias")
    def test_one_of_two_OT(self):
        cls = one_of_two_bytes_OT()
        ot  = cls(*tags)
        b = choice([0,1])
        self.assertEqual(tags[b], ot.get(b))

    @unittest.skip("em experiencias")
    def test_one_of_N_OT(self):
        cls = one_of_N_OT()
        ot  = cls(*tags)
        b   = choice(range(len(tags)))
        self.assertEqual(tags[b], ot.get(b))

    @unittest.skip("em experiencias")    
    def test_all_but_one_OT(self):
        cls = N_1_of_N_OT()
        ot  = cls(*tags)
        b   = choice(range(len(tags)))
        xcepts = ot.all_but(b)
        self.assertTrue(np.all(np.isin(xcepts,tags)))
        self.assertFalse(np.all(np.isin(tags[b],xcepts)))

    @unittest.skip("em experiencias")
    def test_all_but_one_noreduct_OT(self):
        cls = N_1_of_N_noreduct_OT()
        ot  = cls(*tags)
        b   = choice(range(len(tags)))
        xcepts = ot.all_but(b)
        self.assertTrue(np.all(np.isin(xcepts,tags)))
        self.assertFalse(np.all(np.isin(tags[b],xcepts)))


if __name__ == "__main__":
    app.run()
