import numpy as np
import math
import sys
np.set_printoptions(threshold=sys.maxsize)
nr = 23
rmax=500
nz = 15
zmax=150
nphi = 30
rmid = nr/2
zmid = nz/2
testarray = np.zeros((nz, nr))
for z in range(nz):
    for r in range(nr):
        if (np.abs(zmid - z) >= 0.15*np.abs(rmid - r)):
            testarray[z, r] = 1
print(testarray)
newArray = (np.tile(testarray.T, (nphi, 1, 1)))
print(newArray.shape)