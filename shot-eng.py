import configparser
import ctypes
import json
import os
import re
import subprocess
import sys
import threading
import time
from hashlib import md5
from math import sin
from tkinter import *
from tkinter.messagebox import *
from urllib import parse, request

import clipboard
import pygetwindow
import pytesseract
import requests
from PIL import Image, ImageDraw, ImageGrab, ImageTk
from pygtrans import Translate

"""
sentence: text got from the screen
transText: translated text
ifNewSentence: if successfully get new text
ifNewTranslate: if successfully translate
translateSource: translation source
scale: screen scale
"""

sentence = ""
transText = ""
ifNewSentence = False
ifNewTranslate = False
translateSource = 1
IPA=None
translaterResult = None
scale=1

# dirname: The working directory of the python script
dirname = ""
if getattr(sys, "frozen", False):  # 判断是以打包成EXE还是PY方式执行
    # 如果程序以打包形式运行，获取可执行文件的路径
    dirname, filename = os.path.split(os.path.abspath(sys.executable))
    # 生成可执行文件路径下的tesseract.exe的绝对路径
    filename = dirname + r"\tesseract.exe"
    _path = os.path.join(sys._MEIPASS, filename)
    # _path = os.path.join(sys._MEIPASS,  r"tesseract.exe")
    print(_path)
    pytesseract.pytesseract.tesseract_cmd = _path
    # print('1',pytesseract.pytesseract.tesseract_cmd)
    # the .exe will look here
else:
    # 以.py方式运行
    dirname = os.path.dirname(os.path.realpath(__file__))
    pytesseract.pytesseract.tesseract_cmd =  r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    # print('2',pytesseract.pytesseract.tesseract_cmd)

img=Image.open(dirname +  r'\cc.dat')
img=img.resize((140,140))
myphotoimg=None



def get_IPA(word):    # get IPA from Cambridge.org, return [UK_IPA,US_IPA]
    t = 'https://dictionary.cambridge.org/dictionary/english/'+word
    header= {'User-Agent':"Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36"}   
    r=requests.get(t, headers=header)          
    
    ipa=re.findall('</span><span class="pron dpron">/<span class="ipa dipa lpr-2 lpl-1">(.*)</span>/</span></span>',r.text)
    if len(ipa)>=2:
        for i,k in enumerate(ipa):
            if k.find('</span>/</span></span>'):
                try:
                    ipa[i]=re.findall('(.*)</span>/</span></span>',ipa[i])[0]
                except:
                    pass
            ipa[i]=ipa[i].replace('<span class="sp dsp">','(').replace('</span>',')')

    return ['/'+ipa[0]+'/','/'+ipa[1]+'/']



# CreateToolTip类是为了生成控件的hint
# https://stackoverflow.com/questions/3221956/how-do-i-display-tooltips-in-tkinter
class CreateToolTip(object):
    """
    create a tooltip for a given widget
    """

    def __init__(self, widget, text="widget info"):
        self.waittime = 500  # miliseconds
        self.wraplength = 180  # pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule(event)

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self, event=None):
        self.unschedule()
        self.id = self.widget.after(self.waittime, lambda: self.showtip(event))

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        (x,y,) = self.widget.winfo_pointerxy()  # 与win32api.GetCursorPos()相同，但尽量避免用win32api
        x += 15
        y += 15

        # creates a toplevel window
        self.tw = Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.attributes("-topmost", 1)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = Label(
            self.tw,
            text=self.text,
            justify="left",
            background="#ffffff",
            relief="solid",
            borderwidth=1,
            wraplength=self.wraplength,
        )
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()


class youdaoTranslation:
    def __init__(self):
        pass

    def translate(self, content):
        self.content = content
        data = {"doctype": "json", "type": "auto", "i": content}
        r = requests.get("http://fanyi.youdao.com/translate", params=data)
        result = r.json()
        self.translatedText = result["translateResult"][0][0]["tgt"]
        self.source = result["translateResult"][0][0]["src"]
        return self.translatedText


