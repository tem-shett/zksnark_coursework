from r1cs_utils import write_r1cs_to_file
from single_r1cs import R1CS
import sys

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <source_json_path> <target_json_path>")
        sys.exit(1)
    r1cs_json = eval(open(sys.argv[1], 'r').read())
    r1cs = R1CS(r1cs_json)
    old_time_estimation = r1cs.time_estimation()
    r1cs.full_optimize()
    new_time_estimation = r1cs.time_estimation()
    print(f'Difficulty estimation: {old_time_estimation}->{new_time_estimation}')
    write_r1cs_to_file(r1cs, sys.argv[2])
