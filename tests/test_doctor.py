import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import agentmd_doctor as d


def make(files):
    root = tempfile.mkdtemp()
    for name, text in files.items():
        p = os.path.join(root, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
    return root


def codes(files):
    return {c for _, c, _, _ in d.scan(make(files))}


RULES = "Always run the full test suite before committing changes.\n"


class T(unittest.TestCase):
    def test_clean_import(self):
        self.assertEqual(codes({"AGENTS.md": RULES, "CLAUDE.md": "@AGENTS.md\n"}), set())

    def test_shadowed(self):
        self.assertIn("shadowed-agents-md", codes({"AGENTS.md": RULES, "CLAUDE.md": "Use tabs for indentation everywhere.\n"}))

    def test_drift(self):
        self.assertIn("drift", codes({"AGENTS.md": RULES + "Never commit secrets to the repository.\n", "CLAUDE.md": RULES}))

    def test_broken_import(self):
        self.assertIn("broken-import", codes({"CLAUDE.md": "@docs/missing.md\n"}))

    def test_code_span_not_import(self):
        self.assertEqual(codes({"CLAUDE.md": "Use `@types/node` here.\n"}), set())

    def test_cycle_safe(self):
        d.scan(make({"CLAUDE.md": "@a.md\n", "a.md": "@CLAUDE.md\n"}))

    def test_unsupported_name(self):
        self.assertIn("unsupported-name", codes({"AGENTS.override.md": "x"}))

    def test_nested(self):
        self.assertIn("nested-agents-md", codes({"CLAUDE.md": "@x.md\n", "x.md": "hi", "pkg/AGENTS.md": RULES}))

    def test_exit_code(self):
        r = make({"AGENTS.md": RULES, "CLAUDE.md": "other long unrelated instruction text here.\n"})
        self.assertEqual(d.main([r]), 1)
        r = make({"AGENTS.md": RULES, "CLAUDE.md": "@AGENTS.md"})
        self.assertEqual(d.main([r]), 0)


if __name__ == "__main__":
    unittest.main()
