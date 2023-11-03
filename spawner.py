import os
import re


import nuke
from loader import PathsHandler
import pyseq


def deselect_all():
    for node in nuke.selectedNodes():
        node.setSelected(False)

def get_spawners(selection):
    results = []
    for node in selection:
        if node.knob("__spawner") and node.knob("input_spawn"):
            results.append(node)

    return results


class SpawnerNode(object):

    CLASS = "NoOp"
    INPANEL = False
    VERSION = "v0.2"

    @classmethod
    def create(cls):
        selected_node = nuke.selectedNodes()
        selected_node = None if len(selected_node)==0 else selected_node[0]

        node = nuke.createNode(cls.CLASS)
        node.setName("Spawner1")
        node.knob("tile_color").setValue(1280068863)

        script = """
n = nuke.thisNode()
k = nuke.thisKnob()
if k.name() == "inputChange":
    inpt = n.input(0)
    if inpt and n.knob("file"):
        knob = inpt.knob("file")
        if knob:
            n["file"].setValue(knob.getValue())
            n["file"].setEnabled(False)
    elif n.knob("file"):
        n["file"].setEnabled(True)
        n["file"].setValue("")
"""
        node["knobChanged"].setValue(script)

        knob = nuke.Tab_Knob("Spawner")
        node.addKnob(knob)
        knob = nuke.Text_Knob("credit1", "", '<font size = 5 style="color:#F2E8C6">OutlineVFX</font>')
        node.addKnob(knob)
        knob = nuke.Text_Knob("credit2", "", '<font size = 6 style="color:#FFBB5C"><b>Spawner</b></font>')
        node.addKnob(knob)
        knob = nuke.Text_Knob("credit3", "", '<font size = 3 style="color:#666"><br>{}</br></font>'.format(cls.VERSION))
        knob.clearFlag(nuke.STARTLINE)
        node.addKnob(knob)
        knob = nuke.Text_Knob("div_00", "")
        node.addKnob(knob)
        knob = nuke.File_Knob("file", "file")
        node.addKnob(knob)
        knob = nuke.PyScript_Knob("analize", "analize", "import spawner\nspawner.SpawnerNode.analize()")
        knob.clearFlag(nuke.STARTLINE)
        node.addKnob(knob)
        knob = nuke.Boolean_Knob("delete_line", "delete after")
        knob.setFlag(nuke.STARTLINE)
        node.addKnob(knob)
        knob = nuke.Boolean_Knob("guess", "from env")
        knob.clearFlag(nuke.STARTLINE)
        knob.setValue(1)
        node.addKnob(knob)
        knob = nuke.Text_Knob("div_01", "")
        node.addKnob(knob)
        knob = nuke.Boolean_Knob("delete_after", "delete spawner")
        node.addKnob(knob)
        knob = nuke.Boolean_Knob("select_after", "select node")
        knob.clearFlag(nuke.STARTLINE)
        node.addKnob(knob)
        knob = nuke.XY_Knob("position_after", "position")
        node.addKnob(knob)
        knob.setValue([0, 100])
        knob = nuke.Text_Knob("div_02", "")
        node.addKnob(knob)
        knob = nuke.Text_Knob("__spawner", "")
        knob.setVisible(False)
        node.addKnob(knob)

        cls.fill_filepath(selected_node, node)

        return node

    @classmethod
    def fill_filepath(cls, selected_node, spawner):
        if selected_node:
            knob = selected_node.knob("file")
            if knob:
                spawner["file"].setValue(knob.getValue())
                spawner["analize"].execute()

    @classmethod
    def analize(cls):
        node = nuke.thisNode()
        file_path = node.knob("file").value()
        if not os.path.splitext(file_path)[1] in PathsHandler.FILE_FOLMATS:
            file_path = None

        delete_after = node.knob("delete_line").getValue()
        guess = node.knob("guess").getValue() == 1.0

        [node.removeKnob(node[n]) for n in node.knobs() if n.startswith("input_")]

        if file_path:
            knob = nuke.Boolean_Knob("input_is_seq", "image sequence")
            knob.setValue(1)
            node.addKnob(knob)

            path_list = PathsHandler._split(file_path, guess)
            for i, string in enumerate(path_list):
                knob = nuke.String_Knob("input_{}".format(i), "search".format(i), string)
                node.addKnob(knob)
                remove_script = "n=nuke.thisNode()\nn.removeKnob(n['input_{0}'])\nn.removeKnob(nuke.thisKnob())".format(i)
                knob = nuke.PyScript_Knob("input_{}_x".format(i), "X", remove_script)
                knob.clearFlag(nuke.STARTLINE)
                node.addKnob(knob)
            knob = nuke.Text_Knob("input_div", "")
            node.addKnob(knob)
            knob = nuke.Multiline_Eval_String_Knob("input_post_script", "post spawn script")
            node.addKnob(knob)
            knob = nuke.PyScript_Knob("input_spawn", "Spawn!", "import spawner\nspawner.SpawnerNode.spawn()")
            knob.setFlag(nuke.STARTLINE)
            node.addKnob(knob)

            if delete_after:
                node.removeKnob(node.knob("file"))
                node.removeKnob(node.knob("analize"))
                node.removeKnob(node.knob("delete_line"))
                node.removeKnob(node.knob("guess"))
                node.removeKnob(node.knob("div_01"))
        else:
            nuke.message("wrong filepath!\n\n    - must not be empty\n    - must be a file")

    @classmethod
    def _collect_search_inputs(cls):
        node = nuke.thisNode()

        knobs = [str(node[n].toScript()) for n in node.knobs() if re.match(r'^input_\d+$', n)]

        input_data = {
            "file_list": knobs,
            "seq": node["input_is_seq"].getValue() == 1.0,
            "node": node,
        }
        return input_data

    @classmethod
    def _create_read_node(cls, filepath):
        read_node = nuke.createNode("Read", inpanel=cls.INPANEL)
        read_node.knob("file").fromUserText(filepath)
        return read_node

    @classmethod
    def _handle_image_files(cls, is_seq, folder, content):
        node_list = []

        if is_seq:
            if content.length() > 1:
                seq = "{} {}".format(content.format("%h%p%t"), content.format("%s-%e"))
            else:
                seq = "{} {}".format(str(content), "1-1")

            node_list.append(cls._create_read_node(os.path.join(folder, seq)))
        else:
            for seq in nuke.getFileNameList(folder):
                if os.path.splitext(seq.rsplit(" ", 1)[0])[1] in PathsHandler.FILE_FOLMATS:
                    node_list.append(cls._create_read_node(os.path.join(folder, seq)))

        return node_list

    @classmethod
    def _create_read_geo_node(cls, filepath):
        read_node = nuke.createNode("ReadGeo2", inpanel=cls.INPANEL)
        read_node.knob("file").setValue(filepath)
        return read_node

    @classmethod
    def _create_camera_node(cls, filepath):
        camera_node = nuke.createNode("Camera3", inpanel=False)
        camera_node.knob("file").setValue(filepath)
        camera_node["read_from_file"].setValue(1)
        camera_node.showControlPanel()
        return camera_node

    @classmethod
    def _handle_geo_files(cls, is_seq, folder, content, is_cam):
        node_list = []

        if is_seq:
            if is_cam:
                geo_node = cls._create_camera_node(os.path.join(folder, str(content)))
            else:
                geo_node = cls._create_read_geo_node(os.path.join(folder, str(content)))
            node_list.append(geo_node)
        else:
            for file in content:
                if is_cam:
                    node_list.append(cls._create_camera_node(file))
                else:
                    node_list.append(cls._create_read_geo_node(file))

        return node_list

    @classmethod
    def _handle_script_files(cls, is_seq, folder, content):
        if is_seq:
            nuke.nodePaste(os.path.join(folder, str(content)))
        else:
            for c in content:
                nuke.nodePaste(os.path.join(c))

    @classmethod
    def _get_content_ext(cls, content):
        if isinstance(content, list):
            _, ext = os.path.splitext(content[0])
        else:
            _, ext = os.path.splitext(str(content))

        return ext

    @classmethod
    def _post_spawn_connections(cls, spawner, spawned):
        dep = spawner.dependent(nuke.INPUTS)
        for n in dep:
            for i in range(n.inputs()):
                inpt = n.input(i)
                if inpt and inpt==spawner:
                    n.setInput(i, spawned[0])

    @classmethod
    def _post_spawn_positions(cls, spawner, spawned):
        position = spawner["position_after"].getValue()
        select = spawner["select_after"].getValue() == 1.0
        offset_x = 0
        offset_y = 0
        for node in spawned:
            node.setSelected(select)
            node.setXYpos(int(spawner.xpos()+position[0]+offset_x), int(spawner.ypos()+position[1]+offset_y))
            if position[0] != 0:
                offset_x += 100
            if position[1] != 0:
                offset_x += 100

    @classmethod
    def _post_spawn_script(cls, spawner, spawned):
        script = spawner["input_post_script"].value()
        if script != "" and spawned:
            post_script = "spawner = nuke.toNode(\"{}\")\n".format(spawner.name())
            post_script += "spawned = [nuke.toNode(n) for n in \"{}\".split(\",\")]\n".format(",".join([n.name() for n in spawned]))
            post_script += script
            exec(post_script)


    @classmethod
    def _post_spawn_actions(cls, spawner, spawned):
        if spawned:
            cls._post_spawn_connections(spawner, spawned)
            cls._post_spawn_positions(spawner, spawned)
            cls._post_spawn_script(spawner, spawned)

    @classmethod
    def spawn(cls):

        deselect_all()

        input_data = cls._collect_search_inputs()
        file_list = input_data["file_list"]
        is_seq = input_data["seq"]
        spawner = input_data["node"]
        delete_after = spawner["delete_after"].getValue() == 1.0

        PathsHandler.SEQ = is_seq

        files_dict = PathsHandler.construct_file_paths(file_list)
        spawned = []
        for folder, content in files_dict.items():
            ext = cls._get_content_ext(content)

            if ext in PathsHandler.FILE_FOLMATS[:9]:
                node_list = cls._handle_image_files(is_seq, folder, content)
                spawned.extend(node_list)

            elif ext in PathsHandler.FILE_FOLMATS[9:12]:
                cam = spawner.knob("cam")
                if cam:
                    cam = cam.getValue() == 1.0
                node_list = cls._handle_geo_files(is_seq, folder, content, cam)
                spawned.extend(node_list)

            elif ext in PathsHandler.FILE_FOLMATS[12:]:
                cls._handle_script_files(is_seq, folder, content)
                if delete_after:
                    nuke.delete(spawner)
                return
            else:
                return

        cls._post_spawn_actions(spawner, spawned)

        # delete
        if delete_after:
            nuke.delete(spawner)


