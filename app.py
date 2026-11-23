import os, sys, sqlite3, shutil, hashlib, secrets, csv, webbrowser, tempfile
from pathlib import Path
from datetime import date, datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_NAME = 'ICON PUCLIC SCHOOL – School Fee & Transport Management System'
BASE = Path(os.getenv('LOCALAPPDATA', Path.home())) / 'IconPublicSchoolPro'
BASE.mkdir(parents=True, exist_ok=True)
DB = BASE / 'school.db'
RECEIPTS = BASE / 'Receipts'; RECEIPTS.mkdir(exist_ok=True)

DEFAULT_CATS = ['School Tuition Fee','Bus / Transport Fee','Examination Fee','Admission Fee','Annual Fee','Computer Fee','Activity Fee','Library Fee','Sports Fee','Other Charges']

def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def pw_hash(p, salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+'$'+hashlib.pbkdf2_hmac('sha256',p.encode(),salt.encode(),180000).hex()

def init_db():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY, admission TEXT UNIQUE, name TEXT NOT NULL, father TEXT, mother TEXT, class_name TEXT, section TEXT, roll TEXT, phone TEXT, address TEXT, admission_date TEXT, status TEXT DEFAULT 'Active', bus_id INTEGER, photo TEXT);
        CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY,name TEXT UNIQUE,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS fee_rates(id INTEGER PRIMARY KEY,class_name TEXT,category_id INTEGER,amount REAL DEFAULT 0, UNIQUE(class_name,category_id), FOREIGN KEY(category_id) REFERENCES categories(id));
        CREATE TABLE IF NOT EXISTS buses(id INTEGER PRIMARY KEY,bus_no TEXT UNIQUE,driver TEXT,phone TEXT,route TEXT,stops TEXT,stop_fee REAL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS exam_types(id INTEGER PRIMARY KEY,name TEXT,class_name TEXT,amount REAL DEFAULT 0,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,receipt_no TEXT UNIQUE,student_id INTEGER,pay_date TEXT,month_name TEXT,academic_year TEXT,discount REAL DEFAULT 0,fine REAL DEFAULT 0,paid REAL,payment_mode TEXT,notes TEXT,cancelled INTEGER DEFAULT 0,created_by TEXT,FOREIGN KEY(student_id) REFERENCES students(id));
        CREATE TABLE IF NOT EXISTS payment_items(id INTEGER PRIMARY KEY,payment_id INTEGER,category_id INTEGER,category_name TEXT,amount REAL,FOREIGN KEY(payment_id) REFERENCES payments(id),FOREIGN KEY(category_id) REFERENCES categories(id));
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,at TEXT,username TEXT,action TEXT,details TEXT);
        ''')
        if not c.execute('SELECT 1 FROM users').fetchone(): c.execute('INSERT INTO users(username,password,role) VALUES(?,?,?)',('admin',pw_hash('admin123'),'Admin'))
        for x in DEFAULT_CATS: c.execute('INSERT OR IGNORE INTO categories(name) VALUES(?)',(x,))
        for k,v in [('school_name','ICON PUCLIC SCHOOL'),('tagline','School Fee & Transport Management System'),('address',''),('contact',''),('logo','')]: c.execute('INSERT OR IGNORE INTO settings VALUES(?,?)',(k,v))

def setting(k):
    with connect() as c:
        r=c.execute('SELECT value FROM settings WHERE key=?',(k,)).fetchone(); return r['value'] if r else ''

def audit(user,action,details=''):
    with connect() as c: c.execute('INSERT INTO audit(at,username,action,details) VALUES(?,?,?,?)',(datetime.now().isoformat(timespec='seconds'),user,action,details))

class App:
 def __init__(self,root,user,role):
    self.root=root; self.user=user; self.role=role; self.root.title(APP_NAME); self.root.geometry('1250x780'); self.root.minsize(1050,650)
    self.style=ttk.Style(); self.style.theme_use('clam'); self.style.configure('Treeview',rowheight=28,font=('Segoe UI',10)); self.style.configure('Treeview.Heading',font=('Segoe UI',10,'bold')); self.style.configure('TButton',font=('Segoe UI',10),padding=6)
    head=tk.Frame(root,bg='#14243a',height=70); head.pack(fill='x'); tk.Label(head,text='ICON PUCLIC SCHOOL',bg='#14243a',fg='white',font=('Segoe UI',19,'bold')).pack(anchor='w',padx=20,pady=(10,0)); tk.Label(head,text='School Fee & Transport Management System  •  '+user+' ('+role+')',bg='#14243a',fg='#c8d6e5',font=('Segoe UI',9)).pack(anchor='w',padx=21)
    self.nb=ttk.Notebook(root); self.nb.pack(fill='both',expand=True,padx=12,pady=12)
    self.make_dashboard(); self.make_students(); self.make_collect(); self.make_buses(); self.make_categories(); self.make_reports(); self.make_settings()
    self.refresh_all()
 def page(self,title):
    f=ttk.Frame(self.nb,padding=12); self.nb.add(f,text=title); return f
 def tree(self,parent,cols,widths=None):
    t=ttk.Treeview(parent,columns=cols,show='headings');
    for i,x in enumerate(cols): t.heading(x,text=x); t.column(x,width=(widths[i] if widths else 130),anchor='w')
    t.pack(fill='both',expand=True,pady=8); return t
 def make_dashboard(self):
    f=self.page('Dashboard'); ttk.Label(f,text='School Overview',font=('Segoe UI',18,'bold')).pack(anchor='w')
    self.stats=tk.Frame(f); self.stats.pack(fill='x',pady=12)
    self.statlabels={}
    for title in ['Total Students','Active Students','Inactive Students','Total Collected','Pending Payments','Today Collection']:
      card=tk.Frame(self.stats,bg='#edf3f9',padx=16,pady=13); card.pack(side='left',fill='both',expand=True,padx=5); tk.Label(card,text=title,bg='#edf3f9',fg='#526579',font=('Segoe UI',9)).pack(anchor='w'); v=tk.Label(card,text='0',bg='#edf3f9',fg='#14243a',font=('Segoe UI',17,'bold')); v.pack(anchor='w'); self.statlabels[title]=v
    ttk.Label(f,text='Recent Transactions',font=('Segoe UI',13,'bold')).pack(anchor='w',pady=(15,0)); self.dtree=self.tree(f,['Receipt','Date','Student','Class','Month','Paid','Mode'],[120,110,190,90,120,100,110])
 def make_students(self):
    f=self.page('Students'); bar=ttk.Frame(f); bar.pack(fill='x'); ttk.Label(bar,text='Student Records',font=('Segoe UI',16,'bold')).pack(side='left'); ttk.Button(bar,text='Add Student',command=self.student_form).pack(side='right'); self.ssearch=tk.StringVar(); ttk.Entry(bar,textvariable=self.ssearch,width=30).pack(side='right',padx=8); ttk.Button(bar,text='Search',command=self.refresh_students).pack(side='right')
    self.stree=self.tree(f,['ID','Admission No.','Student Name','Father','Class','Section','Phone','Status','Bus'],[55,130,190,150,80,80,120,85,100]); self.stree.bind('<Double-1>',lambda e:self.student_form(self.selected(self.stree)))
    ttk.Button(f,text='Delete Selected Student',command=self.delete_student).pack(anchor='e')
 def selected(self,t):
    s=t.selection(); return t.item(s[0])['values'][0] if s else None
 def student_form(self,sid=None):
    old=None
    if sid:
      with connect() as c: old=c.execute('SELECT * FROM students WHERE id=?',(sid,)).fetchone()
    w=tk.Toplevel(self.root); w.title('Student Details'); w.geometry('480x650'); w.transient(self.root); w.grab_set(); vars={}
    fields=[('Admission Number','admission'),('Student Name','name'),("Father's Name",'father'),("Mother's Name",'mother'),('Class','class_name'),('Section','section'),('Roll Number','roll'),('Contact Number','phone'),('Address','address'),('Admission Date (YYYY-MM-DD)','admission_date')]
    for label,key in fields:
      ttk.Label(w,text=label).pack(anchor='w',padx=18,pady=(7,0)); v=tk.StringVar(value=(old[key] or '') if old else (date.today().isoformat() if key=='admission_date' else '')); ttk.Entry(w,textvariable=v).pack(fill='x',padx=18); vars[key]=v
    ttk.Label(w,text='Status').pack(anchor='w',padx=18,pady=(7,0)); status=tk.StringVar(value=old['status'] if old else 'Active'); ttk.Combobox(w,textvariable=status,values=['Active','Inactive'],state='readonly').pack(fill='x',padx=18)
    def save():
      d={k:v.get().strip() for k,v in vars.items()}
      if not d['admission'] or not d['name'] or not d['class_name']: messagebox.showerror('Required','Admission number, name and class are required',parent=w); return
      try:
       with connect() as c:
        if sid: c.execute('UPDATE students SET admission=?,name=?,father=?,mother=?,class_name=?,section=?,roll=?,phone=?,address=?,admission_date=?,status=? WHERE id=?',tuple(d[k] for _,k in fields)+(status.get(),sid))
        else: c.execute('INSERT INTO students(admission,name,father,mother,class_name,section,roll,phone,address,admission_date,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)',tuple(d[k] for _,k in fields)+(status.get(),))
      except Exception as e:
       # Explicit parameter path for new records
       if not sid:
        try:
         with connect() as c: c.execute('INSERT INTO students(admission,name,father,mother,class_name,section,roll,phone,address,admission_date,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(*[d[k] for _,k in fields],status.get()))
        except Exception as e2: messagebox.showerror('Save failed',str(e2),parent=w); return
       else: messagebox.showerror('Save failed',str(e),parent=w); return
      audit(self.user,'Student saved',d['admission']); w.destroy(); self.refresh_all()
    ttk.Button(w,text='Save Student',command=save).pack(pady=16)
 def delete_student(self):
    sid=self.selected(self.stree)
    if not sid: return
    if self.role!='Admin': messagebox.showwarning('Permission','Only Admin can delete students'); return
    if messagebox.askyesno('Confirm','Delete this student? Payment history will prevent deletion if linked.'):
      try:
       with connect() as c: c.execute('DELETE FROM students WHERE id=?',(sid,))
       audit(self.user,'Student deleted',str(sid)); self.refresh_all()
      except Exception as e: messagebox.showerror('Cannot delete',str(e))
 def make_collect(self):
    f=self.page('Collect Payment'); ttk.Label(f,text='Combined Fee Collection',font=('Segoe UI',17,'bold')).pack(anchor='w')
    top=ttk.Frame(f); top.pack(fill='x',pady=10); self.pay_student=tk.StringVar(); self.student_combo=ttk.Combobox(top,textvariable=self.pay_student,width=42,state='readonly'); self.student_combo.pack(side='left',padx=5); self.month=tk.StringVar(value=date.today().strftime('%B')); ttk.Combobox(top,textvariable=self.month,values=['January','February','March','April','May','June','July','August','September','October','November','December'],width=14,state='readonly').pack(side='left',padx=5); self.year=tk.StringVar(value=str(date.today().year)); ttk.Entry(top,textvariable=self.year,width=10).pack(side='left',padx=5); ttk.Button(top,text='Load Fees',command=self.load_fee_rows).pack(side='left',padx=5)
    self.payrows=tk.Frame(f); self.payrows.pack(fill='both',expand=True); self.pay_total=tk.StringVar(value='Selected total: ₹0.00'); ttk.Label(f,textvariable=self.pay_total,font=('Segoe UI',13,'bold')).pack(anchor='e',pady=5)
    row=ttk.Frame(f); row.pack(fill='x'); ttk.Label(row,text='Discount ₹').pack(side='left'); self.discount=tk.StringVar(value='0'); ttk.Entry(row,textvariable=self.discount,width=10).pack(side='left',padx=5); ttk.Label(row,text='Late Fine ₹').pack(side='left'); self.fine=tk.StringVar(value='0'); ttk.Entry(row,textvariable=self.fine,width=10).pack(side='left',padx=5); ttk.Label(row,text='Paid Amount ₹').pack(side='left'); self.paid=tk.StringVar(); ttk.Entry(row,textvariable=self.paid,width=12).pack(side='left',padx=5); ttk.Label(row,text='Mode').pack(side='left'); self.mode=tk.StringVar(value='Cash'); ttk.Combobox(row,textvariable=self.mode,values=['Cash','UPI','Bank Transfer','Cheque','Other'],width=15,state='readonly').pack(side='left',padx=5); ttk.Button(row,text='Generate Combined Receipt',command=self.save_payment).pack(side='right')
    self.fee_vars=[]
 def load_fee_rows(self):
    if not self.pay_student.get(): messagebox.showwarning('Select student','Select a student first'); return
    sid=int(self.pay_student.get().split(' | ')[0]);
    with connect() as c:
      s=c.execute('SELECT * FROM students WHERE id=?',(sid,)).fetchone(); cats=c.execute('SELECT * FROM categories WHERE active=1').fetchall(); rates={r['category_id']:r['amount'] for r in c.execute('SELECT * FROM fee_rates WHERE class_name=?',(s['class_name'],))}; bus=c.execute('SELECT stop_fee FROM buses WHERE id=?',(s['bus_id'],)).fetchone() if s['bus_id'] else None
      # Outstanding amounts are computed per category from assessed fees minus successful payments.
      paid={r['category_id']:r['v'] for r in c.execute('SELECT pi.category_id,SUM(pi.amount) v FROM payment_items pi JOIN payments p ON p.id=pi.payment_id WHERE p.student_id=? AND p.cancelled=0 GROUP BY pi.category_id',(sid,))}
    for x in self.payrows.winfo_children(): x.destroy()
    self.fee_vars=[]; ttk.Label(self.payrows,text='Select the fee heads being paid. Enter the amount to collect; unpaid heads remain pending.',foreground='#526579').pack(anchor='w',pady=5)
    for cat in cats:
      amount=float(rates.get(cat['id'],0));
      if cat['name']=='Bus / Transport Fee' and bus: amount=float(bus['stop_fee'])
      if cat['name']=='Examination Fee':
       with connect() as c: ex=c.execute('SELECT SUM(amount) n FROM exam_types WHERE class_name=? AND active=1',(s['class_name'],)).fetchone()['n'] or 0
       amount=max(amount,float(ex))
      prior=float(paid.get(cat['id'],0)); outstanding=max(0,amount-prior)
      if amount==0 and outstanding==0: continue
      v=tk.BooleanVar(value=outstanding>0); a=tk.StringVar(value=f'{outstanding:.2f}'); line=ttk.Frame(self.payrows); line.pack(fill='x',pady=3); ttk.Checkbutton(line,text=cat['name'],variable=v).pack(side='left'); ttk.Label(line,text=f'Assessed ₹{amount:.2f}  •  Previously paid ₹{prior:.2f}  •  Due ₹{outstanding:.2f}',width=70).pack(side='left',padx=8); ttk.Entry(line,textvariable=a,width=14).pack(side='right'); self.fee_vars.append((cat['id'],cat['name'],v,a))
    self.update_total()
    for _,_,v,a in self.fee_vars: v.trace_add('write',lambda *args:self.update_total()); a.trace_add('write',lambda *args:self.update_total())
 def update_total(self):
    total=0
    for _,_,v,a in getattr(self,'fee_vars',[]):
      if v.get():
       try: total+=float(a.get() or 0)
       except: pass
    self.pay_total.set(f'Selected total: ₹{total:.2f}')
 def save_payment(self):
    if not self.pay_student.get(): messagebox.showwarning('Student','Select student'); return
    items=[]
    for cid,name,v,a in self.fee_vars:
      if v.get():
       try: val=float(a.get())
       except: messagebox.showerror('Amount','Enter valid amount'); return
       if val<0: messagebox.showerror('Amount','Amount cannot be negative'); return
       if val>0: items.append((cid,name,val))
    if not items: messagebox.showwarning('Fees','Select at least one fee'); return
    try: discount=float(self.discount.get() or 0); fine=float(self.fine.get() or 0); paid=float(self.paid.get() or (sum(x[2] for x in items)-discount+fine))
    except: messagebox.showerror('Amount','Invalid discount, fine or paid amount'); return
    total=sum(x[2] for x in items)-discount+fine
    if discount<0 or fine<0 or paid<0 or paid>total+0.001: messagebox.showerror('Amount','Check discount/fine/paid amount. Paid amount cannot exceed payable total.'); return
    sid=int(self.pay_student.get().split(' | ')[0]); receipt='IPS-'+datetime.now().strftime('%y%m%d-%H%M%S')+'-'+secrets.token_hex(2).upper()
    with connect() as c:
      c.execute('INSERT INTO payments(receipt_no,student_id,pay_date,month_name,academic_year,discount,fine,paid,payment_mode,created_by) VALUES(?,?,?,?,?,?,?,?,?,?)',(receipt,sid,date.today().isoformat(),self.month.get(),self.year.get(),discount,fine,paid,self.mode.get(),self.user)); pid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
      for cid,name,val in items: c.execute('INSERT INTO payment_items(payment_id,category_id,category_name,amount) VALUES(?,?,?,?)',(pid,cid,name,val))
      s=c.execute('SELECT * FROM students WHERE id=?',(sid,)).fetchone()
    audit(self.user,'Payment collected',receipt); self.make_receipt(pid); self.refresh_all(); messagebox.showinfo('Payment saved',f'Receipt {receipt} generated.');
 def make_receipt(self,pid):
    with connect() as c:
      p=c.execute('SELECT p.*,s.name,s.admission,s.class_name,s.section FROM payments p JOIN students s ON s.id=p.student_id WHERE p.id=?',(pid,)).fetchone(); items=c.execute('SELECT * FROM payment_items WHERE payment_id=?',(pid,)).fetchall()
    subtotal=sum(x['amount'] for x in items); total=subtotal-p['discount']+p['fine']; balance=max(0,total-p['paid'])
    html=f'''<html><head><meta charset="utf-8"><style>body{{font-family:Arial;margin:35px;color:#17283d}}.box{{border:2px solid #17283d;padding:25px}}h1{{text-align:center;margin:0}}h3{{text-align:center;margin:6px}}table{{width:100%;border-collapse:collapse;margin-top:20px}}td,th{{border:1px solid #bbb;padding:9px;text-align:left}}.r{{text-align:right}}.foot{{margin-top:50px;display:flex;justify-content:space-between}}</style></head><body><div class="box"><h1>ICON PUCLIC SCHOOL</h1><h3>School Fee &amp; Transport Management System</h3><p style="text-align:center">{setting('address')} | {setting('contact')}</p><hr><b>Receipt No:</b> {p['receipt_no']} <span style="float:right"><b>Payment Date:</b> {p['pay_date']}</span><p><b>Student:</b> {p['name']} &nbsp; <b>Admission No:</b> {p['admission']}<br><b>Class:</b> {p['class_name']} {p['section'] or ''} &nbsp; <b>Month:</b> {p['month_name']} {p['academic_year']}</p><table><tr><th>Fee Particulars</th><th class="r">Amount</th></tr>{''.join(f"<tr><td>{x['category_name']}</td><td class='r'>₹{x['amount']:.2f}</td></tr>" for x in items)}<tr><td>Subtotal</td><td class="r">₹{subtotal:.2f}</td></tr><tr><td>Discount</td><td class="r">₹{p['discount']:.2f}</td></tr><tr><td>Late Fine</td><td class="r">₹{p['fine']:.2f}</td></tr><tr><th>Grand Total</th><th class="r">₹{total:.2f}</th></tr><tr><th>Paid Amount ({p['payment_mode']})</th><th class="r">₹{p['paid']:.2f}</th></tr><tr><th>Remaining Balance</th><th class="r">₹{balance:.2f}</th></tr></table><div class="foot"><span>Parent / Student Signature</span><span>Authorized Signature</span></div></div></body></html>'''
    path=RECEIPTS/(p['receipt_no']+'.html'); path.write_text(html,encoding='utf-8'); webbrowser.open(path.as_uri()); return path
 def make_buses(self):
    f=self.page('Bus Management'); bar=ttk.Frame(f); bar.pack(fill='x'); ttk.Label(bar,text='Buses & Routes',font=('Segoe UI',16,'bold')).pack(side='left'); ttk.Button(bar,text='Add Bus',command=self.bus_form).pack(side='right'); self.btree=self.tree(f,['ID','Bus Number','Driver','Phone','Route','Stops','Stop Fee'],[50,130,160,120,150,260,100])
 def bus_form(self):
    w=tk.Toplevel(self.root); w.title('Add Bus'); w.geometry('400x400'); v={}
    for label,key in [('Bus Number','bus_no'),('Driver Name','driver'),('Driver Contact','phone'),('Route Name','route'),('Bus Stops (comma separated)','stops'),('Stop-wise Monthly Fee','stop_fee')]:
      ttk.Label(w,text=label).pack(anchor='w',padx=15,pady=(8,0)); v[key]=tk.StringVar(); ttk.Entry(w,textvariable=v[key]).pack(fill='x',padx=15)
    def save():
      try:
       with connect() as c: c.execute('INSERT INTO buses(bus_no,driver,phone,route,stops,stop_fee) VALUES(?,?,?,?,?,?)',(v['bus_no'].get(),v['driver'].get(),v['phone'].get(),v['route'].get(),v['stops'].get(),float(v['stop_fee'].get() or 0)))
       w.destroy(); self.refresh_all()
      except Exception as e: messagebox.showerror('Save failed',str(e),parent=w)
    ttk.Button(w,text='Save Bus',command=save).pack(pady=15)
 def make_categories(self):
    f=self.page('Fee Setup'); ttk.Label(f,text='Fee Categories & Class-wise Rates',font=('Segoe UI',16,'bold')).pack(anchor='w'); row=ttk.Frame(f); row.pack(fill='x',pady=8); self.catname=tk.StringVar(); ttk.Entry(row,textvariable=self.catname,width=30).pack(side='left'); ttk.Button(row,text='Add Category',command=self.add_category).pack(side='left',padx=5); self.ctree=self.tree(f,['ID','Category','Active'],[80,400,100]); ttk.Label(f,text='Set class-wise amount for a category').pack(anchor='w'); r=ttk.Frame(f); r.pack(fill='x'); self.rateclass=tk.StringVar(); self.ratecat=tk.StringVar(); self.rateamount=tk.StringVar(); ttk.Entry(r,textvariable=self.rateclass,width=15).pack(side='left',padx=4); self.ratecatcombo=ttk.Combobox(r,textvariable=self.ratecat,width=30,state='readonly'); self.ratecatcombo.pack(side='left',padx=4); ttk.Entry(r,textvariable=self.rateamount,width=12).pack(side='left',padx=4); ttk.Button(r,text='Save Class Fee',command=self.save_rate).pack(side='left')
 def add_category(self):
    try:
     with connect() as c: c.execute('INSERT INTO categories(name) VALUES(?)',(self.catname.get().strip(),))
     self.catname.set(''); self.refresh_all()
    except Exception as e: messagebox.showerror('Category',str(e))
 def save_rate(self):
    try:
     with connect() as c:
      cat=c.execute('SELECT id FROM categories WHERE name=?',(self.ratecat.get(),)).fetchone(); c.execute('INSERT INTO fee_rates(class_name,category_id,amount) VALUES(?,?,?) ON CONFLICT(class_name,category_id) DO UPDATE SET amount=excluded.amount',(self.rateclass.get().strip(),cat['id'],float(self.rateamount.get())))
     messagebox.showinfo('Saved','Class fee rate saved')
    except Exception as e: messagebox.showerror('Fee setup',str(e))
 def make_reports(self):
    f=self.page('Reports & Backup'); ttk.Label(f,text='Reports, Exports & Database Backup',font=('Segoe UI',16,'bold')).pack(anchor='w'); ttk.Button(f,text='Export All Payments to CSV',command=self.export_csv).pack(anchor='w',pady=8); ttk.Button(f,text='Export Student List to CSV',command=self.export_students).pack(anchor='w',pady=8); ttk.Button(f,text='Backup Database',command=self.backup).pack(anchor='w',pady=8); ttk.Button(f,text='Restore Database Backup',command=self.restore).pack(anchor='w',pady=8); ttk.Label(f,text=f'Database location: {DB}').pack(anchor='w',pady=15)
 def export_csv(self):
    path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')]);
    if not path:return
    with connect() as c: rows=c.execute('SELECT p.receipt_no,p.pay_date,s.admission,s.name,s.class_name,p.month_name,p.academic_year,pi.category_name,pi.amount,p.discount,p.fine,p.paid,p.payment_mode,p.cancelled FROM payments p JOIN students s ON s.id=p.student_id JOIN payment_items pi ON pi.payment_id=p.id ORDER BY p.id DESC').fetchall()
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
      w=csv.writer(f); w.writerow(rows[0].keys() if rows else ['No records']); [w.writerow(tuple(r)) for r in rows]
    messagebox.showinfo('Export','Payment report exported')
 def export_students(self):
    path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')]);
    if not path:return
    with connect() as c: rows=c.execute('SELECT admission,name,father,mother,class_name,section,roll,phone,address,admission_date,status FROM students').fetchall()
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
      w=csv.writer(f); w.writerow(rows[0].keys() if rows else ['No records']); [w.writerow(tuple(r)) for r in rows]
    messagebox.showinfo('Export','Student list exported')
 def backup(self):
    p=filedialog.asksaveasfilename(defaultextension='.db',filetypes=[('SQLite database','*.db')]);
    if p: shutil.copy2(DB,p); messagebox.showinfo('Backup','Database backup created')
 def restore(self):
    if self.role!='Admin': messagebox.showwarning('Permission','Admin only'); return
    p=filedialog.askopenfilename(filetypes=[('SQLite database','*.db')]);
    if p and messagebox.askyesno('Restore','Replace current database? Close app and keep a backup first.'):
      shutil.copy2(p,DB); messagebox.showinfo('Restore','Restored. Please restart the software.'); self.root.destroy()
 def make_settings(self):
    f=self.page('School Settings'); ttk.Label(f,text='School Branding & Admin Settings',font=('Segoe UI',16,'bold')).pack(anchor='w'); self.setvars={}
    for label,key in [('School Name (fixed branding)','school_name'),('Address','address'),('Contact Number','contact'),('Logo File Path','logo')]:
      ttk.Label(f,text=label).pack(anchor='w',pady=(12,0)); v=tk.StringVar(value=setting(key)); ttk.Entry(f,textvariable=v,width=80).pack(anchor='w'); self.setvars[key]=v
    ttk.Button(f,text='Browse Logo',command=self.browse_logo).pack(anchor='w',pady=6); ttk.Button(f,text='Save School Details',command=self.save_settings).pack(anchor='w',pady=8); ttk.Separator(f).pack(fill='x',pady=15); ttk.Label(f,text='Default Admin Login: admin / admin123 — change this password before real use.',foreground='#a33').pack(anchor='w'); ttk.Button(f,text='Change Admin Password',command=self.change_password).pack(anchor='w',pady=8)
 def browse_logo(self):
    p=filedialog.askopenfilename(filetypes=[('Images','*.png *.jpg *.jpeg')]);
    if p:self.setvars['logo'].set(p)
 def save_settings(self):
    with connect() as c:
      for k,v in self.setvars.items(): c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,v.get()))
    messagebox.showinfo('Saved','School details saved')
 def change_password(self):
    w=tk.Toplevel(self.root); w.title('Change Password'); w.geometry('320x190'); a=tk.StringVar(); b=tk.StringVar(); ttk.Label(w,text='New Password').pack(pady=5); ttk.Entry(w,textvariable=a,show='*').pack(); ttk.Label(w,text='Confirm Password').pack(pady=5); ttk.Entry(w,textvariable=b,show='*').pack()
    def save():
      if len(a.get())<8 or a.get()!=b.get(): messagebox.showerror('Password','Passwords must match and be at least 8 characters'); return
      with connect() as c:c.execute('UPDATE users SET password=? WHERE username=?',(pw_hash(a.get()),self.user))
      w.destroy(); messagebox.showinfo('Password','Password updated')
    ttk.Button(w,text='Update',command=save).pack(pady=10)
 def refresh_students(self):
    for x in self.stree.get_children(): self.stree.delete(x)
    q='%'+self.ssearch.get().strip()+'%'
    with connect() as c: rows=c.execute('SELECT s.*,b.bus_no FROM students s LEFT JOIN buses b ON b.id=s.bus_id WHERE s.name LIKE ? OR s.admission LIKE ? ORDER BY s.id DESC',(q,q)).fetchall()
    for r in rows:self.stree.insert('', 'end',values=(r['id'],r['admission'],r['name'],r['father'],r['class_name'],r['section'],r['phone'],r['status'],r['bus_no'] or ''))
 def refresh_all(self):
    self.refresh_students()
    with connect() as c:
      students=c.execute('SELECT COUNT(*) n FROM students').fetchone()['n']; active=c.execute("SELECT COUNT(*) n FROM students WHERE status='Active'").fetchone()['n']; inactive=students-active; collected=c.execute('SELECT COALESCE(SUM(paid),0) n FROM payments WHERE cancelled=0').fetchone()['n']; today=c.execute('SELECT COALESCE(SUM(paid),0) n FROM payments WHERE cancelled=0 AND pay_date=?',(date.today().isoformat(),)).fetchone()['n']; rows=c.execute('SELECT p.receipt_no,p.pay_date,s.name,s.class_name,p.month_name,p.paid,p.payment_mode FROM payments p JOIN students s ON s.id=p.student_id WHERE p.cancelled=0 ORDER BY p.id DESC LIMIT 15').fetchall(); ss=c.execute('SELECT id,admission,name,class_name FROM students ORDER BY name').fetchall(); cats=c.execute('SELECT * FROM categories').fetchall(); buses=c.execute('SELECT * FROM buses').fetchall()
    for k,v in [('Total Students',students),('Active Students',active),('Inactive Students',inactive),('Total Collected',f'₹{collected:,.2f}'),('Pending Payments','Track by fee head'),('Today Collection',f'₹{today:,.2f}')]: self.statlabels[k].config(text=str(v))
    for x in self.dtree.get_children():self.dtree.delete(x)
    for r in rows:self.dtree.insert('','end',values=tuple(r))
    self.student_combo['values']=[f"{r['id']} | {r['admission']} | {r['name']} | {r['class_name']}" for r in ss]
    self.ratecatcombo['values']=[r['name'] for r in cats]
    for x in self.btree.get_children():self.btree.delete(x)
    for r in buses:self.btree.insert('','end',values=(r['id'],r['bus_no'],r['driver'],r['phone'],r['route'],r['stops'],r['stop_fee']))
    for x in self.ctree.get_children():self.ctree.delete(x)
    for r in cats:self.ctree.insert('','end',values=(r['id'],r['name'],'Yes' if r['active'] else 'No'))

