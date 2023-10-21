import os
import re


import nuke
from loader import PathsHandler
import pyseq


class SpawnerNode(object):

    CLASS = "NoOp"

    @classmethod
    def create(cls):
        node = nuke.createNode(cls.CLASS)
        node.setName("Spawner1")
        node.knob("tile_color").setValue(1280068863)

        knob = nuke.Tab_Knob("Spawner")
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

        return node

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
    def spawn(cls):
        input_data = cls._collect_search_inputs()
        file_list = input_data["file_list"]
        is_seq = input_data["seq"]
        spawner = input_data["node"]

        PathsHandler.SEQ = is_seq

        files_dict = PathsHandler.construct_file_paths(file_list)
        spawned = []
        for folder, content in files_dict.items():
            if isinstance(content, list):
                _, ext = os.path.splitext(content[0])
            else:
                _, ext = os.path.splitext(str(content))

            if ext in PathsHandler.FILE_FOLMATS[:9]:
                if is_seq:
                    if content.length() > 1:
                        seq = "{} {}".format(content.format("%h#%t"), content.format("%s-%e"))
                    else:
                        seq = "{} {}".format(str(content), "1-1")

                    read_node = nuke.createNode('Read', inpanel=False)
                    read_node.knob("file").fromUserText(os.path.join(folder, seq))
                    spawned.append(read_node)
                else:
                    for seq in nuke.getFileNameList(folder):
                        if os.path.splitext(seq.rsplit(" ", 1)[0])[1] in PathsHandler.FILE_FOLMATS:
                            read_node = nuke.createNode('Read')
                            read_node.knob('file').fromUserText(os.path.join(folder, seq))
                            spawned.append(read_node)

            elif ext in PathsHandler.FILE_FOLMATS[9:12]:
                if is_seq:
                    read_node = nuke.createNode('ReadGeo2', inpanel=False)
                    read_node.knob("file").setValue(os.path.join(folder, str(content)))
                    spawned.append(read_node)

            elif ext in PathsHandler.FILE_FOLMATS[12:]:

                if is_seq:
                    nuke.nodePaste(os.path.join(folder, str(content)))
                else:
                    for c in content:
                        nuke.nodePaste(os.path.join(c))
                # delete
                if spawner["delete_after"].getValue() == 1.0:
                    nuke.delete(spawner)
                return

        for node in spawner.dependent(nuke.INPUTS):
            node.setInput(0, spawned[0])

        # position nodes and selection
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

        # run post script
        script = spawner["input_post_script"].value()
        if script != "" and spawned:
            post_script = """
spawner = nuke.toNode("{}")
spawned = [nuke.toNode(n) for n in "{}".split(",")]

""".format(spawner.name(), ",".join([n.name() for n in spawned]))

            post_script += script
            exec(post_script)

        # delete
        if spawner["delete_after"].getValue() == 1.0:
            nuke.delete(spawner)
