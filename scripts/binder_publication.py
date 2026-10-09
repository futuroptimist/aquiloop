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
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY = "futuroptimist/aquiloop"
CHANNEL = "C0C8T7FDAAC"
TEAM = "T0C80NYUHHP"
STATE_BRANCH = "binder-publication-state"
PDF_NAME = "aquiloop-binder-succulents-draft.pdf"
PAGE_COUNT = 41
SCHEMA = "aquiloop-rendered-binder-v1"


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
        raise ValueError(f"Expected the validated {PAGE_COUNT}-page succulent binder and proofs")
    pages = []
    for number, (page, proof) in enumerate(zip(reader.pages, proofs), 1):
        if int(proof.stem.split("-")[-1]) != number:
            raise ValueError("Proof page order is incomplete")
        if list(page.mediabox) != [0, 0, 612, 792] or list(page.cropbox) != [0, 0, 612, 792] or page.get("/Rotate", 0):
            raise ValueError("Unexpected page geometry")
        links = []
        for annotation in page.get("/Annots", []):
            item = annotation.get_object()
            action = item.get("/A")
            if action:
                action = action.get_object()
                # Binder links are URI links. Fail closed on new interaction types.
                if action.get("/S") != "/URI":
                    raise ValueError("Unsupported PDF action")
                links.append(str(action.get("/URI", "")))
            elif item.get("/Dest"):
                raise ValueError("Unsupported internal PDF destination")
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
        raise ValueError("Artifact provenance or PDF digest mismatch")
    return record, pdf.read_bytes()


class ApiError(RuntimeError):
    def __init__(self, service, status):
        self.status = status
        super().__init__(f"{service} request failed ({status}); rerun to reconcile")


def request(url, method="GET", data=None, token=None, raw=False):
    headers = {"User-Agent": "aquiloop-binder-publication"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        headers["Content-Type"] = "application/octet-stream" if raw else "application/json"
        if not raw:
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
        result = request(url, verb, data, os.environ["SLACK_BOT_TOKEN"])
        if not result.get("ok"):
            # Error codes are allowlisted, never dump the potentially sensitive body.
            raise ApiError("Slack", "api_error")
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
            raise ValueError("Unexpected Slack upload host")
        request(ticket["upload_url"], "POST", pdf, raw=True)
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
        raise ValueError("Slack workspace mismatch")
    previous = api.load()
    if previous:
        if previous.get("status") not in ("pending", "published") or not re.fullmatch(r"F[A-Z0-9]+", previous.get("file_id", "")):
            raise ValueError("Invalid publication checkpoint; owner reconciliation required")
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
            raise ValueError("Diverged publication history; owner reconciliation required")
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
        pdf = args.bundle / PDF_NAME
        record = manifest(pdf, args.bundle.parent / "publication-color")
        (args.bundle / "provenance.json").write_bytes(encoded(record))
    else:
        if (os.environ.get("GITHUB_EVENT_NAME") != "push"
                or os.environ.get("GITHUB_REF") != "refs/heads/main"
                or os.environ.get("GITHUB_REPOSITORY") != REPOSITORY):
            raise ValueError("Only trusted repository main push builds can publish")
        record, pdf = validate(args.bundle)
        print(publish(Services(), record, pdf))


if __name__ == "__main__":
    main()
