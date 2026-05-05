import marimo

__generated_with = "0.20.4"
app = marimo.App()


@app.cell
def _(kappa, m, n, tsize):
    from os import urandom
    import numpy as np
    import arrays as ar
    import config
    globals().update(config.params)

    def svole():
    # In[70]:

        class Prover(object):

            def __init__(self):
                pass

            def accept(self, items: ar.bits, ots):
                self.items = items
                signs = list(items.unpack())
                self.tags = [ot.get(sig) for sig, ot in zip(signs, ots)]

            def reveal(self):
                return (self.items, self.tags)

        class Verifier(object):

            def __init__(self, delta: ar.bits=None):
                if delta is None:
                    delta = ar.bits_rng_sampler().secrets(tsize)
                self.delta = delta
                self.OT_class = ar.one_of_two_bytes_OT()
                self.sampler = ar.bits_hash_expand()

            def accept(self, sid: int=0, nitems: int=n):
                tweak = str(sid).encode()
                self.qs = self.sampler.QS(tweak, nitems)
                ots = [self.OT_class(q, q + self.delta) for q in self.qs]
                return ots

            def reveal(self):
                return (self.delta, self.qs)

        class __main__(object):

            def __init__(self, delta: ar.bits=None):
                self.verifier = Verifier(delta)
                self.prover = Prover()

            def run_accept(self, items, sid: int=0):
                ots = self.verifier.accept(sid, nitems=8 * len(items))
                self.prover.accept(items, ots)

            def run_reveal(self):
                X, tags = self.prover.reveal()
                delta, qs = self.verifier.reveal()
                items = X.unpack()
                for it, tg, q in zip(items, tags, qs):
                    try:
                        assert tg == q if it == 0 else tg == q + delta, f'erro de validação SVOLE'
                    except ValueError:
                        return False
                return True
        return __main__

    def cs_to_bytes(cs):
        data = ar.pack([0 if c == ar.zero else 1 for c in cs])
        return data.tobytes()

    def cs_from_bytes(cs_: bytes):
        data = ar.bits(cs_).unpack()
        return [ar.zero if b == 0 else ar.ones for b in data]

    def keysGen():
        master = urandom(kappa)
        sk = ar.bits_rng_sampler(master + b'sk').secrets(n // 8)
        seed = sk.hash()
        pols = ar.bits_hash_expand(seed).POLS(m)
        cs = [pol.eval(sk) for pol in pols]
        pk = {'cs': cs_to_bytes(cs), 'seed': seed}
        delta = ar.bits_rng_sampler(master + b'vk').secrets(tsize)
        return (sk, pk, delta)  # master_seed

    def expand(pk):  # sk
        cs = cs_from_bytes(pk['cs'])
        seed = pk['seed']  # pk
        pols = ar.bits_hash_expand(key=seed).POLS(m)
        for c, pol in zip(cs, pols):
            pol.set_c(c=c)
        return pols
      # vk
    def zk_vole():

        class Prover(object):

            def __init__(self, ots, sk, pk):
                self.sk = sk
                self.pk = pk
                self.ots = ots

            def Commit(self):
                pass

            def Reply(self, challendge):
                psi = ar.bits_rng_sampler().secrets(m // 8)
                items = self.sk.append(psi)
                signs = list(items.unpack())
                tags = [ot.get(sig) for sig, ot in zip(signs, self.ots)]
                pols = expand(self.pk)
                As = [pol.eval(self.sk, Tau=tags[:n]) for pol in pols]
                R = ar.bits(challendge)
                A1 = R.mask([a1 for a1, _ in As]) + R.mask(psi)
                A0 = R.mask([a0 for _, a0 in As]) + R.mask(tags[n:])
                return (A1, A0)

        class Verifier(object):

            def __init__(self, delta, pk):
                self.delta = delta
                self.pk = pk

            def Challendge(self, message: bytes=None):
                if message is None:
                    message = urandom(16)
                R = ar.bits_rng_sampler(seed=ar.bits(message)).secrets(m // 8)
                return R.tobytes()

            def Verify(self, challendge, reply):
                qs = ar.bits_hash_expand(self.delta.hash()).QS(tweak=b'\x00', nitems=n + m)
                pols = expand(self.pk)
                Bs = [pol.eval(qs[:n], Y=self.delta) for pol in pols]
                R = ar.bits(challendge)
                B = R.mask(Bs) + R.mask(qs[n:])
                A1, A0 = reply
                assert B == A1 * self.delta + A0, f'verifier fail'
                return True

        class __main__(object):

            def __init__(self):
                sk, pk, delta = keysGen()
                OT_class = ar.one_of_two_bytes_OT()
                qs = ar.bits_hash_expand(delta.hash()).QS(tweak=b'\x00', nitems=n + m)
                ots = [OT_class(q, q + delta) for q in qs]
                self.prover = Prover(ots, sk, pk)
                self.verifier = Verifier(delta, pk)

            def run_pk(self, message: bytes=None):
                try:
                    self.prover.Commit()
                    cha = self.verifier.Challendge(message)
                    reply = self.prover.Reply(cha)
                    return self.verifier.Verify(cha, reply)
                except AssertionError as err:
                    return err
        return __main__

    def SignClass():

        class Verifier(object):

            def __init__(self, qs, delta, pk):
                self.delta = delta
                self.qs = qs
                self.pols = expand(pk)

            def verify(self, signature, message):
                Bs = [pol.eval(self.qs[:n], Y=self.delta) for pol in self.pols]
                R = ar.bits_rng_sampler(seed=ar.bits(message)).secrets(m // 8)
                B = R.mask(Bs) + R.mask(self.qs[n:])
                A1_, A0_ = signature
                return B == ar.bits(A1_) * self.delta + ar.bits(A0_)

        class Signer(object):

            def __init__(self, ots, sk, pk):
                self.sk = sk
                self.pk = pk
                self.ots = ots

            def sign(self, message):
                pols = expand(self.pk)
                psi = ar.bits_rng_sampler().secrets(m // 8)
                items = self.sk.append(psi)
                signs = list(items.unpack())
                tags = [ot.get(sig) for sig, ot in zip(signs, self.ots)]
                As = [pol.eval(self.sk, Tau=tags[:n]) for pol in pols]
                R = ar.bits_rng_sampler(seed=ar.bits(message)).secrets(m // 8)
                A1 = R.mask([a1 for a1, _ in As]) + R.mask(psi)
                A0 = R.mask([a0 for _, a0 in As]) + R.mask(tags[n:])
                return (A1.tobytes(), A0.tobytes())

        class __main__(object):

            def __init__(self):
                sk, pk, delta = keysGen()
                OT_class = ar.one_of_two_bytes_OT()
                qs = ar.bits_hash_expand(delta.hash()).QS(tweak=b'\x00', nitems=n + m)
                ots = [OT_class(q, q + delta) for q in qs]
                self.verifier = Verifier(qs, delta, pk)
                self.signer = Signer(ots, sk, pk)

            def sign(self, message):
                return self.signer.sign(message)

            def verify(self, signature, message):
                return self.verifier.verify(signature, message)
        return __main__

    return ar, np, urandom


@app.cell
def _(M, N, ar, kappa, m, n, np, urandom):
    from random import randrange
    from hashlib import shake_256
    from config import params
    from pickle import loads, dumps
    globals().update(params)

    def svole():
        as_bits = lambda x: ar.bits([x])

        class Prover(object):

            def __init__(self, key: bytes=None):
                if key is None:
                    key = urandom(kappa)
                self.sampler = ar.bits_hash_expand(key)

            def accept(self, items: ar.bits, sid: int=0):
                self.items = items
                tweak = str(sid).encode()
                self.Z = self.sampler.Z(tweak=tweak, nitems=N)
                sampler = ar.bits_rng_sampler()
                ot_cls = ar.N_1_of_N_OT()
                ots = []
                self.tags = []
                for item in items:
                    ts = sampler.secrets(l=N)
                    x = as_bits(item)
                    ts[0] = (x + ts[1:].sum())[0]
                    ts_ = [ar.bits(u) for u in zip(np.arange(N), ts)]
                    ots.append(ot_cls(*ts_))
                    tag = ar.as_tag(0)
                    for u in ts_:
                        z = self.Z[u[0]]
                        t = ar.as_tag(u[1])
                        tag = tag + t * z
                    self.tags.append(tag)
                return ots

            def reveal(self):
                return (self.items, self.tags)

        class Verifier(object):

            def __init__(self, key: bytes):
                self.sampler = ar.bits_hash_expand(key)

            def accept(self, ots, b: int=None, sid: int=0):
                tweak = str(sid).encode()
                self.Z = self.sampler.Z(tweak=tweak, nitems=N)
                if b is None:
                    b = randrange(N)
                delta = self.Z[b]
                self.qs = []
                for ot in ots:
                    ts = ot.get(b, tsize=2)
                    q = ar.as_tag(0)
                    for u in ts:
                        z = self.Z[u[0]]
                        t = ar.as_tag(u[1])
                        q = q + t * (z + delta)
                    self.qs.append(q)
                self.delta = delta

            def reveal(self):
                return (self.delta, self.qs)

        class __main__(object):

            def __init__(self, key: bytes=None):
                if key is None:
                    key = urandom(kappa)
                self.verifier = Verifier(key)
                self.prover = Prover(key)
      #assert x == ts.sum(), f"erro na validação de ts, x"
            def run(self, items, sid: int=0):
                ots = self.prover.accept(items, sid)  #print(ts_)
                self.verifier.accept(ots, sid)

            def test_svole(self):
                items = ar.bits(urandom(n // 8))
                self.run(items)
                items, tags = self.prover.reveal()
                delta, qs = self.verifier.reveal()
                for item, tag, q in zip(items, tags, qs):
                    try:
                        x = ar.as_tag(item)
                        lhs = q + tag
                        rhs = x * delta
                        assert lhs == rhs, f'erro de validação SVOLE\nlhs={lhs}\nrhs={rhs}'
                    except AssertionError as msg:
                        print(msg)
                        return False
                return True
        return __main__

    def keysGen():
        master = urandom(kappa)
        sk = ar.bits_rng_sampler(master + b'sk').secrets(n // 8)
        seed = sk.hash()
        sampler = ar.bits_hash_expand(seed)
        pols = sampler.POLS(m)
        cs = []
        for pol in pols:
            c = pol.evalB(sk)
            cs.append(c)  #print(ts)
        pk = {'cs': cs, 'seed': seed}
        return (sk, pk)

    def expand(pk):
        cs = pk['cs']
        seed = pk['seed']
        pols = ar.bits_hash_expand(key=seed).POLS(m)
        for c, pol in zip(cs, pols):
            pol.set_c(c=c)
        return pols

    def zk_vole():

        class Prover(object):

            def __init__(self, vole, pk, sk):
                self.vole = vole
                self.sk = sk
                self.pk = pk

            def Commit(self, sid: int=0):
                self.mu = ar.bits_rng_sampler().secrets(m)
                self.items = ar.bits(np.concatenate((self.sk, self.mu)))
                ots = self.vole.prover.accept(self.items, sid=sid)
                _, tags_ = self.vole.prover.reveal()
                self.tags = tags_[:n // 8]
                self.csi = tags_[n // 8:]
                return ots

            def Reply(self, challendge):
                pols = expand(self.pk)
                A1s = []
                A0s = []
                for pol in pols:
                    a1, a0 = pol.evalB(X=self.sk, Tau=self.tags)
                    A1s.append(a1)
                    A0s.append(a0)
                R = ar.bits(challendge)
                reply = (R.maskB(A1s) + R.maskB(self.mu), R.maskB(A0s) + R.maskB(self.csi))
                return reply

        class Verifier(object):

            def __init__(self, vole, pk):
                self.vole = vole
                self.pk = pk

            def Challendge(self, message: bytes=None, sid: int=0):
                if message is None:
                    token = urandom(16)
                else:
                    token = shake_256(message).digest(16)  # master_seed
                seed = ar.bits(token + str(sid).encode())
                R = ar.bits_rng_sampler(seed=seed).secrets(m)  # sk
                return R.tobytes()
      # pk
            def Verify(self, ots, challendge, reply, sid: int=0):
                self.vole.verifier.accept(ots, sid=sid)
                delta, qs_ = self.vole.verifier.reveal()
                qs = qs_[:n // 8]
                rho = qs_[n // 8:]
                pols = expand(self.pk)
                Bs = [pol.evalB(X=qs, Y=delta) for pol in pols]
                R = ar.bits(challendge)
                B = R.maskB(Bs) + R.maskB(rho)
                A1, A0 = reply
                assert B == A1 * delta + A0, f'erro na verificação em sid={sid}'

        class __main__(object):

            def __init__(self, key: bytes=None):
                if key is None:
                    key = urandom(kappa)
                self.sk, self.pk = keysGen()
                self.vole = svole()(key)

            def run_zk(self, message: bytes=None):
                if message == None:
                    message = urandom(16)
                verifier = Verifier(self.vole, self.pk)
                prover = Prover(self.vole, self.pk, self.sk)
                try:
                    for sid in range(M):
                        ots = prover.Commit(sid=sid)
                        cha = verifier.Challendge(message, sid=sid)
                        reply = prover.Reply(cha)
                        verifier.Verify(ots, cha, reply, sid=sid)  #    print(f"sk={self.sk}\nmu = {self.mu}")
                    return True
                except AssertionError as err:
                    print(err)
                    return False

            def sign_pv(self, message: bytes):
                verifier = Verifier(self.vole, self.pk)
                prover = Prover(self.vole, self.pk, self.sk)  #
                sign = dict()
                for sid in range(M):
                    ots = prover.Commit(sid=sid)
                    cha = verifier.Challendge(message, sid=sid)
                    reply = prover.Reply(cha)
                    sign[sid] = {'ots': ots, 'reply': reply}
                return sign  #    print(f"R={R}")

            def verify_pv(self, sign, message: bytes):
                verifier = Verifier(self.vole, self.pk)
                try:
                    for sid in range(M):
                        tuple = sign[sid]
                        verifier.Verify(tuple['ots'], verifier.Challendge(message, sid), tuple['reply'], sid=sid)
                    return True
                except AssertionError as err:
                    print(err)
                    return False
        return __main__

    return


if __name__ == "__main__":
    app.run()
