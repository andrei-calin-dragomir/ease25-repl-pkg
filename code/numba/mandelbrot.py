# The Computer Language Benchmarks Game
# https://salsa.debian.org/benchmarksgame-team/benchmarksgame/
#
# contributed by Tupteq
# 2to3 - fixed by Daniele Varrazzo, fixed by Isaac Gouy

import sys
from numba import njit

@njit
def critical_loop(z, c, bit, byte_acc):
    for i in range(50):
        z = z * z + c
        if abs(z) >= 2.0:
            break
        else:
            byte_acc += bit
        return z, byte_acc

def main(size):
    cout = sys.stdout.buffer.write
    #size = int(sys.argv[1])
    xr_size = range(size)
    xr_iter = range(50)
    bit = 128
    byte_acc = 0

    cout(("P4\n%d %d\n" % (size, size)).encode('ascii'))

    size = float(size)
    for y in xr_size:
        fy = 2j * y / size - 1j
        for x in xr_size:
            z = 0j
            c = 2. * x / size - 1.5 + fy

            z, bit_acc = critical_loop(z, c, bit, byte_acc)

            if bit > 1:
                bit >>= 1
            else:
                cout(bytes([byte_acc]))
                bit = 128
                byte_acc = 0

        if bit != 128:
            cout(bytes([byte_acc]))
            bit = 128
            byte_acc = 0

main(500)
