def main(n):
   perm1 = [0] * n   
   for i in range(n): perm1[i] = i      
   perm = [0] * n
   count = [0] * n       
   f = flips = nperm = checksum = j = k = r = 0          
  
   r = n
   while r > 0: 
      i = 0  
      while r != 1: count[r-1] = r; r -= 1  
      while i < n: perm[i] = perm1[i]; i += 1  

      f = 0
      k = perm[0]  
      while k != 0:
         i = 0  
         while 2*i < k:          
            t = perm[i]; perm[i] = perm[k-i]; perm[k-i] = t  
            i += 1           

         k = perm[0]
         f += 1   
       
      if f > flips: flips = f         
      if (nperm & 0x1) == 0: 
         checksum += f 
      else: 
         checksum -= f
   
      more = True
      while more:  
         if r == n:
            print( checksum )                     
            return flips 

         p0 = perm1[0]
         i = 0
         while i < r:
            j = i + 1
            perm1[i] = perm1[j]
            i = j            

         perm1[r] = p0 
         
         count[r] -= 1        
         if count[r] > 0: more = False
         else: r += 1 

      nperm += 1

   return flips      
