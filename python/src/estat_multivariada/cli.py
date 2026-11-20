import argparse, json
from pathlib import Path
from .pipeline import run_pipeline

def main():
    parser=argparse.ArgumentParser(description="ETL, multivariate analytics and ML")
    sub=parser.add_subparsers(dest="command",required=True)
    run=sub.add_parser("run"); run.add_argument("--input",type=Path,default=Path("data/raw"))
    run.add_argument("--output",type=Path,default=Path("data")); run.add_argument("--docs-data",type=Path,default=Path("docs/data"))
    args=parser.parse_args()
    summary=run_pipeline(args.input,args.output,args.docs_data)
    print(json.dumps({"datasets":summary["dataset_count"],"rows":summary["total_rows"]}))
if __name__=="__main__": main()
