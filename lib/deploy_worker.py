import time
import threading
import concurrent.futures
from datetime import datetime

from config import MAX_WORKERS, UPLOAD_MAX_ATTEMPTS, UPLOAD_RETRY_DELAY_SEC
from ssh_utils import open_ssh_client, run_ssh_command_on_client, test_connection
from sftp_utils import open_sftp, ensure_remote_dir, remote_file_exists, upload_file


def _run_elevated_once(ssh, remote_exe_path, log, detail):
    """Fire a remote .exe with an elevated (Highest) run level, without
    needing an interactive UAC click, by wrapping it in a throwaway
    scheduled task. Same idiom the reminder dashboard uses to install
    scheduled tasks — here it's a create -> run -> delete one-shot."""
    task_name = f"AlfaDeploy_Run_{int(time.time() * 1000)}"

    create_cmd = (
        f'schtasks /Create /TN "{task_name}" /TR "{remote_exe_path}" '
        f'/SC ONCE /ST 00:00 /RL HIGHEST /F'
    )
    run_cmd = f'schtasks /Run /TN "{task_name}"'
    delete_cmd = f'schtasks /Delete /TN "{task_name}" /F'

    ok_c, out_c, err_c = run_ssh_command_on_client(ssh, create_cmd)
    if not ok_c or "SUCCESS" not in out_c.upper():
        log(f"FAILED to register elevated run task for {remote_exe_path}: {err_c.strip() or out_c.strip()}", tag="failed")
        return False

    ok_r, out_r, err_r = run_ssh_command_on_client(ssh, run_cmd)
    if not ok_r:
        log(f"FAILED to trigger elevated run for {remote_exe_path}: {err_r.strip()}", tag="failed")
        run_ssh_command_on_client(ssh, delete_cmd)  # best-effort cleanup
        return False

    detail(f"Launched elevated: {remote_exe_path}")
    run_ssh_command_on_client(ssh, delete_cmd)  # best-effort cleanup, ignore result
    return True


def _upload_one_file(sftp, file_entry, remote_dir, log, detail):
    """Upload a single queued file, respecting replace_if_exists.
    Returns (uploaded: bool, remote_path: str | None)."""
    local_path = file_entry["path"]
    name = file_entry["name"]
    remote_dir_norm = remote_dir.replace("\\", "/").rstrip("/")
    remote_path = f"{remote_dir_norm}/{name}"

    if not file_entry.get("replace_if_exists", True) and remote_file_exists(sftp, remote_path):
        detail(f"Skipped {name} — already exists remotely and replace is off.")
        return False, remote_path

    last_err = None
    for attempt in range(1, UPLOAD_MAX_ATTEMPTS + 1):
        try:
            upload_file(sftp, local_path, remote_dir, filename=name)
            detail(f"Uploaded {name} -> {remote_path}")
            return True, remote_path
        except Exception as e:
            last_err = e
            if attempt < UPLOAD_MAX_ATTEMPTS:
                time.sleep(UPLOAD_RETRY_DELAY_SEC)

    log(f"FAILED to upload {name}: {last_err}", tag="failed")
    return False, None


def _upload_all_files(sftp, ssh, deploy_files, remote_dir, ip, log_queue, log, detail):
    uploaded_count = 0
    total_files = len(deploy_files)
    any_upload_failed = False

    for i, file_entry in enumerate(deploy_files):
        log_queue.put(("status", f"Uploading {file_entry['name']} to {ip} ({i + 1}/{total_files})...", None))
        uploaded, remote_path = _upload_one_file(sftp, file_entry, remote_dir, log, detail)

        if uploaded:
            uploaded_count += 1
            if file_entry.get("run_as_admin") and remote_path:
                _run_elevated_once(ssh, remote_path, log, detail)
        elif remote_path is None:
            any_upload_failed = True

    return uploaded_count, total_files, any_upload_failed


