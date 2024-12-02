from math import sqrt
from numba import njit, types, typed
import sys

@njit
def eval_A(i, j):
  return 1.0/((i+j)*(i+j+1)/2+i+1)

@njit
def eval_A_times_u(N, u, Au):
  for i in range(N):  
    Au[i] = 0 
    for j in range(N):
        Au[i]+=eval_A(i,j)*u[j]
@njit
def eval_At_times_u(N, u, Au):
  for i in range(N):  
    Au[i]=0
    for j in range(N): Au[i]+=eval_A(j,i)*u[j]   

@njit
def eval_AtA_times_u(N, u, AtAu):
  #v=[0]*N;
  v = typed.List.empty_list(types.float64)
  for i in range(N): v.append(0);

  eval_A_times_u(N,u,v); eval_At_times_u(N,v,AtAu)

@njit
def main(n):
  u = typed.List.empty_list(types.float64)
  v = typed.List.empty_list(types.float64)

  for i in range(n): u.append(1)
  for i in range(n): v.append(0)

  for i in range(10):
    eval_AtA_times_u(n,u,v)
    eval_AtA_times_u(n,v,u)

  vBv=vv=0
  for i in range(n): vBv+=u[i]*v[i]; vv+=v[i]*v[i]
  print(float(int(sqrt(vBv/vv) * 10**9)) / 10**9)

if __name__ == '__main__':
  main( int(sys.argv[1]) if len(sys.argv) > 1 else 100 )