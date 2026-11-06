import subprocess, sys
from pathlib import Path
out = Path(r"C:\Users\admin\AppData\Local\Temp\rtx_old.pdf")
p = subprocess.run(["git", "show", "HEAD:research/rtx-pro-6000/paper/PAPER.pdf"],
                   cwd=r"D:\github\DeepResearchRSI", capture_output=True)
out.write_bytes(p.stdout)
print("bytes", out.stat().st_size)
