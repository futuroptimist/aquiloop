import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import binder_publication as publication


def record(content="a", commit="1"):
    return {"schema": publication.SCHEMA, "repository": publication.REPOSITORY,
            "commit": commit * 40, "content_sha256": content * 64,
            "pdf_sha256": "b" * 64, "run_id": "123", "run_attempt": "1",
            "pdf_name": publication.PDF_NAME, "pages": 31}


class FakeServices:
    def __init__(self):
        self.state = None
        self.uploads = 0
        self.posts = 0
        self.is_shared = False
        self.team = publication.TEAM
        self.commits = []
        self.status = "ahead"
        self.fail_save = False
        self.uncertain_complete = False

    def slack(self, method, data):
        return {"team_id": self.team}

    def load(self):
        return copy.deepcopy(self.state)

    def save(self, value):
        if self.fail_save:
            raise RuntimeError("checkpoint unavailable")
        self.state = copy.deepcopy(value)

    def relation(self, previous, current):
        self.commits.append((previous, current))
        return self.status

    def upload(self, pdf):
        self.uploads += 1
        self.is_shared = False
        return f"F{self.uploads}"

    def shared(self, file):
        return self.is_shared

    def complete(self, value):
        if not self.is_shared:
            self.posts += 1
            self.is_shared = True
        if self.uncertain_complete:
            raise RuntimeError("response lost")


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeServices()

    def publish(self, value=None):
        return publication.publish(self.api, value or record(), b"%PDF-fixture")

    def test_first_upload_and_repeat(self):
        self.publish()
        self.publish()
        self.assertEqual((self.api.uploads, self.api.posts), (1, 1))
        self.assertEqual(self.api.state["status"], "published")

    def test_changed_content_and_reversion_are_published(self):
        self.publish()
        self.publish(record("c", "2"))
        self.publish(record("a", "3"))
        self.assertEqual(self.api.posts, 3)

    def test_uncertain_share_recovers_without_duplicate(self):
        self.api.uncertain_complete = True
        with self.assertRaises(RuntimeError):
            self.publish()
        self.assertEqual(self.api.state["status"], "pending")
        self.api.uncertain_complete = False
        self.publish()
        self.assertEqual((self.api.uploads, self.api.posts), (1, 1))

    def test_checkpoint_failure_never_shares(self):
        self.api.fail_save = True
        with self.assertRaises(RuntimeError):
            self.publish()
        self.assertEqual(self.api.posts, 0)

    def test_crash_before_complete_resumes_same_file(self):
        self.api.state = dict(record(), file_id="F1", status="pending")
        self.publish()
        self.assertEqual((self.api.uploads, self.api.posts), (0, 1))

    def test_unresolvable_pending_blocks_new_content(self):
        self.api.state = dict(record(), file_id="F1", status="pending")
        with patch.object(self.api, "shared", side_effect=RuntimeError("unknown file")):
            with self.assertRaises(RuntimeError):
                self.publish(record("c", "2"))
        self.assertEqual(self.api.uploads, 0)

    def test_wrong_workspace_never_uploads(self):
        self.api.team = "wrong"
        with self.assertRaises(ValueError):
            self.publish()
        self.assertEqual(self.api.uploads, 0)

    def test_older_build_never_regresses_publication(self):
        self.publish()
        self.api.status = "behind"
        self.publish(record("c", "2"))
        self.assertEqual(self.api.posts, 1)

    def test_unchanged_build_advances_high_water_commit(self):
        self.publish()
        self.publish(record("a", "3"))
        self.api.status = "behind"
        self.publish(record("c", "2"))
        self.assertEqual(self.api.commits[-1][0], "3" * 40)
        self.assertEqual(self.api.posts, 1)

    def test_divergence_stops(self):
        self.publish()
        self.api.status = "diverged"
        with self.assertRaises(ValueError):
            self.publish(record("c", "2"))

    def test_untrusted_event_rejected_before_network(self):
        for event, ref, repo in [("pull_request", "refs/heads/main", publication.REPOSITORY),
                                 ("workflow_dispatch", "refs/heads/main", publication.REPOSITORY),
                                 ("push", "refs/heads/feature", publication.REPOSITORY),
                                 ("push", "refs/heads/main", "fork/aquiloop")]:
            with self.subTest(event=event, ref=ref, repo=repo), patch.dict(os.environ, {
                    "GITHUB_EVENT_NAME": event, "GITHUB_REF": ref, "GITHUB_REPOSITORY": repo}), \
                    patch.object(sys, "argv", ["publisher", "publish"]), \
                    patch.object(publication, "Services") as services:
                with self.assertRaises(ValueError):
                    publication.main()
                services.assert_not_called()

    def test_tampered_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            (bundle / publication.PDF_NAME).write_bytes(b"%PDF-tampered")
            (bundle / "provenance.json").write_text(json.dumps(record()))
            with patch.dict(os.environ, {"GITHUB_SHA": "1" * 40, "GITHUB_RUN_ID": "123"}):
                with self.assertRaises(ValueError):
                    publication.validate(bundle)

    def test_file_reconciliation_uses_documented_get_endpoint(self):
        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "test-placeholder"}, clear=True), \
                patch.object(publication, "request", return_value={"ok": True}) as request:
            publication.Services().slack("files.info", {"file": "F1"})
        self.assertEqual(request.call_args.args[:3],
                         ("https://slack.com/api/files.info?file=F1", "GET", None))


class FingerprintTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pdf = self.root / "binder.pdf"
        for number in range(1, 32):
            Image.new("RGB", (4, 4), "white").save(self.root / f"page-{number:02}.png")

    def write_pdf(self, date, link="https://example.com/a"):
        from pypdf import PdfWriter
        from pypdf.annotations import Link
        writer = PdfWriter()
        for _ in range(31):
            writer.add_blank_page(width=612, height=792)
        writer.add_metadata({"/CreationDate": date, "/ModDate": date})
        writer.add_annotation(0, Link(rect=(1, 1, 2, 2), url=link))
        writer.write(self.pdf)

    def fingerprint(self):
        return publication.fingerprint(self.pdf, self.root)

    def test_pdf_and_png_timestamp_metadata_do_not_trigger(self):
        from PIL import Image, PngImagePlugin
        self.write_pdf("D:20261009040000")
        first_bytes = self.pdf.read_bytes()
        first = self.fingerprint()
        self.write_pdf("D:20261009120000")
        info = PngImagePlugin.PngInfo()
        info.add_text("Creation Time", "different")
        Image.new("RGB", (4, 4), "white").save(self.root / "page-01.png", pnginfo=info)
        self.assertNotEqual(first_bytes, self.pdf.read_bytes())
        self.assertEqual(first, self.fingerprint())

    def test_changed_pixels_trigger(self):
        from PIL import Image
        self.write_pdf("date")
        first = self.fingerprint()
        Image.new("RGB", (4, 4), "red").save(self.root / "page-01.png")
        self.assertNotEqual(first, self.fingerprint())

    def test_changed_link_target_triggers(self):
        self.write_pdf("date")
        first = self.fingerprint()
        self.write_pdf("date", "https://example.com/b")
        self.assertNotEqual(first, self.fingerprint())

    def test_missing_proof_rejected(self):
        self.write_pdf("date")
        (self.root / "page-10.png").unlink()
        with self.assertRaises(ValueError):
            self.fingerprint()


if __name__ == "__main__":
    unittest.main()
