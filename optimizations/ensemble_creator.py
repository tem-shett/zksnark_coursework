import random

from field_class import Field
from consts import MOD
from single_r1cs import R1CS, R1CS_constraint, R1CS_term
from r1cs_utils import write_r1cs_to_file
from r1cs_creator import *
from ensemble_r1cs import EnsembleR1CS
from random import randint

def create_independent_ensemble():
    r1cs_1 = create_for_new_vars_optimization()
    r1cs_2 = create_with_extra_constraints()
    r1cs_3 = create_with_extra_variables()

    ensemble = EnsembleR1CS(None)
    ensemble.r1cs_list = [r1cs_1, r1cs_2, r1cs_3]
    return ensemble

def random_part_ensemble(r1cs_1: R1CS, r1cs: R1CS, max_var_num=None, k_not_zeros=None, only_01=False):
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
    part = r1cs.vector_to_constraint_part(random_vector)
    for term in part:
        if randint(0, 1) == 0:
            term.variable = (0, min(max(term.variable, r1cs_1.io_size), r1cs_1.num_variables - 1))
    return part

def calc_left_ensemble(r1cs_1, r1cs: R1CS, constraint_ind, iter, io):
    num_witness_variables = r1cs.num_variables - r1cs.io_size - r1cs.num_public_inputs
    cur_vars = io + r1cs.public_inputs[r1cs.num_public_inputs * iter:r1cs.num_public_inputs * (iter + 1)] + r1cs.witness[num_witness_variables * iter:num_witness_variables * (iter + 1)]
    num_witness_variables_1 = r1cs_1.num_variables - r1cs_1.io_size - r1cs_1.num_public_inputs
    cur_vars_1 = io + r1cs_1.public_inputs[r1cs_1.num_public_inputs * iter:r1cs_1.num_public_inputs * (iter + 1)] + r1cs_1.witness[num_witness_variables_1 * iter:num_witness_variables_1 * (iter + 1)]

    calc_A = sum([(cur_vars[term.variable] if type(term.variable) == int else cur_vars_1[term.variable[1]]) * term.coefficient for term in r1cs.constraints[constraint_ind].A])
    calc_B = sum([(cur_vars[term.variable] if type(term.variable) == int else cur_vars_1[term.variable[1]]) * term.coefficient for term in r1cs.constraints[constraint_ind].B])
    return calc_A * calc_B

def create_dependent_ensemble():
    r1cs_1 = create_with_extra_variables(num_variables=20, num_vital_constraints=5, num_additional_constraints=3)

    r1cs = R1CS(None)
    r1cs.io_size = 2
    r1cs.scheme_length = 10
    r1cs.num_public_inputs = 2
    r1cs.num_variables = 20
    r1cs.constraints = []

    num_witness_variables = r1cs.num_variables - r1cs.io_size - r1cs.num_public_inputs

    r1cs.public_inputs = [Field(1) if i % r1cs.num_public_inputs == 0 else rand_F() for i in range(r1cs.scheme_length * r1cs.num_public_inputs)]
    r1cs.witness = [rand_F() for _ in range(r1cs.scheme_length * num_witness_variables)]

    mapping_index_var = []
    for var in range(r1cs.num_variables - 10, r1cs.num_variables):
        constraint = R1CS_constraint(None)
        constraint.A = random_part_ensemble(r1cs_1, r1cs, var - 1, 5)
        constraint.B = random_part_ensemble(r1cs_1, r1cs, var - 1, 5)
        constraint.C = [R1CS_term((var, 1))]
        mapping_index_var.append((len(r1cs.constraints), var - r1cs.io_size - r1cs.num_public_inputs))
        r1cs.constraints.append(constraint)
    io = [Field(0) for _ in range(r1cs.io_size)]
    for i in range(r1cs.scheme_length):
        for index, var in mapping_index_var:
            r1cs.witness[i * num_witness_variables + var] = calc_left_ensemble(r1cs_1, r1cs, index, i, io)
        cur_vars = io + r1cs.public_inputs[r1cs.num_public_inputs * i:r1cs.num_public_inputs * (i + 1)] + r1cs.witness[num_witness_variables * i:num_witness_variables * (i + 1)]
        io = cur_vars[len(cur_vars) - r1cs.io_size:len(cur_vars)]

    r1cs.num_constraints = len(r1cs.constraints)

    ensemble = EnsembleR1CS(None)
    ensemble.r1cs_list = [r1cs_1, r1cs]
    return ensemble


if __name__ == "__main__":
    ensemble = create_dependent_ensemble()
    write_r1cs_to_file(ensemble, '../r1cs_json/4.json')
