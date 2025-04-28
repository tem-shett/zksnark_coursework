from single_r1cs import R1CS
from copy import deepcopy


class EnsembleR1CS:
    def __init__(self, ensemble_json):
        if ensemble_json is None:
            self.r1cs_list = None
            return
        assert (type(ensemble_json) == list)
        self.r1cs_list = [R1CS(r1cs_json) for r1cs_json in ensemble_json]
        for r1cs in self.r1cs_list:
            assert (r1cs.num_variables - r1cs.io_size - r1cs.num_public_inputs >= r1cs.io_size)
        assert (min([r1cs.scheme_length for r1cs in self.r1cs_list]) == max(
            [r1cs.scheme_length for r1cs in self.r1cs_list]))

    def to_json_format(self):
        return [r1cs.to_json_format() for r1cs in self.r1cs_list]

    def to_single_r1cs(self):
        large_r1cs = R1CS(None)
        large_r1cs.num_variables = sum([r1cs.num_variables for r1cs in self.r1cs_list])
        large_r1cs.io_size = sum([r1cs.io_size for r1cs in self.r1cs_list])
        large_r1cs.num_public_inputs = sum([r1cs.num_public_inputs for r1cs in self.r1cs_list])
        large_r1cs.scheme_length = self.r1cs_list[0].scheme_length

        vars_mapping = dict()
        next_var = 0
        for r1cs_ind in range(len(self.r1cs_list)):
            r1cs = self.r1cs_list[r1cs_ind]
            for i in range(r1cs.io_size):
                vars_mapping[(r1cs_ind, i)] = next_var
                next_var += 1
        for r1cs_ind in range(len(self.r1cs_list)):
            r1cs = self.r1cs_list[r1cs_ind]
            for i in range(r1cs.io_size, r1cs.io_size + r1cs.num_public_inputs):
                vars_mapping[(r1cs_ind, i)] = next_var
                next_var += 1
        for r1cs_ind in range(len(self.r1cs_list)):
            r1cs = self.r1cs_list[r1cs_ind]
            for i in range(r1cs.io_size + r1cs.num_public_inputs, r1cs.num_variables - r1cs.io_size):
                vars_mapping[(r1cs_ind, i)] = next_var
                next_var += 1
        for r1cs_ind in range(len(self.r1cs_list)):
            r1cs = self.r1cs_list[r1cs_ind]
            for i in range(r1cs.num_variables - r1cs.io_size, r1cs.num_variables):
                vars_mapping[(r1cs_ind, i)] = next_var
                next_var += 1

        assert (next_var == large_r1cs.num_variables)

        large_r1cs.constraints = []
        for r1cs_ind in range(len(self.r1cs_list)):
            r1cs = self.r1cs_list[r1cs_ind]
            for constraint in r1cs.constraints:
                new_constraint = deepcopy(constraint)
                for part in [new_constraint.A, new_constraint.B, new_constraint.C]:
                    for term in part:
                        system_index = r1cs_ind if type(term.variable) == int else term.variable[0]
                        var = term.variable if type(term.variable) == int else term.variable[1]
                        term.variable = vars_mapping[(system_index, var)]
                large_r1cs.constraints.append(new_constraint)
        large_r1cs.num_constraints = len(large_r1cs.constraints)

        num_witness_vars = large_r1cs.num_variables - large_r1cs.io_size - large_r1cs.num_public_inputs

        large_r1cs.public_inputs = [None for _ in range(large_r1cs.num_public_inputs * large_r1cs.scheme_length)]
        large_r1cs.witness = [None for _ in range(num_witness_vars * large_r1cs.scheme_length)]

        for iteration in range(large_r1cs.scheme_length):
            for r1cs_index in range(len(self.r1cs_list)):
                r1cs = self.r1cs_list[r1cs_index]
                for var in range(r1cs.num_variables):
                    if var < r1cs.io_size:
                        pass
                    elif var < r1cs.io_size + r1cs.num_public_inputs:
                        large_r1cs.public_inputs[large_r1cs.num_public_inputs * iteration + vars_mapping[
                            (r1cs_index, var)] - large_r1cs.io_size] = r1cs.public_inputs[
                            iteration * r1cs.num_public_inputs + var - r1cs.io_size]
                    else:
                        cur_witness_vars_num = r1cs.num_variables - r1cs.io_size - r1cs.num_public_inputs
                        large_r1cs.witness[num_witness_vars * iteration + vars_mapping[
                            (r1cs_index, var)] - large_r1cs.io_size - large_r1cs.num_public_inputs] = r1cs.witness[
                            iteration * cur_witness_vars_num + var - r1cs.io_size - r1cs.num_public_inputs]

        for el in large_r1cs.witness:
            assert (el is not None)
        for el in large_r1cs.public_inputs:
            assert (el is not None)

        return large_r1cs