def split_into_sentences(text):  
    alphabets = "([A-Za-z])"
    prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
    suffixes = "(Inc|Ltd|Jr|Sr|Co)"
    starters = "(Mr|Mrs|Ms|Dr|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
    acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
    websites = "[.](com|net|org|io|gov|cn|edu)"
    digits = "([0-9])"

    text = " " + text + "   ."
    text = text.replace("\n", " ")
    text = re.sub(prefixes, "\\1<prd>", text)
    text = re.sub(websites, "<prd>\\1", text)
    text = re.sub(digits + "[.]" + digits, "\\1<prd>\\2", text)
    if "..." in text:
        text = text.replace("...", "<prd><prd><prd>")
    if "Ph.D" in text:
        text = text.replace("Ph.D.", "Ph<prd>D<prd>")
    text = re.sub("\s" + alphabets + "[.] ", " \\1<prd> ", text)
    text = re.sub(acronyms + " " + starters, "\\1<stop> \\2", text)
    text = re.sub(
        alphabets + "[.]" + alphabets + "[.]" + alphabets + "[.]",
        "\\1<prd>\\2<prd>\\3<prd>",
        text,
    )
    text = re.sub(alphabets + "[.]" + alphabets + "[.]", "\\1<prd>\\2<prd>", text)
    text = re.sub(" " + suffixes + "[.] " + starters, " \\1<stop> \\2", text)
    text = re.sub(" " + suffixes + "[.]", " \\1<prd>", text)
    text = re.sub(" " + alphabets + "[.]", " \\1<prd>", text)
    if "”" in text:
        text = text.replace(".”", "”.")
    if '"' in text:
        text = text.replace('."', '".')
    if "!" in text:
        text = text.replace('!"', '"!')
    if "?" in text:
        text = text.replace('?"', '"?')
    text = text.replace(".", ".<stop>")
    text = text.replace("?", "?<stop>")
    text = text.replace("!", "!<stop>")
    text = text.replace("<prd>", ".")
    sentences = text.split("<stop>")
    sentences = sentences[:-1]
    sentences = [s.strip() for s in sentences]
    sentences[-1] = sentences[-1][0:-3]
    return sentences

def translate(query):
    global translaterResult, translateSource,IPA
    if query.strip() == "":
        transText = ""
        return ""
    
    try:
        IPA=None
        if query.strip().find(' ')==-1:
            IPA=get_IPA(query)
        else:
            IPA=None
    except:
        IPA=None
    finally:
        transText = ""
        translaterResult = []

        if translateSource == 1:
            google_trans = Translate()
            if query.find("\n"):
                res = query.split("\n")
            if len(res) == 1:
                res.append("")

            for i in range(len(res)):
                if res[i].strip() == "":
                    continue
                item = google_trans.translate(res[i])
                transText += item.translatedText + " "
                translaterResult.append([res[i], item.translatedText])

        elif translateSource == 2:
            youdao = youdaoTranslation()
            if query.find("\n"):
                res = query.split("\n")
            if len(res) == 1:
                res.append("")

            for i in range(len(res)):
                if res[i].strip() == "":
                    continue
                tr = youdao.translate(res[i])
                transText += tr + " "
                translaterResult.append([res[i], tr])

        return transText


class Trans(threading.Thread):
    def __init__(self, query):
        super(Trans, self).__init__()
        self.query = query

    def run(self):
        global transText, ifNewTranslate
        transText = translate(self.query)
        ifNewTranslate = True


