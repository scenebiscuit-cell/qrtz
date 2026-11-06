"""Hands the lava-lamp blobs' numbers to crystal_blobs.glsl.

Synced into the Text DAT /project1/virtual_crystal/droplet_table. The Script CHOP
"droplets" calls onCook once a frame and writes one sample per blob. The numbers
themselves come from the Droplets class in crystal_motion.py.
"""

COLUMNS = ('x', 'y', 'radius', 'distance', 'heading', 'stretch', 'ripple', 'kind')


def onCook(scriptOp):
    rows = op('crystal_motion').module.droplet_rows()
    scriptOp.isTimeSlice = False
    scriptOp.clear()
    scriptOp.numSamples = len(rows)
    for index, name in enumerate(COLUMNS):
        chan = scriptOp.appendChan(name)
        for sample, row in enumerate(rows):
            chan[sample] = row[index]


def onGetCookLevel(scriptOp):
    """Cook every frame, because the blobs are always moving."""
    return CookLevel.ALWAYS
