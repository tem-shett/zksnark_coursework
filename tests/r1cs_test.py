import subprocess
import sys
sys.path.append('../optimizations')
from optimizations.r1cs_creator import create_for_new_vars_optimization, create_with_extra_variables, create_with_extra_constraints
from optimizations.r1cs_utils import write_r1cs_to_file

def run_rust_program(json_path: str):
    result = subprocess.run(
        ["../target/debug/zksnark_coursework", json_path],
        capture_output=True,
        text=True
    )
    assert(result.returncode == 0)
    return result.stdout

def test_extra_constraints():
    r1cs = create_with_extra_constraints()
    write_r1cs_to_file(r1cs, '../r1cs_json/1.json')
    run_rust_program('../r1cs_json/1.json')
    old_time_estimation = r1cs.time_estimation()
    r1cs.reduce_constraints()
    new_time_estimation = r1cs.time_estimation()
    assert(old_time_estimation > new_time_estimation)
    write_r1cs_to_file(r1cs, '../r1cs_json/1_reduced.json')
    run_rust_program('../r1cs_json/1_reduced.json')

def test_extra_variables():
    r1cs = create_with_extra_variables()
    write_r1cs_to_file(r1cs, '../r1cs_json/2.json')
    run_rust_program('../r1cs_json/2.json')
    old_time_estimation = r1cs.time_estimation()
    r1cs.reduce_variables()
    new_time_estimation = r1cs.time_estimation()
    assert(old_time_estimation > new_time_estimation)
    write_r1cs_to_file(r1cs, '../r1cs_json/2_reduced.json')
    run_rust_program('../r1cs_json/2_reduced.json')

def test_new_vars_optimization():
    r1cs = create_for_new_vars_optimization()
    write_r1cs_to_file(r1cs, '../r1cs_json/3.json')
    run_rust_program('../r1cs_json/3.json')
    old_time_estimation = r1cs.time_estimation()
    r1cs.reduce_nonzero_coefficients()
    new_time_estimation = r1cs.time_estimation()
    assert(old_time_estimation > new_time_estimation)
    write_r1cs_to_file(r1cs, '../r1cs_json/3_reduced.json')
    run_rust_program('../r1cs_json/3_reduced.json')

if __name__ == "__main__":
    test_extra_constraints()
    test_extra_variables()
    test_new_vars_optimization()
