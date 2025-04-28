import subprocess
import sys
sys.path.append('../optimizations')
from optimizations.ensemble_creator import create_independent_ensemble, create_dependent_ensemble
from optimizations.r1cs_utils import write_r1cs_to_file

def run_rust_program(json_path: str):
    result = subprocess.run(
        ["../target/debug/zksnark_coursework", json_path],
        capture_output=True,
        text=True
    )
    assert(result.returncode == 0)
    return result.stdout


def test_independent_ensemble():
    ensemble = create_independent_ensemble()
    r1cs = ensemble.to_single_r1cs()
    write_r1cs_to_file(r1cs, '../r1cs_json/independent_ensemble.json')
    run_rust_program('../r1cs_json/independent_ensemble.json')


def test_dependent_ensemble():
    ensemble = create_dependent_ensemble()
    r1cs = ensemble.to_single_r1cs()
    write_r1cs_to_file(r1cs, '../r1cs_json/dependent_ensemble.json')
    run_rust_program('../r1cs_json/dependent_ensemble.json')


if __name__ == "__main__":
    test_independent_ensemble()
    test_dependent_ensemble()