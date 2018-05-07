from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import numpy as np
import os
import os.path
import glob
import random
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from tkinter import ttk

# colors for the bboxes
COLORS = ['red', 'blue', 'yellow', 'pink', 'cyan', 'green', 'black']
# image sizes for the examples
SIZE = 256, 256


class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("LabelTool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width=FALSE, height=FALSE)

        # initialize global state
        self.imageDir = ''
        self.imageList = []
        self.egDir = ''
        self.egList = []
        self.outDir = ''
        self.cur = 0
        self.total = 0
        self.category = 0
        self.imagename = ''
        self.imagesize = ''
        self.labelfilename = ''
        self.tkimg = None
        self.currentLabelclass = ''
        self.cla_can_temp = []
        self.classcandidate_filename = 'class.names'

        # initialize mouse state
        self.STATE = {}
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0

        # reference to bbox
        self.bboxIdList = []
        self.bboxId = None
        self.bboxList = []
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        self.label = Label(self.frame, text="Image Dir:")
        self.label.grid(row=0, column=0, sticky=E)
        self.entry = Entry(self.frame)
        self.entry.grid(row=0, column=1, sticky=W+E)
        self.ldBtn = Button(self.frame, text="Load", command=self.loadDir)
        self.ldBtn.grid(row=0, column=2, sticky=W+E)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross')
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        # press <Espace> to cancel current bbox
        self.parent.bind("<Escape>", self.cancelBBox)
        self.parent.bind("s", self.cancelBBox)
        # press 'a' to go backforward
        self.parent.bind("a", self.prevImage)
        # press 'd' to go forward
        self.parent.bind("d", self.nextImage)
        self.mainPanel.grid(row=1, column=1, rowspan=4, sticky=W+N)

        # choose class
        self.classname = StringVar()
        self.classcandidate = ttk.Combobox(self.frame,
                                           state='readonly',
                                           textvariable=self.classname)
        self.classcandidate.grid(row=1, column=2)
        if os.path.exists(self.classcandidate_filename):
            with open(self.classcandidate_filename) as cf:
                for line in cf.readlines():
                    self.cla_can_temp.append(line.strip('\n'))
        self.classcandidate['values'] = self.cla_can_temp
        self.classcandidate.current(0)
        self.currentLabelclass = self.classcandidate.get()
        self.btnclass = Button(self.frame,
                               text='ComfirmClass',
                               command=self.setClass)
        self.btnclass.grid(row=2, column=2, sticky=W+E)

        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text='Bounding boxes:')
        self.lb1.grid(row=3, column=2,  sticky=W+N)
        self.listbox = Listbox(self.frame, width=22, height=12)
        self.listbox.grid(row=4, column=2, sticky=N)
        self.btnDel = Button(self.frame, text='Delete', command=self.delBBox)
        self.btnDel.grid(row=5, column=2, sticky=W+E+N)
        self.btnClear = Button(self.frame, text='ClearAll',
                               command=self.clearBBox)
        self.btnClear.grid(row=6, column=2, sticky=W+E+N)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row=7, column=1, columnspan=2, sticky=W+E)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev',
                              width=10, command=self.prevImage)
        self.prevBtn.pack(side=LEFT, padx=5, pady=3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>',
                              width=10, command=self.nextImage)
        self.nextBtn.pack(side=LEFT, padx=5, pady=3)
        self.progLabel = Label(self.ctrPanel, text="Progress:     /    ")
        self.progLabel.pack(side=LEFT, padx=5)
        self.tmpLabel = Label(self.ctrPanel, text="Go to Image No.")
        self.tmpLabel.pack(side=LEFT, padx=5)
        self.idxEntry = Entry(self.ctrPanel, width=5)
        self.idxEntry.pack(side=LEFT)
        self.goBtn = Button(self.ctrPanel, text='Go', command=self.gotoImage)
        self.goBtn.pack(side=LEFT)

        # example pannel for illustration
        self.egPanel = Frame(self.frame, border=10)
        self.egPanel.grid(row=1, column=0, rowspan=5, sticky=N)
        self.tmpLabel2 = Label(self.egPanel, text="Examples:")
        self.tmpLabel2.pack(side=TOP, pady=5)
        self.egLabels = []
        for i in range(3):
            self.egLabels.append(Label(self.egPanel))
            self.egLabels[-1].pack(side=TOP)

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side=RIGHT)

        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(4, weight=1)

    def loadDir(self, dbg=False):
        if not dbg:
            s = self.entry.get()
            self.parent.focus()
            self.category = int(s)
        else:
            s = r'D:\workspace\python\labelGUI'
        # get image list
        self.imageDir = os.path.join(r'./Images', '%03d' % (self.category))
        self.imageList = [f for f in glob.glob(
            os.path.join(self.imageDir + '/*')) if ('png'in f or 'jpg' in f)]

        if len(self.imageList) == 0:
            print('No .JPEG images found in the specified dir!')
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

        # set up output dir
        self.outDir = os.path.join(r'./Labels', '%03d' % (self.category))
        if not os.path.exists(self.outDir):
            os.mkdir(self.outDir)

        # load example bboxes
        self.egDir = os.path.join(r'./Examples', '%03d' % (self.category))
        if not os.path.exists(self.egDir):
            return
        filelist = glob.glob(os.path.join(self.egDir, '*.JPEG'))
        self.tmp = []
        self.egList = []
        random.shuffle(filelist)
        for (i, f) in enumerate(filelist):
            if i == 3:
                break
            im = Image.open(f)
            r = min(SIZE[0] / im.size[0], SIZE[1] / im.size[1])
            new_size = int(r * im.size[0]), int(r * im.size[1])
            self.tmp.append(im.resize(new_size, Image.ANTIALIAS))
            self.egList.append(ImageTk.PhotoImage(self.tmp[-1]))
            self.egLabels[i].config(image=self.egList[-1],
                                    width=SIZE[0], height=SIZE[1])

        self.loadImage()
        print(('{0} images loaded from {1}'.format(self.total, s)))

    def loadImage(self):
        # load image
        imagepath = self.imageList[self.cur - 1]
        self.img = Image.open(imagepath)
        self.imagesize = np.asarray(self.img).shape
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width=max(self.tkimg.width(), 400),
                              height=max(self.tkimg.height(), 400))
        self.mainPanel.create_image(0, 0, image=self.tkimg, anchor=NW)
        self.progLabel.config(text="%04d/%04d" % (self.cur, self.total))

        # load labels
        self.clearBBox()
        self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        labelname = self.imagename + '.xml'
        self.labelfilename = os.path.join(self.outDir, labelname)
        bbox_cnt = 0
        print(self.labelfilename)
        if os.path.exists(self.labelfilename):
            with open(self.labelfilename) as f:
                tree = ET.parse(f)
                xmlroot = tree.getroot()
                size = xmlroot.find('size')
                width = int(size.find('width').text)
                height = int(size.find('height').text)

                for obj in xmlroot.iter('object'):
                    cls = obj.find('name').text
                    xmlbox = obj.find('bndbox')
                    bbox = (int(xmlbox.find('xmin').text),
                            int(xmlbox.find('ymin').text),
                            int(xmlbox.find('xmax').text),
                            int(xmlbox.find('ymax').text),
                            cls
                            )
                    self.bboxList.append(bbox)
                    tmpId = self.mainPanel.create_rectangle(
                        bbox[0], bbox[1], bbox[2], bbox[3],
                        width=2,
                        outline=COLORS[(len(self.bboxList)-1) % len(COLORS)]
                        )
                    self.bboxIdList.append(tmpId)
                    self.listbox.insert(
                        END,
                        '{0}: ({1}, {2}) -> ({3}, {4})'.format(
                            cls, bbox[0], bbox[1], bbox[2], bbox[3]))
                    self.listbox.itemconfig(
                        len(self.bboxIdList) - 1,
                        fg=COLORS[(len(self.bboxIdList) - 1) % len(COLORS)])

    def saveImage(self):
        annotation = ET.Element('annotation')
        folder = ET.SubElement(annotation, 'folder')
        folder.text = os.path.basename(self.imageDir)
        filename = ET.SubElement(annotation, 'filename')
        filename.text = os.path.split(
            self.imageList[self.cur - 1])[-1].split('.')[0] + '.jpg'
        size = ET.SubElement(annotation, 'size')
        width = ET.SubElement(size, 'width')
        width.text = str(int(self.imagesize[1]))
        height = ET.SubElement(size, 'height')
        height.text = str(int(self.imagesize[0]))
        is_gray = False
        if len(self.imagesize) == 2:
           is_gray = True
        depth = ET.SubElement(size, 'depth')
        if is_gray:
            depth.text = str(1)
        else:
            depth.text = str(int(self.imagesize[2]))
        for bbox in self.bboxList:
            obj = ET.SubElement(annotation, 'object')
            name = ET.SubElement(obj, 'name')
            name.text = bbox[4]
            bndbox = ET.SubElement(obj, 'bndbox')
            xmin = ET.SubElement(bndbox, 'xmin')
            xmin.text = str(int(bbox[0]))
            ymin = ET.SubElement(bndbox, 'ymin')
            ymin.text = str(int(bbox[1]))
            xmax = ET.SubElement(bndbox, 'xmax')
            xmax.text = str(int(bbox[2]))
            ymax = ET.SubElement(bndbox, 'ymax')
            ymax.text = str(int(bbox[3]))

        string = ET.tostring(annotation, 'utf-8')
        pretty_string = minidom.parseString(string).toprettyxml(indent='  ')
        with open(self.labelfilename, 'w') as f:
            f.write(pretty_string)
        print(('Image No. {0} saved'.format(self.cur)))

    def mouseClick(self, event):
        if self.STATE['click'] == 0:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
        else:
            x1 = min(self.STATE['x'], event.x)
            x2 = max(self.STATE['x'], event.x)
            y1 = min(self.STATE['y'], event.y)
            y2 = max(self.STATE['y'], event.y)
            self.bboxList.append((x1, y1, x2, y2, self.currentLabelclass))
            self.bboxIdList.append(self.bboxId)
            self.bboxId = None
            self.listbox.insert(
                END, '{0}: ({1}, {2}) -> ({3}, {4})'.format(
                    self.currentLabelclass, x1, y1, x2, y2))
            self.listbox.itemconfig(
                len(self.bboxIdList) - 1, fg=COLORS[(
                    len(self.bboxIdList)-1) % len(COLORS)])
        self.STATE['click'] = 1 - self.STATE['click']

    def mouseMove(self, event):
        self.disp.config(text='x: %d, y: %d' % (event.x, event.y))
        if self.tkimg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y,
                                                 self.tkimg.width(), event.y,
                                                 width=2)
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0,
                                                 event.x, self.tkimg.height(),
                                                 width=2)
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            self.bboxId = self.mainPanel.create_rectangle(
                self.STATE['x'], self.STATE['y'],
                event.x, event.y, width=2,
                outline=COLORS[len(self.bboxList) % len(COLORS)])

    def cancelBBox(self, event):
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
                self.bboxId = None
                self.STATE['click'] = 0

    def delBBox(self):
        sel = self.listbox.curselection()
        if len(sel) != 1:
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.bboxIdList[idx])
        self.bboxIdList.pop(idx)
        self.bboxList.pop(idx)
        self.listbox.delete(idx)

    def clearBBox(self):
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
        self.listbox.delete(0, len(self.bboxList))
        self.bboxIdList = []
        self.bboxList = []

    def prevImage(self, event=None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event=None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()

    def setClass(self):
        self.currentLabelclass = self.classcandidate.get()
        print('set label class to {0}'.format(self.currentLabelclass))


if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    root.resizable(width=True, height=True)
    root.mainloop()
