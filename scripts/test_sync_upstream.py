import importlib.util
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("sync_upstream", Path(__file__).with_name("sync-upstream.py"))
sync_upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_upstream)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.upstream = self.root / "upstream"
        self.fork = self.root / "fork"
        self.git("init", "-b", "master", str(self.upstream))
        self.commit(self.upstream, "shared.txt", "original\n")
        self.git("clone", str(self.upstream), str(self.fork))
        self.args = SimpleNamespace(fork_url=str(self.fork), upstream_url=str(self.upstream), upstream_ref="master", publish=False)

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args, cwd=None):
        return subprocess.check_output(["git", *args], cwd=cwd, stderr=subprocess.DEVNULL, text=True).strip()

    def commit(self, repo, name, text):
        (repo / name).write_text(text)
        self.git("add", name, cwd=repo)
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", name, cwd=repo)

    def test_current_fork_does_nothing(self):
        result = sync_upstream.sync(self.args)
        self.assertEqual(result["status"], "up_to_date")
        self.assertEqual(result["behind"], 0)

    def test_clean_update_preserves_both_original_repositories(self):
        self.commit(self.fork, "ko.txt", "한국어\n")
        self.commit(self.upstream, "new.txt", "upstream\n")
        before = self.git("rev-parse", "HEAD", cwd=self.fork)
        result = sync_upstream.sync(self.args)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["behind"], 1)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.fork), before)
        self.assertEqual(self.git("status", "--porcelain", cwd=self.fork), "")
        self.assertFalse((self.fork / "new.txt").exists())

    def test_conflict_is_reported_without_pushing_markers(self):
        self.commit(self.fork, "shared.txt", "한국어\n")
        self.commit(self.upstream, "shared.txt", "new English\n")
        before = self.git("rev-parse", "HEAD", cwd=self.fork)
        result = sync_upstream.sync(self.args)
        self.assertEqual(result["status"], "conflicts")
        self.assertEqual(result["conflicts"], ["shared.txt"])
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.fork), before)
        self.assertEqual((self.fork / "shared.txt").read_text(), "한국어\n")

    def test_publish_creates_only_a_topic_branch_and_deduplicates_prs(self):
        self.commit(self.upstream, "new.txt", "upstream\n")
        before = self.git("rev-parse", "HEAD", cwd=self.fork)
        self.args.publish = True
        self.args.fork_repo = "test/fork"
        original_command = sync_upstream.command
        created = []

        def command(argv, cwd=None, check=True):
            if argv[:3] == ["gh", "pr", "create"]:
                self.assertIn("--draft", argv)
                created.append(argv)
                return subprocess.CompletedProcess(argv, 0, "https://example.invalid/pr/1\n", "")
            if argv[:3] == ["gh", "pr", "list"]:
                return subprocess.CompletedProcess(argv, 0, '[{"url":"https://example.invalid/pr/1","state":"OPEN"}]', "")
            return original_command(argv, cwd, check)

        with patch.object(sync_upstream, "command", command):
            first = sync_upstream.sync(self.args)
            second = sync_upstream.sync(self.args)
        self.assertEqual(first["status"], "draft_created")
        self.assertEqual(second["status"], "already_proposed")
        self.assertEqual(len(created), 1)
        self.assertEqual(self.git("rev-parse", "master", cwd=self.fork), before)
        self.git("merge-base", "--is-ancestor", first["upstream"], first["branch"], cwd=self.fork)


if __name__ == "__main__":
    unittest.main()
