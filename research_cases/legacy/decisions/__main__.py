"""Run the authorized synthetic integration smoke, with persisted actual receipt."""
import argparse
import json
from pathlib import Path
from . import JevAdapter

parser=argparse.ArgumentParser()
parser.add_argument('--receipt-dir',default='var/receipts/jev')
args=parser.parse_args()
state={'text':'Synthetic software check. The calculation process exited normally. No scientific-validity check was performed. A separate note proposes a future calculation; it has not been run.',
       'chinese_boundary':'合成例子：程序正常结束；未验证科学有效性。另一项计算仅为计划，尚未运行。'}
questions={
    'completed':{'type':'noul','instructions':'Does state.text explicitly report normal process exit, without asking about scientific validity?'},
    'validity':{'type':'choice','instructions':'According to state.chinese_boundary, has scientific validity been verified?', 'criteria':{'verified':'Validity was verified.','not_verified':'Validity was explicitly not verified.','insufficient_context':'There is no statement about validity.'}},
    'planning':{'type':'score','instructions':'How much of state.text describes future unexecuted work?', 'criteria':['None of the passage concerns future work.','Future work is one distinct part of the passage.','The passage is primarily future work.']}}
record=JevAdapter(Path(args.receipt_dir)).evaluate('integration_smoke',state,questions,'smoke-cli-v1','advisory-synthetic-v1',egress_scope='synthetic',use_cache=False)
print(json.dumps({key:record[key] for key in ('status','record_path','actual_model','usage','error_category')},indent=2))
raise SystemExit(0 if record['status']=='ok' else 1)
