import json,sqlite3,threading,time,uuid
from pathlib import Path
from .models import Case,redact

class Store:
    def __init__(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path,check_same_thread=False,isolation_level=None)
        self.db.row_factory=sqlite3.Row;self.lock=threading.RLock()
        self.db.executescript('''PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, created REAL, state TEXT, config TEXT, source TEXT);
        CREATE TABLE IF NOT EXISTS cases(run_id TEXT, case_id TEXT, ordinal INTEGER, data TEXT, state TEXT DEFAULT 'Pending', PRIMARY KEY(run_id,case_id));
        CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY, run_id TEXT, case_id TEXT, started REAL, finished REAL, status TEXT, actual TEXT, details TEXT);
        CREATE TABLE IF NOT EXISTS evidence(attempt_id TEXT, kind TEXT, path TEXT);
        CREATE TABLE IF NOT EXISTS flows(case_hash TEXT PRIMARY KEY, actions TEXT, assertions TEXT, verified REAL);
        CREATE TABLE IF NOT EXISTS writebacks(id TEXT PRIMARY KEY, attempt_id TEXT UNIQUE, run_id TEXT, case_id TEXT, state TEXT, payload TEXT, error TEXT);
        CREATE TABLE IF NOT EXISTS events(run_id TEXT, at REAL, kind TEXT, message TEXT);
        CREATE TABLE IF NOT EXISTS chat(id TEXT PRIMARY KEY, at REAL, role TEXT, content TEXT);
        CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY, at REAL, case_id TEXT, fixture_id TEXT, category TEXT, action_hash TEXT, note TEXT);
        CREATE UNIQUE INDEX IF NOT EXISTS one_active_attempt_per_run ON attempts(run_id) WHERE finished IS NULL;
        ''')
    def create_run(self,cases,config,source):
        run=uuid.uuid4().hex
        with self.lock,self.db:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                self.db.execute('INSERT INTO runs VALUES(?,?,?,?,?)',(run,time.time(),'Ready',json.dumps(config),json.dumps(source)))
                for i,c in enumerate(cases):self.db.execute('INSERT INTO cases VALUES(?,?,?,?,?)',(run,c.case_id,i,json.dumps(c.dict()),'Pending'))
                self.db.execute('COMMIT')
            except Exception:self.db.execute('ROLLBACK');raise
        return run
    def recover(self):
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                interrupted=list(self.db.execute("SELECT a.id,a.run_id,a.case_id,c.data FROM attempts a JOIN cases c ON c.run_id=a.run_id AND c.case_id=a.case_id WHERE a.finished IS NULL"))
                for r in interrupted:
                    case=Case.from_dict(json.loads(r['data']))
                    if set(case.categories)-{'read'}:
                        self.db.execute("UPDATE cases SET state='Completed' WHERE run_id=? AND case_id=?",(r['run_id'],r['case_id']))
                        self.db.execute("UPDATE attempts SET finished=?,status='NeedsReview',actual='Interrupted during a mutating case: reconcile the fixture before an explicit new run; no automatic repetition.' WHERE id=?",(time.time(),r['id']))
                self.db.execute("UPDATE cases SET state='Pending' WHERE state='Running'")
                self.db.execute("UPDATE attempts SET finished=?,status='Interrupted',actual='Process interrupted; case can be retried.' WHERE finished IS NULL",(time.time(),))
                self.db.execute("UPDATE runs SET state='Paused' WHERE state='Running'")
                self.db.execute('COMMIT')
            except Exception:self.db.execute('ROLLBACK');raise
    def run(self,run):
        r=self.db.execute('SELECT * FROM runs WHERE id=?',(run,)).fetchone()
        if not r:raise ValueError('Run not found.')
        return {**dict(r),'config':json.loads(r['config']),'source':json.loads(r['source'])}
    def runs(self):return [dict(r) for r in self.db.execute('SELECT id,created,state FROM runs ORDER BY created DESC')]
    def state(self,run,state):
        with self.lock:self.db.execute('UPDATE runs SET state=? WHERE id=?',(state,run))
    def next_case(self,run):
        with self.lock:
            r=self.db.execute("SELECT data FROM cases WHERE run_id=? AND state='Pending' ORDER BY ordinal LIMIT 1",(run,)).fetchone()
            return Case.from_dict(json.loads(r['data'])) if r else None
    def begin(self,run,case):
        attempt=uuid.uuid4().hex
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                updated=self.db.execute("UPDATE cases SET state='Running' WHERE run_id=? AND case_id=? AND state='Pending'",(run,case.case_id))
                if not updated.rowcount:raise ValueError('Case is not pending.')
                self.db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?)',(attempt,run,case.case_id,time.time(),None,'Running','', '{}'))
                self.db.execute('COMMIT')
            except Exception:self.db.execute('ROLLBACK');raise
        return attempt
    def commit(self,attempt,status,actual,details,evidence,writeback=False):
        if status not in ('Pass','Fail','Blocked','NeedsReview'):raise ValueError('Invalid result status.')
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                r=self.db.execute('SELECT * FROM attempts WHERE id=?',(attempt,)).fetchone()
                if not r or r['finished'] is not None:raise ValueError('Attempt already committed or missing.')
                self.db.execute('UPDATE attempts SET finished=?,status=?,actual=?,details=? WHERE id=?',(time.time(),status,redact(actual),json.dumps(details),attempt))
                self.db.execute("UPDATE cases SET state='Completed' WHERE run_id=? AND case_id=?",(r['run_id'],r['case_id']))
                for kind,path in evidence:self.db.execute('INSERT INTO evidence VALUES(?,?,?)',(attempt,kind,str(path)))
                if writeback:self.db.execute('INSERT OR IGNORE INTO writebacks VALUES(?,?,?,?,?,?,?)',(uuid.uuid4().hex,attempt,r['run_id'],r['case_id'],'Pending',json.dumps({'status':status,'actual':redact(actual)}),''))
                self.db.execute('COMMIT')
            except Exception:self.db.execute('ROLLBACK');raise
    def results(self,run):
        return [dict(r) for r in self.db.execute('''SELECT c.case_id,c.state,c.data,a.id attempt_id,a.status,a.actual,a.started,a.finished,a.details
          FROM cases c LEFT JOIN attempts a ON a.id=(SELECT id FROM attempts WHERE run_id=c.run_id AND case_id=c.case_id ORDER BY started DESC LIMIT 1)
          WHERE c.run_id=? ORDER BY c.ordinal''',(run,))]
    def event(self,run,kind,message):
        with self.lock:self.db.execute('INSERT INTO events VALUES(?,?,?,?)',(run,time.time(),kind,redact(message)))
    def events(self,run):return [dict(r) for r in self.db.execute('SELECT * FROM events WHERE run_id=? ORDER BY at DESC LIMIT 80',(run,))]
    def chat_add(self,role,content):
        with self.lock:self.db.execute('INSERT INTO chat VALUES(?,?,?,?)',(uuid.uuid4().hex,time.time(),role,redact(content)))
    def chat_history(self):return [dict(r) for r in self.db.execute('SELECT at,role,content FROM chat ORDER BY at DESC LIMIT 60')][::-1]
    def approve(self,case_id,fixture_id,category,action_hash,note=''):
        with self.lock:self.db.execute('INSERT INTO approvals VALUES(?,?,?,?,?,?,?)',(uuid.uuid4().hex,time.time(),case_id,fixture_id,category,action_hash,redact(note)))
    def approval(self,case_id,fixture_id,category,action_hash):
        return self.db.execute('SELECT 1 FROM approvals WHERE case_id=? AND fixture_id=? AND category=? AND action_hash=? ORDER BY at DESC LIMIT 1',(case_id,fixture_id,category,action_hash)).fetchone() is not None
    def put_flow(self,case_hash,actions,assertions):
        with self.lock:self.db.execute('INSERT OR REPLACE INTO flows VALUES(?,?,?,?)',(case_hash,json.dumps(actions),json.dumps(assertions),time.time()))
    def flow(self,case_hash):
        r=self.db.execute('SELECT * FROM flows WHERE case_hash=?',(case_hash,)).fetchone()
        return {'actions':json.loads(r['actions']),'assertions':json.loads(r['assertions'])} if r else None
    def pending_writebacks(self,run):return [dict(r) for r in self.db.execute("SELECT * FROM writebacks WHERE run_id=? AND state!='Done'",(run,))]
    def writeback_state(self,id,state,error=''):
        with self.lock:self.db.execute('UPDATE writebacks SET state=?,error=? WHERE id=?',(state,redact(error),id))
    def close(self):self.db.close()
