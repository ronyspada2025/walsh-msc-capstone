#!/usr/bin/env python3
"""Verify analysis integrity, final-report agreement, and document checksums."""
from pathlib import Path
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.verification import verify_results,compare_report,get_path

def verify_documents(root):
    manifest=json.loads((root/'docs/document_manifest.json').read_text())
    if set(manifest['files'])!={'docs/final_report.pdf','docs/final_presentation.pdf'}:
        raise ValueError('Document manifest is incomplete')
    for name,digest in manifest['files'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Document checksum mismatch: '+name)
    if manifest['abstract_word_count']!=330:raise ValueError('Unexpected abstract word count')

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports')
    args=parser.parse_args(argv)
    try:
        result=json.loads((args.output/'tables/headline_results.json').read_text())
        verify_results(result,args.output,ROOT)
        comparison=compare_report(result,ROOT/'scripts/final_report_reference.json')
        reference=json.loads((ROOT/'scripts/analysis_regression_reference.json').read_text())
        if not reference.get('metrics'):raise ValueError('Numerical regression reference is empty')
        for ref in reference['metrics']:
            value=get_path(result,ref['path'])
            if abs(value-ref['value'])>ref['absolute_tolerance']:
                raise ValueError('Unexpected numerical change: '+ref['name'])
        verify_documents(ROOT)
        print('COMPUTATION VERIFIED: input, sources, outputs, partitions, convergence, and documents.')
        print('FINAL REPORT:',comparison['summary'])
        if not comparison['exact_match']:
            for row in comparison['metrics']:
                if row['status']!='MATCH':
                    print(row['status'],row['location'],row['name'],'report='+row['reported'],
                          'computed='+row.get('computed_display','MISSING'))
            return 1 if comparison['summary']['MISSING_OR_INVALID'] else 2
        print('FINAL REPORT VERIFIED: all declared metrics agree at the displayed precision.')
        return 0
    except (OSError,ValueError,KeyError,TypeError,IndexError) as error:
        print('VERIFICATION FAILED:',error,file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
