import ezdxf

# create a new DXF R2010 document
doc = ezdxf.new("R2010")

# add new entities to the modelspace
msp = doc.modelspace()
# add a LINE entity
msp.add_line((0, 0), (10, 0))
# save the DXF document
doc.saveas("line.dxf")