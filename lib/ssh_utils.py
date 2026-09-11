import socket
import paramiko


def open_ssh_client(ip, user, pwd, timeout=6):
    """Open and return a connected SSHClient, or raise on failure.
    Caller is responsible for closing it."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=pwd, timeout=timeout)
    return ssh


def run_ssh_command(ip, user, pwd, cmd):
    """One-shot command execution: connect, run, disconnect.
    Returns (ok, stdout_text, stderr_text)."""
    try:
        ssh = open_ssh_client(ip, user, pwd, timeout=5)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        ssh.close()
        return True, out, err
    except Exception as e:
        return False, "", str(e)


def run_ssh_command_on_client(ssh, cmd):
    """Run a command on an already-open SSHClient (no connect/close)."""
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        return True, out, err
    except Exception as e:
        return False, "", str(e)


def test_connection(ip, user, pwd):
    """Validate reachability/credentials only. Returns (True, None) or
    (False, error_code_string)."""
    try:
        ssh = open_ssh_client(ip, user, pwd, timeout=6)
        ssh.close()
        return True, None
    except paramiko.AuthenticationException:
        return False, "AUTH_FAILED"
    except (paramiko.SSHException, socket.timeout, socket.error, OSError) as e:
        return False, f"CONNECTION_ERROR: {e}"
    except Exception as e:
        return False, f"UNKNOWN_ERROR: {e}"
