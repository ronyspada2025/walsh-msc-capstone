#!/usr/bin/env python3
"""Apply the capstone project package in a fresh clone; optionally publish to GitHub.

Called by the self-contained download script. Existing working directories are
never overwritten. No force push, reset, stash, or deletion of user files.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys

REPOSITORY='https://github.com/ronyspada2025/walsh-msc-capstone.git'
EXPECTED_BASE='1321dea9fd9f1ca3e06de6651a32a644e87326c6'


def run(args,cwd=None,capture=False,env=None):
    return subprocess.run([str(x) for x in args],cwd=cwd,env=env,check=True,
                          text=True,stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)


def safe_relative(name):
    path=PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(x in ['..','.git'] for x in path.parts) or '\\' in name:
        raise ValueError('Unsafe bundle path: '+name)
    return Path(*path.parts)


def inspect_bundle(bundle):
    manifest=json.loads((bundle/'bundle_manifest.json').read_text())
    if manifest['base_commit']!=EXPECTED_BASE: raise ValueError('Unexpected bundle base')
    if manifest.get('repository')!=REPOSITORY.removesuffix('.git'):
        raise ValueError('Unexpected package repository')
    paths=[e['path'] for e in manifest['files']+manifest['deletions']]
    if len(paths)!=len(set(paths)):raise ValueError('Duplicate package path')
    for entry in manifest['files']:
        rel=safe_relative(entry['path']); f=bundle/'payload'/rel
        if f.is_symlink() or not f.is_file(): raise ValueError('Missing or unsafe payload: '+str(rel))
        if hashlib.sha256(f.read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError('Payload checksum mismatch: '+str(rel))
    for entry in manifest['deletions']: safe_relative(entry['path'])
    return manifest


def bundle_is_applied(repo,manifest):
    for entry in manifest['files']:
        path=repo/safe_relative(entry['path'])
        if not path.is_file() or path.is_symlink():return False
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:return False
    return all(not (repo/safe_relative(e['path'])).exists() for e in manifest['deletions'])


def apply_bundle(repo,bundle,manifest):
    """Check every preimage before making any change."""
    if run(['git','status','--porcelain'],cwd=repo,capture=True).stdout.strip():
        raise ValueError('Target clone must be clean before applying the bundle')
    if run(['git','rev-parse','HEAD'],cwd=repo,capture=True).stdout.strip()!=manifest['base_commit']:
        raise ValueError('Target commit differs from the verified base')
    entries=manifest['files']+manifest['deletions']
    for entry in entries:
        rel=safe_relative(entry['path']); f=repo/rel
        for parent in [f,*list(f.parents)]:
            if parent==repo:break
            if parent.is_symlink():raise ValueError('Target contains a symlink: '+str(rel))
        expected=entry.get('before_sha256')
        if f.is_symlink(): raise ValueError('Target contains a symlink: '+str(rel))
        actual=hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
        if actual!=expected: raise ValueError('Target file differs from expected base: '+str(rel))
    for entry in manifest['files']:
        rel=safe_relative(entry['path']); target=repo/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(bundle/'payload'/rel,target)
        target.chmod(entry.get('mode',0o644))
    for entry in manifest['deletions']:
        (repo/safe_relative(entry['path'])).unlink()


def commit_changes(repo,manifest):
    paths=[entry['path'] for entry in manifest['files']+manifest['deletions']]
    paths=[path for path in paths if (repo/path).exists() or
           subprocess.run(['git','ls-files','--error-unmatch','--',path],cwd=repo,
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0]
    # Stage only the declared package payload, never an unrelated file.
    for begin in range(0,len(paths),40): run(['git','add','--',*paths[begin:begin+40]],cwd=repo)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=repo).returncode:
        run(['git','commit','-m','Publish final capstone analysis and report'],cwd=repo)
    return run(['git','rev-parse','HEAD'],cwd=repo,capture=True).stdout.strip()


def stream_pipeline(command,repo,env):
    log=repo/'pipeline_execution.log'
    with log.open('w') as output:
        process=subprocess.Popen([str(x) for x in command],cwd=repo,env=env,text=True,
                                 stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        for line in process.stdout:
            print(line,end='',flush=True); output.write(line); output.flush()
        status=process.wait()
    if status: raise RuntimeError(f'Pipeline failed with status {status}. See {log}')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',required=True,type=Path)
    parser.add_argument('--target',type=Path,help='New clone path; must not already exist')
    parser.add_argument('--push',action='store_true',help='Commit and push to the selected branch (default main)')
    parser.add_argument('--branch',default='main',help='Use another branch if desired; default main')
    parser.add_argument('--dry-run',action='store_true',help='Validate package without network or repository changes')
    parser.add_argument('--recompute',action='store_true',help='Run the complete pipeline locally before verification')
    parser.add_argument('--skip-install',action='store_true',help='Use the current interpreter and already installed requirements')
    args=parser.parse_args(argv)
    try:
        bundle=args.bundle.resolve(); manifest=inspect_bundle(bundle)
        if args.dry_run:
            print(f'PACKAGE VALIDATED: {len(manifest["files"])} files; {len(manifest["deletions"])} deletions.')
            print('Repository:',REPOSITORY)
            print('Default action: fresh clone, install pinned dependencies, verify included executed results and documents.')
            print('With --push: commit and normal push to '+args.branch+'. No force push.')
            return 0
        if sys.version_info[:2]!=(3,12): raise RuntimeError('Python 3.12 is required. On macOS install it with: brew install python@3.12. Then run this script again.')
        if shutil.which('git') is None: raise RuntimeError('Git is required. On macOS run xcode-select --install.')
        run(['git','check-ref-format','--branch',args.branch],capture=True)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        repo=(args.target or Path.home()/'Downloads'/f'walsh-msc-capstone-{stamp}').expanduser().resolve()
        if repo.exists(): raise RuntimeError(f'Destination already exists; choose a new --target path: {repo}')
        repo.parent.mkdir(parents=True,exist_ok=True)
        print('Creating fresh clone:',repo,flush=True)
        run(['git','clone','--branch','main','--single-branch',REPOSITORY,repo])
        head=run(['git','rev-parse','HEAD'],cwd=repo,capture=True).stdout.strip()
        installed=bundle_is_applied(repo,manifest)
        if head!=EXPECTED_BASE and not installed:
            raise RuntimeError('GitHub main has additional changes. The package was not applied; retain this clone for review.')
        if args.branch!='main': run(['git','switch','-c',args.branch],cwd=repo)
        if not installed:apply_bundle(repo,bundle,manifest)
        # A Colab opened from the selected branch clones that branch.
        if args.branch!='main':
            nb=repo/'notebooks/06_final_report_pipeline_colab.ipynb'
            doc=json.loads(nb.read_text())
            for cell in doc['cells']:
                if cell['cell_type']=='code':
                    source=''.join(cell['source']).replace("os.environ.get('CAPSTONE_REF', 'main')",
                        'os.environ.get("CAPSTONE_REF", '+json.dumps(args.branch)+')')
                    cell['source']=source.splitlines(keepends=True)
            nb.write_text(json.dumps(doc,indent=2)+'\n')
        python=Path(sys.executable)
        if not args.skip_install:
            venv=repo/'.venv'; run([python,'-m','venv',venv])
            python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
            run([python,'-m','pip','install','-q','-r',repo/'requirements.txt'])
        env=os.environ.copy()
        env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LOKY_MAX_CPU_COUNT='4')
        if args.recompute:
            stream_pipeline([python,'-u','final_pipeline.py','--jobs','4'],repo,env)
        else:
            print('Validating the included completed analysis and final documents. Use --recompute for a new local model run.')
        run([python,'scripts/verify_project.py'],cwd=repo,env=env)
        run([python,'-m','unittest','discover','-s','tests','-v'],cwd=repo,env=env)
        if args.push:
            for field in ['user.name','user.email']:
                value=subprocess.run(['git','config',field],cwd=repo,text=True,stdout=subprocess.PIPE)
                if value.returncode or not value.stdout.strip():
                    raise RuntimeError(f'Verified files are ready at {repo}, but git {field} is unset. Configure your Git identity, then commit and push from that folder.')
            sha=commit_changes(repo,manifest)
            # The ordinary push rejects concurrent updates; history is never overwritten.
            run(['git','push','-u','origin',f'HEAD:refs/heads/{args.branch}'],cwd=repo)
            remote=run(['git','ls-remote','--heads','origin',f'refs/heads/{args.branch}'],cwd=repo,capture=True).stdout.split()
            if not remote or remote[0]!=sha: raise RuntimeError('Push returned but remote commit verification failed')
            print('GITHUB UPDATE VERIFIED:',sha)
            print('Open: https://github.com/ronyspada2025/walsh-msc-capstone/tree/'+args.branch)
        else:
            print('PROJECT READY:',repo)
            print('Files are verified locally. Run the download script with --push to publish from a fresh clone.')
        print('Working folder:',repo)
        return 0
    except (OSError,ValueError,KeyError,RuntimeError,subprocess.CalledProcessError) as e:
        print('UPDATE STOPPED:',e,file=sys.stderr)
        if 'repo' in locals(): print('Working files retained at:',repo,file=sys.stderr)
        return 1

if __name__=='__main__': raise SystemExit(main())
