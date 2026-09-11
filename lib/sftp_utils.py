import posixpath


def open_sftp(ssh):
    """Return an SFTPClient bound to an already-connected SSHClient."""
    return ssh.open_sftp()


def remote_file_exists(sftp, remote_path):
    try:
        sftp.stat(remote_path)
        return True
    except FileNotFoundError:
        return False
    except IOError:
        return False


def ensure_remote_dir(sftp, remote_dir):
    """Create remote_dir (and any missing parent folders) if it doesn't
    exist yet. remote_dir should use backslashes (Windows) or forward
    slashes; both are normalized to forward slashes for SFTP."""
    normalized = remote_dir.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p]

    # Rebuild path piece by piece (handles "C:" drive prefix correctly)
    current = ""
    for i, part in enumerate(parts):
        current = part if i == 0 else current + "/" + part
        try:
            sftp.stat(current)
        except IOError:
            try:
                sftp.mkdir(current)
            except IOError:
                pass  # race condition or drive root — safe to ignore


def upload_file(sftp, local_path, remote_dir, filename=None):
    """Upload a single local file into remote_dir. Returns the remote
    path used."""
    if filename is None:
        filename = posixpath.basename(local_path.replace("\\", "/"))
    remote_dir_norm = remote_dir.replace("\\", "/").rstrip("/")
    remote_path = f"{remote_dir_norm}/{filename}"
    sftp.put(local_path, remote_path)
    return remote_path
