import unittest
import os
from PIL import Image
from src.backend.media_processor import compress_profile_a, compress_profile_b, purge_cached_media_file, STAGING_DIR
from src.backend.template_factory import DocumentTemplateFactory

class TestFieldFlowMediaAndDocs(unittest.TestCase):

    def setUp(self):
        """Creates a dummy high-resolution raw image for processing tests."""
        self.test_img_path = os.path.join(STAGING_DIR, "test_raw_input.jpg")
        img = Image.new("RGB", (2500, 1500), color="blue")
        img.save(self.test_img_path)

    def test_profile_a_compression(self):
        """Verifies equipment data plate photo is resized to max 1080p and saved cleanly."""
        output_path = compress_profile_a(self.test_img_path, "test_profile_a.jpg")
        self.assertIsNotNone(output_path, "Profile A Failure: Compressed file path was not returned!")
        self.assertTrue(os.path.exists(output_path), "Profile A Failure: Compressed image file missing on disk!")
        
        with Image.open(output_path) as processed_img:
            w, h = processed_img.size
            self.assertLessEqual(w, 1920, f"Profile A Failure: Image width {w} exceeds 1920px cap!")
            self.assertLessEqual(h, 1080, f"Profile A Failure: Image height {h} exceeds 1080px cap!")
        
        purge_cached_media_file("test_profile_a.jpg")

    def test_profile_b_receipt_grayscale(self):
        """Verifies receipt photo is converted to grayscale (Mode L) for accounting contrast."""
        output_path = compress_profile_b(self.test_img_path, "test_profile_b.jpg")
        self.assertIsNotNone(output_path, "Profile B Failure: Compressed receipt path was not returned!")
        self.assertTrue(os.path.exists(output_path), "Profile B Failure: Receipt image missing on disk!")
        
        with Image.open(output_path) as processed_img:
            self.assertEqual(processed_img.mode, "L", f"Profile B Failure: Expected grayscale mode 'L', got '{processed_img.mode}'")
        
        purge_cached_media_file("test_profile_b.jpg")

    def test_document_template_token_parsing(self):
        """Verifies that plaintext bracket tokens are parsed without errors."""
        factory = DocumentTemplateFactory(listener=None)
        tokens = {"CLIENT_NAME": "Acme Corp", "JOB_ID": "JOB-QA-2026"}
        success = factory.parse_text_tokens("mock_doc_123", tokens)
        self.assertTrue(success, "Document Factory Failure: Token interpolation failed!")

    def tearDown(self):
        """Cleans up raw test assets."""
        if os.path.exists(self.test_img_path):
            os.remove(self.test_img_path)

if __name__ == "__main__":
    unittest.main()