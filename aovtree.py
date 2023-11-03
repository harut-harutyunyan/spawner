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
    VERSION = "v0.1"

    @classmethod
    def get_aov_dir(cls, filepath):
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
    def shuffle_layer(cls, from_node, to_node, layer):
        cls.create_layer(layer)
        suffle_copy = nuke.createNode("ShuffleCopy", inpanel=False)
        suffle_copy.setName("Shuffle_{}".format(layer))
        suffle_copy.setInput(0, from_node)
        suffle_copy.setInput(1, to_node)
        suffle_copy["out"].setValue(layer)
        suffle_copy["red"].setValue(1)
        suffle_copy["green"].setValue(2)
        suffle_copy["blue"].setValue(3)
        suffle_copy["disable"].setExpression("!_aov_{}".format(layer))

        suffle_copy.setXYpos(int(from_node.xpos()), int(from_node.ypos()+cls.Y_OFFSET))
        return suffle_copy

    @classmethod
    def get_read_string(cls, beauty, change_to=None):
        string = "{}%04d{} {}".format(beauty.format("%D%h"), beauty.format("%t"), beauty.format("%s-%e"))
        string = string.replace("\\", "/")
        if change_to:
            string = string.replace(cls.BEAUTY_NAME, change_to)
        print(string)
        return string

    @classmethod
    def get_beauty(cls, filepath):
        beauty_dir = os.path.join(cls.get_aov_dir(filepath), cls.BEAUTY_NAME)
        beauty = pyseq.Sequence([os.path.join(beauty_dir, f) for f in os.listdir(beauty_dir)])
        return beauty

    @classmethod
    def get_aov_list(cls, filepath):
        aov_list = os.listdir(cls.get_aov_dir(filepath))
        aov_list.remove(cls.BEAUTY_NAME)
        return aov_list

    @classmethod
    def __load_aovs(cls, filepath):
        beauty = cls.get_beauty(filepath)
        aov_list = cls.get_aov_list(filepath)
        beauty_read = cls._create_read_node(cls.get_read_string(beauty))
        last_node = beauty_read
        for aov in aov_list:
            if "crypto" in aov:
                continue
            else:
                aov_read = cls._create_read_node(cls.get_read_string(beauty, aov))
                aov_read.setXYpos(int(last_node.xpos()+cls.X_OFFSET), int(last_node.ypos()+cls.Y_OFFSET))
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