class Login:
 def __init__(self,root):
    self.root=root; root.title('ICON PUCLIC SCHOOL – Login'); root.geometry('420x360'); root.resizable(False,False); root.configure(bg='#edf3f9'); box=tk.Frame(root,bg='white',padx=28,pady=25); box.pack(fill='both',expand=True,padx=25,pady=25); tk.Label(box,text='ICON PUCLIC SCHOOL',font=('Segoe UI',18,'bold'),bg='white',fg='#14243a').pack(pady=(10,0)); tk.Label(box,text='School Fee & Transport Management System',bg='white',fg='#607080').pack(pady=(0,20)); self.u=tk.StringVar(value='admin'); self.p=tk.StringVar(); ttk.Label(box,text='Username').pack(anchor='w'); ttk.Entry(box,textvariable=self.u).pack(fill='x',pady=5); ttk.Label(box,text='Password').pack(anchor='w'); ttk.Entry(box,textvariable=self.p,show='*').pack(fill='x',pady=5); ttk.Button(box,text='Login',command=self.login).pack(fill='x',pady=18); tk.Label(box,text='First login: admin / admin123',bg='white',fg='#a33').pack()
 def login(self):
    with connect() as c:r=c.execute('SELECT * FROM users WHERE username=?',(self.u.get(),)).fetchone()
    ok=False
    if r:
      try:salt,h=r['password'].split('$'); ok=hashlib.pbkdf2_hmac('sha256',self.p.get().encode(),salt.encode(),180000).hex()==h
      except: pass
    if not ok:messagebox.showerror('Login failed','Invalid username or password'); return
    role=r['role']; username=self.u.get(); self.root.destroy(); win=tk.Tk(); App(win,username,role); win.mainloop()

if __name__=='__main__':
 init_db(); root=tk.Tk(); Login(root); root.mainloop()
