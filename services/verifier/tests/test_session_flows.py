from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from app.adapters.evidence_store import StoredBlobRef
from app.adapters.evidence_store import InMemoryEvidenceStore
from app.sessions.models import ChallengeType


def _session_payload(
    wallet_address: str = "0xtest-wallet",
    challenge_sequence: list[str] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "wallet_address": wallet_address,
        "client": {
            "platform": "test-suite",
            "user_agent": "pytest",
        },
    }
    if challenge_sequence is not None:
        payload["challenge_sequence"] = challenge_sequence
    return payload


def _frame_event(metadata: dict[str, object]) -> dict[str, object]:
    return {"type": "frame", "metadata": metadata}


def _frame_event_with_landmarks(
    metadata: dict[str, object],
    landmarks: dict[str, object],
) -> dict[str, object]:
    return {"type": "frame", "metadata": metadata, "landmarks": landmarks}


def _challenge_frames(
    challenge_type: str,
    *,
    spoof_score: float = 0.01,
) -> list[dict[str, object]]:
    common_metadata = {
        "force_face_detected": True,
        "force_quality_pass": True,
        "force_spoof_score": spoof_score,
    }
    if challenge_type == "blink_twice":
        return [
            _frame_event({**common_metadata, "blink": True}),
            _frame_event({**common_metadata, "blink": False}),
            _frame_event({**common_metadata, "blink": True}),
            _frame_event({**common_metadata, "blink": False}),
        ]
    if challenge_type == "turn_left":
        return [
            _frame_event({**common_metadata, "head_turn": "left"})
            for _ in range(4)
        ]
    if challenge_type == "turn_right":
        return [
            _frame_event({**common_metadata, "head_turn": "right"})
            for _ in range(4)
        ]
    if challenge_type == "nod_head":
        return [
            _frame_event({**common_metadata, "pitch": 14}),
            _frame_event({**common_metadata, "pitch": -14}),
            _frame_event({**common_metadata, "pitch": 14}),
            _frame_event({**common_metadata, "pitch": -14}),
        ]
    if challenge_type == "smile":
        return [
            _frame_event({**common_metadata, "smile_ratio": 0.48})
            for _ in range(4)
        ]
    return [_frame_event({**common_metadata, "mouth_open": True})]


