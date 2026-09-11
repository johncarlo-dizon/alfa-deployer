import os
import ipaddress
from config import STORES_FILE


def load_stores():
    """Parse stores.txt into a list of dicts:
    {ip, user, pwd, dc, name, code, pos}

    Format per line: ip,user,pwd,name,code,pos
    A line with no comma is treated as a DC section header that groups
    every store row that follows it, until the next header.
    """
    stores = []
    if os.path.exists(STORES_FILE):
        current_dc = "Ungrouped"
        with open(STORES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "," not in line:
                    current_dc = line
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    ip, user, pwd = parts[0], parts[1], parts[2]
                    try:
                        ipaddress.ip_address(ip)
                    except ValueError:
                        continue  # not a real IP — skip stray example/legend rows
                    name = parts[3] if len(parts) > 3 and parts[3] else ip
                    code = parts[4] if len(parts) > 4 and parts[4] else ""
                    pos = parts[5] if len(parts) > 5 and parts[5] else ""
                    stores.append({
                        "ip": ip, "user": user, "pwd": pwd,
                        "dc": current_dc, "name": name, "code": code, "pos": pos
                    })
    return stores


def read_stores_raw():
    """Return the raw text content of stores.txt for editing, or an empty
    string if the file doesn't exist yet."""
    if os.path.exists(STORES_FILE):
        try:
            with open(STORES_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""
    return ""


def write_stores_raw(content):
    """Overwrite stores.txt with new raw text content from the editor."""
    with open(STORES_FILE, "w", encoding="utf-8") as f:
        f.write(content)
