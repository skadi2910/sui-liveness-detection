#[test_only]
module proof_of_human::proof_of_human_tests;

use proof_of_human::proof_of_human::{Self, ProofOfHuman, ProofRegistry, VerifierCap};
use sui::test_scenario;

const ADMIN: address = @0xA;
const OWNER: address = @0xB;
const OWNER_TWO: address = @0xC;

fun walrus_blob_id(): vector<u8> {
    b"walrus_blob_001"
}

fun seal_identity(): vector<u8> {
    b"seal_identity_001"
}

fun model_hash(): vector<u8> {
    b"model_hash_v1"
}

fun challenge_type(): vector<u8> {
    b"smile"
}

fun blob_object_id(addr: address): object::ID {
    object::id_from_address(addr)
}

fun mint_default_proof(
    registry: &mut ProofRegistry,
    cap: &VerifierCap,
    owner: address,
    issued_at_ms: u64,
    expires_at_ms: u64,
    ctx: &mut sui::tx_context::TxContext,
) {
    proof_of_human::verify_and_mint(
        registry,
        cap,
        owner,
        walrus_blob_id(),
        blob_object_id(@0x111),
        seal_identity(),
        1,
        model_hash(),
        7_500,
        issued_at_ms,
        expires_at_ms,
        challenge_type(),
        ctx,
    )
}

#[test]
fun test_verify_and_mint_and_has_valid_proof() {
    let mut scenario_val = test_scenario::begin(ADMIN);
    let scenario = &mut scenario_val;
    {
        proof_of_human::init_for_testing(test_scenario::ctx(scenario));
    };

    test_scenario::next_tx(scenario, ADMIN);
    {
        let mut registry = test_scenario::take_shared<ProofRegistry>(scenario);
        let cap = test_scenario::take_from_sender<VerifierCap>(scenario);

        mint_default_proof(&mut registry, &cap, OWNER, 100, 1_000, test_scenario::ctx(scenario));

        assert!(proof_of_human::has_valid_proof(&registry, OWNER, 500), 0);
        assert!(proof_of_human::proofs_issued(&registry) == 1, 1);

        test_scenario::return_shared(registry);
        test_scenario::return_to_sender(scenario, cap);
    };

    test_scenario::next_tx(scenario, OWNER);
    {
        let proof = test_scenario::take_from_sender<ProofOfHuman>(scenario);
        let details = proof_of_human::get_proof_details(&proof);
        assert!(proof_of_human::proof_details_owner(&details) == OWNER, 2);
        assert!(proof_of_human::proof_details_confidence_bps(&details) == 7_500, 3);
        assert!(proof_of_human::proof_details_evidence_schema_version(&details) == 1, 4);
        assert!(proof_of_human::proof_details_challenge_type(&details) == challenge_type(), 5);
        test_scenario::return_to_sender(scenario, proof);
    };

    test_scenario::end(scenario_val);
}

#[test, expected_failure(abort_code = ::proof_of_human::proof_of_human::E_ACTIVE_PROOF_EXISTS)]
fun test_verify_and_mint_rejects_duplicate_active_proof() {
    let mut scenario_val = test_scenario::begin(ADMIN);
    let scenario = &mut scenario_val;
    {
        proof_of_human::init_for_testing(test_scenario::ctx(scenario));
    };

    test_scenario::next_tx(scenario, ADMIN);
    {
        let mut registry = test_scenario::take_shared<ProofRegistry>(scenario);
        let cap = test_scenario::take_from_sender<VerifierCap>(scenario);

        mint_default_proof(&mut registry, &cap, OWNER, 100, 1_000, test_scenario::ctx(scenario));
        mint_default_proof(&mut registry, &cap, OWNER, 200, 1_200, test_scenario::ctx(scenario));

        test_scenario::return_shared(registry);
        test_scenario::return_to_sender(scenario, cap);
    };

    test_scenario::end(scenario_val);
}

