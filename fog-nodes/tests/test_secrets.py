import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils import get_secret


class SecretReaderTests(unittest.TestCase):
    def test_environment_value_takes_precedence(self):
        with patch.dict(
            os.environ,
            {"TEST_SECRET": "from-env", "TEST_SECRET_FILE": "missing"},
            clear=False,
        ):
            self.assertEqual(get_secret("TEST_SECRET"), "from-env")

    def test_reads_docker_secret_file(self):
        with tempfile.TemporaryDirectory() as directory:
            secret_path = Path(directory) / "secret"
            secret_path.write_text("from-file\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"TEST_SECRET_FILE": str(secret_path)},
                clear=False,
            ):
                os.environ.pop("TEST_SECRET", None)
                self.assertEqual(get_secret("TEST_SECRET"), "from-file")


if __name__ == "__main__":
    unittest.main()
