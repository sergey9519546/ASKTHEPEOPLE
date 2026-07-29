import os
import tempfile
import pytest
from app.services.simulation_ipc import SimulationIPCClient, SimulationIPCServer, CommandType, IPCResponse, CommandStatus

def test_ipc_atomic_command_and_response():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = SimulationIPCClient(tmpdir)
        server = SimulationIPCServer(tmpdir)

        # Update environment status atomically
        server.start()
        assert client.check_env_alive() is True

        # Send inject event command
        command_id = "test_cmd_123"
        tmp_cmd_file = os.path.join(client.commands_dir, f"{command_id}.tmp")
        final_cmd_file = os.path.join(client.commands_dir, f"{command_id}.json")

        with open(tmp_cmd_file, 'w', encoding='utf-8') as f:
            f.write('{"command_id": "test_cmd_123", "command_type": "inject_event", "args": {"content": "Test scenario"}}')
        os.replace(tmp_cmd_file, final_cmd_file)

        # Server polls command
        cmd = server.poll_commands()
        assert cmd is not None
        assert cmd.command_type == CommandType.INJECT_EVENT
        assert cmd.args.get("content") == "Test scenario"

        # Server sends response atomically
        resp = IPCResponse(command_id=command_id, status=CommandStatus.COMPLETED, result={"ok": True})
        server.send_response(resp)

        assert not os.path.exists(final_cmd_file)
        assert os.path.exists(os.path.join(client.responses_dir, f"{command_id}.json"))

        server.stop()
        assert client.check_env_alive() is False
