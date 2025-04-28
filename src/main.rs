use core::marker::PhantomData;
use ff::{Field, PrimeField, PrimeFieldBits};
use flate2::{write::ZlibEncoder, Compression};
use nova_snark::{
    frontend::{
        num::AllocatedNum, AllocatedBit, ConstraintSystem, LinearCombination, SynthesisError,
    },
    nova::{CompressedSNARK, PublicParams, RecursiveSNARK},
    provider::{Bn256EngineKZG, GrumpkinEngine},
    traits::{circuit::StepCircuit, snark::RelaxedR1CSSNARKTrait, Engine, Group},
};
use rand::Rng;
use std::time::Instant;
use std::{env, fs};
use serde::Deserialize;

type E1 = Bn256EngineKZG;
type E2 = GrumpkinEngine;
type EE1 = nova_snark::provider::hyperkzg::EvaluationEngine<E1>;
type EE2 = nova_snark::provider::ipa_pc::EvaluationEngine<E2>;
type S1 = nova_snark::spartan::snark::RelaxedR1CSSNARK<E1, EE1>;
type S2 = nova_snark::spartan::snark::RelaxedR1CSSNARK<E2, EE2>;

#[derive(Deserialize)]
struct Term {
    variable: usize,
    coefficient: String,
}

#[derive(Deserialize)]
struct Constraint {
    A: Vec<Term>,
    B: Vec<Term>,
    C: Vec<Term>,
}

#[derive(Deserialize)]
struct R1CSJson {
    num_variables: usize,
    num_public_inputs: usize,
    num_constraints: usize,
    io_size: usize,
    scheme_length: usize,
    constraints: Vec<Constraint>,
    public_inputs: Vec<String>,
    witness: Vec<String>
}

#[derive(Clone)]
struct R1CSTerm<Scalar> {
    variable: usize,
    coefficient: Scalar,
}

#[derive(Clone)]
struct R1CSConstraint<Scalar: PrimeField> {
    A: Vec<R1CSTerm<Scalar>>,
    B: Vec<R1CSTerm<Scalar>>,
    C: Vec<R1CSTerm<Scalar>>,
}

#[derive(Clone)]
struct R1CS<Scalar: PrimeField> {
    num_variables: usize,
    num_public_inputs: usize,
    io_size: usize,
    scheme_length: usize,
    constraints: Vec<R1CSConstraint<Scalar>>,
    public_inputs: Vec<Scalar>,
    witness: Vec<Scalar>,
}

fn from_json_to_r1cs<Scalar: PrimeField>(r1cs_json: R1CSJson) -> R1CS<Scalar> {
    let constraints = r1cs_json.constraints.into_iter().map(|constr| {
        let convert = |terms: Vec<Term>| {
            terms.into_iter()
                .map(|t| R1CSTerm{
                    variable: t.variable,
                    coefficient: Scalar::from_str_vartime(&t.coefficient).unwrap()
                })
                .collect::<Vec<_>>()
        };
        R1CSConstraint {
            A: convert(constr.A),
            B: convert(constr.B),
            C: convert(constr.C),
        }
    }).collect::<Vec<_>>();

    let public_inputs = r1cs_json.public_inputs
        .into_iter()
        .map(|s| Scalar::from_str_vartime(&s).unwrap())
        .collect();
    let witness = r1cs_json.witness
        .into_iter()
        .map(|s| Scalar::from_str_vartime(&s).unwrap())
        .collect();
    R1CS {
        num_variables: r1cs_json.num_variables,
        num_public_inputs: r1cs_json.num_public_inputs,
        io_size: r1cs_json.io_size,
        scheme_length: r1cs_json.scheme_length,
        constraints,
        public_inputs,
        witness,
    }
}

#[derive(Clone)]
struct R1CSAdapter<G: Group> {
    r1cs: R1CS<G::Scalar>,
}

