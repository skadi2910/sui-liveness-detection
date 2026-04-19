from __future__ import annotations

import base64
import json

from app.adapters.command_runner import CommandOutput
from app.adapters.evidence_encryptor import SealCommandEvidenceEncryptor
from app.adapters.evidence_store import WalrusCliEvidenceStore
from app.adapters.proof_minter import SuiCliProofMinter
from app.pipeline.types import (
    ChallengeType,
    SessionStatus,
    VerificationResult,
)


class _QueuedRunner:
    def __init__(self, outputs: list[CommandOutput]) -> None:
        self.outputs = outputs
        self.calls: list[tuple[list[str], str | None, str | None, dict[str, str] | None]] = []

    def __call__(self, args, *, input_text=None, cwd=None, env=None):
        self.calls.append((list(args), input_text, cwd, env))
        if not self.outputs:
            raise AssertionError(f"unexpected command: {args}")
        return self.outputs.pop(0)


def _json_output(args: list[str], payload: object) -> CommandOutput:
    return CommandOutput(
        args=tuple(args),
        returncode=0,
        stdout=json.dumps(payload),
        stderr="",
    )


def _pipeline_result() -> VerificationResult:
    return VerificationResult(
        session_id="sess_real_adapter",
        wallet_address="0xwallet",
        challenge_type=ChallengeType.SMILE,
        status=SessionStatus.VERIFIED,
        human=True,
        confidence=0.92,
        spoof_score=0.03,
        walrus_blob_id="blob123",
        walrus_blob_object_id="0xblobobject123",
        seal_identity="seal_identity_live",
        evidence_schema_version=1,
        model_hash="sha256:model_bundle",
    )


def test_seal_command_encryptor_round_trips_command_contract() -> None:
    payload_bytes = b'{"hello":"seal"}'
    runner = _QueuedRunner(
        [
            _json_output(
                ["seal-encrypt"],
                {
                    "encrypted_bytes_b64": base64.b64encode(b"ciphertext").decode("utf-8"),
                    "seal_identity": "seal_identity_live",
                    "policy_version": "seal-v1",
                    "metadata": {"wallet_address": "0xwallet"},
                },
            ),
            _json_output(
                ["seal-decrypt"],
                {
                    "decrypted_bytes_b64": base64.b64encode(payload_bytes).decode("utf-8"),
                },
            ),
        ]
    )
    encryptor = SealCommandEvidenceEncryptor(
        encrypt_command="seal-encrypt",
        decrypt_command="seal-decrypt",
        command_cwd="/tmp",
        runner=runner,
    )

    encrypted = encryptor.encrypt_for_wallet("0xwallet", payload_bytes)
    decrypted = encryptor.decrypt_for_dispute(
        {"wallet_address": "0xwallet", "encrypted_bytes": encrypted.encrypted_bytes}
    )

    assert encrypted.seal_identity == "seal_identity_live"
    assert encrypted.encrypted_bytes == b"ciphertext"
    assert decrypted == payload_bytes
    assert runner.calls[0][0] == ["seal-encrypt"]
    assert runner.calls[0][2] == "/tmp"


def test_walrus_cli_store_and_delete_parse_blob_metadata() -> None:
    runner = _QueuedRunner(
        [
            _json_output(
                ["walrus", "store"],
                {
                    "newlyCreated": {
                        "blobObject": {
                            "id": "0xwalrusobject123",
                            "blobId": "walrus_blob_123",
                        }
                    }
                },
            ),
            _json_output(["walrus", "delete"], {"deleted": True}),
        ]
    )
    store = WalrusCliEvidenceStore(
        walrus_binary="walrus",
        storage_epochs=3,
        runner=runner,
    )

    blob_ref = store.put_encrypted_blob(b"ciphertext", {"session_id": "sess_1"})
    deleted = store.delete_blob(blob_ref.blob_id)

    assert blob_ref.blob_id == "walrus_blob_123"
    assert blob_ref.blob_object_id == "0xwalrusobject123"
    assert blob_ref.metadata["session_id"] == "sess_1"
    assert deleted is True
    assert runner.calls[0][0][0:2] == ["walrus", "store"]
    assert "--deletable" in runner.calls[0][0]
    assert runner.calls[1][0][0:2] == ["walrus", "delete"]


