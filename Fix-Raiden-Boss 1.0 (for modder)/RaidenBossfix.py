print("MAKE SURE YOU DONE ALL STEP BEFORE THIS STEP")
print("if you got ERROR after this don't ask why")
input("Press Enter to continue...")
#create DISABLED folder bc im stupid
import os
if not os.path.exists("DISABLED"):
    os.mkdir("DISABLED")
print("create DISABLED folder")
#copy backup file file
import shutil
src_dir = os.getcwd() #get the current working dir

dest_dir = src_dir+"/DISABLED"
src_file = os.path.join(src_dir, 'RaidenShogun.ini')
if not os.path.exists(dest_dir+"/RaidenShogun.ini"): #check file already exist
  shutil.copy(src_file,dest_dir)
#it double bc im stupid dont ask why and this will have on next version

#dest_dir = src_dir+"/DISABLED"
#src_file = os.path.join(src_dir, 'RaidenShogunBlend.buf')
#if not os.path.exists(dest_dir+"/RaidenShogunBlend.buf"):
 #shutil.copy(src_file,dest_dir)

print("copy backup file to "+src_dir+"\DISABLED")
print("if you want it back move them back i don't know how to make script for give back (lazy)")
#addline on the ini file and copy the draw number
import configparser
from sys import argv
import re

src = "RaidenShogun.ini" 
add = """\
;raiden boss fixed by NK#1321 if you used it for fix your raiden pls give credit for "Nhok0169"
;thank nguen#2011 for support
[TextureOverrideRaidenShogunBossBlend]
hash = fe5c0180
vb1 = ResourceRaidenShogunBossBlend
handling = skip

[ResourceRaidenShogunBossBlend]
type = Buffer
stride = 32
filename = RaidenShogunBossBlend.buf
"""

pattern = re.compile(r"TextureOverride(\w+)Blend")
parser = configparser.ConfigParser()

parser.read(src)

for k in dict(parser).keys():
    if pattern.match(k) != None:
        blend = dict(parser[k])

if blend["draw"]:
    draw: str = blend["draw"]

parser.clear()
parser.read_string(add)
for k in dict(parser).keys():
    if pattern.match(k) != None:
        parser[k]['draw'] = draw
    
with open(src, "r") as f:
    original = f.read()

with open(src, "w") as f:
    parser.write(f)

with open(src, "a") as f:
    f.write(original)
