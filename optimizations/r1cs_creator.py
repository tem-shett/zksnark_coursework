import random

from field_class import Field
from consts import MOD
from single_r1cs import R1CS, R1CS_constraint, R1CS_term
from r1cs_utils import write_r1cs_to_file
from random import randint

def rand_F(only_01=False):
    return Field(randint(1, 1)) if only_01 else Field(randint(0, MOD - 1))

def random_part(r1cs: R1CS, max_var_num=None, k_not_zeros=None, only_01=False):
    assert(max_var_num + 1 >= k_not_zeros)
    if k_not_zeros is None:
        k_not_zeros = r1cs.num_variables
    if max_var_num is None:
        max_var_num = r1cs.num_variables - 1

    random_vector = [rand_F(only_01) for _ in range(max_var_num + 1)] + [Field(0) for _ in range(r1cs.num_variables - max_var_num - 1)]
    k_zeros = max_var_num - k_not_zeros
    while k_zeros > 0:
        i = randint(0, max_var_num)
        if random_vector[i] != 0:
            random_vector[i] = Field(0)
            k_zeros -= 1
    return r1cs.vector_to_constraint_part(random_vector)

def random_linear_combination(r1cs: R1CS, part_AB1, part_AB2, part_C1, part_C2):
    c1 = rand_F()
    c2 = rand_F()
    vec_AB1 = r1cs.constraint_part_to_vector(part_AB1)
    vec_AB2 = r1cs.constraint_part_to_vector(part_AB2)
    vec_C1 = r1cs.constraint_part_to_vector(part_C1)
    vec_C2 = r1cs.constraint_part_to_vector(part_C2)
    vec_AB = [vec_AB1[i] * c1 + vec_AB2[i] * c2 for i in range(r1cs.num_variables)]
    vec_C = [vec_C1[i] * c1 + vec_C2[i] * c2 for i in range(r1cs.num_variables)]
    return r1cs.vector_to_constraint_part(vec_AB), r1cs.vector_to_constraint_part(vec_C)

def calc_left(r1cs: R1CS, constraint_ind, iter, io):
    num_witness_variables = r1cs.num_variables - r1cs.io_size - r1cs.num_public_inputs
    cur_vars = io + r1cs.public_inputs[r1cs.num_public_inputs * iter:r1cs.num_public_inputs * (iter + 1)] + r1cs.witness[num_witness_variables * iter:num_witness_variables * (iter + 1)]
    calc_A = sum([cur_vars[term.variable] * term.coefficient for term in r1cs.constraints[constraint_ind].A])
    calc_B = sum([cur_vars[term.variable] * term.coefficient for term in r1cs.constraints[constraint_ind].B])
    return calc_A * calc_B


def create_with_extra_constraints(scheme_length=10, io_size=2, num_public_inputs=2, num_variables=30, num_vital_constraints=5, num_additional_constraints=20, k_not_zeros=4):
    r1cs = R1CS(None)
    r1cs.io_size = io_size
    r1cs.scheme_length = scheme_length
    r1cs.num_public_inputs = num_public_inputs
    r1cs.num_variables = num_variables
    r1cs.constraints = []

    num_witness_variables = r1cs.num_variables - r1cs.io_size - r1cs.num_public_inputs

    r1cs.public_inputs = [Field(1) if i % r1cs.num_public_inputs == 0 else rand_F() for i in range(r1cs.scheme_length * r1cs.num_public_inputs)]
    r1cs.witness = [rand_F() for _ in range(r1cs.scheme_length * num_witness_variables)]

    common_part = random_part(r1cs, r1cs.num_variables - num_vital_constraints, k_not_zeros)
    mapping_index_var = []
    for var in range(r1cs.num_variables - num_vital_constraints, r1cs.num_variables):
        constraint = R1CS_constraint(None)
        constraint.A = common_part
        constraint.B = random_part(r1cs, var - 1, k_not_zeros)
        constraint.C = [R1CS_term((var, 1))]
        mapping_index_var.append((len(r1cs.constraints), var - r1cs.io_size - r1cs.num_public_inputs))
        r1cs.constraints.append(constraint)
    io = [Field(0) for _ in range(r1cs.io_size)]
    for i in range(r1cs.scheme_length):
        for index, var in mapping_index_var:
            r1cs.witness[i * num_witness_variables + var] = calc_left(r1cs, index, i, io)
        cur_vars = io + r1cs.public_inputs[r1cs.num_public_inputs * i:r1cs.num_public_inputs * (i + 1)] + r1cs.witness[num_witness_variables * i:num_witness_variables * (i + 1)]
        io = cur_vars[len(cur_vars) - r1cs.io_size:len(cur_vars)]

    for _ in range(num_additional_constraints):
        i = random.randint(0, len(r1cs.constraints) - 1)
        j = random.randint(0, len(r1cs.constraints) - 1)
        constraint = R1CS_constraint(None)
        constraint.A = common_part
        constraint.B, constraint.C = random_linear_combination(r1cs, r1cs.constraints[i].B, r1cs.constraints[j].B, r1cs.constraints[i].C, r1cs.constraints[j].C)
        r1cs.constraints.append(constraint)

    r1cs.num_constraints = len(r1cs.constraints)
    return r1cs


