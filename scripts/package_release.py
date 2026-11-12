"""Package only the application and documentation, never runtime/device data."""
import hashlib
import importlib.metadata
import sys
import zipfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    dist = root / "dist"
    executable = dist / "UZ801-OpenStick-Manager.exe"
    if not executable.is_file():
        raise SystemExit("Build the executable first")
    notices = ["Third-party licenses included with the Windows build.\n"
               "Build-time tools are included for transparency; ADB, EDL and firmware are not bundled.\n"]
    for package in sorted(importlib.metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        if package.metadata["Name"] == "uz801-openstick-manager":
            continue
        for file in package.files or []:
            if any(word in file.name.lower() for word in ("license", "copying", "copyright")) and file.suffix.lower() not in (".py", ".pyc"):
                path = package.locate_file(file)
                if path.is_file() and path.stat().st_size < 512 * 1024:
                    notices.append(f"\n{'=' * 72}\n{package.metadata['Name']} {package.version} — {file.name}\n")
                    notices.append(path.read_text(encoding="utf-8", errors="replace"))
    python_root = Path(sys.base_prefix)
    for path in [python_root / "LICENSE.txt", *python_root.glob("tcl/**/license.terms")]:
        if path.is_file():
            notices.append(f"\n{'=' * 72}\nPython / Tcl / Tk: {path.name}\n")
            notices.append(path.read_text(encoding="utf-8", errors="replace"))
    notices_path = dist / "THIRD_PARTY_NOTICES.txt"
    notices_path.write_text("\n".join(notices), encoding="utf-8")
    archive = dist / "UZ801-OpenStick-Manager-v0.1.0-Windows-x64.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(executable, executable.name)
        z.write(notices_path, notices_path.name)
        for filename in ("README.md", "LICENSE"):
            z.write(root / filename, filename)
        for path in sorted((root / "docs").glob("*.md")):
            z.write(path, "docs/" + path.name)
        z.writestr("START.bat", '@echo off\r\ncd /d "%~dp0"\r\n"UZ801-OpenStick-Manager.exe" %*\r\n')
        z.writestr("DEMO.bat", '@echo off\r\ncd /d "%~dp0"\r\n"UZ801-OpenStick-Manager.exe" --demo\r\n')
    assets = [executable, archive, notices_path]
    checksums = "\n".join(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name for path in assets) + "\n"
    (dist / "SHA256SUMS.txt").write_text(checksums, encoding="ascii")
    print(checksums, end="")


if __name__ == "__main__":
    main()
