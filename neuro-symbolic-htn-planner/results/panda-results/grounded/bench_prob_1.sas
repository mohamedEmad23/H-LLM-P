;; #state features
5
-expected-value-calculated[]
-path-chosen[]
+expected-value-calculated[]
+path-chosen[]
+at[end]

;; Mutex Groups
5
0 0 -expected-value-calculated[]
1 1 -path-chosen[]
2 2 +expected-value-calculated[]
3 3 +path-chosen[]
4 4 +at[end]

;; further strict Mutex Groups
0

;; further non strict Mutex Groups
0

;; known invariants
0

;; Actions
7
0
1 -1
-1
-1
1
4 -1
-1
-1
1
3 -1
0 4  -1
-1
0
1 2 -1
-1
-1
1
1 -1
0 3  -1
0 1  -1
1
1 -1
0 3  -1
0 1  -1
1
0 -1
0 2  -1
0 0  -1

;; initial state
1 0 -1

;; goal
-1

;; tasks (primitive and abstract)
9
0 __method_precondition_strategic-approach[start]
0 verify-goal[end]
0 traverse-to-goal[end]
0 __method_precondition_choose-safe-path-strategic[]
0 select-safe-path[]
0 select-risky-path[]
0 calculate-expected-values[start]
1 __top[]
1 analyze-and-choose-path[start]

;; initial abstract task
7

;; methods
3
<__top_method;solve-probabilistic-graph[start,end];strategic-approach;0;-1,-2,-3,-4,-5>
7
0 6 8 2 1 -1
0 4 0 3 0 2 0 1 3 4 2 3 1 2 -1
choose-safe-path-strategic
8
3 4 -1
0 1 -1
choose-risky-path-strategic
8
3 5 -1
0 1 -1
