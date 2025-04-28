from linear_algebra import check_vector_in_hull
from field_class import Field
from r1cs_utils import write_r1cs_to_file
from copy import deepcopy
from math import log2, ceil

def get_r1cs_statistics(r1cs):
    variables = r1cs['num_variables']
    constraints = len(r1cs['constraints'])
    nonzero_items = sum([sum([len(part) for part in constraint.values()]) for constraint in r1cs['constraints']])
    return {'variables': variables, 'constraints': constraints, 'nonzero_items': nonzero_items}

class R1CS_term:
    def __init__(self, term):
        if type(term) == dict:
            self.variable = term['variable']
            self.coefficient = Field(term['coefficient'])
        else:
            self.variable = term[0]
            self.coefficient = term[1] if type(term[1]) == Field else Field(term[1])

    def to_json_format(self):
        return {"variable": self.variable, "coefficient": str(self.coefficient.x)}

class R1CS_constraint:
    def __init__(self, constraint):
        if constraint is None:
            self.A = None
            self.B = None
            self.C = None
            return
        self.A = [R1CS_term(term) for term in constraint['A']]
        self.B = [R1CS_term(term) for term in constraint['B']]
        self.C = [R1CS_term(term) for term in constraint['C']]

    def size(self):
        return len(self.A) + len(self.B) + len(self.C)

    def to_json_format(self):
        return {'A': [term.to_json_format() for term in self.A],
                'B': [term.to_json_format() for term in self.B],
                'C': [term.to_json_format() for term in self.C]}

