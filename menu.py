import nuke
from spawner import SpawnerTemplates

SpawnerTemplates.initialize()

menu = nuke.menu("Nuke")
menu.addCommand('Edit/spawner/create', "import spawner\nspawner.SpawnerNode.create()")
menu.addCommand('Edit/spawner/Spawn!', lambda: [node["input_spawn"].execute() for node in nuke.selectedNodes() if node.knob("input_spawn")], 'shift+E')
