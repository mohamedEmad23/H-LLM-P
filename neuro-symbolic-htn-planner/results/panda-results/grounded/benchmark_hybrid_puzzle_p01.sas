;; #state features
7
+on-peg[disk1,peg-a]
+peg-locked[peg-c]
+at-graph-node[n1]
+solving-unlock[peg-c]
+at-graph-node[n2]
+peg-unlocked[peg-c]
+on-peg[disk1,peg-c]

;; Mutex Groups
7
0 0 +on-peg[disk1,peg-a]
1 1 +peg-locked[peg-c]
2 2 +at-graph-node[n1]
3 3 +solving-unlock[peg-c]
4 4 +at-graph-node[n2]
5 5 +peg-unlocked[peg-c]
6 6 +on-peg[disk1,peg-c]

;; further strict Mutex Groups
0

;; further non strict Mutex Groups
0

;; known invariants
0

;; Actions
16
0
5 0 -1
-1
-1
1
5 0 -1
0 6  -1
0 0  -1
0
0 5 -1
-1
-1
0
5 6 -1
-1
-1
1
5 6 -1
0 6  -1
-1
0
6 5 -1
-1
-1
1
5 -1
-1
-1
0
0 1 -1
-1
-1
0
2 -1
-1
-1
1
2 -1
-1
0 2  -1
1
4 -1
-1
0 4  -1
1
2 -1
0 4  -1
0 2  -1
1
1 -1
0 3  0 2  -1
-1
0
1 -1
-1
-1
1
1 3 -1
0 5  -1
0 3  0 1  -1
0
6 1 -1
-1
-1

;; initial state
1 0 -1

;; goal
-1

;; tasks (primitive and abstract)
24
0 __method_precondition_move-single[disk1,peg-a,peg-c]
0 move-disk[disk1,peg-a,peg-c]
0 __method_precondition_solve-direct-move[peg-c,peg-a,disk1]
0 __method_precondition_move-single[disk1,peg-c,peg-c]
0 move-disk[disk1,peg-c,peg-c]
0 __method_precondition_solve-direct-move[peg-c,peg-c,disk1]
0 mark-solved[peg-c]
0 __method_precondition_solve-by-unlock-then-move[peg-c,peg-a,disk1]
0 __method_precondition_graph-single-step[n1,n3]
0 traverse-graph[n1,n3]
0 traverse-graph[n2,n3]
0 traverse-graph[n1,n2]
0 enter-graph[peg-c,n1]
0 __method_precondition_unlock-via-graph_base_base[peg-c]
0 complete-unlock[peg-c]
0 __method_precondition_solve-by-unlock-then-move[peg-c,peg-c,disk1]
1 __top[]
1 solve-hybrid-puzzle[peg-c]
1 solve-direct-move_splitted_4[peg-c]
1 solve-direct-move_splitted_2[disk1,peg-a,peg-c]
1 solve-direct-move_splitted_2[disk1,peg-c,peg-c]
1 solve-by-unlock-then-move_splitted_1[disk1,peg-a,peg-c]
1 solve-unlock-graph[peg-c,n1,n3]
1 solve-by-unlock-then-move_splitted_1[disk1,peg-c,peg-c]

;; initial abstract task
16

;; methods
20
__top_method
16
17 -1
-1
solve-direct-move
17
18 6 -1
0 1 -1
_splitting_method_solve-direct-move_splitted_4
18
2 19 -1
0 1 -1
<_splitting_method_solve-direct-move_splitted_2;move-tower[disk1,peg-a,peg-c,peg-a];move-single;0;-1,-2>
19
0 1 -1
0 1 -1
<_splitting_method_solve-direct-move_splitted_2;move-tower[disk1,peg-a,peg-c,peg-b];move-single;0;-1,-2>
19
0 1 -1
0 1 -1
<_splitting_method_solve-direct-move_splitted_2;move-tower[disk1,peg-a,peg-c,peg-c];move-single;0;-1,-2>
19
0 1 -1
0 1 -1
_splitting_method_solve-direct-move_splitted_4
18
5 20 -1
0 1 -1
<_splitting_method_solve-direct-move_splitted_2;move-tower[disk1,peg-c,peg-c,peg-a];move-single;0;-1,-2>
20
3 4 -1
0 1 -1
<_splitting_method_solve-direct-move_splitted_2;move-tower[disk1,peg-c,peg-c,peg-b];move-single;0;-1,-2>
20
3 4 -1
0 1 -1
<_splitting_method_solve-direct-move_splitted_2;move-tower[disk1,peg-c,peg-c,peg-c];move-single;0;-1,-2>
20
3 4 -1
0 1 -1
<<<solve-by-unlock-then-move;unlock-peg[peg-c];unlock-via-graph;1;0,-1,-2,-3,2,3>;unlock-via-graph_splitted_5[peg-c];_splitting_method_unlock-via-graph_splitted_5;2;0,1,-1,-2,3,4,5>;unlock-via-graph_splitted_3[peg-c,n1];_splitting_method_unlock-via-graph_splitted_3;3;0,1,2,-1,4,5,6>
17
7 13 12 22 14 21 6 -1
5 6 0 5 0 6 0 3 0 1 0 4 0 2 3 5 3 4 1 5 1 3 1 4 1 2 4 5 2 5 2 3 2 4 -1
<_splitting_method_solve-by-unlock-then-move_splitted_1;move-tower[disk1,peg-a,peg-c,peg-a];move-single;0;-1,-2>
21
0 1 -1
0 1 -1
<_splitting_method_solve-by-unlock-then-move_splitted_1;move-tower[disk1,peg-a,peg-c,peg-b];move-single;0;-1,-2>
21
0 1 -1
0 1 -1
<_splitting_method_solve-by-unlock-then-move_splitted_1;move-tower[disk1,peg-a,peg-c,peg-c];move-single;0;-1,-2>
21
0 1 -1
0 1 -1
graph-single-step
22
8 9 -1
0 1 -1
graph-two-step
22
8 11 10 -1
0 2 0 1 1 2 -1
<<<solve-by-unlock-then-move;unlock-peg[peg-c];unlock-via-graph;1;0,-1,-2,-3,2,3>;unlock-via-graph_splitted_5[peg-c];_splitting_method_unlock-via-graph_splitted_5;2;0,1,-1,-2,3,4,5>;unlock-via-graph_splitted_3[peg-c,n1];_splitting_method_unlock-via-graph_splitted_3;3;0,1,2,-1,4,5,6>
17
15 13 12 22 14 23 6 -1
5 6 0 5 0 6 0 3 0 1 0 4 0 2 3 5 3 4 1 5 1 3 1 4 1 2 4 5 2 5 2 3 2 4 -1
<_splitting_method_solve-by-unlock-then-move_splitted_1;move-tower[disk1,peg-c,peg-c,peg-a];move-single;0;-1,-2>
23
3 4 -1
0 1 -1
<_splitting_method_solve-by-unlock-then-move_splitted_1;move-tower[disk1,peg-c,peg-c,peg-b];move-single;0;-1,-2>
23
3 4 -1
0 1 -1
<_splitting_method_solve-by-unlock-then-move_splitted_1;move-tower[disk1,peg-c,peg-c,peg-c];move-single;0;-1,-2>
23
3 4 -1
0 1 -1
