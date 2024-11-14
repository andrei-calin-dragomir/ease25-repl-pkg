# The Computer Language Benchmarks Game
# https://salsa.debian.org/benchmarksgame-team/benchmarksgame/
#
# contributed by Isaac Gouy

from typing import Optional

class Tree:
  left: Optional[Tree]
  right: Optional[Tree]

  def __init__(self, left: Optional[Tree], right: Optional[Tree]):
    self.left = left
    self.right = right 
    
  def with_(depth):
    return Tree(None, None) if (depth == 0) \
        else Tree( Tree.with_(depth-1), Tree.with_(depth-1) )    
    
  def node_count(self):
    return 1 if (self.left is None) \
        else 1 + self.left.node_count() + self.right.node_count()
        
  def clear(self):
    if self.left is not None:
      self.left.clear()
      self.left = None
      # del self.left
      self.right.clear()
      self.right = None  

def count(depth):
  t = Tree.with_(depth);         
  c = t.node_count();
  t.clear(); 
  return c;   

def stretch(depth):
  #print("stretch tree of depth %d\t check:" % depth, count(depth))   
 print(f"stretch tree of depth %d\t check: {count(depth)}")  


def main(n):
  MIN_DEPTH = 4  
  max_depth = (MIN_DEPTH + 2) if (MIN_DEPTH + 2 > n) else n
  stretch_depth = max_depth + 1   
  
  stretch(stretch_depth) 
  long_lived_tree = Tree.with_(max_depth) 
  
  for depth in range(MIN_DEPTH, stretch_depth, 2): 
    iterations = 1 << (max_depth - depth + MIN_DEPTH)  
    sum = 0   
    for i in range(iterations):           
      sum += count(depth)        
    print(f"{iterations}\t trees of depth {depth}\t check: {sum}")             
    # print("%d\t trees of depth %d\t check:" % (iterations, depth), sum)             
         
  c = long_lived_tree.node_count();         
  long_lived_tree.clear();         

  print(f"long lived tree of depth {max_depth}\t check: {c}")  
  #print("long lived tree of depth %d\t check:" % max_depth, c)  
      
#if __name__ == '__main__':
  #main( int(sys.argv[1]) if len(sys.argv) > 1 else 10 )
