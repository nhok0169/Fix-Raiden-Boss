# FIX RAIDEN BOSS
[![PyPI](https://img.shields.io/pypi/v/FixRaidenBoss2)](https://pypi.org/project/FixRaidenBoss2/)
[![PyPI](https://img.shields.io/pypi/pyversions/FixRaidenBoss2)](https://www.python.org/downloads/)
<a href=""><img alt="" src="https://cdn.discordapp.com/attachments/1030715335910887425/1060179887933104229/raiden.png?width=838&height=417"></a>
- Author Ideal [NK#1321](https://discordapp.com/users/277117247523389450)
- Thank [SilentNightSound#7430](https://github.com/SilentNightSound) for the logic rewrite
- Thank HazrateGolabi#1364 for combine and make final script
- Thank [Albert Gold#2696](https://github.com/Alex-Au1) for update the code for merged mods
## Requirements 
- [Python](https://www.python.org/downloads/)
- [DOWNLOAD](https://github.com/nhok0169/Fix-Raiden-Boss/archive/refs/heads/nhok0169.zip) script on this github

## How to Run
- Choose your pick of which way to run the script:
  1. [Quickstart!](#lets-start-)
  2. [CMD without a Script](#run-on-cmd-with-a-script)
  3. [CMD With a Script](#run-on-cmd-with-a-script)  

## Let's Start !
### STEP 1:
- Copy [THIS](https://github.com/nhok0169/Fix-Raiden-Boss/blob/nhok0169/Fix-Raiden-Boss%202.0%20(for%20all%20user%20)/RaidenBossFix2.py) script into Raiden Mod Folder 
### STEP 2:
- Double click on the script
  
- **RECOMMENDED** that you only run **1 TIME**  
*(By default, the script undos changes from previous runs before adding new changes or you can explicitely add the `--revert` option if you only want to undo previous runs without adding any new changes)*
### STEP 3:
- Open the game and enjoy it

## Update for merged mods
For merged mods, run the script wherever the `merged.ini` file is located.

## VIDEO TUTORIAL AND EXAMPLES:

### Quickstart
**Individual Mod:** https://www.youtube.com/watch?v=29FM0GywcWA  
**Merged Mods:** https://www.youtube.com/watch?v=nEyMYIHdrQM  
**Mega Merged Mods:** https://www.youtube.com/watch?v=08co5ct7zeg  

### More Features
[More examples here](../Examples)

## Run on CMD Without a Script
### STEP 1:
[open cmd](https://www.google.com/search?q=how+to+open+cmd+in+a+folder&oq=how+to+open+cmd) and type :
```python
python -m pip install -U FixRaidenBoss2
```
then enter

### STEP 2:
go to your mod folder and type:
```python
python -m FixRaidenBoss2
```
then enter

## Run on CMD With a Script
### STEP 1:
- Copy [THIS](https://github.com/nhok0169/Fix-Raiden-Boss/blob/nhok0169/Fix-Raiden-Boss%202.0%20(for%20all%20user%20)/RaidenBossFix2.py) script into Raiden Mod Folder 

### STEP 2:
go to your mod folder and type:
```python
python FixRaidenBoss2
```
then enter

## Command Options
```
  -h, --help           show this help message and exit
  -d, --deleteBackup   deletes backup copies of the original .ini files
  -f, --fixOnly        only fixes the mod without cleaning any previous runs of the script
  -r, --revert         reverts back previous runs of the script
  -m, --manualDisable  goes into an error when duplicate .ini or Blend.buf are found in a mod
                       instead of choosing which file you want to use
```
