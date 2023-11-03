import os

import nuke
import pyseq

class NukeGroupOpen:
    def __init__(self, parent):
        if isinstance(parent, str):
            parent = nuke.toNode(parent)
        if parent and parent.Class() == "Group":
            self._parent = parent

    def __enter__(self):
        self._parent.begin()

    def __exit__(self, exc_type, exc_value, traceback):
        self._parent.end()

class AOVTree(object):

    BEAUTY_NAME = "primary"
    Y_OFFSET = 200
    X_OFFSET = -250
    VERSION = "v0.2"

    @classmethod
    def get_aov_dir(cls, filepath):
        if filepath.endswith("/"):
            filepath = filepath[:-1]
        if os.path.isdir(filepath):
            if filepath.endswith(cls.BEAUTY_NAME):
                return os.path.dirname(filepath)
            return filepath
        if filepath.endswith(".exr"):
            return cls.get_aov_dir(os.path.dirname(filepath))

    @classmethod
    def create_layer(cls, name, alpha=False):
        if not name in set(nuke.layers()):
            channels = [".red",
                      ".green",
                      ".blue",
                      ]
            if alpha:
                channels.append(".alpha")
            nuke.Layer(name, [name+c for c in channels] )

    @classmethod
    def _create_read_node(cls, filepath):
        read_node = nuke.createNode("Read", inpanel=False)
        read_node.knob("file").fromUserText(filepath)
        return read_node

    @classmethod
    def shuffle_crypto(cls, from_node, to_node, layer):
        last_node = from_node
        for i in ["", "00", "01", "02"]:
            pos = [int(last_node.xpos()), int(last_node.ypos()+25)]
            last_node = cls.shuffle_layer(last_node, to_node, layer+i, layer+i)
            last_node["disable"].setExpression("!_aov_{}".format(layer))
            if i == "":
                pos[1] = pos[1]+150
            last_node.setXYpos(pos[0], pos[1])
        cp = nuke.createNode("CopyMetaData", inpanel=False)
        cp.setName("copy_meta_{}".format(layer))
        cp.setInput(0, last_node)
        cp.setInput(1, to_node)
        cp.setXYpos(int(last_node.xpos()), int(last_node.ypos()+25))
        cp["disable"].setExpression("!_aov_{}".format(layer))
        return cp

    @classmethod
    def shuffle_layer(cls, from_node, to_node, layer, in_c="rgba"):
        cls.create_layer(layer)
        suffle_copy = nuke.createNode("ShuffleCopy", inpanel=False)
        suffle_copy.setName("Shuffle_{}".format(layer))
        suffle_copy.setInput(0, from_node)
        suffle_copy.setInput(1, to_node)
        suffle_copy["in"].setValue(in_c)
        suffle_copy["out"].setValue(layer)
        suffle_copy["red"].setValue(1)
        suffle_copy["green"].setValue(2)
        suffle_copy["blue"].setValue(3)
        suffle_copy["disable"].setExpression("!_aov_{}".format(layer))

        suffle_copy.setXYpos(int(from_node.xpos()), int(from_node.ypos()+cls.Y_OFFSET))
        return suffle_copy

    @classmethod
    def get_read_string(cls, beauty, change_to=None):
        if len(beauty.frames()) > 0:
            string = "{}%04d{} {}".format(beauty.format("%D%h"), beauty.format("%t"), beauty.format("%s-%e"))
        else:
            string = beauty.format("%D%h")
        string = string.replace("\\", "/")
        if change_to:
            string = string.replace(cls.BEAUTY_NAME, change_to)
        return string

    @classmethod
    def get_beauty(cls, filepath):
        beauty_dir = os.path.join(cls.get_aov_dir(filepath), cls.BEAUTY_NAME)
        beauty = pyseq.Sequence([os.path.join(beauty_dir, f) for f in os.listdir(beauty_dir) if f.endswith(".exr")])
        return beauty

    @classmethod
    def get_aov_list(cls, filepath):
        aov_list = [d for d in os.listdir(cls.get_aov_dir(filepath)) if d.startswith("__")]
        return sorted(aov_list)

    @classmethod
    def __load_aovs(cls, filepath):
        beauty = cls.get_beauty(filepath)
        aov_list = cls.get_aov_list(filepath)
        beauty_read = cls._create_read_node(cls.get_read_string(beauty))
        last_node = beauty_read
        for aov in aov_list:
            aov_read = cls._create_read_node(cls.get_read_string(beauty, aov))
            aov_read.setXYpos(int(last_node.xpos()+cls.X_OFFSET), int(last_node.ypos()+cls.Y_OFFSET))
            if "crypto" in aov:

                last_node = cls.shuffle_crypto(last_node, aov_read, aov)
            else:
                last_node = cls.shuffle_layer(last_node, aov_read, aov)

        return last_node

    @classmethod
    def clear_group(cls, node):
        with NukeGroupOpen(node):
            [nuke.delete(n) for n in nuke.allNodes() if not n.name()=="Output1"]
        [node.removeKnob(node[n]) for n in node.knobs() if n.startswith("_aov_")]

    @classmethod
    def load_aovs(cls, filepath, group):
        cls.clear_group(group)
        with NukeGroupOpen(group):
            last_node = cls.__load_aovs(filepath)
            nuke.toNode("Output1").setInput(0, last_node)

        for aov in cls.get_aov_list(filepath):
            knob = nuke.Boolean_Knob("_aov_{}".format(aov), aov)
            knob.setFlag(nuke.STARTLINE)
            knob.setValue(1)
            group.addKnob(knob)
        group["postage_stamp"].setValue(1)
        group["label"].setValue("[file tail [value file]]")

    @classmethod
    def create_group(cls):
        node = nuke.createNode("Group")
        node.setName("AOVTree1")
        node["tile_color"].setValue(1314742527)
        with NukeGroupOpen(node):
            nuke.nodes.Output()
        knob = nuke.Tab_Knob("aovtree", "AOV Tree")
        node.addKnob(knob)
        knob = nuke.Text_Knob("credit1", "", '<font size = 5 style="color:#F2E8C6">OutlineVFX</font>')
        node.addKnob(knob)
        knob = nuke.Text_Knob("credit2", "", '<font size = 6 style="color:#FFBB5C"><b>AOV Tree</b></font>')
        node.addKnob(knob)
        knob = nuke.Text_Knob("credit3", "", '<font size = 3 style="color:#666"><br>{}</br></font>'.format(cls.VERSION))
        knob.clearFlag(nuke.STARTLINE)
        node.addKnob(knob)
        knob = nuke.Text_Knob("div_00", "")
        node.addKnob(knob)
        knob = nuke.File_Knob("file", "beauty")
        node.addKnob(knob)
        knob = nuke.PyScript_Knob("load", "load", "import aovtree\nn=nuke.thisNode()\naovtree.AOVTree.load_aovs(n['file'].getValue(), n)")
        knob.clearFlag(nuke.STARTLINE)
        node.addKnob(knob)
        knob = nuke.Text_Knob("div_01", "")
        node.addKnob(knob)

        return node

    @classmethod
    def create_and_load(cls, filepath):
        node = cls.create_group()
        node["file"].setValue(filepath)
        cls.load_aovs(filepath, node)
        return node


def check_string(string):
    string = os.path.dirname(string)
    return string.endswith(AOVTree.BEAUTY_NAME)

def drop_aovtree(mimeType, text):
    """
    used with nukescripts.addDropDataCallback()
    triggered on if text is dropped to DAG

    @args
    @return
    """

    if not mimeType == 'text/plain' or not check_string(text):
        return False

    if not os.path.isdir(text):
        return False

    if isinstance(AOVTree.get_aov_dir(text), str):
        if len(AOVTree.get_aov_list(text))>0:
            AOVTree.create_and_load(text)

    return True