#[test]
fun test_renew_updates_same_lineage() {
    let mut scenario_val = test_scenario::begin(ADMIN);
    let scenario = &mut scenario_val;
    {
        proof_of_human::init_for_testing(test_scenario::ctx(scenario));
    };

    test_scenario::next_tx(scenario, ADMIN);
    {
        let mut registry = test_scenario::take_shared<ProofRegistry>(scenario);
        let cap = test_scenario::take_from_sender<VerifierCap>(scenario);

        mint_default_proof(&mut registry, &cap, ADMIN, 100, 1_000, test_scenario::ctx(scenario));

        test_scenario::return_shared(registry);
        test_scenario::return_to_sender(scenario, cap);
    };

    test_scenario::next_tx(scenario, ADMIN);
    {
        let mut registry = test_scenario::take_shared<ProofRegistry>(scenario);
        let cap = test_scenario::take_from_sender<VerifierCap>(scenario);

        let mut proof = test_scenario::take_from_sender<ProofOfHuman>(scenario);
        let original_details = proof_of_human::get_proof_details(&proof);
        let original_proof_id = proof_of_human::proof_details_proof_id(&original_details);

        proof_of_human::renew(
            &mut registry,
            &cap,
            &mut proof,
            b"walrus_blob_renewed",
            blob_object_id(@0x222),
            b"seal_identity_renewed",
            2,
            b"model_hash_v2",
            8_800,
            2_000,
            4_000,
            b"turn_left",
        );

        let details = proof_of_human::get_proof_details(&proof);
        assert!(proof_of_human::proof_details_proof_id(&details) == original_proof_id, 10);
        assert!(proof_of_human::proof_details_expires_at_ms(&details) == 4_000, 11);
        assert!(proof_of_human::proof_details_seal_identity(&details) == b"seal_identity_renewed", 12);
        assert!(proof_of_human::debug_record_proof_id(&registry, 0) == original_proof_id, 13);
        assert!(proof_of_human::debug_record_expires_at_ms(&registry, 0) == 4_000, 14);

        test_scenario::return_to_sender(scenario, proof);
        test_scenario::return_shared(registry);
        test_scenario::return_to_sender(scenario, cap);
    };

    test_scenario::end(scenario_val);
}

#[test]
fun test_revoke_marks_registry_and_deletes_owned_proof() {
    let mut scenario_val = test_scenario::begin(ADMIN);
    let scenario = &mut scenario_val;
    {
        proof_of_human::init_for_testing(test_scenario::ctx(scenario));
    };

    test_scenario::next_tx(scenario, ADMIN);
    {
        let mut registry = test_scenario::take_shared<ProofRegistry>(scenario);
        let cap = test_scenario::take_from_sender<VerifierCap>(scenario);

        mint_default_proof(&mut registry, &cap, OWNER, 100, 1_000, test_scenario::ctx(scenario));

        test_scenario::return_shared(registry);
        test_scenario::return_to_sender(scenario, cap);
    };

    test_scenario::next_tx(scenario, OWNER);
    {
        let mut registry = test_scenario::take_shared<ProofRegistry>(scenario);
        let proof = test_scenario::take_from_sender<ProofOfHuman>(scenario);

        proof_of_human::revoke(&mut registry, proof, test_scenario::ctx(scenario));

        assert!(!proof_of_human::has_valid_proof(&registry, OWNER, 101), 20);
        assert!(proof_of_human::debug_record_revoked(&registry, 0), 21);

        test_scenario::return_shared(registry);
    };

    test_scenario::next_tx(scenario, OWNER);
    {
        assert!(!test_scenario::has_most_recent_for_sender<ProofOfHuman>(scenario), 22);
    };

    test_scenario::end(scenario_val);
}

#[test]
fun test_seal_approve_owner_succeeds_for_owner_with_matching_identity() {
    let mut scenario_val = test_scenario::begin(ADMIN);
    let scenario = &mut scenario_val;
    {
        proof_of_human::init_for_testing(test_scenario::ctx(scenario));
    };

    test_scenario::next_tx(scenario, ADMIN);
    {
        let mut registry = test_scenario::take_shared<ProofRegistry>(scenario);
        let cap = test_scenario::take_from_sender<VerifierCap>(scenario);
        mint_default_proof(&mut registry, &cap, OWNER, 100, 1_000, test_scenario::ctx(scenario));
        test_scenario::return_shared(registry);
        test_scenario::return_to_sender(scenario, cap);
    };

    test_scenario::next_tx(scenario, OWNER);
    {
        let proof = test_scenario::take_from_sender<ProofOfHuman>(scenario);
        assert!(proof_of_human::seal_approve_owner(&proof, seal_identity(), test_scenario::ctx(scenario)), 30);
        test_scenario::return_to_sender(scenario, proof);
    };

    test_scenario::end(scenario_val);
}