def test_walrus_cli_store_accepts_list_shaped_json_output() -> None:
    runner = _QueuedRunner(
        [
            _json_output(
                ["walrus", "store"],
                [
                    {
                        "newlyCreated": {
                            "blobObject": {
                                "id": "0xwalrusobject456",
                                "blobId": "walrus_blob_456",
                            }
                        }
                    }
                ],
            ),
        ]
    )
    store = WalrusCliEvidenceStore(
        walrus_binary="walrus",
        storage_epochs=3,
        runner=runner,
    )

    blob_ref = store.put_encrypted_blob(b"ciphertext", {"session_id": "sess_list"})

    assert blob_ref.blob_id == "walrus_blob_456"
    assert blob_ref.blob_object_id == "0xwalrusobject456"
    assert blob_ref.metadata["session_id"] == "sess_list"


def test_walrus_cli_store_accepts_blob_store_result_wrapper() -> None:
    runner = _QueuedRunner(
        [
            _json_output(
                ["walrus", "store"],
                [
                    {
                        "blobStoreResult": {
                            "newlyCreated": {
                                "blobObject": {
                                    "id": "0xwalrusobject789",
                                    "blobId": "walrus_blob_789",
                                }
                            }
                        }
                    }
                ],
            ),
        ]
    )
    store = WalrusCliEvidenceStore(
        walrus_binary="walrus",
        storage_epochs=3,
        runner=runner,
    )

    blob_ref = store.put_encrypted_blob(b"ciphertext", {"session_id": "sess_wrapped"})

    assert blob_ref.blob_id == "walrus_blob_789"
    assert blob_ref.blob_object_id == "0xwalrusobject789"
    assert blob_ref.metadata["session_id"] == "sess_wrapped"


def test_sui_cli_proof_minter_find_active_proof_reads_owned_object_details() -> None:
    runner = _QueuedRunner(
        [
            CommandOutput(
                args=("sui", "client", "active-address"),
                returncode=0,
                stdout="0xverifier",
                stderr="",
            ),
            _json_output(
                ["sui", "client", "object"],
                {"content": {"fields": {"records": []}}},
            ),
            _json_output(
                ["sui", "client", "objects"],
                [
                    {
                        "objectId": "0xproof123",
                        "type": "0xpackage::proof_of_human::ProofOfHuman",
                    }
                ],
            ),
            _json_output(
                ["sui", "client", "object"],
                {
                    "content": {
                        "fields": {
                            "expires_at_ms": str(4_102_444_800_000),
                        }
                    }
                },
            ),
        ]
    )
    minter = SuiCliProofMinter(
        package_id="0xpackage",
        registry_object_id="0xregistry",
        verifier_cap_object_id="0xcap",
        expected_active_address="0xverifier",
        runner=runner,
    )

    active_proof = minter.find_active_proof("0xwallet")

    assert active_proof is not None
    assert active_proof.proof_id == "0xproof123"
    assert active_proof.object_id == "0xproof123"


def test_sui_cli_proof_minter_find_active_proof_reads_registry_records_first() -> None:
    runner = _QueuedRunner(
        [
            CommandOutput(
                args=("sui", "client", "active-address"),
                returncode=0,
                stdout="0xverifier",
                stderr="",
            ),
            _json_output(
                ["sui", "client", "object"],
                {
                    "content": {
                        "fields": {
                            "records": [
                                {
                                    "owner": "0xwallet",
                                    "proof_id": "0xproof_from_registry",
                                    "issued_at_ms": "100",
                                    "expires_at_ms": str(4_102_444_800_000),
                                    "revoked": False,
                                }
                            ]
                        }
                    }
                },
            ),
        ]
    )
    minter = SuiCliProofMinter(
        package_id="0xpackage",
        registry_object_id="0xregistry",
        verifier_cap_object_id="0xcap",
        expected_active_address="0xverifier",
        runner=runner,
    )

    active_proof = minter.find_active_proof("0xwallet")

    assert active_proof is not None
    assert active_proof.proof_id == "0xproof_from_registry"
    assert active_proof.object_id == "0xproof_from_registry"
    assert active_proof.metadata["source"] == "registry_record"
    assert len(runner.calls) == 2


