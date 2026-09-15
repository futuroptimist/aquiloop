import hashlib, json, shutil, subprocess, tempfile, unittest
from pathlib import Path
from PIL import Image
import sys
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/"scripts"))
import build_binder, prepare_binder_photo

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.entry=ROOT/"binder/entries/sedum-loves-fire"
    def test_draft_selection_and_unselected_record(self):
        catalog, selected=build_binder.validate(self.entry,"draft")
        self.assertEqual(selected,["sedum-draft-placeholder-001"])
        self.assertIn("sedum-unselected-placeholder-002",catalog)
    def test_final_rejects_selected_placeholder_but_not_unselected(self):
        with self.assertRaisesRegex(ValueError,"not final-qualified"): build_binder.validate(self.entry,"final")
        with tempfile.TemporaryDirectory() as td:
            entry=Path(td); data=json.loads((self.entry/"assets.json").read_text())
            data["assets"][0].update(kind="photograph"); data["assets"][0]["source"]["rights"]="CC0-1.0"; data["assets"][0]["path"]="assets/a.jpg"
            (entry/"assets").mkdir(); Image.new("RGB",(990,990)).save(entry/"assets/a.jpg")
            (entry/"assets.json").write_text(json.dumps(data)); (entry/"page.tex").write_text((self.entry/"page.tex").read_text())
            _,selected=build_binder.validate(entry,"final"); self.assertEqual(len(selected),1)
    def test_no_details_and_limit(self):
        page=(self.entry/"page.tex").read_text(); self.assertEqual(build_binder.selections(page)[1],[])
        page=page.replace("details={}","details={a,b,c}")
        with tempfile.TemporaryDirectory() as td:
            entry=Path(td); (entry/"assets.json").write_text((self.entry/"assets.json").read_text()); (entry/"page.tex").write_text(page)
            with self.assertRaisesRegex(ValueError,"at most two"): build_binder.validate(entry,"draft")

    @unittest.skipUnless(shutil.which("lualatex") and shutil.which("pdfinfo"), "LuaLaTeX and Poppler required")
    def test_proof_is_exactly_one_letter_page(self):
        with tempfile.TemporaryDirectory() as td:
            output=Path(td)/"proof.pdf"; build_binder.build("sedum-loves-fire","draft",output)
            info=subprocess.run(["pdfinfo",str(output)],check=True,text=True,capture_output=True).stdout
            self.assertIn("Pages:           1\n", info)
            self.assertRegex(info,r"Page size:\s+612 x 792 pts")

class PrepareTests(unittest.TestCase):
    def test_prepares_without_changing_original_and_rejects_low_resolution(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"synthetic.png"; out=Path(td)/"derived.jpg"
            Image.new("RGB",(1200,1200),(220,80,180)).save(src); before=hashlib.sha256(src.read_bytes()).digest()
            result=prepare_binder_photo.prepare(src,out,"hero",None,False)
            self.assertEqual(before,hashlib.sha256(src.read_bytes()).digest()); self.assertGreaterEqual(result["effective_ppi"],240)
            low=Path(td)/"low.png"; Image.new("RGB",(700,700)).save(low)
            with self.assertRaisesRegex(ValueError,"insufficient"): prepare_binder_photo.prepare(low,Path(td)/"no.jpg","hero",None,False)
    def test_same_file_and_overwrite_require_consent(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"synthetic.png"; Image.new("RGB",(990,990)).save(src)
            with self.assertRaisesRegex(ValueError,"differ"): prepare_binder_photo.prepare(src,src,"hero",None,False)
            out=Path(td)/"exists.jpg"; out.write_bytes(b"x")
            with self.assertRaises(FileExistsError): prepare_binder_photo.prepare(src,out,"hero",None,False)

if __name__ == "__main__": unittest.main()
