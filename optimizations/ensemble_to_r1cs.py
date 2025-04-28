from r1cs_utils import write_r1cs_to_file
from ensemble_r1cs import EnsembleR1CS
import sys

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <source_ensemble_json_path> <target_single_r1cs_json_path>")
        sys.exit(1)
    r1cs_json = eval(open(sys.argv[1], 'r').read())
    ensemble = EnsembleR1CS(r1cs_json)
    r1cs = ensemble.to_single_r1cs()
    write_r1cs_to_file(r1cs, sys.argv[2])
