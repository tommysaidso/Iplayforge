"""
iplayForge license + free-trial gate — Mac port of the Windows plugin's
licensing.py + trial gate (D:\\OSTERTOG_Music\\iplay_plugin\\).

Same HMAC-SHA256 scheme, same SIGNING_SECRET (IPLAY_LICENSE_SECRET), same
~/.iplay/ paths — a license minted by issue_license.py for the Windows
plugin verifies here unchanged, and vice versa. This app has no other
auth (api/auth.py is a local-user stub, no real login), so this module is
the entire gate.

Ben, 2026-09-27: "if the person really wanting to try they will sign up its
free and download the simple acestep system... allows them to play that
little piece but only that, unless they subscribe or pay for the rig in
full." One song, ever, per install: short, watermarked, plain text2music
only (no cover/retake/repaint/extend/lego/edit tasks). Costs nothing to
offer — it runs on the visitor's own Mac GPU, not Ben's.
"""
from __future__ import annotations
import hmac, hashlib, json, base64, time, os, pathlib, platform, uuid, logging

SIGNING_SECRET = os.environ.get(
    "IPLAY_LICENSE_SECRET",
    "D6dc2B5mqx-rEHmLgA4Ms8bFNgPN3sbZ3cvELDjrCs8"  # dev secret — must match issue_license.py in production
).encode()

PAID_PLANS = {"songwriter", "composer", "studio", "founder"}

LICENSE_PATH = pathlib.Path(os.environ.get(
    "IPLAY_LICENSE_PATH", str(pathlib.Path.home() / ".iplay" / "license.key")
))
TRIAL_PATH = pathlib.Path(os.environ.get(
    "IPLAY_TRIAL_PATH", str(pathlib.Path.home() / ".iplay" / "trial_used.json")
))
TRIAL_DURATION_S = 20   # "that little piece" — vs. up to 240s for a licensed build


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def machine_id() -> str:
    raw = f"{uuid.getnode()}-{platform.node()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def verify_license(license_str: str) -> tuple[bool, str, dict]:
    """Verify a license offline. Returns (ok, reason, payload)."""
    try:
        payload_enc, sig_enc = license_str.strip().split(".", 1)
    except ValueError:
        return False, "malformed license", {}

    expected = hmac.new(SIGNING_SECRET, payload_enc.encode(), hashlib.sha256).digest()
    try:
        provided = _b64d(sig_enc)
    except Exception:
        return False, "bad signature encoding", {}
    if not hmac.compare_digest(expected, provided):
        return False, "invalid signature — license forged or tampered", {}

    try:
        payload = json.loads(_b64d(payload_enc))
    except Exception:
        return False, "corrupt payload", {}

    now = int(time.time())
    if payload.get("expires", 0) < now:
        return False, "license expired", payload
    if payload.get("plan") not in PAID_PLANS:
        return False, f"plan '{payload.get('plan')}' is not a paid tier", payload
    locked = payload.get("machine")
    if locked and locked != machine_id():
        return False, "license is locked to a different machine", payload

    return True, "valid", payload


def install_license(license_str: str) -> tuple[bool, str, dict]:
    """Validate then persist a license the user pasted/activated."""
    ok, reason, payload = verify_license(license_str)
    if not ok:
        return ok, reason, payload
    LICENSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LICENSE_PATH.write_text(license_str.strip(), encoding="utf-8")
    return True, "activated", payload


def load_installed_license() -> tuple[bool, str, dict]:
    """Read + verify the license file on disk."""
    if not LICENSE_PATH.exists():
        return False, "no license installed — activate with your paid account", {}
    try:
        lic = LICENSE_PATH.read_text(encoding="utf-8").strip()
    except Exception as e:
        return False, f"could not read license: {e}", {}
    return verify_license(lic)


# ── free trial ───────────────────────────────────────────────────────────────

def trial_used() -> bool:
    return TRIAL_PATH.exists()


def mark_trial_used() -> None:
    TRIAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRIAL_PATH.write_text(json.dumps({"used_at": int(time.time())}), encoding="utf-8")


def tag_trial_preview(path: pathlib.Path) -> None:
    """Metadata-only watermark on the trial output — audio bytes untouched.
    Handles both .wav (ACE-Step's native output here) and .mp3, since this
    pipeline writes wav_path but other export paths in the app may re-encode
    to mp3 — tag whichever extension actually lands on disk."""
    try:
        suffix = path.suffix.lower()
        note = ("Free one-time preview from the iplay local studio (iplayForge). "
                "Subscribe or buy the rig for unlimited, unwatermarked songs — "
                "iplay.studio/#access")
        if suffix == ".mp3":
            from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, COMM
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                tags = ID3()
            tags["TIT2"] = TIT2(encoding=3, text="iplay.studio — free preview")
            tags["COMM"] = COMM(encoding=3, lang="eng", desc="", text=note)
            tags.save(path, v2_version=3)
        elif suffix == ".wav":
            from mutagen.wave import WAVE
            from mutagen.id3 import ID3, TIT2, COMM
            audio = WAVE(path)
            if audio.tags is None:
                audio.add_tags()
            audio.tags.add(TIT2(encoding=3, text="iplay.studio — free preview"))
            audio.tags.add(COMM(encoding=3, lang="eng", desc="", text=note))
            audio.save()
        else:
            logging.warning("[trial] unrecognized audio extension %s — no watermark tag applied", suffix)
    except Exception as e:
        logging.warning("[trial] watermark tagging failed (non-fatal): %s", e)
