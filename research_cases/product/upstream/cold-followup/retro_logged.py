import subprocess,sys,json,time
from pathlib import Path
R=Path(__file__).parent;W=R.parent.parent
name=sys.argv[1];args=sys.argv[2:];start=time.monotonic()
p=subprocess.run(["rtk","proxy","/home/sun07ao/retro-workspaces/retro-product-evaluation/product-upstream-env/bin/retro","-w",str(W),*args],capture_output=True,text=True)
(R/(name+".stdout.json")).write_text(p.stdout);(R/(name+".stderr.txt")).write_text(p.stderr);(R/(name+".receipt.json")).write_text(json.dumps({"argv":args,"exit_code":p.returncode,"elapsed_s":time.monotonic()-start},indent=2))
print(p.stdout);print(p.stderr,file=sys.stderr);raise SystemExit(p.returncode)
