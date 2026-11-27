@echo off
cd /d C:\Users\hachk\pilotage_b2b
python -X utf8 tests\bench_rerun.py 2026,2025,2026 "Vue Executive" > tests\_bench.log 2>&1
echo DONE >> tests\_bench.log