def _run_post_command(ssh, post_command, ip, log_queue, log, detail):
    """Returns True if there was nothing to run, or it ran successfully."""
    if not post_command.strip():
        return True
    log_queue.put(("status", f"Running command on {ip}...", None))
    ok_p, out_p, err_p = run_ssh_command_on_client(ssh, post_command.strip())
    if ok_p:
        detail(f"Command ran. Output: {out_p.strip() or '(none)'}")
        return True
    log(f"FAILED to run command: {err_p}", tag="failed")
    return False


def _deploy_to_store(store, deploy_files, remote_dir, post_command, execution_order, log_queue):
    ip, user, pwd = store["ip"], store["user"], store["pwd"]
    store_code = store.get("code", "")
    store_pos = store.get("pos", "")
    label_parts = [p for p in [store_code, store_pos] if p]
    store_label = f"{' - '.join(label_parts)} ({ip})" if label_parts else ip

    def log(text, tag=None):
        log_queue.put(("log", f"[STORE: {ip}] {text}", tag))

    def detail(text):
        log_queue.put(("detail", f"[STORE: {ip}] {text}", None))

    log("Connecting...")
    log_queue.put(("status", f"Connecting to {ip}...", None))

    conn_ok, conn_err = test_connection(ip, user, pwd)
    if not conn_ok:
        if conn_err == "AUTH_FAILED":
            log("FAILED — SSH authentication rejected.", tag="failed")
        else:
            log(f"FAILED — could not connect: {conn_err}", tag="failed")
        log("SKIPPED — fix connectivity/credentials for this store and re-run.", tag="failed")
        log_queue.put(("failed_store", store_label, None))
        log_queue.put(("progress", 1, None))
        return

    try:
        ssh = open_ssh_client(ip, user, pwd, timeout=8)
    except Exception as e:
        log(f"FAILED — could not open session for file transfer: {e}", tag="failed")
        log_queue.put(("failed_store", store_label, None))
        log_queue.put(("progress", 1, None))
        return

    log("Connected and authenticated successfully.")
    uploaded_count = 0
    total_files = len(deploy_files)
    any_upload_failed = False
    command_failed = False

    try:
        sftp = open_sftp(ssh)
        ensure_remote_dir(sftp, remote_dir)
        detail(f"Target directory ready: {remote_dir}")

        if execution_order == "commands_first":
            command_failed = not _run_post_command(ssh, post_command, ip, log_queue, log, detail)
            uploaded_count, total_files, any_upload_failed = _upload_all_files(
                sftp, ssh, deploy_files, remote_dir, ip, log_queue, log, detail
            )
        else:  # files_first (default)
            uploaded_count, total_files, any_upload_failed = _upload_all_files(
                sftp, ssh, deploy_files, remote_dir, ip, log_queue, log, detail
            )
            command_failed = not _run_post_command(ssh, post_command, ip, log_queue, log, detail)

        sftp.close()

    except Exception as e:
        log(f"FAILED during transfer: {e}", tag="failed")
        any_upload_failed = True
    finally:
        ssh.close()

    done_tag = "failed" if (any_upload_failed or command_failed) else None
    log(f"Completed: {uploaded_count}/{total_files} file(s) uploaded.", tag=done_tag)

    if any_upload_failed or command_failed or uploaded_count < total_files:
        log_queue.put(("failed_store", store_label, None))
    else:
        log_queue.put(("success_store", store_label, None))
    log_queue.put(("progress", 1, None))


def start_deployment(selected_stores, deploy_files, remote_dir, post_command, execution_order, log_queue):
    """Kick off the whole batch on a background thread so the Tk main
    loop never blocks. Workers only ever push to log_queue — the caller
    is expected to poll it on the main thread (see dashboard.py)."""

    def deploy_worker(store):
        _deploy_to_store(store, deploy_files, remote_dir, post_command, execution_order, log_queue)

    def run_all():
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            list(executor.map(deploy_worker, selected_stores))
        log_queue.put(("done", None, None))

    threading.Thread(target=run_all, daemon=True).start()