def _send_frame_and_receive_progress(websocket, event: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    websocket.send_json(event)
    challenge_update = websocket.receive_json()
    progress = websocket.receive_json()
    return challenge_update, progress


def _force_sequence(client: TestClient, sequence: list[ChallengeType]) -> None:
    service = client.app.state.session_service
    service._select_challenge_sequence = lambda _session_id: sequence  # type: ignore[attr-defined]


class _WalrusBlobRef(str):
    def __new__(
        cls,
        blob_id: str,
        *,
        blob_object_id: str,
        created_at: str,
        provider_metadata: dict[str, object] | None = None,
    ) -> "_WalrusBlobRef":
        instance = str.__new__(cls, blob_id)
        instance.blob_id = blob_id
        instance.blob_object_id = blob_object_id
        instance.created_at = created_at
        instance.provider_metadata = provider_metadata or {}
        return instance


class _SealEnvelope(bytes):
    def __new__(
        cls,
        encrypted_bytes: bytes,
        *,
        seal_identity: str,
        evidence_schema_version: int,
        policy_version: str,
    ) -> "_SealEnvelope":
        instance = bytes.__new__(cls, encrypted_bytes)
        instance.encrypted_bytes = encrypted_bytes
        instance.seal_identity = seal_identity
        instance.evidence_schema_version = evidence_schema_version
        instance.policy_version = policy_version
        return instance


class _TrackingEvidenceStore(InMemoryEvidenceStore):
    def __init__(self) -> None:
        super().__init__()
        self.put_results: list[_WalrusBlobRef] = []
        self.deleted_blob_ids: list[str] = []

    def put_encrypted_blob(self, blob_bytes: bytes, metadata: dict[str, object]) -> _WalrusBlobRef:
        blob_ref = super().put_encrypted_blob(bytes(blob_bytes), metadata)
        assert isinstance(blob_ref, StoredBlobRef)
        blob_ref = _WalrusBlobRef(
            blob_ref.blob_id,
            blob_object_id=blob_ref.blob_object_id,
            created_at=blob_ref.created_at,
            provider_metadata=blob_ref.metadata,
        )
        self.put_results.append(blob_ref)
        return blob_ref

    def delete_blob(self, blob_id: str) -> bool:
        self.deleted_blob_ids.append(blob_id)
        return super().delete_blob(blob_id)


class _TrackingEvidenceEncryptor:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def encrypt_for_wallet(self, wallet_address: str, payload: bytes | str | dict[str, object]) -> _SealEnvelope:
        self.calls.append(
            {
                "wallet_address": wallet_address,
                "payload": payload,
            }
        )
        return _SealEnvelope(
            b'{"ciphertext":"phase1"}',
            seal_identity="seal_phase1_identity",
            evidence_schema_version=1,
            policy_version="mock-seal-v1",
        )

    def decrypt_for_dispute(self, policy_input) -> bytes:  # pragma: no cover - not used in these tests
        return b"{}"


class _Phase1ProofMinter:
    def __init__(self, *, success: bool, reason: str | None = None) -> None:
        self.success = success
        self.reason = reason
        self.mint_calls: list[object] = []

    def mint_proof(self, session_result) -> SimpleNamespace:
        self.mint_calls.append(session_result)
        walrus_blob_id = getattr(session_result, "walrus_blob_id", None) or getattr(
            session_result,
            "blob_id",
            None,
        )
        walrus_blob_object_id = getattr(session_result, "walrus_blob_object_id", None)
        return SimpleNamespace(
            success=self.success,
            proof_id="0xproof_phase1",
            transaction_digest="0xtxn_phase1",
            expires_at="2026-07-17T00:00:00+00:00",
            walrus_blob_id=walrus_blob_id,
            walrus_blob_object_id=walrus_blob_object_id,
            seal_identity="seal_phase1_identity",
            evidence_schema_version=1,
            model_hash="model_hash_phase1",
            metadata={
                "network": "mock-sui-testnet",
                "model_hash": "model_hash_phase1",
            },
            reason=self.reason,
        )

    def renew_proof(self, wallet_address: str, previous_proof_id: str) -> SimpleNamespace:
        return SimpleNamespace(
            success=True,
            proof_id=previous_proof_id,
            expires_at="2026-07-17T00:00:00+00:00",
            transaction_digest="0xtxn_phase1_renew",
            metadata={"network": "mock-sui-testnet"},
        )


def _mark_event_as_full_mode_success(event: dict[str, object]) -> dict[str, object]:
    metadata = event.setdefault("metadata", {})
    assert isinstance(metadata, dict)
    metadata.update(
        {
            "force_human_face_score": 0.92,
            "force_deepfake_score": 0.08,
        }
    )
    return event


def _run_full_mode_terminal_event(
    client: TestClient,
    *,
    wallet_address: str,
    challenge_sequence: list[ChallengeType],
) -> tuple[dict[str, object], dict[str, object]]:
    _force_sequence(client, challenge_sequence)
    create_response = client.post("/api/sessions", json=_session_payload(wallet_address))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        for challenge in session["challenge_sequence"]:
            for event in _challenge_frames(challenge, spoof_score=0.02):
                _send_frame_and_receive_progress(
                    websocket,
                    _mark_event_as_full_mode_success(event),
                )

        websocket.send_json({"type": "finalize", "mode": "full"})
        assert websocket.receive_json()["type"] == "processing"
        terminal_event = websocket.receive_json()

    return session, terminal_event


def test_create_session_returns_expected_contract(client: TestClient) -> None:
    response = client.post("/api/sessions", json=_session_payload())

    assert response.status_code == 201
    payload = response.json()

    assert payload["session_id"].startswith("sess_")
    assert payload["status"] == "created"
    assert payload["challenge_type"] in {"turn_left", "turn_right", "nod_head", "smile", "open_mouth"}
    assert 2 <= payload["total_challenges"] <= 3
    assert len(payload["challenge_sequence"]) == payload["total_challenges"]
    assert payload["ws_url"] == f"/ws/sessions/{payload['session_id']}/stream"
    assert "blink_twice" not in payload["challenge_sequence"]

    session_response = client.get(f"/api/sessions/{payload['session_id']}")
    assert session_response.status_code == 200
    session_payload = session_response.json()
    assert session_payload["status"] == "created"
    assert session_payload["challenge_sequence"] == payload["challenge_sequence"]


def test_create_session_accepts_fixed_sequence_override(client: TestClient) -> None:
    response = client.post(
        "/api/sessions",
        json=_session_payload(
            "0xfixed-sequence-wallet",
            challenge_sequence=["turn_left", "open_mouth", "smile"],
        ),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["challenge_sequence"] == ["turn_left", "open_mouth", "smile"]
    assert payload["challenge_type"] == "turn_left"
    assert payload["total_challenges"] == 3


def test_create_session_waits_for_models_to_be_ready(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = client.app.state.session_service
    monkeypatch.setattr(
        type(service.face_detector),
        "models_ready",
        property(lambda self: False),
    )

    response = client.post("/api/sessions", json=_session_payload("0xwarming-wallet"))

    assert response.status_code == 503
    assert "still loading" in response.json()["detail"]


def test_health_exposes_tuning_snapshot(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ready"
    assert payload["tuning"]["minimum_step_frames"] == 2
    assert payload["tuning"]["quality_blur_threshold"] == 45.0
    assert payload["tuning"]["quality_min_face_size"] == 80
    assert payload["tuning"]["turn_yaw_threshold_degrees"] == 18.0
    assert payload["tuning"]["smile_ratio_threshold"] == 0.36
    assert payload["tuning"]["landmark_spotcheck_max_center_mismatch_px"] == 96.0
    assert payload["tuning"]["motion_min_displacement"] == 0.002
    assert payload["tuning"]["motion_max_still_ratio"] == 0.8
    assert payload["tuning"]["motion_min_transitions"] == 4
    assert payload["model_details"]["human_face"]["enabled"] is True
    assert payload["model_details"]["human_face"]["ready"] is True
    assert payload["model_details"]["human_face"]["enforced"] is True
    assert payload["tuning"]["human_face_threshold"] == 0.55
    assert payload["model_details"]["deepfake"]["enabled"] is True
    assert payload["model_details"]["deepfake"]["ready"] is True
    assert payload["model_details"]["deepfake"]["enforced"] is True
    assert payload["tuning"]["deepfake_threshold"] == 0.65
    assert payload["tuning"]["proof_minimum_confidence"] == 0.35


def test_create_session_supersedes_existing_active_session(client: TestClient) -> None:
    first_response = client.post("/api/sessions", json=_session_payload("0xrestart-wallet"))
    second_response = client.post("/api/sessions", json=_session_payload("0xrestart-wallet"))

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    first_session = first_response.json()
    second_session = second_response.json()

    assert first_session["session_id"] != second_session["session_id"]

    first_record = client.get(f"/api/sessions/{first_session['session_id']}")
    assert first_record.status_code == 200
    assert first_record.json()["status"] == "expired"

    second_record = client.get(f"/api/sessions/{second_session['session_id']}")
    assert second_record.status_code == 200
    assert second_record.json()["status"] == "created"


def test_calibration_append_persists_ndjson_row(client: TestClient) -> None:
    response = client.post(
        "/api/calibration/append",
        json={
            "record": {
                "sample_id": "sess_auto_saved",
                "label": "human",
                "challenge_type": "open_mouth",
                "status": "verified",
                "human": True,
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved"] is True
    assert payload["sample_id"] == "sess_auto_saved"

    output_path = client.app.state.session_service.calibration_output_path
    saved_text = output_path.read_text(encoding="utf-8")
    assert '"sample_id": "sess_auto_saved"' in saved_text

    admin_response = client.post(
        "/api/admin/calibration/append",
        json={"record": {"sample_id": "sess_admin_saved", "label": "human"}},
    )
    assert admin_response.status_code == 200


def test_attack_matrix_append_persists_ndjson_row(client: TestClient) -> None:
    response = client.post(
        "/api/attack-matrix/append",
        json={
            "record": {
                "sample_id": "sess_attack_saved",
                "label": "spoof",
                "attack_type": "screen_replay",
                "challenge_type": "turn_right",
                "status": "failed",
                "human": False,
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved"] is True
    assert payload["sample_id"] == "sess_attack_saved"

    output_path = client.app.state.session_service.attack_matrix_output_path
    saved_text = output_path.read_text(encoding="utf-8")
    assert '"attack_type": "screen_replay"' in saved_text

    admin_response = client.post(
        "/api/admin/attack-matrix/append",
        json={"record": {"sample_id": "sess_attack_admin_saved", "attack_type": "print"}},
    )
    assert admin_response.status_code == 200


def test_admin_evaluate_frame_returns_stage_outputs(client: TestClient) -> None:
    response = client.post(
        "/api/admin/evaluate/frame",
        json={
            "challenge_type": "open_mouth",
            "mode": "full",
            "frame": {
                "frame_index": 0,
                "metadata": {
                    "force_face_detected": True,
                    "force_quality_pass": True,
                    "force_spoof_score": 0.04,
                },
                "landmarks": {
                    "mouth_open": True,
                    "point_count": 478,
                    "frame_width": 640,
                    "frame_height": 480,
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_for_liveness"] is True
    assert payload["face_detection"]["detected"] is True
    assert payload["quality"]["passed"] is True
    assert payload["human_face"]["enabled"] is True
    assert payload["human_face"]["score"] is not None
    assert payload["antispoof"]["spoof_score"] == 0.04
    assert payload["deepfake"]["enabled"] is True
    assert payload["deepfake"]["frames_processed"] == 1


def test_admin_evaluate_frame_waits_for_models_to_be_ready(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = client.app.state.session_service
    monkeypatch.setattr(
        type(service.face_detector),
        "models_ready",
        property(lambda self: False),
    )

    response = client.post(
        "/api/admin/evaluate/frame",
        json={
            "challenge_type": "smile",
            "mode": "full",
            "frame": {"frame_index": 0, "metadata": {"force_face_detected": True}},
        },
    )

    assert response.status_code == 503
    assert "still loading" in response.json()["detail"]


def test_admin_evaluate_frame_surfaces_human_face_signal(client: TestClient) -> None:
    response = client.post(
        "/api/admin/evaluate/frame",
        json={
            "challenge_type": "smile",
            "mode": "full",
            "frame": {
                "frame_index": 0,
                "metadata": {
                    "force_face_detected": True,
                    "force_quality_pass": True,
                    "force_human_face_score": 0.12,
                    "force_human_face_label": "a cartoon face",
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["human_face"]["enabled"] is True
    assert payload["human_face"]["passed"] is False
    assert payload["human_face"]["score"] == 0.12
    assert payload["human_face"]["top_label"] == "a cartoon face"


def test_admin_evaluate_session_returns_verdict_preview(client: TestClient) -> None:
    response = client.post(
        "/api/admin/evaluate/session",
        json={
            "challenge_type": "turn_right",
            "mode": "full",
            "frames": [
                {
                    "frame_index": index,
                    "metadata": {
                        "force_face_detected": True,
                        "force_quality_pass": True,
                        "force_spoof_score": 0.03,
                        "head_turn": "right",
                    },
                    "landmarks": {
                        "point_count": 478,
                        "frame_width": 640,
                        "frame_height": 480,
                    },
                }
                for index in range(4)
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["frames_processed"] == 4
    assert payload["accepted_frame_indices"] == [0, 1, 2, 3]
    assert payload["liveness"]["passed"] is True
    assert payload["verdict_preview"]["human"] is True
    assert payload["verdict_preview"]["attack_analysis"]["suspected_attack_family"] == "none"
    assert payload["human_face"]["enabled"] is True
    assert payload["deepfake"]["enabled"] is True
    assert payload["deepfake"]["frames_processed"] == 4


def test_websocket_flow_supports_two_step_sequence(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.OPEN_MOUTH, ChallengeType.TURN_RIGHT])
    create_response = client.post("/api/sessions", json=_session_payload("0xverified-wallet"))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        ready_event = websocket.receive_json()
        assert ready_event["type"] == "session_ready"

        last_progress = None
        for challenge in session["challenge_sequence"]:
            for event in _challenge_frames(challenge, spoof_score=0.02):
                challenge_update, progress = _send_frame_and_receive_progress(websocket, event)
                assert challenge_update["type"] == "challenge_update"
                assert progress["type"] == "progress"
                last_progress = progress["payload"]

        assert last_progress is not None
        assert last_progress["challenge_sequence"] == ["open_mouth", "turn_right"]
        assert last_progress["completed_challenges"] == ["open_mouth", "turn_right"]
        assert last_progress["current_challenge_index"] == 1
        assert last_progress["step_status"] == "completed"
        assert last_progress["challenge_type"] == "turn_right"
        assert last_progress["debug"]["antispoof"]["spoof_score"] == 0.02
        assert last_progress["debug"]["antispoof"]["max_spoof_score"] == 0.02
        assert last_progress["debug"]["antispoof"]["preview"] is True

        websocket.send_json({"type": "finalize"})
        processing_event = websocket.receive_json()
        terminal_event = websocket.receive_json()

        assert processing_event["type"] == "processing"
        assert terminal_event["type"] == "verified"
        assert terminal_event["payload"]["human"] is True
        assert terminal_event["payload"]["status"] == "verified"
        assert terminal_event["payload"]["challenge_sequence"] == ["open_mouth", "turn_right"]
        assert terminal_event["payload"]["human_face_enabled"] is True
        assert terminal_event["payload"]["human_face_score"] is not None
        assert terminal_event["payload"]["deepfake_enabled"] is True


def test_legacy_websocket_alias_still_works(client: TestClient) -> None:
    response = client.post("/api/sessions", json=_session_payload("0xlegacy-alias"))
    session = response.json()

    with client.websocket_connect(f"/ws/verify/{session['session_id']}") as websocket:
        ready_event = websocket.receive_json()
        assert ready_event["type"] == "session_ready"


def test_websocket_flow_supports_three_step_sequence(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.NOD_HEAD, ChallengeType.SMILE, ChallengeType.OPEN_MOUTH])
    create_response = client.post("/api/sessions", json=_session_payload("0xthree-step-wallet"))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        for challenge in session["challenge_sequence"]:
            for event in _challenge_frames(challenge, spoof_score=0.03):
                _send_frame_and_receive_progress(websocket, event)

        websocket.send_json({"type": "finalize"})
        assert websocket.receive_json()["type"] == "processing"
        terminal_event = websocket.receive_json()

        assert terminal_event["type"] == "verified"
        assert terminal_event["payload"]["human"] is True
        assert terminal_event["payload"]["challenge_sequence"] == [
            "nod_head",
            "smile",
            "open_mouth",
        ]
        assert terminal_event["payload"]["completed_challenges"] == [
            "nod_head",
            "smile",
            "open_mouth",
        ]


def test_liveness_only_mode_can_pass_despite_spoof_score(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.OPEN_MOUTH, ChallengeType.TURN_RIGHT])
    create_response = client.post("/api/sessions", json=_session_payload("0xliveness-only-wallet"))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        for challenge in session["challenge_sequence"]:
            for event in _challenge_frames(challenge, spoof_score=0.96):
                _send_frame_and_receive_progress(websocket, event)

        websocket.send_json({"type": "finalize", "mode": "liveness_only"})
        assert websocket.receive_json()["type"] == "processing"
        terminal_event = websocket.receive_json()

        assert terminal_event["type"] == "verified"
        assert terminal_event["payload"]["human"] is True
        assert terminal_event["payload"]["evaluation_mode"] == "liveness_only"
        assert terminal_event["payload"]["proof_id"] is None


def test_antispoof_only_mode_can_pass_without_completed_challenge_sequence(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.TURN_LEFT, ChallengeType.OPEN_MOUTH])
    create_response = client.post("/api/sessions", json=_session_payload("0xantispoof-only-wallet"))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        for index in range(5):
            _send_frame_and_receive_progress(
                websocket,
                _frame_event(
                    {
                        "force_face_detected": True,
                        "force_quality_pass": True,
                        "force_spoof_score": 0.02,
                        "frame_number": index + 1,
                        "frame_width": 640,
                        "frame_height": 480,
                    }
                ),
            )

        websocket.send_json({"type": "finalize", "mode": "antispoof_only"})
        assert websocket.receive_json()["type"] == "processing"
        terminal_event = websocket.receive_json()

        assert terminal_event["type"] == "verified"
        assert terminal_event["payload"]["human"] is True
        assert terminal_event["payload"]["evaluation_mode"] == "antispoof_only"
        assert terminal_event["payload"]["completed_challenges"] == []


def test_deepfake_only_mode_can_pass_without_completed_challenge_sequence(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.TURN_LEFT, ChallengeType.OPEN_MOUTH])
    create_response = client.post("/api/sessions", json=_session_payload("0xdeepfake-only-wallet"))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        for index in range(5):
            _send_frame_and_receive_progress(
                websocket,
                _frame_event(
                    {
                        "force_face_detected": True,
                        "force_quality_pass": True,
                        "force_spoof_score": 0.02,
                        "force_deepfake_score": 0.18,
                        "frame_number": index + 1,
                        "frame_width": 640,
                        "frame_height": 480,
                    }
                ),
            )

        websocket.send_json({"type": "finalize", "mode": "deepfake_only"})
        assert websocket.receive_json()["type"] == "processing"
        terminal_event = websocket.receive_json()

        assert terminal_event["type"] == "verified"
        assert terminal_event["payload"]["human"] is True
        assert terminal_event["payload"]["evaluation_mode"] == "deepfake_only"
        assert terminal_event["payload"]["completed_challenges"] == []
        assert terminal_event["payload"]["deepfake_score"] == 0.18


def test_deepfake_only_mode_fails_when_deepfake_score_is_high(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.TURN_LEFT, ChallengeType.OPEN_MOUTH])
    create_response = client.post("/api/sessions", json=_session_payload("0xdeepfake-only-fail-wallet"))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        for index in range(5):
            _send_frame_and_receive_progress(
                websocket,
                _frame_event(
                    {
                        "force_face_detected": True,
                        "force_quality_pass": True,
                        "force_spoof_score": 0.02,
                        "force_deepfake_score": 0.92,
                        "frame_number": index + 1,
                        "frame_width": 640,
                        "frame_height": 480,
                    }
                ),
            )

        websocket.send_json({"type": "finalize", "mode": "deepfake_only"})
        assert websocket.receive_json()["type"] == "processing"
        terminal_event = websocket.receive_json()

        assert terminal_event["type"] == "failed"
        assert terminal_event["payload"]["human"] is False
        assert terminal_event["payload"]["evaluation_mode"] == "deepfake_only"
        assert terminal_event["payload"]["failure_reason"] == "deepfake_detected"


def test_full_mode_fails_when_human_face_gate_flags_non_human_subject(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.SMILE])
    create_response = client.post("/api/sessions", json=_session_payload("0xhuman-face-fail-wallet"))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        for _ in range(4):
            _send_frame_and_receive_progress(
                websocket,
                _frame_event(
                    {
                        "force_face_detected": True,
                        "force_quality_pass": True,
                        "force_spoof_score": 0.02,
                        "force_human_face_score": 0.08,
                        "force_human_face_label": "a cartoon face",
                        "smile_ratio": 0.5,
                    }
                ),
            )

        websocket.send_json({"type": "finalize", "mode": "full"})
        assert websocket.receive_json()["type"] == "processing"
        terminal_event = websocket.receive_json()

        assert terminal_event["type"] == "failed"
        assert terminal_event["payload"]["human"] is False
        assert terminal_event["payload"]["failure_reason"] == "no_human_face_detected"
        assert (
            terminal_event["payload"]["attack_analysis"]["failure_category"]
            == "non_human_face"
        )
        assert (
            terminal_event["payload"]["attack_analysis"]["suspected_attack_family"]
            == "non_human_face"
        )


def test_full_mode_reports_proof_mint_failure_consistently(client: TestClient) -> None:
    service = client.app.state.session_service
    service.proof_minter.minimum_confidence = 0.99

    _force_sequence(client, [ChallengeType.SMILE])
    create_response = client.post("/api/sessions", json=_session_payload("0xproof-threshold-wallet"))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        for _ in range(4):
            _send_frame_and_receive_progress(
                websocket,
                _frame_event(
                    {
                        "force_face_detected": True,
                        "force_quality_pass": True,
                        "force_spoof_score": 0.02,
                        "force_human_face_score": 0.92,
                        "force_deepfake_score": 0.1,
                        "smile_ratio": 0.5,
                    }
                ),
            )

        websocket.send_json({"type": "finalize", "mode": "full"})
        assert websocket.receive_json()["type"] == "processing"
        terminal_event = websocket.receive_json()

        assert terminal_event["type"] == "failed"
        assert terminal_event["payload"]["failure_reason"] == "confidence_below_threshold"
        assert (
            terminal_event["payload"]["attack_analysis"]["failure_category"]
            == "proof_mint_failure"
        )
        assert (
            terminal_event["payload"]["attack_analysis"]["suspected_attack_family"]
            == "none"
        )


def test_full_mode_terminal_result_exposes_sui_walrus_and_seal_fields(client: TestClient) -> None:
    service = client.app.state.session_service
    tracking_store = _TrackingEvidenceStore()
    service.evidence_store = tracking_store
    service.evidence_encryptor = _TrackingEvidenceEncryptor()
    service.proof_minter = _Phase1ProofMinter(success=True)

    session, terminal_event = _run_full_mode_terminal_event(
        client,
        wallet_address="0xphase1-shape-wallet",
        challenge_sequence=[ChallengeType.SMILE],
    )

    assert terminal_event["type"] == "verified"
    payload = terminal_event["payload"]

    assert payload["proof_id"] == "0xproof_phase1"
    assert payload["transaction_digest"] == "0xtxn_phase1"
    assert payload["walrus_blob_id"] == tracking_store.put_results[0].blob_id
    assert payload["walrus_blob_object_id"] == tracking_store.put_results[0].blob_object_id
    assert payload["seal_identity"] == "seal_phase1_identity"
    assert payload["evidence_schema_version"] == 1
    assert payload["expires_at"].startswith("2026-07-17T00:00:00")

    session_response = client.get(f"/api/sessions/{session['session_id']}")
    assert session_response.status_code == 200
    persisted_result = session_response.json()["result"]
    assert persisted_result["proof_id"] == payload["proof_id"]
    assert persisted_result["transaction_digest"] == payload["transaction_digest"]
    assert persisted_result["walrus_blob_id"] == payload["walrus_blob_id"]
    assert persisted_result["walrus_blob_object_id"] == payload["walrus_blob_object_id"]
    assert persisted_result["seal_identity"] == payload["seal_identity"]
    assert persisted_result["evidence_schema_version"] == payload["evidence_schema_version"]


def test_full_mode_deletes_blob_when_storage_succeeds_but_mint_fails(client: TestClient) -> None:
    service = client.app.state.session_service
    tracking_store = _TrackingEvidenceStore()
    service.evidence_store = tracking_store
    service.evidence_encryptor = _TrackingEvidenceEncryptor()
    service.proof_minter = _Phase1ProofMinter(success=False, reason="mock_mint_failure")

    _, terminal_event = _run_full_mode_terminal_event(
        client,
        wallet_address="0xphase1-cleanup-wallet",
        challenge_sequence=[ChallengeType.SMILE],
    )

    assert terminal_event["type"] == "failed"
    assert terminal_event["payload"]["failure_reason"] == "mock_mint_failure"
    assert tracking_store.deleted_blob_ids == [tracking_store.put_results[0].blob_id]
    assert tracking_store.get_blob(tracking_store.put_results[0].blob_id) is None
    assert terminal_event["payload"]["proof_id"] is None
    if "walrus_blob_id" in terminal_event["payload"]:
        assert terminal_event["payload"]["walrus_blob_id"] is None
    if "walrus_blob_object_id" in terminal_event["payload"]:
        assert terminal_event["payload"]["walrus_blob_object_id"] is None


def test_order_enforcement_prevents_later_step_from_counting_early(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.TURN_LEFT, ChallengeType.OPEN_MOUTH])
    create_response = client.post("/api/sessions", json=_session_payload("0xorder-wallet"))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        early_progress = None
        for event in _challenge_frames("open_mouth", spoof_score=0.02):
            _, progress = _send_frame_and_receive_progress(websocket, event)
            early_progress = progress["payload"]

        assert early_progress is not None
        assert early_progress["current_challenge_index"] == 0


def test_landmark_spotcheck_rejects_mismatched_landmark_telemetry(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.TURN_LEFT, ChallengeType.OPEN_MOUTH])
    create_response = client.post("/api/sessions", json=_session_payload("0xspotcheck-wallet"))
    session = create_response.json()

    mismatched_landmarks = {
        "head_turn": "left",
        "nose_tip_x": 0.88,
        "nose_tip_y": 0.18,
        "left_eye_outer_x": 0.80,
        "left_eye_outer_y": 0.12,
        "right_eye_outer_x": 0.96,
        "right_eye_outer_y": 0.12,
        "mouth_left_x": 0.84,
        "mouth_left_y": 0.28,
        "mouth_right_x": 0.92,
        "mouth_right_y": 0.28,
    }
    metadata = {
        "force_face_detected": True,
        "force_quality_pass": True,
        "face_bbox": {
            "x": 160,
            "y": 120,
            "width": 320,
            "height": 240,
        },
        "frame_width": 640,
        "frame_height": 480,
    }

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        blocked_progress = None
        for _ in range(4):
            challenge_update, progress = _send_frame_and_receive_progress(
                websocket,
                _frame_event_with_landmarks(metadata, mismatched_landmarks),
            )
            assert challenge_update["payload"]["current_challenge_index"] == 0
            blocked_progress = progress["payload"]

        assert blocked_progress is not None
        assert blocked_progress["current_challenge_index"] == 0
        assert blocked_progress["completed_challenges"] == []
        assert blocked_progress["debug"]["landmark_spotcheck"]["enforced"] is True
        assert blocked_progress["debug"]["landmark_spotcheck"]["passed"] is False
        assert (
            blocked_progress["message"]
            == "Landmark telemetry does not match the detected face position"
        )

        turn_progress = None
        for event in _challenge_frames("turn_left", spoof_score=0.02):
            _, progress = _send_frame_and_receive_progress(websocket, event)
            turn_progress = progress
        assert turn_progress is not None
        assert turn_progress["payload"]["current_challenge_index"] == 1
        assert turn_progress["payload"]["completed_challenges"] == ["turn_left"]
        assert turn_progress["payload"]["challenge_type"] == "open_mouth"


def test_landmark_spotcheck_becomes_enforced_after_landmark_event(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.TURN_LEFT, ChallengeType.OPEN_MOUTH])
    create_response = client.post("/api/sessions", json=_session_payload("0xspotcheck-enforced-wallet"))
    session = create_response.json()

    frame_metadata = {
        "force_face_detected": True,
        "force_quality_pass": True,
        "face_bbox": {
            "x": 160,
            "y": 120,
            "width": 320,
            "height": 240,
        },
        "frame_width": 640,
        "frame_height": 480,
        "head_turn": "left",
    }
    aligned_landmarks = {
        "head_turn": "left",
        "nose_tip_x": 0.50,
        "nose_tip_y": 0.48,
        "left_eye_outer_x": 0.42,
        "left_eye_outer_y": 0.44,
        "right_eye_outer_x": 0.58,
        "right_eye_outer_y": 0.44,
        "mouth_left_x": 0.45,
        "mouth_left_y": 0.58,
        "mouth_right_x": 0.55,
        "mouth_right_y": 0.58,
    }

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        challenge_update, frame_progress = _send_frame_and_receive_progress(
            websocket,
            _frame_event(frame_metadata),
        )
        assert challenge_update["payload"]["current_challenge_index"] == 0
        assert frame_progress["payload"]["debug"]["landmark_spotcheck"]["enforced"] is False

        websocket.send_json(
            {
                "type": "landmarks",
                "landmarks": aligned_landmarks,
                "metadata": {
                    "frame_width": 640,
                    "frame_height": 480,
                    "head_turn": "left",
                },
            }
        )
        landmark_progress = websocket.receive_json()

        assert landmark_progress["type"] == "progress"
        assert landmark_progress["payload"]["debug"]["landmark_spotcheck"]["enforced"] is True
        assert landmark_progress["payload"]["debug"]["landmark_spotcheck"]["passed"] is True


def test_sequence_step_requires_configured_hold_window(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.TURN_RIGHT, ChallengeType.SMILE])
    client.app.state.session_service.minimum_step_frames = 6
    create_response = client.post("/api/sessions", json=_session_payload("0xhold-wallet"))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        for _ in range(4):
            _, progress = _send_frame_and_receive_progress(
                websocket,
                _frame_event(
                    {
                        "force_face_detected": True,
                        "force_quality_pass": True,
                        "force_spoof_score": 0.02,
                        "head_turn": "right",
                    }
                ),
            )

        assert progress["payload"]["current_challenge_index"] == 0
        assert progress["payload"]["completed_challenges"] == []
        assert progress["payload"]["step_status"] == "active"

        for _ in range(2):
            _, progress = _send_frame_and_receive_progress(
                websocket,
                _frame_event(
                    {
                        "force_face_detected": True,
                        "force_quality_pass": True,
                        "force_spoof_score": 0.02,
                        "head_turn": "right",
                    }
                ),
            )

        assert progress["payload"]["current_challenge_index"] == 1
        assert progress["payload"]["completed_challenges"] == ["turn_right"]
        assert progress["payload"]["challenge_type"] == "smile"


def test_quality_gate_blocks_progress_until_good_frame_arrives(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.TURN_RIGHT, ChallengeType.SMILE])
    create_response = client.post("/api/sessions", json=_session_payload("0xquality-wallet"))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        for _ in range(4):
            _, progress = _send_frame_and_receive_progress(
                websocket,
                _frame_event(
                    {
                        "force_face_detected": True,
                        "force_spoof_score": 0.02,
                        "force_quality_pass": False,
                        "force_quality_issue": "frame_too_blurry",
                        "force_quality_feedback": "Hold still so the camera can focus",
                        "head_turn": "right",
                    }
                ),
            )

        assert progress["payload"]["current_challenge_index"] == 0
        assert progress["payload"]["completed_challenges"] == []
        assert progress["payload"]["debug"]["quality"]["passed"] is False
        assert progress["payload"]["message"] == "Hold still so the camera can focus"

        for _ in range(4):
            _, progress = _send_frame_and_receive_progress(
                websocket,
                _frame_event(
                    {
                        "force_face_detected": True,
                        "force_spoof_score": 0.02,
                        "force_quality_pass": True,
                        "head_turn": "right",
                    }
                ),
            )

        assert progress["payload"]["current_challenge_index"] == 1
        assert progress["payload"]["completed_challenges"] == ["turn_right"]
        assert progress["payload"]["debug"]["quality"]["passed"] is True


def test_websocket_flow_emits_failed_terminal_event_for_spoof(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.BLINK_TWICE, ChallengeType.TURN_RIGHT])
    create_response = client.post("/api/sessions", json=_session_payload("0xspoof-wallet"))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        for challenge in session["challenge_sequence"]:
            for event in _challenge_frames(challenge, spoof_score=0.96):
                _send_frame_and_receive_progress(websocket, event)

        websocket.send_json({"type": "finalize"})
        processing_event = websocket.receive_json()
        terminal_event = websocket.receive_json()

        assert processing_event["type"] == "processing"
        assert terminal_event["type"] == "failed"
        assert terminal_event["payload"]["human"] is False
        assert terminal_event["payload"]["status"] == "failed"
        assert terminal_event["payload"]["failure_reason"] == "spoof_detected"
        assert terminal_event["payload"]["attack_analysis"]["suspected_attack_family"] == "presentation_attack"
        assert terminal_event["payload"]["attack_analysis"]["presentation_attack_detected"] is True
        assert terminal_event["payload"]["attack_analysis"]["deepfake_detected"] is False


def test_terminal_event_marks_combined_attack_signals_when_both_models_flag(client: TestClient) -> None:
    _force_sequence(client, [ChallengeType.OPEN_MOUTH, ChallengeType.TURN_RIGHT])
    create_response = client.post("/api/sessions", json=_session_payload("0xcombined-attack-wallet"))
    session = create_response.json()

    with client.websocket_connect(session["ws_url"]) as websocket:
        assert websocket.receive_json()["type"] == "session_ready"

        for challenge in session["challenge_sequence"]:
            for event in _challenge_frames(challenge, spoof_score=0.96):
                event["metadata"]["force_deepfake_score"] = 0.91
                _send_frame_and_receive_progress(websocket, event)

        websocket.send_json({"type": "finalize"})
        assert websocket.receive_json()["type"] == "processing"
        terminal_event = websocket.receive_json()

        assert terminal_event["type"] == "failed"
        assert terminal_event["payload"]["attack_analysis"]["suspected_attack_family"] == "combined_attack_signals"
        assert terminal_event["payload"]["attack_analysis"]["presentation_attack_detected"] is True
        assert terminal_event["payload"]["attack_analysis"]["deepfake_detected"] is True
