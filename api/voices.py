"""House voices — re-sing the current take in one of iplay's two house voices
(male tenor / female mezzo), built with RVC (Applio) on the render fleet.

RVC needs CUDA; there is no Mac-local engine for this, so unlike song
generation (which runs fully on this machine's own GPU), house-voice morph is
the one feature that calls out to a real GPU machine over the network —
same relationship iplay's web demo has to Playtime's ACE-Step, and the
"remote DAW" pattern discussed for a phone client. The engine lives on
SongLab (D:\OSTERTOG_Music\songlab\features\vocal_morph.py), reached here
through its /api/vocal/morph/remote endpoint.

This is a licensed feature, not part of the free trial — a trial user gets
one local song on their own GPU at zero cost to us; house-voice morph spends
real compute on OUR machine, so it's gated the same way builds are.
"""
from __future__ import annotations
import os
from flask import Blueprint, jsonify, request, Response
import requests

from iplay_license import load_installed_license

bp = Blueprint("api_voices", __name__)

MORPH_URL = os.environ.get("IPLAY_MORPH_URL", "http://192.168.1.130:7788").rstrip("/")

VOICES = {
    "house_m": "House Voice M — male tenor",
    "house_f": "House Voice F — female mezzo",
}


def _engine_alive() -> bool:
    """Fast reachability probe (same pattern as generate_relay.py's
    _acestep_alive()) so a resting/offline render box fails in ~2-3s with a
    friendly message instead of a long hang."""
    try:
        r = requests.get(f"{MORPH_URL}/api/vocal/morph/status", timeout=3.0)
        return r.ok and r.json().get("available", False)
    except Exception:
        return False


@bp.route("/list", methods=["GET"])
def list_voices():
    return jsonify({"voices": [{"id": k, "label": v} for k, v in VOICES.items()],
                    "engine_online": _engine_alive()})


@bp.route("/morph", methods=["POST"])
def morph():
    lic_ok, lic_reason, _ = load_installed_license()
    if not lic_ok:
        return jsonify({"error": "House voices need a license — "
                                  "subscribe or buy the rig for unlimited songs.",
                        "reason": "license_required"}), 402

    if "audio" not in request.files:
        return jsonify({"error": "audio file required"}), 400
    voice = request.form.get("voice", "house_f")
    if voice not in VOICES:
        return jsonify({"error": f"unknown voice '{voice}'"}), 400

    if not _engine_alive():
        return jsonify({"error": "The house-voice engine is resting right now — "
                                  "please check back soon.",
                        "reason": "engine_resting"}), 503

    audio = request.files["audio"]
    try:
        r = requests.post(
            f"{MORPH_URL}/api/vocal/morph/remote",
            files={"audio": (audio.filename or "take.wav", audio.stream, audio.mimetype or "audio/wav")},
            data={
                "voice": voice,
                "in_tune": request.form.get("in_tune", 60),
                "voice_amount": request.form.get("voice_amount", 75),
                "protect": request.form.get("protect", 0.33),
                "octave_extra": request.form.get("octave_extra", 0),
            },
            timeout=900,   # RVC inference can genuinely take a while; the fast
                           # engine_alive() check above is what keeps a DOWN
                           # engine from hanging, not this timeout.
        )
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "The house-voice engine is resting right now — "
                                  "please check back soon.",
                        "reason": "engine_resting", "detail": str(e)[:200]}), 503

    if r.status_code != 200:
        return jsonify({"error": r.text[:300] or "Voice engine failed."}), r.status_code

    return Response(r.content, mimetype="audio/wav", headers={
        "X-Octave-Shift": r.headers.get("X-Octave-Shift", ""),
        "X-Voice-Label": r.headers.get("X-Voice-Label", VOICES[voice]),
    })