def create_with_extra_variables(scheme_length=10, io_size=2, num_public_inputs=2, num_variables=50, num_vital_constraints=15, num_additional_constraints=10, k_not_zeros=10):
    r1cs = R1CS(None)
    r1cs.io_size = io_size
    r1cs.scheme_length = scheme_length
    r1cs.num_public_inputs = num_public_inputs
    r1cs.num_variables = num_variables
    r1cs.constraints = []

    num_witness_variables = r1cs.num_variables - r1cs.io_size - r1cs.num_public_inputs
    assert(num_witness_variables >= num_vital_constraints + num_additional_constraints)

    r1cs.public_inputs = [Field(1) if i % r1cs.num_public_inputs == 0 else rand_F() for i in range(r1cs.scheme_length * r1cs.num_public_inputs)]
    r1cs.witness = [rand_F() for _ in range(r1cs.scheme_length * num_witness_variables)]

    mapping_index_var = []
    for var in range(r1cs.num_variables - num_vital_constraints - num_additional_constraints, r1cs.num_variables - num_vital_constraints):
        constraint = R1CS_constraint(None)
        constraint.A = [R1CS_term((io_size, 1))]
        constraint.B = random_part(r1cs, var - 1, randint(1, 2))
        constraint.C = [R1CS_term((var, 1))]
        mapping_index_var.append((len(r1cs.constraints), var - r1cs.io_size - r1cs.num_public_inputs))
        r1cs.constraints.append(constraint)
    for var in range(r1cs.num_variables - num_vital_constraints, r1cs.num_variables):
        constraint = R1CS_constraint(None)
        constraint.A = random_part(r1cs, var - 1, k_not_zeros)
        constraint.B = random_part(r1cs, var - 1, k_not_zeros)
        constraint.C = [R1CS_term((var, 1))]
        mapping_index_var.append((len(r1cs.constraints), var - r1cs.io_size - r1cs.num_public_inputs))
        r1cs.constraints.append(constraint)
    io = [Field(0) for _ in range(r1cs.io_size)]
    for i in range(r1cs.scheme_length):
        for index, var in mapping_index_var:
            r1cs.witness[i * num_witness_variables + var] = calc_left(r1cs, index, i, io)
        cur_vars = io + r1cs.public_inputs[r1cs.num_public_inputs * i:r1cs.num_public_inputs * (i + 1)] + r1cs.witness[num_witness_variables * i:num_witness_variables * (i + 1)]
        io = cur_vars[len(cur_vars) - r1cs.io_size:len(cur_vars)]

    r1cs.num_constraints = len(r1cs.constraints)
    return r1cs

def create_for_new_vars_optimization(scheme_length=10, io_size=2, num_public_inputs=2, num_variables=30, num_constraints=15, k_not_zeros=10):
    r1cs = R1CS(None)
    r1cs.io_size = io_size
    r1cs.scheme_length = scheme_length
    r1cs.num_public_inputs = num_public_inputs
    r1cs.num_variables = num_variables
    r1cs.constraints = []

    num_witness_variables = r1cs.num_variables - r1cs.io_size - r1cs.num_public_inputs

    r1cs.public_inputs = [Field(1) if i % r1cs.num_public_inputs == 0 else rand_F() for i in range(r1cs.scheme_length * r1cs.num_public_inputs)]
    r1cs.witness = [rand_F() for _ in range(r1cs.scheme_length * num_witness_variables)]

    mapping_index_var = []
    for var in range(r1cs.num_variables - num_constraints, r1cs.num_variables):
        constraint = R1CS_constraint(None)
        constraint.A = random_part(r1cs, r1cs.num_variables - num_constraints - 1, k_not_zeros, only_01=True)
        constraint.B = random_part(r1cs, r1cs.num_variables - num_constraints - 1, k_not_zeros, only_01=True)
        constraint.C = [R1CS_term((var, 1))]
        mapping_index_var.append((len(r1cs.constraints), var - r1cs.io_size - r1cs.num_public_inputs))
        r1cs.constraints.append(constraint)
    io = [Field(0) for _ in range(r1cs.io_size)]
    for i in range(r1cs.scheme_length):
        for index, var in mapping_index_var:
            r1cs.witness[i * num_witness_variables + var] = calc_left(r1cs, index, i, io)
        cur_vars = io + r1cs.public_inputs[r1cs.num_public_inputs * i:r1cs.num_public_inputs * (i + 1)] + r1cs.witness[num_witness_variables * i:num_witness_variables * (i + 1)]
        io = cur_vars[len(cur_vars) - r1cs.io_size:len(cur_vars)]

    r1cs.num_constraints = len(r1cs.constraints)
    return r1cs


if __name__ == "__main__":
    #r1cs = create_with_extra_constraints()
    #r1cs = create_with_extra_variables()
    r1cs = create_for_new_vars_optimization()
    write_r1cs_to_file(r1cs, '../r1cs_json/4.json')
