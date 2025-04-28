from field_class import Field

def gauss(vectors: list[list[Field]]):
    n = len(vectors)
    m = len(vectors[0])
    row = 0
    for col in range(m):
        if row >= n:
            break
        for i in range(row, n):
            if vectors[i][col] != 0:
                vectors[i], vectors[row] = vectors[row], vectors[i]
                break
        if vectors[row][col] == 0:
            continue
        for i in range(n):
            if i != row and vectors[i][col]:
                val = vectors[i][col] / vectors[row][col]
                for j in range(col, m):
                    vectors[i][j] -= val * vectors[row][j]
        row += 1
    return vectors

def check_vector_in_hull(vectors, vector_for_check):
    vectors = gauss(vectors)
    n = len(vectors)
    m = len(vectors[0])
    for i in range(n):
        row = 0
        while row < m and vectors[i][row] == 0:
            row += 1
        if row == m:
            continue
        val = vector_for_check[row] / vectors[i][row]
        for j in range(m):
            vector_for_check[j] -= vectors[i][j] * val
    return vector_for_check == [0] * m