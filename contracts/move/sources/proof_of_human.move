module proof_of_human::proof_of_human;

use std::bcs;
use sui::address;
use sui::clock::{Self, Clock};
use sui::ed25519;

const E_CONFIDENCE_BELOW_THRESHOLD: u64 = 0;
const E_ACTIVE_PROOF_EXISTS: u64 = 1;
const E_NOT_PROOF_OWNER: u64 = 2;
const E_SEAL_IDENTITY_MISMATCH: u64 = 3;
const E_INVALID_EXPIRY: u64 = 4;
const E_REGISTRY_RECORD_NOT_FOUND: u64 = 5;
const E_INVALID_CLAIM_SIGNATURE: u64 = 6;
const E_CLAIM_EXPIRED: u64 = 7;
const E_CLAIM_ALREADY_USED: u64 = 8;
const E_CLAIM_OWNER_MISMATCH: u64 = 9;
const E_CLAIM_PROOF_MISMATCH: u64 = 10;

const CLAIM_MINT_DOMAIN: vector<u8> = b"sui-human:claim-mint:v1";
const CLAIM_RENEW_DOMAIN: vector<u8> = b"sui-human:claim-renew:v1";
const DEFAULT_MINIMUM_CONFIDENCE_BPS: u64 = 3_500;
const DEFAULT_CLAIM_SIGNER_PUBLIC_KEY: vector<u8> =
    x"fa78d1932eb3727a318602a7135fb09d73392230ba4c83d3f95530f344990b35";

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
    claim_signer_public_key: vector<u8>,
    used_claim_ids: vector<vector<u8>>,
    records: vector<RegistryRecord>,
    proofs_issued: u64,
}

public struct VerifierCap has key {
    id: UID,
}

fun init(ctx: &mut TxContext) {
    create_registry_and_cap(DEFAULT_MINIMUM_CONFIDENCE_BPS, 90 * 24 * 60 * 60 * 1000, ctx)
}

#[test_only]
public fun init_for_testing(ctx: &mut TxContext) {
    create_registry_and_cap(DEFAULT_MINIMUM_CONFIDENCE_BPS, 90 * 24 * 60 * 60 * 1000, ctx)
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
    mint_internal(
        registry,
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
        ctx,
    );
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
    renew_internal(
        registry,
        proof,
        walrus_blob_id,
        walrus_blob_object_id,
        seal_identity,
        evidence_schema_version,
        model_hash,
        confidence_bps,
        issued_at_ms,
        expires_at_ms,
        challenge_type,
    );
}

public entry fun claim_and_mint(
    registry: &mut ProofRegistry,
    clock: &Clock,
    claim_id: vector<u8>,
    claim_expires_at_ms: u64,
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
    signature: vector<u8>,
    ctx: &mut TxContext,
) {
    assert!(tx_context::sender(ctx) == owner, E_CLAIM_OWNER_MISMATCH);
    validate_claim_window_and_replay(registry, clock, &claim_id, claim_expires_at_ms);

    let message = mint_claim_message(
        &claim_id,
        claim_expires_at_ms,
        owner,
        &walrus_blob_id,
        &walrus_blob_object_id,
        &seal_identity,
        evidence_schema_version,
        &model_hash,
        confidence_bps,
        issued_at_ms,
        expires_at_ms,
        &challenge_type,
    );
    assert!(
        ed25519::ed25519_verify(&signature, &registry.claim_signer_public_key, &message),
        E_INVALID_CLAIM_SIGNATURE,
    );
    mark_claim_used(registry, claim_id);

    mint_internal(
        registry,
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
        ctx,
    );
}

public entry fun claim_and_renew(
    registry: &mut ProofRegistry,
    clock: &Clock,
    proof: &mut ProofOfHuman,
    claim_id: vector<u8>,
    claim_expires_at_ms: u64,
    owner: address,
    proof_id: ID,
    walrus_blob_id: vector<u8>,
    walrus_blob_object_id: ID,
    seal_identity: vector<u8>,
    evidence_schema_version: u16,
    model_hash: vector<u8>,
    confidence_bps: u64,
    issued_at_ms: u64,
    expires_at_ms: u64,
    challenge_type: vector<u8>,
    signature: vector<u8>,
    ctx: &TxContext,
) {
    assert!(tx_context::sender(ctx) == owner, E_CLAIM_OWNER_MISMATCH);
    assert!(proof.owner == owner, E_NOT_PROOF_OWNER);
    assert!(object::id(proof) == proof_id, E_CLAIM_PROOF_MISMATCH);
    validate_claim_window_and_replay(registry, clock, &claim_id, claim_expires_at_ms);

    let message = renew_claim_message(
        &claim_id,
        claim_expires_at_ms,
        owner,
        &proof_id,
        &walrus_blob_id,
        &walrus_blob_object_id,
        &seal_identity,
        evidence_schema_version,
        &model_hash,
        confidence_bps,
        issued_at_ms,
        expires_at_ms,
        &challenge_type,
    );
    assert!(
        ed25519::ed25519_verify(&signature, &registry.claim_signer_public_key, &message),
        E_INVALID_CLAIM_SIGNATURE,
    );
    mark_claim_used(registry, claim_id);

    renew_internal(
        registry,
        proof,
        walrus_blob_id,
        walrus_blob_object_id,
        seal_identity,
        evidence_schema_version,
        model_hash,
        confidence_bps,
        issued_at_ms,
        expires_at_ms,
        challenge_type,
    );
}

