import subprocess, sys, os
base = r'C:/Users/empir/Downloads/Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026/Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026'
out = os.path.join(base, 'data', 'study011_runs', 'confirmatory', 'canonical-run-002')
log = open(os.path.join(out, 'console.log'), 'a', encoding='utf-8', newline='\n')
env = dict(os.environ)
env['OPENROUTER_API_KEY'] = os.environ.get('OPENROUTER_API_KEY','')
env['DIALAGRAM_API_KEY'] = os.environ.get('DIALAGRAM_API_KEY','')
p = subprocess.Popen([sys.executable, 'experiments/live_benchmark/run_study_011.py',
    '--mode', 'LIVE_ONLY', '--phase', '1',
    '--workload-file', os.path.join(base, 'data', 'study011_workload_manifest.json'),
    '--output-dir', out],
    stdout=log, stderr=subprocess.STDOUT, cwd=base, env=env,
    creationflags=0x00000008 | 0x00000200)  # DETACHED_PROCESS | NEW_PROCESS_GROUP
print('detached PID:', p.pid)
