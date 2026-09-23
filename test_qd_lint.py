import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from qd_lint import InputError, read_inputs


class FilelistTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "inc").mkdir()
        (self.root / "inc" / "defs.svh").write_text("`define OK 1\n")
        (self.root / "a.sv").write_text("module a; endmodule\n")
        (self.root / "b.sv").write_text("module b; endmodule\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_nested_options_and_source_order(self):
        (self.root / "inner.vf").write_text("+incdir+inc\n-DINNER=2\na.sv\n")
        (self.root / "main.vf").write_text("-f inner.vf\n+define+OUTER=1\nb.sv\n")
        src, inc, defines, lists = read_inputs(self.root / "main.vf")
        self.assertEqual([p.name for p in src], ["a.sv", "b.sv"])
        self.assertEqual(inc, [(self.root / "inc").resolve()])
        self.assertEqual(defines, ["INNER=2", "OUTER=1"])
        self.assertEqual([p.name for p in lists], ["main.vf", "inner.vf"])

    def test_filelist_cycle_and_missing_environment(self):
        (self.root / "one.vf").write_text("-f two.vf\n")
        (self.root / "two.vf").write_text("-f one.vf\n")
        with self.assertRaisesRegex(InputError, "cycle"):
            read_inputs(self.root / "one.vf")
        (self.root / "missing.vf").write_text("${QD_LINT_TEST_MISSING}/x.sv\n")
        os.environ.pop("QD_LINT_TEST_MISSING", None)
        with self.assertRaisesRegex(InputError, "not set"):
            read_inputs(self.root / "missing.vf")

    def test_missing_source(self):
        (self.root / "bad.vf").write_text("absent.sv\n")
        with self.assertRaisesRegex(InputError, "not found"):
            read_inputs(self.root / "bad.vf")

    def test_broken_module_fails_each_installed_engine(self):
        if not shutil.which("verilator") and not shutil.which("slang"):
            self.skipTest("no supported lint engine installed")
        broken = self.root / "broken.sv"
        broken.write_text("module broken(input logic a); assign a = ; endmodule\n")
        for engine in ("verilator", "slang"):
            if shutil.which(engine):
                run = subprocess.run([sys.executable, "qd-lint", "check", "--filelist", str(broken), "--top", "broken", "--engine", engine], capture_output=True)
                self.assertNotEqual(run.returncode, 0, engine)


if __name__ == "__main__":
    unittest.main()
