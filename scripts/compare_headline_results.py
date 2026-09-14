#!/usr/bin/env python3
"""Exit 0 for exact agreement, 2 for document differences, 1 for invalid output."""
from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.verification import compare_report, verify_results

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('actual',nargs='?',type=Path,default=ROOT/'reports/tables/headline_results.json')
    p.add_argument('--expected',type=Path,default=ROOT/'scripts/final_report_reference.json')
    args=p.parse_args()
    try:
        result=json.loads(args.actual.read_text())
        verify_results(result,args.actual.resolve().parent.parent,ROOT)
        comparison=compare_report(result,args.expected)
        print('REPORT CHECK:',comparison['summary'])
        for row in comparison['metrics']:
            if row['status']!='MATCH':
                print(row['status'],row['location'],row['name'],
                      'report='+row['reported'],'computed='+row.get('computed_display','MISSING'))
        if comparison['summary']['MISSING_OR_INVALID']: return 1
        return 0 if comparison['exact_match'] else 2
    except (OSError,ValueError,KeyError,TypeError) as e:
        print('INVALID OUTPUT:',e,file=sys.stderr); return 1

if __name__=='__main__': raise SystemExit(main())
