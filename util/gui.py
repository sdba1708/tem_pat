
# -*- coding: utf-8 -*-
# common
#from sys import get_asyncgen_hooks
from tkinter import * 
from tkinter import ttk, font
#from xml.dom import NoModificationAllowedErr
#from ttkwidgets.frames import ScrolledFrame
#from tkscrolledframe import ScrolledFrame
from PIL import Image, ImageTk, ImageGrab
import numpy as np
import os
import win32gui
import win32con
import time
import pandas as pd
import cv2
import webbrowser
import threading
import yaml
# personal
from util.img_process import detect_tem, gen_tech_imgs, load_icon, IsPBWindow, expand_img, to_binary, re_img_detection, extract_tem_region
from util.data_process import data_processor, get_setting_init, save_setting_init
from util.common import get_app_rect, get_config_data, save_config_data, is_num

DEBUG_FLAG=False

BASE_DIR=os.getcwd()

class Window():
    def __init__(self):
        self.root = Tk()
        self.root.geometry("1800x900+100+100")
        self.root.title('Tem Pick Assist Tool')
        self.root.config(bg = '#add123')
        self.root.wm_attributes('-transparentcolor','#add123')
        # load icon
        #icon = PhotoImage(file="data\\icon.png")
        self.root.iconphoto(True, PhotoImage(data=load_icon()))
        
        self.yaml_path = os.path.join(BASE_DIR, 'data', 'config.yaml')
        self.config_data = get_config_data(self.yaml_path)
      
        self.detection_dump_flag = BooleanVar(value=self.config_data['det_win']['dump'])
        self.link_var = StringVar(value=self.config_data['general']['link'])
        self.auto_detection_var = BooleanVar(value=self.config_data['general']['auto_det'])
        if self.auto_detection_var.get():
            self.root.title('Tem Pick Assist Tool - 検出中')
        self.url_setting={
            "official" : "https://temtem.wiki.gg/wiki",
            "temtetsu" : "https://temtetsu.pages.dev/species"
        }
        
        # Menu Window
        self.men_win = Menu(self.root, tearoff=0)
        self.root.config(menu=self.men_win)
        menu_set = Menu(self.root, tearoff=0)
        self.men_win.add_cascade(label="オプション", menu=menu_set)
        menu_set.add_checkbutton(label='自動検出ON', command= lambda:self.autodet_change("general", ["auto_det"], [self.auto_detection_var.get()]) ,variable=self.auto_detection_var)
        menu_set.add_command(label='検出枠位置調整', command=lambda:self.show_tuning_window())
        menu_set.add_command(label='設定', command=lambda:self.show_setting_window())
        
        #menu_set.add_separator() 
        
        # 透過
        a = ttk.Style()
        a.configure('trans.TFrame', background='#add123')

        # generate widged
        self.left_base_frame = ttk.Frame(self.root, width=100, height=900)
        self.trans_base_frame = ttk.Frame(self.root, width=1600, height=900, style='trans.TFrame')#ScrolledFrame(self.root, autohidescrollbar=False)
        self.right_base_frame = ttk.Frame(self.root, width=100, height=900)
        self.left_base_frame.propagate(False)
        self.trans_base_frame.propagate(False)
        self.right_base_frame.propagate(False)
        '''
            csv data
            tem_db.iat[NoID, Pos]
            ex) tem_db.iat[0, 1] = "Mimit", tem_db.iat[0, 2] = "Digital"
        
        '''
        csv_file=os.path.join(BASE_DIR, "data", "data.csv")
        self.tem_db = pd.read_csv(csv_file, encoding='utf-8', delimiter=',', header=None)

        # label
        # height, width, ch
        self.left_small_frame = []
        self.right_small_frame = []
        self.dummy_image = ImageTk.PhotoImage(Image.fromarray(np.zeros((64, 64, 3)), mode="RGB"))
        self.dummy_type = ImageTk.PhotoImage(Image.fromarray(np.zeros((32, 24, 4)), mode="RGBA"))
        self.buf_imgs = [
            {
            "face" : [],
            "name" : [],
            "type1" : [],
            "type2" : [],
            "stats" : []
        },
        {
            "face" : [],
            "name" : [],
            "type1" : [],
            "type2" : [],
            "stats" : []
        }]
        type_dir = os.path.join(BASE_DIR, "data", "icon")#".\\data\\icon"
        self.type_imgs = { 
            "Neutral"   : ImageTk.PhotoImage(Image.open(os.path.join(type_dir, "Neutral.png")).resize((24, 32))),
            "Wind"      : ImageTk.PhotoImage(Image.open(os.path.join(type_dir, "Wind.png")).resize((24, 32))),
            "Earth"     : ImageTk.PhotoImage(Image.open(os.path.join(type_dir, "Earth.png")).resize((24, 32))),
            "Water"     : ImageTk.PhotoImage(Image.open(os.path.join(type_dir, "Water.png")).resize((24, 32))),
            "Fire"      : ImageTk.PhotoImage(Image.open(os.path.join(type_dir, "Fire.png")).resize((24, 32))),
            "Nature"    : ImageTk.PhotoImage(Image.open(os.path.join(type_dir, "Nature.png")).resize((24, 32))),
            "Electric"  : ImageTk.PhotoImage(Image.open(os.path.join(type_dir, "Electric.png")).resize((24, 32))),
            "Mental"    : ImageTk.PhotoImage(Image.open(os.path.join(type_dir, "Mental.png")).resize((24, 32))),
            "Digital"   : ImageTk.PhotoImage(Image.open(os.path.join(type_dir, "Digital.png")).resize((24, 32))),
            "Melee"     : ImageTk.PhotoImage(Image.open(os.path.join(type_dir, "Melee.png")).resize((24, 32))),
            "Crystal"   : ImageTk.PhotoImage(Image.open(os.path.join(type_dir, "Crystal.png")).resize((24, 32))),
            "Toxic"     : ImageTk.PhotoImage(Image.open(os.path.join(type_dir, "Toxic.png")).resize((24, 32))),
            "Dummy"     : self.dummy_type
        }
        self.buf_obj = [{
            "name" : [],
            "face" : [],
            "type1" : [],
            "type2" : []
        },
        {
            "name" : [],
            "face" : [],
            "type1" : [],
            "type2" : []
        }]
        

        for i in range(8):
            # set small frames
            self.left_small_frame.append(ttk.Frame(self.left_base_frame, width=100, height=100, relief="groove"))
            self.right_small_frame.append(ttk.Frame(self.right_base_frame, width=100, height=100, relief="groove"))
            # set dummy images
            self.buf_imgs[0]["face"].append(self.dummy_image)
            self.buf_imgs[0]["name"].append("None")
            self.buf_imgs[0]["type1"].append("Dummy")
            self.buf_imgs[0]["type2"].append("Dummy")
            self.buf_imgs[0]["stats"].append([])
            self.buf_imgs[1]["face"].append(self.dummy_image)
            self.buf_imgs[1]["name"].append("None")
            self.buf_imgs[1]["type1"].append("Dummy")
            self.buf_imgs[1]["type2"].append("Dummy")
            self.buf_imgs[1]["stats"].append([])
            # set objects
            self.buf_obj[0]['name'].append(ttk.Label(self.left_small_frame[i], text="None", foreground="blue", cursor="hand1"))
            self.buf_obj[0]['type1'].append(ttk.Label(self.left_small_frame[i], image=self.type_imgs["Dummy"]))
            self.buf_obj[0]['type2'].append(ttk.Label(self.left_small_frame[i], image=self.type_imgs["Dummy"]))
            self.buf_obj[1]['name'].append(ttk.Label(self.right_small_frame[i], text="None", foreground="blue", cursor="hand1"))
            self.buf_obj[1]['type1'].append(ttk.Label(self.right_small_frame[i], image=self.type_imgs["Dummy"]))
            self.buf_obj[1]['type2'].append(ttk.Label(self.right_small_frame[i], image=self.type_imgs["Dummy"]))
            
            #self.buf_obj[0]['face'].append(ttk.Button(self.left_small_frame[i], image=self.buf_imgs[0]["face"][i], command =lambda c=i:self.show_tem_face_window(left_flag=True, idx=c)))
            #self.buf_obj[1]['face'].append(ttk.Button(self.right_small_frame[i], image=self.buf_imgs[1]["face"][i], command =lambda c=i:self.show_tem_face_window(left_flag=False, idx=c)))
            self.buf_obj[0]['face'].append(Button(self.left_small_frame[i], image=self.buf_imgs[0]["face"][i], bg='white', command =lambda c=i:self.change_tem_face_bg(lr_idx=0, obj_idx=c)))
            self.buf_obj[1]['face'].append(Button(self.right_small_frame[i], image=self.buf_imgs[1]["face"][i], bg='white', command =lambda c=i:self.change_tem_face_bg(lr_idx=1, obj_idx=c)))
            
        
        self.list_imgs_for_det = [        # Image list. use for tem face detection
            None,
            None
        ]

        self.left_frame_for_det_button = ttk.Frame(self.left_base_frame)
        self.flag_left_run_detection_var = BooleanVar(value=True)
        self.cb_left_run_detection = Checkbutton(self.left_frame_for_det_button, variable=self.flag_left_run_detection_var, text='認識')
        self.right_frame_for_det_button = ttk.Frame(self.right_base_frame)
        self.flag_right_run_detection_var = BooleanVar(value=True)
        self.cb_right_run_detection = Checkbutton(self.right_frame_for_det_button, variable=self.flag_right_run_detection_var, text='認識')
      
        self.left_button = ttk.Button(
            self.left_frame_for_det_button,
            text='開始',
            command=lambda: self.button_update_window(left_flag=self.flag_left_run_detection_var.get(), right_flag = self.flag_right_run_detection_var.get())
            )
        
        self.left_detail_button = ttk.Button(
            self.left_base_frame,
            text='耐性一覧',
            command=lambda: self.show_type_res(left_flag=True)
            )
        self.left_stats_button = ttk.Button(
            self.left_base_frame,
            text='基本能力値一覧',
            command=lambda: self.show_stats(left_flag=True)
            )

        self.right_button = ttk.Button(
            self.right_frame_for_det_button,
            text='開始',
            command=lambda: self.button_update_window(left_flag=self.flag_left_run_detection_var.get(), right_flag = self.flag_right_run_detection_var.get())
            )
        
        self.right_detail_button = ttk.Button(
            self.right_base_frame,
            text='耐性一覧',
            command=lambda: self.show_type_res(left_flag=False)
            )
        
        self.right_stats_button = ttk.Button(
            self.right_base_frame,
            text='基本能力値一覧',
            command=lambda: self.show_stats(left_flag=False)
            )
        

        self.left_base_frame.pack(side=LEFT)
        self.trans_base_frame.pack(side=LEFT)
        self.right_base_frame.pack(side=LEFT)  
        
        # 一番上に認識関連置く
        # left
        self.left_frame_for_det_button.pack(side=TOP)
        self.cb_left_run_detection.pack(side=LEFT)
        self.left_button.pack(side=RIGHT)
        self.right_frame_for_det_button.pack(side=TOP)
        self.cb_right_run_detection.pack(side=LEFT)
        self.right_button.pack(side=RIGHT)
             

        for i in range(8):
            self.left_small_frame[i].grid_propagate(False)
            self.right_small_frame[i].grid_propagate(False)
            self.left_small_frame[i].pack(side=TOP)
            self.right_small_frame[i].pack(side=TOP)
            self.buf_obj[0]['name'][i].grid(column=0, row=0, columnspan=2, sticky=E+W, padx=4, pady=4)
            self.buf_obj[0]['face'][i].grid(column=0, row=1, rowspan=2, sticky=N+S)
            self.buf_obj[0]['type1'][i].grid(column=1, row=1)
            self.buf_obj[0]['type2'][i].grid(column=1, row=2)
            self.buf_obj[1]['name'][i].grid(column=0, row=0, columnspan=2, sticky=E+W, padx=4, pady=4)
            self.buf_obj[1]['face'][i].grid(column=0, row=1, rowspan=2, sticky=N+S)
            self.buf_obj[1]['type1'][i].grid(column=1, row=1)
            self.buf_obj[1]['type2'][i].grid(column=1, row=2)
            
        #self.left_button.pack(side=TOP)
        self.left_detail_button.pack(side=TOP)
        self.left_stats_button.pack(side=TOP)
        #self.right_button.pack(side=TOP)
        self.right_detail_button.pack(side=TOP)
        self.right_stats_button.pack(side=TOP)
        
        
        class subwindow():
            def __init__(self):
                self.obj = [
                    None,
                    None
                ]
                self.pos = [
                    None,
                    None
                ]
                self.size = [
                    None,
                    None
                ]
        self.res_sub = subwindow()
        self.stats_sub = subwindow()
        self.battle_mask = np.load(os.path.join("data", "mask_for_battle.npy"))
        self.pickban_mask = np.load(os.path.join("data", "mask_for_pickban.npy"))
        self.pb_region = [630, 990, 60, 200]    # left, right, top, bottom
        self.flag_not_detected_yet = True
        self.is_battle_cnt = 0
        self.list_re_det = []
        self.selected_tem = None
        self.timeEvent()
        

    def timeEvent(self):
        th = threading.Thread(target=self.update)   # スレッドインスタンス
        th.start()                                  # スレッドスタート
        self.root.after(1000, self.timeEvent)       # 再帰的な関数呼び出し。afterはもともとあるっぽい

    #
    def update(self):
        # update window pos
        tem_window, rect = get_app_rect(width=1600, height=930, ofst_x = self.config_data["general"]["show_ofst_x"], ofst_y = self.config_data["general"]["show_ofst_y"])       # window, [left, right, top, bottom]
        if rect is not None:
            #print(rect)
            self.root.geometry("+"+str(rect[0]- 108)+"+"+str(rect[2] - 20))
            
            # 以降 自動認識部
            if self.auto_detection_var.get() :
                bb = [
                    rect[0] + self.pb_region[0],    # left
                    rect[2] + self.pb_region[2],    # top
                    rect[0] + self.pb_region[1],    # right
                    rect[2] + self.pb_region[3]     # bottm
                ]
                #bb = [rect[0], rect[2], rect[1], rect[3]]
                #win32gui.SetWindowPos(tem_window,win32con.HWND_TOP,0,0,0,0,win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                scs = expand_img(to_binary(np.array(ImageGrab.grab(bbox=bb))))
                battle_flag = IsPBWindow(scs, self.battle_mask)
                pickban_flag = False
                # 連続5回battle_flagがTrueだったら対戦画面へ移行と判断
                if battle_flag:
                    self.is_battle_cnt += 1     
                #if battle_flag and (self.flag_prev_battle is False):    # 対戦画面への移り変わり
                if self.is_battle_cnt > 4:
                    pickban_flag = IsPBWindow(scs, self.pickban_mask)
                    #cv2.imwrite("dump_pickban_input.png", scs)
                    if pickban_flag and self.flag_not_detected_yet:     # pickbanフラグがTrueでなおかつまだ検出が動いていない場合だけ検出する
                        # ここで検出する
                        self.button_update_window(left_flag=self.flag_left_run_detection_var.get(), right_flag = self.flag_right_run_detection_var.get(), called_auto=True)
                        self.flag_not_detected_yet = False
                        
                    '''
                    if not self.flag_not_detected_yet:  # もしまだbattle画面でかつflag_not_detected_yetがFalse -> 検出は終わっているがまだ選出画面
                        # ここでテムがピック/バンされたかどうかを判定する
                        fullbb = [rect[0], rect[2], rect[1], rect[3]]
                        fullscs = np.array(ImageGrab.grab(bbox=fullbb))
                        left_list = extract_tem_region(fullscs, self.config_data["det_win"]["ofst_x"], self.config_data["det_win"]["ofst_y"], False, True)
                        right_list = extract_tem_region(fullscs, self.config_data["det_win"]["ofst_x"], self.config_data["det_win"]["ofst_y"], False, False)
                        self.check_pb_done(left_list, lr_idx=0)
                        self.check_pb_done(right_list, lr_idx=1)
                    '''    
                    if battle_flag is False:  # 連続して5回以上battleだったのに現フレームはbattle_flag=False -> 対戦画面から他画面への移り変わり
                        self.flag_not_detected_yet = True
                        self.is_battle_cnt = 0
                elif (self.is_battle_cnt <= 4) and (battle_flag is False):
                    self.is_battle_cnt=0
                    
     
    def autodet_change(self, keyname, keylist, keyvalue):
        # change 
        if keyvalue[0]:
            self.root.title('Tem Pick Assist Tool - 検出中')
        else:
            self.root.title('Tem Pick Assist Tool')
        self.update_config_file(keyname, keylist, keyvalue)
        
    def check_pb_done(self, img_list, lr_idx):
        for i in range(len(img_list)):
            diff = cv2.cvtColor(img_list[i], cv2.COLOR_BGR2RGB) - self.list_imgs_for_det[lr_idx][i]
            diff_abs = abs(diff).sum()
            if diff_abs > 0:
                diff_B = diff[:,:,0].sum()
                diff_G = diff[:,:,1].sum()
                diff_R = diff[:,:,2].sum()
                print("lr_idx : ", lr_idx, ", idx : ", i, ", diff_R : ", diff_R, ", diff_G : ", diff_G, ", diff_B : ", diff_B)
                if diff_R >= 0 and diff_B < 0 and diff_G < 0:   # 画面全体が赤っぽくなってたらban
                    self.buf_obj[lr_idx]["face"][i].config(bg="tomato")
                else:   # そうじゃなかったらピック
                    self.buf_obj[lr_idx]["face"][i].config(bg="turquoise1")
                
        

    def run(self):
        self.root.mainloop()
    
    def get_screenshot(self, dummy=False):
        
        if dummy:
            scs = cv2.imread(os.path.join(BASE_DIR, "dump_screenshot.png"))
            return scs

        tem_window, rect = get_app_rect(width=1600, height=930)
        if rect is None:
            return []
        #bb = [x1, y1, x2, y2]
        bb = [rect[0], rect[2], rect[1], rect[3]]
        win32gui.SetForegroundWindow(tem_window)
        time.sleep(0.1)
        scs = ImageGrab.grab(bbox=bb)

        return np.array(scs)
    
    def link_click(self, url):
        webbrowser.open_new(url)

    def update_whole_data(self, lr_idx, tem_idx, tgt_obj_idx, tem_face_img):
        
        image_dir = os.path.join(BASE_DIR, "data", "port") #.\\data\\port"
        image_name = os.path.join(image_dir, str(tem_idx).zfill(5)+".png")
        i = tgt_obj_idx
        with Image.open(image_name) as im:
            if im.size[0] != 64 and im.size[1] != 64:
                self.buf_imgs[lr_idx]["face"][i] = ImageTk.PhotoImage(im.resize((64, 64)))
            else:
                self.buf_imgs[lr_idx]["face"][i] = ImageTk.PhotoImage(im)
        self.buf_obj[lr_idx]['face'][i].config(image=(self.buf_imgs[lr_idx]["face"][i]), bg='white')
        # update type
        tmp_type1 = self.tem_db.iat[tem_idx, 3]
        self.buf_imgs[lr_idx]["type1"][i] = tmp_type1
        self.buf_obj[lr_idx]["type1"][i].config(image=self.type_imgs[tmp_type1])

        tmp_type2 = self.tem_db.iat[tem_idx, 4]
        if tmp_type2 != "None":
            self.buf_imgs[lr_idx]["type2"][i] = tmp_type2
            self.buf_obj[lr_idx]["type2"][i].config(image=self.type_imgs[tmp_type2])
        else:
            self.buf_imgs[lr_idx]["type2"][i] = "Dummy"
            self.buf_obj[lr_idx]["type2"][i].config(image=self.type_imgs["Dummy"])
                
        tmp_name = self.tem_db.iat[tem_idx, 1]
        tmp_name_jp = self.tem_db.iat[tem_idx, 2]
        self.buf_imgs[lr_idx]["name"][i] = tmp_name
        self.buf_obj[lr_idx]["name"][i].config(text=tmp_name_jp)
        self.buf_imgs[lr_idx]["stats"][i] = [self.tem_db.iloc[tem_idx, 5], self.tem_db.iloc[tem_idx, 6], self.tem_db.iloc[tem_idx, 7], self.tem_db.iloc[tem_idx, 8], self.tem_db.iloc[tem_idx, 9], self.tem_db.iloc[tem_idx, 10], self.tem_db.iloc[tem_idx, 11]]
        if self.link_var.get() == "official":
            #link_list[lr_idx].append("https://temtem.wiki.gg/wiki/" + tmp_name)
            tmp_link = "https://temtem.wiki.gg/wiki/" + tmp_name
        else:
            #link_list[lr_idx].append("https://temtetsu.pages.dev/species/" + str(self.tem_db.iat[tem_list[i], 0]))
            tmp_link = "https://temtetsu.pages.dev/species/" + str(self.tem_db.iat[tem_idx, 0])

        self.buf_obj[lr_idx]["name"][i].bind("<Button-1>",lambda e, c=tmp_link:self.link_click(c))
        self.buf_obj[lr_idx]["face"][i].bind("<Button-3>", lambda e, c=i, lr=lr_idx, tfi=tem_face_img:self.run_re_detection(lr, tfi, idx=c))
        
        
    def button_update_window(self, left_flag=False, right_flag=False, called_auto=False):
        
        if (called_auto is False) and self.auto_detection_var.get():
            return
        
        # get screenshot
        scs = self.get_screenshot(dummy=DEBUG_FLAG)
        
        # get Entry data
        ofs_x = self.config_data["det_win"]["ofst_x"]
        ofs_y = self.config_data["det_win"]["ofst_y"] #is_num(self.tb2.get())
        tmp_flag = self.detection_dump_flag.get()

        # update image
        if left_flag:
            # get tem list
            tem_list, face_img_list = detect_tem(cv2.cvtColor(scs, cv2.COLOR_BGR2RGB),  ofs_x, ofs_y, tmp_flag, left_flag = True)
            self.list_imgs_for_det[0] = face_img_list
            # メインウィンドウに更新かける
            for i in range(len(tem_list)):
                self.update_whole_data(lr_idx=0, tem_idx = tem_list[i], tgt_obj_idx=i, tem_face_img=face_img_list[i])                
            
            # update sub windows if they are opend
            if self.res_sub.obj[0] is not None:
                self.close_res_win(0)
                self.show_type_res(left_flag=True)
                
            if self.stats_sub.obj[0] is not None:
                self.close_stats_win(0)
                self.show_stats(left_flag=True)
                
            # 左側は1度認識走ったらチェックボックス外す
            self.flag_left_run_detection_var.set(False)
        else:   # 左側に検出かからない場合は背景色だけ元に戻す
            for i in range(8):
                self.buf_obj[1]["face"][i].config(bg="white")

        if right_flag:  # right side
            # get tem list
            tem_list, face_img_list= detect_tem(cv2.cvtColor(scs, cv2.COLOR_BGR2RGB),  ofs_x, ofs_y, tmp_flag, left_flag = False)
            self.list_imgs_for_det[1] = face_img_list
            for i in range(len(tem_list)):
                self.update_whole_data(lr_idx=1, tem_idx = tem_list[i], tgt_obj_idx=i, tem_face_img=face_img_list[i])  
                
            
            # update sub windows if they are opend
            if self.res_sub.obj[1] is not None:
                self.close_res_win(1)
                self.show_type_res(left_flag=False)
                
            if self.stats_sub.obj[1] is not None:
                self.close_stats_win(1)
                self.show_stats(left_flag=False)
        else:   # 検出かからない場合は背景色だけ元に戻す
            for i in range(8):
                self.buf_obj[1]["face"][i].config(bg="white")
                

         
    def show_type_res(self, left_flag=False):
        flag_idx = 0 if left_flag else 1
       
        if self.res_sub.obj[flag_idx] is not None:
            return
        
        self.res_sub.obj[flag_idx] = Toplevel()
        tmp_x, tmp_y = str(0), str(0)
        if self.res_sub.pos[flag_idx] is None:
            if left_flag:
                tmp_x = str(self.left_detail_button.winfo_rootx())
                tmp_y = str(self.left_detail_button.winfo_rooty()-400)
            else:
                tmp_x = str(self.right_detail_button.winfo_rootx())
                tmp_y = str(self.right_detail_button.winfo_rooty()-400)
            self.res_sub.pos[flag_idx] = [tmp_x, tmp_y]
        else:
            tmp_x = str(self.res_sub.pos[flag_idx][0] - 8)      # なぜかずれるのでオフセットが必要
            tmp_y = str(self.res_sub.pos[flag_idx][1] - 31)     # なぜかずれるのでオフセットが必要
        
        tmp_w, tmp_h = 460, 340
        if self.res_sub.size[flag_idx] is not None:
            tmp_w, tmp_h = self.res_sub.size[flag_idx]
             
        self.res_sub.obj[flag_idx].geometry(str(tmp_w)+"x"+str(tmp_h)+"+"+tmp_x+"+"+tmp_y)
        self.res_sub.obj[flag_idx].title('Team Resistances')
        #type_window = Frame(self.res_sub.obj[flag_idx], width = tmp_w, height = tmp_h)
        type_window = Frame(self.res_sub.obj[flag_idx])
        type_window.pack(anchor="center")
            
        # Obj for get type info
        dp = data_processor()
        type_list = dp.get_type_name()

        tmp_label = Label(type_window, text="", height = 2, width=1)
        tmp_label.grid(column=0, row=0)
        for idx in range(len(type_list)):
            tmp_label = Label(type_window, image=self.type_imgs[type_list[idx]], height = 32, width=24)
            tmp_label.grid(column=idx+1, row=0)
                   
        for i in range(8):
            # get tem type info
            tmp_name = self.buf_obj[1]["name"][i].cget("text")
            if tmp_name != "None":
                tmp_type1= self.buf_imgs[flag_idx]["type1"][i] if self.buf_imgs[flag_idx]["type1"][i] is not "Dummy" else None
                tmp_type2= self.buf_imgs[flag_idx]["type2"][i] if self.buf_imgs[flag_idx]["type2"][i] is not "Dummy" else None
                face = Label(type_window,image=self.buf_imgs[flag_idx]["face"][i], height = 32, width=32)
                res_summary = dp.calc_type_res(type1=tmp_type1, type2=tmp_type2)
                face.grid(column=0, row=i+1)
                for j in range(len(res_summary)):
                    tmp_color="azure"
                    if res_summary[j] == "2":
                        tmp_color="pale green"
                    elif res_summary[j] == "4":
                        tmp_color="lime green"
                    elif res_summary[j] == "0.5":
                        tmp_color="light coral"
                    elif res_summary[j] == "0.25":
                        tmp_color="red"
                    res_num = Label(type_window, text="x"+res_summary[j], height = 2, width=4, relief=SOLID, bg=tmp_color)
                    res_num.grid(column=j+1, row=i+1) 
          
        self.res_sub.obj[flag_idx].protocol("WM_DELETE_WINDOW", lambda : self.close_res_win(flag_idx))
        
        
    def close_res_win(self, idx):
        pos_x = self.res_sub.obj[idx].winfo_rootx()
        pos_y = self.res_sub.obj[idx].winfo_rooty()
        size_x = self.res_sub.obj[idx].winfo_width()
        size_y = self.res_sub.obj[idx].winfo_height()
        self.res_sub.pos[idx] = [pos_x, pos_y]
        self.res_sub.size[idx] = [size_x, size_y]
        self.res_sub.obj[idx].destroy()
        self.res_sub.obj[idx] = None
        

    def show_stats(self, left_flag=False):
        
        flag_idx = 0 if left_flag else 1
        if self.stats_sub.obj[flag_idx] is not None:
            return
        
        self.stats_sub.obj[flag_idx] = Toplevel()
        tmp_x, tmp_y = 0, 0
        if self.stats_sub.pos[flag_idx] is None:
            if left_flag:
                tmp_x = str(self.left_detail_button.winfo_rootx())
                tmp_y = str(self.left_detail_button.winfo_rooty()-400)
            else:
                tmp_x = str(self.right_detail_button.winfo_rootx())
                tmp_y = str(self.right_detail_button.winfo_rooty()-400)
            self.stats_sub.pos[flag_idx] = [tmp_x, tmp_y]
        else:
            tmp_x = str(self.stats_sub.pos[flag_idx][0] - 8)
            tmp_y = str(self.stats_sub.pos[flag_idx][1] - 31)     
     
        tmp_w, tmp_h = 390, 320
        if self.stats_sub.size[flag_idx] is not None:
            tmp_w, tmp_h = self.stats_sub.size[flag_idx]
     
        self.stats_sub.obj[flag_idx].geometry(str(tmp_w)+"x"+str(tmp_h)+"+"+tmp_x+"+"+tmp_y)
        self.stats_sub.obj[flag_idx].title('Team Stats')
        stats_window = Frame(self.stats_sub.obj[flag_idx])
        stats_window.pack(anchor="center")

        # Obj for get type info
        stats_list = ["HP", "STA", "SPD", "ATK", "DEF", "SPATK", "SPDEF"]

        blank_label = Label(stats_window, text="", height = 1, width=1)
        blank_label.grid(column=0, row=0)
        for idx in range(len(stats_list)):
            tmp_label = Label(stats_window, text=stats_list[idx], height = 1, width=6)
            tmp_label.grid(column=idx+1, row=0)
                   
        for i in range(8):
            # get tem type info
            tmp_name = self.buf_obj[1]["name"][i].cget("text")
            if tmp_name is not "None":

                tmp_stats = self.buf_imgs[flag_idx]["stats"][i]
                face = Label(stats_window,image=self.buf_imgs[flag_idx]["face"][i], height = 32, width=32)
                
                face.grid(column=0, row=i+1)
                for j in range(len(tmp_stats)):
                    tmp_color="azure"
                    if int(tmp_stats[j]) > 79:
                        tmp_color="PaleGreen1"
                    elif int(tmp_stats[j]) < 51:
                        tmp_color="tomato"
                    stats_num = Label(stats_window, text=tmp_stats[j], height =2, width=6, relief=SOLID, bg=tmp_color)
                    stats_num.grid(column=j+1, row=i+1)
        self.stats_sub.obj[flag_idx].protocol("WM_DELETE_WINDOW", lambda : self.close_stats_win(flag_idx))
                    
    def close_stats_win(self, idx):
        pos_x = self.stats_sub.obj[idx].winfo_rootx()
        pos_y = self.stats_sub.obj[idx].winfo_rooty()
        size_x = self.stats_sub.obj[idx].winfo_width()
        size_y = self.stats_sub.obj[idx].winfo_height()
        self.stats_sub.pos[idx] = [pos_x, pos_y]
        self.stats_sub.size[idx] = [size_x, size_y]
        self.stats_sub.obj[idx].destroy()
        self.stats_sub.obj[idx] = None
                    
    def show_tuning_window(self):
        sub_win = Toplevel()
        sub_win.geometry("300x200")
        sub_win.title('Tuning Window')
        
        tmp_text0 = ttk.Label(sub_win, text="検出枠の位置調整")
        tmp_text1 = ttk.Label(sub_win, text="左右方向（左 : -100 ~ 100 : 右）")
        tmp_text2 = ttk.Label(sub_win, text="上下方向（上 : -100 ~ 100 : 下）")
        tmp_text3 = ttk.Label(sub_win, text="pixel")
        tmp_text4 = ttk.Label(sub_win, text="pixel")
        tb1 = ttk.Entry(sub_win, width=10)
        tb2 = ttk.Entry(sub_win,width=10)
        dump_check = ttk.Checkbutton(sub_win, text="検出枠出力", variable=self.detection_dump_flag, onvalue=True, offvalue=False)
        ref_bt = ttk.Button(sub_win, text="反映", command=lambda: self.update_config_file(
            "det_win",
            ["ofst_x", "ofst_y", "dump"],
            [is_num(tb1.get()), is_num(tb2.get()), self.detection_dump_flag.get()]
            ))
        tb1.delete(0, END)
        tb2.delete(0, END)
        tb1.insert(END, str(self.config_data["det_win"]["ofst_x"]))
        tb2.insert(END, str(self.config_data["det_win"]["ofst_y"]))
        
        tmp_text0.grid(column=0, row=0, columnspan=2, sticky=E+W, padx=4, pady=4)
        tmp_text1.grid(column=0, row=1)
        tb1.grid(column=1, row=1)
        tmp_text3.grid(column=2, row=1)
        tmp_text2.grid(column=0, row=2)
        tb2.grid(column=1, row=2)
        tmp_text4.grid(column=2, row=2)
        dump_check.grid(column=0, row=3)
        ref_bt.grid(column=0, row=4)
           
  
    def update_config_file(self, tgt_key, param_names, param_data):
        if len(param_names) != len(param_data):
            return
        for i in range(len(param_names)):
            self.config_data[tgt_key][param_names[i]] = param_data[i]
        save_config_data(self.yaml_path, self.config_data)
        
        
    def show_setting_window(self):
        sub_win = Toplevel()
        sub_win.geometry("300x200")
        sub_win.title('Setting Window')
        tmp_text0 = ttk.Label(sub_win, text="使用するリンク先")
        rdb0 = ttk.Radiobutton(sub_win, value="official", variable=self.link_var, text='公式Wiki')
        rdb1 = ttk.Radiobutton(sub_win, value="temtetsu", variable=self.link_var, text='テムテム対戦データベース')
        
        tmp_text0.grid(column=0, row=0, rowspan=2,sticky=W, padx=4, pady=4)
        rdb0.grid(column=1, row=0, columnspan=2, sticky=W, padx=4)
        rdb1.grid(column=1, row=1, columnspan=2, sticky=W, padx=4)
        
        
        # tuning for 
        tmp_void0 = ttk.Label(sub_win, text=" ")
        tmp_text00 = ttk.Label(sub_win, text="Tem-PAT 表示位置修正")
        tmp_text1 = ttk.Label(sub_win, text="左右方向\n（左 : -100 ~ 100 : 右）")
        tmp_text2 = ttk.Label(sub_win, text="上下方向\n（上 : -100 ~ 100 : 下）")
        tmp_text3 = ttk.Label(sub_win, text="pixel")
        tmp_text4 = ttk.Label(sub_win, text="pixel")
        tb1 = ttk.Entry(sub_win, width=10)
        tb2 = ttk.Entry(sub_win,width=10)
        tb1.delete(0, END)
        tb2.delete(0, END)
        tb1.insert(END, str(self.config_data["general"]["show_ofst_x"]))
        tb2.insert(END, str(self.config_data["general"]["show_ofst_y"]))
        ref_bt = ttk.Button(sub_win, text="保存", command=lambda: self.update_config_file(
            "general",
            ["link", "show_ofst_x", "show_ofst_y"],
            [self.link_var.get(), is_num(tb1.get()), is_num(tb2.get())])
            )
        tmp_void0.grid(column=0, row=2, columnspan=3, sticky=E+W)
        tmp_text00.grid(column=0, row=3, columnspan=3, sticky=W)
        tmp_text1.grid(column=0, row=4, sticky=N+S)
        tb1.grid(column=1, row=4, sticky=W)
        tmp_text3.grid(column=2, row=4, sticky=W)
        
        tmp_text2.grid(column=0, row=5, sticky=N+S)
        tb2.grid(column=1, row=5, sticky=W)
        tmp_text4.grid(column=2, row=5, sticky=W)
        ref_bt.grid(column=0, row=6, columnspan=3, sticky=E+W, padx=4, pady=4 )
        
        
    def run_re_detection(self, lr_idx, tem_face_img, idx):
        
        image_dir = os.path.join(BASE_DIR, "data", "port")  #".\\data\\port"
        
        if len(self.list_re_det) > 0:
            return
        #self.list_re_det = []
        #self.selected_tem = None
        
        # 0) 別ウィンドウを表示する
        sub_win = Toplevel()
        if lr_idx == 0:
            tmp_x = str(self.buf_obj[0]["face"][idx].winfo_rootx())
            tmp_y = str(self.buf_obj[0]["face"][idx].winfo_rooty())
        else:
            tmp_x = str(self.buf_obj[1]["face"][idx].winfo_rootx())
            tmp_y = str(self.buf_obj[1]["face"][idx].winfo_rooty())
        sub_win.geometry("360x150+"+tmp_x+"+"+tmp_y)
        sub_win.title('Re-Detection')
        sub_win.protocol("WM_DELETE_WINDOW", lambda : self.destroy_re_det_win(sub_win))
        frame_blank= Frame(sub_win)
        frame_blank.pack()
        text_disc = Label(frame_blank, text="認識結果 - 上位5位", anchor="w")
        text_disc.pack(side=TOP, fill='x')
        frame_img = Frame(frame_blank)
        frame_img.pack(side=TOP)
        
        
        # 1) 再度認識をかけて上位5種を取得する
        self.list_best_five = re_img_detection(tem_face_img)
         
        # 2) 取得したテムの画像をウィンドウに表示する
        list_best_five_obj = []
        for i in range(len(self.list_best_five)):
            image_name = os.path.join(image_dir, str(self.list_best_five[i]).zfill(5)+".png")
            with Image.open(image_name) as im:
                if im.size[0] != 64 and im.size[1] != 64:
                    tmp = ImageTk.PhotoImage(im.resize((64, 64)))
                else:
                    tmp = ImageTk.PhotoImage(im)
                #list_best_five_img.append(tmp)
                self.list_re_det.append(tmp)
                list_best_five_obj.append(Button(frame_img, image=self.list_re_det[i], bg="white"))
                list_best_five_obj[i].pack(side=LEFT)
                list_best_five_obj[i].bind("<Button-1>",lambda e, c=i:self.tem_selection(list_best_five_obj, c))
        
        # 3) 決定ボタンを押すとそのテムが窓に表示される
        button_determin = Button(frame_blank, text="反映", command=lambda sw=sub_win, lr=lr_idx, tfi=tem_face_img, oidx=idx: self.close_re_det_window(subwindow=sw, lr_idx=lr, obj_idx=oidx, tem_face_image=tfi))
        button_determin.pack(side=TOP)
        
        
    def close_re_det_window(self, subwindow, lr_idx,  obj_idx, tem_face_image):
        if self.selected_tem is None:   # まだ選択されていない場合は何もしない
            return 
        # update window
        self.update_whole_data(lr_idx=lr_idx, tem_idx = self.list_best_five[self.selected_tem], tgt_obj_idx=obj_idx, tem_face_img=tem_face_image)
        self.destroy_re_det_win(subwindow)
        
    def destroy_re_det_win(self, sub_win):
        self.selected_tem = None
        self.list_re_det = []
        sub_win.destroy()
        

    def tem_selection(self, list_obj, current_idx): # 
        
        if current_idx == self.selected_tem:
            return
        else:
            list_obj[current_idx].config(bg="turquoise1")
            if self.selected_tem is not None:
                list_obj[self.selected_tem].config(bg="white")
            self.selected_tem = current_idx
        return
    
    def change_tem_face_bg(self, lr_idx, obj_idx):
        cur_col = self.buf_obj[lr_idx]["face"][obj_idx].cget('bg')
        if cur_col == "white":
            self.buf_obj[lr_idx]["face"][obj_idx].config(bg="turquoise1")
        elif cur_col == 'turquoise1':
            self.buf_obj[lr_idx]["face"][obj_idx].config(bg="tomato")
        else:
            self.buf_obj[lr_idx]["face"][obj_idx].config(bg="white")
        
    
    def show_tem_face_window(self, left_flag=True, idx=0):
        return  # 使用不可
        sub_win = Toplevel()
        # get position
        if left_flag:
            tmp_x = str(self.buf_obj[0]['face'][idx].winfo_rootx()-300)
            tmp_y = str(self.buf_obj[0]['face'][idx].winfo_rooty())
            tmp_name = str(self.buf_obj[0]['name'][idx].cget("text"))
        else:
            tmp_x = str(self.buf_obj[1]['face'][idx].winfo_rootx())
            tmp_y = str(self.buf_obj[1]['face'][idx].winfo_rooty())
            tmp_name = str(self.buf_obj[1]['name'][idx].cget("text"))
        
        sub_win.geometry("400x300+"+tmp_x+"+"+tmp_y)
        sub_win.title(tmp_name)
        tem_face_window = Frame(sub_win,width = 400, height=300)
        tem_face_window.pack(fill='both', expand=True)
        
        
        if left_flag:
            tmp_stats = self.buf_imgs[0]["stats"][idx]
            face = Label(tem_face_window,image=self.buf_imgs[0]["face"][idx], height = 64, width=64)
        else:
            tmp_stats = self.buf_imgs[1]["stats"][idx]
            face = Label(tem_face_window,image=self.buf_imgs[1]["face"][idx], height = 64, width=64)
        face.grid(column=0, row=0, columnspan=2, rowspan=2, padx=6, pady=6)
        
        # status 
        status_font = font.Font(family='normal', size=9, weight="bold")
        stats_list = ["HP", "STA", "SPD", "ATK", "DEF", "SPATK", "SPDEF"]
        for i in range(len(stats_list)):
            tmp_label = Label(tem_face_window, text=stats_list[i], font=status_font, height = 1, width=5)
            tmp_label.grid(column=i+3, row=0)
        for j in range(len(tmp_stats)):
            tmp_color="azure"
            if int(tmp_stats[j]) > 79:
                tmp_color="PaleGreen1"
            elif int(tmp_stats[j]) < 51:
                tmp_color="tomato"
            stats_num = Label(tem_face_window, text=tmp_stats[j], font=status_font, height = 2, width=5, relief=SOLID, bg=tmp_color)
            stats_num.grid(column=j+3, row=1)
        
        # Trait
        name_font = font.Font(family='normal', size=12, weight="bold")
        disc_font = font.Font(family='normal', size=8)
        trait_name = ['Trait 1', 'Trait 2']
        trait_disc = ['ここは個性1の説明だよ～～～～～～～～～～～～～～～～～～～～～～', 'ここは個性2の説明だよぉぉぉぉぉぉぉぉぉぉぉぉぉぉぉぉぉぉぉ']
        for i in range(len(trait_name)):
            tmp_label = Label(tem_face_window, text=trait_name[i], font=name_font, anchor="w", justify='left', relief=RAISED)
            tmp_label.grid(column=0, row=2+i*6, columnspan=4, sticky=E+W)
            tmp_label = Message(tem_face_window, text=trait_disc[i], font=disc_font, anchor="w", justify='left', relief=SUNKEN)
            tmp_label.grid(column=0, row=4+i*6, columnspan=4, rowspan=2, sticky=E+W)
        
        # Techniques
        
        
        




    
    