impl<G: Group> StepCircuit<G::Scalar> for R1CSAdapter<G>
where
{
    fn arity(&self) -> usize {
        self.r1cs.io_size
    }

    fn synthesize<CS: ConstraintSystem<G::Scalar>>(
        &self,
        cs: &mut CS,
        z_in: &[AllocatedNum<G::Scalar>],
    ) -> Result<Vec<AllocatedNum<G::Scalar>>, SynthesisError> {
        let mut allocated_vars = Vec::with_capacity(self.r1cs.num_variables);
        for i in 0..self.r1cs.num_variables {
            let var = if i < self.r1cs.io_size {
                z_in[i].clone()
            } else if i < self.r1cs.num_public_inputs + self.r1cs.io_size {
                AllocatedNum::alloc(cs.namespace(|| format!("input_{}", i)), || {
                    Ok(self.r1cs.public_inputs[i - self.r1cs.io_size].clone())
                })?
            } else {
                AllocatedNum::alloc(cs.namespace(|| format!("witness_{}", i)), || {
                    Ok(self.r1cs.witness[i - self.r1cs.io_size - self.r1cs.num_public_inputs].clone())
                })?
            };
            allocated_vars.push(var);
        }

        for (constr_idx, constraint) in self.r1cs.constraints.iter().enumerate() {

            let mut lc_a = LinearCombination::zero();
            for term in &constraint.A {
                lc_a = lc_a + (term.coefficient.clone(), allocated_vars[term.variable].get_variable());
            }

            let mut lc_b = LinearCombination::zero();
            for term in &constraint.B {
                lc_b = lc_b + (term.coefficient.clone(), allocated_vars[term.variable].get_variable());
            }

            let mut lc_c = LinearCombination::zero();
            for term in &constraint.C {
                lc_c = lc_c + (term.coefficient.clone(), allocated_vars[term.variable].get_variable());
            }

            cs.enforce(
                || format!("r1cs constraint {}", constr_idx),
                |_| lc_a.clone(),
                |_| lc_b.clone(),
                |_| lc_c.clone(),
            );
        }

        Ok(allocated_vars[allocated_vars.len() - self.r1cs.io_size..].to_vec())
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        eprintln!("Usage: {} <path_to_json>", args[0]);
        std::process::exit(1);
    }
    
    // let r1cs_json_string = fs::read_to_string("r1cs_json/0.json").unwrap();
    let r1cs_json_string = fs::read_to_string(&args[1]).unwrap();
    let r1cs_json_object: R1CSJson = serde_json::from_str(&r1cs_json_string).unwrap();
    let r1cs: R1CS<<E1 as Engine>::Scalar> = from_json_to_r1cs(r1cs_json_object);
    let r1cs_adapter = R1CSAdapter{ r1cs };

    type C = R1CSAdapter<<E1 as Engine>::GE>;

    let pp = PublicParams::<E1, E2, C>::setup(
        &r1cs_adapter,
        &*S1::ck_floor(),
        &*S2::ck_floor(),
    ).unwrap();

    let mut recursive_snark: RecursiveSNARK<E1, E2, C> =
        RecursiveSNARK::<E1, E2, C>::new(&pp, &r1cs_adapter, &vec![<E1 as Engine>::Scalar::zero(); r1cs_adapter.r1cs.io_size])
            .unwrap();

    let witness_inputs = &r1cs_adapter.r1cs.num_variables - &r1cs_adapter.r1cs.num_public_inputs - &r1cs_adapter.r1cs.io_size;
    let public_inputs = &r1cs_adapter.r1cs.num_public_inputs;
    let circuits = (0..r1cs_adapter.r1cs.scheme_length)
        .map(|i| {
            let mut cur_adapter = r1cs_adapter.clone();
            let witness_start_index = i * witness_inputs;
            let witness_end_index = (i + 1) * witness_inputs;
            let public_start_index = i * public_inputs;
            let public_end_index = (i + 1) * public_inputs;
            if witness_end_index > cur_adapter.r1cs.witness.len() {
                panic!("Insufficient witness entries for iteration {}", i);
            }
            if public_end_index > cur_adapter.r1cs.public_inputs.len() {
                panic!("Insufficient public inputs entries for iteration {}", i);
            }
            cur_adapter.r1cs.witness = cur_adapter.r1cs.witness[witness_start_index..witness_end_index]
                .to_vec();
            cur_adapter.r1cs.public_inputs = cur_adapter.r1cs.public_inputs[public_start_index..public_end_index]
                .to_vec();
            cur_adapter
        })
        .collect::<Vec<_>>();

    let start_t_prover = Instant::now();

    for circuit in circuits.iter() {
        let res = recursive_snark.prove_step(&pp, circuit);
        assert!(res.is_ok());
    }

    println!(
        "Prover time: {:?}",
        start_t_prover.elapsed()
    );

    let start_t_verifier = Instant::now();

    let res = recursive_snark.verify(&pp, r1cs_adapter.r1cs.scheme_length, &vec![<E1 as Engine>::Scalar::ZERO; r1cs_adapter.r1cs.io_size]);

    assert!(res.is_ok());

    println!(
        "Verifier time: {:?}",
        start_t_verifier.elapsed()
    );
}
