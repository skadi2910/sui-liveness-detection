module proof_of_human::proof_of_human;

const E_CONFIDENCE_BELOW_THRESHOLD: u64 = 0;
const E_ACTIVE_PROOF_EXISTS: u64 = 1;
const E_NOT_PROOF_OWNER: u64 = 2;
const E_SEAL_IDENTITY_MISMATCH: u64 = 3;
const E_INVALID_EXPIRY: u64 = 4;
const E_REGISTRY_RECORD_NOT_FOUND: u64 = 5;

public struct ProofOfHuman has key {
    id: UID,
    owner: address,
    walrus_blob_id: vector<u8>,
    walrus_blob_object_id: ID,
    seal_identity: vector<u8>,
    evidence_schema_version: u16,
    model_hash: vector<u8>,
    confidence_bps: u64,
    issued_at_ms: u64,
    expires_at_ms: u64,
    challenge_type: vector<u8>,
}

public struct ProofDetails has copy, drop, store {
    proof_id: ID,
    owner: address,
    walrus_blob_id: vector<u8>,
    walrus_blob_object_id: ID,
    seal_identity: vector<u8>,
    evidence_schema_version: u16,
    model_hash: vector<u8>,
    confidence_bps: u64,
    issued_at_ms: u64,
    expires_at_ms: u64,
    challenge_type: vector<u8>,
}

public struct RegistryRecord has copy, drop, store {
    owner: address,
    proof_id: ID,
    issued_at_ms: u64,
    expires_at_ms: u64,
    revoked: bool,
}

public struct ProofRegistry has key {
    id: UID,
    minimum_confidence_bps: u64,
    default_ttl_ms: u64,
    records: vector<RegistryRecord>,
    proofs_issued: u64,
}

public struct VerifierCap has key {
    id: UID,
}

fun init(ctx: &mut TxContext) {
    create_registry_and_cap(7_000, 90 * 24 * 60 * 60 * 1000, ctx)
}

#[test_only]
public fun init_for_testing(ctx: &mut TxContext) {
    create_registry_and_cap(7_000, 90 * 24 * 60 * 60 * 1000, ctx)
}

#[test_only]
public fun init_for_testing_with_config(
    minimum_confidence_bps: u64,
    default_ttl_ms: u64,
    ctx: &mut TxContext,
) {
    create_registry_and_cap(minimum_confidence_bps, default_ttl_ms, ctx)
}

public entry fun verify_and_mint(
    registry: &mut ProofRegistry,
    _cap: &VerifierCap,
    owner: address,
    walrus_blob_id: vector<u8>,
    walrus_blob_object_id: ID,
    seal_identity: vector<u8>,
    evidence_schema_version: u16,
    model_hash: vector<u8>,
    confidence_bps: u64,
    issued_at_ms: u64,
    expires_at_ms: u64,
    challenge_type: vector<u8>,
    ctx: &mut TxContext,
) {
    assert!(confidence_bps >= registry.minimum_confidence_bps, E_CONFIDENCE_BELOW_THRESHOLD);
    assert!(expires_at_ms > issued_at_ms, E_INVALID_EXPIRY);
    assert!(!has_valid_proof(registry, owner, issued_at_ms), E_ACTIVE_PROOF_EXISTS);

    let proof = ProofOfHuman {
        id: object::new(ctx),
        owner,
        walrus_blob_id,
        walrus_blob_object_id,
        seal_identity,
        evidence_schema_version,
        model_hash,
        confidence_bps,
        issued_at_ms,
        expires_at_ms,
        challenge_type,
    };

    upsert_registry_record(
        registry,
        owner,
        object::id(&proof),
        issued_at_ms,
        expires_at_ms,
    );
    registry.proofs_issued = registry.proofs_issued + 1;
    transfer::transfer(proof, owner);
}

public entry fun renew(
    registry: &mut ProofRegistry,
    _cap: &VerifierCap,
    proof: &mut ProofOfHuman,
    walrus_blob_id: vector<u8>,
    walrus_blob_object_id: ID,
    seal_identity: vector<u8>,
    evidence_schema_version: u16,
    model_hash: vector<u8>,
    confidence_bps: u64,
    issued_at_ms: u64,
    expires_at_ms: u64,
    challenge_type: vector<u8>,
) {
    assert!(confidence_bps >= registry.minimum_confidence_bps, E_CONFIDENCE_BELOW_THRESHOLD);
    assert!(expires_at_ms > issued_at_ms, E_INVALID_EXPIRY);

    let proof_id = *proof.id.as_inner();
    update_registry_record(
        registry,
        proof.owner,
        proof_id,
        issued_at_ms,
        expires_at_ms,
    );

    proof.walrus_blob_id = walrus_blob_id;
    proof.walrus_blob_object_id = walrus_blob_object_id;
    proof.seal_identity = seal_identity;
    proof.evidence_schema_version = evidence_schema_version;
    proof.model_hash = model_hash;
    proof.confidence_bps = confidence_bps;
    proof.issued_at_ms = issued_at_ms;
    proof.expires_at_ms = expires_at_ms;
    proof.challenge_type = challenge_type;
}

public entry fun revoke(
    registry: &mut ProofRegistry,
    proof: ProofOfHuman,
    ctx: &TxContext,
) {
    assert!(tx_context::sender(ctx) == proof.owner, E_NOT_PROOF_OWNER);

    let proof_id = *proof.id.as_inner();
    revoke_registry_record(registry, proof.owner, proof_id);

    let ProofOfHuman {
        id,
        owner: _,
        walrus_blob_id: _,
        walrus_blob_object_id: _,
        seal_identity: _,
        evidence_schema_version: _,
        model_hash: _,
        confidence_bps: _,
        issued_at_ms: _,
        expires_at_ms: _,
        challenge_type: _,
    } = proof;
    object::delete(id);
}

