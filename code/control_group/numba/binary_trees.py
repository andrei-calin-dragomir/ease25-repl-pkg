from numba import njit, deferred_type, optional, typeof, int32
from numba.experimental import jitclass

NodeType = deferred_type()
spec = [
    ('left', optional(NodeType)),
    ('right', optional(NodeType))
]

@jitclass(spec)
class Tree:
  def __init__(self, left, right):
    self.left = left
    self.right = right

@njit
def node_count(tree):
    if tree.left is None:
        return 1
    else:
        return 1 + node_count(tree.left) + node_count(tree.right)

@njit
def with_(depth):
    return Tree(None, None) if (depth == 0) \
        else Tree( with_(depth-1), with_(depth-1) )    

@njit
def clear(tree):
    if tree.left is not None:
        clear(tree.left)
        left = None
        clear(tree.right)
        right = None  

NodeType.define(Tree.class_type.instance_type)

@njit
def count(depth):
    t = with_(depth)
    c = node_count(t)
    clear(t)

    return c 

@njit
def stretch(depth):
    print("stretch tree of depth", depth, '\t', "check:", count(depth)) 

@njit
def main(n):
    MIN_DEPTH = 4  
    max_depth = (MIN_DEPTH + 2) if (MIN_DEPTH + 2 > n) else n
    stretch_depth = max_depth + 1   
                                                              
    stretch(stretch_depth) 
    long_lived_tree = with_(max_depth)
    for depth in range(MIN_DEPTH, stretch_depth, 2):
        iterations = 1 << (max_depth - depth + MIN_DEPTH)
        sum = 0
        for i in range(iterations):
            sum += count(depth)        
        print(f"{iterations}\t trees of depth {depth}\t check: {sum}")             

    c = node_count(long_lived_tree);         
    clear(long_lived_tree);         

    print(f"long lived tree of depth {max_depth}\t check: {c}") 