import marimo

__generated_with = "0.19.11"
app = marimo.App()


@app.cell
def _(N, cut, ecc, eps, gamma, m, n, s, ssize, t, tsize):
    #!/opt/anaconda3/bin/python ''
    # coding: utf-8

    # In[34]:

    import numpy as np
    from os import urandom
    from math import ceil, trunc, floor, log2
    from hashlib import shake_256
    import numpy.ma as ma
    from config import params
    from random import choice
    from reedsolo import RSCodec, ReedSolomonError
    from collections.abc import Iterable
    from pickle import dumps, loads
    globals().update(params)




    class bits(np.ndarray):
        def __new__(cls, input_array):
            if isinstance(input_array, bytes) or isinstance(input_array, bytearray):
                obj = np.frombuffer(input_array, dtype=np.uint8).view(cls)
            elif isinstance(input_array, np.ndarray):
                obj = input_array.astype(np.uint8).view(cls)
            elif isinstance(input_array, Iterable):
                obj = np.stack(input_array).astype(np.uint8).view(cls)
            else:
                obj = np.packbits(input_array).view(cls)
            return obj

        def __array_finalize__(self, obj):
            if obj is None: return
            self.n = getattr(obj, 'n', None)
            self.dtype = np.uint8
        
 
        def __str__(self):
            return np.array_str(self)
    
        def __repr__(self):
            return np.array_repr(self)     #[:-1] + ', p=' + str(self.p) + ')'
    

        def unpack(self):
            return np.unpackbits(self)

        def lift(self):
            return self.view(np.ndarray)
    
        def bit_counts(self):
            if np.ndim(self) > 0:
                data = np.vectorize(lambda x: int(x).bit_count() , otypes=[np.uint8])(self.lift())
                if np.ndim(data) < 2:
                    return data
                else:
                    data = data.reshape((data.shape[0], -1))
                    return data
            if np.issubdtype(self.dtype, np.integer):
                return np.add.reduce(data)
            return np.unpackbits(self).sum()
    
        def bit_count(self):
            res = self.bit_counts()
            if np.ndim(res) == 0:
                return res
            else:
                return sum(res)
    

        def byte_round(self):
            data = self.unpack().reshape((-1,8)).T
            l   = len(data[0]) ; err = floor(gamma * l)
            _0 = np.uint(0) ; _1 = np.uint(1)
            byt = []
            for i in range(8):
                x = sum(data[i])
                if l - x < err:
                    byt.append(_1)
                elif x < err:
                    byt.append(_0)
                else:
                    byt.append(choice([_0 , _1]))
            return np.packbits(byt)
        
    
    
        def __eq__(self, other):
    #        return np.array_equal(self, other)
            return np.array_equiv(self, other)
    
        def tobytes(self):
            return self.lift().tobytes().strip(b'\x00')

        def hash(self):
            hash = shake_256(self.tobytes())
            return hash.digest(tsize)

    
        def add(self, other):
            if np.ndim(self) > 0:
                return np.bitwise_xor.__call__(self,other).view(bits)
            return np.bitwise_xor(self,other)
    
        def __add__(self,other):
            return self.add(other)

        def mul(self, other):
            if np.ndim(self) > 0:
                return np.bitwise_and.__call__(self,other).view(bits)
            return np.bitwise_and(self, other)
    
        def __mul__(self,other):
            return self.mul(other)

        def sum(self):
            return np.bitwise_xor.reduce(self)

        def as_unit_tags(self, unit = None):
            if unit is None:
                unit = ones_tag
            return [unit if b == 1 else zero_tag for b in self.unpack()]

        def as_tag(self):
            return bits(np.repeat(self, tsize // self.size))
    
        def join(self,*args):
            return np.concatenate((bits(args),self))
    
        def append(self,other):
            return bits(np.concatenate((self,other)))
    
        def mask(self,other):
        
            assert isinstance(other, Iterable) and len(other) > 0, f"2nd argument must be a non-empty Iterable"
            msk = self.unpack()
            if isinstance(other,np.ndarray) and other.ndim == 1:
                res  = (self * other).bit_count() % 2
                return sign(res)
        
            return sum([msk[j]*other[j] for j in range(len(msk))])

        def maskB(self, other):
            mask = list(self)
            if isinstance(other,np.ndarray) and other.ndim < 2:
                res = (self * other).sum()
                return bits([res])
            if isinstance(other, Iterable) and len(other) > 0:
                return sum([bits([s]) * u  for (s,u) in zip(mask,other)])
            raise ValueError(f"arguments of improper kind")
    
    
        def bissect(self):
            l = self.size // 2
            return (self[:l], self[l:])


    def bits_concatenate(*args):
        return bits(np.concatenate(args))      

    def as_tag(x):
        x_ = np.array(x,dtype=np.uint8)
        return bits(x_).as_tag()

    zero = bits(b'\x00')
    one  = bits(b'\x01')
    ones = bits(b'\xff')
    zerof    =  lambda n : bits(b'\x00' * n)
    onesf    =  lambda n : bits(b'\xff' * n)
    zero_tag = zerof(tsize)
    ones_tag = onesf(tsize)

    def as_bits(x):
        return bits([x])

    def sign(x):
        return zero if x == zero else ones

    def bit_sum(args):
        return np.bitwise_xor.reduce(args)

    def pack(arg):
        return bits(np.packbits(arg))

    class bits_rng_sampler(object):

        def __init__(self, seed=None):
            if seed is None:
                seed = bits(urandom(s))
            if not isinstance(seed, bits):
                seed = bits(seed)
            self.rng = np.random.default_rng(seed)
        


        def bernoulli(self, l=16, eps=eps):
            return bits(np.packbits([1 if self.rng.random() < eps else 0 for _ in range(l * 8)]))
            
        def secrets(self, l=16):
            data = self.rng.integers(256, size=l, dtype=np.uint8)
            return bits(data)

        def phi(self, data, slice : list = None, size : float = cut):
            if slice is None:
                l = len(data) ; d = ceil(size * l)
                slice = self.rng.permutation(l)[:d]
            return slice, bits(data[slice])
    

    class bits_hash_expand(object):
        def __init__(self, key=None):
            if key is None:
                key = urandom(ssize)
            self.key = key 
        

        def AU(self, tweak : bytes, s = s, t = t):
            hash = shake_256(b'AU' + self.key + tweak)
            A = bits(hash.digest(s*t)).reshape((t,s))
            hash.update(b'U')
            U = bits(hash.digest(t))
            return A,U

        def POLS(self, npols : int = m , nitems : int = n):
            hash = shake_256(b'POLS' + self.key)
            pols = []
            for j in range(npols):
                hash.update(str(j).encode())
                pols.append(POL(hash.digest(3*nitems//8),nitems))
            return pols

        def QS(self, tweak : bytes , nitems : int = n):
            hash = shake_256(b'QS' + self.key + tweak)
            qs = []
            for j in range(nitems):
                hash.update(str(j).encode())
                qs.append(bits(hash.digest(tsize)))
            return qs

        def psi(self, nitems : int = m, tweak : bytes = b'\x00'):
            hash = shake_256(b'psi' + self.key + tweak)
            return bits(hash.digest(nitems // 8))
    
        def Z(self, tweak : bytes = b'\x00' , nitems : int = N):
            hash = shake_256(b'Z' + self.key + tweak)
            zs = []
            for j in range(nitems):
                hash.update(str(j).encode())
                zs.append(bits(hash.digest(tsize)))
            return zs


    def one_of_two_bytes_OT():
        class Provider(object):
            def __init__(self, ):
                self.rspl = bits_rng_sampler()
                self.hspl = bits_hash_expand()
            

            def choose(self, m0 : np.uint8  , m1 : np.uint8) -> bytes:
        #        print(f"m's = {(m0,m1)}")
                self.m0   = np.array([m0]*t)
                self.m1   = np.array([m1]*t)
                return self.hspl.key

            def transfer(self, P, sid=0):
            
            #    phi  = self.rspl.bernoulli(t)
                phi = self.rspl.phi
                SID = str(sid).encode()
                a , u    = self.hspl.AU(tweak=SID)
                (p0, p1) = P ; c0 = p0 + self.m0 ; c1 = p1 + self.m1
                assert p0 + p1 == u , f"public keys p0,p1 = ({p0},{p1}) unmatch u={u}"
        #        
                sl, a_ = phi(a) ; _,c0_ = phi(c0,sl); _,c1_ = phi(c1, sl)
            #    a_ = phi.maskB(a) ; c0_ = phi.maskB(c0) ; c1_ = phi.maskB(c1)
            #    print(f"shapes a={a_.shape}, c0={c0_.shape}, c1={c1_.shape} ")
                return (a_, c0_, c1_)

        class Receiver(object):
            def __init__(self):
                self.rspl = bits_rng_sampler()
                self.r    = self.rspl.secrets(s)     # LPN OT  key
            
            def choose(self, key, b, sid=0):
                self.hspl = bits_hash_expand(key)
                self.b    = b
                SID = str(sid).encode()
                a, u = self.hspl.AU(tweak=SID)
                e    = self.rspl.bernoulli(t)
                T    =  a.dot(self.r) + e
                if self.b == 0:
                    return  (T , T + u)
                return (T + u , T)

            def transfer(self,C):
                (a, c0, c1) = C 
                key = a.dot(self.r)
                if self.b == 0:
                    return (c0 + key).byte_round()
                else:
                    return (c1 + key).byte_round()

        class __main__(object):
            def __init__(self, mess0 : bits , mess1 : bits):
                self.rsc = RSCodec(ecc)
                self.provider = Provider()
                self.receiver = Receiver()
                assert len(mess0) == len(mess1), f"messages must have equal length"
                self.mess0 = bits(self.rsc.encode(mess0))
                self.mess1 = bits(self.rsc.encode(mess1))
                #self.mess0 = mess0 
                #self.mess1 = mess1

            def get(self, b):
                data = []
                for sid in range(len(self.mess0)):
                    key  = self.provider.choose(self.mess0[sid], self.mess1[sid])
                    P    = self.receiver.choose(key, b, sid)
                    crpt = self.provider.transfer(P , sid)
                    res  = self.receiver.transfer(crpt)
                    if not (res is None):
                        data.append(res[0])
                #print(data)
                data_ , _ , _ = self.rsc.decode(data)
                return bits(data_)


        return __main__



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
                    if b < width:
                        receiver = Receiver(0)
                    else:
                        receiver = Receiver(1)
                        b = b - width
                    receiver.accept(ot)
                    data = receiver.reveal()
                return data

        return __main__

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
                self.data    =  bits(np.concatenate(tags))
                self.width   =  len(tags)
            
            def get(self, b : np.uint8, tsize=tsize):
                assert b < self.width , f"message index {b} out of range 0..{self.width-1}"
                data  = self.data
                resto = []
                width = self.width
                while True: 
                    if width <= 1:
                        break
                    left, right = data.bissect()
                    provider = Provider(left, right)
                    ot       = provider.reveal()
                    width    = width // 2
                    if b < width:
                        receiver = Receiver(0)
                    else:
                        receiver = Receiver(1)
                        b = b - width
                    receiver.accept(ot)
                    data = receiver.reveal()
                    resto.append(left if data == right else right)
                res = bits(np.concatenate(resto))
                return np.split(res, res.size // tsize)

        return __main__



    class POL(object):
        def __init__(self, bytes, nargs : int = n):
            nn = nargs // 8
            try:
                buffer = np.frombuffer(bytes, count=3*nn, dtype=np.uint8)
                if len(buffer) != 3 * nn:
                    raise ValueError(f"Expected {3 * nn} bytes, got {len(buffer)} bytes")
            except ValueError as err:
                print(err)
                return 
        
            self.b = bits(buffer[ : nn])
            self.u = bits(buffer[nn : 2*nn])
            self.v = bits(buffer[2*nn : ])
            self.c = zero

        def __repr__(self):
            return f"[\n c : {self.c}\n b : {self.b}\n u : {self.u}\n v : {self.v}\n]"


        def eval(self, X, Y=None, Tau=None):
            xb = self.b.mask(X) ; xu = self.u.mask(X); xv = self.v.mask(X)
        
            # argumento X
            if Y is None and Tau is None:
                assert X.ndim == 1 , f"X={X} deve ser um vetor de {n} bits ou {n//8} bytes"
                return self.c +  xb  +  xu * xv
        
            # argumentos  qs, delta -> produz a tag B
            if Tau is None:
                return  self.c * Y +  xb * Y  +  xu * xv

            # argumentos X , Tau -> produz o par de tags  A1, A0
            assert X.ndim == 1 , f"X={X} deve ser um vetor de {n} bits ou {n//8} bytes"
            Tb = self.b.mask(Tau) ; Tu = self.u.mask(Tau) ; Tv = self.v.mask(Tau)
            return (Tb + (xv * Tu) + (xu * Tv) , Tu * Tv)

        def evalB(self, X, Y=None, Tau=None):
            xb = self.b.maskB(X) ; xu = self.u.maskB(X); xv = self.v.maskB(X)
        
            # argumento X
            if Y is None and Tau is None:
                assert X.ndim == 1 , f"X={X} deve ser um vetor de {n} bits ou {n//8} bytes"
                return self.c +  xb  +  xu * xv
        
            # argumentos  qs, delta -> produz a tag B
            if Tau is None:
                return  self.c * Y +  xb * Y  +  xu * xv

            # argumentos X , Tau -> produz o par de tags  A1, A0
            assert X.ndim == 1 , f"X={X} deve ser um vetor de {n} bits ou {n//8} bytes"
            Tb = self.b.maskB(Tau) ; Tu = self.u.maskB(Tau) ; Tv = self.v.maskB(Tau)
            return (Tb + (xv * Tu) + (xu * Tv) , Tu * Tv)

        def set_c(self, c=None, X=None):   
            assert not (c is None  and X is None), f"one of the arguments must be set"   
            if c is None:                            
                self.c = self.evalB(X)
            else:
                self.c = c

    return


if __name__ == "__main__":
    app.run()
