"""Unit tests for Agent.stop() (stdlib only: unittest + unittest.mock). No Windows, no backend, no real MT5.
Run from the agent folder:   python -m unittest test_agent_stop -v
"""
import logging
import unittest
from unittest import mock

import psutil

import agent

EXE = r"C:\Trading\MT5\A\terminal64.exe"
BASE = {"application_type": "MT5", "executable_path": EXE, "working_directory": r"C:\Trading\MT5\A"}
CFG = {"url": "http://127.0.0.1:8000", "secret": "x" * 30, "name": "test", "roots": [r"C:\Trading"], "poll": 1.0}


def cmd(sid="s1", pid=None, **over):
    return {"session_id": sid, "pid": pid, **BASE, **over}


class StopFallbackTests(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)                                # expected 'stop failed' errors stay out of test output
        self.addCleanup(logging.disable, logging.NOTSET)
        self.agent = agent.Agent(CFG)
        self.agent.report = mock.Mock()                                  # never talk to a backend
        self.find = self._patch("find_running")
        self.close = self._patch("close_process")
        self.found = mock.Mock(name="found_process", pid=4321)

    def _patch(self, name):
        p = mock.patch.object(agent, name)
        self.addCleanup(p.stop)
        return p.start()

    def test_pid_none_but_matching_process_exists_is_closed(self):
        self.find.return_value = self.found
        self.agent.stop(cmd(pid=None))
        self.close.assert_called_once_with(self.found)
        self.agent.report.assert_called_once_with("s1", "stopped", message="Stopped by agent")

    def test_stale_pid_but_matching_process_exists_is_closed(self):
        self.find.return_value = self.found
        with mock.patch.object(agent.psutil, "Process", side_effect=psutil.NoSuchProcess(999)):
            self.agent.stop(cmd(pid=999))
        self.close.assert_called_once_with(self.found)
        self.agent.report.assert_called_once_with("s1", "stopped", message="Stopped by agent")

    def test_no_matching_process_reports_stopped_without_closing(self):
        self.find.return_value = None
        self.agent.stop(cmd(pid=None))
        self.close.assert_not_called()
        self.agent.report.assert_called_once_with("s1", "stopped", message="Stopped by agent")

    def test_existing_handle_is_used_and_fallback_not_called(self):
        handle = mock.Mock(name="handle")
        self.agent.procs["s1"] = handle
        self.agent.stop(cmd(pid=handle.pid))
        self.find.assert_not_called()
        self.close.assert_called_once_with(handle)
        self.assertNotIn("s1", self.agent.procs)
        self.agent.report.assert_called_once_with("s1", "stopped", message="Stopped by agent")

    def test_adopted_process_is_used_and_fallback_not_called(self):
        live = mock.Mock(pid=42)
        live.is_running.return_value = True
        live.status.return_value = psutil.STATUS_RUNNING
        live.exe.return_value = EXE
        with mock.patch.object(agent.psutil, "Process", return_value=live):
            self.agent.stop(cmd(pid=42))
        self.find.assert_not_called()
        self.close.assert_called_once_with(live)

    def test_invalid_path_never_reaches_fallback_and_fails_safely(self):
        bad = [r"C:\Windows\System32\cmd.exe",                 # wrong executable name
               r"C:\Trading\..\Windows\terminal64.exe",         # traversal
               r"C:\Other\terminal64.exe",                      # outside allowed roots
               r"\\server\share\terminal64.exe"]                # UNC
        for path in bad:
            with self.subTest(path=path):
                self.find.reset_mock(); self.agent.report.reset_mock()
                self.agent.stop(cmd(executable_path=path))
                self.find.assert_not_called()
                self.close.assert_not_called()
                (sid, status), kw = self.agent.report.call_args
                self.assertEqual((sid, status), ("s1", "failed"))
                self.assertTrue(kw["message"].startswith("stop failed:"))

    def test_find_running_receives_the_validated_path(self):
        self.find.return_value = None
        self.agent.stop(cmd(executable_path="C:/Trading/MT5/A/terminal64.exe"))       # forward slashes in
        self.find.assert_called_once_with(EXE)                                         # normalised path out


if __name__ == "__main__":
    unittest.main()