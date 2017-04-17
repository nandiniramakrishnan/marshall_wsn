import copy

gridSize = [5,6]

avoidList = [(1,1), (2,3), (3,3)]

curr_row = 2
curr_col = 1

dest_row = 3
dest_col = 4


def findPath(curr_row, curr_col, dest_row, dest_col, avoidList):
    path_found = 0
    paths = [[(curr_row, curr_col)]]
    paths_to_remove = []
    
    while path_found == 0:
        paths_traverse = copy.deepcopy(paths)
        for path in paths_traverse:
            if (dest_row, dest_col) in path:
                path_found = 1
                return path
            
            elif (dest_row, dest_col) not in path:
                tmp_path = path

                row = tmp_path[len(tmp_path)-1][0]
                col = tmp_path[len(tmp_path)-1][1]

                adjacents = []
                if row >= 1:
                    adjacents.append((row-1, col))
                if row < (gridSize[0]-1):
                    adjacents.append((row+1, col))
                if col < (gridSize[1]-1):
                    adjacents.append((row, col+1))
                if col >= 1:
                    adjacents.append((row, col-1))

                for i in range(len(adjacents)):
                    if (adjacents[i] not in avoidList) and (adjacents[i] not in tmp_path):
                        tmp_path.append(adjacents[i])
                        tmp_copy = copy.deepcopy(tmp_path)
                        paths.append(tmp_copy)
                        tmp_path.remove(adjacents[i])

#find_route(curr_row, curr_col, dest_row, dest_col, avoidList, [], direction)
paths = findPath(curr_row, curr_col, dest_row, dest_col, avoidList)
print(paths)
