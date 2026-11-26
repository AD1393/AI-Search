import re, html, threading
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.core.text import LabelBase

LANGS={
'fa':{'title':'جستجوی هوشمند اینترنت','placeholder':'سؤالت را اینجا بنویس...','search':'جستجو','settings':'تنظیمات','ready':'آماده جستجو','searching':'در حال جستجو و بررسی صفحات...','empty':'سؤال را بنویس.','error':'خطا در جستجو یا اتصال اینترنت','size':'اندازه نوشته','close':'ذخیره و بستن','language':'زبان برنامه','sources':'منابع','noresult':'نتیجه مناسبی پیدا نشد.','answer':'پاسخ'},
'en':{'title':'Smart Internet Search','placeholder':'Type your question...','search':'Search','settings':'Settings','ready':'Ready','searching':'Searching and reading websites...','empty':'Enter a question.','error':'Search or connection error','size':'Text size','close':'Save and close','language':'App language','sources':'Sources','noresult':'No useful results found.','answer':'Answer'},
'ar':{'title':'البحث الذكي في الإنترنت','placeholder':'اكتب سؤالك هنا...','search':'بحث','settings':'الإعدادات','ready':'جاهز','searching':'جارٍ البحث وقراءة المواقع...','empty':'اكتب السؤال.','error':'خطأ في البحث أو الاتصال','size':'حجم النص','close':'حفظ وإغلاق','language':'لغة البرنامج','sources':'المصادر','noresult':'لم يتم العثور على نتائج مفيدة.','answer':'الإجابة'}}
HEADERS={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36'}
def clean_text(t): return re.sub(r'\s+',' ',t).strip()
def google_search(q):
 out=[]
 try:
  with DDGS() as engine:
   for it in engine.text(q,max_results=12): out.append({'title':it.get('title',''),'snippet':it.get('body',''),'url':it.get('href','')})
 except Exception: pass
 return out
def read_pages(items):
 s=requests.Session(); s.headers.update(HEADERS)
 for it in items:
  try:
   r=s.get(it.get('url',''),timeout=8); r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser')
   for e in soup.select('script,style,nav,footer,header,aside,iframe,noscript,form,svg'): e.decompose()
   it['page_text']=clean_text(soup.get_text(' ',strip=True))[:12000]
  except Exception: it['page_text']=''
 return items
def tokenize(t):
 stop=set('the and for that with from this what when where which about how are is was were to of in on it a an as by or be can do does did why who will would has have had not و در از به که این آن را با برای چه چرا چگونه کجا کی است بود هست های یک یا اگر تا می شود شد هم اما درباره روی پس باید في من إلى على عن هذا هذه هو هي ما كيف لماذا ماذا كان أن أو مع ذلك التي الذي هل هناك'.split())
 return [w for w in re.findall(r'[\w\u0600-\u06FF]+',t.lower()) if w not in stop and len(w)>1]
def make_answer(q,items):
 qw=set(tokenize(q)); cand=[]
 for it in items:
  combined=it.get('title','')+'. '+it.get('snippet','')+'. '+it.get('page_text','')
  for sent in re.split(r'(?<=[.!?؟。])\s+',combined):
   sent=clean_text(sent)
   if len(sent)<35: continue
   words=set(tokenize(sent)); overlap=len(words&qw)
   if overlap:
    score=overlap*2.8+(1.5 if sent in it.get('page_text','') else 0)-(2 if len(sent)>550 else 0)
    cand.append((score,sent))
 cand.sort(reverse=True); chosen=[]; seen=set()
 for _,s in cand:
  if s.lower() not in seen: seen.add(s.lower()); chosen.append(s)
  if len(chosen)>=7: break
 if chosen:return '\n\n'.join(chosen)
 fb=[]
 for it in items:
  if it.get('snippet') and len(it['snippet'])>30: fb.append(it['snippet'])
  if it.get('page_text') and len(it['page_text'])>100: fb.append(it['page_text'][:500])
  if len(fb)>=5:break
 return '\n\n'.join(fb) if fb else 'No useful text was found.'
class AISearchApp(App):
 def build(self):
  self.lang='fa'; self.font_size=16
  root=BoxLayout(orientation='vertical',padding=12,spacing=10)
  top=BoxLayout(size_hint_y=None,height=48)
  self.title=Label(text='AI Search',font_size=24)
  self.settings=Button(text='⚙',size_hint_x=None,width=65)
  self.settings.bind(on_press=self.open_settings)
  top.add_widget(self.title);top.add_widget(self.settings);root.add_widget(top)
  self.subtitle=Label(text=LANGS[self.lang]['title'],size_hint_y=None,height=40)
  root.add_widget(self.subtitle)
  self.input=TextInput(hint_text=LANGS['fa']['placeholder'],multiline=False,size_hint_y=None,height=54,font_size=18)
  root.add_widget(self.input)
  self.btn=Button(text='جستجو',size_hint_y=None,height=52);self.btn.bind(on_press=self.search);root.add_widget(self.btn)
  self.status=Label(text='آماده جستجو',size_hint_y=None,height=35)
  root.add_widget(self.status)
  self.out=Label(text='',size_hint_y=None,halign='right',valign='top',text_size=(None,None),font_size=self.font_size)
  self.scroll=ScrollView();self.scroll.add_widget(self.out);root.add_widget(self.scroll)
  return root
 def update_out(self,text):
  self.out.text=text; self.out.font_size=self.font_size
  self.out.size_hint_y=None; self.out.text_size=(self.scroll.width-24,None)
  self.out.bind(texture_size=lambda obj,val:setattr(obj,'height',val[1]+20));self.out.height= max(100,self.out.texture_size[1]+20)
 def search(self,*args):
  q=self.input.text.strip()
  if not q:self.status.text=LANGS[self.lang]['empty'];return
  self.btn.disabled=True;self.status.text=LANGS[self.lang]['searching'];self.update_out('')
  threading.Thread(target=self.worker,args=(q,),daemon=True).start()
 def worker(self,q):
  try:
   items=google_search(q)
   if not items: result=(LANGS[self.lang]['noresult'],'');
   else:
    items=read_pages(items); answer=make_answer(q,items)
    src='\n\n'+LANGS[self.lang]['sources']+'\n'+'\n'.join(f"{i+1}. {x.get('title','')}\n{x.get('url','')}" for i,x in enumerate(items) if x.get('url'))
    result=(answer,src)
  except Exception: result=(LANGS[self.lang]['error'],'')
  Clock.schedule_once(lambda dt:self.finish(result),0)
 def finish(self,result):
  self.update_out(LANGS[self.lang]['answer']+'\n\n'+result[0]+result[1]);self.status.text='پاسخ آماده شد' if self.lang=='fa' else 'Answer ready';self.btn.disabled=False
 def open_settings(self,*args):
  box=BoxLayout(orientation='vertical',spacing=12,padding=12)
  sp=Spinner(text={'fa':'فارسی','en':'English','ar':'العربية'}[self.lang],values=('فارسی','English','العربية'),size_hint_y=None,height=50)
  sl=Spinner(text=str(self.font_size),values=tuple(str(x) for x in range(12,25)),size_hint_y=None,height=50)
  box.add_widget(Label(text=LANGS[self.lang]['language']));box.add_widget(sp);box.add_widget(Label(text=LANGS[self.lang]['size']));box.add_widget(sl)
  b=Button(text=LANGS[self.lang]['close'],size_hint_y=None,height=50);box.add_widget(b)
  pop=Popup(title=LANGS[self.lang]['settings'],content=box,size_hint=(.85,.65))
  def save(*a):
   self.lang={'فارسی':'fa','English':'en','العربية':'ar'}[sp.text];self.font_size=int(sl.text)
   self.subtitle.text=LANGS[self.lang]['title'];self.input.hint_text=LANGS[self.lang]['placeholder'];self.btn.text=LANGS[self.lang]['search'];self.settings.text=LANGS[self.lang]['settings'];self.status.text=LANGS[self.lang]['ready'];self.out.font_size=self.font_size;pop.dismiss()
  b.bind(on_press=save);pop.open()
if __name__=='__main__': AISearchApp().run()
