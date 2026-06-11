# /// script
# dependencies = [
#     "marimo",
#     "numpy==2.4.6",
#     "pytest==9.0.3",
# ]
# requires-python = ">=3.13"
# ///

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")

with app.setup:
    import marimo  as mo
    import asyncio as aio
    import numpy   as np
    from   secrets import randbits, token_bytes
    from bits import bits


@app.class_definition
class Master(object):
    def __init__(self, ksize):
        master = np.random.default_rng(randbits(ksize))
        rngs   = master.spawn(3)
        parties = [Party(rngs[i]) for i in range(3)]

    async def main(self):
        pass


@app.class_definition
class Party(object):
    def __init__(self,rng):
        self.rng = rng


@app.cell
def _():
    m = Master(16)
    return


if __name__ == "__main__":
    app.run()
