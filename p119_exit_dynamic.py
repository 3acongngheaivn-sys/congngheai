"""Safe exit confirmation and lightweight animated 3A advertisement."""
import os,sys,tkinter as tk,random,math,threading
from PIL import Image,ImageTk

BG='#151C27'; CARD='#202B3B'; GOLD='#FFC66B'; LIGHT='#F6F8FC'; MUTED='#B9C6D5'

def asset(name):
    base=getattr(sys,'_MEIPASS',os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base,'assets',name)

def confirm_close(root, version='P119', busy=False):
    win=tk.Toplevel(root);win.title('XÁC NHẬN THOÁT — QUẢNG CÁO 3A');win.configure(bg=BG)
    win.resizable(False,False);win.transient(root)
    result={'exit':False};state={'running':True,'frame':0,'job':None}
    w,h=760,510
    root.update_idletasks()
    x=root.winfo_rootx()+max(0,(root.winfo_width()-w)//2)
    y=root.winfo_rooty()+max(0,(root.winfo_height()-h)//2)
    win.geometry('%dx%d+%d+%d'%(w,h,x,y))
    def finish(leave=False):
        result['exit']=leave;state['running']=False
        if state['job'] is not None:
            try:win.after_cancel(state['job'])
            except tk.TclError:pass
        win.destroy()
    win.protocol('WM_DELETE_WINDOW',finish)
    win.bind('<Escape>',lambda e:finish())
    win.bind('<Return>',lambda e:finish())
    top=tk.Frame(win,bg=CARD,padx=20,pady=14);top.pack(fill='x',padx=14,pady=(14,0))
    try:
        im=Image.open(asset('3a_logo.png')).convert('RGBA');im.thumbnail((145,105),Image.Resampling.LANCZOS)
        photo=ImageTk.PhotoImage(im,master=win)
        l=tk.Label(top,image=photo,bg='white',padx=6,pady=6);l.image=photo;l.pack(side='left',padx=(0,18))
    except (OSError,tk.TclError,ValueError):
        tk.Label(top,text='3A',bg=CARD,fg='#FF8420',font=('Segoe UI',34,'bold')).pack(side='left',padx=(0,18))
    info=tk.Frame(top,bg=CARD);info.pack(side='left',fill='both',expand=True)
    tk.Label(info,text='THIẾT KẾ IN ẤN QUẢNG CÁO 3A',bg=CARD,fg=GOLD,font=('Segoe UI',15,'bold'),anchor='w').pack(fill='x')
    for t in ('ĐT: 0987620727 - 0979400 417',
              'Chuyên: IN Quảng Cáo - Khắc Dấu - Laser Siêu Tốc - Biển hiệu',
              'Đc: 34 Kha Vạn Cân, KP. Bình Đường 2,',
              'Phường Dĩ An, TP. Hồ Chí Minh'):
        tk.Label(info,text=t,bg=CARD,fg=LIGHT,font=('Segoe UI',9),anchor='w').pack(fill='x',pady=2)
    canvas=tk.Canvas(win,height=75,bg=BG,highlightthickness=0);canvas.pack(fill='x',padx=14,pady=(4,2))
    # Lightweight confetti fireworks + animated applause (visual).
    rng=random.Random(119)
    sparks=[]
    for k in range(42):
        cx=145 if k<21 else 580
        cy=30
        angle=2*math.pi*(k%21)/21
        speed=0.8+0.65*(k%4)
        obj=canvas.create_oval(cx,cy,cx+4,cy+4,fill=['#FF9C48','#FFD47E','#4AC6C4','#75D0A5','#C6A2F2'][k%5],outline='')
        sparks.append((obj,cx,cy,math.cos(angle)*speed,math.sin(angle)*speed,k))
    applause=canvas.create_text(365,36,text='👏  ✨  👏',fill='#FFD47E',font=('Segoe UI Emoji',17,'bold'))
    colors=['#FF9C48','#FFD47E','#4AC6C4','#75D0A5','#C6A2F2']
    dots=[]
    for i in range(17):
        xx=28+i*42; yy=11+(i*7)%24
        obj=canvas.create_oval(xx,yy,xx+4,yy+4,fill=colors[i%len(colors)],outline='')
        dots.append((obj,xx,yy,i))
    def play_applause():
        if sys.platform != 'win32':return
        def worker():
            try:
                import winsound
                winsound.PlaySound(asset('3a_applause.wav'),winsound.SND_FILENAME)
            except (OSError,RuntimeError,AttributeError):pass
        threading.Thread(target=worker,daemon=True).start()
    play_applause()
    def animate():
        if not state['running'] or not win.winfo_exists():return
        state['frame']+=1;f=state['frame']
        # First ~2.5 seconds: expanding confetti; no permanent CPU-heavy effect.
        for obj,cx,cy,vx,vy,k in sparks:
            t=min(f,27)
            px=cx+vx*t*2.7
            py=cy+vy*t*1.15+0.025*t*t
            canvas.coords(obj,px,py,px+4,py+4)
            if f>32:canvas.itemconfigure(obj,state='hidden')
        canvas.itemconfigure(applause,text=('👏  ✨  👏' if f%12<6 else '✨  👏  ✨'))
        for obj,x,y,i in dots:
            dy=((f+i*5)%24)-12
            canvas.coords(obj,x,y+dy*.32,x+4,y+dy*.32)
        state['job']=win.after(120,animate)
    animate()
    tk.Label(win,text='BẠN MUỐN THOÁT CHƯƠNG TRÌNH?',bg=BG,fg=GOLD,font=('Segoe UI',17,'bold')).pack(pady=(2,6))
    tk.Label(win,text='AI Font Finder PRO đang sẵn sàng phục vụ bạn!',bg=BG,fg=LIGHT,font=('Segoe UI',11)).pack()
    tk.Label(win,text='Nếu vừa bấm nhầm dấu X, hãy chọn Ở LẠI để tiếp tục.',bg=BG,fg=MUTED,font=('Segoe UI',10)).pack(pady=(5,0))
    if busy:
        tk.Label(win,text='LƯU Ý: Đang có tác vụ xử lý. Thoát có thể làm gián đoạn công việc.',bg=BG,fg='#FFAE9B',font=('Segoe UI',9,'bold')).pack(pady=(5,0))
    bar=tk.Frame(win,bg=BG);bar.pack(fill='x',padx=22,pady=(22,9))
    stay=tk.Button(bar,text='✓  Ở LẠI · TIẾP TỤC',command=finish,bg='#236A51',fg='white',activebackground='#2D8768',activeforeground='white',font=('Segoe UI',11,'bold'),height=2,bd=0,cursor='hand2')
    stay.pack(side='left',fill='x',expand=True,padx=(0,7))
    tk.Button(bar,text='THOÁT CHƯƠNG TRÌNH',command=lambda:finish(True),bg='#913F49',fg='white',activebackground='#B34D5A',activeforeground='white',font=('Segoe UI',11,'bold'),height=2,bd=0,cursor='hand2').pack(side='left',fill='x',expand=True,padx=(7,0))
    tk.Label(win,text='3A  •  '+version+'  •  BUSINESS PRO',bg=BG,fg=MUTED,font=('Segoe UI',8)).pack(side='bottom',pady=(0,10))
    win.grab_set();stay.focus_set();root.wait_window(win)
    return result['exit']
