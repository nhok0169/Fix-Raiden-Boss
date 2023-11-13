# FIX RAIDEN BOSS
[![PyPI](https://img.shields.io/pypi/pyversions/FixRaidenBoss2)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/FixRaidenBoss2)](https://pypi.org/project/FixRaidenBoss2/)
[![PyPI](https://img.shields.io/pypi/dm/FixRaidenBoss2?label=pypi%20downloads)](https://pypi.org/project/FixRaidenBoss2/)
<a href=""><img alt="" src="https://cdn.discordapp.com/attachments/1030715335910887425/1060179887933104229/raiden.png?width=838&height=417"></a>
- Author Ideal [NK#1321](https://discordapp.com/users/277117247523389450)
- Thank [SilentNightSound#7430](https://github.com/SilentNightSound) for the logic rewrite
- Thank HazrateGolabi#1364 for combine and make final script
- Thank [Albert Gold#2696](https://github.com/Alex-Au1) for update the code for merged mods
## Requirements 
- [Python](https://www.python.org/downloads/)

## Update for merged mods
For merged mods, run the script wherever the `merged.ini` file is located.

## VIDEO TUTORIAL AND EXAMPLES:

### Quickstart
**Individual Mod:** https://www.youtube.com/watch?v=29FM0GywcWA  
**Merged Mods:** https://www.youtube.com/watch?v=nEyMYIHdrQM  
**Mega Merged Mods:** https://www.youtube.com/watch?v=08co5ct7zeg  

### More Features
[More examples here](https://github.com/nhok0169/Fix-Raiden-Boss/tree/nhok0169/Examples)

## How to Run
- Choose your pick of which way to run the script:

  1. [Quickstart!](#lets-start-)  &nbsp;&nbsp;(for beginners)
  2. [CMD WITHOUT a Script](#run-on-cmd-without-a-script) &nbsp;&nbsp; (recommended if you run by CMD)
  3. [CMD with a Script](#run-on-cmd-with-a-script) &nbsp;&nbsp; (the convention that other GIMI scripts follow)

## Let's Start !
### STEP 1:
- Copy [THIS](https://github.com/nhok0169/Fix-Raiden-Boss/blob/nhok0169/Fix-Raiden-Boss%202.0%20(for%20all%20user%20)/src/FixRaidenBoss2/FixRaidenBoss2.py) script into Raiden Mod Folder 
### STEP 2:
- Double click on the script
### STEP 3:
- Open the game and enjoy it

## Run on CMD Without a Script
### STEP 1:
- Install the module onto your computer by [opening cmd](https://www.google.com/search?q=how+to+open+cmd+in+a+folder&oq=how+to+open+cmd) and typing :
```python
python -m pip install -U FixRaidenBoss2
```
then enter

*( you can now run the program anywhere without copying a script! )*

### STEP 2:
- [open cmd](https://www.google.com/search?q=how+to+open+cmd+in+a+folder&oq=how+to+open+cmd) in your mod folder and type:
```python
python -m FixRaidenBoss2
```
then enter

### STEP 3:
- Open the game and enjoy it

## Run on CMD With a Script
### STEP 1:
- Copy [THIS](https://github.com/nhok0169/Fix-Raiden-Boss/blob/nhok0169/Fix-Raiden-Boss%202.0%20(for%20all%20user%20)/src/FixRaidenBoss2/FixRaidenBoss2.py) script into Raiden Mod Folder 

### STEP 2:
- [open cmd](https://www.google.com/search?q=how+to+open+cmd+in+a+folder&oq=how+to+open+cmd) and type
```python
python FixRaidenBoss2.py
```
then enter

### STEP 3:
- Open the game and enjoy it

## Command Options
```
  -h, --help           show this help message and exit
  -s str, --src str    The path to the Raiden mod folder. If this option is not specified, then will use the current
                       directory as the mod folder.
  -d, --deleteBackup   deletes backup copies of the original .ini files
  -f, --fixOnly        only fixes the mod without cleaning any previous runs of the script
  -r, --revert         reverts back previous runs of the script
  -m, --manualDisable  goes into an error when duplicate .ini or Blend.buf are found in a mod instead of choosing
                       which file you want to use
  -p, --purgeDups      deletes unused duplicate .ini or Blend.buf instead of keeping a disabled backup copy of those
                       files
  -l, --log            Logs the printed out log into the RSFixLog.txt file
```

## API Usage

Tool developpers can now include the fix within their code.

<br>

*Make sure you first install the module by typing into [cmd](https://www.google.com/search?q=how+to+open+cmd+in+a+folder&oq=how+to+open+cmd):*
```bash
python -m pip install -U FixRaidenBoss2
```

<br>

### Example of Successful Run
```python
import FixRaidenBoss2 as FRB

raidenBossFixService = FRB.RaidenBossFixService(path = r"my raiden folder path", log = True, verbose = False)
raidenBossFixService.fix()

print("The Raiden Mod is fixed!")
```
<br>

<details>
<summary>Example Result</summary>
<br>

```
Creating log file, RSFixLog.txt
The Raiden Mod is fixed!
```
</details>
<br>

### Example of Handling Errors
```python
import FixRaidenBoss2 as FRB

raidenBossFixService = FRB.RaidenBossFixService(path = r"my raiden folder path that contains a duplicate .ini file", log = True, verbose = False)

print("Starting to fix mod...")
try:
    raidenBossFixService.fix()
except FRB.DuplicateFileException as e:
    print("The fix failed because there is a duplicate .ini file... :(")
else:
    print("The Raiden Mod is fixed!")
```
<br>

<details>
<summary>Example Result</summary>
<br>

```
Starting to fix mod...
Creating log file, RSFixLog.txt
The fix failed because there is a duplicate .ini file... :(
```
</details>
<br>

More info [here](https://github.com/nhok0169/Fix-Raiden-Boss/blob/nhok0169/Fix-Raiden-Boss%202.0%20(for%20all%20user%20)/src/FixRaidenBoss2/FixRaidenBoss2.py)
