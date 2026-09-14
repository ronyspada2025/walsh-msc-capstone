#!/usr/bin/env python3
"""Compatibility entry point: all analyses now run through final_pipeline.py."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from final_pipeline import main
if __name__=='__main__': raise SystemExit(main())