#[test, expected_failure(abort_code = ::proof_of_human::proof_of_human::E_SEAL_IDENTITY_MISMATCH)]
fun test_seal_approve_owner_rejects_mismatched_identity() {
    let mut scenario_val = test_scenario::begin(ADMIN);
    let scenario = &mut scenario_val;
    {
        proof_of_human::init_for_testing(test_scenario::ctx(scenario));
    };

    test_scenario::next_tx(scenario, ADMIN);
    {
        let mut registry = test_scenario::take_shared<ProofRegistry>(scenario);
        let cap = test_scenario::take_from_sender<VerifierCap>(scenario);
        mint_default_proof(&mut registry, &cap, OWNER, 100, 1_000, test_scenario::ctx(scenario));
        test_scenario::return_shared(registry);
        test_scenario::return_to_sender(scenario, cap);
    };

    test_scenario::next_tx(scenario, OWNER);
    {
        let proof = test_scenario::take_from_sender<ProofOfHuman>(scenario);
        let _ = proof_of_human::seal_approve_owner(&proof, b"wrong_identity", test_scenario::ctx(scenario));
        test_scenario::return_to_sender(scenario, proof);
    };

    test_scenario::end(scenario_val);
}

#[test, expected_failure(abort_code = ::proof_of_human::proof_of_human::E_NOT_PROOF_OWNER)]
fun test_seal_approve_owner_rejects_non_owner() {
    let mut scenario_val = test_scenario::begin(ADMIN);
    let scenario = &mut scenario_val;
    {
        proof_of_human::init_for_testing(test_scenario::ctx(scenario));
    };

    test_scenario::next_tx(scenario, ADMIN);
    {
        let mut registry = test_scenario::take_shared<ProofRegistry>(scenario);
        let cap = test_scenario::take_from_sender<VerifierCap>(scenario);
        mint_default_proof(&mut registry, &cap, OWNER, 100, 1_000, test_scenario::ctx(scenario));
        test_scenario::return_shared(registry);
        test_scenario::return_to_sender(scenario, cap);
    };

    test_scenario::next_tx(scenario, OWNER);
    {
        let proof = test_scenario::take_from_sender<ProofOfHuman>(scenario);
        test_scenario::return_to_sender(scenario, proof);
    };

    test_scenario::next_tx(scenario, OWNER_TWO);
    {
        let registry = test_scenario::take_shared<ProofRegistry>(scenario);
        let proof_id = proof_of_human::debug_record_proof_id(&registry, 0);
        test_scenario::return_shared(registry);

        let proof = test_scenario::take_from_address_by_id<ProofOfHuman>(scenario, OWNER, proof_id);
        let _ = proof_of_human::seal_approve_owner(&proof, seal_identity(), test_scenario::ctx(scenario));
        test_scenario::return_to_address(OWNER, proof);
    };

    test_scenario::end(scenario_val);
}

#[test, expected_failure(abort_code = ::proof_of_human::proof_of_human::E_CONFIDENCE_BELOW_THRESHOLD)]
fun test_verify_and_mint_rejects_low_confidence() {
    let mut scenario_val = test_scenario::begin(ADMIN);
    let scenario = &mut scenario_val;
    {
        proof_of_human::init_for_testing_with_config(8_000, 100, test_scenario::ctx(scenario));
    };

    test_scenario::next_tx(scenario, ADMIN);
    {
        let mut registry = test_scenario::take_shared<ProofRegistry>(scenario);
        let cap = test_scenario::take_from_sender<VerifierCap>(scenario);

        proof_of_human::verify_and_mint(
            &mut registry,
            &cap,
            OWNER,
            walrus_blob_id(),
            blob_object_id(@0x111),
            seal_identity(),
            1,
            model_hash(),
            7_999,
            100,
            1_000,
            challenge_type(),
            test_scenario::ctx(scenario),
        );

        test_scenario::return_shared(registry);
        test_scenario::return_to_sender(scenario, cap);
    };

    test_scenario::end(scenario_val);
}
