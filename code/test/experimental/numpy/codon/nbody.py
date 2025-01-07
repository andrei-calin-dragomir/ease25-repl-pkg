import math, sys
from python import numpy as np

eps_2 = np.float32(1e-6)
zero = np.float32(0.0)
one = np.float32(1.0)

def run_numpy_nbody(positions, weights):
    accelerations = np.zeros_like(positions)
    n = weights.size
    for j in range(n):
        # Compute influence of j'th body on all bodies
        r = positions[j] - positions
        rx = r[:,0]
        ry = r[:,1]
        sqr_dist = rx * rx + ry * ry + eps_2
        sixth_dist = sqr_dist * sqr_dist * sqr_dist
        inv_dist_cube = one / np.sqrt(sixth_dist)
        s = weights[j] * inv_dist_cube
        accelerations += (r.transpose() * s).transpose()
    return accelerations


def make_nbody_samples(n_bodies):
    positions = np.random.RandomState(0).uniform(-1.0, 1.0, (n_bodies, 2))
    weights = np.random.RandomState(0).uniform(1.0, 2.0, n_bodies)
    return positions.astype(np.float32), weights.astype(np.float32)

def main(n_bodies):
    positions, weights = make_nbody_samples(n_bodies)
    return run_numpy_nbody(positions, weights)

#if __name__ == "__main__":
#    arg1 = int(sys.argv[1])
#    res = main(arg1)
#    print(res)
main(200)