public entry fun set_claim_signer_public_key(
    registry: &mut ProofRegistry,
    _cap: &VerifierCap,
    claim_signer_public_key: vector<u8>,
) {
    registry.claim_signer_public_key = claim_signer_public_key;
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

public fun claim_signer_public_key(registry: &ProofRegistry): vector<u8> {
    registry.claim_signer_public_key
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
        claim_signer_public_key: DEFAULT_CLAIM_SIGNER_PUBLIC_KEY,
        used_claim_ids: vector::empty(),
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

fun mint_internal(
    registry: &mut ProofRegistry,
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

fun renew_internal(
    registry: &mut ProofRegistry,
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

fun validate_claim_window_and_replay(
    registry: &ProofRegistry,
    clock: &Clock,
    claim_id: &vector<u8>,
    claim_expires_at_ms: u64,
) {
    assert!(claim_expires_at_ms > clock::timestamp_ms(clock), E_CLAIM_EXPIRED);
    assert!(!claim_used(registry, claim_id), E_CLAIM_ALREADY_USED);
}

fun claim_used(registry: &ProofRegistry, claim_id: &vector<u8>): bool {
    let len = vector::length(&registry.used_claim_ids);
    let mut i = 0;
    while (i < len) {
        if (vector::borrow(&registry.used_claim_ids, i) == claim_id) {
            return true
        };
        i = i + 1;
    };
    false
}

fun mark_claim_used(registry: &mut ProofRegistry, claim_id: vector<u8>) {
    vector::push_back(&mut registry.used_claim_ids, claim_id);
}

fun mint_claim_message(
    claim_id: &vector<u8>,
    claim_expires_at_ms: u64,
    owner: address,
    walrus_blob_id: &vector<u8>,
    walrus_blob_object_id: &ID,
    seal_identity: &vector<u8>,
    evidence_schema_version: u16,
    model_hash: &vector<u8>,
    confidence_bps: u64,
    issued_at_ms: u64,
    expires_at_ms: u64,
    challenge_type: &vector<u8>,
): vector<u8> {
    let mut message = CLAIM_MINT_DOMAIN;
    message.append(bcs::to_bytes(claim_id));
    message.append(bcs::to_bytes(&claim_expires_at_ms));
    message.append(address::to_bytes(owner));
    message.append(bcs::to_bytes(walrus_blob_id));
    message.append(object::id_to_bytes(walrus_blob_object_id));
    message.append(bcs::to_bytes(seal_identity));
    message.append(bcs::to_bytes(&evidence_schema_version));
    message.append(bcs::to_bytes(model_hash));
    message.append(bcs::to_bytes(&confidence_bps));
    message.append(bcs::to_bytes(&issued_at_ms));
    message.append(bcs::to_bytes(&expires_at_ms));
    message.append(bcs::to_bytes(challenge_type));
    message
}

fun renew_claim_message(
    claim_id: &vector<u8>,
    claim_expires_at_ms: u64,
    owner: address,
    proof_id: &ID,
    walrus_blob_id: &vector<u8>,
    walrus_blob_object_id: &ID,
    seal_identity: &vector<u8>,
    evidence_schema_version: u16,
    model_hash: &vector<u8>,
    confidence_bps: u64,
    issued_at_ms: u64,
    expires_at_ms: u64,
    challenge_type: &vector<u8>,
): vector<u8> {
    let mut message = CLAIM_RENEW_DOMAIN;
    message.append(bcs::to_bytes(claim_id));
    message.append(bcs::to_bytes(&claim_expires_at_ms));
    message.append(address::to_bytes(owner));
    message.append(object::id_to_bytes(proof_id));
    message.append(bcs::to_bytes(walrus_blob_id));
    message.append(object::id_to_bytes(walrus_blob_object_id));
    message.append(bcs::to_bytes(seal_identity));
    message.append(bcs::to_bytes(&evidence_schema_version));
    message.append(bcs::to_bytes(model_hash));
    message.append(bcs::to_bytes(&confidence_bps));
    message.append(bcs::to_bytes(&issued_at_ms));
    message.append(bcs::to_bytes(&expires_at_ms));
    message.append(bcs::to_bytes(challenge_type));
    message
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