class shotScreen:
    img = None
    tkImg = None
    drawRect = [0, 0, 0, 0]
    ifdrawRect = False
    ifPress = False

    def mouseLPressEvent(self, event):
        self.ifdrawRect = not self.ifdrawRect
        if self.ifdrawRect:
            self.drawRect[0], self.drawRect[1] = event.x, event.y
            self.drawRect[2], self.drawRect[3] = event.x, event.y
            self.rect = self.canvas.create_rectangle(
                self.drawRect[0],
                self.drawRect[1],
                self.drawRect[2],
                self.drawRect[3],
                outline="red",
                dash=(3, 3, 3, 3),
            )

    def mouseMoveEvent(self, event):
        if self.ifdrawRect == False:
            return
        self.drawRect[2], self.drawRect[3] = event.x, event.y
        self.canvas.coords(
            self.rect,
            self.drawRect[0],
            self.drawRect[1],
            self.drawRect[2],
            self.drawRect[3],
        )  

    def formEvent(self, event):
        if event.state != 0:  # press any key for exit
            self.mainForm.destroy()
        self.mainForm.destroy()

    def mouseRPressEvent(self, event):
        global sentence, transText, ifNewSentence, ifautoLine, iftrans, ifNewTranslate,IPA
        if self.ifdrawRect:
            self.mainForm.destroy()
        else:
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.tkImg)

            if self.drawRect[0] > self.drawRect[2]:
                self.drawRect[0], self.drawRect[2] = self.drawRect[2], self.drawRect[0]
            if self.drawRect[1] > self.drawRect[3]:
                self.drawRect[1], self.drawRect[3] = self.drawRect[3], self.drawRect[1]

            self.img = self.img.crop((self.drawRect))

            try:
                data = pytesseract.image_to_string(self.img, lang='eng')

                txt = data.replace("\n", " ")  # replace a line
                txt = split_into_sentences(txt)  # resplit new sentence
                sentence = ""
                sentence = "\n".join(txt)  # re-arrange lines
                sentence = re.sub(r"[|]", r"I", sentence)

            except:
                sentence = ""

            clipboard.copy(sentence)  # cross-platform clipboard

            if sentence.strip() != "":
                ifNewSentence = True
            ifNewTranslate = False

            if self.root.iftrans.get():

                tr = Trans(sentence)  # multi-thread translate
                tr.setDaemon(True)
                tr.start()

            else:
                transText = ""

            self.mainForm.destroy()

    def __init__(self, root):
        self.root = root
        self.mainForm = Toplevel(root.mForm)  # create screen shot background
        self.mainForm.attributes("-topmost", 1)
        self.mainForm.overrideredirect(True)
        self.mainForm.config(borderwidth=0, highlightthickness=0)

        
        self.mainForm.geometry(
            f"{root.mForm.winfo_screenwidth()}x{root.mForm.winfo_screenheight()}+0+0"
        )

        
        self.img = ImageGrab.grab(all_screens=True)
        self.tkImg = ImageTk.PhotoImage(self.img)

        self.canvas = Canvas(
            self.mainForm,
            width=self.img.size[0],
            height=self.img.size[1],
            cursor="cross",
        )
        self.canvas.create_image(0, 0, anchor="nw", image=self.tkImg)
        self.canvas.place(x=0, y=0)
        self.canvas.pack(fill="both", expand=True)

        self.mainForm.focus_force()
        self.mainForm.bind("<Key>", self.formEvent)
        self.mainForm.bind("<Button-1>", self.mouseLPressEvent)
        self.mainForm.bind("<Button-3>", self.mouseRPressEvent)
        self.mainForm.bind("<Motion>", self.mouseMoveEvent)
        

class AboutForm(Toplevel):
    def __init__(self, parent):
        global img,photoimg
        super().__init__(parent)  
                 
        self.parent = parent
        self.result = None

        self.title("About me")
        self.geometry(
            f"{int(400*scale)}x{int(220*scale)}+{self.winfo_screenwidth()//2-200}+{self.winfo_screenheight()//2-100}"
        )      
        self.resizable(False, False)
        
        self.label1=Label(self,text='Author: Xinwei Wang(2023/10/29)\nEmail: coldraymagic@gmail.com')
        self.label1.pack(side='top',fill=X)
        
        self.label2=Label(self,image=photoimg)
        self.label2.pack()
        
        self.btn1 = Button(self, text="OK", command=lambda: self.destroy())
        self.btn1.pack(side="bottom", fill=X)