public fun has_valid_proof(
    registry: &ProofRegistry,
    owner: address,
    now_ms: u64,
): bool {
    let len = vector::length(&registry.records);
    let mut i = 0;
    while (i < len) {
        let record = vector::borrow(&registry.records, i);
        if (record.owner == owner && !record.revoked && record.expires_at_ms > now_ms) {
            return true
        };
        i = i + 1;
    };
    false
}

public fun get_proof_details(proof: &ProofOfHuman): ProofDetails {
    ProofDetails {
        proof_id: *proof.id.as_inner(),
        owner: proof.owner,
        walrus_blob_id: proof.walrus_blob_id,
        walrus_blob_object_id: proof.walrus_blob_object_id,
        seal_identity: proof.seal_identity,
        evidence_schema_version: proof.evidence_schema_version,
        model_hash: proof.model_hash,
        confidence_bps: proof.confidence_bps,
        issued_at_ms: proof.issued_at_ms,
        expires_at_ms: proof.expires_at_ms,
        challenge_type: proof.challenge_type,
    }
}

public fun proof_details_proof_id(details: &ProofDetails): ID {
    details.proof_id
}

public fun proof_details_owner(details: &ProofDetails): address {
    details.owner
}

public fun proof_details_seal_identity(details: &ProofDetails): vector<u8> {
    details.seal_identity
}

public fun proof_details_evidence_schema_version(details: &ProofDetails): u16 {
    details.evidence_schema_version
}

public fun proof_details_confidence_bps(details: &ProofDetails): u64 {
    details.confidence_bps
}

public fun proof_details_expires_at_ms(details: &ProofDetails): u64 {
    details.expires_at_ms
}

public fun proof_details_challenge_type(details: &ProofDetails): vector<u8> {
    details.challenge_type
}

public fun seal_approve_owner(
    proof: &ProofOfHuman,
    requested_seal_identity: vector<u8>,
    ctx: &TxContext,
): bool {
    assert!(tx_context::sender(ctx) == proof.owner, E_NOT_PROOF_OWNER);
    assert!(proof.seal_identity == requested_seal_identity, E_SEAL_IDENTITY_MISMATCH);
    true
}

public fun minimum_confidence_bps(registry: &ProofRegistry): u64 {
    registry.minimum_confidence_bps
}

public fun default_ttl_ms(registry: &ProofRegistry): u64 {
    registry.default_ttl_ms
}

public fun proofs_issued(registry: &ProofRegistry): u64 {
    registry.proofs_issued
}

#[test_only]
public fun debug_owner(registry: &ProofRegistry, index: u64): address {
    vector::borrow(&registry.records, index).owner
}

#[test_only]
public fun debug_record_expires_at_ms(registry: &ProofRegistry, index: u64): u64 {
    vector::borrow(&registry.records, index).expires_at_ms
}

#[test_only]
public fun debug_record_revoked(registry: &ProofRegistry, index: u64): bool {
    vector::borrow(&registry.records, index).revoked
}

#[test_only]
public fun debug_record_proof_id(registry: &ProofRegistry, index: u64): ID {
    vector::borrow(&registry.records, index).proof_id
}

fun create_registry_and_cap(
    minimum_confidence_bps: u64,
    default_ttl_ms: u64,
    ctx: &mut TxContext,
) {
    let registry = ProofRegistry {
        id: object::new(ctx),
        minimum_confidence_bps,
        default_ttl_ms,
        records: vector::empty(),
        proofs_issued: 0,
    };
    let cap = VerifierCap { id: object::new(ctx) };

    transfer::share_object(registry);
    transfer::transfer(cap, tx_context::sender(ctx));
}

fun upsert_registry_record(
    registry: &mut ProofRegistry,
    owner: address,
    proof_id: ID,
    issued_at_ms: u64,
    expires_at_ms: u64,
) {
    let len = vector::length(&registry.records);
    let mut i = 0;
    while (i < len) {
        let record = vector::borrow_mut(&mut registry.records, i);
        if (record.owner == owner) {
            record.proof_id = proof_id;
            record.issued_at_ms = issued_at_ms;
            record.expires_at_ms = expires_at_ms;
            record.revoked = false;
            return
        };
        i = i + 1;
    };

    vector::push_back(
        &mut registry.records,
        RegistryRecord {
            owner,
            proof_id,
            issued_at_ms,
            expires_at_ms,
            revoked: false,
        },
    );
}

fun update_registry_record(
    registry: &mut ProofRegistry,
    owner: address,
    proof_id: ID,
    issued_at_ms: u64,
    expires_at_ms: u64,
) {
    let len = vector::length(&registry.records);
    let mut i = 0;
    while (i < len) {
        let record = vector::borrow_mut(&mut registry.records, i);
        if (record.owner == owner && record.proof_id == proof_id && !record.revoked) {
            record.issued_at_ms = issued_at_ms;
            record.expires_at_ms = expires_at_ms;
            return
        };
        i = i + 1;
    };
    abort E_REGISTRY_RECORD_NOT_FOUND
}

fun revoke_registry_record(
    registry: &mut ProofRegistry,
    owner: address,
    proof_id: ID,
) {
    let len = vector::length(&registry.records);
    let mut i = 0;
    while (i < len) {
        let record = vector::borrow_mut(&mut registry.records, i);
        if (record.owner == owner && record.proof_id == proof_id && !record.revoked) {
            record.revoked = true;
            record.expires_at_ms = 0;
            return
        };
        i = i + 1;
    };
    abort E_REGISTRY_RECORD_NOT_FOUND
}