class SpawnerTemplates(object):

    TEMPLATES_DIR = os.getenv("SPAWNER_TEMPLATES_DIR", "/mnt/outline/work/_tools/nuke_spawner")
    SHOW_SPECIFIC = True
    ROOT_NAME = "SPAWNER"

    @classmethod
    def __templates_path(cls):
        if cls.SHOW_SPECIFIC:
            return os.path.join(cls.TEMPLATES_DIR, os.getenv("MY_PROJECT_ABBR", ""))
        return cls.TEMPLATES_DIR

    @classmethod
    def __get_templates_root(cls):
        if cls.SHOW_SPECIFIC:
            return os.getenv("MY_PROJECT_ABBR", "").upper()
        return cls.ROOT_NAME

    @classmethod
    def _get_templates(cls):
        search_path = cls.__templates_path()
        templates = []

        for root, dirs, files in os.walk(search_path):
            for file in files:
                if file.endswith('.nk'):
                    templates.append("{}{}/{}".format(cls.__get_templates_root(), root.replace(search_path, ""), file[:-3]))

        return templates

    @classmethod
    def _clear_toolbar(cls):
        nuke.toolbar("Nodes").removeItem(cls.__get_templates_root())

    @classmethod
    def load_template(cls, template_path):
        deselect_all()
        nuke.nodePaste(template_path)
        spawners = get_spawners(nuke.selectedNodes())
        for spawner in spawners:
            spawner["input_spawn"].execute()

    @classmethod
    def reload_toolbar(cls):
        cls._clear_toolbar()
        cls.initialize()

    @classmethod
    def initialize(cls):
        toolbar = nuke.toolbar("Nodes")
        root_name = cls.__get_templates_root()
        toolbar = toolbar.addMenu(root_name)

        for template in cls._get_templates():
            template_path = "{}{}.nk".format(cls.__templates_path(), template.replace(root_name, ""))
            toolbar.addCommand(template.replace(root_name+"/", ""), "import spawner\nspawner.SpawnerTemplates.load_template('{}')".format(template_path))

        toolbar.addSeparator()
        toolbar.addCommand("Reload", "import spawner\nspawner.SpawnerTemplates.reload_toolbar()")
