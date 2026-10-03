"""One-off: precompute deterministic row_hash (uint32 from md5 of full row bytes) and cache.

Vectorized via struct packing; deterministic across runs and machines.
Column order/fixed formatting is the hash source: floats reinterpreted as raw
little-endian float64 bytes, ints as int64 bytes; column order fixed = config order.
"""
import hashlib
import time

import numpy as np
import pandas as pd

import config as C

t0 = time.time()
df = pd.read_parquet(C.PARQUET)
print("load", round(time.time() - t0, 1))

cols = C.FEATURES + [C.TREATMENT, C.VISIT, C.CONVERSION, C.EXPOSURE]  # fixed order

arrays = []
for c in cols:
    if c in (C.TREATMENT, C.VISIT, C.CONVERSION, C.EXPOSURE):
        arrays.append(df[c].to_numpy(dtype=np.int64))
    else:
        arrays.append(df[c].to_numpy(dtype=np.float64).view(np.uint64))

# pack to fixed-width little-endian byte rows
X = np.array(arrays)  # (ncols, nrows)
n = len(df)
digest = np.empty(n, dtype=np.uint32)
B = 1_000_000
for s in range(0, n, B):
    chunk = X[:, s:s + B]
    buf = b"".join(
        bytes(np.ascontiguousarray(chunk[i]).view(np.uint8)) for i in range(X.shape[0])
    )
    # we need md5 per ROW, not per buffer; so transpose chunk packing per row
for s in range(0, n, B):
    pass

out = np.empty(n, dtype=np.uint32)
for s in range(0, n, B):
    sub = X[:, s:s + B]
    rows = sub.T.copy()  # (rows, ncols); each cell = uint64 view of the feature value
    byt = rows.view(np.uint8).reshape(-1, X.shape[0] * 8)
    flat = np.ascontiguousarray(byt)
    for r in range(0, flat.shape[0], 8192):
        blk = flat[r:r + 8192]
        for i in range(blk.shape[0]):
            out[s + r + i] = int.from_bytes(hashlib.md5(blk[i].tobytes()).digest()[:4], "big")

df["row_hash"] = out.astype(np.int64)
df.to_parquet(C.ROOT / "criteo_uplift_v2_hashed.parquet")
print("done in", round(time.time() - t0, 1), "s")
print(df["row_hash"].head(3).tolist())