def test_sui_cli_proof_minter_mint_and_renew_return_operation_metadata() -> None:
    runner = _QueuedRunner(
        [
            _json_output(
                ["sui", "client", "object"],
                {"content": {"fields": {"minimum_confidence_bps": "7000", "default_ttl_ms": "1000"}}},
            ),
            _json_output(
                ["sui", "client", "call"],
                {
                    "effects": {"transactionDigest": "0xtxn_mint"},
                    "objectChanges": [
                        {
                            "objectType": "0xpackage::proof_of_human::ProofOfHuman",
                            "objectId": "0xproof_new",
                        }
                    ],
                },
            ),
            _json_output(
                ["sui", "client", "object"],
                {"content": {"fields": {"minimum_confidence_bps": "7000", "default_ttl_ms": "1000"}}},
            ),
            _json_output(
                ["sui", "client", "call"],
                {
                    "effects": {"transactionDigest": "0xtxn_renew"},
                },
            ),
        ]
    )
    minter = SuiCliProofMinter(
        package_id="0xpackage",
        registry_object_id="0xregistry",
        verifier_cap_object_id="0xcap",
        network="sui-testnet",
        runner=runner,
    )

    minted = minter.mint_proof(_pipeline_result())
    renewed = minter.renew_proof(_pipeline_result(), "0xproof_new")

    assert minted.success is True
    assert minted.proof_id == "0xproof_new"
    assert minted.proof_operation == "minted"
    assert minted.chain_network == "sui-testnet"
    assert renewed.success is True
    assert renewed.proof_id == "0xproof_new"
    assert renewed.proof_operation == "renewed"
    assert renewed.transaction_digest == "0xtxn_renew"


def test_sui_cli_proof_minter_places_client_flags_after_client_command() -> None:
    runner = _QueuedRunner(
        [
            CommandOutput(
                args=("sui", "client", "--client.config", "/tmp/client.yaml", "--client.env", "testnet", "active-address"),
                returncode=0,
                stdout="0xverifier",
                stderr="",
            ),
            _json_output(
                ["sui", "client", "--client.config", "/tmp/client.yaml", "--client.env", "testnet", "object"],
                {"content": {"fields": {"records": []}}},
            ),
            _json_output(
                ["sui", "client", "--client.config", "/tmp/client.yaml", "--client.env", "testnet", "objects"],
                [],
            ),
        ]
    )
    minter = SuiCliProofMinter(
        package_id="0xpackage",
        registry_object_id="0xregistry",
        verifier_cap_object_id="0xcap",
        client_config_path="/tmp/client.yaml",
        env_alias="testnet",
        expected_active_address="0xverifier",
        runner=runner,
    )

    active = minter.find_active_proof("0xwallet")

    assert active is None
    assert runner.calls[0][0] == [
        "sui",
        "client",
        "--client.config",
        "/tmp/client.yaml",
        "--client.env",
        "testnet",
        "active-address",
    ]
    assert runner.calls[1][0][:7] == [
        "sui",
        "client",
        "--client.config",
        "/tmp/client.yaml",
        "--client.env",
        "testnet",
        "object",
    ]
    assert runner.calls[2][0][:7] == [
        "sui",
        "client",
        "--client.config",
        "/tmp/client.yaml",
        "--client.env",
        "testnet",
        "objects",
    ]


def test_sui_cli_proof_minter_extracts_fields_from_flat_content_shape() -> None:
    minter = SuiCliProofMinter(
        package_id="0xpackage",
        registry_object_id="0xregistry",
        verifier_cap_object_id="0xcap",
    )

    fields = minter._extract_object_fields(  # type: ignore[attr-defined]
        {
            "content": {
                "default_ttl_ms": "7776000000",
                "minimum_confidence_bps": "7000",
                "proofs_issued": "0",
                "records": [],
            }
        }
    )

    assert fields["default_ttl_ms"] == "7776000000"
    assert fields["minimum_confidence_bps"] == "7000"
