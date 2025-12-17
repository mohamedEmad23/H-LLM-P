;; #state features
4
+at[A]
+at[C]
+at[D]
+path-complete[]

;; Mutex Groups
4
0 0 +at[A]
1 1 +at[C]
2 2 +at[D]
3 3 +path-complete[]

;; further strict Mutex Groups
0

;; further non strict Mutex Groups
0

;; known invariants
0

;; Actions
3
5
1 -1
0 2  -1
0 1  -1
15
0 -1
0 1  -1
0 0  -1
0
2 -1
0 3  -1
-1

;; initial state
0 -1

;; goal
3 2 -1

;; tasks (primitive and abstract)
4
0 traverse[C,D]
0 traverse[A,C]
0 complete-path[D]
1 __top[]

;; initial abstract task
3

;; methods
1
<<__top_method;find-path[A,D];path-with-known-weights;0;-1,-2>;path-with-known-weights_splitted_1[A,D];_splitting_method_path-with-known-weights_splitted_1;0;-1,-2,1>
3
1 0 2 -1
1 2 0 1 0 2 -1
