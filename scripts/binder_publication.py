"""Fingerprint validated binder proofs and publish one recoverable Slack file.

Network operations run only from the gated, successful main push job. No API
response bodies, tokens, or temporary upload URLs are logged or persisted.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY = "futuroptimist/aquiloop"
CHANNEL = "C0C8T7FDAAC"
TEAM = "T0C80NYUHHP"
STATE_BRANCH = "binder-publication-state"
PDF_NAME = "aquiloop-binder-red-wiggler-draft.pdf"
PAGE_COUNT = 48
SCHEMA = "aquiloop-rendered-binder-v1"

# Only constants from these tables may reach publication diagnostics.
SLACK_METHODS = frozenset({"auth.test", "files.info", "files.getUploadURLExternal",
                           "files.completeUploadExternal", "upload_bytes"})
SLACK_HINTS = {
    "api_error": "Review the method documentation and installed app configuration.",
    "missing_scope": "Verify the installed token's effective file scopes; configured scopes alone are not proof.",
    "invalid_auth": "Have the owner verify the installed credential and network policy without logging it.",
    "not_authed": "Have the owner verify the configured bot credential without logging it.",
    "not_allowed_token_type": "Verify the installed credential is an approved bot token.",
    "token_revoked": "Have the owner verify the app installation and credential status.",
    "token_expired": "Have the owner verify the app installation and credential status.",
    "account_inactive": "Have the owner verify the app and workspace are active.",
    "no_permission": "Verify installed file permissions and target channel membership.",
    "channel_not_found": "Verify the configured target channel and bot membership.",
    "not_in_channel": "Verify bot membership in the configured target channel.",
    "file_not_found": "Reconcile the pending file with the owner; do not allocate a replacement.",
    "invalid_arguments": "Check the method's required arguments and payload types.",
    "missing_argument": "Check the method's required arguments and nonzero file length.",
    "ratelimited": "Wait for rate limits to recover, then rerun to reconcile the checkpoint.",
    "internal_error": "Wait for service recovery, then rerun to reconcile the checkpoint.",
    "service_unavailable": "Wait for service recovery, then rerun to reconcile the checkpoint.",
    "file_uploads_disabled": "Have the owner inspect workspace file upload policy.",
    "file_uploads_except_images_disabled": "Have the owner inspect workspace PDF upload policy.",
    "file_type_not_allowed": "Have the owner inspect workspace PDF upload policy.",
    "file_upload_size_restricted": "Check the PDF size against workspace upload policy.",
    "storage_limit_reached": "Have the owner inspect workspace file storage limits.",
    "http_error": "Check service availability and access policy, then reconcile before retrying.",
    "transport_error": "The outcome may be uncertain; rerun only through checkpoint reconciliation.",
    "invalid_response": "Check service health; reconcile the checkpoint before retrying.",
}


class SlackError(RuntimeError):
    def __init__(self, method, code):
        method = method if isinstance(method, str) and method in SLACK_METHODS else "unknown_method"
        code = code if isinstance(code, str) and code in SLACK_HINTS else "api_error"
        super().__init__(f"Slack {method} failed ({code}). {SLACK_HINTS[code]}")


SAFE_ERRORS = {
    "page_count": f"Expected the validated {PAGE_COUNT}-page red-wiggler binder and proofs",
    "proof_order": "Proof page order is incomplete",
    "geometry": "Unexpected page geometry",
    "pdf_action": "Unsupported PDF action",
    "pdf_destination": "Unsupported internal PDF destination",
    "provenance": "Artifact provenance or PDF digest mismatch",
    "upload_host": "Unexpected Slack upload host",
    "workspace": "Slack workspace mismatch",
    "checkpoint": "Invalid publication checkpoint; owner reconciliation required",
    "history": "Diverged publication history; owner reconciliation required",
    "trust": "Only trusted repository main push builds can publish",
    "manifest": "Binder manifest failed; verify local PDF, proofs and build provenance environment",
    "unexpected": "Binder command failed; verify validated inputs and configured environment",
}


class SafeError(ValueError):
    """Deliberate failures select fixed messages, never arbitrary exception text."""
    def __init__(self, code):
        code = code if isinstance(code, str) and code in SAFE_ERRORS else "unexpected"
        super().__init__(SAFE_ERRORS[code])


def slack_failure_code(status):
    return {"uncertain": "transport_error", "invalid_response": "invalid_response",
            429: "ratelimited"}.get(status, "http_error")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def fingerprint(pdf, proof_dir):
    """Hash ordered RGB pixels, text and link targets, excluding PDF metadata.

    Uses the build's complete pinned 150-DPI color proofs; PNG container metadata
    and PDF CreationDate/ModDate/document IDs are deliberately irrelevant.
    """
    from PIL import Image
    from pypdf import PdfReader

    reader = PdfReader(pdf)
    proofs = sorted(proof_dir.glob("page-*.png"),
                    key=lambda path: int(path.stem.split("-")[-1]))
    if len(reader.pages) != PAGE_COUNT or len(proofs) != PAGE_COUNT:
        raise SafeError("page_count")
    pages = []
    for number, (page, proof) in enumerate(zip(reader.pages, proofs), 1):
        if int(proof.stem.split("-")[-1]) != number:
            raise SafeError("proof_order")
        if list(page.mediabox) != [0, 0, 612, 792] or list(page.cropbox) != [0, 0, 612, 792] or page.get("/Rotate", 0):
            raise SafeError("geometry")
        links = []
        for annotation in page.get("/Annots", []):
            item = annotation.get_object()
            action = item.get("/A")
            if action:
                action = action.get_object()
                # Binder links are URI links. Fail closed on new interaction types.
                if action.get("/S") != "/URI":
                    raise SafeError("pdf_action")
                links.append(str(action.get("/URI", "")))
            elif item.get("/Dest"):
                raise SafeError("pdf_destination")
        with Image.open(proof) as source:
            image = source.convert("RGB")
            pages.append({"size": image.size, "pixels": digest(image.tobytes()),
                          "text": page.extract_text(), "links": links})
    return digest(encoded({"schema": SCHEMA, "pages": pages}))


def manifest(pdf, proof_dir):
    return {"schema": SCHEMA, "content_sha256": fingerprint(pdf, proof_dir),
            "pdf_sha256": digest(pdf.read_bytes()), "pdf_name": PDF_NAME,
            "repository": REPOSITORY, "commit": os.environ["GITHUB_SHA"],
            "run_id": os.environ["GITHUB_RUN_ID"],
            "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"], "pages": PAGE_COUNT}


def validate(bundle):
    record = json.loads((bundle / "provenance.json").read_text())
    pdf = bundle / PDF_NAME
    if (record.get("schema") != SCHEMA or record.get("repository") != REPOSITORY
            or record.get("commit") != os.environ["GITHUB_SHA"]
            or record.get("run_id") != os.environ["GITHUB_RUN_ID"]
            or record.get("pdf_name") != PDF_NAME or record.get("pages") != PAGE_COUNT
            or not re.fullmatch(r"[0-9a-f]{64}", record.get("content_sha256", ""))
            or record.get("pdf_sha256") != digest(pdf.read_bytes())
            or not pdf.read_bytes().startswith(b"%PDF-")):
        raise SafeError("provenance")
    return record, pdf.read_bytes()


class ApiError(RuntimeError):
    def __init__(self, service, status):
        self.status = status
        super().__init__(f"{service} request failed ({status}); rerun to reconcile")


def request(url, method="GET", data=None, token=None, raw=False, form=False):
    headers = {"User-Agent": "aquiloop-binder-publication"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        if raw:
            headers["Content-Type"] = "application/octet-stream"
        elif form:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            data = urllib.parse.urlencode(data).encode("utf-8")
        else:
            headers["Content-Type"] = "application/json"
            data = encoded(data)
    # Do not follow redirects carrying Authorization or log signed upload URLs.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    try:
        with urllib.request.build_opener(NoRedirect).open(
                urllib.request.Request(url, data=data, headers=headers, method=method), timeout=45) as response:
            body = response.read()
            return None if raw else json.loads(body)
    except urllib.error.HTTPError as error:
        raise ApiError("HTTP", error.code) from None
    except (urllib.error.URLError, TimeoutError):
        raise ApiError("Transport", "uncertain") from None
    except (ValueError, UnicodeError):
        raise ApiError("Response", "invalid_response") from None


class Services:
    def __init__(self):
        self.revision = None

    def github(self, path, method="GET", data=None):
        return request(f"https://api.github.com/repos/{REPOSITORY}/{path}", method,
                       data, os.environ["GH_TOKEN"])

    def slack(self, method, data):
        url = f"https://slack.com/api/{method}"
        verb = "POST"
        if method == "files.info":
            url += "?" + urllib.parse.urlencode(data)
            verb, data = "GET", None
        try:
            # Match Slack's synchronous SDK wire format for ticket allocation.
            # JSON is documented too; this is a scoped compatibility adjustment.
            result = request(url, verb, data, os.environ["SLACK_BOT_TOKEN"],
                             form=method == "files.getUploadURLExternal")
        except ApiError as error:
            raise SlackError(method, slack_failure_code(error.status)) from None
        if not isinstance(result, dict):
            raise SlackError(method, "invalid_response")
        if not result.get("ok"):
            raise SlackError(method, result.get("error"))
        return result

    def load(self):
        try:
            item = self.github(f"contents/publication.json?ref={STATE_BRANCH}")
        except ApiError as error:
            if error.status != 404:
                raise
            return None
        self.revision = item["sha"]
        return json.loads(base64.b64decode(item["content"]))

    def save(self, record):
        if self.revision is None:
            try:
                self.github(f"git/ref/heads/{STATE_BRANCH}")
            except ApiError as error:
                if error.status != 404:
                    raise
                self.github("git/refs", "POST", {"ref": f"refs/heads/{STATE_BRANCH}",
                            "sha": record["commit"]})
        body = {"message": "Record binder publication checkpoint", "branch": STATE_BRANCH,
                "content": base64.b64encode(encoded(record)).decode()}
        if self.revision:
            body["sha"] = self.revision
        saved = self.github("contents/publication.json", "PUT", body)
        self.revision = saved["content"]["sha"]

    def relation(self, previous, current):
        return self.github(f"compare/{previous}...{current}")["status"]

    def upload(self, pdf):
        ticket = self.slack("files.getUploadURLExternal", {"filename": PDF_NAME, "length": len(pdf)})
        url = urllib.parse.urlparse(ticket["upload_url"])
        if url.scheme != "https" or url.hostname != "files.slack.com" or url.username or url.password:
            raise SafeError("upload_host")
        try:
            request(ticket["upload_url"], "POST", pdf, raw=True)
        except ApiError as error:
            raise SlackError("upload_bytes", slack_failure_code(error.status)) from None
        return ticket["file_id"]

    def shared(self, file_id):
        file = self.slack("files.info", {"file": file_id})["file"]
        return any(CHANNEL in file.get("shares", {}).get(kind, {}) for kind in ("public", "private"))

    def complete(self, record):
        run = f"https://github.com/{REPOSITORY}/actions/runs/{record['run_id']}"
        self.slack("files.completeUploadExternal", {
            "files": [{"id": record["file_id"], "title": "Aquiloop care binder — draft"}],
            "channel_id": CHANNEL,
            "initial_comment": f"Updated {record['pages']}-page care binder (draft). Build: {run}\n"
                               f"Commit: {record['commit']}\nPDF SHA-256: {record['pdf_sha256']}\n"
                               f"Content fingerprint: {record['content_sha256']}"})


def publish(api, record, pdf):
    if api.slack("auth.test", {})["team_id"] != TEAM:
        raise SafeError("workspace")
    previous = api.load()
    if previous:
        if previous.get("status") not in ("pending", "published") or not re.fullmatch(r"F[A-Z0-9]+", previous.get("file_id", "")):
            raise SafeError("checkpoint")
        if previous["status"] == "pending":
            # A crash after sharing is reconciled before any new file is allocated.
            # Slack completion is a one-shot operation on this persisted file ID.
            if not api.shared(previous["file_id"]):
                api.complete(previous)
            previous = dict(previous, status="published")
            api.save(previous)
        relation = api.relation(previous.get("checked_commit", previous["commit"]), record["commit"])
        if relation == "behind":
            return "Skipped stale build"
        if relation not in ("ahead", "identical"):
            raise SafeError("history")
        if previous["content_sha256"] == record["content_sha256"]:
            api.save(dict(previous, checked_commit=record["commit"]))
            return "Unchanged binder content"
    file_id = api.upload(pdf)
    pending = dict(record, file_id=file_id, status="pending")
    # A failed/uncertain checkpoint write MUST abort before channel publication.
    api.save(pending)
    api.complete(pending)
    api.save(dict(pending, status="published"))
    return "Published binder PDF"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("manifest", "publish"))
    parser.add_argument("--bundle", type=Path, default=Path("build/binder/publication"))
    args = parser.parse_args()
    if args.command == "manifest":
        try:
            pdf = args.bundle / PDF_NAME
            record = manifest(pdf, args.bundle.parent / "publication-color")
            (args.bundle / "provenance.json").write_bytes(encoded(record))
        except SafeError:
            raise
        except Exception:
            raise SafeError("manifest") from None
    else:
        if (os.environ.get("GITHUB_EVENT_NAME") != "push"
                or os.environ.get("GITHUB_REF") != "refs/heads/main"
                or os.environ.get("GITHUB_REPOSITORY") != REPOSITORY):
            raise SafeError("trust")
        record, pdf = validate(args.bundle)
        print(publish(Services(), record, pdf))


def cli():
    try:
        main()
    except (SlackError, SafeError) as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    except Exception:
        # No traceback: even parser/transport exceptions may contain response data.
        print(f"::error::{SAFE_ERRORS['unexpected']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(cli())
