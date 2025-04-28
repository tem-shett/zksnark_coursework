import json

def write_r1cs_to_file(r1cs, filename):
    with open(filename, 'w') as f:
        f.write(json.dumps(r1cs.to_json_format(), indent=2))