class R1CS:
    def __init__(self, r1cs_json):
        if r1cs_json is None:
            self.num_variables = None
            self.num_public_inputs = None
            self.num_constraints = None
            self.io_size = None
            self.scheme_length = None
            self.constraints = None
            self.public_inputs = None
            self.witness = None
            self.mapping = None
            return
        self.num_variables = r1cs_json['num_variables']
        self.num_public_inputs = r1cs_json['num_public_inputs']
        self.num_constraints = r1cs_json['num_constraints']
        self.io_size = r1cs_json['io_size']
        self.scheme_length = r1cs_json['scheme_length']
        self.constraints = [R1CS_constraint(constraint) for constraint in r1cs_json['constraints']]
        self.public_inputs = [Field(el) for el in r1cs_json['public_inputs']]
        for i in range(self.scheme_length):
            assert(self.public_inputs[i * self.num_public_inputs] == 1)
        self.witness = [Field(el) for el in r1cs_json['witness']]
        self.mapping = None

    def __is_variable_1(self, variable):
        return variable == self.io_size

    def __is_constraint_part_1(self, part: list[R1CS_term]):
        return len(part) == 1 and self.__is_variable_1(part[0].variable)

    def __is_hidden_variable(self, variable):
        return self.io_size + self.num_public_inputs <= variable < self.num_variables - self.io_size

    def __nonzero_coefs(self):
        return sum([sum([len(part) for part in [constraint.A, constraint.B, constraint.C]]) for constraint in self.constraints])

    def time_estimation(self):
        return self.__nonzero_coefs() + self.num_constraints * ceil(log2(self.num_constraints))

    def to_json_format(self):
        return {
            'num_variables': self.num_variables,
            'num_public_inputs': self.num_public_inputs,
            'num_constraints': self.num_constraints,
            'io_size': self.io_size,
            'scheme_length': self.scheme_length,
            'constraints': [constraint.to_json_format() for constraint in self.constraints],
            'public_inputs': [str(el.x) for el in self.public_inputs],
            'witness': [str(el.x) for el in self.witness]
        }

    def __create_mapping(self):
        next_ind = self.num_variables
        self.mapping = [[0] * self.num_variables for _ in range(self.num_variables)]
        for i in range(self.num_variables):
            for j in range(i, self.num_variables):
                self.mapping[i][j] = self.mapping[j][i] = next_ind
                next_ind += 1

    def __constraint_to_vector(self, constraint: R1CS_constraint):
        if self.mapping is None:
            self.__create_mapping()
        vector = [Field(0)] * (self.num_variables + self.num_variables * (self.num_variables + 1) // 2)
        for term1 in constraint.A:
            for term2 in constraint.B:
                if self.__is_variable_1(term1.variable):
                    vector[term2.variable] += term1.coefficient * term2.coefficient
                elif self.__is_variable_1(term2.variable):
                    vector[term1.variable] += term1.coefficient * term2.coefficient
                else:
                    vector[self.mapping[term1.variable][term2.variable]] += term1.coefficient * term2.coefficient
        for term3 in constraint.C:
            vector[term3.variable] -= term3.coefficient
        return vector

    def __check_constraint_necessity(self, constraint_ind):
        assert(0 <= constraint_ind < len(self.constraints))
        if len(self.constraints) == 1:
            return True
        set_of_constraints = self.constraints[:constraint_ind] + self.constraints[constraint_ind + 1:]
        constraint_for_check = self.constraints[constraint_ind]
        vectors = [self.__constraint_to_vector(constraint) for constraint in set_of_constraints]
        vector_for_check = self.__constraint_to_vector(constraint_for_check)
        return not check_vector_in_hull(vectors, vector_for_check)

    def __delete_constraint(self, constraint_ind):
        self.constraints = self.constraints[:constraint_ind] + self.constraints[constraint_ind + 1:]
        self.num_constraints = len(self.constraints)

    def constraint_part_to_vector(self, constraint_part: list[R1CS_term]):
        vector = [Field(0)] * self.num_variables
        for term in constraint_part:
            vector[term.variable] += term.coefficient
        return vector

    def vector_to_constraint_part(self, vector):
        assert(len(vector) == self.num_variables)
        part = []
        for var in range(self.num_variables):
            if vector[var] != 0:
                part.append(R1CS_term((var, vector[var])))
        return part

    def __substitute_in_constraint_part(self, part: list[R1CS_term], variable, lc):
        vector = [Field(0)] * self.num_variables
        for term in part:
            if term.variable == variable:
                for j in range(self.num_variables):
                    vector[j] += lc[j] * term.coefficient
            else:
                vector[term.variable] += term.coefficient
        return self.vector_to_constraint_part(vector)

    def __substitute(self, variable, lc):
        r1cs_copy = deepcopy(self)
        for i in range(len(r1cs_copy.constraints)):
            r1cs_copy.constraints[i].A = r1cs_copy.__substitute_in_constraint_part(r1cs_copy.constraints[i].A, variable, lc)
            r1cs_copy.constraints[i].B = r1cs_copy.__substitute_in_constraint_part(r1cs_copy.constraints[i].B, variable, lc)
            r1cs_copy.constraints[i].C = r1cs_copy.__substitute_in_constraint_part(r1cs_copy.constraints[i].C, variable, lc)
        # r1cs_copy.reduce_constraints()
        return r1cs_copy

    def __delete_unused_hidden_variables(self):
        cnt_vars_used = [0] * self.num_variables
        for constraint in self.constraints:
            for part in [constraint.A, constraint.B, constraint.C]:
                for term in part:
                    cnt_vars_used[term.variable] += 1

        next_var = 0
        mapping_old_vars_to_new_vars = [-1] * self.num_variables
        for var in range(self.num_variables):
            if cnt_vars_used[var] == 0 and self.__is_hidden_variable(var):
                pass
            else:
                mapping_old_vars_to_new_vars[var] = next_var
                next_var += 1

        new_witness = []
        for i in range(len(self.witness)):
            var = i % (self.num_variables - self.io_size - self.num_public_inputs) + self.io_size + self.num_public_inputs
            if mapping_old_vars_to_new_vars[var] != -1:
                new_witness.append(self.witness[i])
        self.witness = new_witness

        for constraint in self.constraints:
            for part in [constraint.A, constraint.B, constraint.C]:
                for term in part:
                    term.variable = mapping_old_vars_to_new_vars[term.variable]
        self.num_variables = next_var

        self.__create_mapping()

    def __reduce_variables_step(self):
        linear_combination: list[None | list] = [None] * self.num_variables
        constraint_index_for_lc = [-1] * self.num_variables
        for i in range(len(self.constraints)):
            if self.__is_constraint_part_1(self.constraints[i].A) or self.__is_constraint_part_1(self.constraints[i].B):
                lc = self.__constraint_to_vector(self.constraints[i])[:self.num_variables]
                for var in range(self.num_variables):
                    if lc[var] != 0:
                        constraint_index_for_lc[var] = i
                        linear_combination[var] = lc.copy()
                        coef = -Field(1) / lc[var]
                        linear_combination[var][var] = Field(0)
                        for j in range(self.num_variables):
                            linear_combination[var][j] *= coef

        possible_r1cs = [(deepcopy(self), -1)]
        for var in range(self.num_variables):
            if self.__is_hidden_variable(var) and linear_combination[var] is not None:
                r1cs_subst = self.__substitute(var, linear_combination[var])
                r1cs_subst.__delete_constraint(constraint_index_for_lc[var])
                possible_r1cs.append((r1cs_subst, var))
        best_r1cs, var = min(possible_r1cs, key=lambda x: x[0].time_estimation())
        self.__dict__.update(best_r1cs.__dict__)
        return var != -1

    def __calc_zeros_new_variable_in_constraint_part(self, part_vec: list[Field], w: list[Field]):
        cnt_r = dict()
        zeros_not_in_w = 0
        for j in range(self.num_variables):
            if w[j] != 0:
                r = part_vec[j] / w[j]
                cnt_r[r.x] = cnt_r.get(r.x, 0) + 1
            elif part_vec[j] == 0:
                zeros_not_in_w += 1
        for r in cnt_r:
            if r != 0:
                cnt_r[r] -= 1
        return (max([val for val in cnt_r.values()]) if len(cnt_r) > 0 else 0) + zeros_not_in_w

    def __update_constraint_part_with_new_var(self, part: list[R1CS_term], w: list[Field], new_var: int):
        part_vec = self.constraint_part_to_vector(part)
        cnt_r = dict()
        for j in range(self.num_variables):
            if w[j] != 0:
                r = part_vec[j] / w[j]
                cnt_r[r.x] = cnt_r.get(r.x, 0) + 1
        for r in cnt_r:
            if r != 0:
                cnt_r[r] -= 1
        r = 0 if len(cnt_r) == 0 else max([(cnt_r[r], r) for r in cnt_r])[1]
        for j in range(self.num_variables):
            part_vec[j] -= r * w[j]
        part_vec[new_var] += r
        return self.vector_to_constraint_part(part_vec)

    def __create_new_variable(self):
        var = self.num_variables - self.io_size - 1
        for constraint in self.constraints:
            for part in [constraint.A, constraint.B, constraint.C]:
                for term in part:
                    if term.variable >= var:
                        term.variable += 1
        new_witness = []
        witness_vars_num = self.num_variables - self.num_public_inputs - self.io_size
        for i in range(len(self.witness)):
            if i % witness_vars_num == var - self.num_public_inputs - self.io_size:
                new_witness.append(Field(0))
            new_witness.append(self.witness[i])
        self.witness = new_witness
        self.num_variables += 1
        return var

    def __reduce_nonzero_coefficients_step(self):
        all_parts = []
        for constraint in self.constraints:
            for part in [constraint.A, constraint.B, constraint.C]:
                all_parts.append(self.constraint_part_to_vector(part))

        w = [Field(0) for _ in range(self.num_variables)]

        is_first = True
        while True:
            possib_vals = [set() for _ in range(self.num_variables)]
            for var in range(self.num_variables):
                if w[var] != 0:
                    continue
                possib_vals[var].add(1)
                for part in all_parts:
                    if part[var] == 0:
                        continue
                    for j in range(self.num_variables):
                        if w[j] != 0 and part[j] != 0:
                            possib_vals[var].add((w[j] * part[var] / part[j]).x)
            possib = []
            for var in range(self.num_variables):
                for r in possib_vals[var]:
                    possib.append((var, r))
            best = None
            best_delta = 0
            for var, c in possib:
                new_w = w.copy()
                new_w[var] = c
                delta = 0
                for part in all_parts:
                    delta += self.__calc_zeros_new_variable_in_constraint_part(part, new_w) - self.__calc_zeros_new_variable_in_constraint_part(part, w)
                if not is_first:
                    delta -= 1
                if best_delta < delta or (delta == best_delta and best is None):
                    best_delta = delta
                    best = (var, c)
            if best is None:
                break
            w[best[0]] = best[1]
            is_first = False

        new_r1cs = deepcopy(self)
        new_var = new_r1cs.__create_new_variable()
        w = w[:new_var] + [Field(0)] + w[new_var:]

        new_constraint = R1CS_constraint(None)
        new_constraint.A = [R1CS_term((new_r1cs.io_size, 1))]
        new_constraint.B = new_r1cs.vector_to_constraint_part(w)
        new_constraint.C = [R1CS_term((new_var, 1))]

        for i in range(new_r1cs.scheme_length):
            witness_vars_nums = new_r1cs.num_variables - new_r1cs.num_public_inputs - new_r1cs.io_size
            vals = new_r1cs.public_inputs[i*self.num_public_inputs:(i+1)*self.num_public_inputs] + new_r1cs.witness[i*witness_vars_nums:(i+1)*witness_vars_nums]
            if i == 0:
                vals = [Field(0) for _ in range(new_r1cs.io_size)] + vals
            else:
                vals = new_r1cs.witness[i*witness_vars_nums-new_r1cs.io_size:i*witness_vars_nums] + vals
            new_var_val = 0
            for j in range(new_r1cs.num_variables):
                new_var_val += w[j] * vals[j]
            new_r1cs.witness[i*witness_vars_nums+new_var-new_r1cs.num_public_inputs-new_r1cs.io_size] = new_var_val

        for constraint in new_r1cs.constraints:
            constraint.A = new_r1cs.__update_constraint_part_with_new_var(constraint.A, w, new_var)
            constraint.B = new_r1cs.__update_constraint_part_with_new_var(constraint.B, w, new_var)
            constraint.C = new_r1cs.__update_constraint_part_with_new_var(constraint.C, w, new_var)

        new_r1cs.constraints.append(new_constraint)
        new_r1cs.num_constraints = len(new_r1cs.constraints)
        if self.time_estimation() > new_r1cs.time_estimation():
            self.__dict__.update(new_r1cs.__dict__)
            return True
        return False

    def reduce_constraints(self):
        while True:
            constraints_for_del = []
            for ind in range(len(self.constraints)):
                if not self.__check_constraint_necessity(ind):
                    constraints_for_del.append((self.constraints[ind].size(), ind))
            if len(constraints_for_del) == 0:
                break
            constraints_for_del.sort(reverse=True)
            self.__delete_constraint(constraints_for_del[0][1])

    def reduce_variables(self):
        while self.__reduce_variables_step():
            self.__delete_unused_hidden_variables()
            self.reduce_constraints()

    def reduce_nonzero_coefficients(self):
        while self.__reduce_nonzero_coefficients_step():
            continue

    def full_optimize(self):
        self.reduce_constraints()
        self.reduce_variables()
        self.reduce_nonzero_coefficients()

if __name__ == "__main__":
    r1cs_json = eval(open('../r1cs_json/4.json', 'r').read())
    r1cs = R1CS(r1cs_json)
    print('Time estimation before optimization:', r1cs.time_estimation())
    #r1cs.reduce_constraints()
    #r1cs.reduce_variables()
    r1cs.reduce_nonzero_coefficients()
    print('Time estimation after optimization', r1cs.time_estimation())
    write_r1cs_to_file(r1cs, '../r1cs_json/0.json')
