from numba import njit, deferred_type, optional
from numba.experimental import jitclass

NodeType = deferred_type()

spec = [
    ('left', optional(NodeType)),
    ('right', optional(NodeType))
]

@jitclass(spec)
class Tree:
  def __init__(self, left, right):
    self.left = None
    self.right = None 

  def with_(depth):
    return Tree(None, None) if (depth == 0) \
        else Tree( Tree.with_(depth-1), Tree.with_(depth-1) )    

NodeType.define(Tree.class_type.instance_type)

#@njit
#def count(depth):
#    Tree.with_(depth)