class MainWindow:
    # rgb is list object:[255,0,255]; return value is a color string:'#ff00ff'
    def cvtColor(self, rgb):
        r = f"{rgb[0]:02x}"
        g = f"{rgb[1]:02x}"
        b = f"{rgb[2]:02x}"
        return "#" + r + g + b

    def mouseDown(self, e):
        self.iPress = True
        self.downPosition = [e.x, e.y]

    def mouseUp(self, e):
        self.iPress = False
        self.downPosition = None

    def mouseMove(self, e):
        if self.iPress and self.downPosition:
            left = self.mForm.winfo_x() + e.x - self.downPosition[0]
            top = self.mForm.winfo_y() + e.y - self.downPosition[1]

            if left < 0:
                left = 0
            if top < 0:
                top = 0
            if top + self.btnSize > self.mForm.winfo_screenheight():
                top = self.mForm.winfo_screenheight() - self.btnSize
            if left + self.btnSize > self.mForm.winfo_screenwidth():
                left = self.mForm.winfo_screenwidth() - self.btnSize

            self.mForm.geometry("+%s+%s" % (left, top))
            self.left = left
            self.top = top
            if self.transPanel:
                self.transPanel.geometry("+%s+%s" % (left, top + self.btnSize + 3))

    def winExit(self, e):
        try:
            newini = open(dirname + r"\shot.ini", "w")
            newini.write("[config]\n")
            newini.write(f"position={self.mForm.winfo_x()}+{self.mForm.winfo_y()}\n")
            newini.write(f"source={translateSource}\n")
            newini.write(f"sentences={self.ifautoLine.get()}\n")
            newini.write(f"duolingo={self.iftwolang.get()}\n")
            newini.write(f"history={self.ifhistory.get()}\n")
            newini.close()
            self.mForm.destroy()
        finally:
            sys.exit(0)

    def toolMenuClick(self, event):
        """
        if hwnd==0:
            hwnd=win32gui.FindWindow(None, 'Words Hunter')
        """
        # left, top, right, bot = win32gui.GetWindowRect(hwnd)

        self.left = self.mForm.winfo_rootx()
        self.top = self.mForm.winfo_rooty()
        self.right = self.mForm.winfo_height() + self.mForm.winfo_rootx()
        self.bot = self.mForm.winfo_width() + self.mForm.winfo_rooty()

        tmp = 0 if self.bot - self.top == self.btnSize else self.btnSize
        self.popmenu.post(self.left, self.top + self.toolSize - tmp)

    def setPanel(self, widget, txt):
        self.curPanelSize = self.curPanelSize + int(30*scale) if self.curPanelSize < int(400*scale) else int(300*scale)

        left = self.mForm.winfo_x()
        top = self.mForm.winfo_y()
        bot = self.top + self.btnSize
        widget.geometry(
            f"{self.curPanelSize}x{self.curPanelSize*self.panelHeight//int(300*scale)}+{left}+{bot+3}"
        )
        txt.configure(font=("微软雅黑", 10 * self.curPanelSize // int(300*scale), "bold"))
        txt.config(padx=5 * self.curPanelSize // int(300*scale))
        txt.config(pady=5 * self.curPanelSize // int(300*scale))
        widget.update()

    def transClipboard(self, widget):
        global sentences
        txt = widget.clipboard_get()
        # txt=codecs.decode(txt, 'unicode_escape')
        txt = txt.replace("\n", " ")  # 替换掉换行
        txt = split_into_sentences(txt)  # 重新对文本进行分句
        sentence = ""
        sentence = "\n".join(txt)  # 根据分的句子重新换行

        tr = Trans(sentence)  # 多线程翻译
        tr.setDaemon(True)
        tr.start()

    def chkMenuClick(self):
        global sentence
        if self.iftrans.get():
            self.transPanel = Toplevel()
            # hwnd=win32gui.FindWindow(None, 'Words Hunter')
            # left, top, right, bot = win32gui.GetWindowRect(hwnd)

            left = self.left
            top = self.top
            bot = top + self.btnSize
            # print(f'{top}, {self.btnSize}')

            self.transPanel.geometry(
                f"{self.curPanelSize}x{int(self.curPanelSize*self.panelHeight//(300*scale))}+{left}+{bot+3}"
            )
            self.transPanel.attributes("-topmost", 1)
            self.transPanel.overrideredirect(True)
            self.transPanel.attributes("-alpha", 0.85)
            if self.txtFrame:
                self.txtFrame.destroy()

            # Frame(transPanel,height=toolSize,width=300)
            # headFrame.pack(side='top')
            self.minPanelBtn = Frame(self.transPanel, width=self.curPanelSize)
            self.minPanelBtn.pack(side="top", anchor="nw", fill=X)

            self.txtFrame = Text(self.transPanel, wrap=WORD, bg="light cyan")
            self.txtFrame.config(padx=5)
            self.txtFrame.config(pady=5)

            self.scroll = Scrollbar()
            self.scroll = Scrollbar(self.transPanel)
            self.scroll.pack(side=RIGHT, fill=Y)
            self.scroll.config(command=self.txtFrame.yview)

            self.txtFrame.config(yscrollcommand=self.scroll.set)
            self.txtFrame.configure(
                font=("微软雅黑", 10 * self.curPanelSize // int(300*scale), "bold")
            )
            self.txtFrame.pack(side="top", anchor="sw", expand="yes", fill="both")
            self.txtFrame.delete(0.0, END)

            self.btn1 = Button(
                self.minPanelBtn,
                height=int(8*scale),
                width=self.btnSize,
                image=self.btnImg01,
                compound="center",
                command=lambda: self.iftrans.set(False),
            )
            self.btn1.pack(side="left", anchor="w")

            self.btn3 = Button(
                self.minPanelBtn,
                height=int(8*scale),
                width=self.btnSize,
                image=self.btnImg03,
                compound="center",
                command=lambda: self.setPanel(self.transPanel, self.txtFrame),
            )
            self.btn3.pack(side="left")

            self.btn4 = Button(
                self.minPanelBtn,
                height=int(8*scale),
                width=self.btnSize,
                image=self.btnImg04,
                compound="center",
                command=lambda: self.transClipboard(self.mForm),
            )
            self.btn4.pack(side="left")

            self.btn2 = Button(
                self.minPanelBtn,
                height=8,
                width=self.btnSize,
                image=self.btnImg02,
                compound="center",
                command=lambda: self.txtFrame.delete(0.0, END),
            )
            self.btn2.pack(side="right", anchor="e")

            self.panelPopmenu = Menu(self.transPanel, tearoff=0)
            self.panelPopmenu.add_command(
                label="Copy",
                command=lambda: clipboard.copy(self.txtFrame.get(SEL_FIRST, SEL_LAST)),
            )
            self.panelPopmenu.add_command(
                label="Paste",
                command=lambda: self.txtFrame.insert(
                    INSERT, self.mForm.clipboard_get()
                ),
            )
            self.panelPopmenu.add_separator()
            self.panelPopmenu.add_command(
                label="Clear", command=lambda: self.txtFrame.delete(0.0, END)
            )
            self.transPanel.bind(
                "<Button-3>", lambda evt: self.panelPopmenu.post(evt.x_root, evt.y_root)
            )

            CreateToolTip(self.btn1, "Hide Panel")
            CreateToolTip(self.btn2, "Clean Panel")
            CreateToolTip(self.btn3, "Change Size")
            CreateToolTip(self.btn4, "Translate from Clipboard")

        else:
            if self.transPanel:
                sentence = ""
                self.txtFrame.destroy()
                self.txtFrame = None
                self.transPanel.destroy()
                self.transPanel = None

    def sourceChk(self, s):
        global translateSource
        self.sourceChk_1.set(False)
        self.sourceChk_2.set(False)
        self.sourceChk_3.set(False)
        translateSource = s
        if s == 1:
            self.sourceChk_1.set(True)
        elif s == 2:
            self.sourceChk_2.set(True)
        elif s == 3:
            self.sourceChk_3.set(True)

        print(translateSource)

    """
    def panelClose(self,event):
        showinfo('Success!', 'ok')
    """

    def globalMousePress(self, event):
        if self.transPanel:
            self.transPanel.destroy()

    def emptyEvent(self, event):
        pass

    def btnClick(self):
        shotScreen(self)

    def change(self):
        global ifNewSentence, transText, sentence, ifNewTranslate

        self.t += 1
        if self.t > 359:
            self.t = 0
        r = int(127.5 * sin(self.t * 3.142 / 180) + 127.5)
        g = int(127.5 * sin(self.t * 3.142 / 180 * 2) + 127.5)
        b = int(127.5 * sin(self.t * 3.142 / 180 * 3) + 127.5)
        self.topFrame.configure(background=self.cvtColor((r, g, b)))

        if self.iftrans.get() == False and self.transPanel:
            sentence = ""
            self.txtFrame.destroy()
            self.txtFrame = None
            self.transPanel.destroy()
            self.transPanel = None

        if ifNewTranslate and self.transPanel:
            self.txtFrame.delete(0.0, END)
            #if sentence.strip().find(' ') == -1:
            if IPA!=None:

                self.txtFrame.insert("end",f"UK: {IPA[0]}"+ "\n")
                self.txtFrame.insert("end",f"US: {IPA[1]}" + "\n\n")
                               
            if self.iftwolang.get():
                if self.ifautoLine.get():
                    print(translaterResult)
                    for item in translaterResult:
                        self.txtFrame.insert("end", item[0] + "\n")
                        self.txtFrame.insert("end", item[1] + "\n\n")
                else:
                    s = t = ""
                    for item in translaterResult:
                        s += item[0].strip() + " "
                        t += item[1].strip()
                    self.txtFrame.insert("end", s + "\n")
                    t = "".join(x for x in t if x.isprintable())  # 去除中文字符串中不可见字符
                    self.txtFrame.insert(
                        "end",
                        t.replace("\n", "").replace("\r", "").replace(" ", "") + "\n",
                    )

            else:
                self.txtFrame.insert("end", transText)
            ifNewTranslate = False
        self.mForm.after(self.interval, self.change)

    def onTrayClick(self,event):
        showinfo("提示", "点击了托盘图标！")

    def __init__(self):
        global dirname, translateSource, scale
        # scale=1.5
        # print("initital")
        position = "0+0"  # position string format: XXX+XXX
        source = 1
        divSentence = True
        duolingo = False
        history = True
        if not os.path.exists(dirname + r"\shot.ini"):
            newini = open(dirname + r"\shot.ini", "w")
            newini.write("[config]\n")
            newini.write("position=0+0\n")
            newini.write("source=1\n")
            newini.write("sentences=True\n")
            newini.write("duolingo=False\n")
            newini.write("history=True\n")
            newini.close()
        else:
            config = configparser.ConfigParser()
            config.read(dirname + r"\shot.ini")
            position = config.get("config", "position")
            source = config.getint("config", "source")
            divSentence = config.getboolean("config", "sentences")
            duolingo = config.getboolean("config", "duolingo")
            history = config.getboolean("config", "history")

        self.left = position[0 : position.find("+")]
        self.top = position[position.find("+") + 1 :]

        self.t = 0  # 彩色标题，正弦角度初始值
        self.toolSize = int(10*scale)
        self.btnSize = int(50*scale)
        self.iPress = False
        self.downPosition = None
        self.transPanel = None
        self.txtFrame = None
        self.translaterResult = []
        # self.curPanelSize = 300
        # self.panelHeight = 430
        self.interval = 20
        translateSource = source

        # print("mForm create")
        self.mForm = Tk()
        self.mForm.attributes("-topmost", 1)
        self.mForm.geometry(f"{int(self.btnSize)}x{int(self.btnSize)}+{position}")
        
        self.mForm.overrideredirect(True)
        self.mForm.title("Words Hunter")
        self.mForm.resizable(False, False)

        self.topFrame = Frame(self.mForm, width=self.btnSize, height=self.toolSize)
        self.topFrame.pack(side="top", fill="x")
        self.topFrame.configure(background="blue")
        self.iPress = False
        self.downPosition = None
        self.transPanel = None
        self.txtFrame = None
        self.translaterResult = []
        self.curPanelSize = int(300*scale)
        self.panelHeight = int(430*scale)

        self.iftrans = BooleanVar()
        self.iftrans.set(False)
        self.ifautoLine = BooleanVar()
        self.ifautoLine.set(divSentence)
        self.iftwolang = BooleanVar()
        self.iftwolang.set(duolingo)
        self.ifhistory = BooleanVar()
        self.ifhistory.set(history)

        # 在button上画画，要先建个Image,把这个Image关联一个内存画画对象ImageDraw，在ImageDraw上画画，再把Image转换为ImageTk
        # 这个转换有时间差，要提前转化，否则不能显示
        self.image1 = Image.new("RGB", (int(20*scale), int(2*scale)), "#f0f0f0")
        self.draw1 = ImageDraw.Draw(self.image1)
        self.draw1.rectangle((0, 0, int(19*scale), int(1*scale)), fill="green")
        self.btnImg01 = ImageTk.PhotoImage(self.image1)

        self.image2 = Image.new("RGB", (int(25*scale), int(4*scale)), "#f0f0f0")
        self.draw2 = ImageDraw.Draw(self.image2)
        self.draw2.ellipse((0, 0, int(4*scale), int(3*scale)), fill="green")
        self.draw2.ellipse((int(10*scale), 0, int(14*scale), int(3*scale)), fill="green")
        self.draw2.ellipse((int(20*scale), 0, int(24*scale), int(3*scale)), fill="green")
        self.btnImg02 = ImageTk.PhotoImage(self.image2)

        self.image3 = Image.new("RGB", (int(18*scale), int(6*scale)), "#f0f0f0")
        self.draw3 = ImageDraw.Draw(self.image3)
        self.draw3.rectangle((0, int(2*scale), int(5*scale), int(3*scale)), fill="green")
        self.draw3.rectangle((int(2*scale), 0, int(3*scale), int(5*scale)), fill="green")
        self.draw3.rectangle((int(12*scale), int(2*scale), int(17*scale), int(3*scale)), fill="green")
        self.btnImg03 = ImageTk.PhotoImage(self.image3)

        self.image4 = Image.new("RGB", (int(13*scale), int(8*scale)), "#f0f0f0")
        self.draw4 = ImageDraw.Draw(self.image4)
        self.draw4.rectangle((int(4*scale), 0, int(12*scale), int(5*scale)), outline="green")
        self.draw4.rectangle((0, int(2*scale), int(7*scale), int(7*scale)), fill="green")
        self.btnImg04 = ImageTk.PhotoImage(self.image4)
        
        

        self.rCanvas = Canvas(
            self.topFrame, width=self.toolSize, height=self.toolSize, background="red"
        )
        self.rCanvas.pack(side="right")
        self.rCanvas.config(highlightthickness=0)
        self.rCanvas.create_line(int(2*scale), int(2*scale), int(7*scale), int(7*scale), fill="#f0f0f0")
        self.rCanvas.create_line(int(6*scale), int(2*scale), int(1*scale), int(7*scale), fill="#f0f0f0")

        self.lCanvas = Canvas(
            self.topFrame, width=self.toolSize, height=self.toolSize, background="red"
        )
        self.lCanvas.pack(side="left")
        self.lCanvas.config(highlightthickness=0)
        self.lCanvas.create_line(int(2*scale), int(2*scale), int(7*scale), int(2*scale), fill="#f0f0f0")
        self.lCanvas.create_line(int(2*scale), int(5*scale), int(7*scale), int(5*scale), fill="#f0f0f0")
        self.lCanvas.bind("<Button-1>", self.toolMenuClick)

        CreateToolTip(self.lCanvas, "Menu")
        CreateToolTip(self.rCanvas, "Exit")

        self.topFrame.bind("<Button-1>", self.mouseDown)
        self.topFrame.bind("<ButtonRelease-1>", self.mouseUp)
        self.topFrame.bind("<Motion>", self.mouseMove)

        self.rCanvas.bind("<Button-1>", self.winExit)
        self.popmenu = Menu(self.lCanvas, tearoff=0)

        self.popmenu.add_checkbutton(
            label="Auto wrapped", onvalue=1, offvalue=0, variable=self.ifautoLine
        )
        self.popmenu.add_checkbutton(
            label="Bilingual", onvalue=1, offvalue=0, variable=self.iftwolang
        )
        self.popmenu.add_separator()
        self.popmenu.add_checkbutton(
            label="Translate",
            onvalue=1,
            offvalue=0,
            variable=self.iftrans,
            command=self.chkMenuClick,
        )
        self.popmenu.add_checkbutton(
            label="History",
            onvalue=1,
            offvalue=0,
            variable=self.ifhistory
        )

        self.sourceChk_1 = BooleanVar()
        self.sourceChk_1.set(True if source == 1 else False)
        self.sourceChk_2 = BooleanVar()
        self.sourceChk_2.set(True if source == 2 else False)
        self.sourceChk_3 = BooleanVar()
        self.sourceChk_3.set(True if source == 3 else False)

        self.popmenu.choices = Menu(self.popmenu, tearoff=0)
        self.popmenu.choices.add_checkbutton(
            label="Google",
            onvalue=1,
            offvalue=0,
            variable=self.sourceChk_1,
            command=lambda: self.sourceChk(1),
        )
        self.popmenu.choices.add_checkbutton(
            label="Youdao",
            onvalue=1,
            offvalue=0,
            variable=self.sourceChk_2,
            command=lambda: self.sourceChk(2),
        )
        # self.popmenu.choices.add_checkbutton(label="Bing", onvalue=1, offvalue=0, variable=self.sourceChk_3,command=lambda :self.sourceChk(3))

        self.popmenu.add_cascade(label="Source", menu=self.popmenu.choices)

        self.popmenu.add_separator()
        self.popmenu.add_command(
            label="About", command=lambda: AboutForm(self.mForm).wait_window()
        )

        self.Btn = Button(self.mForm)
        self.Btn.configure(text="Shot")
        self.Btn.configure(command=self.btnClick)
        self.Btn.configure(font=("Arial", 10, "bold"))
        self.Btn.pack(side="top", anchor="sw", expand="yes", fill="both")

        self.mForm.after(self.interval, self.change)
        

        tray_icon = PhotoImage(file=dirname+r"\cam.png")
        # print(dirname+r"\cam.png")
        self.mForm.iconphoto(True, tray_icon)
        traymenu = Menu(self.mForm, tearoff=False)
        traymenu.add_command(label="Information", command=lambda : self.onTrayClick())


haveOpened = pygetwindow.getWindowsWithTitle("Words Hunter")

if len(haveOpened) == 0:
    ctypes.windll.user32.SetProcessDPIAware()
    
    dc = ctypes.windll.user32.GetDC(0)
    dpi_y = ctypes.windll.gdi32.GetDeviceCaps(dc, 90)
    ctypes.windll.user32.ReleaseDC(0, dc)
    scale = dpi_y / 96
    # print(f"Scale factor: {scale}")

    f = MainWindow()

    photoimg=ImageTk.PhotoImage(img)
    f.mForm.mainloop()
